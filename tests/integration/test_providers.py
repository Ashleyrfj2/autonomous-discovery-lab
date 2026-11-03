import json
from decimal import Decimal

import httpx
import pytest
from pydantic import BaseModel, SecretStr, ValidationError

from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts
from autodiscover.evidence.chain import verify_chain
from autodiscover.hypotheses.proposals import ResearchProposal
from autodiscover.models.contracts import (
    BASETEN_HACKATHON_KEY_ENV,
    BASETEN_HACKATHON_MODEL,
    GenerationRequest,
    ProviderConfig,
    ProviderError,
)
from autodiscover.models.providers import BasetenProvider, MetaProvider, MockProvider
from autodiscover.models.router import Router
from autodiscover.models.teams import (
    CriticalReview,
    ResearchReviewPacket,
    ResearchTeam,
    RoleSeparationError,
)
from autodiscover.orchestrator.store import Store
from autodiscover.research.catalog import Catalog
from autodiscover.research.retrieval import Fetched
from autodiscover.security.budget import Budget, BudgetError


class Proposal(BaseModel):
    prediction: str


def config(kind="meta", **overrides):
    defaults = {
        "name": kind,
        "kind": kind,
        "model": "configured-test-model",
        "api_key_env": "TEST_PROVIDER_KEY",
        "input_usd_per_million": "1",
        "output_usd_per_million": "2",
        "context_window": 8192,
        "output_limit": 1024,
        "structured_output": True,
        "capability_source": "contract fixture; not live capability evidence",
        "pricing_source": "test rates, not real prices",
        "verified_on": "2026-11-03",
        "live_authorized": True,
    }
    return ProviderConfig.model_validate(defaults | overrides)


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
        {"model": None},
        {"usage": {"prompt_tokens": -1, "completion_tokens": 2}},
        {"usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 1}},
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


def hackathon_config(**overrides):
    settings = {
        "profile": "baseten_hackathon",
        "model": BASETEN_HACKATHON_MODEL,
        "api_key_env": BASETEN_HACKATHON_KEY_ENV,
        "structured_output": False,
    }
    return config("baseten", **(settings | overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"model": "meta-models/muse-spark-open"},
        {"model": "deepseek-ai/DeepSeek-V4.1-Flash-1017"},
        {"reasoning_effort": "low"},
        {"structured_output": True},
        {"api_key_env": "BASETEN_API_KEY"},
        {"profile": "standard"},
    ],
)
def test_hackathon_profile_rejects_unverified_config_at_validation_and_adapter(overrides):
    with pytest.raises(ValidationError):
        hackathon_config(**overrides)
    with pytest.raises(ValidationError):
        BasetenProvider(hackathon_config().model_copy(update=overrides))


def test_hackathon_uses_only_the_email_model_and_inference_path(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url)
        assert request.method == "POST"
        assert str(request.url) == "https://inference.baseten.co/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer fake-hackathon-fixture"
        wire = json.loads(request.content)
        assert wire["model"] == BASETEN_HACKATHON_MODEL
        assert wire["stream"] is False
        assert wire["max_tokens"] == 512
        assert "reasoning_effort" not in wire and "response_format" not in wire
        assert '"required":["prediction"]' in wire["messages"][0]["content"]
        return response(model=BASETEN_HACKATHON_MODEL)

    monkeypatch.setenv(BASETEN_HACKATHON_KEY_ENV, "fake-hackathon-fixture")
    provider = BasetenProvider(hackathon_config(), transport=httpx.MockTransport(handler))
    typed, generated = provider.generate_structured(GenerationRequest(prompt="test"), Proposal)
    assert typed.prediction == "measurable"
    assert generated.model == BASETEN_HACKATHON_MODEL
    with pytest.raises(ProviderError, match="HACKATHON_INFERENCE_ENDPOINT_ONLY"):
        provider.health_check()
    assert len(calls) == 1



def test_hackathon_does_not_send_its_key_in_prompt(monkeypatch):
    calls = []
    monkeypatch.setenv(BASETEN_HACKATHON_KEY_ENV, "fake-hackathon-fixture")
    provider = BasetenProvider(
        hackathon_config(),
        transport=httpx.MockTransport(lambda request: calls.append(request) or response()),
    )
    with pytest.raises(ProviderError, match="CREDENTIAL_IN_PROMPT") as error:
        provider.generate(GenerationRequest(prompt="Review fake-hackathon-fixture."))
    assert error.value.known_zero_cost and not calls

