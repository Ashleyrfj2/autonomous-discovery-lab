"""Stage routing with persistent reservations, cache, bounded retries and circuit breakers."""

import time
from collections.abc import Callable
from decimal import Decimal

from pydantic import ValidationError

from autodiscover.config import Limits
from autodiscover.models.contracts import Generation, GenerationRequest, Provider, ProviderError, T
from autodiscover.orchestrator.store import Store
from autodiscover.security.budget import Budget, request_fingerprint
from autodiscover.security.cancellation import cancellable_wait
from autodiscover.security.redaction import sanitize


class Router:
    def __init__(
        self,
        store: Store,
        routes: dict[str, list[Provider]],
        *,
        fallback_evidence: dict[str, str] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.store, self.routes = store, routes
        self.budget = Budget(store)
        self.fallback_evidence, self.sleeper = fallback_evidence or {}, sleeper
        for stage, providers in routes.items():
            if not providers:
                raise ValueError("Every route requires a provider")
            if len(providers) > 1 and not self.fallback_evidence.get(stage):
                raise ValueError("Fallback requires recorded task-specific evaluation evidence")

    def _circuit(self, provider: Provider, error: str | None) -> None:
        with self.store.connection(write=True) as db:
            row = db.execute(
                "SELECT * FROM circuits WHERE provider=? AND model=?",
                (provider.name, provider.model),
            ).fetchone()
            failures = (row["failures"] if row else 0) + 1 if error else 0
            until = self.store.clock() + 60 if failures >= 3 else 0
            db.execute(
                """INSERT INTO circuits VALUES(?,?,?,?,?)
                ON CONFLICT(provider,model) DO UPDATE SET failures=excluded.failures,
                open_until=excluded.open_until,last_error=excluded.last_error""",
                (provider.name, provider.model, failures, until, error),
            )

    def _available(self, provider: Provider) -> bool:
        with self.store.connection() as db:
            row = db.execute(
                "SELECT open_until FROM circuits WHERE provider=? AND model=?",
                (provider.name, provider.model),
            ).fetchone()
        return row is None or row[0] <= self.store.clock()

    def generate(
        self, run_id: str, stage: str, request: GenerationRequest, *, key: str
    ) -> Generation:
        if not key or len(key) > 180:
            raise ValueError("Bounded stable request key required")
        providers = self.routes.get(stage)
        if not providers:
            raise ProviderError("STAGE_NOT_CONFIGURED")
        fingerprint = request_fingerprint(
            {
                "request": request.model_dump(mode="json"),
                "stage": stage,
                "route": [(p.name, p.model) for p in providers],
            }
        )
        cached = self.budget.cached(run_id, key, fingerprint)
        if cached is not None:
            result = Generation.model_validate(cached)
            if (result.provider, result.model) not in {(p.name, p.model) for p in providers}:
                raise ProviderError("PROVIDER_IDENTITY_MISMATCH")
            return result
        row = self.store.get_run(run_id)
        policy = Limits.model_validate_json(row["policy_json"])
        last_error = ProviderError("NO_AVAILABLE_PROVIDER")
        attempts = 0
        for index, provider in enumerate(providers):
            if provider.is_live and not policy.allow_live_inference:
                raise ProviderError("RUN_LIVE_NOT_AUTHORIZED")
            if not self._available(provider):
                continue
            while attempts <= policy.max_retries_per_step:
                amount = provider.estimate_cost(request)
                reservation = self.budget.reserve(
                    run_id,
                    f"{key}:{attempts}",
                    fingerprint,
                    amount,
                    provider.name,
                    provider.model,
                    request_limit_usd=policy.max_cost_per_run_usd
                    / max(2, policy.max_hypotheses_per_cycle),
                )
                attempts += 1
                try:
                    result = provider.generate(request)
                except ProviderError as error:
                    self.budget.settle(reservation, Decimal(0) if error.known_zero_cost else None)
                    self._circuit(provider, error.code)
                    with self.store.connection(write=True) as db:
                        self.store._event(
                            db,
                            run_id,
                            "provider_failed",
                            {
                                "provider": provider.name,
                                "model": provider.model,
                                "code": error.code,
                                "uncertain": error.uncertain,
                                "attempt": attempts,
                            },
                        )
                    last_error = error
                    if error.code == "PROVIDER_CANCEL_REQUESTED":
                        raise error
                    # A timeout/ambiguous server result is never replayed automatically.
                    if (
                        error.retryable
                        and not error.uncertain
                        and attempts <= policy.max_retries_per_step
                        and self._available(provider)
                    ):
                        delay = min(max(error.retry_after, 0.25 * 2 ** (attempts - 1)), 30)
                        if not cancellable_wait(delay, self.sleeper):
                            raise ProviderError(
                                "PROVIDER_CANCEL_REQUESTED", known_zero_cost=True
                            ) from None
                        continue
                    break
                # No prompt/auth/error bodies are persisted. Redact recognizable secrets in output.
                result = result.model_copy(update={"text": sanitize(result.text)})
                identity_matches = (result.provider, result.model) == (
                    provider.name, provider.model
                )
                within_bound = result.cost_usd <= amount
                self.budget.settle(
                    reservation,
                    result.cost_usd,
                    usage=result.usage.model_dump(),
                    result=(
                        result.model_dump(mode="json")
                        if identity_matches and within_bound
                        else None
                    ),
                )
                if not within_bound:
                    raise ProviderError("RESERVATION_BOUND_EXCEEDED", uncertain=True)
                if not identity_matches:
                    self._circuit(provider, "PROVIDER_IDENTITY_MISMATCH")
                    raise ProviderError("PROVIDER_IDENTITY_MISMATCH")
                self._circuit(provider, None)
                with self.store.connection(write=True) as db:
                    self.store._event(
                        db,
                        run_id,
                        "provider_selected",
                        {
                            "stage": stage,
                            "provider": result.provider,
                            "model": result.model,
                            "fallback": index > 0,
                            "evaluation": self.fallback_evidence.get(stage),
                            "request_fingerprint": fingerprint,
                        },
                    )
                return result
            if attempts > policy.max_retries_per_step:
                break
        raise last_error

    def generate_structured(
        self, run_id: str, stage: str, request: GenerationRequest, schema: type[T], *, key: str
    ) -> tuple[T, Generation]:
        request = request.model_copy(update={"json_schema": schema.model_json_schema()})
        result = self.generate(run_id, stage, request, key=key)
        try:
            return schema.model_validate_json(result.text), result
        except ValidationError:
            raise ProviderError("INVALID_STRUCTURED_RESPONSE") from None
