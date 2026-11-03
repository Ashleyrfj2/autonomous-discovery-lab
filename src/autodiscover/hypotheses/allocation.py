"""Explicit reviewed allocation hypotheses: measurable, not automatically novel."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.orchestrator.durability import canonical


class AllocationHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    experiment_family: Literal["allocation-v1"] = "allocation-v1"
    question: str = Field(min_length=10, max_length=1000)
    domain: str = Field(min_length=2, max_length=100)
    connection_domain: str = Field(min_length=2, max_length=100)
    prediction: str = Field(min_length=10, max_length=2000)
    metric: Literal["normalized-value-gain-vs-ratio-greedy"] = (
        "normalized-value-gain-vs-ratio-greedy"
    )
    comparator: Literal["ratio-greedy"] = "ratio-greedy"
    algorithm: Literal["greedy", "dynamic"] = "dynamic"
    threshold: float = Field(default=0.15, ge=0, lt=1, allow_inf_nan=False)
    data_profile: Literal["trap"] = "trap"
    parent_id: None = None  # No automated cross-family or optimizer revision is reviewed yet.
    revision_reason: None = None
    source_ids: list[str] = Field(default_factory=list)

    @property
    def identity(self) -> str:
        body = {
            "family": self.experiment_family,
            "algorithm": self.algorithm,
            "metric": self.metric,
            "threshold": self.threshold,
            "data_profile": self.data_profile,
            "comparator": self.comparator,
        }
        return hashlib.sha256(canonical(body).encode()).hexdigest()


def allocation_demo_proposal(domain: str = "resource scheduling") -> AllocationHypothesis:
    return AllocationHypothesis(
        question=f"Can dynamic programming improve bounded allocations for {domain[:60]}?",
        domain=domain[:100],
        connection_domain="discrete optimization",
        prediction="Beat ratio-greedy by at least 15 percent of optimum "
        "on each locked held-out allocation-trap case",
    )
