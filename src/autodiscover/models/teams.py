"""Opt-in separated model roles; model criticism is not scientific verification."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.evidence.artifacts import Artifacts
from autodiscover.hypotheses.proposals import ResearchProposal, propose
from autodiscover.models.contracts import GenerationRequest
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical
from autodiscover.research.catalog import Catalog
from autodiscover.security.redaction import contains_credential


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
            identities[role] = {(provider.name, provider.model) for provider in providers}
        for index, first in enumerate(self.ROLES):
            for second in self.ROLES[index + 1 :]:
                if identities[first] & identities[second]:
                    raise RoleSeparationError(
                        "Research roles must use distinct provider/model pairs"
                    )
        self.router = router

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
                    "task": "Challenge this proposal; find confounds and competing explanations. "
                    "Suggest a falsifying test. You are a critic, not a scientific verifier. "
                    "Do not assert novelty, technical validation or commercial demand.",
                    "hypothesis": proposal.model_dump(mode="json"),
                    "source_context_untrusted": source_context[:10000],
                    "permitted_source_ids": source_ids,
                }
            )
        )
        review, _ = self.router.generate_structured(
            run_id, "CRITIQUE", request, CriticalReview, key=key
        )
        if not set(review.source_ids).issubset(source_ids):
            raise ValueError("Critic referenced unavailable sources")
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
        for identifier in sources:
            source, _text = catalog.source(identifier)
            if source.retrieval_provenance != "live_https":
                raise ValueError(
                    "Private, mock or unverified sources require separate sharing policy"
                )
        context = catalog.context(run_id) if sources else "No external research sources"
        if contains_credential(canonical({"topic": topic, "domains": domains, "context": context})):
            raise ValueError("Refusing to send recognizable credentials to model roles")
        candidates = []
        for role in ("RESEARCH_PROPOSALS", "EXPLORATORY"):
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
            critic = self._critique(
                run_id,
                proposal,
                source_ids=sources,
                source_context=context,
                key=f"{key}:{role}:critique",
            )
            candidates.append(
                {
                    "role": role,
                    "proposal": proposal.model_dump(mode="json"),
                    "critique": critic.model_dump(mode="json"),
                    "scientific_verdict": "not_evaluated",
                }
            )
        packet: dict[str, object] = {
            "schema_version": 1,
            "run_id": run_id,
            "source_ids": sources,
            "models_not_independent_scientific_oracles": True,
            "candidate_reviews": candidates,
            "novelty": "unknown",
            "commercial_validation": "unvalidated",
            "next_step": "Independent method review and preregistered experiment required",
        }
        # Persist a content-addressed, non-authoritative research packet. Recheck
        # sources under the event writer lock after all potentially slow model calls.
        digest = Artifacts(self.router.store.root / "artifacts").put_json(packet)
        with self.router.store.connection(write=True) as db:
            for identifier in sources:
                row = db.execute(
                    "SELECT valid FROM research_nodes WHERE id=? AND kind='source'",
                    (identifier,),
                ).fetchone()
                if row is None or not row["valid"]:
                    raise ValueError("Research source invalidated during model review")
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
        return {**packet, "artifact_digest": digest}
