"""Capability-v2 role and consistency gates; not a natural-language truth oracle."""

import re
from collections.abc import Sequence
from typing import Any

from autodiscover.research.discovery_contracts import (
    AtomicFinding,
    CapabilityClaimV2,
    CapabilityDirection,
    CapabilityFindingV2,
    CapabilityProposal,
    Direction,
    Evidence,
    GapAnalysis,
)
from autodiscover.research.quality import screen_evidence

EXTRACTION_V2 = (
    "Extract exact source-bound findings about relevant needs, methods, mechanisms and context. "
    "An intervention outcome or measured improvement is NOT required for contextual relevance. "
    "Classify evidence_roles separately: unmet_need, mechanism, observed_constraint, "
    "measured_improvement, context. Labels remain unverified. Use relation=context for "
    "background or descriptive relevance; this is never proof of causality or efficacy. "
    "Measured improvement requires actual comparative outcome evidence, not a method or need. "
    "Do not expand an observation beyond its quoted passage. Preserve title/access limitations."
)
GAP_V2 = (
    "Relevant target-domain context can identify a need or motivate investigation without proving "
    "its cause or an intervention's benefit. Keep contextual need distinct from source mechanism "
    "and measured improvement. Observed constraints require target-domain finding IDs explicitly "
    "classified observed_constraint with relation=supports. Otherwise use speculative and state "
    "what must be tested. Do not label a constraint observed while saying none was evidenced. "
    "Never use placeholders. Unknown demand and untested effects are valid uncertainties."
)
PROPOSAL_V2 = (
    "Classify each claim's evidence_role; empirical claims require matching supporting findings. "
    "Context may motivate an inference/prediction, never an empirical causal or efficacy claim. "
    "Component and source bridge IDs must support mechanism; target bridge IDs may supply "
    "relevant unmet-need context. Measured improvement is separate and is not required for a "
    "provisional hypothesis. If constraint_status=observed, register its exact root_constraint "
    "text as an empirical observed_constraint claim with its IDs. Copy gap analysis unchanged. "
    "Use concrete effect units such as percentage points, seconds, kg/ha, errors per 100 cases, "
    "or points on a named scale. Generic units, unknown units, TODO and contradictory fields "
    "are invalid. A numeric minimum effect is a prospective threshold, not observed improvement."
)
CRITIC_V2 = (
    "Assess the evidence roles against original quoted passages. Context can support need "
    "relevance, never causal mechanism or measured efficacy. Check every observed constraint "
    "and report constraint_support; use not_claimed for speculative constraints. Challenge "
    "contradictory fields, units, causal/efficacy leaps and any observations exceeding a quote."
)

_PLACEHOLDER = re.compile(
    r"(?i)(?<!\w)#?(?:todo|fixme|tbd)(?!\w)|^\s*(?:placeholder|insert here|\.\.\.)\s*$"
)


def placeholder_fields(value: Any, path: str = "") -> list[str]:
    """Inspect model-authored fields, leaving literal source quotations untouched."""
    if isinstance(value, dict):
        return [
            hit
            for key, item in value.items()
            if key != "quote"
            for hit in placeholder_fields(item, f"{path}.{key}" if path else key)
        ]
    if isinstance(value, list):
        return [
            hit for i, item in enumerate(value) for hit in placeholder_fields(item, f"{path}.{i}")
        ]
    return (
        [f"placeholder_field:{path}"]
        if isinstance(value, str) and _PLACEHOLDER.search(value)
        else []
    )


def roles(finding: AtomicFinding) -> set[str]:
    return set(finding.evidence_roles) if isinstance(finding, CapabilityFindingV2) else set()


def usable_findings(
    findings: Sequence[AtomicFinding], evidence: list[Evidence], direction: Direction
) -> list[AtomicFinding]:
    domains = {
        direction.first_domain.casefold().strip(),
        direction.second_domain.casefold().strip(),
    }
    return [
        finding
        for finding in findings
        if finding.domain.casefold().strip() in domains
        and screen_evidence([finding], evidence, allow_context=True).eligible_for_critique
    ]


