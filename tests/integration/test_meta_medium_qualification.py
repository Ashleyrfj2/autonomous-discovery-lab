"""New profile through the real HTTP adapter; every external response is mocked."""

import json
import os
import threading
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel, ConfigDict
from test_capability_discovery import CONFIG

from autodiscover.evidence.chain import verify_chain
from autodiscover.models import providers as provider_module
from autodiscover.models.contracts import GenerationRequest, ProviderError
from autodiscover.models.providers import MetaProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.store import SnapshotStore, Store
from autodiscover.research.capability_rehearsal import (
    CapabilityArchive,
    CapabilityProvider,
    rehearsal,
)
from autodiscover.research.discovery import ROLES, replay
from autodiscover.research.discovery_cli import preflight
from autodiscover.research.discovery_contracts import DiscoverySpec
from autodiscover.research.opportunity import stage_envelope, stage_for
from autodiscover.research.session import Session, create_session, session_report
from autodiscover.research.session_cli import _configs, session_preflight
from autodiscover.research.session_contracts import SessionProfile
from autodiscover.security.budget import BudgetError
from autodiscover.security.cancellation import cancellation_scope

MANIFEST = CONFIG / "discovery-capability-meta-medium-v2.json"
PROFILE = CONFIG / "session-capability-qualification-medium-v2.json"


def profile():
    return SessionProfile.model_validate_json(PROFILE.read_text())


def test_new_profile_bounds_and_conservative_inclusive_usage():
    selected = profile()
    configs = _configs(MANIFEST)
    spec = selected.discovery
    assert spec == DiscoverySpec.model_validate_json(
        (CONFIG / "discovery-capability-medium-v2.json").read_text()
    )
    assert spec.capability is not None
    expected = {
        "planning": ("low", 4096, 90),
        "extraction": ("low", 4096, 45),
        "gap": ("medium", 4096, 60),
        "proposal": ("medium", 8192, 90),
        "critique": ("medium", 8192, 90),
    }
    for stage, settings in spec.capability.stages.items():
        assert (
            settings.reasoning_effort,
            settings.max_output_tokens,
            settings.timeout_seconds,
        ) == (expected[stage])
    assert spec.capability.tracks == ["ai_native", "open_science"]
    assert spec.retry_limit == 0 and selected.concurrency == 1
    assert selected.aggregate_cost_ceiling_usd is None
    estimate = preflight(spec, configs)
    session = session_preflight(selected, configs)
    assert estimate["input_tokens_estimated_upper_bound"] == 624000
    assert estimate["output_tokens_including_reasoning_max"] == 77824
    assert session["max_attempts"] == 26
    assert session["max_estimated_tokens_including_reasoning"] == 1403648
    assert Decimal(session["max_calculated_gross_usd"]) == Decimal("3.787648")
    # All 13 calls, including one recovery: no success/discount assumption.
    model_wait = sum(
        spec.capability.stages[stage].timeout_seconds * n
        for stage, _, n in stage_envelope(spec.capability)
    )
    assert model_wait == 945
    assert model_wait + estimate["bibliographic_fetches_max"] * 8 == 1057 < spec.seconds == 1200
    assert selected.duration_seconds == selected.max_branches * spec.seconds + 600 == 3000
    assert [c.reasoning_effort for c in configs.values()] == ["minimal", "minimal", "low"]
    for role in ROLES:
        assert configs[role].timeout_seconds == 90
    # The historical manifest fails before dispatch with the new stage settings.
    with pytest.raises(ValueError, match="Stage timeout exceeds"):
        preflight(spec, _configs(CONFIG / "discovery-capability-meta.json"))


