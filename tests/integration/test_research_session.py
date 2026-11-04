"""Session safety and accelerated research across actual Discovery-v2 checkpoints."""

import threading
from pathlib import Path

import pytest

from autodiscover.evidence.chain import verify_chain
from autodiscover.models.contracts import GenerationRequest, ProviderError
from autodiscover.orchestrator.store import SnapshotStore, StateError, Store
from autodiscover.research.discovery import ROLES
from autodiscover.research.session import Session, create_session, session_report
from autodiscover.research.session_cli import _configs, session_preflight
from autodiscover.research.session_contracts import SessionProfile
from autodiscover.research.session_rehearsal import Archive, RehearsalProvider, rehearsal

CONFIG = Path(__file__).parents[2] / "config"
PROVIDERS = CONFIG / "discovery-meta.json"


def profile(**updates) -> SessionProfile:
    base = SessionProfile.model_validate_json((CONFIG / "session-four-hour.json").read_text())
    return SessionProfile.model_validate({**base.model_dump(), **updates})


def make(store, spec, *, factory=None, monotonic=None):
    plan = session_preflight(spec, _configs(PROVIDERS))["branch"]
    identifier = create_session(store, spec, plan, live=False)
    factory = factory or (lambda i: rehearsal(store, i))
    controller = (
        Session(store, factory, monotonic=monotonic) if monotonic else Session(store, factory)
    )
    return controller, identifier


def test_accelerated_four_hours_and_reports(tmp_path):
    store = Store(tmp_path)
    time = [0.0]
    logs = []
    barriers = [threading.Barrier(2) for _ in range(2)]

    class AdvanceClock(Archive):
        pass

    class TimedProvider(RehearsalProvider):
        def generate(self, request: GenerationRequest):
            import json

            prompt = json.loads(request.prompt)
            if prompt["task"] == "plan":
                logs.append(prompt["session_context"])
                if self.branch < 4:
                    barriers[self.branch // 2].wait(timeout=6)
                time[0] += 3500
            return super().generate(request)

    def factory(branch):
        lab = rehearsal(store, branch)
        lab.fetcher = AdvanceClock()
        lab.router.routes[ROLES[0]] = [TimedProvider(ROLES[0], branch)]
        return lab

    controller, identifier = make(
        store,
        profile(concurrency=2),
        factory=factory,
        monotonic=lambda: time[0],
    )
    controller.execute(identifier)
    result = session_report(store, identifier)
    assert time[0] >= 14400
    assert result["stop_reason"] == "SESSION_DEADLINE"
    assert result["branches_closed"] >= 4
    assert result["critiques_completed"] >= 1
    assert result["duplicate_queries"] >= 1
    assert result["duplicate_hypotheses"] >= 1
    assert result["usage"]["charged_usd"] == "0"
    assert result["usage"]["uncertain"] == 0
    assert len({item["investigation"] for item in logs}) >= 4
    assert any(item["recent_evidence"] for item in logs)
    assert result["dossiers"] and result["next_research"]
    with SnapshotStore(tmp_path) as snapshot:
        assert session_report(snapshot, identifier)["evidence_anchor"] == verify_chain(store)


def test_failure_isolated_and_stagnation_stops(tmp_path):
    store = Store(tmp_path)

    class BadResponse(RehearsalProvider):
        def answer(self, prompt):
            return {"invalid": True}

    def factory(branch):
        lab = rehearsal(store, branch)
        if branch == 0:
            lab.router.routes[ROLES[0]] = [BadResponse(ROLES[0], branch)]
        return lab

    controller, identifier = make(
        store,
        profile(max_stagnant_branches=2),
        factory=factory,
    )
    controller.execute(identifier)
    result = session_report(store, identifier)
    assert result["branches"][0]["error"] == "INVALID_STRUCTURED_RESPONSE"
    assert result["branches"][1]["packet_digest"]
    assert result["stop_reason"] == "RESEARCH_STAGNATION"
    assert result["duplicate_hypotheses"] >= 1
    assert result["critiques_completed"] == 1
    assert result["falsifiable_candidates_requiring_external_review"] == 1
    assert result["usage"]["uncertain"] == 0


def test_ambiguous_timeout_prevents_resume_and_later_branch(tmp_path):
    store = Store(tmp_path)

    class Timeout(RehearsalProvider):
        def generate(self, request):
            raise ProviderError("PROVIDER_TIMEOUT", uncertain=True)

    def factory(branch):
        lab = rehearsal(store, branch)
        lab.router.routes[ROLES[0]] = [Timeout(ROLES[0], branch)]
        return lab

    controller, identifier = make(store, profile(), factory=factory)
    controller.execute(identifier)
    result = session_report(store, identifier)
    assert result["stop_reason"] == "REQUEST_RECONCILIATION_REQUIRED"
    assert result["status"] == "PAUSED"
    assert result["branches_admitted"] == 1
    assert result["unresolved_reservations"][0]["status"] == "UNCERTAIN"
    with pytest.raises(StateError, match="reconciliation"):
        controller.execute(identifier, resume=True)
    assert session_report(store, identifier)["usage"]["requests"] == 1


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"max_model_calls": 10}, "MODEL_CALL_LIMIT"),
        ({"max_total_tokens": 265600}, "TOKEN_LIMIT"),
        ({"aggregate_cost_ceiling_usd": "0.73"}, "AGGREGATE_COST_LIMIT"),
        ({"max_branches": 1}, "BRANCH_LIMIT"),
    ],
)
def test_admission_hard_bounds(tmp_path, updates, reason):
    store = Store(tmp_path)
    controller, identifier = make(store, profile(**updates))
    controller.execute(identifier)
    result = session_report(store, identifier)
    assert result["branches_admitted"] == 1
    assert result["stop_reason"] == reason
    assert result["usage"]["requests"] == 4


