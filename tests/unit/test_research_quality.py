"""No-network evidence quality sentinels; these are synthetic fixtures, not the live packet."""

from typing import Literal

import pytest

from autodiscover.research.discovery_contracts import Citation, Evidence
from autodiscover.research.quality import (
    AtomicFinding,
    MechanismBridge,
    decide_recovery,
    screen_evidence,
)

SOURCE = "source-" + "a" * 64
OTHER = "source-" + "b" * 64
TITLE = "Acoustic emission for monitoring machine tool wear"
QUOTE = "The measured acoustic response increased with crack growth under laboratory loads."


def source(
    *,
    scope: Literal["title", "abstract", "document"] = "abstract",
    excerpt=QUOTE,
    title=TITLE,
    source_id=SOURCE,
):
    return Evidence(
        source_id=source_id,
        title=title,
        url="https://example.org/fixture",
        publisher="Fictional benchmark",
        published_on="2020-01-01",
        retrieved_at="2026-11-03T00:00:00Z",
        excerpt=excerpt,
        category="publication",
        provenance="fixture_only",
        scope=scope,
        limitation="Synthetic fixture not a real publication or study.",
    )


def finding(
    *,
    quote=QUOTE,
    source_id=SOURCE,
    location: Literal["abstract", "document"] = "abstract",
    relation: Literal["supports", "contradicts", "context", "unrelated"] = "supports",
):
    return AtomicFinding(
        finding_id="F-001",
        citation=Citation(source_id=source_id, quote=quote),
        location=location,
        domain="laboratory rock fracture",
        method="Measure acoustic response under controlled laboratory loads",
        observation="Measured signal increased with crack growth in the fixture",
        limitations="No measurements of target machine wear are provided",
        relation=relation,
    )


def bridge(*, advantage=False, target_ids=None, metric="false alarm rate"):
    return MechanismBridge(
        source_finding_ids=["F-001"],
        source_domain="rock fracture",
        target_domain="machinery wear",
        shared_mechanism="Material change can emit elastic waves detectable by sensors",
        domain_mismatches=["Different material and operational noise"],
        target_evidence_ids=target_ids or [],
        target_outcome_metric=metric,
        comparator="current vibration alarm",
        falsifier="Worse false alarm rate on held-out wear events than baseline",
        established_advantage_claimed=advantage,
    )


def test_title_scope_never_counts_as_empirical_support():
    title_quote = "Acoustic emission for monitoring machine tool wear"
    result = screen_evidence(
        [finding(quote=title_quote, location="document")],
        [source(scope="document", excerpt=title_quote, title=title_quote)],
    )
    assert result.status == "needs_substantive_evidence"
    assert "title_or_metadata_as_empirical_evidence" in result.codes


def test_title_only_source_cannot_pass():
    result = screen_evidence([finding(location="abstract")], [source(scope="title")])
    assert result.status == "needs_substantive_evidence"


def test_unowned_source_id_fails_closed():
    result = screen_evidence([finding(source_id=OTHER)], [source()])
    assert result.status == "invalid_source"
    assert "source_not_in_run_evidence" in result.codes


def test_unmatched_quote_fails_closed():
    result = screen_evidence(
        [finding()], [source(excerpt="A different observed effect under loads")]
    )
    assert result.status == "invalid_source"


def test_wrong_access_scope_does_not_qualify():
    result = screen_evidence([finding(location="document")], [source(scope="abstract")])
    assert result.status == "needs_substantive_evidence"


def test_context_not_misreported_as_support():
    result = screen_evidence([finding(relation="context")], [source()])
    assert result.status == "needs_substantive_evidence"


def test_transfer_advantage_from_rock_to_machinery_requires_target_evidence():
    result = screen_evidence([finding()], [source()], bridge(advantage=True))
    assert result.status == "needs_target_evidence"
    assert not result.eligible_for_critique


def test_provisional_transfer_can_enter_critique_but_cannot_be_verified():
    result = screen_evidence([finding()], [source()], bridge())
    assert result.eligible_for_critique
    assert result.semantic_entailment == "independent_review_required"
    assert result.technical_advantage == "unverified"
    assert result.novelty == "unverified"
    assert result.commercial_level == 0


def test_no_invented_target_finding_ids():
    result = screen_evidence([finding()], [source()], bridge(advantage=True, target_ids=["F-999"]))
    assert result.status == "invalid_source"


def test_duplicate_finding_ids_fail_closed():
    result = screen_evidence([finding(), finding()], [source()])
    assert result.status == "invalid_source"


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("invalid_source", "reject"),
        ("semantic_mismatch", "reject"),
        ("known_prior_art", "record_prior_art"),
        ("missing_target_evidence", "retrieve"),
        ("no_new_evidence", "inconclusive"),
    ],
)
def test_typed_recovery(failure, expected):
    assert decide_recovery(failure, revisions_used=0).action == expected


def test_recovery_requires_distinct_evidence_for_revision():
    assert (
        decide_recovery(
            "missing_target_evidence", revisions_used=0, distinct_new_source_count=1
        ).action
        == "revise"
    )
    assert (
        decide_recovery(
            "missing_target_evidence", revisions_used=0, query_already_attempted=True
        ).action
        == "inconclusive"
    )


def test_recovery_never_exceeds_revision_bound():
    assert (
        decide_recovery(
            "missing_target_evidence", revisions_used=1, distinct_new_source_count=1
        ).action
        == "inconclusive"
    )


def test_relabeling_rock_finding_as_target_evidence_does_not_prove_advantage():
    result = screen_evidence([finding()], [source()], bridge(advantage=True, target_ids=["F-001"]))
    assert result.status == "needs_target_evidence"


def test_no_negative_recovery_counters():
    with pytest.raises(ValueError, match="negative"):
        decide_recovery("missing_target_evidence", revisions_used=-1)


def test_offline_cli_does_not_emit_source_text(tmp_path, capsys):
    import json

    from autodiscover.research.quality_cli import main

    record = {
        "findings": [finding().model_dump(mode="json")],
        "evidence": [source().model_dump(mode="json")],
        "bridge": bridge().model_dump(mode="json"),
    }
    path = tmp_path / "control.json"
    path.write_text(json.dumps(record))
    assert main([str(path)]) == 0
    output = capsys.readouterr().out
    assert "eligible_for_critique" in output
    assert QUOTE not in output
    assert "unverified" in output
