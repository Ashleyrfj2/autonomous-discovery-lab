"""Reconcile branch/director projections against their append-only evidence events."""

import hashlib
import json
from typing import Any

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.orchestrator.durability import canonical


def verify_branch_projections(
    events: list[dict[str, Any]], tables: dict[str, list[dict[str, Any]]]
) -> None:
    nodes: dict[tuple[str, str], dict[str, Any]] = {}
    policies: dict[str, dict[str, Any]] = {}
    allocations: dict[tuple[str, str], dict[str, Any]] = {}
    results: set[tuple[str, str, str, int]] = set()
    progress: dict[tuple[str, str], str] = {}
    for event in events:
        payload = json.loads(event["payload_json"])
        run = event["run_id"]
        kind = event["kind"]
        if kind == "hypothesis_registered":
            identifier = payload["hypothesis_id"]
            nodes[(run, identifier)] = {
                "id": identifier,
                "run_id": run,
                "identity": payload["identity"],
                "parent_id": payload["parent_id"],
                "depth": payload["depth"],
                "domain": payload["domain"],
                "kind": payload["kind"],
                "status": "THEORETICAL" if payload["kind"] == "theoretical" else "PENDING",
                "revision_evidence": payload["revision_evidence"],
                "score": None,
            }
        elif kind == "branch_evaluated":
            identifier = payload["hypothesis_id"]
            if (run, identifier) not in nodes:
                raise IntegrityError("Branch evaluation has no registered hypothesis")
            nodes[(run, identifier)].update(
                status=payload.get("status", "PROMISING" if payload["passed"] else "FAILED"),
                score=payload["score"],
            )
            results.add((run, identifier, payload["report_digest"], int(payload["passed"])))
        elif kind == "search_configured":
            policies[run] = {
                "run_id": run,
                "policy_json": canonical(payload["policy"]),
                "stopped_reason": None,
            }
        elif kind == "search_stopped":
            policies[run]["stopped_reason"] = payload["reason"]
        elif kind == "branch_allocated":
            key = payload["step_key"]
            allocations[(run, key)] = {
                "run_id": run,
                "step_key": key,
                "hypothesis_id": payload["hypothesis_id"],
                "mode": payload["mode"],
                "ordinal": payload["ordinal"],
            }
        elif kind == "progress_observed":
            progress[(run, payload["task_id"])] = payload["state_sha256"]
    actual_nodes = {(r["run_id"], r["id"]): r for r in tables["hypotheses"]}
    actual_policies = {r["run_id"]: r for r in tables["director_state"]}
    actual_allocations = {(r["run_id"], r["step_key"]): r for r in tables["branch_allocations"]}
    actual_results = {
        (r["run_id"], r["hypothesis_id"], r["report_digest"], r["passed"])
        for r in tables["branch_results"]
    }
    actual_progress = {
        (r["run_id"], r["task_id"]): hashlib.sha256(r["state_json"].encode()).hexdigest()
        for r in tables["progress_guards"]
    }
    if (
        nodes != actual_nodes
        or policies != actual_policies
        or allocations != actual_allocations
        or results != actual_results
        or progress != actual_progress
    ):
        raise IntegrityError("Branch or progress projection disagrees with evidence")
