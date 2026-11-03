import json
from decimal import Decimal

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from autodiscover.config import Limits
from autodiscover.hypotheses.proposals import ResearchProposal
from autodiscover.models.contracts import GenerationRequest, ProviderConfig, ProviderError
from autodiscover.models.providers import BasetenProvider, MetaProvider, MockProvider
from autodiscover.models.router import Router
from autodiscover.models.teams import CriticalReview
from autodiscover.orchestrator.store import Store
from autodiscover.security.budget import Budget, BudgetError


class Proposal(BaseModel):
    prediction: str


def config(kind="meta", **overrides):
    return ProviderConfig.model_validate(
        dict(
            name=kind,
            kind=kind,
            model="configured-test-model",
            api_key_env="TEST_PROVIDER_KEY",
            input_usd_per_million="1",
            output_usd_per_million="2",
            context_window=8192,
            output_limit=1024,
            structured_output=True,
            capability_source="contract fixture; not live capability evidence",
            pricing_source="test rates, not real prices",
            verified_on="2026-11-03",
            live_authorized=True,
            **overrides,
        )
    )


def response(text='{"prediction":"measurable"}', **changes):
    data = {
        "model": "configured-test-model",
        "choices": [{"finish_reason": "stop", "message": {"content": text}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
    }
    data.update(changes)
    return httpx.Response(200, json=data)


@pytest.mark.parametrize("kind,cls", [("meta", MetaProvider), ("baseten", BasetenProvider)])
def test_http_contracts_structured_usage_health(kind, cls):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer contract-secret"
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "configured-test-model"}]})
        body = json.loads(request.content)
        assert body["model"] == "configured-test-model"
        cap = "max_completion_tokens" if kind == "meta" else "max_tokens"
        assert body[cap] == 512
        assert body["response_format"]["type"] == "json_schema"
        return response()

    provider = cls(
        config(kind), transport=httpx.MockTransport(handler), api_key=SecretStr("contract-secret")
    )
    typed, generated = provider.generate_structured(
        GenerationRequest(prompt="bounded question"), Proposal
    )
    assert typed.prediction == "measurable"
    assert generated.cost_usd == Decimal("0.00016")
    assert provider.estimate_cost(GenerationRequest(prompt="question")) == Decimal("0.009216")
    assert provider.get_usage().input_tokens == 100
    assert provider.health_check()["healthy"]
    assert len(requests) == 2


def test_live_authority_and_capabilities_fail_closed(tmp_path):
    c = config().model_copy(update={"live_authorized": False})
    provider = MetaProvider(c, api_key=SecretStr("never-sent"))
    with pytest.raises(ProviderError, match="LIVE_NOT_AUTHORIZED"):
        provider.generate(GenerationRequest(prompt="test"))
    with pytest.raises(ProviderError, match="OUTPUT_CAPABILITY_EXCEEDED"):
        provider.estimate_cost(GenerationRequest(prompt="test", max_output_tokens=1025))
    store = Store(tmp_path)
    run = store.create_run("test", {})
    with pytest.raises(ProviderError, match="RUN_LIVE_NOT_AUTHORIZED"):
        Router(store, {"hypothesize": [provider]}).generate(
            run, "hypothesize", GenerationRequest(prompt="test"), key="request1"
        )
    assert Budget(store).totals(run)["requests"] == 0


