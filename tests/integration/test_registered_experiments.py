"""New reviewed allocation family, independent outcomes and durable run integration."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from autodiscover.config import Limits
from autodiscover.evidence.chain import verify_chain
from autodiscover.experiments.allocation_contracts import AllocationPlan
from autodiscover.experiments.allocation_evaluator import (
    AllocationEvaluationError,
    evaluate_allocation,
)
from autodiscover.experiments.registry import evaluate_registered, family, parse_plan
from autodiscover.experiments.runner import ExecutionError, preflight, run
from autodiscover.hypotheses.allocation import allocation_demo_proposal
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal
from autodiscover.orchestrator.lab import Lab


def test_registered_allocation_worker_is_independently_optimal():
    plan = AllocationPlan(hypothesis_id="resource-allocation")
    preflight(plan, Limits())
    raw = run(plan, Limits())
    report = evaluate_registered(plan, raw)
    assert report["passed"] is True
    assert report["all_heldout_optimal"] is True
    assert report["heldout_min_gain"] >= plan.minimum_gain
    assert report["heldout_mean_gain"] > 0
    assert report["limitations"].startswith("Synthetic")
    assert raw["isolation"] == "macOS-seatbelt"
    assert evaluate_registered(
        plan, run(plan, Limits(), replication=1), replication=1
    )["passed"]
    greedy = AllocationPlan(hypothesis_id="baseline", algorithm="greedy")
    baseline = evaluate_allocation(greedy, run(greedy, Limits()))
    assert baseline["passed"] is False
    assert baseline["heldout_mean_gain"] == 0


def test_allocation_metric_tampering_is_recomputed_from_selected_items():
    plan = AllocationPlan(hypothesis_id="tampers")
    raw = run(plan, Limits())
    extra = deepcopy(raw)
    extra["output"]["rows"][0]["selected"] = [0, 0]
    with pytest.raises(AllocationEvaluationError, match="INVALID_ALLOCATION_SELECTION"):
        evaluate_allocation(plan, extra)
    overweight = deepcopy(raw)
    overweight["output"]["rows"][0]["selected"] = [0, 1, 2]
    with pytest.raises(AllocationEvaluationError, match="OVERWEIGHT_ALLOCATION"):
        evaluate_allocation(plan, overweight)
    injected = deepcopy(raw)
    injected["output"]["technical_success"] = True
    with pytest.raises(AllocationEvaluationError, match="INVALID_ALLOCATION_RESULT_SCHEMA"):
        evaluate_allocation(plan, injected)
    swapped = deepcopy(raw)
    swapped["plan_digest"] = "0" * 64
    with pytest.raises(AllocationEvaluationError, match="PLAN_OR_REPLICATION"):
        evaluate_allocation(plan, swapped)
    wrong = deepcopy(raw)
    wrong["output"]["rows"][0]["id"] = "heldout:999"
    with pytest.raises(AllocationEvaluationError, match="CASE_ID"):
        evaluate_allocation(plan, wrong)


def test_registration_limits_and_preregistered_code_identity_fail_closed():
    assert family("allocation-v1").worker_file == "allocation_worker.py"
    assert family("encoding-v1").worker_file == "worker.py"
    with pytest.raises(ValueError, match="UNREVIEWED"):
        family("arbitrary-python")
    with pytest.raises(ValueError, match="UNREVIEWED"):
        parse_plan({"implementation": "generated-python"})
    with pytest.raises(ValidationError):
        AllocationPlan.model_validate(
            {"hypothesis_id": "unsafe", "algorithm": "eval(open('/etc/passwd'))"}
        )
    altered = AllocationPlan(hypothesis_id="changed").model_copy(
        update={"worker_sha256": "0" * 64}
    )
    with pytest.raises(ExecutionError, match="PREREGISTERED_CODE_CHANGED"):
        preflight(altered, Limits())


def test_allocation_family_uses_full_durable_loop_and_replications(tmp_path):
    lab = Lab(tmp_path)
    run_id = lab.explore(
        "regional inventory allocation",
        [allocation_demo_proposal("regional inventory allocation")],
    )
    report = lab.report(run_id)
    assert report["status"] == "COMPLETED"
    assert report["assessment"]["technical_success"] is True
    assert report["assessment"]["novelty"] == "unknown"
    assert report["commercial"]["level"] == 0
    assert report["commercial"]["validated"] is False
    assert report["usage"]["charged_usd"] == "0"
    assert all(node["kind"] == "allocation" for node in report["search"]["nodes"])
    assert len(report["jobs"]) >= 3
    assert all(job["status"] == "COMPLETED" for job in report["jobs"])
    assert lab.plan(run_id).implementation == "allocation-v1"
    assert verify_chain(lab.store)["verified_events"] >= 12


def test_failed_greedy_candidate_cannot_claim_success(tmp_path):
    lab = Lab(tmp_path)
    greedy = allocation_demo_proposal().model_copy(update={"algorithm": "greedy"})
    run_id = lab.explore("resource allocation baseline", [greedy])
    report = lab.report(run_id)
    assert report["status"] == "COMPLETED"
    assert report["assessment"] is None
    assert all(node["status"] == "FAILED" for node in report["search"]["nodes"])
    assert report["search"]["stopped_reason"] is None
    assert not lab.director.has_work(run_id)
    assert report["commercial"] is None


def test_two_genuinely_different_reviewed_families_can_share_search(tmp_path):
    lab = Lab(tmp_path)
    encoding = Hypothesis.model_validate(demo_proposal("consumer telemetry"))
    allocation = allocation_demo_proposal("supply chain")
    run_id = lab.explore("cross-family research", [encoding, allocation])
    report = lab.report(run_id)
    assert report["status"] == "COMPLETED"
    assert {node["kind"] for node in report["search"]["nodes"]} == {
        "encoding", "allocation"
    }
    assert {job["status"] for job in report["jobs"]} == {"COMPLETED"}
    assert len({job["plan_digest"] for job in report["jobs"]}) >= 2
    assert report["assessment"]["novelty"] == "unknown"
    assert report["commercial"]["level"] == 0
    assert verify_chain(lab.store)["verified_events"] > 20


def test_preflight_rejects_changed_evaluator_and_malformed_typed_plan():
    plan = AllocationPlan(hypothesis_id="changed")
    for update in (
        {"evaluator_sha256": "0" * 64},
        {"implementation": "encoding-v1"},
        {"memory_mb": 1000},
    ):
        with pytest.raises(ExecutionError, match="PREREGISTERED_CODE_CHANGED"):
            preflight(plan.model_copy(update=update), Limits())
    with pytest.raises(ValidationError):
        parse_plan(plan.model_dump() | {"worker_file": "../unreviewed.py"})


def test_replications_and_greedy_control_reject_substituted_evidence():
    plan = AllocationPlan(hypothesis_id="replica")
    with pytest.raises(ExecutionError, match="REPLICATION_OUTSIDE_PLAN"):
        run(plan, Limits(), replication=3)
    raw = run(plan, Limits())
    with pytest.raises(AllocationEvaluationError, match="REPLICATION_OUTSIDE_PLAN"):
        evaluate_allocation(plan, raw | {"replication": 3}, replication=3)
    greedy = plan.model_copy(update={"algorithm": "greedy"})
    with pytest.raises(AllocationEvaluationError, match="GREEDY_SELECTION_MISMATCH"):
        evaluate_allocation(greedy, raw | {"plan_digest": greedy.digest})


def test_allocation_result_requires_completed_job_in_same_run(tmp_path):
    from autodiscover.evidence.artifacts import IntegrityError
    from autodiscover.orchestrator.contracts import Stage

    lab = Lab(tmp_path)
    proposal = allocation_demo_proposal()
    original = lab.explore("same allocation proposal", [proposal])
    other = lab.store.create_run("different run", {})
    candidate = lab.director.register(other, proposal)
    digest = lab.latest(original, Stage.VERIFY)["report_digest"]
    with pytest.raises(IntegrityError, match="completed allocation job"):
        lab.director.record(other, candidate, digest)