def test_complete_medium_session_on_slow_structured_http_and_exact_replay(tmp_path, monkeypatch):
    monkeypatch.setenv("META_API_KEY", "fixture-only-placeholder")
    selected = profile()
    configs = _configs(MANIFEST)
    store = Store(tmp_path)
    wire = []
    clock = [0.0]
    # Simulate 31 seconds per successful HTTP response, beyond the failed 30s caller.
    # Only the adapter clock changes; the actual test performs no network or long sleeps.
    monkeypatch.setattr(provider_module, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    class SimulatedHTTPS(CapabilityArchive):
        def fetch(self, url):
            return replace(super().fetch(url), provenance="live_https")

    def factory(branch):
        lab = rehearsal(store, branch)
        lab.fetcher = SimulatedHTTPS()

        def handler(request):
            body = json.loads(request.content)
            prompt = json.loads(body["messages"][1]["content"])
            role = next(r for r, c in configs.items() if c.model == body["model"])
            stage = stage_for(prompt["task"])
            assert selected.discovery.capability
            settings = selected.discovery.capability.stages[stage]
            assert body["reasoning_effort"] == settings.reasoning_effort
            assert body["max_completion_tokens"] == settings.max_output_tokens
            assert body["response_format"]["json_schema"]["strict"] is True
            # The actual httpx transport receives every stage's bound, not the 90s default.
            assert set(request.extensions["timeout"].values()) == {settings.timeout_seconds}
            wire.append((stage, body))
            clock[0] += 31
            return httpx.Response(
                200,
                json={
                    "model": body["model"],
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    CapabilityProvider(role, branch).answer(prompt)
                                )
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 80,
                        "completion_tokens_details": {"reasoning_tokens": 15},
                    },
                },
            )

        for role, config in configs.items():
            lab.router.routes[role] = [
                MetaProvider(
                    config.model_copy(update={"live_authorized": True}),
                    transport=httpx.MockTransport(handler),
                )
            ]
        return lab

    identifier = create_session(
        store, selected, session_preflight(selected, configs)["branch"], live=True
    )
    controller = Session(store, factory)
    controller.execute(identifier)
    checkpoint = session_report(store, identifier)
    assert checkpoint["status"] == "PAUSED"
    assert checkpoint["stop_reason"] == "QUALIFICATION_CHECKPOINT"
    assert checkpoint["critiques_completed"] >= 1
    assert not checkpoint["unresolved_reservations"]
    controller.execute(identifier, resume=True)
    final = session_report(store, identifier)
    assert final["status"] == "COMPLETED" and final["branches_closed"] == 2
    assert final["usage"]["requests"] == len(wire)
    assert final["usage"]["output_tokens"] == len(wire) * 80
    assert final["usage"]["reasoning_tokens_reported"] == len(wire) * 15
    assert {s for s, _ in wire} == {"planning", "extraction", "gap", "proposal", "critique"}
    before = len(wire), verify_chain(store)
    for dossier in final["dossiers"]:
        digest, packet = replay(store, dossier["packet"]["run_id"])
        assert digest == dossier["digest"]
        assert packet.novelty_status == "unverified" and packet.commercial_level == 0
        for candidate in packet.candidates:
            if candidate.opportunity:
                assert candidate.opportunity.validation_status == "unverified_idea"
    assert (len(wire), verify_chain(store)) == before


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str


