"""Cost-aware advisory selection; estimates cannot grant execution or novelty authority."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CandidateEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    candidate_id: str = Field(min_length=1, max_length=120)
    family: Literal["encoding-v1", "allocation-v1", "theoretical"]
    estimated_max_cost_usd: Decimal = Field(ge=0, allow_inf_nan=False)
    estimated_seconds: float = Field(gt=0, le=3600, allow_inf_nan=False)
    expected_information_gain: float = Field(ge=0, le=1, allow_inf_nan=False)
    uncertainty: float = Field(ge=0, le=1, allow_inf_nan=False)
    provenance: Literal["independent_calibration", "operator_estimate", "model_estimate"]
    supporting_evidence_digest: str | None = Field(
        default=None, pattern=r"^[a-f0-9]{64}$"
    )

    @model_validator(mode="after")
    def require_calibration_reference(self) -> "CandidateEstimate":
        if self.provenance == "independent_calibration" and not self.supporting_evidence_digest:
            raise ValueError("Independently calibrated estimates need evidence identity")
        return self


class PortfolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    budget_usd: Decimal = Field(gt=0, allow_inf_nan=False)
    seconds_budget: float = Field(gt=0, le=86400, allow_inf_nan=False)
    max_experiments: int = Field(ge=1, le=100)
    candidates: list[CandidateEstimate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_candidates(self) -> "PortfolioRequest":
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate candidate identities")
        return self


def rank_portfolio(request: PortfolioRequest) -> dict[str, object]:
    """Greedy bounded planner, not an optimizer and never an admission authority.

    Preserve budget constraints, prioritize calibrated evidence and uncertainty,
    and avoid rewarding repeated exploration of one family by default.
    """
    remaining_cost = request.budget_usd
    remaining_seconds = request.seconds_budget
    selected: list[dict[str, object]] = []
    family_counts: dict[str, int] = {}
    available = list(request.candidates)
    excluded: list[dict[str, str]] = []

    while available and len(selected) < request.max_experiments:
        affordable = [
            candidate
            for candidate in available
            if candidate.estimated_max_cost_usd <= remaining_cost
            and candidate.estimated_seconds <= remaining_seconds
        ]
        if not affordable:
            break

        def score(candidate: CandidateEstimate) -> tuple[float, str]:
            # Scores are planning estimates, NOT scientific validity or verified reward.
            evidence_weight = {
                "independent_calibration": 1.0,
                "operator_estimate": 0.6,
                "model_estimate": 0.25,
            }[candidate.provenance]
            uncertain_gain = candidate.expected_information_gain * (1 - candidate.uncertainty)
            diversity = 1 / (1 + family_counts.get(candidate.family, 0))
            cost_penalty = 1 + float(candidate.estimated_max_cost_usd) + (
                candidate.estimated_seconds / 60
            )
            return evidence_weight * uncertain_gain * diversity / cost_penalty, candidate.candidate_id

        choice = sorted(affordable, key=lambda item: (-score(item)[0], item.candidate_id))[0]
        selected.append(
            {
                "candidate_id": choice.candidate_id,
                "family": choice.family,
                "estimate_provenance": choice.provenance,
                "planning_priority": round(score(choice)[0], 8),
                "estimated_max_cost_usd": str(choice.estimated_max_cost_usd),
                "estimated_seconds": choice.estimated_seconds,
            }
        )
        remaining_cost -= choice.estimated_max_cost_usd
        remaining_seconds -= choice.estimated_seconds
        family_counts[choice.family] = family_counts.get(choice.family, 0) + 1
        available.remove(choice)

    for item in available:
        excluded.append(
            {
                "candidate_id": item.candidate_id,
                "reason": (
                    "estimate exceeds remaining cost/time"
                    if item.estimated_max_cost_usd > remaining_cost
                    or item.estimated_seconds > remaining_seconds
                    else "maximum planned experiment count reached"
                ),
            }
        )
    return {
        "schema_version": 1,
        "advisory_only": True,
        "execution_authorized": False,
        "scientific_validity": "not_assessed",
        "novelty": "unknown",
        "commercial_validation": "unvalidated",
        "selected": selected,
        "excluded": excluded,
        "estimated_reserved_cost_usd": str(request.budget_usd - remaining_cost),
        "remaining_estimated_budget_usd": str(remaining_cost),
        "remaining_seconds_budget": remaining_seconds,
        "limitations": (
            "Uncalibrated information gain and time/cost predictions are guesses; "
            "actual authorization, spending reservations and independent tests are separate"
        ),
    }