def test_cached_response_survives_new_router_without_duplicate_calls(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("cache", {})
    request = GenerationRequest(prompt="propose")
    first = Router(store, {"hypothesize": [MockProvider([{"prediction": "falsifiable"}])]})
    proposal, result = first.generate_structured(
        run, "hypothesize", request, Proposal, key="stable"
    )
    empty = MockProvider()
    empty.responses = []
    second = Router(Store(tmp_path), {"hypothesize": [empty]})
    assert (
        second.generate_structured(run, "hypothesize", request, Proposal, key="stable")[1] == result
    )
    assert proposal.prediction == "falsifiable"
    assert Budget(store).totals(run)["requests"] == 1


def test_fallback_recorded_and_not_assumed_equivalent(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("fallback", Limits(allow_live_inference=True).model_dump(mode="json"))
    bad = MetaProvider(
        config(),
        api_key=SecretStr("secret"),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, text="Bearer secret-do-not-save")
        ),
    )
    mock = MockProvider([{"prediction": "fallback fixture only"}])
    with pytest.raises(ValueError, match="Fallback requires"):
        Router(store, {"hypothesize": [bad, mock]})
    router = Router(
        store,
        {"hypothesize": [bad, mock]},
        fallback_evidence={"hypothesize": "explicit test fixture comparison; not live equivalence"},
    )
    result = router.generate(
        run, "hypothesize", GenerationRequest(prompt="propose"), key="fallback"
    )
    assert result.provider == "mock"
    assert Budget(store).totals(run)["uncertain"] == 1
    with store.connection() as db:
        events = [dict(r) for r in db.execute("SELECT * FROM events")]
        assert any('"fallback":true' in r["payload_json"] for r in events)
        assert "secret-do-not-save" not in json.dumps(events)


def test_rate_retry_bound_timeout_no_replay_and_persistent_circuit(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("errors", Limits(allow_live_inference=True).model_dump(mode="json"))
    calls, delays = [], []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "0.01"})

    provider = MetaProvider(
        config(), transport=httpx.MockTransport(handler), api_key=SecretStr("key")
    )
    router = Router(store, {"research": [provider]}, sleeper=delays.append)
    with pytest.raises(ProviderError, match="HTTP_429"):
        router.generate(run, "research", GenerationRequest(prompt="test"), key="rate")
    assert len(calls) == 3 and len(delays) == 2
    with pytest.raises(ProviderError, match="NO_AVAILABLE_PROVIDER"):
        router.generate(run, "research", GenerationRequest(prompt="test"), key="circuit")
    assert len(calls) == 3

    def timeout(request):
        raise httpx.ReadTimeout("Bearer transport-secret")

    other = BasetenProvider(
        config("baseten"), transport=httpx.MockTransport(timeout), api_key=SecretStr("key")
    )
    r2 = Router(store, {"research": [other]})
    with pytest.raises(ProviderError, match="PROVIDER_TIMEOUT"):
        r2.generate(run, "research", GenerationRequest(prompt="test"), key="ambiguous")
    with pytest.raises(BudgetError, match="reconciliation"):
        r2.generate(run, "research", GenerationRequest(prompt="test"), key="ambiguous")