@pytest.mark.parametrize(
    "failure,code,uncertain",
    [
        ("read-timeout", "PROVIDER_TIMEOUT", True),
        ("transport-interrupted", "PROVIDER_TRANSPORT", True),
        ("caller-timeout", "PROVIDER_TIMEOUT", True),
        ("cancel", "PROVIDER_CANCEL_REQUESTED", True),
        ("bad-structure", "INVALID_STRUCTURED_RESPONSE", False),
        ("wrong-model", "PROVIDER_IDENTITY_MISMATCH", True),
        ("reasoning-only", "REASONING_ONLY", False),
    ],
)
def test_http_faults_keep_durable_accounting_and_never_retry(
    tmp_path, monkeypatch, failure, code, uncertain
):
    monkeypatch.setenv("META_API_KEY", "fixture-only-placeholder")
    config = _configs(MANIFEST)[ROLES[0]].model_copy(update={"live_authorized": True})
    calls = []
    entered, release, done, cancelled = (threading.Event() for _ in range(4))

    def handler(request):
        calls.append(request)
        entered.set()
        if failure == "read-timeout":
            raise httpx.ReadTimeout("fixture read deadline")
        if failure == "transport-interrupted":
            raise httpx.ReadError("fixture interrupted connection")
        if failure in {"caller-timeout", "cancel"}:
            if failure == "cancel":
                cancelled.set()
            assert release.wait(3)
        done.set()
        return httpx.Response(
            200,
            json={
                "model": "wrong-identity" if failure == "wrong-model" else config.model,
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"other":"field"}'
                                if failure == "bad-structure"
                                else ""
                                if failure == "reasoning-only"
                                else '{"answer":"bounded"}'
                            )
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "completion_tokens_details": {
                        "reasoning_tokens": 8 if failure == "reasoning-only" else 3
                    },
                },
            },
        )

    store = Store(tmp_path)
    identifier = store.create_run("Mock HTTP fault accounting", {"allow_live_inference": True})
    router = Router(
        store, {"stage": [MetaProvider(config, transport=httpx.MockTransport(handler))]}
    )
    selected = profile()
    assert selected.discovery.capability
    settings = selected.discovery.capability.stages["planning"]
    request = GenerationRequest(
        prompt="Return a structured bounded fixture", **settings.model_dump()
    )
    if failure == "caller-timeout":
        request = request.model_copy(update={"timeout_seconds": 0.03})
    try:
        with cancellation_scope(cancelled.is_set):
            with pytest.raises(ProviderError, match=code):
                router.generate_structured(identifier, "stage", request, Answer, key="no-retry")
        with pytest.raises(BudgetError, match="reconciliation"):
            router.generate_structured(identifier, "stage", request, Answer, key="no-retry")
        with store.connection() as db:
            row = db.execute("SELECT * FROM reservations").fetchone()
            assert row["status"] == ("UNCERTAIN" if uncertain else "SETTLED")
            assert row["result_json"] is None
            if uncertain:
                assert row["charged_nano"] == row["reserved_nano"] == 77408000
            else:
                assert json.loads(row["usage_json"])["output_tokens"] == 8
                assert row["charged_nano"] == 46500
        assert len(calls) == 1 and entered.is_set()
        verify_chain(store)
    finally:
        release.set()
        if failure in {"caller-timeout", "cancel"}:
            assert done.wait(3)
    # A late HTTP completion cannot settle a reservation or populate the cache.
    with SnapshotStore(tmp_path) as snapshot:
        with snapshot.connection() as db:
            row = db.execute("SELECT status,result_json FROM reservations").fetchone()
            assert row["status"] == ("UNCERTAIN" if uncertain else "SETTLED")
            assert row["result_json"] is None


def test_saved_timeout_baseline_remains_unresolved_in_read_only_copy():
    root = os.environ.get("ADL_TIMEOUT_BASELINE_ROOT")
    if not root:
        pytest.skip("ADL_TIMEOUT_BASELINE_ROOT must point to a COPY of the failed qualification")
    with SnapshotStore(Path(root)) as snapshot:
        before = verify_chain(snapshot)
        report = session_report(snapshot, "session-4c376b05f4e8440aab2d15c30a603ec8")
        assert report["status"] == "PAUSED"
        assert report["stop_reason"] == "REQUEST_RECONCILIATION_REQUIRED"
        assert report["usage"]["requests"] == 1 and report["usage"]["uncertain"] == 1
        assert report["usage"]["uncertain_usd"] == "0.077408"
        assert report["usage"]["input_tokens"] == report["usage"]["output_tokens"] == 0
        assert report["unresolved_reservations"][0]["id"] == (
            "a0bca7a6-91a3-4b90-9e63-91b3b4afaa75"
        )
        assert before["hash"] == "43dc8e65ce8ab1a32f42df08f22a876fdf2c79e82d477a7d29fdf7b3dfc35ee7"
        assert verify_chain(snapshot) == before
