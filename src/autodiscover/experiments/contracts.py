"""Preregistered bounded experiment contract for reviewed lossless encoding workers."""

import hashlib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.orchestrator.durability import canonical


def code_digest(name: str) -> str:
    return hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[2] = 2
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
    protocol_version: Literal["encoding-evaluation-v2"] = "encoding-evaluation-v2"
    worker_sha256: str = Field(
        default_factory=lambda: code_digest("worker.py"), pattern=r"^[a-f0-9]{64}$"
    )
    fixture_sha256: str = Field(
        default_factory=lambda: code_digest("datasets.py"), pattern=r"^[a-f0-9]{64}$"
    )
    evaluator_sha256: str = Field(
        default_factory=lambda: code_digest("evaluator.py"), pattern=r"^[a-f0-9]{64}$"
    )

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical(self.model_dump(mode="json")).encode()).hexdigest()


Byte = Annotated[int, Field(strict=True, ge=0, le=255)]


class EncodedCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: str = Field(pattern=r"^(train|heldout):[0-9]{1,3}$")
    encoded: list[Byte] = Field(max_length=2048)


class WorkerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal[1]
    rows: list[EncodedCase] = Field(min_length=1, max_length=300)


class RawResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    output: WorkerOutput
    plan_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    replication: int = Field(ge=0, le=5)
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)
    peak_rss_bytes: int = Field(ge=0)
    worker_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    python_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    isolation: Literal["macOS-seatbelt"]
