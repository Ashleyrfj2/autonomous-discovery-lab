"""Independent brute-force evaluator for the reviewed allocation worker."""

from itertools import combinations
from statistics import mean
from typing import Any

from pydantic import ValidationError

from autodiscover.experiments.allocation_contracts import (
    AllocationPlan,
    AllocationRawResult,
    allocation_digest,
)
from autodiscover.experiments.allocation_fixtures import allocation_fixtures


class AllocationEvaluationError(ValueError):
    pass


def optimal_value(items: list[dict[str, int]], capacity: int) -> int:
    """Enumerate every bounded subset independently from worker dynamic programming."""
    best = 0
    for size in range(len(items) + 1):
        for chosen in combinations(range(len(items)), size):
            weight = sum(items[i]["weight"] for i in chosen)
            if weight <= capacity:
                best = max(best, sum(items[i]["value"] for i in chosen))
    return best


def greedy_baseline(items: list[dict[str, int]], capacity: int) -> int:
    order = sorted(
        range(len(items)),
        key=lambda i: (-items[i]["value"] / items[i]["weight"], i),
    )
    total, remaining = 0, capacity
    for index in order:
        if items[index]["weight"] <= remaining:
            total += items[index]["value"]
            remaining -= items[index]["weight"]
    return total


def evaluate_allocation(
    plan: AllocationPlan, raw: dict[str, Any], *, replication: int = 0
) -> dict[str, Any]:
    try:
        result = AllocationRawResult.model_validate(raw).model_dump(mode="json")
    except ValidationError:
        raise AllocationEvaluationError("INVALID_ALLOCATION_RESULT_SCHEMA") from None
    if (
        plan.worker_sha256 != allocation_digest("allocation_worker.py")
        or plan.fixture_sha256 != allocation_digest("allocation_fixtures.py")
        or plan.evaluator_sha256 != allocation_digest("allocation_evaluator.py")
        or result["worker_sha256"] != plan.worker_sha256
    ):
        raise AllocationEvaluationError("PREREGISTERED_ALLOCATION_CODE_MISMATCH")
    if result["plan_digest"] != plan.digest or result["replication"] != replication:
        raise AllocationEvaluationError("ALLOCATION_PLAN_OR_REPLICATION_MISMATCH")
    rows = result["output"]["rows"]
    expected = allocation_fixtures(plan, replication=replication)
    if len(rows) != len(expected):
        raise AllocationEvaluationError("ALLOCATION_CASE_COUNT_MISMATCH")
    train_count, gains, optimality = 0, [], []
    candidate_values = []
    baseline_values = []
    for observed, actual in zip(rows, expected, strict=True):
        if observed["id"] != actual["id"]:
            raise AllocationEvaluationError("ALLOCATION_CASE_ID_MISMATCH")
        indices = observed["selected"]
        if indices != sorted(set(indices)) or any(i >= len(actual["items"]) for i in indices):
            raise AllocationEvaluationError("INVALID_ALLOCATION_SELECTION")
        total_weight = sum(actual["items"][i]["weight"] for i in indices)
        if total_weight > actual["capacity"]:
            raise AllocationEvaluationError("OVERWEIGHT_ALLOCATION")
        value = sum(actual["items"][i]["value"] for i in indices)
        reference = optimal_value(actual["items"], actual["capacity"])
        baseline = greedy_baseline(actual["items"], actual["capacity"])
        if value > reference:
            raise AllocationEvaluationError("IMPOSSIBLE_ALLOCATION_SCORE")
        if actual["split"] == "heldout":
            gains.append((value - baseline) / max(1, reference))
            optimality.append(value == reference)
            candidate_values.append(value)
            baseline_values.append(baseline)
        else:
            train_count += 1
    if not gains:
        raise AllocationEvaluationError("MISSING_HELDOUT_ALLOCATION_CASES")
    minimum_gain, average_gain = min(gains), mean(gains)
    passed = all(optimality) and minimum_gain >= plan.minimum_gain
    return {
        "schema_version": 1,
        "plan_digest": plan.digest,
        "protocol_version": plan.protocol_version,
        "code_identity": {
            "worker": plan.worker_sha256,
            "fixture": plan.fixture_sha256,
            "evaluator": plan.evaluator_sha256,
        },
        "replication": replication,
        "passed": passed,
        "metric": "normalized-value-gain-vs-ratio-greedy",
        "heldout_min_gain": minimum_gain,
        "heldout_mean_gain": average_gain,
        "heldout_cases": len(gains),
        "train_cases": train_count,
        "candidate_mean_value": mean(candidate_values),
        "baseline_mean_value": mean(baseline_values),
        "all_heldout_optimal": all(optimality),
        "threshold": plan.minimum_gain,
        "failure_analysis": None if passed else "Independent optimum or preregistered gain unmet",
        "uncertainty": {
            "type": "seeded synthetic allocation traps",
            "min": minimum_gain,
            "max": max(gains),
            "population_claim": False,
        },
        "limitations": (
            "Synthetic bounded 0/1 allocation with known algorithms; "
            "not evidence of novelty, field deployment or commercial demand"
        ),
    }
