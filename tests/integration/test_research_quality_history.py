"""Opt-in regressions against a copy of the original live SQLite and CAS."""

import os
from pathlib import Path

import pytest

from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import SnapshotStore
from autodiscover.research.discovery import replay
from autodiscover.research.discovery_contracts import AtomicFinding, Evidence, MechanismBridge
from autodiscover.research.quality import decide_recovery, screen_evidence

LIVE_ROOT = os.environ.get("ADL_HISTORICAL_DISCOVERY_ROOT")
RUN_ID = "discovery-9d86dedf2a48c9f787c13e5284e81b1a8e38e495ccfdbdd9e435723a8f144c4e"
PACKET = "7259db666e6d4842df8f40eb66ab90ab07b217295812f56ab84359ffb934034e"


@pytest.fixture
def historical():
    if not LIVE_ROOT:
        pytest.skip("ADL_HISTORICAL_DISCOVERY_ROOT must point to a copy of the original live run")
    with SnapshotStore(Path(LIVE_ROOT)) as store:
        before = verify_chain(store)
        digest, report = replay(store, RUN_ID)
        assert digest == PACKET
        assert replay(store, RUN_ID) == (digest, report)
        assert verify_chain(store) == before
        assert report.usage["requests"] == 4
    return report, {s.source_id: s for receipt in report.searches for s in receipt.evidence}


def test_authentic_cell_title_spans_are_not_findings(historical):
    report, by_id = historical
    cell = next(candidate for candidate in report.candidates if candidate.direction == 1)
    assert cell.original_review is None and cell.disposition == "rejected"
    findings = []
    sources: list[Evidence] = []
    for index, citation in enumerate(cell.original.evidence):
        source = by_id[citation.source_id]
        assert source.scope == "abstract" and citation.quote in source.excerpt
        assert citation.quote.rstrip(".") in source.title
        sources.append(source)
        findings.append(
            AtomicFinding(
                finding_id=f"historical-{index}",
                citation=citation,
                location="abstract",
                domain="resurrection plant biology",
                method="No method in the cited span",
                observation="No observed result in the cited span",
                limitations="Cited title has no mammalian post-rehydration viability result.",
            )
        )
    result = screen_evidence(findings, sources)
    assert result.source_bound_findings == 0
    assert set(result.codes) == {"title_or_metadata_as_empirical_evidence"}
    # A new experiment-design query could resolve the gap. No new evidence is assumed.
    assert decide_recovery("title_as_result", revisions_used=0).action == "retrieve"
    assert (
        decide_recovery(
            "title_as_result",
            revisions_used=0,
            query_already_attempted=True,
        ).action
        == "inconclusive"
    )


def test_authentic_acoustic_source_supports_analogy_only(historical):
    report, by_id = historical
    acoustic = next(candidate for candidate in report.candidates if candidate.direction == 0)
    assert acoustic.original_review is not None and acoustic.disposition == "rejected"
    hypothesis = acoustic.original
    assert "No novelty or experimental success is claimed." in hypothesis.novelty_claim
    title, rock = hypothesis.evidence
    assert by_id[title.source_id].scope == "title"
    source = by_id[rock.source_id]
    assert source.url == "https://doi.org/10.22541/au.174081248.86195051/v1"
    assert source.scope == "abstract" and rock.quote in source.excerpt
    assert "uniaxial compression" in rock.quote and "acoustic emission" in rock.quote
    finding = AtomicFinding(
        finding_id="phyllite-method",
        citation=rock,
        location="abstract",
        domain="rock fracture",
        method="Acoustic emission during uniaxial compression",
        observation="The source describes a phyllite fracture measurement method.",
        limitations="The cited span supplies no machinery-wear performance result.",
    )
    # Prospective design annotation. The original packet and numerical claim are untouched.
    bridge = MechanismBridge(
        source_finding_ids=[finding.finding_id],
        source_domain="rock fracture",
        target_domain="machinery wear",
        shared_mechanism="Damage events can emit elastic waves.",
        domain_mismatches=["Uniaxial phyllite compression versus moving lubricated machinery"],
        target_outcome_metric="Lead time in seconds at a fixed false alarm rate",
        comparator="Paired vibration alarm on the same independently labeled wear events",
        falsifier="Reject advantage when lead time is no better at the matched false alarm rate.",
        missing_target_evidence="No paired machinery wear measurements under variable load.",
    )
    result = screen_evidence(
        [finding],
        [source],
        bridge.model_copy(update={"established_advantage_claimed": True}),
    )
    assert result.status == "needs_target_evidence"
    provisional = screen_evidence([finding], [source], bridge)
    assert provisional.eligible_for_critique and provisional.technical_advantage == "unverified"
    query = acoustic.original_review.objections[0].query
    assert "bearing" in query and "lubrication" in query
    assert decide_recovery("irrelevant_domain", revisions_used=0).action == "retrieve"
