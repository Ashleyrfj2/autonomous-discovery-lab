import json

import pytest

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import Store
from autodiscover.research.catalog import Catalog
from autodiscover.research.intelligence import (
    compare_methods,
    contradiction_candidates,
    questions,
    retrieve_publications,
    synthesize,
)
from autodiscover.research.retrieval import Fetched


class FixtureFetcher:
    def fetch(self, url):
        return Fetched(
            url,
            url,
            json.dumps(
                {
                    "message": {
                        "items": [
                            {
                                "title": ["Existing compression method"],
                                "DOI": "10.1234/fixture",
                                "published": {"date-parts": [[2020, 1, 2]]},
                            }
                        ]
                    }
                }
            ).encode(),
            "application/json",
            "2026-11-03T00:00:00+00:00",
        )


def add(catalog, run, text, title="Document"):
    fetched = Fetched(
        "https://www.rfc-editor.org/test/" + title.replace(" ", "_"),
        "https://www.rfc-editor.org/test/" + title.replace(" ", "_"),
        text.encode(),
        "text/plain",
        "2026-11-03T00:00:00+00:00",
    )
    return catalog.add(run, fetched, title=title, text=text, source_kind="primary_document")


def test_metadata_retrieval_and_synthesis_provenance(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("compression", {})
    catalog = Catalog(store)
    source_ids = retrieve_publications(catalog, run, FixtureFetcher(), "compression", count=1)
    source, text = catalog.source(source_ids[0])
    assert source.doi == "10.1234/fixture"
    assert source.published_on == "2020-1-2"
    assert source.raw_digest and source.text_digest
    synthesis = synthesize(catalog, source_ids, "Is this novel?")
    assert synthesis["novelty"] == "unknown"
    assert synthesis["source_evidence"][0]["source_id"] == source_ids[0]
    assert source.title in text
    assert compare_methods(catalog, source_ids, ["compression"])[0]["source_id"] == source_ids[0]
    assert catalog.search("compression")
    assert len(questions("resource waste", ["gaming", "materials", "consumer"])) == 3
    assert verify_chain(store)["verified_events"] >= 2


def test_quotes_claim_links_and_transitive_invalidation(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("claims", {})
    catalog = Catalog(store)
    source = add(catalog, run, "A reviewed source states compression reduces storage.")
    quote = "compression reduces storage"
    claim = catalog.claim(run, quote, supports=[source], quotes={source: quote})
    derived = catalog.claim(
        run, "A possible application requires testing", supports=[claim], kind="interpretation"
    )
    with pytest.raises(IntegrityError, match="quote"):
        catalog.claim(run, "an invented quote", supports=[source], quotes={source: "invented"})
    with pytest.raises(IntegrityError):
        catalog.claim(run, "unsupported conclusion", supports=[source], quotes={source: quote})
    affected = catalog.invalidate(run, source, reason="source corrected")
    assert set(affected) == {source, claim, derived}
    assert not catalog.node(derived)["valid"]
    assert not catalog.search("application")
    assert catalog.search("application", include_invalid=True)
    with pytest.raises(IntegrityError):
        catalog.source(source)
    with pytest.raises(IntegrityError):
        catalog.claim(run, "more unsupported claims", supports=[claim], kind="interpretation")


def test_possible_conflicts_preserve_both_original_quotes(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("conflicts", {})
    catalog = Catalog(store)
    ids = [
        add(catalog, run, "Method Alpha increases throughput.", "A"),
        add(catalog, run, "Method Alpha decreases throughput.", "B"),
    ]
    conflicts = contradiction_candidates(catalog, ids)
    assert len(conflicts) == 1
    assert {o["source_id"] for o in conflicts[0]["observations"]} == set(ids)
    assert "possible conflict" in conflicts[0]["status"]


def test_changed_source_invalidates_supported_findings_and_prevents_resurrection(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("source changed", {})
    catalog = Catalog(store)
    first = add(catalog, run, "Original supported finding.")
    claim = catalog.claim(
        run,
        "Original supported finding.",
        supports=[first],
        quotes={first: "Original supported finding."},
    )
    replacement = add(catalog, run, "Corrected finding.")
    assert replacement != first
    assert not catalog.node(first)["valid"]
    assert not catalog.node(claim)["valid"]
    assert catalog.node(replacement)["valid"]
    assert verify_chain(store)["verified_events"] >= 5
    with pytest.raises(IntegrityError, match="silently restored"):
        add(catalog, run, "Original supported finding.")
    with store.connection(write=True) as db:
        db.execute("UPDATE research_nodes SET valid=1 WHERE id=?", (claim,))
    with pytest.raises(IntegrityError, match="validity projection"):
        verify_chain(store)
