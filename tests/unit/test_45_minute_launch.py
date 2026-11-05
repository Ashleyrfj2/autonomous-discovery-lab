"""Launch candidate regression checks; no network or billable model calls."""

import json
from pathlib import Path

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
