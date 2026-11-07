"""Launch candidate regression checks; no network or billable model calls."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from autodiscover.research.discovery_sources import _query_relevant
from autodiscover.research.session import _research_memory
from autodiscover.research.session_contracts import BranchOutcome, SessionProfile

PROFILE = (
    Path(__file__).parents[2]
    / "config"
    / "session-capability-forty-five-minute.json"
)


def test_forty_five_minute_profile_bounds() -> None:
    profile = SessionProfile.model_validate_json(PROFILE.read_text())
    assert profile.duration_seconds == 2700
    assert profile.discovery.capability is not None
    assert profile.discovery.capability.version == "capability-v2"
    assert profile.discovery.capability.relevance_screen is True
    assert profile.discovery.capability.stages["planning"].reasoning_effort == "low"
    assert profile.discovery.capability.stages["critique"].reasoning_effort == "medium"
    assert profile.max_model_calls == 13 * profile.max_branches
    assert profile.max_total_tokens == 701824 * profile.max_branches
    assert profile.aggregate_cost_ceiling_usd is not None
    assert profile.max_branches * 1.893824 <= float(profile.aggregate_cost_ceiling_usd)
    assert not profile.pause_after_first_branch


def test_off_topic_research_is_not_treated_as_source_support() -> None:
    assert not _query_relevant(
        "National implementation of Parkinson's disease screening in Thailand",
        "Digital population screening platform implementation and adoption.",
        "rural field maintenance troubleshooting manuals connectivity barriers",
    )
    assert not _query_relevant(
        "Occupational Therapist-Led Smart Home Modification Program",
        "A community practice implementation evaluation.",
        "rural field maintenance troubleshooting manuals connectivity barriers",
    )


def test_relevant_mechanism_and_title_only_prior_art() -> None:
    assert _query_relevant(
        "Orchestrated Retrieval-Augmented Generation with Visual Verification",
        "Engineering compliance checking with source citations.",
        "multimodal retrieval augmented generation verification offline agents",
    )
    assert _query_relevant(
        "Transmission of tacit knowledge",
        "",
        "tacit knowledge apprenticeship embodied skill transmission mechanisms",
    )
    assert not _query_relevant(
        "Clinical applications of smart home sensors",
        "",
        "rural field maintenance troubleshooting manuals connectivity barriers",
    )


def test_profile_is_strictly_serial_and_bounded() -> None:
    raw = json.loads(PROFILE.read_text())
    assert raw["concurrency"] == 1
    assert raw["discovery"]["seconds"] == 1200
    assert raw["max_consecutive_errors"] == 2
    assert raw["max_stagnant_branches"] == 5


def test_prior_branch_evidence_gaps_survive_in_context() -> None:
    older = BranchOutcome(
        number=0,
        child_id="discovery-older",
        direction_notes=[{
            "question": "Can fishing apprentices learn safe navigation?",
            "outcome": "inconclusive",
            "gap": "The target literature did not measure navigation judgment.",
            "issues": ["missing_target_evidence"],
            "next_query": "fisheries apprenticeship navigation safety measured outcomes",
            "evidence_tier": "unreviewed",
        }],
    )
    newer = BranchOutcome(
        number=1,
        child_id="discovery-newer",
        direction_notes=[{
            "question": "Can field engineers use verified offline instructions?",
            "outcome": "inconclusive",
            "gap": "Maintenance field studies were not retrieved.",
            "issues": ["no_source_bound_findings"],
            "next_query": "rural equipment repair technicians controlled study",
            "evidence_tier": "unreviewed",
        }],
    )
    memory = _research_memory([older, newer])
    assert len(memory) == 2
    assert "rural equipment repair technicians controlled study" in memory[0]
    assert "fisheries apprenticeship navigation safety measured outcomes" in memory[1]
    assert all("unreviewed" in note for note in memory)
    assert all(len(note) <= 800 for note in memory)


def test_repeated_questions_only_receive_one_memory_slot() -> None:
    note = {
        "question": "Can field engineers use verified offline instructions?",
        "gap": "No source-bound findings.",
        "outcome": "inconclusive",
        "next_query": "rural repair evaluation",
    }
    memory = _research_memory([
        BranchOutcome(number=0, child_id="discovery-first", direction_notes=[note]),
        BranchOutcome(number=1, child_id="discovery-last", direction_notes=[note]),
    ])
    assert len(memory) == 1


def test_historical_capability_config_does_not_enable_optin_relevance() -> None:
    from autodiscover.research.discovery_contracts import DiscoverySpec

    previous = (
        Path(__file__).parents[2]
        / "config"
        / "session-capability-qualification-evidence-v3.json"
    )
    legacy = SessionProfile.model_validate_json(previous.read_text())
    assert legacy.discovery.capability is not None
    assert legacy.discovery.capability.relevance_screen is False
    assert "relevance_screen" not in legacy.discovery.model_dump(mode="json")["capability"]
    assert (
        DiscoverySpec.model_validate(legacy.discovery.model_dump(mode="json"))
        == legacy.discovery
    )



def test_eighty_dollar_profile_has_extended_hypothesis_output() -> None:
    extended = (
        Path(__file__).parents[2] / "config"
        / "session-capability-forty-five-minute-80usd.json"
    )
    model = SessionProfile.model_validate_json(extended.read_text())
    assert model.duration_seconds == 2700
    assert model.aggregate_cost_ceiling_usd == Decimal("80.00")
    assert model.max_branches == 256
    assert model.max_consecutive_errors == 2
    assert model.discovery.capability is not None
    assert model.discovery.capability.relevance_screen
    assert model.discovery.capability.stages["proposal"].max_output_tokens == 16384
    assert model.discovery.capability.stages["proposal"].timeout_seconds == 110


def test_budget_admission_rejects_request_before_dispatch(tmp_path) -> None:
    from autodiscover.orchestrator.store import Store
    from autodiscover.security.budget import Budget, BudgetError, nano

    store = Store(tmp_path)
    run_id = store.create_run("budget reservation test", {})
    limit = nano(Decimal("0.06"))

    def guard(db, child_id, projected_nano):
        charged = db.execute(
            "SELECT COALESCE(SUM(charged_nano), 0) FROM reservations "
            "WHERE run_id=?", (child_id,)
        ).fetchone()[0]
        if charged + projected_nano > limit:
            raise BudgetError("SESSION_SPEND_LIMIT")

    ledger = Budget(store, admission=guard)
    first = ledger.reserve(
        run_id, "first", "digest-first", Decimal("0.04"), "mock", "fixture"
    )
    assert first
    with pytest.raises(BudgetError, match="SESSION_SPEND_LIMIT"):
        ledger.reserve(
            run_id, "second", "digest-second", Decimal("0.03"), "mock", "fixture"
        )
    assert ledger.totals(run_id)["requests"] == 1


def test_provider_manifest_matches_extended_profile() -> None:
    from autodiscover.models.contracts import ProviderConfig
    from autodiscover.research.session_cli import session_preflight

    root = Path(__file__).parents[2] / "config"
    profile = SessionProfile.model_validate_json(
        (root / "session-capability-forty-five-minute-80usd.json").read_text()
    )
    providers = {
        role: ProviderConfig.model_validate(item)
        for role, item in json.loads(
            (root / "discovery-capability-meta-extended-20261104.json").read_text()
        ).items()
    }
    estimate = session_preflight(profile, providers)
    assert estimate["max_calculated_gross_usd"]
    assert float(estimate["max_calculated_gross_usd"]) <= 80
    assert estimate["max_admitted_branches"] >= 1
    assert estimate["max_parallel_requests"] == 1
