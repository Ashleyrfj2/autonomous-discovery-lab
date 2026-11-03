"""Versioned independently generated fixtures; no provider receives held-out observations."""

import random
from typing import Any

from autodiscover.experiments.contracts import Plan


def fixtures(plan: Plan, *, replication: int = 0) -> list[dict[str, Any]]:
    rows = []
    for split, offset, count in (("train", 0, plan.samples), ("heldout", 100003, plan.samples * 2)):
        rng = random.Random(plan.seed + offset + replication * 9973)  # noqa: S311 - reproducible data
        for index in range(count):
            data: list[int] = []
            if plan.data_profile == "alternating":
                data = [i % 2 for i in range(plan.bytes_per_sample)]
            else:
                while len(data) < plan.bytes_per_sample:
                    data.extend([rng.randrange(256)] * rng.randint(6, 24))
                data = data[: plan.bytes_per_sample]
            rows.append({"id": f"{split}:{index}", "split": split, "data": data})
    return rows
