"""Offline, fail-closed structural evidence and transfer screening for discovery.

This module deliberately does not assert semantic entailment, scientific novelty,
or commercial validation. All model-extracted findings require independent review.
No network, model or provider dispatch is performed here.
"""

from autodiscover.research.discovery_contracts import (
    AtomicFinding as AtomicFinding,
)
from autodiscover.research.discovery_contracts import Evidence, EvidenceScreen, MechanismBridge
from autodiscover.research.discovery_contracts import RecoveryDecision as RecoveryDecision
from autodiscover.research.discovery_contracts import RecoveryFailure as RecoveryFailure

EXTRACTOR_PROMPT_V1 = (
    "You extract atomic findings, not inventions. Read only the supplied source spans. "
    "For each result record source ID, exact quotation, passage location, studied material, "
    "method, observed outcome and limits. Titles, keywords and bibliographic metadata are "
    "not empirical results. If no source passage supports an observed outcome, return no finding. "
    "Never invent numerical results or claim full-text access from an abstract. All extracted "
    "claims remain unreviewed until separately checked against source context."
)
BRIDGE_PROMPT_V1 = (
    "Given source-bound findings and a proposed target, identify a shared physical or causal "
    "mechanism, differences in material, environment, scale and confounders, and target-domain "
    "prior art. State precisely where inference starts. If target-domain evidence is absent, "
    "mark any performance transfer untested, never established. Provide a measurable target "
    "prediction, an existing comparator and a falsifying result. A shared keyword is not a bridge."
)
HYPOTHESIS_PROMPT_V1 = (
    "Create competing, falsifiable hypotheses from valid finding IDs. Distinguish empirical facts "
    "from untested inferences and desired effects. Give target, mechanism, baseline, metric, "
    "alternative explanation, disconfirming test and missing evidence. Do not invent quotations, "
    "novelty, technical superiority or buyer demand. Return no proposal if no useful testable "
    "hypothesis is possible."
)
CRITIC_PROMPT_V1 = (
    "Independently inspect the original linked passages, not just the hypothesis summary. "
    "Challenge context and negation, source independence, causal inference, prior art, target "
    "conditions, comparator, measurement and confounding alternatives. Return specific source IDs "
    "for factual claims and an exact retrieval question for resolvable evidence gaps. Separate "
    "a testable but unproven bridge from a false claim of established advantage."
)
RECOVERY_PROMPT_V1 = (
    "Given a typed failure, attempted searches and revision lineage, select targeted retrieval, "
    "revision, rejection or inconclusive. An invalid or fabricated citation fails closed. Never "
    "reuse the same search without distinct evidence, invent support to meet a critique quota, "
    "or imply novelty, technical verification or commercial validation."
)


def _normalized(text: str) -> str:
    return " ".join(text.casefold().strip().rstrip(".?!:;").split())


def _findings_screen(
    findings: list[AtomicFinding], evidence: list[Evidence]
) -> tuple[int, list[str], list[str]]:
    sources = {s.source_id: s for s in evidence}
    valid_ids: list[str] = []
    fatal: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()
    for finding in findings:
        if finding.finding_id in seen:
            fatal.append("duplicate_finding_id")
            continue
        seen.add(finding.finding_id)
        source = sources.get(finding.citation.source_id)
        if source is None:
            fatal.append("source_not_in_run_evidence")
            continue
        quote = finding.citation.quote
        if quote not in source.excerpt:
            fatal.append("quote_not_in_captured_excerpt")
            continue
        if source.scope == "title" or _normalized(quote) in _normalized(source.title):
            missing.append("title_or_metadata_as_empirical_evidence")
            continue
        if source.scope != finding.location:
            missing.append("incorrect_document_access_scope")
            continue
        if finding.relation in {"context", "unrelated"}:
            missing.append("finding_not_claim_support")
            continue
        if finding.relation == "contradicts":
            missing.append("contradictory_finding")
            continue
        valid_ids.append(finding.finding_id)
    return len(valid_ids), fatal, missing


def screen_evidence(
    findings: list[AtomicFinding],
    evidence: list[Evidence],
    bridge: MechanismBridge | None = None,
) -> EvidenceScreen:
    """Check provenance structure and transfer claims, not source truth/entailment."""
    valid_count, fatal, missing = _findings_screen(findings, evidence)
    codes = [*fatal, *missing]
    if bridge is not None:
        all_ids = {finding.finding_id for finding in findings}
        if not set(bridge.source_finding_ids).issubset(all_ids):
            codes.append("bridge_uses_unknown_finding")
            fatal.append("bridge_uses_unknown_finding")
        # Target evidence ID may be a finding in this same packet but must bind.
        if not set(bridge.target_evidence_ids).issubset(all_ids):
            codes.append("target_evidence_not_in_findings")
            fatal.append("target_evidence_not_in_findings")
    if fatal:
        return EvidenceScreen(
            status="invalid_source", codes=codes, source_bound_findings=valid_count
        )
    if valid_count == 0 or missing:
        return EvidenceScreen(
            status="needs_substantive_evidence",
            codes=codes or ["no_source_bound_findings"],
            source_bound_findings=valid_count,
        )
    if bridge is not None:
        by_finding = {item.finding_id: item for item in findings}
        target_bound = [
            identifier
            for identifier in bridge.target_evidence_ids
            if identifier in by_finding
            and _normalized(by_finding[identifier].domain) == _normalized(bridge.target_domain)
        ]
        if bridge.established_advantage_claimed and not target_bound:
            return EvidenceScreen(
                status="needs_target_evidence",
                codes=[*codes, "unsupported_established_target_advantage"],
                source_bound_findings=valid_count,
            )
        if not bridge.target_outcome_metric.strip() or not bridge.comparator.strip():
            return EvidenceScreen(
                status="needs_experiment_design",
                codes=[*codes, "missing_comparator_or_metric"],
                source_bound_findings=valid_count,
            )
    return EvidenceScreen(
        status="eligible_for_critique",
        codes=codes,
        source_bound_findings=valid_count,
    )


def decide_recovery(
    failure: RecoveryFailure,
    *,
    revisions_used: int,
    maximum_revisions: int = 1,
    distinct_new_source_count: int = 0,
    query_already_attempted: bool = False,
) -> RecoveryDecision:
    """Pure bounded recovery; does not dispatch retrieval or alter recorded evidence."""
    if failure in {"invalid_source", "invalid_review", "quote_not_in_source", "semantic_mismatch"}:
        return RecoveryDecision(action="reject", reason="Current evidence/claim is invalid")
    if failure == "known_prior_art":
        return RecoveryDecision(
            action="record_prior_art", reason="Retain prior art; narrow only with new evidence"
        )
    if revisions_used < 0 or maximum_revisions < 0 or distinct_new_source_count < 0:
        raise ValueError("Recovery counters cannot be negative")
    if revisions_used >= maximum_revisions:
        return RecoveryDecision(action="inconclusive", reason="Revision allowance exhausted")
    if distinct_new_source_count:
        return RecoveryDecision(
            action="revise", reason="Distinct source evidence warrants one revision"
        )
    if query_already_attempted or failure == "no_new_evidence":
        return RecoveryDecision(action="inconclusive", reason="No new evidence; stop loop")
    return RecoveryDecision(
        action="retrieve", reason="A distinct targeted query may resolve the gap"
    )