@pytest.mark.parametrize(
    "change",
    [
        {"usage": None},
        {"usage": {"prompt_tokens": -1, "completion_tokens": 2}},
        {"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]},
        {"choices": []},
    ],
)
def test_invalid_responses_never_accepted(change):
    provider = MetaProvider(
        config(),
        transport=httpx.MockTransport(lambda r: response(**change)),
        api_key=SecretStr("key"),
    )
    with pytest.raises(ProviderError):
        provider.generate(GenerationRequest(prompt="test"))


def test_invalid_structured_response_still_accounted(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("bad JSON", {})
    router = Router(store, {"research": [MockProvider(["not json"])]})
    with pytest.raises(ProviderError, match="INVALID_STRUCTURED"):
        router.generate_structured(
            run, "research", GenerationRequest(prompt="test"), Proposal, key="bad"
        )
    assert Budget(store).totals(run)["requests"] == 1


def test_absolute_provider_deadline_retains_unknown_cost_and_never_replays(tmp_path):
    import threading
    import time

    store = Store(tmp_path)
    run = store.create_run(
        "absolute timeout", Limits(allow_live_inference=True).model_dump(mode="json")
    )
    calls = []

    def stalled(request):
        calls.append(1)
        time.sleep(0.2)  # Local transport fixture, no real network or provider billing.
        return response()

    c = config().model_copy(update={"timeout_seconds": 0.02})
    provider = MetaProvider(c, transport=httpx.MockTransport(stalled), api_key=SecretStr("fixture"))
    router = Router(store, {"research": [provider]})
    started = time.monotonic()
    with pytest.raises(ProviderError, match="PROVIDER_TIMEOUT"):
        router.generate(
            run, "research", GenerationRequest(prompt="bounded caller deadline"), key="deadline"
        )
    assert time.monotonic() - started < 0.15
    assert Budget(store).totals(run)["uncertain"] == 1
    with pytest.raises(BudgetError, match="reconciliation"):
        router.generate(
            run, "research", GenerationRequest(prompt="bounded caller deadline"), key="deadline"
        )
    assert len(calls) == 1
    deadline = time.monotonic() + 1
    while (
        any(t.name == "adl-provider-request" for t in threading.enumerate())
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    assert not any(t.name == "adl-provider-request" for t in threading.enumerate())


def test_concurrent_provider_usage_is_not_lost():
    from concurrent.futures import ThreadPoolExecutor

    provider = MetaProvider(
        config(), transport=httpx.MockTransport(lambda r: response()), api_key=SecretStr("fixture")
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        generated = list(
            pool.map(lambda i: provider.generate(GenerationRequest(prompt=f"case {i}")), range(8))
        )
    assert len(generated) == 8
    assert provider.get_usage().input_tokens == 800
    assert provider.get_usage().output_tokens == 240


def test_cancelled_provider_call_retains_reservation_and_does_not_fallback(tmp_path):
    import threading
    import time

    from autodiscover.security.cancellation import cancellation_scope

    store = Store(tmp_path)
    run = store.create_run(
        "cooperative cancellation", Limits(allow_live_inference=True).model_dump(mode="json")
    )
    stopped = threading.Event()

    def stalled(request):
        stopped.set()
        time.sleep(0.15)
        return response()

    provider = MetaProvider(
        config(), transport=httpx.MockTransport(stalled), api_key=SecretStr("fixture")
    )
    fallback = MockProvider()
    router = Router(
        store,
        {"research": [provider, fallback]},
        fallback_evidence={"research": "explicit comparison fixture, no model equivalence claim"},
    )
    with cancellation_scope(stopped.is_set):
        with pytest.raises(ProviderError, match="PROVIDER_CANCEL_REQUESTED"):
            router.generate(
                run, "research", GenerationRequest(prompt="cancel active inference"), key="cancel"
            )
    assert Budget(store).totals(run)["uncertain"] == 1
    assert len(fallback.responses) == 1
    deadline = time.monotonic() + 1
    while (
        any(t.name == "adl-provider-request" for t in threading.enumerate())
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)


def test_rate_backoff_cancels_without_another_call_or_reservation(tmp_path):
    import threading

    from autodiscover.security.cancellation import cancellation_scope

    store = Store(tmp_path)
    run = store.create_run(
        "stop during backoff", Limits(allow_live_inference=True).model_dump(mode="json")
    )
    calls = []
    stopped = threading.Event()

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "30"})

    def stop_on_wait(seconds):
        assert seconds <= 0.05
        stopped.set()

    provider = MetaProvider(
        config(), transport=httpx.MockTransport(handler), api_key=SecretStr("key")
    )
    router = Router(store, {"research": [provider]}, sleeper=stop_on_wait)
    with cancellation_scope(stopped.is_set), pytest.raises(ProviderError, match="CANCEL_REQUESTED"):
        router.generate(run, "research", GenerationRequest(prompt="bounded backoff"), key="backoff")
    assert len(calls) == 1
    assert Budget(store).totals(run)["requests"] == 1
    assert Budget(store).totals(run)["uncertain"] == 1


@pytest.mark.parametrize("schema_type", [ResearchProposal, CriticalReview])
def test_research_role_wire_schema_requires_all_fields_in_strict_mode(schema_type):
    original = schema_type.model_json_schema()
    assert set(original["required"]) < set(original["properties"])
    seen = []

    def handler(request):
        wire = json.loads(request.content)["response_format"]["json_schema"]
        seen.append(wire)
        assert wire["strict"] is True
        assert set(wire["schema"]["required"]) == set(original["properties"])
        assert {k: v for k, v in wire["schema"].items() if k != "required"} == {
            k: v for k, v in original.items() if k != "required"
        }
        return response(text="{}")

    provider = MetaProvider(
        config(), transport=httpx.MockTransport(handler), api_key=SecretStr("contract-secret")
    )
    request = GenerationRequest(prompt="research role", json_schema=original)
    provider.generate(request)
    assert request.json_schema == original
    assert len(seen) == 1
