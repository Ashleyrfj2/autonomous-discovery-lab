"""Versioned, conservative local policy. No credentials belong in this contract."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: int = Field(default=1, ge=1, le=1)
    max_experiment_seconds: float = Field(default=120, gt=0, le=120, allow_inf_nan=False)
    max_retries_per_step: int = Field(default=2, ge=0, le=10)
    max_hypotheses_per_cycle: int = Field(default=5, ge=1, le=100)
    max_concurrent_experiments: int = Field(default=1, ge=1, le=8)
    explore_existing_candidates: bool = False
    allow_live_inference: bool = False
    allow_retrieval: bool = False

    @model_validator(mode="before")
    @classmethod
    def read_legacy_policy(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Historical policies remain hash-bound in SQLite and readable after cap removal.
            return {
                key: value
                for key, value in data.items()
                if key not in {"max_cost_per_run_usd", "max_cost_per_day_usd"}
            }
        return data

    @classmethod
    def load(cls, path: Path) -> "Limits":
        return cls.model_validate_json(path.read_text())
