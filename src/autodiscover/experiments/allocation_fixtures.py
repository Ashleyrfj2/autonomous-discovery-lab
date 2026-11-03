"""Independent reproducible 0/1-knapsack fixtures with ratio-greedy counterexamples."""

import random
from typing import Any

from autodiscover.experiments.allocation_contracts import AllocationPlan


def allocation_fixtures(
    plan: AllocationPlan, *, replication: int = 0
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, offset, count in (
        ("train", 0, plan.samples),
        ("heldout", 100003, plan.samples * 2),
    ):
        rng = random.Random(plan.seed + offset + replication * 9973)  # noqa: S311
        for index in range(count):
            # Greedy selects the high-ratio weight-6 item, missing the better
            # combination of two weight-5 items. Extra items distract but cannot win.
            bonus = rng.randrange(3)
            items = [
                {"weight": 6, "value": 13 + bonus},
                {"weight": 5, "value": 10},
                {"weight": 5, "value": 10},
                {"weight": 9, "value": 2},
                {"weight": 8, "value": 3},
                {"weight": 7, "value": 2},
            ]
            rng.shuffle(items)
            rows.append(
                {"id": f"{split}:{index}", "split": split, "capacity": 10, "items": items}
            )
    return rows
