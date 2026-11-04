"""Validate durable workflow authority/state against its evidence history."""

import hashlib
import json
from typing import Any

from autodiscover.evidence.artifacts import IntegrityError


def verify_run_projections(
    events: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> dict[str, int]:
    expected: dict[str, dict[str, Any]] = {}
    legacy = set()
    topic_digests = {}
    for event in events:
        run = event["run_id"]
        payload = json.loads(event["payload_json"])
        kind = event["kind"]
        if kind == "run_created":
            expected[run] = {
                "id": run,
                "stage": "DISCOVER",
                "status": "ACTIVE",
                "version": 0,
                "owner": None,
                "fence": 0,
                "failures": 0,
                "last_error": None,
                "policy": payload["policy"],
            }
            if "topic_sha256" in payload:
                topic_digests[run] = payload["topic_sha256"]
            else:
                legacy.add(run)
        elif kind == "claimed":
            if payload["fence"] != expected[run]["fence"] + 1:
                raise IntegrityError("Run claim fence inconsistent with evidence")
            expected[run].update(owner=payload["owner"], fence=payload["fence"])
        elif kind == "run_released":
            if payload["fence"] != expected[run]["fence"]:
                raise IntegrityError("Run release fence inconsistent with evidence")
            expected[run]["owner"] = None
        elif kind == "stage_completed":
            if (
                payload["version"] != expected[run]["version"]
                or payload["stage"] != expected[run]["stage"]
            ):
                raise IntegrityError("Run transition sequence inconsistent with evidence")
            expected[run].update(
                stage=payload["target"] or payload["stage"],
                status="ACTIVE" if payload["target"] else "COMPLETED",
                version=payload["version"] + 1,
                failures=0,
                last_error=None,
            )
        elif kind == "discovery_finished":
            expected[run].update(status="COMPLETED")
        elif kind == "session_stopped":
            expected[run].update(status=payload["status"])
        elif kind == "step_failed":
            expected[run].update(
                failures=payload["attempt"],
                last_error=payload["error_code"],
                status="ACTIVE" if payload["retry_allowed"] else "FAILED",
            )
        elif kind in ("control", "run_budget_paused"):
            expected[run].update(
                status=payload.get("status", "PAUSED"), owner=None, fence=expected[run]["fence"] + 1
            )
    if set(expected) != {row["id"] for row in rows}:
        raise IntegrityError("Run registry missing or unexpected evidence")
    for row in rows:
        actual = {
            key: row[key]
            for key in (
                "id",
                "stage",
                "status",
                "version",
                "owner",
                "fence",
                "failures",
                "last_error",
            )
        }
        actual["policy"] = json.loads(row["policy_json"])
        if row["id"] in legacy and row["owner"] is None:
            # Historical releases were not evented; never invent their missing provenance.
            actual["owner"] = expected[row["id"]]["owner"]
        if actual != expected[row["id"]]:
            raise IntegrityError("Run state/authority/policy disagrees with evidence")
        if (
            row["id"] in topic_digests
            and hashlib.sha256(row["topic"].encode()).hexdigest() != topic_digests[row["id"]]
        ):
            raise IntegrityError("Research topic disagrees with evidence")
    return {"legacy_runs_without_topic_or_release_anchors": len(legacy)}
