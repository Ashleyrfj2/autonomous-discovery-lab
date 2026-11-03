"""Audit commercial provenance, authority records and current-profile projections."""

import json
from typing import Any

from autodiscover.evidence.artifacts import Artifacts, IntegrityError


def verify_market_projections(
    events: list[dict[str, Any]], tables: dict[str, list[dict[str, Any]]], artifacts: Artifacts
) -> None:
    opportunities, current, evidence, reviews = {}, {}, {}, {}
    review_sequence = 0
    for event in events:
        payload = json.loads(event["payload_json"])
        run = event["run_id"]
        kind = event["kind"]
        if kind == "market_opportunity_saved":
            identifier = payload["opportunity_id"]
            opportunities[identifier] = {
                "id": identifier,
                "run_id": run,
                "candidate_id": payload["candidate_id"],
                "artifact_digest": payload["artifact_digest"],
            }
            current[(run, payload["candidate_id"])] = {
                "run_id": run,
                "candidate_id": payload["candidate_id"],
                "opportunity_id": identifier,
            }
            record = artifacts.get_json(payload["artifact_digest"])
            if (
                identifier != "opportunity-" + payload["artifact_digest"]
                or record["run_id"] != run
                or record["opportunity"]["candidate_id"] != payload["candidate_id"]
            ):
                raise IntegrityError("Commercial opportunity content disagrees with evidence")
        elif kind == "market_evidence_added":
            identifier = payload["evidence_id"]
            evidence[identifier] = {
                "id": identifier,
                "opportunity_id": payload["opportunity_id"],
                "artifact_digest": payload["artifact_digest"],
                "origin": payload["origin"],
            }
            record = artifacts.get_json(payload["artifact_digest"])
            if (
                identifier != "market-evidence-" + payload["artifact_digest"]
                or record["evidence"]["origin"] != payload["origin"]
                or record["opportunity_id"] != payload["opportunity_id"]
            ):
                raise IntegrityError("Commercial evidence origin/ownership changed")
        elif kind == "market_review_recorded":
            review_sequence += 1
            identifier = payload["review_id"]
            reviews[identifier] = {
                "seq": review_sequence,
                "id": identifier,
                "evidence_id": payload["evidence_id"],
                "artifact_digest": payload["artifact_digest"],
            }
            record = artifacts.get_json(payload["artifact_digest"])
            if (
                identifier != "market-review-" + payload["artifact_digest"]
                or record["evidence_id"] != payload["evidence_id"]
                or record["actor_kind"] != "human"
                or payload["actor_kind"] != "human"
                or record["review"]["accepted"] != payload["accepted"]
                or record["review"]["facts"] != payload["facts"]
            ):
                raise IntegrityError("Commercial review authority/content changed")
    actual_opportunities = {r["id"]: r for r in tables["market_opportunities"]}
    actual_current = {(r["run_id"], r["candidate_id"]): r for r in tables["market_current"]}
    actual_evidence = {r["id"]: r for r in tables["market_evidence"]}
    actual_reviews = {r["id"]: r for r in tables["market_reviews"]}
    if (
        opportunities != actual_opportunities
        or current != actual_current
        or evidence != actual_evidence
        or reviews != actual_reviews
    ):
        raise IntegrityError("Commercial projection disagrees with evidence")
