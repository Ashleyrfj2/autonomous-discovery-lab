"""Authored repair sentinels: executable structure, not independent semantic validation."""

import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from autodiscover.evidence.chain import verify_chain
from autodiscover.models.contracts import GenerationRequest
from autodiscover.orchestrator.store import Store
from autodiscover.research.capability_rehearsal import (
    SOURCE,
    TARGET,
    CapabilityArchive,
    CapabilityProvider,
    rehearsal,
)
from autodiscover.research.discovery import ROLES, replay
from autodiscover.research.discovery_contracts import (
    CapabilityDirection,
    CapabilityPlan,
    CapabilityProposal,
    CapabilityResponse,
    CapabilityReview,
    DiscoverySpec,
    Opportunity,
)
from autodiscover.research.session import _progress, _summarize
from autodiscover.research.session_contracts import BranchIntent, BranchOutcome

CONFIG = Path(__file__).parents[2] / "config"


def specification():
    return DiscoverySpec.model_validate_json((CONFIG / "discovery-capability-v1.json").read_text())


class Mutation(CapabilityProvider):
    scenario = "positive"
    seen: list | None = None

    def generate(self, request: GenerationRequest):
        if self.seen is not None:
            self.seen.append((json.loads(request.prompt)["task"], request))
        return super().generate(request)

    def answer(self, prompt):
        result = super().answer(prompt)
        task = prompt["task"]
        if task == "plan" and self.scenario == "open_science":
            for d in result["directions"]:
                d["track"] = "open_science"
        if task.startswith("extract"):
            if self.scenario == "title":
                for f, s in zip(result["findings"], prompt["sources"], strict=True):
                    f["citation"]["quote"] = s["title"]
            if self.scenario == "irrelevant":
                for f in result["findings"]:
                    f["domain"] = "unrelated forensic DNA"
                    f["relation"] = "unrelated"
        if task.startswith("gap") and self.scenario in {"ordinary", "open_science"}:
            result["ai_advantage"] = "unnecessary"
        if task.startswith("gap") and self.scenario == "no_need":
            result["need_finding_ids"] = []
        if task.startswith("hypothesis"):
            p = result["proposal"]
            if self.scenario == "advantage":
                p["established_advantage_claimed"] = True
            if self.scenario == "prior_art":
                p["opportunity"].update(
                    prior_art_status="equivalent",
                    prior_art_evidence=[prompt["findings"][0]["citation"]],
                )
            if self.scenario == "no_bridge":
                p["bridge"]["variables"] = []
            if self.scenario == "foreign_need":
                p["opportunity"]["gap"]["need_finding_ids"] = ["foreign-finding"]
            if self.scenario == "validated":
                p["opportunity"]["validation_status"] = "commercially_validated_opportunity"
        if task.startswith("review"):
            if self.scenario == "critic_no_ai":
                result["ai_necessity"] = "unnecessary"
            if self.scenario == "critic_no_bridge":
                result["bridge_plausibility"] = "unsupported"
        return result


def run_case(tmp_path, scenario="positive"):
    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    seen = []
    for role in ROLES:
        provider = Mutation(role, 0)
        provider.scenario, provider.seen = scenario, seen
        lab.router.routes[role] = [provider]
    spec = specification()
    if scenario != "positive" and scenario != "open_science":
        assert spec.capability
        spec = spec.model_copy(
            update={"capability": spec.capability.model_copy(update={"tracks": ["ai_native"]})}
        )
    if scenario == "open_science":
        assert spec.capability is not None
        spec = spec.model_copy(
            update={"capability": spec.capability.model_copy(update={"tracks": ["open_science"]})}
        )
    run_id = lab.register(spec)
    digest, report = lab.execute(run_id)
    before = verify_chain(store)
    assert replay(store, run_id) == (digest, report)
    assert verify_chain(store) == before
    return store, report, seen


