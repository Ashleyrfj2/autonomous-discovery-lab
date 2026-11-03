import json
from decimal import Decimal

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from autodiscover.config import Limits
from autodiscover.models.contracts import GenerationRequest, ProviderConfig, ProviderError
from autodiscover.models.providers import BasetenProvider, MetaProvider, MockProvider
from autodiscover.models.router import Router
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
