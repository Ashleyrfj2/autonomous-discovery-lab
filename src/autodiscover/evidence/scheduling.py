"""Check queue ownership/status/progress against durable scheduler events."""

import json
from typing import Any

from autodiscover.evidence.artifacts import IntegrityError


def verify_queue_projections(events: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    expected = {}
    fields = ("run_id", "status", "owner", "fence", "attempts", "completed_steps", "last_error")
    for event in events:
        if event["kind"] not in (
            "queue_enqueued",
            "queue_claimed",
            "queue_synchronized",
            "queue_step_finished",
        ):
            continue
        payload = json.loads(event["payload_json"])
        expected[event["run_id"]] = {
            "run_id": event["run_id"],
            "status": payload["status"],
            "owner": payload.get("owner"),
            "fence": payload["fence"],
            "attempts": payload["attempts"],
            "completed_steps": payload["completed_steps"],
            "last_error": payload["last_error"],
        }
    actual = {row["run_id"]: {field: row[field] for field in fields} for row in rows}
    if actual != expected:
        raise IntegrityError("Scheduler queue projection disagrees with evidence")
