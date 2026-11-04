"""Typed inputs, model proposals and evidence for bounded discovery."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Short = Annotated[str, Field(min_length=3, max_length=220)]
Text = Annotated[str, Field(min_length=3, max_length=800)]
Score = Annotated[int, Field(ge=1, le=5)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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


class DiscoverySpec(Record):
    objective: str = Field(min_length=12, max_length=1000)
    sources: list[SourceSeed] = Field(default_factory=list, max_length=6)
    protocol: Literal["discovery-v1"] = "discovery-v1"
    seconds: int = Field(default=120, ge=10, le=240)
    max_output_tokens: int = Field(default=1536, ge=256, le=4096)
    retry_limit: int = Field(default=1, ge=0, le=2)
    mode: Literal["reviewed", "single_model"] = "reviewed"


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
