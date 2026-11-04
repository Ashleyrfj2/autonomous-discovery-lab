"""Cross-domain proposals that remain theoretical until a reviewed execution adapter exists."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autodiscover.models.contracts import GenerationRequest
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical


class ResearchProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    question: str = Field(min_length=10, max_length=1000)
    domain: str = Field(min_length=2, max_length=100)
    connection_domain: str = Field(min_length=2, max_length=100)
    prediction: str = Field(min_length=10, max_length=2000)
    metric: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,63}$")
    unit: str = Field(min_length=1, max_length=100)
    comparator: str = Field(min_length=3, max_length=500)
    direction: Literal["increase", "decrease"]
    minimum_effect: float = Field(gt=0, allow_inf_nan=False)
    measurement_protocol: str = Field(min_length=20, max_length=2000)
    experiment_family: Literal["theoretical"] = "theoretical"
    parent_id: str | None = None
    revision_reason: str | None = None
    source_ids: list[str] = []

    @model_validator(mode="after")
    def revision_requires_reason(self) -> "ResearchProposal":
        if self.parent_id and not self.revision_reason:
            raise ValueError("Revision requires evidence-based rationale")
        return self

    @property
    def identity(self) -> str:
        body = {
            key: value
            for key, value in self.model_dump(mode="json").items()
            if key not in {"parent_id", "revision_reason", "source_ids"}
        }
        return hashlib.sha256(canonical(body).encode()).hexdigest()


def propose(
    router: Router,
    run_id: str,
    *,
    topic: str,
    domains: list[str],
    source_context: str,
    available_source_ids: list[str],
    key: str,
    stage: Literal["RESEARCH_PROPOSALS", "EXPLORATORY"] = "RESEARCH_PROPOSALS",
    max_output_tokens: int = 512,
) -> ResearchProposal:
    request = GenerationRequest(
        max_output_tokens=max_output_tokens,
        prompt=canonical(
            {
                "task": "Return one falsifiable theoretical cross-domain hypothesis. "
                "Keep each text field to one short sentence. Give a quantitative effect, "
                "units, comparator and measurement protocol. Set parent_id and revision_reason "
                "to null. Cite a permitted source when supplied. "
                "Do not assert novelty, verification or demand.",
                "topic": topic,
                "eligible_domains": domains,
                "untrusted_source_data": source_context,
                "permitted_source_ids": available_source_ids,
            }
        )
    )
    proposal, _ = router.generate_structured(
        run_id, stage, request, ResearchProposal, key=key
    )
    if not set(proposal.source_ids).issubset(available_source_ids):
        raise ValueError("Proposal references unavailable sources")
    if available_source_ids and not proposal.source_ids:
        raise ValueError("Proposal must cite at least one available source")
    return proposal