def test_independent_domains_without_transfer_trial_reach_critique(tmp_path):
    store, packet, seen = run_case(tmp_path)
    assert packet.critique_coverage == 1
    c = next(c for c in packet.candidates if c.disposition == "external_review_required")
    assert c.epistemic_state == "testable_hypothesis"
    assert c.opportunity_status == "evidence_grounded_hypothesis"
    assert c.opportunity is not None and c.quality is not None
    assert c.quality.original.proposal is not None
    assert c.quality.original.proposal.bridge is not None
    assert c.opportunity.technical_feasibility == "untested"
    assert c.opportunity.validation_status == "unverified_idea"
    assert c.opportunity.commercial_validation == "unvalidated"
    assert packet.commercial_level == 0 and packet.novelty_status == "unverified"
    assert c.quality.original.proposal.bridge.target_evidence_ids
    assert isinstance(c.quality.original.proposal, CapabilityProposal)
    assert isinstance(c.quality.original.review, CapabilityReview)
    assert {r.stage for r in packet.searches} == {"source", "target", "prior_art"}
    assert all(r.direction in {0, 1} for r in packet.searches)
    assert all(isinstance(d, CapabilityDirection) for d in packet.plan.directions)
    assert isinstance(packet.plan, CapabilityPlan)
    assert {d.track for d in packet.plan.directions} == {"ai_native", "open_science"}
    assert any("Direct cross-domain experimental proof" in r.prompt for _, r in seen)
    assert SOURCE in str(packet) and TARGET in str(packet)
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0] == len(seen)


@pytest.mark.parametrize(
    "scenario",
    [
        "title",
        "advantage",
        "ordinary",
        "prior_art",
        "no_need",
        "no_bridge",
        "foreign_need",
        "irrelevant",
        "critic_no_ai",
        "critic_no_bridge",
    ],
)
def test_unsafe_or_unjustified_candidates_do_not_advance(tmp_path, scenario):
    _, packet, _ = run_case(tmp_path, scenario)
    assert not any(c.disposition == "external_review_required" for c in packet.candidates)
    assert packet.commercial_level == 0
    if scenario == "prior_art":
        assert any(
            r.failure == "known_prior_art"
            for c in packet.candidates
            if c.quality
            for r in c.quality.recovery
        )
    if scenario in {"title", "irrelevant"}:
        assert packet.critique_coverage == 0


def test_open_science_does_not_require_ai(tmp_path):
    _, packet, _ = run_case(tmp_path, "open_science")
    assert any(c.disposition == "external_review_required" for c in packet.candidates)
    assert all(c.track == "open_science" for c in packet.candidates)


def test_model_cannot_promote_validation_state(tmp_path):
    from autodiscover.models.contracts import ProviderError

    with pytest.raises(ProviderError, match="INVALID_STRUCTURED_RESPONSE"):
        run_case(tmp_path, "validated")


def test_direction_bound_summary_never_joins_other_gap(tmp_path):
    _, packet, _ = run_case(tmp_path, "irrelevant")
    traces = packet.quality_closed_directions
    assert traces is not None
    assert len(traces) == 2
    for index, trace in list(traces.items()):
        traces[index] = trace.model_copy(
            update={
                "original": trace.original.model_copy(
                    update={
                        "extraction": trace.original.extraction.model_copy(
                            update={"gap": f"UNIQUE GAP FOR DIRECTION {index}"}
                        )
                    }
                )
            }
        )
    intent = BranchIntent(number=0, child_id=packet.run_id, specification=packet.specification)
    outcome = _summarize(intent, "0" * 64, packet, [])
    for note in outcome.direction_notes:
        i = note["direction"]
        assert note["question"] == packet.plan.directions[i].question
        # Failed screen issues also remain direction-specific, never a different trace's gap.
        assert str(1 - i) not in note["gap"]
        assert note["source_ids"] == sorted(
            {f.citation.source_id for f in traces[i].original.extraction.findings}
        )


