"""Multi-model roles and cost-aware *advisory* experiment selection."""

from decimal import Decimal
from typing import Literal

import pytest
from pydantic import ValidationError

from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.hypotheses.portfolio import (
    CandidateEstimate,
    PortfolioRequest,
    rank_portfolio,
)
from autodiscover.models.contracts import ProviderError
from autodiscover.models.providers import MockProvider
from autodiscover.models.router import Router
from autodiscover.models.teams import ResearchTeam, RoleSeparationError
from autodiscover.orchestrator.store import Store


class Proposer(MockProvider):
    name, model = "mock-generator", "generator-test"


class Explorer(MockProvider):
    name, model = "mock-explorer", "explorer-test"


class Critic(MockProvider):
    name, model = "mock-critic", "critic-test"


def proposal():
    return {
        "question": "Can improved resource allocation reduce material waste?",
        "domain": "logistics",
        "connection_domain": "discrete optimization",
        "prediction": "At least 10 percent fewer wasted units on held-out tasks.",
        "metric": "wasted-units",
        "unit": "units per task",
        "comparator": "current manual assignment",
        "direction": "decrease",
        "minimum_effect": 10,
        "measurement_protocol": "Compare task allocations against a preregistered static baseline.",
        "source_ids": [],
    }


def critique():
    return {
        "assumptions_at_risk": ["Observed task mix may not represent deployment."],
        "methodological_flaws": ["The baseline may be unusually weak."],
        "alternative_explanations": ["Data splitting artifacts explain the gain."],
        "disconfirming_experiment": (
            "Use a newly generated hidden-task split and a stronger independent baseline."
        ),
        "source_ids": [],
    }


def test_three_separate_model_roles_are_not_scientific_authority(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("research teams", {})
    router = Router(
        store,
        {
            "RESEARCH_PROPOSALS": [Proposer([proposal()])],
            "EXPLORATORY": [Explorer([proposal()])],
            "CRITIQUE": [Critic([critique(), critique()])],
        },
    )
    team = ResearchTeam(router)
    report = team.investigate(
        run, topic="resource allocation research", domains=["logistics"], key="team1"
    )
    reviews = report["candidate_reviews"]
    assert isinstance(reviews, list) and len(reviews) == 2
    assert report["novelty"] == "unknown"
    assert report["commercial_validation"] == "unvalidated"
    assert all(
        item["critique"]["novelty_verified"] is False
        for item in reviews
    )
    assert report["models_not_independent_scientific_oracles"] is True
    digest = report["artifact_digest"]
    assert isinstance(digest, str)
    saved = Artifacts(tmp_path / "artifacts").get_json(digest)
    assert saved["candidate_reviews"] == report["candidate_reviews"]
    cursor = verify_chain(store)["seq"]
    repeated = team.investigate(
        run, topic="resource allocation research", domains=["logistics"], key="team1"
    )
    assert repeated["artifact_digest"] == report["artifact_digest"]
    assert verify_chain(store)["seq"] == cursor
    assert store.outputs(run) == []
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM experiment_jobs").fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM events WHERE kind='research_team_reviewed'"
        ).fetchone()[0] == 1
    assert router.budget.totals(run)["requests"] == 4
    assert router.budget.totals(run)["charged_usd"] == "0"

    # A disposable copy of the review packet has to match its event's content address.
    Artifacts(tmp_path / "artifacts").path(digest).write_text("{}")
    with pytest.raises(IntegrityError, match="Artifact digest"):
        verify_chain(store)


def test_role_identity_overlap_rejected(tmp_path):
    store = Store(tmp_path)
    with pytest.raises(RoleSeparationError, match="distinct"):
        ResearchTeam(
            Router(
                store,
                {
                    "RESEARCH_PROPOSALS": [Proposer([proposal()])],
                    "EXPLORATORY": [Proposer([proposal()])],
                    "CRITIQUE": [Critic([critique()])],
                },
            )
        )


