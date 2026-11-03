from decimal import Decimal
from typing import Literal

import pytest

from autodiscover.commercial.contracts import HumanReview, MarketEvidence, Opportunity
from autodiscover.commercial.service import CommercialError, Market
from autodiscover.evidence.chain import verify_chain
from autodiscover.hypotheses.director import Director
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal
from autodiscover.orchestrator.store import Store


def setup(tmp_path, **opportunity_changes):
    store = Store(tmp_path / "runtime")
    run = store.create_run("market gate contract test", {})
    candidate = Director(store).register(run, Hypothesis.model_validate(demo_proposal("test")))
    market = Market(store)
    opportunity = Opportunity.model_validate(
        {
            "candidate_id": candidate,
            "target_user": "operations analyst",
            "economic_buyer": "operations director",
            "problem": "Repeated manual exports consume analyst time",
            "buyer_reachability": "Unvalidated test contact route",
            **opportunity_changes,
        }
    )
    identifier = market.save(run, opportunity)
    return store, run, market, identifier, opportunity


def external(
    market,
    run,
    opportunity_id,
    tmp_path,
    *,
    kind,
    facts,
    subject_role: Literal["user", "buyer", "unknown"] = "buyer",
    amount=None,
):
    # Local contract fixture, not evidence of a real customer, interview, pilot or payment.
    quote = f"Record for {kind}: analyst export problem and the described commitment."
    path = tmp_path / f"{kind}.txt"
    path.write_text(quote)
    source_id = market.add_document(run, path, title="Commercial classification contract fixture")
    source, _ = market.catalog.source(source_id)
    evidence = MarketEvidence(
        origin="external",
        kind=kind,
        source_id=source_id,
        quote=quote,
        subject_role=subject_role,
        buyer_role="operations director",
        amount=amount,
        currency="USD" if amount is not None else None,
    )
    identifier = market.add_evidence(opportunity_id, evidence)
    review = HumanReview(
        accepted=True,
        facts=facts,
        rationale="Test fixture operator attestation only",
        source_digest=source.raw_digest,
    )
    return identifier, review, source_id


def test_external_evidence_levels_require_review_and_remain_independent(tmp_path):
    store, run, market, opportunity, _ = setup(tmp_path)
    assert market.assess(opportunity)["level"] == 0
    problem, review, _ = external(
        market, run, opportunity, tmp_path, kind="problem_report", facts=["real_problem"]
    )
    assert market.assess(opportunity)["level"] == 0
    with pytest.raises(PermissionError):
        market.review(problem, review, actor_kind="model")
    with pytest.raises(PermissionError):
        market.review(problem, review)
    market.review(problem, review, actor_kind="human")
    assert market.assess(opportunity)["level"] == 1
    buyer, review, _ = external(
        market, run, opportunity, tmp_path, kind="buyer_interview", facts=["direct_buyer"]
    )
    market.review(buyer, review, actor_kind="human")
    assert market.assess(opportunity)["level"] == 2
    pilot, review, _ = external(
        market, run, opportunity, tmp_path, kind="pilot_commitment", facts=["serious_adoption"]
    )
    market.review(pilot, review, actor_kind="human")
    assert market.assess(opportunity)["level"] == 3
    payment, review, _ = external(
        market,
        run,
        opportunity,
        tmp_path,
        kind="payment",
        facts=["payment_received"],
        amount=Decimal("100"),
    )
    market.review(payment, review, actor_kind="human")
    assessed = market.assess(opportunity)
    assert assessed["level"] == 4 and assessed["validated"]
    assert "technical_success" not in assessed and "novelty" not in assessed
    assert "not automatically verified" in assessed["limitations"]
    assert verify_chain(store)["verified_events"] >= 10


@pytest.mark.parametrize("origin", ["synthetic", "model_generated", "benchmark"])
def test_synthetic_customers_models_and_benchmarks_never_validate(origin, tmp_path):
    _, _, market, opportunity, _ = setup(tmp_path)
    evidence = market.add_evidence(
        opportunity,
        MarketEvidence(
            origin=origin,
            kind="payment",
            notes="Model claims enormous demand",
            amount=Decimal("99999"),
            currency="USD",
            subject_role="buyer",
        ),
    )
    assert market.assess(opportunity)["level"] == 0
    with pytest.raises(CommercialError, match="cannot qualify"):
        market.review(
            evidence,
            HumanReview(
                accepted=True,
                facts=["real_problem", "payment_received"],
                rationale="Attempted synthetic evidence promotion",
                source_digest="0" * 64,
            ),
            actor_kind="human",
        )


def test_source_change_and_review_withdrawal_remove_validation(tmp_path):
    store, run, market, opportunity, _ = setup(tmp_path)
    evidence, review, source_id = external(
        market,
        run,
        opportunity,
        tmp_path,
        kind="payment",
        facts=["real_problem", "payment_received"],
        amount=Decimal("100"),
    )
    market.review(evidence, review, actor_kind="human")
    assert market.assess(opportunity)["level"] == 4
    rejected = review.model_copy(
        update={"accepted": False, "rationale": "Operator withdraws prior attestation"}
    )
    market.review(evidence, rejected, actor_kind="human")
    assert market.assess(opportunity)["level"] == 0
    market.review(evidence, review, actor_kind="human")
    assert market.assess(opportunity)["level"] == 4
    market.catalog.invalidate(run, source_id, reason="Receipt provenance disputed")
    assert market.assess(opportunity)["level"] == 0
    assert verify_chain(store)["verified_events"] > 5


