"""Commercial hypotheses, source evidence and explicit human review are separate contracts."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1


class Alternative(Contract):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=3, max_length=1000)
    source_ids: list[str] = Field(default_factory=list, max_length=10)


class Opportunity(Contract):
    candidate_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    target_user: str | None = Field(default=None, max_length=300)
    economic_buyer: str | None = Field(default=None, max_length=300)
    problem: str = Field(min_length=10, max_length=2000)
    problem_severity: Literal["unknown", "low", "moderate", "high", "critical"] = "unknown"
    current_alternatives: list[Alternative] = Field(default_factory=list, max_length=20)
    competitors: list[Alternative] = Field(default_factory=list, max_length=20)
    adoption_constraints: list[str] = Field(default_factory=list, max_length=20)
    buyer_reachability: str | None = Field(default=None, max_length=1000)
    assumptions: list[str] = Field(default_factory=list, max_length=20)


class MarketEvidence(Contract):
    origin: Literal["external", "synthetic", "model_generated", "benchmark"]
    kind: Literal[
        "problem_report",
        "user_interview",
        "buyer_interview",
        "pilot_commitment",
        "adoption",
        "payment",
        "strong_commercial_commitment",
    ]
    source_id: str | None = Field(default=None, max_length=100)
    quote: str | None = Field(default=None, min_length=3, max_length=1000)
    subject_role: Literal["user", "buyer", "unknown"] = "unknown"
    buyer_role: str | None = Field(default=None, max_length=300)
    amount: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def external_has_source(self) -> "MarketEvidence":
        if self.origin == "external" and (not self.source_id or not self.quote):
            raise ValueError("External evidence requires an actual source and exact quote")
        return self


Fact = Literal[
    "real_problem",
    "direct_user",
    "direct_buyer",
    "serious_adoption",
    "payment_received",
    "comparable_commercial_commitment",
]


class HumanReview(Contract):
    accepted: bool
    facts: list[Fact] = Field(default_factory=list, max_length=6)
    rationale: str = Field(min_length=10, max_length=1000)
    source_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
