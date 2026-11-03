"""Versioned lifecycle envelopes. Stage outputs are validated before state can move."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Stage(StrEnum):
    DISCOVER = "DISCOVER"
    RESEARCH = "RESEARCH"
    HYPOTHESIZE = "HYPOTHESIZE"
    PRIORITIZE = "PRIORITIZE"
    DESIGN = "DESIGN"
    PREFLIGHT = "PREFLIGHT"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REPLICATE = "REPLICATE"
    ASSESS = "ASSESS"
    VALIDATE_MARKET = "VALIDATE_MARKET"
    DECIDE = "DECIDE"


class RunStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1


class DiscoverResult(Contract):
    questions: list[str] = Field(min_length=1, max_length=100)


class ResearchResult(Contract):
    source_ids: list[str]
    coverage_limitations: str = Field(min_length=1)


class HypothesizeResult(Contract):
    hypothesis_ids: list[str] = Field(min_length=1, max_length=100)


class PrioritizeResult(Contract):
    selected_ids: list[str] = Field(min_length=1, max_length=100)


class DesignResult(Contract):
    plan_id: str = Field(min_length=1)
    plan_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class PreflightResult(DesignResult):
    authorized: Literal[True]


class ExecuteResult(Contract):
    artifact_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    plan_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)


class VerifyResult(Contract):
    passed: bool
    report_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReplicateResult(Contract):
    passed: bool
    report_digests: list[str] = Field(min_length=2)


class AssessResult(Contract):
    hypothesis_id: str | None = None
    technical_success: bool
    novelty: Literal["unknown", "supported", "not_new"]
    novelty_source_ids: list[str] = []
    limitations: str = Field(min_length=1)

    @model_validator(mode="after")
    def novelty_requires_sources(self) -> "AssessResult":
        if self.novelty == "supported" and not self.novelty_source_ids:
            raise ValueError("Novelty requires actual prior-art evidence and assessment")
        return self


class MarketResult(Contract):
    level: int = Field(ge=0, le=4)
    evidence_ids: list[str]
    validated: bool

    @model_validator(mode="after")
    def evidence_gate(self) -> "MarketResult":
        if (self.level > 0 or self.validated) and not self.evidence_ids:
            raise ValueError("External market evidence required")
        if self.validated and self.level < 4:
            raise ValueError("Commercial success requires level 4 evidence")
        return self


class DecideResult(Contract):
    decision: Literal["stop", "revise", "explore"]
    rationale: str = Field(min_length=1)


OUTPUTS: dict[Stage, type[Contract]] = {
    Stage.DISCOVER: DiscoverResult,
    Stage.RESEARCH: ResearchResult,
    Stage.HYPOTHESIZE: HypothesizeResult,
    Stage.PRIORITIZE: PrioritizeResult,
    Stage.DESIGN: DesignResult,
    Stage.PREFLIGHT: PreflightResult,
    Stage.EXECUTE: ExecuteResult,
    Stage.VERIFY: VerifyResult,
    Stage.REPLICATE: ReplicateResult,
    Stage.ASSESS: AssessResult,
    Stage.VALIDATE_MARKET: MarketResult,
    Stage.DECIDE: DecideResult,
}
STAGES = list(Stage)
BACKWARD: dict[Stage, set[Stage]] = {
    Stage.RESEARCH: {Stage.DISCOVER},
    Stage.HYPOTHESIZE: {Stage.RESEARCH},
    Stage.PRIORITIZE: {Stage.HYPOTHESIZE},
    Stage.DESIGN: {Stage.HYPOTHESIZE},
    Stage.PREFLIGHT: {Stage.DESIGN},
    Stage.EXECUTE: {Stage.DESIGN},
    Stage.VERIFY: {Stage.HYPOTHESIZE, Stage.DESIGN},
    Stage.REPLICATE: {Stage.HYPOTHESIZE, Stage.DESIGN},
    Stage.ASSESS: {Stage.RESEARCH, Stage.HYPOTHESIZE},
    Stage.VALIDATE_MARKET: {Stage.RESEARCH},
    Stage.DECIDE: {Stage.DISCOVER, Stage.HYPOTHESIZE},
}


class StepInput(Contract):
    run_id: str = Field(min_length=1)
    stage: Stage
    version: int = Field(ge=0)
    predecessor_event: str | None = None
    resource_limit_usd: str