def test_consecutive_errors_stop_without_dispatching_more(tmp_path):
    store = Store(tmp_path)

    class KnownFailure(RehearsalProvider):
        def generate(self, request):
            raise ProviderError("PROVIDER_RATE_LIMIT", retryable=True, known_zero_cost=True)

    def factory(branch):
        lab = rehearsal(store, branch)
        lab.router.routes[ROLES[0]] = [KnownFailure(ROLES[0], branch)]
        return lab

    controller, identifier = make(store, profile(), factory=factory)
    controller.execute(identifier)
    result = session_report(store, identifier)
    assert result["stop_reason"] == "CONSECUTIVE_PROVIDER_ERRORS"
    assert result["branches_admitted"] == result["usage"]["requests"] == 2
    assert result["usage"]["uncertain"] == 0


def test_transient_provider_retry_and_source_failure(tmp_path):
    from autodiscover.research.retrieval import RetrievalError

    store = Store(tmp_path)

    class RetryOnce(RehearsalProvider):
        failed = False

        def generate(self, request):
            if not self.failed:
                self.failed = True
                raise ProviderError("PROVIDER_RATE_LIMIT", retryable=True, known_zero_cost=True)
            return super().generate(request)

    class RetrievalUnavailable(Archive):
        def fetch(self, url):
            raise RetrievalError("SIMULATED_SOURCE_UNAVAILABLE")

    def factory(branch):
        lab = rehearsal(store, branch)
        lab.router.sleeper = lambda _seconds: None
        if branch == 0:
            lab.router.routes[ROLES[0]] = [RetryOnce(ROLES[0], branch)]
            lab.fetcher = RetrievalUnavailable()
        return lab

    base = profile()
    controller, identifier = make(
        store,
        profile(
            discovery=base.discovery.model_copy(update={"retry_limit": 1}),
            max_branches=2,
        ),
        factory=factory,
    )
    controller.execute(identifier)
    result = session_report(store, identifier)
    assert result["source_failures"] >= 1
    assert result["branches_closed"] == 2
    assert result["branches"][0]["proposed"] == 0
    assert result["branches"][1]["proposed"] == 1
    assert result["usage"]["requests"] == 6
    assert result["usage"]["uncertain"] == 0


def test_qualification_live_path_with_mock_transport(tmp_path, monkeypatch, capsys):
    import json
    import sys
    from dataclasses import replace
    from decimal import Decimal

    import httpx
    from pydantic import SecretStr

    from autodiscover.cli import main
    from autodiscover.models.providers import MetaProvider
    from autodiscover.research import session_cli

    seen = []

    def handler(request):
        assert str(request.url) == "https://api.meta.ai/v1/chat/completions"
        body = json.loads(request.content)
        prompt = json.loads(body["messages"][-1]["content"])
        seen.append((body["model"], prompt["task"]))
        assert body["response_format"]["json_schema"]["strict"]
        context = prompt.get("session_context", {})
        payload = RehearsalProvider(body["model"], context.get("branch", 0)).answer(prompt)
        return httpx.Response(
            200,
            json={
                "model": body["model"],
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(payload)}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 80,
                    "completion_tokens_details": {"reasoning_tokens": 15},
                },
            },
        )

    def clients(configs):
        return {
            role: MetaProvider(
                config.model_copy(update={"live_authorized": True}),
                transport=httpx.MockTransport(handler),
                api_key=SecretStr("mock-session-only"),
            )
            for role, config in configs.items()
        }

    class PublicArchive(Archive):
        def __init__(self, **kwargs):
            assert kwargs["authorized"]

        def fetch(self, url):
            return replace(super().fetch(url), provenance="live_https")

    monkeypatch.setattr(session_cli, "_clients", clients)
    monkeypatch.setattr(session_cli, "Fetcher", PublicArchive)
    command = [
        "autodiscover",
        "--root",
        str(tmp_path),
        "session",
    ]
    flags = ["--providers", str(PROVIDERS), "--authorize-live", "--allow-network"]
    monkeypatch.setattr(
        sys,
        "argv",
        command
        + [
            "start",
            "--profile",
            str(CONFIG / "session-qualification.json"),
            *flags,
        ],
    )
    main()
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "PAUSED" and first["stop_reason"] == "QUALIFICATION_CHECKPOINT"
    monkeypatch.setattr(sys, "argv", command + ["resume", first["session_id"], *flags])
    main()
    done = json.loads(capsys.readouterr().out)
    assert done["status"] == "COMPLETED" and done["usage"]["requests"] == len(seen) == 7
    assert done["usage"]["reasoning_tokens_reported"] == 105
    assert Decimal(done["usage"]["settled_usd"]) == Decimal("0.00479")
    assert done["falsifiable_candidates_requiring_external_review"] == 1
    assert done["commercial_level"] == 0
