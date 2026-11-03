import json
from typing import Any

import pytest
from pydantic import ValidationError

from autodiscover.config import Limits
from autodiscover.orchestrator.contracts import (
    OUTPUTS,
    STAGES,
    AssessResult,
    MarketResult,
    RunStatus,
    Stage,
)
from autodiscover.orchestrator.store import StateError, Store

OUTPUT = {
    Stage.DISCOVER: {"questions": ["Can a bounded estimator beat a baseline?"]},
    Stage.RESEARCH: {"source_ids": [], "coverage_limitations": "Offline fixture"},
    Stage.HYPOTHESIZE: {"hypothesis_ids": ["h1"]},
    Stage.PRIORITIZE: {"selected_ids": ["h1"]},
    Stage.DESIGN: {"plan_id": "p1", "plan_digest": "a" * 64},
    Stage.PREFLIGHT: {"plan_id": "p1", "plan_digest": "a" * 64, "authorized": True},
    Stage.EXECUTE: {"plan_digest": "a" * 64, "artifact_digest": "b" * 64, "elapsed_seconds": 0.01},
    Stage.VERIFY: {"passed": True, "report_digest": "c" * 64},
    Stage.REPLICATE: {"passed": True, "report_digests": ["d" * 64, "e" * 64]},
    Stage.ASSESS: {"technical_success": True, "novelty": "unknown", "limitations": "Fixture only"},
    Stage.VALIDATE_MARKET: {"level": 0, "evidence_ids": [], "validated": False},
    Stage.DECIDE: {"decision": "stop", "rationale": "Bounded cycle finished"},
}


def make(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("test", Limits().model_dump(mode="json"))
    fence = store.claim(run, "worker")
    return store, run, fence


def test_full_lifecycle_schema_and_idempotency(tmp_path):
    store, run, fence = make(tmp_path)
    for version, stage in enumerate(STAGES):
        args: dict[str, Any] = dict(
            owner="worker",
            fence=fence,
            expected=stage,
            version=version,
            key=str(version),
            output=OUTPUT[stage],
        )
        result = store.complete_step(run, **args)
        if stage != Stage.DECIDE:
            assert store.complete_step(run, **args) == result
        assert result["version"] == version + 1
    assert store.get_run(run)["status"] == RunStatus.COMPLETED
    assert len(store.outputs(run)) == 12
    with store.connection() as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5
    assert (
        json.loads((tmp_path / "checkpoints" / f"{run}.json").read_text())["run"]["version"] == 12
    )


def test_schema_and_invalid_transitions(tmp_path):
    store, run, fence = make(tmp_path)
    with pytest.raises(ValidationError):
        store.complete_step(
            run,
            owner="worker",
            fence=fence,
            expected=Stage.DISCOVER,
            version=0,
            key="invalid",
            output={"questions": []},
        )
    with pytest.raises(StateError):
        store.complete_step(
            run,
            owner="worker",
            fence=fence,
            expected=Stage.DISCOVER,
            version=0,
            key="jump",
            output=OUTPUT[Stage.DISCOVER],
            target=Stage.EXECUTE,
        )
    assert store.get_run(run)["version"] == 0
    with pytest.raises(ValidationError):
        AssessResult(technical_success=True, novelty="supported", limitations="none")
    with pytest.raises(ValidationError):
        MarketResult(level=4, evidence_ids=[], validated=True)
    with pytest.raises(ValidationError):
        OUTPUTS[Stage.PREFLIGHT].model_validate({**OUTPUT[Stage.PREFLIGHT], "authorized": False})
    with pytest.raises(ValueError):
        store.create_run("path injection", {}, run_id="../../escape")


def test_pause_resume_cancel_fences_worker(tmp_path):
    store, run, old = make(tmp_path)
    store.control(run, "pause")
    with pytest.raises(StateError):
        store.heartbeat(run, "worker", old)
    store.control(run, "resume")
    new = store.claim(run, "replacement")
    assert new > old
    with pytest.raises(StateError):
        store.complete_step(
            run,
            owner="worker",
            fence=old,
            expected=Stage.DISCOVER,
            version=0,
            key="old",
            output=OUTPUT[Stage.DISCOVER],
        )
    store.control(run, "cancel")
    with pytest.raises(StateError):
        store.control(run, "resume")
    with pytest.raises(StateError):
        store.claim(run, "other")


def test_expiry_reclaim_and_retry_limits(tmp_path):
    current = [100.0]
    store = Store(tmp_path, clock=lambda: current[0])
    run = store.create_run("test", {})
    old = store.claim(run, "worker", 5)
    with pytest.raises(StateError):
        store.claim(run, "competitor")
    current[0] += 6
    new = store.claim(run, "competitor")
    with pytest.raises(StateError):
        store.heartbeat(run, "worker", old)
    for expected in (RunStatus.ACTIVE, RunStatus.ACTIVE, RunStatus.FAILED):
        assert store.fail_step(run, "competitor", new, "PROVIDER_TIMEOUT") == expected
    assert store.get_run(run)["failures"] == 3
    with pytest.raises(StateError):
        store.claim(run, "unbounded-retry")


def test_idempotency_conflict_and_input_envelope(tmp_path):
    store, run, fence = make(tmp_path)
    step = store.step_input(run)
    assert step.stage == Stage.DISCOVER
    assert step.predecessor_event is None
    args: dict[str, Any] = dict(
        owner="worker",
        fence=fence,
        expected=Stage.DISCOVER,
        version=0,
        key="one",
        output=OUTPUT[Stage.DISCOVER],
    )
    store.complete_step(run, **args)
    with pytest.raises(StateError):
        store.complete_step(run, **{**args, "output": {"questions": ["changed"]}})
    assert store.step_input(run).predecessor_event is not None
