"""Multi-model roles and cost-aware *advisory* experiment selection."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

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
    assert len(report["candidate_reviews"]) == 2
    assert report["novelty"] == "unknown"
    assert report["commercial_validation"] == "unvalidated"
    assert all(
        item["critic" if "critic" in item else "critique"]["novelty_verified"] is False
        for item in report["candidate_reviews"]
    )
    assert report["models_not_independent_scientific_oracles"] is True


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
    assert result["selected"][0]["candidate_id"] == "calibrated"
    assert Decimal(result["estimated_reserved_cost_usd"]) <= request.budget_usd
    assert result["remaining_seconds_budget"] >= 0
    assert any(item["candidate_id"] == "overspend" for item in result["excluded"])


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
