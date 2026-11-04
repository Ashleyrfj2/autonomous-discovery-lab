"""Separate-process operator controls and hard crash recovery on temporary roots."""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from test_research_session import PROVIDERS, make, profile

from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import Store

CHILD = """
import os, sys, time
from pathlib import Path
from autodiscover.orchestrator.store import Store
from autodiscover.research.discovery import ROLES
from autodiscover.research.session import Session
from autodiscover.research.session_rehearsal import RehearsalProvider, rehearsal
root, identifier, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
store = Store(root)
original_event = store._event
class Gated(RehearsalProvider):
    def generate(self, request):
        if mode == 'ambiguous':
            os._exit(76)
        (root / 'dispatch-entered').touch()
        while not (root / 'release-dispatch').exists():
            time.sleep(0.01)
        return super().generate(request)
def event(db, run_id, kind, payload):
    if mode == 'cached' and kind == 'discovery_checkpoint' and payload.get('key') == 'plan':
        os._exit(75)
    if mode == 'completed-child' and kind == 'session_branch_closed':
        os._exit(77)
    return original_event(db, run_id, kind, payload)
store._event = event
def factory(branch):
    lab = rehearsal(store, branch)
    if mode in {'ambiguous', 'gate'}:
        lab.router.routes[ROLES[0]] = [Gated(ROLES[0], branch)]
    return lab
Session(store, factory).execute(identifier)
"""


def cli(root, *args, ok=True):
    result = subprocess.run(  # noqa: S603 - fixed Python module and explicit argv
        [sys.executable, "-m", "autodiscover.cli", "--root", str(root), "session", *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if ok:
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    assert result.returncode != 0
    return {}


def spawn(root, session_id, mode):
    return subprocess.Popen(  # noqa: S603 - fixed child program and explicit argv
        [sys.executable, "-c", CHILD, str(root), session_id, mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def await_gate(root: Path):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if (root / "dispatch-entered").exists():
            return
        time.sleep(0.02)
    pytest.fail("The rehearsal worker did not reach the provider gate")


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_external_control_and_process_resume(tmp_path, action):
    store = Store(tmp_path)
    _, identifier = make(store, profile(max_branches=2))
    child = spawn(tmp_path, identifier, "gate")
    try:
        await_gate(tmp_path)
        before = cli(tmp_path, "status", identifier)
        assert before["worker_attached"] and before["usage"]["requests"] == 1
        cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS), ok=False)
        assert len(before["unresolved_reservations"]) == 1  # In flight, not yet ambiguous.
        args = ("--confirm",) if action == "cancel" else ()
        receipt = cli(tmp_path, action, identifier, *args)
        assert receipt["pause_requested"] if action == "pause" else receipt["status"] == "CANCELLED"
        (tmp_path / "release-dispatch").touch()
        _, stderr = child.communicate(timeout=12)
        assert child.returncode == 0, stderr
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()
    after = cli(tmp_path, "status", identifier)
    assert after["usage"]["requests"] == 1 and not after["worker_attached"]
    if action == "pause":
        assert after["status"] == "PAUSED"
        resumed = cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS))
        assert resumed["status"] == "COMPLETED"
        assert resumed["branches_closed"] == 2
        assert resumed["usage"]["requests"] == 7
        assert cli(tmp_path, "report", identifier)["dossiers"]
    else:
        assert after["status"] == "CANCELLED"
        assert after["stop_reason"] == "OPERATOR_CANCEL"
        cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS), ok=False)
    assert verify_chain(store)


@pytest.mark.parametrize(
    ("mode", "code"), [("cached", 75), ("ambiguous", 76), ("completed-child", 77)]
)
def test_abrupt_process_death_before_checkpoint(tmp_path, mode, code):
    store = Store(tmp_path)
    _, identifier = make(store, profile(max_branches=1))
    child = spawn(tmp_path, identifier, mode)
    _, stderr = child.communicate(timeout=12)
    assert child.returncode == code, stderr
    before = cli(tmp_path, "status", identifier)
    assert before["usage"]["requests"] == (4 if mode == "completed-child" else 1)
    assert before["usage"]["uncertain"] == (mode == "ambiguous")
    if mode != "ambiguous":
        resumed = cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS))
        assert resumed["status"] == "COMPLETED"
        assert resumed["usage"]["requests"] == 4
    else:
        cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS), ok=False)
        paused = cli(tmp_path, "status", identifier)
        assert paused["status"] == "PAUSED"
        assert paused["unresolved_reservations"][0]["status"] == "RESERVED"
        assert paused["usage"]["requests"] == 1
        cli(tmp_path, "resume", identifier, "--providers", str(PROVIDERS), ok=False)
    assert verify_chain(store)


def test_cli_offline_preflight_dry_run_and_live_authority(tmp_path):
    selected = PROVIDERS.with_name("session-qualification.json")
    preflight = cli(tmp_path, "preflight", "--profile", str(selected))
    assert preflight["max_attempts"] == 20
    assert preflight["model_access"] == "not checked"
    cli(tmp_path, "start", "--profile", str(selected), ok=False)
    assert not (tmp_path / "lab.sqlite3").exists()
    result = cli(tmp_path, "dry-run", "--profile", str(selected))
    assert result["status"] == "PAUSED" and result["usage"]["charged_usd"] == "0"
    assert result["stop_reason"] == "QUALIFICATION_CHECKPOINT"
    done = cli(tmp_path, "resume", result["session_id"], "--providers", str(PROVIDERS))
    assert done["status"] == "COMPLETED" and done["branches_closed"] == 2
