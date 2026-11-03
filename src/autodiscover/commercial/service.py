"""Conservative commercial gates. No model or benchmark can validate external demand."""

import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from autodiscover.commercial.contracts import HumanReview, MarketEvidence, Opportunity
from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.orchestrator.durability import canonical, now
from autodiscover.orchestrator.store import Store
from autodiscover.research.catalog import Catalog
from autodiscover.research.retrieval import Fetched, SourceFetcher
from autodiscover.security.redaction import contains_credential


class CommercialError(ValueError):
    pass


class CommercialConflict(CommercialError):
    pass


class Market:
    def __init__(self, store: Store):
        self.store, self.artifacts = (
            store,
            Artifacts(store.root / "artifacts", read_only=store.read_only),
        )
        self.catalog = Catalog(store)

    def save(self, run_id: str, opportunity: Opportunity) -> str:
        with self.store.connection() as db:
            candidate = db.execute(
                "SELECT 1 FROM hypotheses WHERE id=? AND run_id=?",
                (opportunity.candidate_id, run_id),
            ).fetchone()
        if candidate is None:
            raise CommercialError("Opportunity must reference a real candidate in this run")
        for alternative in opportunity.current_alternatives + opportunity.competitors:
            for source in alternative.source_ids:
                self.catalog.source(source)
        profile = {"run_id": run_id, "opportunity": opportunity.model_dump(mode="json")}
        if contains_credential(canonical(profile)):
            raise CommercialError("Credential material is not permitted in market artifacts")
        digest = self.artifacts.put_json(profile)
        identifier = "opportunity-" + digest
        with self.store.connection(write=True) as db:
            db.execute(
                "INSERT OR IGNORE INTO market_opportunities VALUES(?,?,?,?)",
                (identifier, run_id, opportunity.candidate_id, digest),
            )
            db.execute(
                "INSERT INTO market_current VALUES(?,?,?) ON CONFLICT(run_id,candidate_id) "
                "DO UPDATE SET opportunity_id=excluded.opportunity_id",
                (run_id, opportunity.candidate_id, identifier),
            )
            self.store._event(
                db,
                run_id,
                "market_opportunity_saved",
                {
                    "opportunity_id": identifier,
                    "candidate_id": opportunity.candidate_id,
                    "artifact_digest": digest,
                },
            )
        return identifier

    def current(self, run_id: str, candidate_id: str) -> str | None:
        with self.store.connection() as db:
            row = db.execute(
                "SELECT opportunity_id FROM market_current WHERE run_id=? AND candidate_id=?",
                (run_id, candidate_id),
            ).fetchone()
        return row[0] if row else None

    def opportunity(self, identifier: str) -> tuple[str, Opportunity]:
        with self.store.connection() as db:
            row = db.execute(
                "SELECT * FROM market_opportunities WHERE id=?", (identifier,)
            ).fetchone()
        if row is None or identifier != "opportunity-" + row["artifact_digest"]:
            raise CommercialError("Opportunity missing or identity changed")
        record = self.artifacts.get_json(row["artifact_digest"])
        if record["run_id"] != row["run_id"]:
            raise IntegrityError("Commercial opportunity run ownership changed")
        opportunity = Opportunity.model_validate(record["opportunity"])
        if opportunity.candidate_id != row["candidate_id"]:
            raise IntegrityError("Commercial candidate ownership changed")
        return row["run_id"], opportunity

    def add_document(self, run_id: str, path: Path, *, title: str) -> str:
        if path.name.startswith(".env"):
            raise CommercialError("Environment files are not commercial evidence")
        if path.stat().st_size > 2000000:
            raise CommercialError("Operator document exceeds 2 MB")
        content = path.read_bytes()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise CommercialError("Only UTF-8 evidence documents are supported") from None
        if contains_credential(text):
            raise CommercialError("Credential material is not permitted in market artifacts")
        identifier = "urn:local-document:sha256:" + hashlib.sha256(content).hexdigest()
        fetched = Fetched(identifier, identifier, content, "text/plain", now(), "operator_document")
        return self.catalog.add(
            run_id, fetched, title=title, text=text, source_kind="primary_document"
        )

    def collect_source(self, run_id: str, url: str, *, title: str, fetcher: SourceFetcher) -> str:
        fetched = fetcher.fetch(url)
        if len(fetched.body) > 2000000:
            raise CommercialError("Market source exceeds 2 MB")
        text = fetched.body.decode("utf-8", errors="replace")
        if contains_credential(text):
            raise CommercialError("Credential material is not permitted in market artifacts")
        return self.catalog.add(
            run_id, fetched, title=title, text=text, source_kind="primary_document"
        )

    def _external_source(self, evidence: MarketEvidence) -> tuple[str, str]:
        if evidence.origin != "external" or evidence.source_id is None or evidence.quote is None:
            raise CommercialError("Synthetic/model/benchmark evidence cannot qualify as external")
        source, text = self.catalog.source(evidence.source_id)
        if (
            source.source_kind != "primary_document"
            or evidence.quote not in text
            or source.retrieval_provenance not in ("live_https", "operator_document")
        ):
            raise CommercialError("External demand needs an exact quote from a primary document")
        return source.raw_digest, source.url

    def add_evidence(self, opportunity_id: str, evidence: MarketEvidence) -> str:
        run_id, _opportunity = self.opportunity(opportunity_id)
        if evidence.origin == "external":
            self._external_source(evidence)
        record = {"opportunity_id": opportunity_id, "evidence": evidence.model_dump(mode="json")}
        if contains_credential(canonical(record)):
            raise CommercialError("Credential material is not permitted in market artifacts")
        digest = self.artifacts.put_json(record)
        identifier = "market-evidence-" + digest
        with self.store.connection(write=True) as db:
            count = db.execute(
                "SELECT COUNT(*) FROM market_evidence WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone()[0]
            if count >= 100:
                raise CommercialError("Commercial evidence record limit reached")
            existing = db.execute(
                "SELECT 1 FROM market_evidence WHERE id=?", (identifier,)
            ).fetchone()
            if existing is None:
                db.execute(
                    "INSERT INTO market_evidence VALUES(?,?,?,?)",
                    (identifier, opportunity_id, digest, evidence.origin),
                )
                self.store._event(
                    db,
                    run_id,
                    "market_evidence_added",
                    {
                        "evidence_id": identifier,
                        "opportunity_id": opportunity_id,
                        "artifact_digest": digest,
                        "origin": evidence.origin,
                    },
                )
        return identifier

    def evidence(self, identifier: str) -> tuple[str, MarketEvidence]:
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM market_evidence WHERE id=?", (identifier,)).fetchone()
        if row is None or identifier != "market-evidence-" + row["artifact_digest"]:
            raise CommercialError("Commercial evidence missing or identity changed")
        data = self.artifacts.get_json(row["artifact_digest"])
        if data["opportunity_id"] != row["opportunity_id"]:
            raise IntegrityError("Commercial evidence ownership changed")
        evidence = MarketEvidence.model_validate(data["evidence"])
        if evidence.origin != row["origin"]:
            raise IntegrityError("Commercial evidence origin changed")
        return row["opportunity_id"], evidence

    def review(
        self,
        evidence_id: str,
        review: HumanReview,
        *,
        actor_kind: Literal["human", "model", "system"] = "system",
        request_id: str | None = None,
        expected_cursor: int | None = None,
    ) -> str:
        # Trusted operator boundary only; request metadata never establishes human authority.
        from autodiscover.evidence.chain import verify_chain

        if actor_kind != "human":
            raise PermissionError(
                "Only explicit operator review can attest external commercial facts"
            )
        if (request_id is None) != (expected_cursor is None):
            raise CommercialError("Review commands require identity and cursor together")
        if contains_credential(canonical(review.model_dump(mode="json"))):
            raise CommercialError("Credential material is not permitted in review records")
        fingerprint = hashlib.sha256(
            canonical(
                {
                    "evidence_id": evidence_id,
                    "review": review.model_dump(mode="json"),
                    "expected_cursor": expected_cursor,
                }
            ).encode()
        ).hexdigest()
        with self.store.connection(write=True) as db:
            checked = verify_chain(self.store)
            opportunity_id, evidence = self.evidence(evidence_id)
            run_id, _ = self.opportunity(opportunity_id)
            if request_id is not None:
                old = db.execute(
                    "SELECT payload_json FROM events WHERE run_id=? "
                    "AND kind='market_review_recorded' "
                    "AND json_extract(payload_json,'$.command.id')=?",
                    (run_id, request_id),
                ).fetchone()
                if old:
                    payload = json.loads(old[0])
                    if payload["command"]["fingerprint"] != fingerprint:
                        raise CommercialConflict("Review identity reused with different inputs")
                    return payload["review_id"]
                if checked["seq"] != expected_cursor:
                    raise CommercialConflict("Evidence changed; refresh the review context")
            # Source validation and event commit share the writer lock.
            actual_digest, _url = self._external_source(evidence)
            if review.source_digest != actual_digest:
                raise CommercialConflict("Review refers to different source content")
            record = {
                "evidence_id": evidence_id,
                "actor_kind": "human",
                "review_event_id": str(uuid4()),
                "reviewed_at": now(),
                "review": review.model_dump(mode="json"),
            }
            digest = self.artifacts.put_json(record)
            identifier = "market-review-" + digest
            db.execute(
                "INSERT INTO market_reviews(id,evidence_id,artifact_digest) VALUES(?,?,?)",
                (identifier, evidence_id, digest),
            )
            payload: dict[str, Any] = {
                "review_id": identifier,
                "evidence_id": evidence_id,
                "artifact_digest": digest,
                "accepted": review.accepted,
                "facts": review.facts,
                "actor_kind": "human",
            }
            if request_id is not None:
                payload["command"] = {"id": request_id, "fingerprint": fingerprint}
            self.store._event(db, run_id, "market_review_recorded", payload)
        return identifier

    def assess(self, opportunity_id: str) -> dict[str, Any]:
        from autodiscover.evidence.chain import verify_chain

        verify_chain(self.store)
        run_id, opportunity = self.opportunity(opportunity_id)
        with self.store.connection() as db:
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM market_evidence WHERE opportunity_id=? ORDER BY id",
                    (opportunity_id,),
                )
            ]
        accepted: list[tuple[str, MarketEvidence, set[str]]] = []
        rejected = []
        for identifier in ids:
            _owner, evidence = self.evidence(identifier)
            try:
                source_digest, _url = self._external_source(evidence)
            except (CommercialError, IntegrityError) as error:
                rejected.append({"evidence_id": identifier, "reason": str(error)})
                continue
            with self.store.connection() as db:
                row = db.execute(
                    "SELECT * FROM market_reviews WHERE evidence_id=? ORDER BY seq DESC LIMIT 1",
                    (identifier,),
                ).fetchone()
            if row is None:
                rejected.append({"evidence_id": identifier, "reason": "Human review required"})
                continue
            if row["id"] != "market-review-" + row["artifact_digest"]:
                raise IntegrityError("Commercial review identity changed")
            record = self.artifacts.get_json(row["artifact_digest"])
            review = HumanReview.model_validate(record["review"])
            if (
                record["evidence_id"] != identifier
                or record["actor_kind"] != "human"
                or not review.accepted
                or review.source_digest != source_digest
            ):
                rejected.append(
                    {"evidence_id": identifier, "reason": "Review rejected, revoked or stale"}
                )
                continue
            accepted.append((identifier, evidence, set(review.facts)))
        problem = any("real_problem" in facts for _, _, facts in accepted)
        direct = any(
            e.kind
            in (
                "user_interview",
                "buyer_interview",
                "pilot_commitment",
                "adoption",
                "payment",
                "strong_commercial_commitment",
            )
            and (
                (e.subject_role == "user" and "direct_user" in facts)
                or (e.subject_role == "buyer" and "direct_buyer" in facts)
            )
            for _, e, facts in accepted
        )
        adoption = any(
            e.kind in ("adoption", "pilot_commitment")
            and "serious_adoption" in facts
            and e.subject_role in ("user", "buyer")
            for _, e, facts in accepted
        )

        def identified(role: str | None) -> bool:
            return bool(
                role
                and len(role.strip()) >= 3
                and role.casefold().strip()
                not in {"unknown", "unvalidated", "hypothetical", "tbd", "none"}
            )

        buyer_identified = identified(opportunity.economic_buyer) and identified(
            opportunity.target_user
        )
        payment = any(
            e.kind == "payment"
            and "payment_received" in facts
            and e.amount is not None
            and e.amount > 0
            and e.currency is not None
            and e.subject_role == "buyer"
            and buyer_identified
            and e.buyer_role == opportunity.economic_buyer
            for _, e, facts in accepted
        )
        strong = any(
            e.kind == "strong_commercial_commitment"
            and "comparable_commercial_commitment" in facts
            and e.subject_role == "buyer"
            and buyer_identified
            and e.buyer_role == opportunity.economic_buyer
            for _, e, facts in accepted
        )
        level = 0
        if problem:
            level = 1
            if direct:
                level = 2
            if adoption:
                level = 3
            if payment or strong:
                level = 4
        missing = []
        for field in ("target_user", "economic_buyer", "buyer_reachability"):
            if not getattr(opportunity, field):
                missing.append(field)
        comparisons = []
        for alternative in opportunity.current_alternatives + opportunity.competitors:
            valid_sources = []
            for source in alternative.source_ids:
                try:
                    _source_record, source_text = self.catalog.source(source)
                    if alternative.name.casefold() in source_text.casefold():
                        valid_sources.append(source)
                except IntegrityError:
                    pass
            comparisons.append(
                {
                    "name": alternative.name,
                    "status": "source name mention; not a validated competitive advantage"
                    if valid_sources
                    else "hypothetical/unvalidated",
                    "source_ids": valid_sources,
                }
            )
        return {
            "schema_version": 1,
            "run_id": run_id,
            "opportunity_id": opportunity_id,
            "candidate_id": opportunity.candidate_id,
            "level": level,
            "validated": level == 4,
            "evidence_ids": [i for i, _, _ in accepted],
            "rejected_evidence": rejected,
            "missing_information": missing,
            "competition": comparisons,
            "problem_severity": opportunity.problem_severity,
            "adoption_constraints": opportunity.adoption_constraints,
            "classification": "commercial commitment supported by reviewed external records"
            if level == 4
            else "commercial opportunity unvalidated",
            "limitations": "Levels reflect source-bound human-attested evidence; "
            "document authenticity "
            "and real payment are not automatically verified. No revenue forecast, "
            "novelty or technical result is inferred.",
        }
