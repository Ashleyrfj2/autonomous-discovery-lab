"""Chain verification and no-overwrite exports for independently retained snapshots."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.evidence.branches import verify_branch_projections
from autodiscover.evidence.jobs import verify_job_projections
from autodiscover.evidence.markets import verify_market_projections
from autodiscover.evidence.runs import verify_run_projections
from autodiscover.evidence.scheduling import verify_queue_projections
from autodiscover.orchestrator.durability import canonical, now
from autodiscover.orchestrator.store import Store


def verify_events(
    events: list[dict[str, Any]], anchor: dict[str, Any] | None = None
) -> dict[str, Any]:
    previous, last_seq = "0" * 64, 0
    seen_anchor = anchor is None or (anchor.get("seq") == 0 and anchor.get("hash") == previous)
    for event in events:
        if event["seq"] != last_seq + 1 or event["previous_hash"] != previous:
            raise IntegrityError("Evidence sequence/parent mismatch")
        body = {
            k: event[k]
            for k in ("id", "run_id", "kind", "payload_json", "timestamp", "previous_hash")
        }
        digest = hashlib.sha256(canonical(body).encode()).hexdigest()
        if digest != event["hash"]:
            raise IntegrityError("Evidence content hash mismatch")
        if anchor and event["seq"] == anchor["seq"]:
            if digest != anchor["hash"]:
                raise IntegrityError("Independent anchor mismatch")
            seen_anchor = True
        previous, last_seq = digest, event["seq"]
    if not seen_anchor:
        raise IntegrityError("Evidence truncated before retained anchor")
    return {
        "seq": last_seq,
        "hash": previous,
        "verified_events": len(events),
        "trust_limit": "Tamper-evident relative to retained anchor; not immutable",
    }


def verify_chain(store: Store, anchor: dict[str, Any] | None = None) -> dict[str, Any]:
    with store.connection() as db:
        if not db.in_transaction:
            db.execute("BEGIN")
        events = [dict(r) for r in db.execute("SELECT * FROM events ORDER BY seq")]
        steps = [dict(r) for r in db.execute("SELECT * FROM steps ORDER BY rowid")]
        nodes = [dict(r) for r in db.execute("SELECT * FROM research_nodes")]
        runs = [dict(r) for r in db.execute("SELECT * FROM runs")]
        queries = {
            "hypotheses": "SELECT * FROM hypotheses",
            "director_state": "SELECT * FROM director_state",
            "branch_allocations": "SELECT * FROM branch_allocations",
            "branch_results": "SELECT * FROM branch_results",
            "progress_guards": "SELECT * FROM progress_guards",
            "market_opportunities": "SELECT * FROM market_opportunities",
            "market_current": "SELECT * FROM market_current",
            "market_evidence": "SELECT * FROM market_evidence",
            "market_reviews": "SELECT * FROM market_reviews",
            "experiment_jobs": "SELECT * FROM experiment_jobs",
            "work_queue": "SELECT * FROM work_queue",
        }
        branch_tables = {
            name: [dict(r) for r in db.execute(query)] for name, query in queries.items()
        }
    checked = verify_events(events, anchor)
    checked.update(verify_run_projections(events, runs))
    by_id = {event["id"]: event for event in events}
    for step in steps:
        result = json.loads(step["result_json"])
        event = by_id.get(result.get("event_id"))
        if event is None or event["run_id"] != step["run_id"] or event["kind"] != "stage_completed":
            raise IntegrityError("Step missing authoritative evidence event")
        payload = json.loads(event["payload_json"])
        if (
            payload["output"] != json.loads(step["output_json"])
            or payload["stage"] != step["stage"]
            or result["version"] != payload["version"] + 1
        ):
            raise IntegrityError("Step projection disagrees with evidence")
    authoritative_steps = {event["id"] for event in events if event["kind"] == "stage_completed"}
    if authoritative_steps != {json.loads(step["result_json"])["event_id"] for step in steps}:
        raise IntegrityError("Completed step projection missing evidence")
    artifacts = Artifacts(store.root / "artifacts", read_only=True)
    validity: dict[str, bool] = {}
    for event in events:
        payload = json.loads(event["payload_json"])
        if event["kind"] in (
            "research_team_reviewed", "discovery_registered", "discovery_checkpoint",
            "discovery_finished", "discovery_commercial_reviewed",
        ):
            artifacts.get(payload["artifact_digest"])
        elif event["kind"] == "source_registered":
            validity.setdefault(payload["source_id"], True)
        elif event["kind"] == "claim_registered":
            validity[payload["claim_id"]] = True
        elif event["kind"] in ("evidence_invalidated", "source_updated"):
            for identifier in payload["affected"]:
                validity[identifier] = False
    for node in nodes:
        if node["id"] != node["kind"] + "-" + node["artifact_digest"] or bool(
            node["valid"]
        ) != validity.get(node["id"]):
            raise IntegrityError("Research validity projection disagrees with evidence")
    if set(validity) != {node["id"] for node in nodes}:
        raise IntegrityError("Research node projection missing evidence")
    verify_branch_projections(events, branch_tables)
    verify_market_projections(
        events, branch_tables, Artifacts(store.root / "artifacts", read_only=store.read_only)
    )
    verify_job_projections(
        events,
        branch_tables["experiment_jobs"],
        Artifacts(store.root / "artifacts", read_only=store.read_only),
    )
    verify_queue_projections(events, branch_tables["work_queue"])
    return checked


def export_snapshot(store: Store, destination: Path) -> dict[str, Any]:
    with store.connection() as db:
        events = [dict(r) for r in db.execute("SELECT * FROM events ORDER BY seq")]
    checked = verify_events(events)
    anchor = {"seq": checked["seq"], "hash": checked["hash"]}
    snapshot = {"schema_version": 1, "exported_at": now(), "anchor": anchor, "events": events}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL prevents races from overwriting a retained snapshot.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(canonical(snapshot) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        loaded = json.loads(destination.read_text())
        verify_events(loaded["events"], anchor)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return anchor
