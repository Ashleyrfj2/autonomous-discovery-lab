"""Provider-independent contracts. Model names, prices and capabilities are configuration."""

import json
from decimal import Decimal
from math import isfinite
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T", bound=BaseModel)
BASETEN_HACKATHON_MODEL = "meta-models/muse-spark-open-1026"
BASETEN_HACKATHON_KEY_ENV = "BASETEN_HACKATHON_API_KEY"

# Only the reasoning controls used by this integration are configured here.
_REASONING_EFFORTS = {
    ("meta", "muse-wonder-1.0"): {"minimal", "low"},
    ("meta", "muse-spark-1.2"): {"minimal", "low"},
    ("meta", "muse-spark-1.3"): {"minimal", "low"},
    ("baseten", "meta-models/muse-spark-open"): {"low"},
}


def _unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("Duplicate JSON member")
    return obj


def _reject_constant(_value: str) -> None:
    raise ValueError("Non-finite JSON constant")


def parse_structured[T: BaseModel](text: str, schema: type[T]) -> T:
    # Pydantic's JSON parser accepts duplicate members and nonstandard numeric constants.
    json.loads(text, object_pairs_hook=_unique_members, parse_constant=_reject_constant)
    return schema.model_validate_json(text, strict=True)


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    kind: Literal["meta", "baseten"]
    model: str = Field(min_length=1, max_length=200)
    api_key_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,99}$")
    input_usd_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    output_usd_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    context_window: int = Field(ge=512, le=10000000)
    output_limit: int = Field(ge=1, le=1000000)
    structured_output: bool = False
    profile: Literal["standard", "baseten_hackathon"] = "standard"
    reasoning_effort: Literal["minimal", "low"] | None = None
    capability_source: str = Field(min_length=1)
    pricing_source: str = Field(min_length=1)
    verified_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    timeout_seconds: float = Field(default=30, gt=0, le=120, allow_inf_nan=False)
    live_authorized: bool = False

    @model_validator(mode="after")
    def validate_profile(self) -> "ProviderConfig":
        if self.profile == "baseten_hackathon":
            if (self.kind, self.model) != ("baseten", BASETEN_HACKATHON_MODEL):
                raise ValueError("Hackathon profile requires the exact Baseten hackathon model")
            if self.api_key_env != BASETEN_HACKATHON_KEY_ENV:
                raise ValueError("Hackathon profile requires its dedicated credential environment")
            if self.structured_output:
                raise ValueError("Hackathon native structured output is unverified")
        elif self.model == BASETEN_HACKATHON_MODEL or self.api_key_env == BASETEN_HACKATHON_KEY_ENV:
            raise ValueError(
                "Restricted Baseten model and credential require the hackathon profile"
            )
        if (
            self.reasoning_effort is not None
            and self.reasoning_effort not in _REASONING_EFFORTS.get((self.kind, self.model), set())
        ):
            raise ValueError("Reasoning effort is not verified for this provider/model")
        return self


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    prompt: str = Field(min_length=1, max_length=50000)
    max_output_tokens: int = Field(default=512, ge=1, le=100000)
    json_schema: dict[str, Any] | None = None


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def reasoning_within_output(self) -> "Usage":
        if self.reasoning_tokens is not None and self.reasoning_tokens > self.output_tokens:
            raise ValueError("Reasoning tokens exceed completion tokens")
        return self


class Generation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    text: str
    provider: str
    model: str
    usage: Usage
    cost_usd: Decimal = Field(ge=0, allow_inf_nan=False)
    finish_reason: Literal["stop"] = "stop"


class ProviderError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool = False,
        uncertain: bool = False,
        retry_after: float = 0,
        known_zero_cost: bool = False,
        usage: Usage | None = None,
        cost_usd: Decimal | None = None,
    ):
        super().__init__(code)
        self.code, self.retryable, self.uncertain = code, retryable, uncertain
        self.retry_after = min(max(retry_after, 0), 30) if isfinite(retry_after) else 0
        self.known_zero_cost = known_zero_cost
        self.usage, self.cost_usd = usage, cost_usd


class Provider(Protocol):
    name: str
    model: str
    is_live: bool

    def generate(self, request: GenerationRequest) -> Generation: ...
    def generate_structured(
        self, request: GenerationRequest, schema: type[T]
    ) -> tuple[T, Generation]: ...
    def get_usage(self) -> Usage: ...
    def estimate_cost(self, request: GenerationRequest) -> Decimal: ...
    def health_check(self) -> dict[str, Any]: ...
