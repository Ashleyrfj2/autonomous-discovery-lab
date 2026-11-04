"""Typed inputs, model proposals and evidence for bounded discovery."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Short = Annotated[str, Field(min_length=3, max_length=220)]
Text = Annotated[str, Field(min_length=3, max_length=800)]
Score = Annotated[int, Field(ge=1, le=5)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _strict_quality_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Close defaults in nested quality schemas without changing older role schemas."""
    result = {key: value for key, value in schema.items() if key != "default"}
    for key in ("properties", "$defs"):
        if key in result:
            result[key] = {
                name: _strict_quality_schema(child) for name, child in result[key].items()
            }
    if "items" in result:
        result["items"] = _strict_quality_schema(result["items"])
    if "anyOf" in result:
        result["anyOf"] = [_strict_quality_schema(child) for child in result["anyOf"]]
    if result.get("additionalProperties") is False and "properties" in result:
        result["required"] = list(result["properties"])
    return result


class _QualityResponse(Record):
    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return _strict_quality_schema(super().model_json_schema(*args, **kwargs))


class SourceSeed(Record):
    url: str = Field(min_length=10, max_length=1000, pattern=r"^https://")
    title: Short
    publisher: Short | None = None
    published_on: str | None = Field(default=None, max_length=30)
    category: Literal[
        "publication",
        "technical",
        "patent",
        "dataset",
        "industry",
        "market",
        "regulatory",
        "discussion",
    ]
    direction: int = Field(ge=0, le=2)


class SessionContext(Record):
    session_id: str = Field(pattern=r"^session-[a-f0-9]{32}$")
    branch: int = Field(ge=0, lt=256)
    investigation: Short
    recent_evidence: list[Text] = Field(max_length=3)


class DiscoverySpec(Record):
    objective: str = Field(min_length=12, max_length=1000)
    sources: list[SourceSeed] = Field(default_factory=list, max_length=6)
    protocol: Literal["discovery-v1", "discovery-v2"] = "discovery-v1"
    seconds: int = Field(default=120, ge=10, le=240)
    max_output_tokens: int = Field(default=1536, ge=256, le=4096)
    retry_limit: int = Field(default=1, ge=0, le=2)
    mode: Literal["reviewed", "single_model"] = "reviewed"
    session_context: SessionContext | None = Field(default=None, exclude_if=lambda v: v is None)


class Direction(Record):
    question: Short
    first_domain: Short
    second_domain: Short
    query: Short
    expected_support: Text
    expected_falsifier: Text
    value: Score
    uncertainty: Score
    search_effort: Score


class Plan(Record):
    directions: list[Direction] = Field(min_length=3, max_length=3)


class Citation(Record):
    source_id: str = Field(pattern=r"^source-[a-f0-9]{64}$")
    quote: str = Field(min_length=15, max_length=360)


class Hypothesis(Record):
    problem: Text
    evidence: list[Citation] = Field(min_length=1, max_length=4)
    mechanism: Text
    rationale: Text
    novelty_claim: Text
    alternatives: list[Short] = Field(min_length=1, max_length=4)
    prior_art: list[Citation] = Field(max_length=4)
    counterargument: Text
    falsifier: Text
    validation: Text
    metric: Short
    comparator: Short
    minimum_effect: float = Field(gt=0, allow_inf_nan=False)
    uncertainty: Text
    target_user: Text
    economic_buyer: Text
    workaround_and_cost: Text
    adoption_obstacles: Text
    commercial_test: Text


class Objection(Record):
    category: Literal[
        "assumption",
        "evidence",
        "prior_art",
        "alternative",
        "feasibility",
        "dependency",
        "commercial",
        "novelty",
        "measurement",
        "bias",
    ]
    issue: Text
    material: bool
    evidence: list[Citation] = Field(max_length=2)
    query: str = Field(max_length=220)
    expected_information: Score
    effort: Score


class Review(Record):
    objections: list[Objection] = Field(min_length=1, max_length=6)
    falsification_test: Text


class Evidence(Record):
    source_id: str
    title: str
    url: str
    publisher: str | None
    published_on: str | None
    retrieved_at: str
    excerpt: str
    category: str
    provenance: str
    scope: Literal["title", "abstract", "document"]
    limitation: str


class SearchReceipt(Record):
    question: str
    query: str
    evidence: list[Evidence]
    failures: list[str]


class AtomicFinding(Record):
    """Unverified model-extracted finding tied to a literal source passage."""

    finding_id: str = Field(min_length=3, max_length=64)
    citation: Citation
    location: Literal["abstract", "document"]
    domain: str = Field(min_length=3, max_length=160)
    method: str = Field(min_length=3, max_length=800)
    observation: str = Field(min_length=3, max_length=800)
    limitations: str = Field(min_length=3, max_length=800)
    relation: Literal["supports", "contradicts", "context", "unrelated"] = "supports"
    independence_group: str | None = Field(default=None, max_length=120)