@pytest.mark.parametrize(
    "buyer,amount",
    [(None, "100"), ("finance director", "100"), ("operations director", "0"), ("unknown", "100")],
)
def test_wrong_buyer_zero_payment_and_unidentified_buyer_cannot_reach_level4(
    tmp_path, buyer, amount
):
    _, run, market, opportunity, _ = setup(tmp_path, economic_buyer=buyer)
    evidence, review, _ = external(
        market,
        run,
        opportunity,
        tmp_path,
        kind="payment",
        facts=["real_problem", "payment_received"],
        amount=Decimal(amount),
    )
    market.review(evidence, review, actor_kind="human")
    assert market.assess(opportunity)["level"] == 1
    if buyer is None:
        assert "economic_buyer" in market.assess(opportunity)["missing_information"]


def test_competitive_claims_are_labelled_and_same_profile_is_run_scoped(tmp_path):
    store, run, market, opportunity_id, opportunity = setup(
        tmp_path,
        competitors=[
            {"name": "Unverified alternative", "description": "A model-suggested competitor"}
        ],
    )
    assert market.assess(opportunity_id)["competition"][0]["status"] == "hypothetical/unvalidated"
    other = store.create_run("another run", {})
    Director(store).register(other, Hypothesis.model_validate(demo_proposal("test")))
    another_id = market.save(other, opportunity)
    assert another_id != opportunity_id
    assert market.opportunity(another_id)[0] == other
    assert market.opportunity(opportunity_id)[0] == run


def test_current_commercial_state_updates_without_changing_technical_or_novelty_results(tmp_path):
    from autodiscover.orchestrator.lab import Lab

    lab = Lab(tmp_path / "runtime")
    run = lab.demo()
    original = lab.report(run)
    market = Market(lab.store)
    candidate = original["assessment"]["hypothesis_id"]
    opportunity = market.save(
        run,
        Opportunity(
            candidate_id=candidate,
            target_user="operations analyst",
            economic_buyer="operations director",
            problem="Repeated manual exports consume analyst time",
        ),
    )
    evidence, review, source_id = external(
        market,
        run,
        opportunity,
        tmp_path,
        kind="payment",
        facts=["real_problem", "payment_received"],
        amount=Decimal("100"),
    )
    market.review(evidence, review, actor_kind="human")
    current = lab.report(run)
    assert current["commercial"]["level"] == 4
    assert current["commercial"]["recorded_level"] == 0
    assert current["commercial"]["opportunity_id"] == opportunity
    assert current["assessment"] == original["assessment"]
    assert current["assessment"]["novelty"] == "unknown"
    market.catalog.invalidate(run, source_id, reason="Operator disputes receipt provenance")
    refreshed = lab.report(run)
    assert refreshed["commercial"]["level"] == 0
    assert not refreshed["commercial"]["validated"]
    assert refreshed["assessment"] == original["assessment"]


def test_collected_public_problem_source_still_needs_human_fact_review(tmp_path):
    from autodiscover.research.retrieval import Fetched

    _, run, market, opportunity, _ = setup(tmp_path)

    class PublicSourceFixture:
        def fetch(self, url):
            return Fetched(
                url,
                url,
                b"The repeated export work consumes hours each week.",
                "text/plain",
                "2026-11-03T00:00:00+00:00",
                "live_https",
            )

    source_id = market.collect_source(
        run,
        "https://example.org/problem",
        title="Public source fixture",
        fetcher=PublicSourceFixture(),
    )
    evidence = market.add_evidence(
        opportunity,
        MarketEvidence(
            origin="external",
            kind="problem_report",
            source_id=source_id,
            quote="The repeated export work consumes hours each week.",
        ),
    )
    assert market.assess(opportunity)["level"] == 0
    source, _ = market.catalog.source(source_id)
    market.review(
        evidence,
        HumanReview(
            accepted=True,
            facts=["real_problem"],
            rationale="Test fixture matches the described problem",
            source_digest=source.raw_digest,
        ),
        actor_kind="human",
    )
    assert market.assess(opportunity)["level"] == 1


def test_payment_without_problem_proof_does_not_establish_commercial_success(tmp_path):
    _, run, market, opportunity, _ = setup(tmp_path)
    evidence, review, _ = external(
        market,
        run,
        opportunity,
        tmp_path,
        kind="payment",
        facts=["payment_received"],
        amount=Decimal("100"),
    )
    market.review(evidence, review, actor_kind="human")
    assert market.assess(opportunity)["level"] == 0
    assert not market.assess(opportunity)["validated"]


def test_strong_commitment_is_reviewed_external_evidence_not_a_model_forecast(tmp_path):
    _, run, market, opportunity, _ = setup(tmp_path)
    evidence, review, _ = external(
        market,
        run,
        opportunity,
        tmp_path,
        kind="strong_commercial_commitment",
        facts=["real_problem", "comparable_commercial_commitment"],
    )
    with pytest.raises(CommercialError, match="different source"):
        market.review(
            evidence, review.model_copy(update={"source_digest": "0" * 64}), actor_kind="human"
        )
    market.review(evidence, review, actor_kind="human")
    result = market.assess(opportunity)
    assert result["level"] == 4
    assert "revenue forecast" in result["limitations"]