def gap_issues(
    direction: Direction, gap: GapAnalysis, findings: Sequence[AtomicFinding]
) -> list[str]:
    issues = placeholder_fields(gap.model_dump())
    by_id = {f.finding_id: f for f in findings}
    ids = [*gap.need_finding_ids, *gap.constraint_finding_ids]
    if any(i not in by_id for i in ids):
        return [*issues, "unknown_gap_finding"]
    ai = isinstance(direction, CapabilityDirection) and direction.track == "ai_native"
    if ai and not gap.need_finding_ids:
        issues.append("unmet_need_without_target_evidence")
    for i in gap.need_finding_ids:
        f = by_id[i]
        if "unmet_need" not in roles(f) or f.domain.casefold().strip() != (
            direction.second_domain.casefold().strip()
        ):
            issues.append("unmet_need_role_or_domain_mismatch")
    if gap.constraint_status == "observed":
        if not gap.constraint_finding_ids:
            issues.append("observed_constraint_without_evidence")
        if re.search(
            r"(?i)none evidenced|no (?:supporting )?(?:evidence|findings?)\b|not evidenced",
            gap.root_constraint,
        ):
            issues.append("contradictory_observed_constraint")
        for i in gap.constraint_finding_ids:
            f = by_id[i]
            if (
                "observed_constraint" not in roles(f)
                or f.relation != "supports"
                or f.domain.casefold().strip() != direction.second_domain.casefold().strip()
            ):
                issues.append("observed_constraint_role_or_domain_mismatch")
    return issues


def meaningful_unit(unit: str) -> bool:
    """Conservative concrete unit syntax; arbitrary named scales need an explicit reference."""
    value = unit.strip()
    if placeholder_fields(value) or re.search(
        r"(?i)unknown|unverified|unspecified|no finding|\bunits?\b", value
    ):
        return False
    if re.fullmatch(r"(?i)%|percent(?:age)?(?: points?)?|percentage points?|basis points?", value):
        return True
    if re.fullmatch(r"(?i)[\w -]{3,60} per (?:\d+ )?[\w -]{3,60}", value):
        return True  # Explicit measured quantity and denominator, e.g. errors per 100 encounters.
    if re.fullmatch(r"(?i)points? on (?:the )?[\w -]{3,70} scale", value):
        return True
    return bool(
        re.fullmatch(
            r"(?i)(?:seconds?|milliseconds?|minutes?|hours?|days?|meters?|metres?|kilograms?|grams?|"
            r"liters?|litres?|joules?|watts?|volts?|bytes?|bits?|dollars?|USD|EUR|kg|mg|g|km|cm|mm|m|"
            r"ms|s|h|Hz|kHz|MHz|J|kJ|W|kW|kWh|V|Pa|kPa|L|mL|MB|GB|Mbps|°C|K)"
            r"(?:\^?[23])?(?:\s*/\s*(?:s|m|h|ha|kg|L|case|cases|sample|samples|request|requests))?",
            value,
        )
    )


def proposal_issues(
    direction: Direction, proposal: CapabilityProposal, findings: Sequence[AtomicFinding]
) -> list[str]:
    issues = placeholder_fields(proposal.model_dump())
    by_id = {f.finding_id: f for f in findings}
    gap, opportunity = proposal.opportunity.gap, proposal.opportunity
    if opportunity.ai_suitability != gap.ai_advantage:
        issues.append("contradictory_ai_suitability")
    if not meaningful_unit(proposal.minimum_effect_unit):
        issues.append("meaningless_minimum_effect_unit")
    # Percentage-point differences of proportions are bounded; relative percent changes need not be.
    if proposal.minimum_effect_unit.strip().casefold() in {"percentage point", "percentage points"}:
        if proposal.hypothesis.minimum_effect > 100:
            issues.append("effect_exceeds_percentage_scale")
    for i in opportunity.component_finding_ids:
        f = by_id.get(i)
        if not f or "mechanism" not in roles(f) or f.relation != "supports":
            issues.append("component_without_mechanism_support")
    if proposal.bridge:
        for i in proposal.bridge.source_finding_ids:
            f = by_id.get(i)
            if not f or "mechanism" not in roles(f) or f.relation != "supports":
                issues.append("bridge_without_mechanism_support")
        for i in proposal.bridge.target_evidence_ids:
            f = by_id.get(i)
            target_roles = {
                "unmet_need",
                "observed_constraint",
                "measured_improvement",
            }
            if isinstance(direction, CapabilityDirection) and direction.track == "open_science":
                target_roles.add("context")
            if not f or not roles(f) & target_roles:
                issues.append("target_bridge_without_relevant_evidence_role")
    for claim in proposal.claims:
        if claim.kind != "empirical":
            continue
        role = claim.evidence_role if isinstance(claim, CapabilityClaimV2) else None
        if role is None:
            issues.append("empirical_claim_without_evidence_role")
        for i in claim.finding_ids:
            f = by_id.get(i)
            if not f or role not in roles(f) or f.relation != "supports":
                issues.append("empirical_claim_role_mismatch_or_context")
    if gap.constraint_status == "observed" and not any(
        isinstance(c, CapabilityClaimV2)
        and c.kind == "empirical"
        and c.evidence_role == "observed_constraint"
        and c.text == gap.root_constraint
        and set(gap.constraint_finding_ids).issubset(c.finding_ids)
        for c in proposal.claims
    ):
        issues.append("observed_constraint_missing_explicit_claim")
    return list(dict.fromkeys(issues))