@pytest.mark.parametrize(
    "kind,cls,model,effort,cap",
    [
        ("meta", MetaProvider, "muse-spark-1.3", "minimal", "max_completion_tokens"),
        ("baseten", BasetenProvider, "meta-models/muse-spark-open", "low", "max_tokens"),
    ],
)
def test_documented_reasoning_controls(kind, cls, model, effort, cap):
    def handler(request):
        wire = json.loads(request.content)
        assert wire["reasoning_effort"] == effort and wire[cap] == 512
        return response(
            model=model, usage={
                "prompt_tokens": 100, "completion_tokens": 30,
                "completion_tokens_details": {"reasoning_tokens": 19},
            }
        )

    provider = cls(
        config(kind, model=model, reasoning_effort=effort),
        transport=httpx.MockTransport(handler),
        api_key=SecretStr("fixture-reasoning"),
    )
    result = provider.generate(GenerationRequest(prompt="test"))
    assert result.usage.reasoning_tokens == 19
    assert result.cost_usd == Decimal("0.00016")
    with pytest.raises(ValidationError, match="Reasoning effort"):
        config(kind, reasoning_effort=effort)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
def test_http_failures_preserve_unconfirmed_charge_without_leaking_body(tmp_path, status):
    store = Store(tmp_path)
    run = store.create_run(
        "provider rejection",
        Limits(allow_live_inference=True, max_retries_per_step=0).model_dump(mode="json"),
    )
    provider = BasetenProvider(
        hackathon_config(),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(status, text="Bearer private-provider-error-fixture")
        ),
        api_key=SecretStr("fixture-key"),
    )
    router = Router(store, {"test": [provider]})
    with pytest.raises(ProviderError, match=f"^HTTP_{status}$") as error:
        router.generate(run, "test", GenerationRequest(prompt="test"), key="http")
    assert error.value.retryable == (status == 429 or status >= 500)
    assert not error.value.known_zero_cost
    assert router.budget.totals(run)["uncertain_usd"] == "0.009216"
    with store.connection() as db:
        payload = db.execute(
            "SELECT payload_json FROM events WHERE kind='provider_failed'"
        ).fetchone()[0]
    assert json.loads(payload)["uncertain"] is True
    assert "private-provider-error-fixture" not in payload


@pytest.mark.parametrize(
    "finish,message,tokens,reasoning,code",
    [
        ("stop", {"content": None, "reasoning_content": "internal"}, 30, 30, "REASONING_ONLY"),
        ("stop", {}, 30, 30, "REASONING_ONLY"),
        (
            "length", {"content": '{"prediction":"complete-looking"}'},
            512, 510, "OUTPUT_TOKEN_LIMIT",
        ),
        ("stop", {"content": ""}, 512, None, "OUTPUT_TOKEN_LIMIT"),
        ("stop", {"content": " \n "}, 30, None, "EMPTY_FINAL_CONTENT"),
        ("stop", {"content": "bad JSON"}, 30, None, "INVALID_STRUCTURED_RESPONSE"),
        ("stop", {"content": '{"prediction":'}, 30, None, "INVALID_STRUCTURED_RESPONSE"),
        ("stop", {"content": '{}'}, 30, None, "INVALID_STRUCTURED_RESPONSE"),
        ("stop", {"content": '{"prediction":7}'}, 30, None, "INVALID_STRUCTURED_RESPONSE"),
        (
            "stop", {"content": '{"prediction":"first","prediction":"second"}'},
            30, None, "INVALID_STRUCTURED_RESPONSE",
        ),
        ("stop", {"content": '{"prediction":"leaked-exact-fixture-key"}'}, 30, None,
         "CREDENTIAL_IN_RESPONSE"),
    ],
)
def test_failed_completion_accounts_reported_usage_without_caching(
    tmp_path, finish, message, tokens, reasoning, code
):
    calls = []

    def handler(request):
        calls.append(request)
        return response(
            choices=[{"finish_reason": finish, "message": message}],
            usage={
                "prompt_tokens": 100, "completion_tokens": tokens,
                "completion_tokens_details": {"reasoning_tokens": reasoning},
            },
        )

    store = Store(tmp_path)
    run = store.create_run("response handling", Limits(allow_live_inference=True).model_dump())
    provider = MetaProvider(
        config(), transport=httpx.MockTransport(handler),
        api_key=SecretStr("leaked-exact-fixture-key"),
    )
    router = Router(store, {"test": [provider]})
    request = GenerationRequest(prompt="test")
    with pytest.raises(ProviderError, match=f"^{code}$"):
        router.generate_structured(run, "test", request, Proposal, key="bad")
    with pytest.raises(BudgetError, match="reconciliation"):
        router.generate_structured(run, "test", request, Proposal, key="bad")
    assert len(calls) == 1
    totals = router.budget.totals(run)
    assert Decimal(totals["settled_usd"]) == Decimal(100 + tokens * 2) / 1_000_000
    assert totals["output_tokens"] == tokens and totals["uncertain"] == 0
    with store.connection() as db:
        row = db.execute("SELECT usage_json, result_json FROM reservations").fetchone()
    assert json.loads(row["usage_json"]).get("reasoning_tokens") == reasoning
    assert row["result_json"] is None


