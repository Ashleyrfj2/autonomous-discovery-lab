"""Frozen live packet plus clearly authored controls; no network or paid inference."""

import copy
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from test_capability_discovery import CONFIG

from autodiscover.evidence.chain import verify_chain
from autodiscover.models.contracts import ProviderError
from autodiscover.models.providers import MetaProvider
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import SnapshotStore, Store
from autodiscover.research import discovery_contracts
from autodiscover.research.capability_rehearsal import CapabilityProvider, rehearsal
from autodiscover.research.discovery import ROLES, replay
from autodiscover.research.discovery_contracts import (
    CapabilityDirection,
    CapabilityExtractionV2,
    CapabilityProposal,
    CapabilityProposalV2,
    CapabilityReviewV2,
    DiscoverySpec,
    Evidence,
    GapAnalysis,
)
from autodiscover.research.discovery_quality import screen_proposal
from autodiscover.research.evidence_roles import (
    gap_issues,
    meaningful_unit,
    placeholder_fields,
    proposal_issues,
    usable_findings,
)
from autodiscover.research.retrieval import Fetched
from autodiscover.research.session_cli import _configs

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures/discovery/medium-qualification-evidence-roles.json"
)
SAVED = json.loads(FIXTURE_PATH.read_text())
NEED = "f3-retail-need"
MECHANISM = "f2-rag-mechanism"


def spec():
    return DiscoverySpec.model_validate_json(
        (CONFIG / "discovery-capability-evidence-v3.json").read_text()
    )


def classified_extraction():
    """New analyst labels only; original extraction remains untouched in SAVED."""
    data = copy.deepcopy(SAVED["extraction"])
    data["version"] = "capability-extraction-v2"
    for f in data["findings"]:
        f["evidence_roles"] = (
            ["mechanism"]
            if f["finding_id"] == MECHANISM
            else ["unmet_need", "context"]
            if f["finding_id"] == NEED
            else ["context"]
        )
    data["query"] = ""
    return data


def positive_gap():
    """Authored prospective annotation, not a corrected historical observation."""
    data = copy.deepcopy(SAVED["gap"])
    data.update(
        unmet_need="Retail dispensing practices motivate investigating verification support.",
        need_finding_ids=[NEED],
        root_constraint="Whether access to references is a binding constraint remains untested.",
        constraint_status="speculative",
        constraint_finding_ids=[],
        ai_advantage="plausible",
        ai_advantage_reason="Compare retrieval for variable queries against rules and checklists.",
    )
    return data


def positive_proposal(gap=None):
    """Authored hypothesis using existing passages, explicitly claiming no observed effect."""
    data = copy.deepcopy(SAVED["proposal"])
    gap = positive_gap() if gap is None else gap
    source = next(f for f in SAVED["extraction"]["findings"] if f["finding_id"] == MECHANISM)
    target = next(f for f in SAVED["extraction"]["findings"] if f["finding_id"] == NEED)
    data["hypothesis"].update(
        problem=gap["unmet_need"],
        evidence=[source["citation"], target["citation"]],
        prior_art=[],
        mechanism="Test retrieved verification against a rule-based checker and checklist.",
        rationale="Target context motivates the question; a benefit remains an untested inference.",
        metric="Contraindicated decisions per 100 standardized encounters",
        minimum_effect=5,
        comparator="Rule-based checker and checklist",
        falsifier="Reject if improvement is below five percentage points at matched review time.",
        validation="Blinded standardized vignette comparison; no measured effect is claimed.",
    )
    data["minimum_effect_unit"] = "percentage points"
    data["claims"] = [
        {
            "text": "RAG couples models to external knowledge at inference time.",
            "kind": "empirical",
            "evidence_role": "mechanism",
            "finding_ids": [MECHANISM],
        },
        {
            "text": "Dispensing context motivates verification; effects remain untested.",
            "kind": "inference",
            "evidence_role": None,
            "finding_ids": [NEED],
        },
    ]
    data["bridge"].update(
        target_evidence_ids=[NEED],
        target_outcome_metric=data["hypothesis"]["metric"],
        shared_mechanism="Hypothesize that retrieved references can support a verification step.",
        missing_target_evidence="No comparative benefit or causal driver is established.",
        measurable_prediction="Prospective gain: five percentage points at matched review time.",
    )
    data["opportunity"].update(
        gap=gap,
        ai_suitability=gap["ai_advantage"],
        ai_reasoning="Variable queries may benefit from retrieval; superiority is unmeasured.",
        prior_art_evidence=[],
        prior_art_status="unknown",
        minimum_meaningful_improvement="Five percentage points at matched review time.",
        falsifiable_prediction=data["bridge"]["measurable_prediction"],
    )
    return data