def test_new_articles_alone_are_not_research_advancement():
    outcomes = [
        BranchOutcome(
            number=i, child_id=f"child-{i}", publications=[f"paper-{i}"], excerpts=[f"excerpt-{i}"]
        )
        for i in range(6)
    ]
    series, stagnant, _ = _progress(outcomes)
    assert stagnant == 6 and all(r["stagnant"] for r in series)
    outcomes.append(BranchOutcome(number=6, child_id="child-6", knowledge=["supported-finding"]))
    assert _progress(outcomes)[1] == 0
    outcomes.append(BranchOutcome(number=7, child_id="child-7", knowledge=["supported-finding"]))
    assert _progress(outcomes)[1] == 1


def test_stage_settings_are_request_local_and_part_of_identity(tmp_path):
    _, _, seen = run_case(tmp_path)
    for task, request in seen:
        expected = (
            "medium"
            if task == "plan" or task.startswith("gap")
            else ("low" if task.startswith("extract") else "high")
        )
        assert request.reasoning_effort == expected
        assert request.max_output_tokens == (8192 if expected == "high" else 4096)
        assert request.timeout_seconds in {20, 30, 45}
    old = GenerationRequest(prompt="historical request")
    assert "reasoning_effort" not in old.model_dump() and "timeout_seconds" not in old.model_dump()


