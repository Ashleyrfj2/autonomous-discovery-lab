"""Explicit fixed review registry; models cannot register executable code or evaluators."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeAlias

from autodiscover.experiments.allocation_contracts import AllocationPlan
from autodiscover.experiments.allocation_fixtures import allocation_fixtures
from autodiscover.experiments.contracts import Plan, code_digest
from autodiscover.experiments.datasets import fixtures


RegisteredPlan: TypeAlias = Plan | AllocationPlan


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
    name = data.get("implementation")
    family(name)
    if name == "encoding-v1":
        return Plan.model_validate(data)
    return AllocationPlan.model_validate(data)


def execution_spec(
    plan: RegisteredPlan, *, replication: int = 0
) -> tuple[Path, list[dict[str, Any]]]:
    selected = family(plan.implementation)
    if isinstance(plan, Plan):
        if plan.worker_sha256 != code_digest(selected.worker_file):
            raise ValueError("REVIEWED_WORKER_IDENTITY_CHANGED")
        return Path(__file__).with_name(selected.worker_file), fixtures(
            plan, replication=replication
        )
    from autodiscover.experiments.allocation_contracts import allocation_digest

    if plan.worker_sha256 != allocation_digest(selected.worker_file):
        raise ValueError("REVIEWED_WORKER_IDENTITY_CHANGED")
    return Path(__file__).with_name(selected.worker_file), allocation_fixtures(
        plan, replication=replication
    )


def evaluate_registered(
    plan: RegisteredPlan, raw: dict[str, Any], *, replication: int = 0
) -> dict[str, Any]:
    family(plan.implementation)
    if isinstance(plan, Plan):
        from autodiscover.experiments.evaluator import evaluate

        return evaluate(plan, raw, replication=replication)
    from autodiscover.experiments.allocation_evaluator import evaluate_allocation

    return evaluate_allocation(plan, raw, replication=replication)