def findings():
    return CapabilityExtractionV2.model_validate(classified_extraction()).findings


def test_saved_context_reaches_gap_but_is_not_empirical_mechanism_or_improvement():
    direction = CapabilityDirection.model_validate(SAVED["direction"])
    sources = [Evidence.model_validate(s) for s in SAVED["sources"]]
    usable = usable_findings(findings(), sources, direction)
    assert NEED in {f.finding_id for f in usable}
    assert next(f for f in usable if f.finding_id == NEED).relation == "context"
    assert gap_issues(direction, GapAnalysis.model_validate(positive_gap()), usable) == []
    p = CapabilityProposalV2.model_validate(positive_proposal())
    screen, failure = screen_proposal(direction, p, usable, sources, role_aware=True)
    assert failure is None and screen.eligible_for_critique
    for role in ["mechanism", "observed_constraint", "measured_improvement", "unmet_need"]:
        bad = p.model_copy(
            update={
                "claims": [
                    p.claims[0].model_copy(update={"finding_ids": [NEED], "evidence_role": role})
                ]
            }
        )
        assert "empirical_claim_role_mismatch_or_context" in proposal_issues(direction, bad, usable)


def test_actual_saved_placeholder_nonunit_and_observed_contradiction_are_rejected():
    direction = CapabilityDirection.model_validate(SAVED["direction"])
    gap = GapAnalysis.model_validate(SAVED["gap"])
    issues = gap_issues(direction, gap, findings())
    assert "observed_constraint_without_evidence" in issues
    assert "contradictory_observed_constraint" in issues
    p = CapabilityProposal.model_validate(SAVED["proposal"])
    issues = proposal_issues(direction, p, findings())
    assert "placeholder_field:hypothesis.problem" in issues
    assert "meaningless_minimum_effect_unit" in issues
    assert not meaningful_unit(SAVED["proposal"]["minimum_effect_unit"])
    assert SAVED["proposal"]["minimum_effect_unit"] == "gap"
    assert SAVED["proposal"]["hypothesis"]["problem"] == "#TODO"


@pytest.mark.parametrize(
    "unit",
    [
        "gap",
        "units",
        "units per unit",
        "score",
        "rate",
        "unknown",
        "#TODO",
        "unverified percentage points",
    ],
)
def test_meaningless_units_rejected(unit):
    assert not meaningful_unit(unit)


@pytest.mark.parametrize(
    "unit",
    [
        "percentage points",
        "seconds",
        "kg/ha",
        "USD",
        "errors per 100 encounters",
        "points on named reliability scale",
    ],
)
def test_concrete_physical_rate_and_named_scale_units(unit):
    assert meaningful_unit(unit)


@pytest.mark.parametrize("field", ["problem", "mechanism", "metric", "comparator", "falsifier"])
def test_placeholders_in_model_fields_are_rejected_but_literal_quotes_are_preserved(field):
    data = positive_proposal()
    data["hypothesis"][field] = "#TODO"
    assert f"placeholder_field:hypothesis.{field}" in placeholder_fields(data)
    assert not placeholder_fields(
        {"citation": {"quote": "A source literally contains #TODO text."}}
    )


def test_observed_constraint_needs_appropriate_domain_role_and_explicit_claim():
    direction = CapabilityDirection.model_validate(SAVED["direction"])
    gap = positive_gap()
    gap.update(
        root_constraint="Reference access limits verification.",
        constraint_status="observed",
        constraint_finding_ids=[NEED],
    )
    assert "observed_constraint_role_or_domain_mismatch" in gap_issues(
        direction, GapAnalysis.model_validate(gap), findings()
    )
    gap["constraint_finding_ids"] = [MECHANISM]
    assert "observed_constraint_role_or_domain_mismatch" in gap_issues(
        direction, GapAnalysis.model_validate(gap), findings()
    )
    p = CapabilityProposalV2.model_validate(positive_proposal(gap))
    assert "observed_constraint_missing_explicit_claim" in proposal_issues(direction, p, findings())


