"""Adversarial checks for the read-only, non-authoritative prior-art dossier."""

import pytest

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import SnapshotStore, Store
from autodiscover.research.catalog import Catalog
from autodiscover.research.prior_art import (
    PriorArtComparison,
    PriorArtRequest,
    compile_prior_art_dossier,
)
from autodiscover.research.retrieval import Fetched


def source(catalog: Catalog, run_id: str, *, metadata: bool = False) -> str:
    text = "Method Alpha reduces storage in laboratory measurements."
    fetched = Fetched(
        "https://www.rfc-editor.org/rfc/rfc1951",
        "https://www.rfc-editor.org/rfc/rfc1951",
        text.encode(),
        "text/plain",
        "2026-11-03T00:00:00+00:00",
    )
    return catalog.add(
        run_id,
        fetched,
        title="Synthetic prior-art contract fixture",
        text=text,
        source_kind="publication_metadata" if metadata else "primary_document",
    )


def request(source_id: str | None = None, *, quote: str | None = None) -> PriorArtRequest:
    comparisons = (
        [
            PriorArtComparison(
                source_id=source_id,
                quote=quote or "Method Alpha reduces storage",
                relationship="possible_functional_overlap",
                explanation="The same mechanism may address a similar metric.",
            )
        ]
        if source_id
        else []
    )
    return PriorArtRequest(
        candidate_id="hypothesis-001",
        hypothesis="A reviewed algorithm may reduce storage usage.",
        claimed_mechanism="Repeated sequences can be represented in shorter blocks.",
        falsifiable_prediction="Held-out measurements exceed a preregistered baseline.",
        search_queries=["lossless block compression prior methods"],
        comparisons=comparisons,
    )


def test_read_only_dossier_never_certifies_novelty(tmp_path):
    store = Store(tmp_path)
    run_id = store.create_run("research", {})
    identifier = source(Catalog(store), run_id)
    before = verify_chain(store)
    with SnapshotStore(tmp_path) as snapshot:
        document = compile_prior_art_dossier(Catalog(snapshot), run_id, request(identifier))
    after = verify_chain(store)
    assert before == after
    assert document["assessment"]["novelty"] == "unknown"
    assert document["assessment"]["novelty_verified"] is False
    assert document["coverage"]["primary_document_comparisons"] == 0
    assert any("Fixture" in warning for warning in document["warnings"])
    assert document["assessment"]["possible_overlap_observations"] == 1
    assert document["searches_executed_by_this_command"] == 0
    assert document["comparisons"][0]["exact_quote"] == "Method Alpha reduces storage"
    assert document["comparisons"][0]["verification"].startswith("quote located")


def test_invalid_quote_cannot_masquerade_as_source_evidence(tmp_path):
    store = Store(tmp_path)
    run_id = store.create_run("research", {})
    identifier = source(Catalog(store), run_id)
    with SnapshotStore(tmp_path) as snapshot:
        with pytest.raises(IntegrityError, match="quote"):
            compile_prior_art_dossier(
                Catalog(snapshot), run_id, request(identifier, quote="An invented measured outcome")
            )


def test_cross_run_and_invalidated_sources_fail_closed(tmp_path):
    store = Store(tmp_path)
    first = store.create_run("first", {})
    second = store.create_run("second", {})
    catalog = Catalog(store)
    identifier = source(catalog, first)
    with SnapshotStore(tmp_path) as snapshot:
        with pytest.raises(IntegrityError, match="not registered"):
            compile_prior_art_dossier(Catalog(snapshot), second, request(identifier))
    catalog.invalidate(first, identifier, reason="Original source corrected")
    with SnapshotStore(tmp_path) as snapshot:
        with pytest.raises(IntegrityError, match="Source invalid"):
            compile_prior_art_dossier(Catalog(snapshot), first, request(identifier))


def test_metadata_does_not_count_as_full_method_review(tmp_path):
    store = Store(tmp_path)
    run_id = store.create_run("research", {})
    identifier = source(Catalog(store), run_id, metadata=True)
    with SnapshotStore(tmp_path) as snapshot:
        document = compile_prior_art_dossier(Catalog(snapshot), run_id, request(identifier))
    assert document["coverage"]["primary_document_comparisons"] == 0
    assert document["assessment"]["novelty"] == "unknown"
    assert any("metadata" in warning for warning in document["warnings"])


def test_empty_comparisons_and_duplicate_queries_do_not_fabricate_coverage(tmp_path):
    store = Store(tmp_path)
    run_id = store.create_run("research", {})
    with SnapshotStore(tmp_path) as snapshot:
        document = compile_prior_art_dossier(Catalog(snapshot), run_id, request())
        assert document["coverage"]["submitted_comparisons"] == 0
        bad = request().model_copy(
            update={"search_queries": ["Prior Art", " prior art "]}
        )
        with pytest.raises(ValueError, match="distinct"):
            compile_prior_art_dossier(Catalog(snapshot), run_id, bad)


def test_duplicate_observations_and_recognizable_secrets_rejected(tmp_path):
    store = Store(tmp_path)
    run_id = store.create_run("research", {})
    identifier = source(Catalog(store), run_id)
    baseline = request(identifier)
    duplicated = baseline.model_copy(
        update={"comparisons": baseline.comparisons * 2}
    )
    contaminated = baseline.model_copy(
        update={"claimed_mechanism": "api_key=sk-secret-example-123456789012345"}
    )
    with SnapshotStore(tmp_path) as snapshot:
        with pytest.raises(ValueError, match="Duplicate"):
            compile_prior_art_dossier(Catalog(snapshot), run_id, duplicated)
        with pytest.raises(ValueError, match="credential"):
            compile_prior_art_dossier(Catalog(snapshot), run_id, contaminated)


def test_operator_document_is_eligible_for_method_comparison_not_novelty(tmp_path):
    store = Store(tmp_path)
    run_id = store.create_run("research", {})
    catalog = Catalog(store)
    text = "Method Alpha reduces storage in laboratory measurements."
    fetched = Fetched(
        "https://www.rfc-editor.org/rfc/rfc1951",
        "https://www.rfc-editor.org/rfc/rfc1951",
        text.encode(),
        "text/plain",
        "2026-11-03T00:00:00+00:00",
        provenance="operator_document",
    )
    identifier = catalog.add(
        run_id,
        fetched,
        title="Operator imported document for source-bound review",
        text=text,
        source_kind="primary_document",
    )
    with SnapshotStore(tmp_path) as snapshot:
        dossier = compile_prior_art_dossier(Catalog(snapshot), run_id, request(identifier))
    assert dossier["coverage"]["primary_document_comparisons"] == 1
    assert dossier["assessment"]["novelty"] == "unknown"
    assert dossier["assessment"]["independent_method_review"] == "not_performed"


def test_relabeling_same_passage_is_not_independent_comparison(tmp_path):
    store = Store(tmp_path)
    run_id = store.create_run("research", {})
    identifier = source(Catalog(store), run_id)
    base = request(identifier)
    renamed = base.comparisons[0].model_copy(
        update={"relationship": "possible_difference"}
    )
    with SnapshotStore(tmp_path) as snapshot:
        with pytest.raises(ValueError, match="Duplicate"):
            compile_prior_art_dossier(
                Catalog(snapshot),
                run_id,
                base.model_copy(update={"comparisons": base.comparisons + [renamed]}),
            )