def test_invalid_policy_and_strict_nested_schema():
    spec = specification().model_dump()
    spec["capability"]["stages"].pop("critique")
    with pytest.raises(ValidationError):
        DiscoverySpec.model_validate(spec)
    for schema in [CapabilityResponse.model_json_schema(), CapabilityReview.model_json_schema()]:

        def check(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    assert node.get("additionalProperties") is False
                    assert set(node["properties"]) == set(node.get("required", []))
                for value in node.values():
                    check(value)
            elif isinstance(node, list):
                for value in node:
                    check(value)

        check(schema)
    assert set(get_args(Opportunity.model_fields["validation_status"].annotation)) == {
        "unverified_idea"
    }


def test_near_identical_queries_are_suppressed():
    from autodiscover.research.opportunity import repeated_query

    assert repeated_query(
        "causal graph sensor verification industrial monitoring studies",
        ["industrial monitoring sensor verification causal graph studies the"],
    )
    assert not repeated_query(
        "clinical triage error attribution", ["aviation taxonomy manufacturing defects"]
    )


@pytest.mark.parametrize("irrelevant", [False, True])
def test_targeted_recovery_requires_relevant_new_findings(tmp_path, irrelevant):
    from urllib.parse import parse_qs, urlsplit

    from autodiscover.orchestrator.durability import canonical
    from autodiscover.research.retrieval import Fetched

    class RecoveryArchive(CapabilityArchive):
        def fetch(self, url):
            q = parse_qs(urlsplit(url).query).get("query.bibliographic", [""])[0]
            if q == "matched field sensor conflict evidence":
                body = {
                    "message": {
                        "items": [
                            {
                                "DOI": "10.0000/synthetic-recovery",
                                "title": ["Synthetic recovery context"],
                                "abstract": "A synthetic study found conflicts during startup.",
                            }
                        ]
                    }
                }
                return Fetched(
                    url,
                    url,
                    canonical(body).encode(),
                    "application/json",
                    "2026-11-04T00:00:00Z",
                    "fixture",
                )
            return super().fetch(url)

    class RecoveryProvider(CapabilityProvider):
        def answer(self, prompt):
            result = super().answer(prompt)
            task = prompt["task"]
            if task.startswith("extract") and irrelevant:
                for f in result["findings"]:
                    if "startup" in f["observation"]:
                        f["relation"], f["domain"] = "unrelated", "unrelated ecology"
            if task.startswith("hypothesis") and "revision" in task:
                new = next(f for f in prompt["findings"] if "startup" in f["observation"])
                result["proposal"]["hypothesis"]["evidence"].append(new["citation"])
                result["proposal"]["hypothesis"]["validation"] = (
                    "Restrict paired sensor evaluation to startup conditions."
                )
                result["proposal"]["claims"].append(
                    {
                        "text": new["observation"],
                        "kind": "empirical",
                        "finding_ids": [new["finding_id"]],
                    }
                )
            if task.startswith("review") and "revision" not in task:
                result["objections"][0].update(
                    material=True,
                    issue="Need startup field context before defining the comparator.",
                    query="matched field sensor conflict evidence",
                    expected_information=5,
                    effort=1,
                )
            return result

    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    lab.fetcher = RecoveryArchive()
    for role in ROLES:
        lab.router.routes[role] = [RecoveryProvider(role, 0)]
    _, report = lab.execute(lab.register(specification()))
    trace = report.candidates[0].quality
    assert trace is not None and trace.revised is not None
    assert (
        len([s for s in report.searches if s.query == "matched field sensor conflict evidence"])
        == 1
    )
    if irrelevant:
        assert trace.revised.proposal is None
        assert trace.recovery[-1].failure == "no_new_evidence"
        assert report.candidates[0].disposition == "rejected"
    else:
        assert trace.revised.valid_review and trace.revised.proposal
        assert report.candidates[0].disposition == "external_review_required"
        assert report.candidates[0].revised is not None
        assert "startup" in report.candidates[0].revised.validation


@pytest.mark.parametrize("completion_limit", [4096, 8192])
def test_meta_wire_stage_overrides_and_exact_cache(tmp_path, monkeypatch, completion_limit):
    from dataclasses import replace

    import httpx

    from autodiscover.models.contracts import ProviderConfig
    from autodiscover.models.providers import MetaProvider
    from autodiscover.research.session_cli import _configs

    monkeypatch.setenv("META_API_KEY", "fixture-only-placeholder")
    store = Store(tmp_path)
    lab = rehearsal(store, 0)

    class SimulatedHTTPS(CapabilityArchive):
        def fetch(self, url):
            # Exercise live-provenance admission with a transport fixture, never live evidence.
            return replace(super().fetch(url), provenance="live_https")

    lab.fetcher = SimulatedHTTPS()
    wire = []
    configs = _configs(CONFIG / "discovery-capability-meta.json")

    def handler(request):
        body = json.loads(request.content)
        prompt = json.loads(body["messages"][1]["content"])
        wire.append((prompt["task"], body))
        role = next(r for r, c in configs.items() if c.model == body["model"])
        answer = CapabilityProvider(role, 0).answer(prompt)
        return httpx.Response(
            200,
            json={
                "model": body["model"],
                "choices": [{"message": {"content": json.dumps(answer)}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 80,
                    "completion_tokens_details": {"reasoning_tokens": 15},
                },
            },
        )

    for role, config in configs.items():
        authorized = ProviderConfig.model_validate({**config.model_dump(), "live_authorized": True})
        lab.router.routes[role] = [MetaProvider(authorized, transport=httpx.MockTransport(handler))]
    spec = specification()
    assert spec.capability
    spec = spec.model_copy(
        update={
            "capability": spec.capability.model_copy(
                update={
                    "stages": {
                        k: v.model_copy(
                            update={"max_output_tokens": min(v.max_output_tokens, completion_limit)}
                        )
                        for k, v in spec.capability.stages.items()
                    }
                }
            )
        }
    )
    run_id = lab.register(spec)
    digest, packet = lab.execute(run_id)
    assert packet.critique_coverage == 1 and int(packet.usage["reasoning_tokens_reported"]) > 0
    before = len(wire), verify_chain(store)
    assert replay(store, run_id) == (digest, packet)
    assert (len(wire), verify_chain(store)) == before
    for task, body in wire:
        expected = (
            "medium"
            if task == "plan" or task.startswith("gap")
            else ("low" if task.startswith("extract") else "high")
        )
        assert body["reasoning_effort"] == expected
        assert body["max_completion_tokens"] == (completion_limit if expected == "high" else 4096)
        assert body["response_format"]["json_schema"]["strict"] is True


def test_two_distinct_provisional_mechanisms_receive_two_critiques(tmp_path):
    class Distinct(CapabilityProvider):
        def answer(self, prompt):
            result = super().answer(prompt)
            if prompt["task"] == "hypothesis-1":
                result["proposal"]["hypothesis"].update(
                    mechanism="Choose informative interventions using active learning.",
                    problem="Minimize experimental measurements needed for a fault diagnosis.",
                )
            return result

    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    for role in ROLES:
        lab.router.routes[role] = [Distinct(role, 0)]
    _, packet = lab.execute(lab.register(specification()))
    assert packet.critique_coverage == 2
    assert len([c for c in packet.candidates if c.disposition == "external_review_required"]) == 2


def test_open_science_can_explore_without_user_problem_or_ai(tmp_path):
    class Scientific(CapabilityProvider):
        def answer(self, prompt):
            result = super().answer(prompt)
            if prompt["task"].startswith("gap"):
                result.update(
                    need_finding_ids=[],
                    ai_advantage="unnecessary",
                    unmet_need="Open question about sensor causal relationships.",
                )
            if prompt["task"].startswith("review"):
                result.update(ai_necessity="unnecessary", need_support="uncertain")
            return result

    store = Store(tmp_path)
    lab = rehearsal(store, 0)
    spec = specification()
    assert spec.capability
    spec = spec.model_copy(
        update={"capability": spec.capability.model_copy(update={"tracks": ["open_science"]})}
    )
    for role in ROLES:
        lab.router.routes[role] = [Scientific(role, 0)]
    _, packet = lab.execute(lab.register(spec))
    assert any(c.disposition == "external_review_required" for c in packet.candidates)
    assert packet.commercial_level == 0


@pytest.mark.parametrize(
    "change", [{"reasoning_effort": "high"}, {"max_output_tokens": 8192}, {"timeout_seconds": 45}]
)
def test_stage_change_cannot_reuse_settled_identity(tmp_path, change):
    from autodiscover.models.providers import MockProvider
    from autodiscover.models.router import Router
    from autodiscover.security.budget import BudgetError

    store = Store(tmp_path)
    run_id = store.create_run("Stage request identity test", {})
    router = Router(store, {"stage": [MockProvider()]})
    request = GenerationRequest(
        prompt="Fixture stage request",
        reasoning_effort="low",
        max_output_tokens=4096,
        timeout_seconds=20,
    )
    router.generate(run_id, "stage", request, key="stable-request")
    with pytest.raises(BudgetError, match="identity conflict"):
        router.generate(run_id, "stage", request.model_copy(update=change), key="stable-request")
    assert router.budget.totals(run_id)["requests"] == 1


def test_stage_timeout_retains_ambiguous_reservation(tmp_path, monkeypatch):
    import time

    import httpx

    from autodiscover.models.contracts import ProviderError
    from autodiscover.models.providers import MetaProvider
    from autodiscover.models.router import Router
    from autodiscover.research.session_cli import _configs
    from autodiscover.security.budget import BudgetError

    monkeypatch.setenv("META_API_KEY", "fixture-only-placeholder")
    config = _configs(CONFIG / "discovery-capability-meta.json")[ROLES[0]]
    calls = []

    def transport(_request):
        calls.append(1)
        time.sleep(0.06)
        return httpx.Response(500)

    provider = MetaProvider(
        config.model_copy(update={"live_authorized": True}),
        transport=httpx.MockTransport(transport),
    )
    store = Store(tmp_path)
    run_id = store.create_run("Ambiguous per-stage timeout test", {"allow_live_inference": True})
    router = Router(store, {"stage": [provider]})
    request = GenerationRequest(
        prompt="Fixture timeout request",
        reasoning_effort="high",
        max_output_tokens=8192,
        timeout_seconds=0.01,
    )
    with pytest.raises(ProviderError, match="PROVIDER_TIMEOUT"):
        router.generate(run_id, "stage", request, key="bounded-stage")
    with pytest.raises(BudgetError, match="reconciliation"):
        router.generate(run_id, "stage", request, key="bounded-stage")
    assert calls == [1]
    assert router.budget.totals(run_id)["uncertain"] == 1
