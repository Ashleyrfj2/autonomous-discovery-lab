"""Shared report aggregation. No writes, initialization, migrations or workflow controls."""

import json
from typing import Any

from autodiscover.commercial.service import Market
from autodiscover.evidence.chain import verify_chain
from autodiscover.hypotheses.director import Director
from autodiscover.orchestrator.contracts import Stage
from autodiscover.orchestrator.jobs import Jobs
from autodiscover.orchestrator.store import Store
from autodiscover.research.catalog import Catalog
from autodiscover.security.budget import Budget


def build_report(store: Store, run_id: str) -> dict[str, Any]:
    checked = verify_chain(store)
    row = store.get_run(run_id)
    if store.is_discovery(run_id):
        from autodiscover.orchestrator.contracts import RunStatus
        from autodiscover.research.discovery import replay

        report = {
            "run_id": run_id,
            "status": row["status"],
            "stage": "DISCOVERY",
            "usage": Budget(store).totals(run_id),
            "evidence": checked,
        }
        if row["status"] == RunStatus.COMPLETED:
            digest, packet = replay(store, run_id)
            report.update(discovery=packet.model_dump(mode="json"), artifact_digest=digest)
        return report
    assessment = None
    market = None
    for step in store.outputs(run_id):
        if step["stage"] == Stage.ASSESS:
            assessment = json.loads(step["output_json"])
        if step["stage"] == Stage.VALIDATE_MARKET:
            market = json.loads(step["output_json"])
    if market and market.get("opportunity_id"):
        service = Market(store)
        _run, profile = service.opportunity(market["opportunity_id"])
        current_id = service.current(run_id, profile.candidate_id) or market["opportunity_id"]
        current = service.assess(current_id)
        market = {
            **market,
            "recorded_opportunity_id": market["opportunity_id"],
            "opportunity_id": current_id,
            "recorded_level": market["level"],
            "recorded_validated": market["validated"],
            "level": current["level"],
            "validated": current["validated"],
            "evidence_ids": current["evidence_ids"],
            "classification": current["classification"],
            "missing_information": current["missing_information"],
            "limitations": current["limitations"],
        }
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "status": row["status"],
        "stage": row["stage"],
        "completed_steps": len(store.outputs(run_id)),
        "search": Director(store).tree(run_id),
        "jobs": Jobs(store).status(run_id),
        "assessment": assessment,
        "assessment_scope": "Last completed hypothesis assessment; see per-branch results",
        "commercial": market,
        "usage": Budget(store).totals(run_id),
        "evidence": checked,
        "research": {
            "source_ids": Catalog(store).sources(run_id),
            "novelty": "unknown",
            "coverage_exhaustive": False,
        },
        "mode": (
            "trusted reviewed encoding/allocation families; source retrieval opt-in; "
            "live providers unverified"
        ),
    }
    return report
