"""Preregistered bounded experiment contract for reviewed lossless encoding workers."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.orchestrator.durability import canonical


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    implementation: Literal["encoding-v1"] = "encoding-v1"
    hypothesis_id: str = Field(min_length=1)
    algorithm: Literal["rle", "identity"] = "rle"
    baseline: Literal["raw-bytes"] = "raw-bytes"
    data_profile: Literal["runs", "alternating"] = "runs"
    seed: int = Field(default=42, ge=0, le=1000000)
    samples: int = Field(default=24, ge=4, le=100)
    bytes_per_sample: int = Field(default=256, ge=16, le=1024)
    minimum_savings: float = Field(default=0.25, gt=0, lt=1, allow_inf_nan=False)
    replications: int = Field(default=2, ge=2, le=5)
    seconds: float = Field(default=10, gt=0, le=120, allow_inf_nan=False)
    memory_mb: int = Field(default=128, ge=64, le=256)
    max_output_bytes: int = Field(default=1000000, ge=1000, le=2000000)
    expected_artifacts: tuple[str, ...] = (
        "raw-encodings",
        "independent-evaluation",
        "replications",
    )
    failure_criteria: str = (
        "Any corrupted roundtrip, fixture mismatch, invalid metric or unmet threshold"
    )
    protocol_version: Literal["encoding-evaluation-v1"] = "encoding-evaluation-v1"

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical(self.model_dump(mode="json")).encode()).hexdigest()
