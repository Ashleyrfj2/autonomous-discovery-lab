"""Stage routing with persistent reservations, cache, bounded retries and circuit breakers."""

import time
from collections.abc import Callable
from decimal import Decimal

from autodiscover.config import Limits
from autodiscover.models.contracts import (
    Generation,
    GenerationRequest,
    Provider,
    ProviderError,
    T,
    parse_structured,
)
from autodiscover.models.providers import HTTPProvider
from autodiscover.orchestrator.durability import canonical
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
        cache_only: bool = False,
    ):
        self.store, self.routes = store, routes
        self.budget = Budget(store)
        self.cache_only = cache_only
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

    def _record_failure(
        self, run_id: str, provider: Provider, code: str, attempt: int, *, uncertain: bool
    ) -> None:
        self._circuit(provider, code)
        with self.store.connection(write=True) as db:
            self.store._event(
                db,
                run_id,
                "provider_failed",
                {
                    "provider": provider.name,
                    "model": provider.model,
                    "code": code,
                    "uncertain": uncertain,
                    "attempt": attempt,
                },
            )

    def generate(
        self, run_id: str, stage: str, request: GenerationRequest, *, key: str
    ) -> Generation:
        return self._generate(run_id, stage, request, key=key)

    def _generate(
        self, run_id: str, stage: str, request: GenerationRequest, *, key: str,
        validate: Callable[[str], str] | None = None,
    ) -> Generation:
        if not key or len(key) > 180:
            raise ValueError("Bounded stable request key required")
        providers = self.routes.get(stage)
        if not providers:
            raise ProviderError("STAGE_NOT_CONFIGURED")
        identity = {
            "request": request.model_dump(mode="json"),
            "stage": stage,
            "route": [(p.name, p.model) for p in providers],
        }
        profiles = [
            (i, p.config.kind, p.config.profile, p.config.reasoning_effort)
            for i, p in enumerate(providers)
            if isinstance(p, HTTPProvider)
            and (p.config.profile != "standard" or p.config.reasoning_effort is not None)
        ]
        if profiles:
            identity["wire_profiles"] = profiles
        fingerprint = request_fingerprint(identity)
        cached = self.budget.cached(run_id, key, fingerprint)
        if cached is not None:
            result = Generation.model_validate(cached)
            if (result.provider, result.model) not in {(p.name, p.model) for p in providers}:
                raise ProviderError("PROVIDER_IDENTITY_MISMATCH")
            return result
        if self.cache_only:
            raise ProviderError("CACHE_MISS")
        row = self.store.get_run(run_id)
        policy = Limits.model_validate_json(row["policy_json"])
        last_error = ProviderError("NO_AVAILABLE_PROVIDER")
        attempts = 0
        ambiguous_live_outcome = False
        for index, provider in enumerate(providers):
            if provider.is_live:
                if ambiguous_live_outcome:
                    continue
                if not policy.allow_live_inference:
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
                )
                attempts += 1
                try:
                    result = provider.generate(request)
                except ProviderError as error:
                    actual = Decimal(0) if error.known_zero_cost else error.cost_usd
                    self.budget.settle(
                        reservation, actual,
                        usage=error.usage.model_dump(exclude_none=True) if error.usage else None,
                    )
                    self._record_failure(
                        run_id, provider, error.code, attempts, uncertain=actual is None
                    )
                    last_error = error
                    ambiguous_live_outcome |= provider.is_live and error.uncertain
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
                identity_matches = (result.provider, result.model) == (
                    provider.name, provider.model
                )
                validation_failed = False
                if identity_matches:
                    try:
                        cleaned = validate(result.text) if validate else sanitize(result.text)
                        result = result.model_copy(update={"text": cleaned})
                    except (ValueError, RecursionError):
                        validation_failed = True
                self.budget.settle(
                    reservation,
                    result.cost_usd if identity_matches or not provider.is_live else None,
                    usage=result.usage.model_dump(exclude_none=True),
                    result=(
                        result.model_dump(mode="json")
                        if identity_matches and not validation_failed
                        else None
                    ),
                )
                if not identity_matches:
                    self._record_failure(
                        run_id, provider, "PROVIDER_IDENTITY_MISMATCH", attempts,
                        uncertain=provider.is_live,
                    )
                    raise ProviderError("PROVIDER_IDENTITY_MISMATCH", uncertain=provider.is_live)
                if validation_failed:
                    self._record_failure(
                        run_id, provider, "INVALID_STRUCTURED_RESPONSE", attempts, uncertain=False
                    )
                    raise ProviderError("INVALID_STRUCTURED_RESPONSE")
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

        def validate(text: str) -> str:
            # Validate before redaction so a changed value cannot legitimize invalid output.
            value = parse_structured(text, schema)
            cleaned = canonical(sanitize(value.model_dump(mode="json")))
            schema.model_validate_json(cleaned, strict=True)
            return cleaned

        result = self._generate(run_id, stage, request, key=key, validate=validate)
        try:
            return parse_structured(result.text, schema), result
        except (ValueError, RecursionError):
            raise ProviderError("INVALID_STRUCTURED_RESPONSE") from None
