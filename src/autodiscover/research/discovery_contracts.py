"""Typed inputs, model proposals and evidence for bounded discovery."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


Track = Literal["ai_native", "open_science"]


class StageSettings(Record):
    reasoning_effort: Literal["minimal", "low", "medium", "high"]
    max_output_tokens: int = Field(ge=256, le=16384)
    timeout_seconds: float = Field(gt=0, le=120, allow_inf_nan=False)


class CapabilityPolicy(Record):
    version: Literal["capability-v1", "capability-v2"] = "capability-v1"
    relevance_screen: bool = Field(default=False, exclude_if=lambda enabled: not enabled)
    tracks: list[Track] = Field(min_length=1, max_length=2)
    stages: dict[str, StageSettings]

    @model_validator(mode="after")
    def complete(self):
        if len(set(self.tracks)) != len(self.tracks):
            raise ValueError("Duplicate discovery track")
        if set(self.stages) != {"planning", "extraction", "gap", "proposal", "critique"}:
            raise ValueError("Configure every capability stage exactly once")
        return self


class DiscoverySpec(Record):
    capability: CapabilityPolicy | None = Field(default=None, exclude_if=lambda v: v is None)
    objective: str = Field(min_length=12, max_length=1000)
    sources: list[SourceSeed] = Field(default_factory=list, max_length=6)
    protocol: Literal["discovery-v1", "discovery-v2"] = "discovery-v1"
    seconds: int = Field(default=120, ge=10, le=1200)
    max_output_tokens: int = Field(default=1536, ge=256, le=16384)
    retry_limit: int = Field(default=1, ge=0, le=2)
    mode: Literal["reviewed", "single_model"] = "reviewed"
    session_context: SessionContext | None = Field(default=None, exclude_if=lambda v: v is None)

    @model_validator(mode="after")
    def capability_bounds(self):
        if self.capability:
            if self.protocol != "discovery-v2":
                raise ValueError("Capability discovery requires Discovery-v2")
            if any(
                s.max_output_tokens > self.max_output_tokens or s.timeout_seconds >= self.seconds
                for s in self.capability.stages.values()
            ):
                raise ValueError("Stage bounds exceed branch limits")
        elif self.seconds > 240 or self.max_output_tokens > 4096:
            raise ValueError("Extended branch bounds require capability policy")
        return self


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


class ResearchPriority(Record):
    gap_importance: Score
    gap_evidence: Score
    ai_suitability: Score
    distinctiveness: Score
    plausibility: Score
    information_gain: Score
    experimental_feasibility: Score
    prior_art_uncertainty: Score
    usefulness: Score
    research_cost: Score
    historical_progress: Score
    rationale: Text


class CapabilityDirection(Direction):
    track: Track
    track_reason: Text
    source_query: Short
    target_query: Short
    prior_art_query: Short
    priority: ResearchPriority


class CapabilityPlan(_QualityResponse):
    directions: list[CapabilityDirection] = Field(min_length=3, max_length=3)


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
    direction: int | None = Field(default=None, exclude_if=lambda v: v is None)
    stage: str | None = Field(default=None, exclude_if=lambda v: v is None)
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


EvidenceRole = Literal["unmet_need", "mechanism", "observed_constraint", "measured_improvement"]


class CapabilityFindingV2(AtomicFinding):
    # Extractor labels are proposals, not independently verified semantic entailment.
    evidence_roles: list[EvidenceRole | Literal["context"]] = Field(min_length=1, max_length=5)


class CapabilityExtractionV2(_QualityResponse):
    version: Literal["capability-extraction-v2"] = "capability-extraction-v2"
    findings: list[CapabilityFindingV2] = Field(max_length=6)
    gap: str = Field(max_length=400)
    query: str = Field(max_length=220)


class ResearchClaim(Record):
    text: Short
    kind: Literal["empirical", "inference", "prediction"]
    finding_ids: list[str] = Field(max_length=6)


class QualityProposal[Claim: ResearchClaim](Record):
    hypothesis: Hypothesis
    claims: list[Claim] = Field(min_length=1, max_length=6)
    bridge: MechanismBridge | None
    established_advantage_claimed: bool
    independent_replication_claimed: bool
    minimum_effect_unit: Short
    recovery_query: str = Field(max_length=220)


class GapAnalysis(_QualityResponse):
    unmet_need: Text
    need_finding_ids: list[Short] = Field(max_length=6)
    current_workaround: Text
    root_constraint: Text
    constraint_status: Literal["observed", "speculative"]
    constraint_finding_ids: list[Short] = Field(max_length=6)
    target_user: Text
    economic_buyer: Text
    frequency_and_severity: Text
    demand_evidence: Text
    ai_capability: Text
    ai_approaches: list[Short] = Field(min_length=1, max_length=6)
    why_ai: Text
    non_ai_alternatives: list[Short] = Field(min_length=1, max_length=6)
    ai_advantage: Literal["plausible", "unnecessary", "unknown"]
    ai_advantage_reason: Text


class Opportunity(Record):
    version: Literal["ai-opportunity-v1"]
    gap: GapAnalysis
    ai_suitability: Literal["plausible", "unnecessary", "unknown"]
    ai_reasoning: Text
    non_ai_challenge: Text
    component_finding_ids: list[Short] = Field(min_length=1, max_length=6)
    unsupported_assumptions: list[Text] = Field(min_length=1, max_length=6)
    technical_dependencies: list[Short] = Field(min_length=1, max_length=6)
    model_and_tool_requirements: Text
    data_requirements: Text
    model_limitations: Text
    integration_and_deployment: Text
    safety_and_reliability: Text
    verification_method: Text
    cost_considerations: Text
    existing_products_and_research: list[Short] = Field(min_length=1, max_length=6)
    prior_art_evidence: list[Citation] = Field(max_length=4)
    prior_art_status: Literal["equivalent", "close", "unknown"]
    differentiation: Text
    falsifiable_prediction: Text
    evaluation_environment: Text
    comparator: Short
    minimum_meaningful_improvement: Text
    next_cheapest_experiment: Text
    adoption_barriers: Text
    # Model output can never confer experimental, replication or commercial authority.
    technical_feasibility: Literal["untested"]
    scientific_novelty: Literal["unverified"]
    commercial_validation: Literal["unvalidated"]
    validation_status: Literal["unverified_idea"]


class CapabilityProposal[Claim: ResearchClaim](QualityProposal[Claim]):
    opportunity: Opportunity


class CapabilityClaimV2(ResearchClaim):
    evidence_role: EvidenceRole | None


class CapabilityProposalV2(CapabilityProposal[CapabilityClaimV2]):
    pass


class CapabilityResponseV2(_QualityResponse):
    proposal: CapabilityProposalV2 | None
    reason: str = Field(max_length=400)


class CapabilityResponse(_QualityResponse):
    proposal: CapabilityProposal | None
    reason: str = Field(max_length=400)


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


class CapabilityReview(QualityReview):
    ai_necessity: Literal["plausible", "unnecessary", "uncertain"]
    bridge_plausibility: Literal["plausible", "unsupported"]
    need_support: Literal["supports", "contradicts", "uncertain"]
    capability_rationale: Text


class CapabilityReviewV2(CapabilityReview):
    constraint_support: Literal["supports", "contradicts", "uncertain", "not_claimed"]


class RecoveryReceipt(Record):
    failure: RecoveryFailure
    decision: RecoveryDecision
    query: str = ""
    new_source_ids: list[str] = Field(default_factory=list)


class QualityAttempt(Record):
    extraction: Extraction | CapabilityExtractionV2
    proposal: CapabilityProposalV2 | CapabilityProposal | QualityProposal | None
    screen: EvidenceScreen
    review: CapabilityReviewV2 | CapabilityReview | QualityReview | None
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
    track: Track | None = Field(default=None, exclude_if=lambda v: v is None)
    opportunity: Opportunity | None = Field(default=None, exclude_if=lambda v: v is None)
    epistemic_state: Literal["testable_hypothesis"] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    opportunity_status: Literal["unverified_idea", "evidence_grounded_hypothesis"] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
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

    plan: CapabilityPlan | Plan
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
