"""Audit durable worker identity, scientific results and admission-state projections."""

import json
from typing import Any

from autodiscover.evidence.artifacts import Artifacts, IntegrityError


def verify_job_projections(
    events: list[dict[str, Any]], rows: list[dict[str, Any]], artifacts: Artifacts
) -> None:
    jobs: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = json.loads(event["payload_json"])
        kind = event["kind"]
        if kind == "job_claimed":
            identifier = payload["job_id"]
            jobs[identifier] = {
                "id": identifier,
                "run_id": event["run_id"],
                "stage_version": payload["stage_version"],
                "replication": payload["replication"],
                "plan_digest": payload["plan_digest"],
                "status": "RUNNING",
                "owner": payload["owner"],
                "fence": payload["fence"],
                "attempts": payload["attempts"],
                "error_count": payload["error_count"],
                "worker_pid": None,
                "worker_created_at": None,
                "artifact_digest": None,
                "last_error": None,
            }
        elif kind in (
            "job_worker_started",
            "job_completed",
            "job_interrupted",
            "job_failed",
            "job_reconciled",
        ):
            identifier = payload["job_id"]
            job = jobs.get(identifier)
            if not job or job["fence"] != payload["fence"] or job["run_id"] != event["run_id"]:
                raise IntegrityError("Job evidence has no matching fenced claim")
            if kind == "job_worker_started":
                job.update(
                    worker_pid=payload["worker_pid"], worker_created_at=payload["worker_created_at"]
                )
            elif kind == "job_completed":
                job.update(
                    status="COMPLETED", owner=None, artifact_digest=payload["artifact_digest"]
                )
                raw = artifacts.get_json(payload["artifact_digest"])
                if (
                    raw["plan_digest"] != job["plan_digest"]
                    or raw["replication"] != job["replication"]
                ):
                    raise IntegrityError(
                        "Completed sub-job result belongs to a different preregistration"
                    )
            else:
                job.update(
                    status=payload["status"],
                    owner=None,
                    error_count=payload["error_count"],
                    last_error=payload["reason"],
                )
    actual = {
        row["id"]: {key: value for key, value in row.items() if key != "lease_until"}
        for row in rows
    }
    if actual != jobs:
        raise IntegrityError("Worker sub-job projection disagrees with evidence")
