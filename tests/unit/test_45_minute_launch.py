"""Launch candidate regression checks; no network or billable model calls."""

import json
from pathlib import Path

from autodiscover.research.discovery_sources import _query_relevant
from autodiscover.research.session_contracts import SessionProfile


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
