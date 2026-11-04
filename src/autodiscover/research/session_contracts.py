"""Operator-selected limits and durable session records."""

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from autodiscover.research.discovery_contracts import DiscoverySpec, Record


class SessionProfile(Record):
    protocol: Literal["research-session-v1"] = "research-session-v1"
    discovery: DiscoverySpec
    duration_seconds: int = Field(ge=10, le=172800)
    pause_after_first_branch: bool = False
    concurrency: int = Field(ge=1, le=4)
    max_branches: int = Field(ge=1, le=256)
    max_model_calls: int = Field(ge=1, le=20000)
    max_total_tokens: int = Field(ge=1, le=500_000_000)
    max_consecutive_errors: int = Field(ge=1, le=20)
    max_stagnant_branches: int = Field(ge=1, le=50)
    aggregate_cost_ceiling_usd: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def managed_protocol(self):
        if self.discovery.protocol != "discovery-v2" or self.discovery.session_context is not None:
            raise ValueError("Sessions require a fresh Discovery-v2 specification")
        if self.concurrency > self.max_branches:
            raise ValueError("Concurrency exceeds branch limit")
        if self.pause_after_first_branch and (self.concurrency != 1 or self.max_branches < 2):
            raise ValueError("Qualification pause requires two branches and serial execution")
        return self


class BranchIntent(Record):
    number: int
    child_id: str
    specification: DiscoverySpec


class BranchOutcome(Record):
    number: int
    child_id: str
    packet_digest: str | None = None
    error: str | None = None
    provider_error: bool = False
    searched: int = 0
    proposed: int = 0
    reviewed: int = 0
    rejected: int = 0
    revised: int = 0
    prior_art: int = 0
    duplicate_queries: int = 0
    source_failures: int = 0
    source_ids: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    excerpts: list[str] = Field(default_factory=list)
    candidates: list[list[str]] = Field(default_factory=list)
    qualified_directions: list[int] = Field(default_factory=list)
    duplicate_directions: list[int] = Field(default_factory=list)
    next_evidence: str = ""