def test_changed_reasoning_setting_conflicts_with_existing_cache(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("reasoning cache", Limits(allow_live_inference=True).model_dump())
    calls = []

    def handler(request):
        calls.append(request)
        return response(model="muse-spark-1.3")

    request = GenerationRequest(prompt="test")
    for effort in ("minimal", "low"):
        provider = MetaProvider(
            config(model="muse-spark-1.3", reasoning_effort=effort),
            transport=httpx.MockTransport(handler), api_key=SecretStr("fixture"),
        )
        router = Router(store, {"test": [provider]})
        if effort == "minimal":
            router.generate_structured(run, "test", request, Proposal, key="stable")
        else:
            with pytest.raises(BudgetError, match="identity conflict"):
                router.generate_structured(run, "test", request, Proposal, key="stable")
    assert len(calls) == 1


def test_role_separation_rejects_two_names_for_same_http_model(tmp_path):
    providers = [
        MetaProvider(config(name=name, model="muse-spark-1.3"))
        for name in ("proposals", "exploratory")
    ]
    with pytest.raises(RoleSeparationError, match="distinct"):
        ResearchTeam(Router(Store(tmp_path), {
            "RESEARCH_PROPOSALS": [providers[0]], "EXPLORATORY": [providers[1]],
            "CRITIQUE": [BasetenProvider(hackathon_config())],
        }))


def test_mock_http_team_source_bound_packet_replays_without_dispatch(tmp_path):
    store = Store(tmp_path)
    cap = Decimal("0.05")
    run = store.create_run("bounded research", Limits(
        allow_live_inference=True, max_retries_per_step=0, max_hypotheses_per_cycle=2,
        max_cost_per_run_usd=cap, max_cost_per_day_usd=cap,
    ).model_dump())
    catalog = Catalog(store)
    url = "https://example.org/allocation-study"
    source_text = "A fixture study compares allocation methods on held-out tasks."
    source = catalog.add(
        run, Fetched(url, url, source_text.encode(), "text/plain", "2026-11-03", "live_https"),
        title="Allocation study fixture", text=source_text, source_kind="primary_document",
    )
    candidate = ResearchProposal(
        question="Can a fixed optimization baseline improve allocations?",
        domain="logistics", connection_domain="optimization",
        prediction="Reduce unassigned items by two.", metric="unassigned", unit="items",
        comparator="Greedy baseline", direction="decrease", minimum_effect=2,
        measurement_protocol="Compare methods on an identical held-out workload.",
        source_ids=[source],
    )
    criticism = CriticalReview(
        assumptions_at_risk=["Workload representativeness."],
        methodological_flaws=["Single fixed comparator."],
        alternative_explanations=["Task difficulty may differ."],
        disconfirming_experiment="Repeat on matched unseen task distributions.",
        source_ids=[source],
    )
    calls = []

    def handler(request):
        wire = json.loads(request.content)
        model = wire["model"]
        calls.append(model)
        prompt = wire["messages"][1]["content"]
        assert source in prompt and source_text in prompt
        typed = criticism if model == BASETEN_HACKATHON_MODEL else candidate
        value = typed.model_dump(mode="json")
        if model == BASETEN_HACKATHON_MODEL:
            value["methodological_flaws"] = ["Bearer fake-recognizable-secret"]
        return response(text=json.dumps(value), model=model)

    transport = httpx.MockTransport(handler)
    key = SecretStr("fixture-key")
    routes = {
        "RESEARCH_PROPOSALS": [MetaProvider(config(
            model="muse-spark-1.3", reasoning_effort="minimal",
        ), transport=transport, api_key=key)],
        "EXPLORATORY": [MetaProvider(config(
            model="muse-spark-1.2", reasoning_effort="minimal",
        ), transport=transport, api_key=key)],
        "CRITIQUE": [BasetenProvider(hackathon_config(), transport=transport, api_key=key)],
    }
    router = Router(store, routes)
    args = {"topic": "allocation comparison", "domains": ["logistics"], "key": "stable"}
    result = ResearchTeam(router).investigate(run, **args)
    digest = result["artifact_digest"]
    assert isinstance(digest, str)
    packet = ResearchReviewPacket.model_validate(Artifacts(tmp_path / "artifacts").get_json(digest))
    assert packet.source_ids == [source]
    assert [review.proposal.source_ids for review in packet.candidate_reviews] == [[source]] * 2
    assert [review.critique.source_ids for review in packet.candidate_reviews] == [[source]] * 2
    assert all(r.critique.methodological_flaws == ["[REDACTED]"] for r in packet.candidate_reviews)
    before = verify_chain(store)
    assert router.budget.totals(run)["settled_usd"] == "0.00064"
    assert router.budget.totals(run)["requests"] == 4
    assert router.budget.totals(run)["uncertain"] == 0

    replay = ResearchTeam(Router(Store(tmp_path), routes, cache_only=True))
    assert replay.investigate(run, **args) == result
    with pytest.raises(ProviderError, match="CACHE_MISS"):
        replay.investigate(run, topic="allocation comparison", domains=["logistics"], key="unseen")
    assert verify_chain(store) == before
    with store.connection() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM events WHERE kind='research_team_reviewed'"
        ).fetchone()[0] == 1
    assert calls == ["muse-spark-1.3", BASETEN_HACKATHON_MODEL,
                     "muse-spark-1.2", BASETEN_HACKATHON_MODEL]
    catalog.invalidate(run, source, reason="Fixture source withdrawn")
    with pytest.raises(ValueError, match="Source invalid"):
        replay.investigate(run, **args)
    assert len(calls) == 4


