"""Preregistered reviewed 0/1 resource-allocation experiment; no generated code."""

import hashlib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.orchestrator.durability import canonical


def allocation_digest(filename: str) -> str:
    return hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()


class AllocationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    implementation: Literal["allocation-v1"] = "allocation-v1"
    hypothesis_id: str = Field(min_length=1)
    algorithm: Literal["dynamic", "greedy"] = "dynamic"
    baseline: Literal["ratio-greedy"] = "ratio-greedy"
    data_profile: Literal["trap"] = "trap"
    seed: int = Field(default=42, ge=0, le=1000000)
    samples: int = Field(default=6, ge=4, le=30)
    minimum_gain: float = Field(default=0.15, ge=0, lt=1, allow_inf_nan=False)
    replications: int = Field(default=2, ge=2, le=5)
    seconds: float = Field(default=10, gt=0, le=120, allow_inf_nan=False)
    memory_mb: int = Field(default=128, ge=64, le=256)
    max_output_bytes: int = Field(default=1000000, ge=1000, le=2000000)
    expected_artifacts: tuple[str, ...] = (
        "raw-allocations",
        "independent-evaluation",
        "replications",
    )
    failure_criteria: str = (
        "Invalid selection, overweight allocation, mismatch from an independent optimum, "
        "or unmet preregistered improvement"
    )
    protocol_version: Literal["allocation-evaluation-v1"] = "allocation-evaluation-v1"
    worker_sha256: str = Field(
        default_factory=lambda: allocation_digest("allocation_worker.py"),
        pattern=r"^[a-f0-9]{64}$",
    )
    fixture_sha256: str = Field(
        default_factory=lambda: allocation_digest("allocation_fixtures.py"),
        pattern=r"^[a-f0-9]{64}$",
    )
    evaluator_sha256: str = Field(
        default_factory=lambda: allocation_digest("allocation_evaluator.py"),
        pattern=r"^[a-f0-9]{64}$",
    )

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical(self.model_dump(mode="json")).encode()).hexdigest()


Index = Annotated[int, Field(strict=True, ge=0, le=31)]


class AllocationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: str = Field(pattern=r"^(train|heldout):[0-9]{1,3}$")
    selected: list[Index] = Field(max_length=12)


class AllocationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal[1]
    rows: list[AllocationCase] = Field(min_length=1, max_length=90)


class AllocationRawResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    output: AllocationOutput
    plan_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    replication: int = Field(ge=0, le=5)
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)
    peak_rss_bytes: int = Field(ge=0)
    worker_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    python_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    isolation: Literal["macOS-seatbelt"]
