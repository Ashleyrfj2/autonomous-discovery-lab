"""Updated objective, ninety-minute virtual duration and real-process recovery/control."""

import json
import subprocess
import sys

import pytest
from test_capability_discovery import CONFIG, specification
from test_research_session_process import CHILD, await_gate, cli

from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import Store
from autodiscover.research.capability_rehearsal import CapabilityProvider, rehearsal
from autodiscover.research.discovery import ROLES, replay
from autodiscover.research.session import Session, create_session, session_report
from autodiscover.research.session_cli import _configs, session_preflight
from autodiscover.research.session_contracts import SessionProfile

PROVIDERS = CONFIG / "discovery-capability-meta.json"
CAP_CHILD = CHILD.replace(
    "from autodiscover.research.session_rehearsal import RehearsalProvider, rehearsal",
    "from autodiscover.research.capability_rehearsal import "
    "CapabilityProvider as RehearsalProvider, rehearsal",
)


def profile(**updates):
    p = SessionProfile.model_validate_json(
        (CONFIG / "session-capability-ninety-minute.json").read_text()
    )
    return SessionProfile.model_validate({**p.model_dump(), **updates})


def make(store, selected):
    plan = session_preflight(selected, _configs(PROVIDERS))["branch"]
    return create_session(store, selected, plan, live=False)


def test_updated_accelerated_ninety_minutes(tmp_path):
    clock = [0.0]
    seen = []
    store = Store(tmp_path)

    class Timed(CapabilityProvider):
        def generate(self, request):
            prompt = json.loads(request.prompt)
            if prompt["task"] == "plan":
                seen.append(prompt)
                clock[0] += 950
            return super().generate(request)

    def factory(branch):
        lab = rehearsal(store, branch)
        lab.router.routes[ROLES[0]] = [Timed(ROLES[0], branch)]
        return lab

    selected = profile()
    identifier = make(store, selected)
    Session(store, factory, monotonic=lambda: clock[0]).execute(identifier)
    report = session_report(store, identifier)
    assert clock[0] >= 5400 and report["stop_reason"] == "SESSION_DEADLINE"
    assert report["critiques_completed"] >= 1 and report["hypotheses_generated"] >= 1
    assert report["usage"]["charged_usd"] == "0" and report["usage"]["uncertain"] == 0
    assert report["duplicate_queries"] + report["duplicate_hypotheses"] > 0
    assert any(p["session_context"]["recent_evidence"] for p in seen)
    assert all(
        note.startswith("Progress:")
        for p in seen
        for note in p["session_context"]["recent_evidence"]
    )
    assert all("AI-enabled" in p["objective"] for p in seen)
    assert len({p["session_context"]["investigation"] for p in seen}) >= 4
    for dossier in report["dossiers"]:
        packet = dossier["packet"]
        assert packet["commercial_level"] == 0 and packet["novelty_status"] == "unverified"
        assert {s["stage"] for s in packet["searches"]} >= {"source", "target", "prior_art"}
        assert replay(store, packet["run_id"])[0] == dossier["digest"]
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "stop_reason",
                    "branches_closed",
                    "usage",
                    "hypotheses_generated",
                    "critiques_completed",
                    "duplicate_queries",
                    "duplicate_hypotheses",
                    "evidence_anchor",
                ]
            },
            sort_keys=True,
        )
    )


@pytest.mark.parametrize("mode,code", [("cached", 75), ("completed-child", 77), ("ambiguous", 76)])
def test_capability_cross_process_recovery(tmp_path, mode, code):
    store = Store(tmp_path)
    selected = profile(max_branches=1)
    identifier = make(store, selected)
    child = subprocess.Popen(  # noqa: S603 - fixed local Python child with explicit argv
        [sys.executable, "-c", CAP_CHILD, str(tmp_path), identifier, mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _, stderr = child.communicate(timeout=15)
    assert child.returncode == code, stderr
    before = cli(tmp_path, "status", identifier)
    if mode == "ambiguous":
        cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS), ok=False)
        after = cli(tmp_path, "status", identifier)
        assert after["usage"]["requests"] == 1 and after["status"] == "PAUSED"
    else:
        after = cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS))
        assert after["status"] == "COMPLETED"
        # One standalone branch with session duplicate admission uses eight settled fixture calls.
        assert after["usage"]["requests"] == 8
        if mode == "completed-child":
            assert before["usage"]["requests"] == after["usage"]["requests"]
    assert verify_chain(store)


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_capability_external_controls(tmp_path, action):
    store = Store(tmp_path)
    identifier = make(store, profile(max_branches=1))
    child = subprocess.Popen(  # noqa: S603 - fixed local Python child with explicit argv
        [sys.executable, "-c", CAP_CHILD, str(tmp_path), identifier, "gate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        await_gate(tmp_path)
        cli(tmp_path, action, identifier, *(("--confirm",) if action == "cancel" else ()))
        (tmp_path / "release-dispatch").touch()
        _, stderr = child.communicate(timeout=15)
        assert child.returncode == 0, stderr
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()
    status = cli(tmp_path, "status", identifier)
    assert status["usage"]["requests"] == 1
    if action == "pause":
        done = cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS))
        assert done["status"] == "COMPLETED" and done["usage"]["requests"] == 8
    else:
        cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS), ok=False)


def test_capability_renews_short_leases_across_long_branch(tmp_path):
    elapsed = [1000.0]
    store = Store(tmp_path, clock=lambda: elapsed[0])
    lab = rehearsal(store, 0)

    class Slow(CapabilityProvider):
        def generate(self, request):
            result = super().generate(request)
            elapsed[0] += 50  # More than 300 s total, each bounded stage below the lease duration.
            return result

    for role in ROLES:
        lab.router.routes[role] = [Slow(role, 0)]
    _, packet = lab.execute(lab.register(specification()))
    assert elapsed[0] > 1300 and packet.critique_coverage == 1
    assert verify_chain(store)
