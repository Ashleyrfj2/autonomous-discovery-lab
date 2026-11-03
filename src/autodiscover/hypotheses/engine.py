"""Falsifiable typed proposals. Unsupported experiment families cannot reach execution."""

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autodiscover.models.contracts import GenerationRequest
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    question: str = Field(min_length=10, max_length=1000)
    domain: str = Field(min_length=1, max_length=100)
    connection_domain: str = Field(min_length=1, max_length=100)
    prediction: str = Field(min_length=10, max_length=2000)
    metric: Literal["encoded-byte-savings-vs-raw"] = "encoded-byte-savings-vs-raw"
    comparator: Literal["raw-bytes"] = "raw-bytes"
    algorithm: Literal["rle", "identity"]
    threshold: float = Field(default=0.25, gt=0, lt=1, allow_inf_nan=False)
    data_profile: Literal["runs", "alternating"] = "runs"
    parent_id: str | None = None
    revision_reason: str | None = None
    source_ids: list[str] = []

    @model_validator(mode="after")
    def revision_has_reason(self) -> "Hypothesis":
        if self.parent_id and not self.revision_reason:
            raise ValueError("Revision requires an evidence-based reason")
        return self

    @property
    def identity(self) -> str:
        body = {
            "algorithm": self.algorithm,
            "metric": self.metric,
            "threshold": self.threshold,
            "data_profile": self.data_profile,
            "comparator": self.comparator,
        }
        return hashlib.sha256(canonical(body).encode()).hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"\W+", " ", text.casefold()).strip()


def generate(
    router: Router,
    run_id: str,
    topic: str,
    *,
    key: str,
    source_context: str = "Offline fixture; no external sources",
) -> Hypothesis:
    prompt = canonical(
        {
            "task": "Propose one falsifiable compression comparison. Experiments support "
            "only encoding-v1; unsupported ideas are theoretical. Never execute model code.",
            "topic": topic,
            "untrusted_source_data": source_context,
            "required_prediction": (
                "Exact lossless roundtrip and savings against raw bytes on held-out data"
            ),
        }
    )
    hypothesis, _ = router.generate_structured(
        run_id, "HYPOTHESIZE", GenerationRequest(prompt=prompt), Hypothesis, key=key
    )
    return hypothesis


def demo_proposal(topic: str, *, algorithm: str = "rle") -> dict[str, object]:
    return {
        "question": f"Can run encoding reduce repeated data costs for {topic[:800]}?",
        "domain": topic[:100],
        "connection_domain": "information theory",
        "prediction": "At least 25% encoded byte savings versus raw "
        "on every held-out runs fixture, "
        "with exact reconstruction",
        "algorithm": algorithm,
        "threshold": 0.25,
    }