def test_critic_cannot_validate_itself_or_invent_source_ids(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("untrusted models", {})
    bad = critique() | {"novelty_verified": True}
    router = Router(
        store,
        {
            "RESEARCH_PROPOSALS": [Proposer([proposal()])],
            "EXPLORATORY": [Explorer([proposal()])],
            "CRITIQUE": [Critic([bad])],
        },
    )
    with pytest.raises(ProviderError, match="INVALID_STRUCTURED_RESPONSE"):
        ResearchTeam(router).investigate(
            run, topic="allocation", domains=["logistics"], key="untrusted1"
        )


def estimate(identifier, family, price, gain, uncertainty, provenance, digest=None):
    return CandidateEstimate(
        candidate_id=identifier,
        family=family,
        estimated_max_cost_usd=Decimal(price),
        estimated_seconds=10,
        expected_information_gain=gain,
        uncertainty=uncertainty,
        provenance=provenance,
        supporting_evidence_digest=digest,
    )


def test_portfolio_is_budget_bounded_and_non_authorizing():
    request = PortfolioRequest(
        budget_usd=Decimal("0.80"),
        seconds_budget=25,
        max_experiments=2,
        candidates=[
            estimate(
                "calibrated", "encoding-v1", "0.30", 0.7, 0.1,
                "independent_calibration", "a" * 64
            ),
            estimate("uncertain", "allocation-v1", "0.30", 1, 0.9, "model_estimate"),
            estimate("overspend", "theoretical", "2.50", 1, 0, "operator_estimate"),
        ],
    )
    result = rank_portfolio(request)
    assert result["advisory_only"] is True
    assert result["execution_authorized"] is False
    assert result["scientific_validity"] == "not_assessed"
    assert result["novelty"] == "unknown"
    selected = result["selected"]
    assert isinstance(selected, list) and selected[0]["candidate_id"] == "calibrated"
    reserved = result["estimated_reserved_cost_usd"]
    assert isinstance(reserved, str) and Decimal(reserved) <= request.budget_usd
    remaining = result["remaining_seconds_budget"]
    assert isinstance(remaining, float) and remaining >= 0
    excluded = result["excluded"]
    assert isinstance(excluded, list)
    assert any(item["candidate_id"] == "overspend" for item in excluded)


def test_portfolio_rejects_duplicate_or_unaudited_calibration():
    case = estimate("one", "encoding-v1", "0", 0.4, 0.3, "model_estimate")
    with pytest.raises(ValueError, match="Duplicate"):
        PortfolioRequest(
            budget_usd=Decimal("1"),
            seconds_budget=20,
            max_experiments=2,
            candidates=[case, case],
        )
    with pytest.raises(ValidationError):
        estimate("notcalibrated", "allocation-v1", "0", 0.9, 0, "independent_calibration")


def test_model_team_rejects_unverified_or_private_sources_before_inference(tmp_path):
    from autodiscover.research.catalog import Catalog
    from autodiscover.research.retrieval import Fetched

    store = Store(tmp_path)
    run = store.create_run("private source review", {})
    catalog = Catalog(store)
    private_text = "Private inspection findings must not be sent to external providers."
    fetched = Fetched(
        "https://example.org/private",
        "https://example.org/private",
        private_text.encode(),
        "text/plain",
        "2026-11-03T00:00:00+00:00",
        provenance="operator_document",
    )
    catalog.add(
        run, fetched, title="Private operator document", text=private_text,
        source_kind="primary_document"
    )
    proposer = Proposer([proposal()])
    team = ResearchTeam(
        Router(
            store,
            {
                "RESEARCH_PROPOSALS": [proposer],
                "EXPLORATORY": [Explorer([proposal()])],
                "CRITIQUE": [Critic([critique(), critique()])],
            },
        )
    )
    with pytest.raises(ValueError, match="Private"):
        team.investigate(run, topic="privacy", domains=["operations"], key="private")
    assert len(proposer.responses) == 1


def test_model_critic_cannot_invent_source_ids(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("citation errors", {})
    invalid = critique() | {"source_ids": ["source-invented"]}
    team = ResearchTeam(
        Router(
            store,
            {
                "RESEARCH_PROPOSALS": [Proposer([proposal()])],
                "EXPLORATORY": [Explorer([proposal()])],
                "CRITIQUE": [Critic([invalid])],
            },
        )
    )
    with pytest.raises(ValueError, match="unavailable sources"):
        team.investigate(run, topic="evidence", domains=["logistics"], key="fake-source")


def test_model_team_rejects_token_bearing_prompt(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("unsafe prompt", {})
    proposer = Proposer([proposal()])
    team = ResearchTeam(
        Router(
            store,
            {
                "RESEARCH_PROPOSALS": [proposer],
                "EXPLORATORY": [Explorer([proposal()])],
                "CRITIQUE": [Critic([critique()])],
            },
        )
    )
    with pytest.raises(ValueError, match="credentials"):
        team.investigate(
            run, topic="api_key=sk-test-secret-123456789012345",
            domains=["logistics"], key="secret",
        )
    assert len(proposer.responses) == 1


def test_reported_model_identity_must_match_route(tmp_path):
    class Impostor(Proposer):
        def generate(self, request):
            return super().generate(request).model_copy(update={"model": Explorer.model})

    store = Store(tmp_path)
    run = store.create_run("routing identity", {})
    router = Router(
        store,
        {
            "RESEARCH_PROPOSALS": [Impostor([proposal()])],
            "EXPLORATORY": [Explorer([proposal()])],
            "CRITIQUE": [Critic([critique()])],
        },
    )
    with pytest.raises(ProviderError, match="PROVIDER_IDENTITY_MISMATCH"):
        ResearchTeam(router).investigate(run, topic="allocation", domains=["logistics"], key="id")
    assert router.budget.totals(run)["requests"] == 1


def test_source_context_uses_only_the_checked_source_selection(tmp_path, monkeypatch):
    from autodiscover.research.catalog import Catalog
    from autodiscover.research.retrieval import Fetched

    store = Store(tmp_path)
    run = store.create_run("source race", {})
    catalog = Catalog(store)
    ids = []
    kinds: tuple[Literal["live_https"], Literal["operator_document"]] = (
        "live_https", "operator_document"
    )
    for kind in kinds:
        url = "https://example.org/" + kind
        ids.append(
            catalog.add(
                run, Fetched(url, url, kind.encode(), "text/plain", "2026-11-03", kind),
                title=kind, text=kind, source_kind="primary_document",
            )
        )
    selections = iter([[ids[0]], [ids[1]]])
    monkeypatch.setattr(Catalog, "sources", lambda self, run_id: next(selections))

    class ObservingProposer(Proposer):
        def generate(self, request):
            assert "operator_document" not in request.prompt
            assert "live_https" in request.prompt
            return super().generate(request)

    cited_critique = critique() | {"source_ids": [ids[0]]}
    router = Router(
        store,
        {
            "RESEARCH_PROPOSALS": [ObservingProposer([proposal() | {"source_ids": [ids[0]]}])],
            "EXPLORATORY": [Explorer([proposal() | {"source_ids": [ids[0]]}])],
            "CRITIQUE": [Critic([cited_critique, cited_critique])],
        },
    )
    ResearchTeam(router).investigate(run, topic="allocation", domains=["logistics"], key="sources")


def test_source_withdrawal_during_proposal_stops_critique_dispatch(tmp_path):
    from autodiscover.research.catalog import Catalog
    from autodiscover.research.retrieval import Fetched

    store = Store(tmp_path)
    run = store.create_run("source withdrawal", {})
    catalog = Catalog(store)
    url = "https://example.org/withdrawn-study"
    source = catalog.add(
        run, Fetched(url, url, b"Public finding", "text/plain", "2026-11-03", "live_https"),
        title="Fixture study", text="Public finding", source_kind="primary_document",
    )

    class WithdrawingProposer(Proposer):
        def generate(self, request):
            result = super().generate(request)
            catalog.invalidate(run, source, reason="Fixture withdrawal during generation")
            return result

    critic = Critic([critique()])
    router = Router(
        store,
        {
            "RESEARCH_PROPOSALS": [WithdrawingProposer([proposal() | {"source_ids": [source]}])],
            "EXPLORATORY": [Explorer([proposal()])],
            "CRITIQUE": [critic],
        },
    )
    with pytest.raises(ValueError, match="source invalidated"):
        ResearchTeam(router).investigate(
            run, topic="allocation", domains=["logistics"], key="withdrawal"
        )
    assert len(critic.responses) == 1
    assert router.budget.totals(run)["requests"] == 1
    with store.connection() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM events WHERE kind='research_team_reviewed'"
        ).fetchone()[0] == 0


def test_portfolio_fractional_time_budget_and_order():
    first = estimate("A", "encoding-v1", "0.1", 0.4, 0.3, "operator_estimate")
    second = first.model_copy(update={"candidate_id": "B"})
    first = first.model_copy(update={"estimated_seconds": 0.1})
    second = second.model_copy(update={"estimated_seconds": 0.2})
    request = PortfolioRequest(
        budget_usd=Decimal("0.2"), seconds_budget=0.3, max_experiments=2,
        candidates=[second, first],
    )
    result = rank_portfolio(request)
    assert result["remaining_seconds_budget"] == 0
    assert result["selected"] == rank_portfolio(
        request.model_copy(update={"candidates": [first, second]})
    )["selected"]


def test_portfolio_rejects_cost_precision_beyond_ledger_units():
    with pytest.raises(ValidationError, match="estimated_max_cost_usd"):
        estimate("tiny", "encoding-v1", "1e-29", 0.4, 0.3, "operator_estimate")