class MechanismBridge(Record):
    """An explicitly provisional transfer from an observed source to a target."""

    source_finding_ids: list[str] = Field(min_length=1, max_length=8)
    source_domain: str = Field(min_length=3, max_length=160)
    target_domain: str = Field(min_length=3, max_length=160)
    shared_mechanism: str = Field(min_length=8, max_length=800)
    domain_mismatches: list[str] = Field(min_length=1, max_length=8)
    target_evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    target_outcome_metric: str = Field(min_length=3, max_length=200)
    comparator: str = Field(min_length=3, max_length=200)
    falsifier: str = Field(min_length=8, max_length=800)
    established_advantage_claimed: bool = False
    variables: list[Short] = Field(default_factory=list, max_length=8)
    alternative_explanations: list[Short] = Field(default_factory=list, max_length=8)
    missing_target_evidence: str = Field(default="", max_length=400)
    existing_approaches: list[Short] = Field(default_factory=list, max_length=8)
    measurable_prediction: str = Field(default="", max_length=400)


class EvidenceScreen(Record):
    status: Literal[
        "invalid_source",
        "needs_substantive_evidence",
        "needs_target_evidence",
        "needs_experiment_design",
        "eligible_for_critique",
    ]
    codes: list[str]
    source_bound_findings: int
    semantic_entailment: Literal["independent_review_required"] = "independent_review_required"
    novelty: Literal["unverified"] = "unverified"
    technical_advantage: Literal["unverified"] = "unverified"
    commercial_level: Literal[0] = 0

    @property
    def eligible_for_critique(self) -> bool:
        return self.status == "eligible_for_critique"


RecoveryFailure = Literal[
    "invalid_source",
    "invalid_review",
    "duplicate_session_candidate",
    "title_as_result",
    "quote_not_in_source",
    "semantic_mismatch",
    "irrelevant_domain",
    "missing_target_evidence",
    "missing_measurement",
    "missing_bridge",
    "unsupported_empirical_claim",
    "insufficient_information",
    "known_prior_art",
    "conflicting_findings",
    "no_new_evidence",
]


class RecoveryDecision(Record):
    action: Literal["reject", "retrieve", "revise", "inconclusive", "record_prior_art"]
    reason: str


class Extraction(_QualityResponse):
    findings: list[AtomicFinding] = Field(max_length=6)
    gap: str = Field(max_length=400)
    query: str = Field(max_length=220)


class ResearchClaim(Record):
    text: Short
    kind: Literal["empirical", "inference", "prediction"]
    finding_ids: list[str] = Field(max_length=6)


class QualityProposal(Record):
    hypothesis: Hypothesis
    claims: list[ResearchClaim] = Field(min_length=1, max_length=6)
    bridge: MechanismBridge | None
    established_advantage_claimed: bool
    independent_replication_claimed: bool
    minimum_effect_unit: Short
    recovery_query: str = Field(max_length=220)


class ProposalResponse(_QualityResponse):
    proposal: QualityProposal | None
    reason: str = Field(max_length=400)


class ClaimAssessment(Record):
    claim_index: int = Field(ge=0, le=5)
    judgment: Literal["supports", "contradicts", "uncertain"]
    rationale: Short


class QualityReview(Review, _QualityResponse):
    claim_assessments: list[ClaimAssessment] = Field(max_length=6)
    prior_art_status: Literal["equivalent", "close", "unknown"]
    prior_art_evidence: list[Citation] = Field(max_length=4)


class RecoveryReceipt(Record):
    failure: RecoveryFailure
    decision: RecoveryDecision
    query: str = ""
    new_source_ids: list[str] = Field(default_factory=list)


class QualityAttempt(Record):
    extraction: Extraction
    proposal: QualityProposal | None
    screen: EvidenceScreen
    review: QualityReview | None
    valid_review: bool = False
    extraction_screen: EvidenceScreen | None = None
    issues: list[str] = Field(default_factory=list)


class QualityTrace(Record):
    original: QualityAttempt
    revised: QualityAttempt | None
    recovery: list[RecoveryReceipt]
    outcome: Literal["rejected", "inconclusive", "external_review_required"]


class ScientificGate(Record):
    evidence_binding: Literal["passed", "failed"]
    prior_art_identified: bool
    review_has_material_objection: bool
    falsifier_registered: bool
    mechanistic_plausibility: Literal["external_review_required"] = "external_review_required"
    technical_feasibility: Literal["untested"] = "untested"
    reproducibility: Literal["experiment_required"] = "experiment_required"
    novelty: Literal["unverified"] = "unverified"


class Candidate(Record):
    quality: QualityTrace | None = Field(default=None, exclude_if=lambda value: value is None)
    direction: int
    original: Hypothesis
    original_review: Review | None
    revised: Hypothesis | None
    revision_review: Review | None
    issues: list[str]
    scientific_gate: ScientificGate
    disposition: Literal["rejected", "external_review_required"]


class Report(Record):
    run_id: str
    specification: DiscoverySpec
    routes: dict[str, list[tuple[str, str]]]
    model_configuration: dict[str, dict[str, str | int | float | bool | None]]

    plan: Plan
    searches: list[SearchReceipt]
    candidates: list[Candidate]
    decisions: list[str]
    technical_status: Literal["not_executed"] = "not_executed"
    novelty_status: Literal["unverified"] = "unverified"
    commercial_level: Literal[0] = 0
    usage: dict[str, str | int]
    quality_closed_directions: dict[int, QualityTrace] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    critique_coverage: int | None = Field(default=None, exclude_if=lambda value: value is None)