def test_mechanism_is_not_measured_improvement_and_crossfield_contradictions_fail():
    direction = CapabilityDirection.model_validate(SAVED["direction"])
    data = positive_proposal()
    data["claims"][0]["evidence_role"] = "measured_improvement"
    data["opportunity"]["ai_suitability"] = "unnecessary"
    p = CapabilityProposalV2.model_validate(data)
    issues = proposal_issues(direction, p, findings())
    assert "empirical_claim_role_mismatch_or_context" in issues
    assert "contradictory_ai_suitability" in issues


class SavedArchive:
    def fetch(self, url):
        # Frozen captured passages transported through mock bibliography. No external access.
        items = [
            {
                "DOI": f"10.0000/saved-role-{i}",
                "title": [s["title"]],
                "abstract": s["excerpt"].removeprefix(s["title"] + ". "),
            }
            for i, s in enumerate(SAVED["sources"])
        ]
        body = (
            {"message": {"items": items}}
            if "api.crossref.org" in url
            else {"resultList": {"result": []}}
        )
        # Crossref admission limit is three rows. Only the mechanism and need sources are needed.
        if "message" in body:
            body["message"]["items"] = items[:3]
        return Fetched(
            url,
            url,
            canonical(body).encode(),
            "application/json",
            "frozen offline fixture",
            "fixture",
        )


class SavedProvider(CapabilityProvider):
    scenario = "positive"
    seen: list | None = None

    def answer(self, prompt):
        task = prompt["task"]
        if self.seen is not None:
            self.seen.append(copy.deepcopy(prompt))
        if task == "plan":
            ds = []
            for i in range(3):
                d = copy.deepcopy(SAVED["direction"])
                d.update(
                    query=f"qualification evidence case {i}",
                    source_query=f"source evidence case {i}",
                    target_query=f"target evidence case {i}",
                    prior_art_query=f"prior evidence case {i}",
                )
                ds.append(d)
            return {"directions": ds}
        if task.startswith("extract"):
            data = classified_extraction()
            bound = []
            for f in data["findings"]:
                s = next(
                    (s for s in prompt["sources"] if f["citation"]["quote"] in s["excerpt"]), None
                )
                if s:
                    f["citation"]["source_id"] = s["source_id"]
                    bound.append(f)
            data["findings"] = bound
            if self.scenario == "unrelated":
                for f in data["findings"]:
                    if f["finding_id"] == NEED:
                        f["relation"] = "unrelated"
            if self.scenario == "extract_placeholder":
                data["gap"] = "#TODO"
            return data
        if task.startswith("gap"):
            if self.scenario != "unrelated":
                assert any(
                    f["finding_id"] == NEED and f["relation"] == "context"
                    for f in prompt["findings"]
                )
            data = positive_gap()
            if self.scenario == "gap_placeholder":
                data["root_constraint"] = "#TODO"
            if self.scenario == "observed":
                data.update(constraint_status="observed", constraint_finding_ids=[NEED])
            return data
        if task.startswith("hypothesis"):
            data = positive_proposal(prompt["gap_analysis"])
            mapping = {f["finding_id"]: f["citation"] for f in prompt["findings"]}
            data["hypothesis"]["evidence"] = [mapping[MECHANISM], mapping[NEED]]
            if self.scenario == "placeholder":
                data["hypothesis"]["problem"] = "#TODO"
            if self.scenario == "unit":
                data["minimum_effect_unit"] = "gap"
            if self.scenario == "improvement":
                data["claims"][0]["evidence_role"] = "measured_improvement"
            if self.scenario == "no_mechanism":
                data["opportunity"]["component_finding_ids"] = [NEED]
            if self.scenario == "causality":
                data["claims"][1].update(kind="empirical", evidence_role="observed_constraint")
            return {
                "proposal": data,
                "reason": "Authored provisional hypothesis; no observed efficacy.",
            }
        if task.startswith("review"):
            out = super().answer(prompt)
            if self.scenario == "review_placeholder":
                out["capability_rationale"] = "#TODO"
            if self.scenario == "contradictory_review":
                out["constraint_support"] = "supports"
            return out
        return super().answer(prompt)


