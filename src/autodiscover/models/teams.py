"""Opt-in separated model roles; model criticism is not scientific verification."""

from sqlite3 import Connection
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.evidence.artifacts import Artifacts
from autodiscover.hypotheses.proposals import ResearchProposal, propose
from autodiscover.models.contracts import GenerationRequest
from autodiscover.models.providers import HTTPProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical
from autodiscover.research.catalog import Catalog
from autodiscover.security.redaction import contains_credential, sanitize


class CriticalReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    assumptions_at_risk: list[str] = Field(min_length=1, max_length=8)
    methodological_flaws: list[str] = Field(min_length=1, max_length=8)
    alternative_explanations: list[str] = Field(min_length=1, max_length=8)
    disconfirming_experiment: str = Field(min_length=20, max_length=2000)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    status: Literal["unverified_critique"] = "unverified_critique"
    novelty_verified: Literal[False] = False
    technical_verified: Literal[False] = False
    commercial_validated: Literal[False] = False


class CandidateReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    role: Literal["RESEARCH_PROPOSALS", "EXPLORATORY"]
    proposal: ResearchProposal
    critique: CriticalReview
    scientific_verdict: Literal["not_evaluated"] = "not_evaluated"


class ResearchReviewPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    run_id: str
    source_ids: list[str] = Field(max_length=5)
    models_not_independent_scientific_oracles: Literal[True] = True
    candidate_reviews: list[CandidateReview] = Field(min_length=2, max_length=2)
    novelty: Literal["unknown"] = "unknown"
    commercial_validation: Literal["unvalidated"] = "unvalidated"
    next_step: str = "Independent method review and preregistered experiment required"


def _check_sources(db: Connection, run_id: str, sources: list[str]) -> None:
    for identifier in sources:
        row = db.execute(
            "SELECT n.valid FROM research_nodes n JOIN run_sources r ON n.id=r.source_id "
            "WHERE r.run_id=? AND n.id=? AND n.kind='source'",
            (run_id, identifier),
        ).fetchone()
        if row is None or not row["valid"]:
            raise ValueError("Research source invalidated during model review")


class RoleSeparationError(ValueError):
    pass


class ResearchTeam:
    """Three distinct routes: candidate generation, exploration and criticism.

    A separate model is not an independent scientific evaluator. This module never
    invokes experiment execution, market approval or novelty-state transitions.
    """

    ROLES = ("RESEARCH_PROPOSALS", "EXPLORATORY", "CRITIQUE")

    def __init__(self, router: Router):
        identities: dict[str, set[tuple[str, str]]] = {}
        for role in self.ROLES:
            providers = router.routes.get(role)
            if not providers:
                raise RoleSeparationError("All three research model roles must be configured")
            identities[role] = {
                (provider.config.kind, provider.config.model)
                if isinstance(provider, HTTPProvider)
                else (provider.name, provider.model)
                for provider in providers
            }
        for index, first in enumerate(self.ROLES):
            for second in self.ROLES[index + 1 :]:
                if identities[first] & identities[second]:
                    raise RoleSeparationError(
                        "Research roles must use distinct provider/model pairs"
                    )
        self.router = router
        self.requires_public_sources = any(
            provider.is_live for role in self.ROLES for provider in router.routes[role]
        )

    def _critique(
        self,
        run_id: str,
        proposal: ResearchProposal,
        *,
        source_ids: list[str],
        source_context: str,
        key: str,
    ) -> CriticalReview:
        request = GenerationRequest(
            prompt=canonical(
                {
                    "task": "Give one short item per risk, flaw and alternative explanation. "
                    "Suggest one falsifying test. Cite a permitted source when supplied. "
                    "Do not assert novelty, technical validation or commercial demand.",
                    "hypothesis": proposal.model_dump(mode="json"),
                    "source_context_untrusted": source_context,
                    "permitted_source_ids": source_ids,
                }
            )
        )
        if contains_credential(request.prompt):
            raise ValueError("Refusing to send recognizable credentials to model roles")
        review, _ = self.router.generate_structured(
            run_id, "CRITIQUE", request, CriticalReview, key=key
        )
        if not set(review.source_ids).issubset(source_ids):
            raise ValueError("Critic referenced unavailable sources")
        if source_ids and not review.source_ids:
            raise ValueError("Critic must cite at least one available source")
        return review

    def investigate(
        self,
        run_id: str,
        *,
        topic: str,
        domains: list[str],
        key: str,
    ) -> dict[str, object]:
        if not key or len(key) > 100:
            raise ValueError("Bounded stable research key required")
        catalog = Catalog(self.router.store)
        sources = catalog.sources(run_id)[:5]
        if self.requires_public_sources and not sources:
            raise ValueError("Live research roles require verified public sources")
        context = (
            catalog.context(run_id, excerpt_characters=450, public_source_ids=sources)
            if sources
            else "No external research sources"
        )
        if contains_credential(canonical({"topic": topic, "domains": domains, "context": context})):
            raise ValueError("Refusing to send recognizable credentials to model roles")
        candidates = []
        for role in ("RESEARCH_PROPOSALS", "EXPLORATORY"):
            with self.router.store.connection() as db:
                _check_sources(db, run_id, sources)
            proposal = propose(
                self.router,
                run_id,
                topic=topic,
                domains=domains,
                source_context=context,
                available_source_ids=sources,
                key=f"{key}:{role}:propose",
                stage=role,
            )
            with self.router.store.connection() as db:
                _check_sources(db, run_id, sources)
            critic = self._critique(
                run_id,
                proposal,
                source_ids=sources,
                source_context=context,
                key=f"{key}:{role}:critique",
            )
            candidates.append(CandidateReview(role=role, proposal=proposal, critique=critic))
        packet = ResearchReviewPacket(
            run_id=run_id, source_ids=sources, candidate_reviews=candidates
        )
        # Recheck sources under the event writer lock after all potentially slow model calls.
        body = sanitize(packet.model_dump(mode="json"))
        with self.router.store.connection(write=True) as db:
            _check_sources(db, run_id, sources)
            digest = Artifacts(self.router.store.root / "artifacts").put_json(body)
            previous = db.execute(
                "SELECT 1 FROM events WHERE run_id=? AND kind='research_team_reviewed' "
                "AND json_extract(payload_json,'$.artifact_digest')=?",
                (run_id, digest),
            ).fetchone()
            if previous is None:
                self.router.store._event(
                    db,
                    run_id,
                    "research_team_reviewed",
                    {"artifact_digest": digest, "source_ids": sources},
                )
        return {**body, "artifact_digest": digest}