@pytest.mark.parametrize("ambiguous", ["timeout", "server-error"])
def test_ambiguous_inference_does_not_dispatch_to_another_live_provider(tmp_path, ambiguous):
    store = Store(tmp_path)
    run = store.create_run("fallback boundary", Limits(allow_live_inference=True).model_dump())
    calls = []

    def uncertain(request):
        calls.append(request.url.host)
        if ambiguous == "timeout":
            raise httpx.ReadTimeout("fixture")
        return httpx.Response(503)

    def alternate(request):
        calls.append(request.url.host)
        return response()

    primary = MetaProvider(
        config(), transport=httpx.MockTransport(uncertain), api_key=SecretStr("fixture-primary")
    )
    backup = BasetenProvider(
        config("baseten"), transport=httpx.MockTransport(alternate),
        api_key=SecretStr("fixture-alternate"),
    )
    router = Router(
        store, {"research": [primary, backup]},
        fallback_evidence={"research": "mock route evaluation"},
    )
    with pytest.raises(ProviderError, match="PROVIDER_TIMEOUT|HTTP_503"):
        router.generate(run, "research", GenerationRequest(prompt="test"), key="stable")
    assert calls == ["api.meta.ai"]
    assert router.budget.totals(run)["uncertain"] == 1


def test_unexpected_response_model_retains_full_reservation(tmp_path):
    store = Store(tmp_path)
    run = store.create_run(
        "unexpected priced model", Limits(allow_live_inference=True).model_dump()
    )
    provider = MetaProvider(
        config(), transport=httpx.MockTransport(lambda r: response(model="unexpected-model")),
        api_key=SecretStr("fixture-key"),
    )
    router = Router(store, {"research": [provider]})
    with pytest.raises(ProviderError, match="PROVIDER_IDENTITY_MISMATCH"):
        router.generate(run, "research", GenerationRequest(prompt="test"), key="wrong-model")
    totals = router.budget.totals(run)
    assert totals["settled_usd"] == "0"
    assert totals["uncertain_usd"] == "0.009216"
    assert totals["output_tokens"] == 30


def test_invalid_retry_after_uses_finite_exponential_backoff(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("malformed backoff", Limits(allow_live_inference=True).model_dump())
    delays = []
    provider = MetaProvider(
        config(), transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": "NaN"})
        ), api_key=SecretStr("fixture-key"),
    )
    router = Router(store, {"research": [provider]}, sleeper=delays.append)
    with pytest.raises(ProviderError, match="HTTP_429"):
        router.generate(run, "research", GenerationRequest(prompt="test"), key="backoff")
    assert delays == [0.25, 0.5]


def test_escaped_credential_from_dispatched_key_is_never_cached(tmp_path, monkeypatch):
    original = "fixture-credential-original"
    monkeypatch.setenv("TEST_PROVIDER_KEY", original)

    def handler(request):
        assert request.headers["authorization"] == "Bearer " + original
        monkeypatch.setenv("TEST_PROVIDER_KEY", "fixture-credential-replacement")
        encoded = "".join(fr"\u{ord(character):04x}" for character in original)
        return response(text='{"prediction":"' + encoded + '"}')

    store = Store(tmp_path)
    run = store.create_run("escaped credential", Limits(allow_live_inference=True).model_dump())
    provider = MetaProvider(config(), transport=httpx.MockTransport(handler))
    router = Router(store, {"research": [provider]})
    with pytest.raises(ProviderError, match="CREDENTIAL_IN_RESPONSE"):
        router.generate_structured(
            run, "research", GenerationRequest(prompt="test"), Proposal, key="escaped"
        )
    with store.connection() as db:
        assert db.execute("SELECT result_json FROM reservations").fetchone()[0] is None