def run_saved(tmp_path, scenario="positive", wire=False):
    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    lab.fetcher = SavedArchive()
    seen = []
    for role in ROLES:
        p = SavedProvider(role, 0)
        p.scenario = scenario
        p.seen = seen
        lab.router.routes[role] = [p]
    if wire:

        class SimulatedHTTPS(SavedArchive):
            def fetch(self, url):
                return replace(super().fetch(url), provenance="live_https")

        lab.fetcher = SimulatedHTTPS()
        selected = spec()
        configs = _configs(CONFIG / "discovery-capability-meta-medium-v2.json")

        def handler(request):
            body = json.loads(request.content)
            prompt = json.loads(body["messages"][1]["content"])
            role = next(r for r, c in configs.items() if c.model == body["model"])
            provider = SavedProvider(role, 0)
            provider.scenario, provider.seen = scenario, seen
            assert body["response_format"]["json_schema"]["strict"] is True
            assert prompt["prompt_version"] == "capability-v2"
            from autodiscover.research.opportunity import stage_for

            assert selected.capability
            settings = selected.capability.stages[stage_for(prompt["task"])]
            assert body["reasoning_effort"] == settings.reasoning_effort
            assert body["max_completion_tokens"] == settings.max_output_tokens
            assert set(request.extensions["timeout"].values()) == {settings.timeout_seconds}
            return httpx.Response(
                200,
                json={
                    "model": body["model"],
                    "choices": [
                        {
                            "message": {"content": json.dumps(provider.answer(prompt))},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 80,
                        "completion_tokens_details": {"reasoning_tokens": 15},
                    },
                },
            )

        for role, config in configs.items():
            lab.router.routes[role] = [
                MetaProvider(
                    config.model_copy(update={"live_authorized": True}),
                    transport=httpx.MockTransport(handler),
                )
            ]
    identifier = lab.register(spec())
    digest, packet = lab.execute(identifier)
    before = verify_chain(store)
    assert replay(store, identifier) == (digest, packet)
    assert verify_chain(store) == before
    return packet, seen


def test_saved_passages_support_provisional_hypothesis_through_independent_critique(tmp_path):
    packet, seen = run_saved(tmp_path)
    assert packet.critique_coverage is not None and packet.critique_coverage >= 1
    assert any(c.disposition == "external_review_required" for c in packet.candidates)
    assert any(p["task"].startswith("review") for p in seen)
    assert packet.novelty_status == "unverified" and packet.commercial_level == 0
    for c in packet.candidates:
        if c.disposition == "external_review_required":
            assert c.quality and isinstance(c.quality.original.proposal, CapabilityProposalV2)
            assert isinstance(c.quality.original.review, CapabilityReviewV2)
            assert c.quality.original.proposal.opportunity.technical_feasibility == "untested"
            assert c.quality.original.proposal.established_advantage_claimed is False
    assert SAVED["proposal"]["hypothesis"]["problem"] == "#TODO"


@pytest.mark.parametrize(
    "scenario",
    [
        "placeholder",
        "unit",
        "improvement",
        "no_mechanism",
        "causality",
        "observed",
        "contradictory_review",
        "unrelated",
        "extract_placeholder",
        "gap_placeholder",
        "review_placeholder",
    ],
)
def test_unsupported_proposals_stay_rejected(tmp_path, scenario):
    packet, seen = run_saved(tmp_path, scenario)
    assert not any(c.disposition == "external_review_required" for c in packet.candidates)
    if scenario not in {"contradictory_review", "review_placeholder"}:
        assert not any(p["task"].startswith("review") for p in seen)


def test_saved_live_packet_exact_replay_and_fixture_match_without_historical_edits():
    root = os.environ.get("ADL_MEDIUM_PACKET_ROOT")
    if not root:
        pytest.skip("ADL_MEDIUM_PACKET_ROOT must identify a COPY of saved medium qualification")
    with SnapshotStore(Path(root)) as store:
        before = verify_chain(store)
        digest, packet = replay(store, SAVED["child_id"])
        assert digest == SAVED["packet_digest"]
        quality = packet.candidates[0].quality
        assert quality is not None and quality.original.proposal is not None
        assert quality.original.proposal.model_dump(mode="json") == SAVED["proposal"]
        assert quality.original.extraction.model_dump(mode="json") == SAVED["extraction"]
        assert before["hash"] == SAVED["evidence_anchor"]["hash"]
        assert verify_chain(store) == before


def test_new_role_contracts_reach_meta_http_transport_and_keep_accounting(tmp_path, monkeypatch):
    monkeypatch.setenv("META_API_KEY", "fixture-only-placeholder")
    packet, seen = run_saved(tmp_path, wire=True)
    assert packet.critique_coverage is not None and packet.critique_coverage >= 1
    assert int(packet.usage["reasoning_tokens_reported"]) > 0
    assert int(packet.usage["requests"]) == len(seen)
    assert int(packet.usage["uncertain"]) == 0
    assert any(p["task"].startswith("gap") for p in seen)


@pytest.mark.parametrize(
    "name",
    [
        "Extraction",
        "GapAnalysis",
        "ProposalResponse",
        "CapabilityResponse",
        "CapabilityReview",
        "CapabilityPlan",
    ],
)
def test_legacy_wire_schemas_are_identical_to_pre_repair_commit(name):
    gold = json.loads((FIXTURE_PATH.parent / "legacy-capability-schema-sha256.json").read_text())
    schema = getattr(discovery_contracts, name).model_json_schema()
    assert (
        hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        == gold["schemas"][name]
    )


def test_supported_observed_constraint_receives_independent_assessment(tmp_path):
    class Observed(CapabilityProvider):
        def answer(self, prompt):
            result = super().answer(prompt)
            if prompt["task"].startswith("extract"):
                for f in result["findings"]:
                    if "unmet_need" in f["evidence_roles"]:
                        f["relation"] = "supports"
                        f["evidence_roles"].append("observed_constraint")
            if prompt["task"].startswith("gap"):
                target = next(
                    f for f in prompt["findings"] if "observed_constraint" in f["evidence_roles"]
                )
                result.update(
                    root_constraint=target["observation"],
                    constraint_status="observed",
                    constraint_finding_ids=[target["finding_id"]],
                )
            if prompt["task"].startswith("hypothesis"):
                result["proposal"]["claims"].append(
                    {
                        "text": prompt["gap_analysis"]["root_constraint"],
                        "kind": "empirical",
                        "finding_ids": prompt["gap_analysis"]["constraint_finding_ids"],
                        "evidence_role": "observed_constraint",
                    }
                )
            return result

    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    for role in ROLES:
        lab.router.routes[role] = [Observed(role, 0)]
    _, packet = lab.execute(lab.register(spec()))
    assert packet.critique_coverage is not None and packet.critique_coverage >= 1
    candidate = next(c for c in packet.candidates if c.disposition == "external_review_required")
    assert candidate.quality
    assert isinstance(candidate.quality.original.review, CapabilityReviewV2)
    assert candidate.quality.original.review.constraint_support == "supports"


def test_placeholder_plan_stops_before_any_retrieval_and_retains_usage(tmp_path):
    class BadPlan(SavedProvider):
        def answer(self, prompt):
            result = super().answer(prompt)
            if prompt["task"] == "plan":
                result["directions"][0]["question"] = "#TODO"
            return result

    class NoRetrieval(SavedArchive):
        def fetch(self, url):
            pytest.fail("Placeholder planning output must not reach retrieval")

    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    lab.fetcher = NoRetrieval()
    for role in ROLES:
        lab.router.routes[role] = [BadPlan(role, 0)]
    identifier = lab.register(spec())
    with pytest.raises(ProviderError, match="INVALID_PLAN_CONTENT"):
        lab.execute(identifier)
    with store.connection() as db:
        rows = db.execute("SELECT status,usage_json FROM reservations").fetchall()
        assert len(rows) == 1 and rows[0]["status"] == "SETTLED"
        assert json.loads(rows[0]["usage_json"])["output_tokens"] > 0


@pytest.mark.parametrize("role_aware", [False, True])
def test_empty_extraction_round_trips_with_exact_versioned_type(role_aware):
    from autodiscover.research.discovery_contracts import EvidenceScreen, Extraction, QualityAttempt

    extraction = (CapabilityExtractionV2 if role_aware else Extraction)(
        findings=[], gap="", query=""
    )
    attempt = QualityAttempt(
        extraction=extraction,
        proposal=None,
        review=None,
        screen=EvidenceScreen(
            status="needs_substantive_evidence", codes=[], source_bound_findings=0
        ),
    )
    assert QualityAttempt.model_validate_json(attempt.model_dump_json()) == attempt


@pytest.mark.parametrize(
    "unit,effect,invalid",
    [("percentage points", 101, True), ("percentage points", 5, False), ("%", 250, False)],
)
def test_percentage_points_and_relative_changes_have_distinct_bounds(unit, effect, invalid):
    p = CapabilityProposalV2.model_validate(positive_proposal())
    p = p.model_copy(
        update={
            "minimum_effect_unit": unit,
            "hypothesis": p.hypothesis.model_copy(update={"minimum_effect": effect}),
        }
    )
    issues = proposal_issues(CapabilityDirection.model_validate(SAVED["direction"]), p, findings())
    assert ("effect_exceeds_percentage_scale" in issues) == invalid


def test_placeholder_plan_is_a_recorded_session_failure_with_settled_usage(tmp_path):
    from autodiscover.research.session import Session, create_session, session_report
    from autodiscover.research.session_cli import session_preflight
    from autodiscover.research.session_contracts import SessionProfile

    class BadPlan(SavedProvider):
        def answer(self, prompt):
            result = super().answer(prompt)
            if prompt["task"] == "plan":
                result["directions"][0]["question"] = "#TODO"
            return result

    profile = SessionProfile.model_validate_json(
        (CONFIG / "session-capability-qualification-evidence-v3.json").read_text()
    )
    profile = SessionProfile.model_validate(
        {**profile.model_dump(), "max_branches": 1, "pause_after_first_branch": False}
    )
    store = Store(tmp_path)
    configs = _configs(CONFIG / "discovery-capability-meta-medium-v2.json")
    identifier = create_session(
        store, profile, session_preflight(profile, configs)["branch"], live=False
    )

    def factory(branch):
        lab = rehearsal(store, branch)
        for role in ROLES:
            lab.router.routes[role] = [BadPlan(role, branch)]
        return lab

    Session(store, factory).execute(identifier)
    report = session_report(store, identifier)
    assert report["branches_closed"] == 1
    assert report["branches"][0]["error"] == "INVALID_PLAN_CONTENT"
    assert report["usage"]["requests"] == 1 and report["usage"]["uncertain"] == 0
    assert not report["unresolved_reservations"]


@pytest.mark.parametrize("track", ["open_science", "ai_native"])
def test_open_science_preserves_contextual_questions_without_fabricating_user_need(tmp_path, track):
    class ContextOnly(CapabilityProvider):
        def answer(self, prompt):
            result = super().answer(prompt)
            if prompt["task"].startswith("extract"):
                for f in result["findings"]:
                    if "unmet_need" in f["evidence_roles"]:
                        f["evidence_roles"] = ["context"]
            if prompt["task"].startswith("gap"):
                result.update(need_finding_ids=[], ai_advantage="unnecessary")
            if prompt["task"].startswith("review"):
                result.update(need_support="uncertain", ai_necessity="unnecessary")
            return result

    selected = spec()
    assert selected.capability
    selected = selected.model_copy(
        update={"capability": selected.capability.model_copy(update={"tracks": [track]})}
    )
    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    for role in ROLES:
        lab.router.routes[role] = [ContextOnly(role, 0)]
    _, packet = lab.execute(lab.register(selected))
    assert any(c.disposition == "external_review_required" for c in packet.candidates) == (
        track == "open_science"
    )
    assert bool(packet.critique_coverage) == (track == "open_science")
