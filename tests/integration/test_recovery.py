import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from autodiscover.orchestrator.contracts import Stage
from autodiscover.orchestrator.store import StateError, Store


def test_crash_after_commit_before_checkpoint_resumes_without_duplicate(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("interrupted workflow", {})
    script = """
import os, sys
from pathlib import Path
from autodiscover.orchestrator.store import Store
from autodiscover.orchestrator.contracts import Stage
store=Store(Path(sys.argv[1]))
fence=store.claim(sys.argv[2], 'crashed', .05)
store.checkpoint=lambda run: os._exit(73)
store.complete_step(sys.argv[2], owner='crashed', fence=fence, expected=Stage.DISCOVER,
                    version=0, key='discover:0', output={'questions':['measurable question']})
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path), run], check=False)  # noqa: S603
    assert result.returncode == 73
    assert json.loads((tmp_path / "checkpoints" / f"{run}.json").read_text())["run"]["version"] == 0
    time.sleep(0.06)
    recovered = Store(tmp_path)
    fence = recovered.claim(run, "replacement")
    assert recovered.get_run(run)["stage"] == Stage.RESEARCH
    assert len(recovered.outputs(run)) == 1
    original = recovered.complete_step(
        run,
        owner="replacement",
        fence=fence,
        expected=Stage.DISCOVER,
        version=0,
        key="discover:0",
        output={"questions": ["measurable question"]},
    )
    assert original["version"] == 1
    assert len(recovered.outputs(run)) == 1
    recovered.checkpoint(run)
    assert json.loads((tmp_path / "checkpoints" / f"{run}.json").read_text())["run"]["version"] == 1


def test_concurrent_claims_have_one_winner(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("race", {})

    def claim(owner):
        try:
            return store.claim(run, str(owner))
        except StateError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        winners = [v for v in pool.map(claim, range(8)) if v is not None]
    assert len(winners) == 1


def test_crash_after_branch_allocation_reuses_credit_on_resumption(tmp_path):
    from autodiscover.orchestrator.lab import Lab

    lab = Lab(tmp_path)
    run = lab.demo(stop_after=3)
    script = """
import os,sys
from pathlib import Path
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.contracts import Stage
lab=Lab(Path(sys.argv[1]))
original=lab.store.complete_step
def crash(run_id,**kwargs):
 if kwargs['expected']==Stage.PRIORITIZE: os._exit(74)
 return original(run_id,**kwargs)
lab.store.complete_step=crash
lab.resume(sys.argv[2])
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path), run], check=False)  # noqa: S603
    assert result.returncode == 74
    assert len(lab.director.tree(run)["allocations"]) == 1
    assert lab.store.get_run(run)["stage"] == "PRIORITIZE"
    recovered = Lab(tmp_path)
    recovered.store.clock = lambda: time.time() + 301
    recovered.resume(run)
    assert recovered.report(run)["status"] == "COMPLETED"
    assert len(recovered.director.tree(run)["allocations"]) == 1


def test_v4_active_workflow_upgrades_without_replaying_completed_execution(tmp_path, monkeypatch):
    from autodiscover.config import Limits
    from autodiscover.evidence.artifacts import Artifacts
    from autodiscover.experiments.contracts import Plan
    from autodiscover.experiments.runner import run as execute
    from autodiscover.hypotheses.engine import Hypothesis, demo_proposal
    from autodiscover.orchestrator import migrations
    from autodiscover.orchestrator.lab import Lab

    full = migrations.MIGRATIONS
    monkeypatch.setattr(migrations, "MIGRATIONS", full[:4])
    store = Store(tmp_path)
    run = store.create_run("legacy v4 run", {})
    artifacts = Artifacts(tmp_path / "artifacts")
    h = Hypothesis.model_validate(demo_proposal("legacy v4 run"))
    h_digest = artifacts.put_json(h.model_dump(mode="json"))
    plan = Plan(hypothesis_id=h.identity)
    plan_digest = artifacts.put_json(plan.model_dump(mode="json"))
    raw = execute(plan, Limits())
    raw_digest = artifacts.put_json(raw)
    outputs = [
        (Stage.DISCOVER, {"questions": [h.question]}),
        (Stage.RESEARCH, {"source_ids": [], "coverage_limitations": "offline v4 fixture"}),
        (Stage.HYPOTHESIZE, {"hypothesis_ids": [h_digest]}),
        (Stage.PRIORITIZE, {"selected_ids": [h.identity]}),
        (Stage.DESIGN, {"plan_id": h.identity, "plan_digest": plan_digest}),
        (Stage.PREFLIGHT, {"plan_id": h.identity, "plan_digest": plan_digest, "authorized": True}),
        (
            Stage.EXECUTE,
            {
                "plan_digest": plan_digest,
                "artifact_digest": raw_digest,
                "elapsed_seconds": raw["elapsed_seconds"],
            },
        ),
    ]
    fence = store.claim(run, "legacy")
    for version, (stage, output) in enumerate(outputs):
        store.complete_step(
            run,
            owner="legacy",
            fence=fence,
            expected=stage,
            version=version,
            key=str(version),
            output=output,
        )
    store.release(run, "legacy", fence)
    committed = store.outputs(run)
    monkeypatch.setattr(migrations, "MIGRATIONS", full)
    recovered = Lab(tmp_path)
    recovered.resume(run)
    assert recovered.report(run)["status"] == "COMPLETED"
    assert recovered.store.outputs(run)[:7] == committed
    assert recovered.latest(run, Stage.EXECUTE)["artifact_digest"] == raw_digest
    assert len(recovered.director.tree(run)["allocations"]) == 1
