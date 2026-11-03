import pytest
from pydantic import ValidationError

from autodiscover.config import Limits
from autodiscover.experiments.contracts import Plan
from autodiscover.experiments.evaluator import evaluate
from autodiscover.experiments.runner import ExecutionError, preflight, run


def test_reviewed_worker_baseline_and_replication():
    plan = Plan(hypothesis_id="test")
    result = run(plan, Limits())
    report = evaluate(plan, result)
    assert report["passed"]
    assert result["peak_rss_bytes"] < plan.memory_mb * 1024 * 1024
    assert result["isolation"] == "macOS-seatbelt"
    assert result["elapsed_seconds"] < plan.seconds
    replication = evaluate(plan, run(plan, Limits(), replication=1), replication=1)
    assert replication["passed"]
    baseline_plan = Plan(hypothesis_id="baseline", algorithm="identity")
    baseline = evaluate(baseline_plan, run(baseline_plan, Limits()))
    assert not baseline["passed"]
    assert baseline["heldout_mean_savings"] == 0
    assert baseline["failure_analysis"]


def test_limits_and_unknown_code_fail_closed():
    with pytest.raises(ValidationError):
        Plan.model_validate(
            {"hypothesis_id": "malicious", "algorithm": "python:open('/etc/passwd')"}
        )
    with pytest.raises(ValidationError):
        Plan(hypothesis_id="too large", samples=100000)
    with pytest.raises(ExecutionError, match="TIME_AUTHORITY"):
        preflight(Plan(hypothesis_id="exceed", seconds=10), Limits(max_experiment_seconds=1))
    with pytest.raises(ExecutionError, match="WORKER_TIMEOUT"):
        run(Plan(hypothesis_id="timeout", seconds=0.000001), Limits())
    with pytest.raises(ExecutionError, match="OUTPUT_LIMIT"):
        run(Plan(hypothesis_id="output", max_output_bytes=1000), Limits())
