"""Read-only, source-bound prior-art dossier; never adjudicates scientific novelty.

A recorded quotation establishes that a document contains those bytes, not that its
method, findings or equivalence assessment are true. Operator/model comparisons
remain unverified assertions until independent subject-matter review.
"""

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.orchestrator.durability import canonical
from autodiscover.research.catalog import Catalog
from autodiscover.security.redaction import contains_credential


class PriorArtComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(pattern=r"^source-[a-f0-9]{64}$")
    quote: str = Field(min_length=5, max_length=1000)
    relationship: Literal[
        "possible_functional_overlap",
        "possible_difference",
        "contradictory_finding",
        "background_only",
    ]
    explanation: str = Field(min_length=10, max_length=2000)


class PriorArtRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    candidate_id: str = Field(min_length=1, max_length=120)
    hypothesis: str = Field(min_length=10, max_length=2000)
    claimed_mechanism: str = Field(min_length=10, max_length=2000)
    falsifiable_prediction: str = Field(min_length=10, max_length=2000)
    search_queries: list[str] = Field(min_length=1, max_length=15)
    comparisons: list[PriorArtComparison] = Field(default_factory=list, max_length=50)


def compile_prior_art_dossier(
    catalog: Catalog, run_id: str, request: PriorArtRequest
) -> dict[str, Any]:
    """Inspect only sources owned by this run. Do not write or promote novelty."""

    catalog.store.get_run(run_id)
    if (
        any(not query.strip() or len(query) > 250 for query in request.search_queries)
        or len({query.casefold().strip() for query in request.search_queries})
        != len(request.search_queries)
    ):
        raise ValueError("Search queries must be distinct and bounded")
    if contains_credential(request.model_dump_json()):
        raise ValueError("Dossier contains recognizable credential material")

    owned_sources = set(catalog.sources(run_id))
    seen: set[tuple[str, str, str]] = set()
    comparisons: list[dict[str, Any]] = []
    warnings: list[str] = []
    primary_count = 0
    overlap_candidates = 0

    for item in request.comparisons:
        key = (item.source_id, item.quote, item.relationship)
        if key in seen:
            raise ValueError("Duplicate comparison is not independent evidence")
        seen.add(key)
        if item.source_id not in owned_sources:
            raise IntegrityError("Prior-art source not registered to this run")
        # Catalog.source rejects invalidated evidence and validates its content digest.
        source, text = catalog.source(item.source_id)
        if item.quote not in text:
            raise IntegrityError("Prior-art quote not present in source content")
        if source.source_kind == "publication_metadata":
            warnings.append("Publication metadata is not a full-text method comparison")
        else:
            primary_count += 1
        if item.relationship == "possible_functional_overlap":
            overlap_candidates += 1
        comparisons.append(
            {
                "source_id": item.source_id,
                "source_title": source.title,
                "source_url": source.url,
                "publication_date": source.published_on,
                "source_kind": source.source_kind,
                "retrieval_provenance": source.retrieval_provenance,
                "raw_digest": source.raw_digest,
                "text_digest": source.text_digest,
                "exact_quote": item.quote,
                "proposed_relationship": item.relationship,
                "unverified_reasoning": item.explanation,
                "verification": "quote located; scientific interpretation not independently reviewed",
            }
        )

    if not request.comparisons:
        warnings.append("No primary-source comparisons submitted")
    if primary_count == 0:
        warnings.append("No primary-document comparison; cannot assess mechanisms")
    if overlap_candidates:
        warnings.append("Possible functional overlap needs independent mechanism review")

    return {
        "schema_version": 1,
        "run_id": run_id,
        "candidate_id": request.candidate_id,
        "request_digest": hashlib.sha256(
            canonical(request.model_dump(mode="json")).encode()
        ).hexdigest(),
        "hypothesis": request.hypothesis,
        "claimed_mechanism": request.claimed_mechanism,
        "falsifiable_prediction": request.falsifiable_prediction,
        "search_queries_proposed": request.search_queries,
        "searches_executed_by_this_command": 0,
        "comparisons": comparisons,
        "coverage": {
            "run_owned_sources": len(owned_sources),
            "submitted_comparisons": len(comparisons),
            "primary_document_comparisons": primary_count,
            "exhaustive": False,
        },
        "assessment": {
            "novelty": "unknown",
            "novelty_verified": False,
            "possible_overlap_observations": overlap_candidates,
            "independent_method_review": "not_performed",
            "independent_replication": "not_performed",
            "commercial_validation": "not_assessed",
        },
        "warnings": sorted(set(warnings)),
        "next_gate": (
            "Execute and record mechanism-oriented prior-art searches; inspect full methods, "
            "study populations and conflicting findings; arrange independent review; "
            "preregister a matched-baseline experiment. A missing match is not proof of novelty."
        ),
    }
