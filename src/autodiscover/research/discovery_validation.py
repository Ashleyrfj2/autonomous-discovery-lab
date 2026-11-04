"""Independent commercial observations for completed discovery candidates."""

from decimal import Decimal
from typing import Literal

from pydantic import Field

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store
from autodiscover.research.catalog import Catalog
from autodiscover.research.discovery import replay
from autodiscover.research.discovery_contracts import Citation, Record
from autodiscover.security.redaction import contains_credential


class CommercialObservation(Record):
    citation: Citation
    kind: Literal["problem", "spending", "direct_buyer_or_pilot", "paid_commitment"]
    buyer_role: str | None = Field(default=None, min_length=3, max_length=200)
    amount: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    interpretation: str = Field(min_length=15, max_length=500)


class CommercialReview(Record):
    observations: list[CommercialObservation] = Field(min_length=1, max_length=12)


def record_commercial_review(
    store: Store,
    run_id: str,
    direction: int,
    review: CommercialReview,
    *,
    operator_attested: bool,
) -> dict:
    """Record an explicit local human assessment of exact independent evidence."""
    if not operator_attested:
        raise ValueError("Commercial observations require independent operator attestation")
    packet_digest, report = replay(store, run_id)
    candidate = next((c for c in report.candidates if c.direction == direction), None)
    if candidate is None:
        raise ValueError("Unknown candidate direction")
    buyer = (candidate.revised or candidate.original).economic_buyer.casefold().strip()
    catalog = Catalog(store)
    owned = set(catalog.sources(run_id))
    verified = set()
    for item in review.observations:
        if contains_credential(canonical(item.model_dump(mode="json"))):
            raise ValueError("Commercial observation contains recognizable credentials")
        identifier = item.citation.source_id
        if identifier not in owned:
            raise ValueError("Commercial evidence must belong to the discovery run")
        source, text = catalog.source(identifier)
        if (
            source.retrieval_provenance not in {"live_https", "operator_document"}
            or source.source_kind != "primary_document"
            or item.citation.quote not in text
        ):
            raise ValueError("Commercial evidence requires an exact quote from a primary document")
        if item.kind in {"direct_buyer_or_pilot", "paid_commitment"}:
            if not item.buyer_role or item.buyer_role.casefold().strip() != buyer:
                raise ValueError("Buyer validation must identify the candidate's economic buyer")
        if item.kind == "paid_commitment" and (item.amount is None or item.currency is None):
            raise ValueError("A paid commitment requires a positive documented amount and currency")
        verified.add(item.kind)
    ranks = {"problem": 1, "spending": 2, "direct_buyer_or_pilot": 3, "paid_commitment": 4}
    level = max(ranks[kind] for kind in verified) if "problem" in verified else 0
    packet = {
        "run_id": run_id,
        "discovery_digest": packet_digest,
        "direction": direction,
        "reviewer": "local_operator",
        "commercial_level": level,
        "review": review.model_dump(
            mode="json",
        ),
    }
    digest = catalog.artifacts.put_json(packet)
    with store.connection(write=True) as db:
        for item in review.observations:
            current = db.execute(
                "SELECT valid FROM research_nodes WHERE id=?",
                (item.citation.source_id,),
            ).fetchone()
            if current is None or not current[0]:
                raise IntegrityError("Commercial evidence invalidated before review commit")
        exists = db.execute(
            "SELECT 1 FROM events WHERE run_id=? AND kind='discovery_commercial_reviewed' "
            "AND json_extract(payload_json,'$.artifact_digest')=?",
            (run_id, digest),
        ).fetchone()
        if exists is None:
            store._event(db, run_id, "discovery_commercial_reviewed", {"artifact_digest": digest})
    return {"artifact_digest": digest, **packet}
