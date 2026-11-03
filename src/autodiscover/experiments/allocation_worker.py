"""Standalone audited allocation worker. Imports only the Python standard library."""

import json
import math
import resource
import sys


def choose(items: list[dict[str, int]], capacity: int, algorithm: str) -> list[int]:
    if algorithm == "greedy":
        order = sorted(
            range(len(items)),
            key=lambda i: (-items[i]["value"] / items[i]["weight"], i),
        )
        chosen: list[int] = []
        remaining = capacity
        for index in order:
            if items[index]["weight"] <= remaining:
                chosen.append(index)
                remaining -= items[index]["weight"]
        return sorted(chosen)
    if algorithm != "dynamic":
        raise ValueError("Unreviewed allocation algorithm")
    # Reviewed bounded 0/1 dynamic program; no shell, network or generated source.
    table: list[tuple[int, tuple[int, ...]]] = [(0, ()) for _ in range(capacity + 1)]
    for index, item in enumerate(items):
        weight, value = item["weight"], item["value"]
        for available in range(capacity, weight - 1, -1):
            previous_score, previous_ids = table[available - weight]
            current_score, _ = table[available]
            candidate = previous_score + value
            if candidate > current_score:
                table[available] = (candidate, previous_ids + (index,))
    _score, indices = max(table, key=lambda pair: pair[0])
    return sorted(indices)


def main() -> None:
    data = json.loads(sys.stdin.read(2000001))
    if not isinstance(data, dict) or set(data) != {
        "algorithm", "rows", "cpu_seconds", "memory_mb"
    }:
        raise ValueError("Invalid worker request")
    if data["algorithm"] not in ("greedy", "dynamic"):
        raise ValueError("Algorithm not allowlisted")
    cpu = max(1, min(120, math.ceil(data["cpu_seconds"])))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    memory = max(64, min(256, int(data["memory_mb"]))) * 1024 * 1024
    if sys.platform != "darwin":
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))

    def deny(event, _args):
        if event == "open" or event.startswith(("socket.", "subprocess.", "os.", "ctypes.")):
            raise PermissionError("Worker capability denied")

    sys.addaudithook(deny)
    rows = data["rows"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 90:
        raise ValueError("Invalid row count")
    output: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "split", "capacity", "items"}:
            raise ValueError("Invalid allocation row")
        capacity, items = row["capacity"], row["items"]
        if type(capacity) is not int or not 1 <= capacity <= 100:
            raise ValueError("Invalid capacity")
        if not isinstance(items, list) or not 1 <= len(items) <= 12:
            raise ValueError("Invalid item count")
        for item in items:
            if (
                not isinstance(item, dict)
                or set(item) != {"weight", "value"}
                or type(item["weight"]) is not int
                or type(item["value"]) is not int
                or not 1 <= item["weight"] <= 100
                or not 1 <= item["value"] <= 100
            ):
                raise ValueError("Invalid allocation item")
        output.append(
            {
                "id": row["id"],
                "selected": choose(items, capacity, data["algorithm"]),
            }
        )
    sys.stdout.write(json.dumps({"schema_version": 1, "rows": output}, allow_nan=False))


if __name__ == "__main__":
    main()
