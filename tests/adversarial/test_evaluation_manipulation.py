from copy import deepcopy

import pytest

from autodiscover.config import Limits
from autodiscover.experiments.contracts import Plan
from autodiscover.experiments.evaluator import EvaluationError, evaluate
from autodiscover.experiments.runner import ExecutionError, preflight, run


@pytest.fixture(scope="module")
def valid():
    plan = Plan(hypothesis_id="adversarial-evaluation")
    return plan, run(plan, Limits())


@pytest.mark.parametrize(
    "attack",
    [
        "success_claim",
        "metric_claim",
        "missing_case",
        "duplicate_id",
        "corrupt_bytes",
        "nan",
        "bool_byte",
        "negative_byte",
        "zero_run",
        "wrong_plan",
        "wrong_replication",
        "wrong_code",
        "invalid_type",
        "oversized",
        "infinite_time",
        "model_approval",
    ],
)
def test_rejects_manipulated_metrics_fixtures_claims_and_provenance(valid, attack):
    plan, original = valid
    result = deepcopy(original)
    rows = result["output"]["rows"]
    if attack == "success_claim":
        result["output"]["success"] = True
    elif attack == "metric_claim":
        result["output"]["savings"] = 1.0
    elif attack == "missing_case":
        rows.pop()
    elif attack == "duplicate_id":
        rows[-1]["id"] = rows[0]["id"]
    elif attack == "corrupt_bytes":
        rows[-1]["encoded"][1] = (rows[-1]["encoded"][1] + 1) % 256
    elif attack == "nan":
        rows[0]["encoded"][0] = float("nan")
    elif attack == "bool_byte":
        rows[0]["encoded"][0] = True
    elif attack == "negative_byte":
        rows[0]["encoded"][0] = -1
    elif attack == "zero_run":
        rows[0]["encoded"][0] = 0
    elif attack == "wrong_plan":
        result["plan_digest"] = "0" * 64
    elif attack == "wrong_replication":
        result["replication"] = 1
    elif attack == "wrong_code":
        result["worker_sha256"] = "0" * 64
    elif attack == "invalid_type":
        result["output"]["rows"] = "not rows"
    elif attack == "oversized":
        rows[0]["encoded"] = [1] * 2049
    elif attack == "infinite_time":
        result["elapsed_seconds"] = float("inf")
    else:
        result["critic_approval"] = "Two models independently approve this result"
    with pytest.raises(EvaluationError):
        evaluate(plan, result)


def test_preregistered_code_cannot_change_after_design(valid):
    plan, _ = valid
    replaced = plan.model_copy(update={"worker_sha256": "0" * 64})
    with pytest.raises(ExecutionError, match="CODE_CHANGED"):
        preflight(replaced, Limits())


def test_known_algorithm_fails_outside_prespecified_distribution():
    plan = Plan(hypothesis_id="alternating-is-adverse", data_profile="alternating")
    report = evaluate(plan, run(plan, Limits()))
    assert report["roundtrip_exact"] is True
    assert report["passed"] is False
    assert report["heldout_mean_savings"] == -1
    assert report["uncertainty"]["population_claim"] is False


def test_persisted_success_projection_cannot_disagree_with_hash_chained_evidence(tmp_path):
    from autodiscover.evidence.artifacts import IntegrityError
    from autodiscover.orchestrator.lab import Lab

    lab = Lab(tmp_path)
    run_id = lab.demo(stop_after=1)
    with lab.store.connection(write=True) as db:
        db.execute(
            "UPDATE steps SET output_json=? WHERE run_id=?",
            ('{"schema_version":1,"questions":["fabricated authoritative output"]}', run_id),
        )
    with pytest.raises(IntegrityError, match="projection"):
        lab.resume(run_id)


def test_tampered_branch_score_and_deleted_allocations_are_detected(tmp_path):
    from autodiscover.evidence.artifacts import IntegrityError
    from autodiscover.evidence.chain import verify_chain
    from autodiscover.orchestrator.lab import Lab

    lab = Lab(tmp_path)
    run = lab.demo(stop_after=4)
    with lab.store.connection(write=True) as db:
        db.execute("UPDATE hypotheses SET score=999 WHERE run_id=?", (run,))
    with pytest.raises(IntegrityError, match="Branch"):
        verify_chain(lab.store)
    with lab.store.connection(write=True) as db:
        db.execute("UPDATE hypotheses SET score=NULL WHERE run_id=?", (run,))
        db.execute("DELETE FROM branch_allocations WHERE run_id=?", (run,))
    with pytest.raises(IntegrityError, match="Branch"):
        verify_chain(lab.store)


@pytest.mark.parametrize(
    "column,value",
    [
        ("topic", "changed research mission"),
        ("status", "COMPLETED"),
        ("stage", "EXECUTE"),
        ("version", 99),
        ("policy_json", '{"allow_live_inference":true}'),
    ],
)
def test_run_state_and_authority_tampering_are_detected_before_execution(tmp_path, column, value):
    from autodiscover.evidence.artifacts import IntegrityError
    from autodiscover.orchestrator.lab import Lab

    lab = Lab(tmp_path)
    run = lab.demo(stop_after=2)
    queries = {
        "topic": "UPDATE runs SET topic=? WHERE id=?",
        "status": "UPDATE runs SET status=? WHERE id=?",
        "stage": "UPDATE runs SET stage=? WHERE id=?",
        "version": "UPDATE runs SET version=? WHERE id=?",
        "policy_json": "UPDATE runs SET policy_json=? WHERE id=?",
    }
    with lab.store.connection(write=True) as db:
        db.execute(queries[column], (value, run))
    with pytest.raises(IntegrityError):
        lab.resume(run)
    assert not lab.jobs.status(run)


@pytest.mark.parametrize(
    "field,value", [("status", "COMPLETED"), ("fence", 999), ("completed_steps", 99)]
)
def test_scheduler_rejects_tampering_before_overwriting_projection(tmp_path, field, value):
    from autodiscover.evidence.artifacts import IntegrityError
    from autodiscover.orchestrator.lab import Lab
    from autodiscover.orchestrator.scheduler import Scheduler

    lab = Lab(tmp_path)
    run_id = lab.store.create_run("queue evidence", {})
    queue = Scheduler(lab.store)
    queue.enqueue(run_id)
    with lab.store.connection(write=True) as db:
        queries = {
            "status": "UPDATE work_queue SET status=? WHERE run_id=?",
            "fence": "UPDATE work_queue SET fence=? WHERE run_id=?",
            "completed_steps": "UPDATE work_queue SET completed_steps=? WHERE run_id=?",
        }
        db.execute(queries[field], (value, run_id))
    with pytest.raises(IntegrityError, match="queue projection"):
        queue.run(max_steps=1, max_seconds=1)
    assert lab.store.get_run(run_id)["version"] == 0
