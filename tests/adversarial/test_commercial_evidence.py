from typing import Literal

import pytest

from autodiscover.commercial.contracts import HumanReview, MarketEvidence, Opportunity
from autodiscover.commercial.service import CommercialError, Market
from autodiscover.hypotheses.director import Director
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal
from autodiscover.orchestrator.store import Store
from autodiscover.research.catalog import Catalog
from autodiscover.research.retrieval import Fetched


def test_metadata_mock_sources_and_invented_quotes_cannot_be_external_demand(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("reject unverifiable commercial claims", {})
    candidate = Director(store).register(run, Hypothesis.model_validate(demo_proposal("test")))
    market = Market(store)
    opportunity = market.save(
        run, Opportunity(candidate_id=candidate, problem="An unvalidated problem hypothesis")
    )
    catalog = Catalog(store)
    fixture = Fetched(
        "https://example.org",
        "https://example.org",
        b"A claimed payment.",
        "text/plain",
        "2026-11-03T00:00:00+00:00",
    )
    kinds: list[Literal["publication_metadata", "primary_document"]] = [
        "publication_metadata",
        "primary_document",
    ]
    for kind in kinds:
        source_id = catalog.add(
            run, fixture, title="Known mock fixture", text="A claimed payment.", source_kind=kind
        )
        with pytest.raises(CommercialError):
            market.add_evidence(
                opportunity,
                MarketEvidence(
                    origin="external",
                    kind="payment",
                    source_id=source_id,
                    quote="A claimed payment.",
                ),
            )
    document = tmp_path / "document.txt"
    document.write_text("A real source must contain the actual quoted text.")
    source_id = market.add_document(run, document, title="Operator-supplied test document")
    with pytest.raises(CommercialError):
        market.add_evidence(
            opportunity,
            MarketEvidence(
                origin="external",
                kind="payment",
                source_id=source_id,
                quote="An invented payment quote",
            ),
        )


def test_credential_documents_are_rejected_before_artifact_persistence(tmp_path):
    store = Store(tmp_path / "runtime")
    run = store.create_run("credential safety", {})
    market = Market(store)
    credential_document = tmp_path / "receipt.txt"
    credential_document.write_text("API_KEY=fictional-sensitive-sentinel")
    with pytest.raises(CommercialError, match="Credential"):
        market.add_document(run, credential_document, title="Not a valid receipt")
    assert not list((store.root / "artifacts").glob("*/*"))
    env = tmp_path / ".env"
    env.write_text("not read")
    with pytest.raises(CommercialError, match="Environment"):
        market.add_document(run, env, title="Not an evidence source")


def test_commercial_review_projection_cannot_be_reordered_or_deleted(tmp_path):
    from autodiscover.evidence.artifacts import IntegrityError
    from autodiscover.evidence.chain import verify_chain

    store = Store(tmp_path / "runtime")
    run = store.create_run("review audit", {})
    candidate = Director(store).register(run, Hypothesis.model_validate(demo_proposal("test")))
    market = Market(store)
    opportunity = market.save(
        run, Opportunity(candidate_id=candidate, problem="An unvalidated external problem")
    )
    document = tmp_path / "source.txt"
    document.write_text("An external problem report for this unit test.")
    source_id = market.add_document(run, document, title="Test fixture")
    source, _ = market.catalog.source(source_id)
    evidence = market.add_evidence(
        opportunity,
        MarketEvidence(
            origin="external",
            kind="problem_report",
            source_id=source_id,
            quote=document.read_text(),
        ),
    )
    market.review(
        evidence,
        HumanReview(
            accepted=True,
            facts=["real_problem"],
            rationale="Explicit test operator attestation",
            source_digest=source.raw_digest,
        ),
        actor_kind="human",
    )
    assert verify_chain(store)["verified_events"] > 1
    with store.connection(write=True) as db:
        db.execute("DELETE FROM market_reviews")
    with pytest.raises(IntegrityError, match="Commercial projection"):
        verify_chain(store)


def test_piped_input_cannot_impersonate_interactive_human_review(tmp_path):
    import json
    import subprocess
    import sys

    review = tmp_path / "review.json"
    review.write_text(
        json.dumps(
            {
                "accepted": True,
                "facts": ["real_problem"],
                "source_digest": "0" * 64,
                "rationale": "Automated attempt to approve external demand",
            }
        )
    )
    result = subprocess.run(  # noqa: S603 - fixed CLI, temporary test fixture, no shell
        [
            sys.executable,
            "-m",
            "autodiscover.cli",
            "--root",
            str(tmp_path / "runtime"),
            "market-review",
            "fabricated-evidence",
            str(review),
        ],
        input="APPROVE EXTERNAL EVIDENCE\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "interactive human terminal" in result.stderr
