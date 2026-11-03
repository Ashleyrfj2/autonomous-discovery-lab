import pytest
from pydantic import ValidationError

from autodiscover.config import Limits
from autodiscover.experiments.allocation_contracts import AllocationPlan
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


@pytest.mark.parametrize("plan_type", [Plan, AllocationPlan])
def test_rss_supervisor_rejects_over_limit_observation_and_cleans_worker(monkeypatch, plan_type):
    from types import SimpleNamespace

    import psutil

    from autodiscover.experiments import runner

    original = psutil.Process
    workers = []

    def monitor(pid):
        process = original(pid)
        workers.append(process)
        return SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=300 * 1024 * 1024))

    monkeypatch.setattr(runner.psutil, "Process", monitor)
    with pytest.raises(ExecutionError, match="WORKER_MEMORY_LIMIT"):
        run(plan_type(hypothesis_id="simulated-rss-observation"), Limits())
    assert workers and all(not process.is_running() for process in workers)


def test_allocation_worker_applies_wall_time_and_output_limits():
    with pytest.raises(ExecutionError, match="WORKER_TIMEOUT"):
        run(AllocationPlan(hypothesis_id="timeout", seconds=0.000001), Limits())
    with pytest.raises(ExecutionError, match="OUTPUT_LIMIT"):
        run(AllocationPlan(hypothesis_id="output", samples=30, max_output_bytes=1000), Limits())
