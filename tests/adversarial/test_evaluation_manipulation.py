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
