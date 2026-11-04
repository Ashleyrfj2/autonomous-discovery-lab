"""Capability-v1 policy, shared Discovery-v2 stages and deterministic opportunity gates."""

import re

from autodiscover.research.discovery_contracts import (
    AtomicFinding,
    CapabilityDirection,
    CapabilityPolicy,
    CapabilityProposal,
    Direction,
    Evidence,
    GapAnalysis,
    ResearchPriority,
)
from autodiscover.research.quality import screen_evidence

MISSION = (
    "Primary track A: discover important unmet needs and genuinely new AI-enabled capabilities, "
    "rather than adding AI to an existing workflow. Investigate evidence of the gap, people "
    "affected, existing products, root constraints and whether AI changes those constraints. "
    "Challenge AI against ordinary software, process redesign and human expertise. Consider "
    "multimodal models, agents, simulation, world models, robotics, learning, knowledge "
    "representation, retrieval, verification and AI/non-AI combinations. Track B preserves open "
    "scientific exploration without forcing an AI product. All industries remain eligible. "
    "Record track selection and any change from prior directions with an evidence-based reason."
)
EXTRACTION = (
    " Extract independently supported source-domain mechanisms AND target-domain limitations, "
    "needs, methods and conditions. Descriptive findings about limitations or established methods "
    "are eligible when an exact substantive passage supports them; a finding need not report a "
    "numerical improvement. Never demand an existing cross-domain trial to form a hypothesis. "
    "Label each finding with its actual direction domain. Mark irrelevant sources unrelated. "
    "Return no finding for title-only or unsupported claims."
)
GAP_PROMPT = (
    "Identify the actual unmet need from supplied findings; distinguish an observed constraint "
    "from a speculative causal explanation. Link the need and any observed constraint to finding "
    "IDs in the target domain. Record workaround, affected users, severity and unknown demand. "
    "Propose an AI capability and approaches, then challenge whether ordinary software, process "
    "change, human expertise or existing products would solve it better. AI suitability is "
    "independent of novelty and demand. Unsupported demand remains unknown. " + MISSION
)
PROPOSAL_PROMPT = (
    "Create a PROVISIONAL mechanism and testable prediction using both independently supported "
    "domains. Direct cross-domain experimental proof is NOT required for a testable hypothesis. "
    "Absence of transfer studies is uncertainty, never proof of novelty or reason alone to "
    "reject. Explain shared variables, causal bridge, mismatches, unsupported assumptions, "
    "comparators, meaningful effect, falsifier and cheapest controlled test. Every empirical "
    "assertion needs a finding-linked claim; predictions and inferences remain explicitly "
    "unverified. Copy the supplied gap analysis unchanged into opportunity.gap. Record AI and "
    "non-AI alternatives, component evidence, data/tools, limitations, integration, safety, "
    "verification, cost and adoption barriers. Inspect staged prior-art sources for products "
    "and equivalent mechanisms. Empty searches mean unknown novelty. Opportunity validation "
    "Independently deepen the AI analysis in ai_reasoning and non_ai_challenge; give a separate "
    "ai_suitability verdict against concrete alternatives. Opportunity validation "
    "stays unverified_idea, technical feasibility untested, novelty unverified and commercial "
    "validation unvalidated. Do not assert measured advantage, replication or buyer demand. "
    "Track B may have AI advantage unnecessary; do not force it into a product."
)


