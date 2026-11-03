"""Independent evaluator: recompute held-out references and metrics from raw worker bytes."""

import math
from typing import Any

from pydantic import ValidationError

from autodiscover.experiments.contracts import Plan, RawResult, code_digest
from autodiscover.experiments.datasets import fixtures


class EvaluationError(ValueError):
    pass


def evaluate(plan: Plan, result: dict[str, Any], *, replication: int = 0) -> dict[str, Any]:
    try:
        result = RawResult.model_validate(result).model_dump(mode="json")
    except ValidationError:
        raise EvaluationError("INVALID_RESULT_SCHEMA_OR_UNSUPPORTED_CLAIM") from None
    if (
        plan.evaluator_sha256 != code_digest("evaluator.py")
        or plan.fixture_sha256 != code_digest("datasets.py")
        or result["worker_sha256"] != plan.worker_sha256
    ):
        raise EvaluationError("PREREGISTERED_CODE_MISMATCH")
    if result.get("plan_digest") != plan.digest or result.get("replication") != replication:
        raise EvaluationError("PLAN_OR_REPLICATION_MISMATCH")
    output = result.get("output", {})
    if set(output) != {"schema_version", "rows"} or output["schema_version"] != 1:
        raise EvaluationError("UNSUPPORTED_OUTPUT_OR_CLAIM")
    expected = fixtures(plan, replication=replication)
    rows = output["rows"]
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise EvaluationError("MISSING_OR_EXTRA_CASES")
    groups: dict[str, list[float]] = {"train": [], "heldout": []}
    for reference, row in zip(expected, rows, strict=True):
        if set(row) != {"id", "encoded"} or row["id"] != reference["id"]:
            raise EvaluationError("CASE_ID_OR_CLAIM_MANIPULATION")
        encoded = row["encoded"]
        if (
            not isinstance(encoded, list)
            or len(encoded) > 2048
            or any(type(x) is not int or not 0 <= x <= 255 for x in encoded)
        ):
            raise EvaluationError("INVALID_BYTES")
        decoded = encoded
        if plan.algorithm == "rle":
            if len(encoded) % 2 or any(c == 0 for c in encoded[::2]):
                raise EvaluationError("INVALID_RLE")
            decoded = [
                value
                for count, value in zip(encoded[::2], encoded[1::2], strict=True)
                for _ in range(count)
            ]
        if decoded != reference["data"]:
            raise EvaluationError("ROUNDTRIP_CORRUPTION")
        saving = 1 - len(encoded) / len(reference["data"])
        if not math.isfinite(saving):
            raise EvaluationError("INVALID_METRIC")
        groups[reference["split"]].append(saving)
    heldout = groups["heldout"]
    average = sum(heldout) / len(heldout)
    # Require every held-out case to meet the preregistered threshold, not only mean gain.
    passed = min(heldout) >= plan.minimum_savings
    return {
        "schema_version": 2,
        "plan_digest": plan.digest,
        "protocol_version": plan.protocol_version,
        "code_identity": {
            "worker": plan.worker_sha256,
            "fixture": plan.fixture_sha256,
            "evaluator": plan.evaluator_sha256,
        },
        "replication": replication,
        "passed": passed,
        "metric": "encoded-byte-savings-vs-raw",
        "heldout_mean_savings": average,
        "heldout_min_savings": min(heldout),
        "heldout_cases": len(heldout),
        "train_cases": len(groups["train"]),
        "threshold": plan.minimum_savings,
        "roundtrip_exact": True,
        "failure_analysis": None if passed else "Preregistered held-out savings threshold unmet",
        "uncertainty": {
            "type": "bounded fixture range",
            "min": min(heldout),
            "max": max(heldout),
            "population_claim": False,
        },
        "limitations": "Seeded synthetic fixtures only; known encoding, no novelty or market claim",
    }
