"""Explicit fixed review registry; models cannot register executable code or evaluators."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from autodiscover.experiments.allocation_contracts import AllocationPlan
from autodiscover.experiments.allocation_fixtures import allocation_fixtures
from autodiscover.experiments.contracts import Plan, code_digest
from autodiscover.experiments.datasets import fixtures

type RegisteredPlan = Plan | AllocationPlan


@dataclass(frozen=True)
class ReviewedFamily:
    name: Literal["encoding-v1", "allocation-v1"]
    worker_file: str
    fixture_file: str
    evaluator_file: str
    metric: str
    scope: str


REGISTERED_FAMILIES: tuple[ReviewedFamily, ...] = (
    ReviewedFamily(
        "encoding-v1", "worker.py", "datasets.py", "evaluator.py",
        "encoded-byte-savings-vs-raw", "reviewed lossless encoding",
    ),
    ReviewedFamily(
        "allocation-v1",
        "allocation_worker.py",
        "allocation_fixtures.py",
        "allocation_evaluator.py",
        "normalized-value-gain-vs-ratio-greedy",
        "reviewed bounded 0/1 resource allocation",
    ),
)


def family(name: str) -> ReviewedFamily:
    for item in REGISTERED_FAMILIES:
        if item.name == name:
            return item
    raise ValueError("UNREVIEWED_EXPERIMENT_FAMILY")


def parse_plan(data: dict[str, Any]) -> RegisteredPlan:
    if not isinstance(data, dict):
        raise ValueError("INVALID_PREREGISTERED_PLAN")
    name = data.get("implementation")
    if not isinstance(name, str):
        raise ValueError("INVALID_PREREGISTERED_PLAN")
    family(name)
    if name == "encoding-v1":
        return Plan.model_validate(data)
    return AllocationPlan.model_validate(data)


def execution_spec(
    plan: RegisteredPlan, *, replication: int = 0
) -> tuple[Path, list[dict[str, Any]]]:
    selected = family(plan.implementation)
    schema = Plan if selected.name == "encoding-v1" else AllocationPlan
    if not isinstance(plan, schema):
        raise ValueError("INVALID_PREREGISTERED_PLAN")
    try:
        validated = schema.model_validate(plan.model_dump(warnings=False), strict=True)
    except ValidationError:
        raise ValueError("INVALID_PREREGISTERED_PLAN") from None
    if (
        validated.worker_sha256 != code_digest(selected.worker_file)
        or validated.fixture_sha256 != code_digest(selected.fixture_file)
        or validated.evaluator_sha256 != code_digest(selected.evaluator_file)
    ):
        raise ValueError("REVIEWED_EXPERIMENT_IDENTITY_CHANGED")
    script = Path(__file__).with_name(selected.worker_file)
    if isinstance(validated, Plan):
        return script, fixtures(validated, replication=replication)
    return script, allocation_fixtures(validated, replication=replication)


def evaluate_registered(
    plan: RegisteredPlan, raw: dict[str, Any], *, replication: int = 0
) -> dict[str, Any]:
    family(plan.implementation)
    if isinstance(plan, Plan):
        from autodiscover.experiments.evaluator import evaluate

        return evaluate(plan, raw, replication=replication)
    from autodiscover.experiments.allocation_evaluator import evaluate_allocation

    return evaluate_allocation(plan, raw, replication=replication)