def query_terms(query: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", query.casefold())) - {"the", "a", "an", "and", "of", "in"}


def repeated_query(query: str, previous: list[str]) -> bool:
    terms = query_terms(query)
    return any(
        terms == query_terms(old)
        or (
            len(terms & query_terms(old)) >= 4
            and len(terms & query_terms(old)) / len(terms | query_terms(old)) >= 0.88
        )
        for old in previous
    )


def priority_score(priority: ResearchPriority, track: str) -> float:
    """Advisory evidence-sensitive allocation, never a validation or authority score."""
    terms = [
        priority.gap_importance,
        priority.gap_evidence,
        priority.distinctiveness,
        priority.plausibility,
        priority.information_gain,
        priority.experimental_feasibility,
        priority.prior_art_uncertainty,
        priority.usefulness,
        priority.historical_progress,
    ]
    if track == "ai_native":
        terms.append(priority.ai_suitability)
    return sum(terms) / priority.research_cost


def stage_for(key: str) -> str:
    if key == "plan":
        return "planning"
    if key.startswith("extract-"):
        return "extraction"
    if key.startswith("gap-"):
        return "gap"
    if key.startswith("review-"):
        return "critique"
    if key.startswith("hypothesis-"):
        return "proposal"
    raise ValueError("Unknown capability inference stage")


def stage_envelope(policy: CapabilityPolicy) -> list[tuple[str, str, int]]:
    # Two admitted directions, and one recovery attempt: extraction/gap/proposal/review x3.
    return [
        ("planning", "RESEARCH_PROPOSALS", 1),
        ("extraction", "RESEARCH_PROPOSALS", 3),
        ("gap", "EXPLORATORY", 3),
        ("proposal", "EXPLORATORY", 3),
        ("critique", "CRITIQUE", 3),
    ]


def opportunity_issues(
    direction: Direction,
    proposal: CapabilityProposal,
    gap: GapAnalysis,
    findings: list[AtomicFinding],
    evidence: list[Evidence],
    *,
    allow_context: bool = False,
) -> list[str]:
    opportunity = proposal.opportunity
    by_id = {f.finding_id: f for f in findings}
    issues = []
    if opportunity.gap != gap:
        issues.append("gap_analysis_changed")
    ids = [*gap.need_finding_ids, *gap.constraint_finding_ids, *opportunity.component_finding_ids]
    if any(identifier not in by_id for identifier in ids):
        return [*issues, "unknown_opportunity_finding"]
    ai_track = isinstance(direction, CapabilityDirection) and direction.track == "ai_native"
    if ai_track and (
        not gap.need_finding_ids
        or any(
            by_id[i].domain.casefold().strip() != direction.second_domain.casefold().strip()
            for i in gap.need_finding_ids
        )
    ):
        issues.append("unmet_need_without_target_evidence")
    if gap.constraint_status == "observed" and not gap.constraint_finding_ids:
        issues.append("observed_constraint_without_evidence")
    if not screen_evidence(
        [by_id[i] for i in ids], evidence, allow_context=allow_context
    ).eligible_for_critique:
        # Deduplicate IDs: a finding can ground both a need and its constraint.
        if not screen_evidence(
            list({i: by_id[i] for i in ids}.values()), evidence, allow_context=allow_context
        ).eligible_for_critique:
            issues.append("invalid_opportunity_evidence")
    if ai_track:
        if gap.ai_advantage != "plausible" or opportunity.ai_suitability != "plausible":
            issues.append("ai_advantage_not_established_as_plausible")
    sources = {s.source_id: s for s in evidence}
    if opportunity.prior_art_status != "unknown" and not opportunity.prior_art_evidence:
        issues.append("prior_art_status_without_evidence")
    for citation in opportunity.prior_art_evidence:
        source = sources.get(citation.source_id)
        if (
            source is None
            or source.scope == "title"
            or citation.quote not in source.excerpt
            or citation.quote.rstrip(".") in source.title
        ):
            issues.append("invalid_opportunity_prior_art")
    if opportunity.prior_art_status == "equivalent":
        issues.append("known_equivalent_opportunity")
    bridge = proposal.bridge
    if direction.first_domain.casefold() != direction.second_domain.casefold():
        if not bridge or not bridge.target_evidence_ids or not bridge.source_finding_ids:
            issues.append("both_domains_require_independent_findings")
        elif {by_id[i].citation.source_id for i in bridge.source_finding_ids if i in by_id} & {
            by_id[i].citation.source_id for i in bridge.target_evidence_ids if i in by_id
        }:
            issues.append("domains_not_independently_supported")
    return issues
