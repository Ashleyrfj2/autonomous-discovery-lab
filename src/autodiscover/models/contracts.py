"""Provider-independent contracts. Model names, prices and capabilities are configuration."""

from decimal import Decimal
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)


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
    capability_source: str = Field(min_length=1)
    pricing_source: str = Field(min_length=1)
    verified_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    timeout_seconds: float = Field(default=30, gt=0, le=120, allow_inf_nan=False)
    live_authorized: bool = False


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    prompt: str = Field(min_length=1, max_length=50000)
    max_output_tokens: int = Field(default=512, ge=1, le=100000)
    json_schema: dict[str, Any] | None = None


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


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
    ):
        super().__init__(code)
        self.code, self.retryable, self.uncertain = code, retryable, uncertain
        self.retry_after = min(max(retry_after, 0), 30)
        self.known_zero_cost = known_zero_cost


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
