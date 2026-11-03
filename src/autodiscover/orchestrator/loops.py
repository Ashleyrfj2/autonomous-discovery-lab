"""Persistent bounded progress guards and task-dependency cycle checks."""

import hashlib
import json
import math
from typing import Any

from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store


class LoopDetected(RuntimeError):
    pass


def validate_dependencies(dependencies: dict[str, list[str]]) -> None:
    visiting, visited = set(), set()

    def visit(task: str) -> None:
        if task in visiting:
            raise LoopDetected("CIRCULAR_TASK_DEPENDENCY")
        if task in visited:
            return
        if task not in dependencies:
            raise ValueError("Dependency references unknown task")
        visiting.add(task)
        for child in dependencies[task]:
            visit(child)
        visiting.remove(task)
        visited.add(task)

    for task in dependencies:
        visit(task)


class ProgressGuard:
    def __init__(self, store: Store):
        self.store = store

    def observe(
        self,
        run_id: str,
        task_id: str,
        *,
        state: str,
        signature: str,
        progress: float = 0,
        tokens: int = 0,
        repeat_limit: int = 3,
        token_limit: int = 100000,
        observation_key: str | None = None,
    ) -> str | None:
        if (
            not task_id
            or not state
            or len(signature) > 500
            or tokens < 0
            or repeat_limit < 2
            or not math.isfinite(progress)
        ):
            raise ValueError("Bounded valid progress observation required")
        fingerprint = hashlib.sha256(signature.encode()).hexdigest()
        with self.store.connection(write=True) as db:
            row = db.execute(
                "SELECT * FROM progress_guards WHERE run_id=? AND task_id=?", (run_id, task_id)
            ).fetchone()
            record: dict[str, Any] = (
                json.loads(row["state_json"])
                if row
                else {
                    "history": [],
                    "best": -1.0e300,
                    "stagnation": 0,
                    "tokens_without_progress": 0,
                    "signature": None,
                    "repeats": 0,
                    "stopped_reason": None,
                }
            )
            if (
                observation_key is not None
                and record.get("last_observation_key") == observation_key
            ):
                if record["signature"] != fingerprint:
                    raise ValueError("Observation key reused with different work")
                return record["stopped_reason"]
            if record["stopped_reason"]:
                return record["stopped_reason"]
            record["last_observation_key"] = observation_key
            record["repeats"] = record["repeats"] + 1 if fingerprint == record["signature"] else 1
            record["signature"] = fingerprint
            if progress > record["best"]:
                record.update(best=progress, stagnation=0, tokens_without_progress=0)
            else:
                record["stagnation"] += 1
                record["tokens_without_progress"] += tokens
            history = (record["history"] + [state])[-20:]
            record["history"] = history
            reason = None
            if record["repeats"] >= repeat_limit:
                reason = "REPEATED_IDENTICAL_WORK"
            elif (
                len(history) >= 6
                and history[-6:-4] == history[-4:-2] == history[-2:]
                and record["stagnation"] >= 5
            ):
                reason = "STATE_OSCILLATION"
            elif record["tokens_without_progress"] > token_limit:
                reason = "TOKEN_CONSUMPTION_WITHOUT_PROGRESS"
            elif record["stagnation"] >= repeat_limit:
                reason = "NO_MEASURABLE_IMPROVEMENT"
            record["stopped_reason"] = reason
            db.execute(
                "INSERT INTO progress_guards VALUES(?,?,?) ON CONFLICT(run_id,task_id) "
                "DO UPDATE SET state_json=excluded.state_json",
                (run_id, task_id, canonical(record)),
            )
            self.store._event(
                db,
                run_id,
                "progress_observed",
                {
                    "task_id": task_id,
                    "state": state,
                    "fingerprint": fingerprint,
                    "progress": progress,
                    "tokens": tokens,
                    "stopped_reason": reason,
                    "state_sha256": hashlib.sha256(canonical(record).encode()).hexdigest(),
                },
            )
        return reason
