"""Frozen fixture A/B/C comparison. Model and retrieval responses are scripted."""

import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from test_discovery import CAPTURE_DATE, Scripted, _hypothesis, _plan

from autodiscover.evidence.chain import verify_chain
from autodiscover.models.contracts import Generation, GenerationRequest, Provider, Usage
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import SnapshotStore, Store
from autodiscover.research.discovery import ROLES, Discovery, replay
from autodiscover.research.discovery_contracts import (
    DiscoverySpec,
    Extraction,
    ProposalResponse,
)
from autodiscover.research.quality import (
    EXTRACTOR_PROMPT_V1,
    HYPOTHESIS_PROMPT_V1,
    screen_evidence,
)
from autodiscover.research.retrieval import Fetched

FIXTURE = Path(__file__).parents[1] / "fixtures" / "discovery" / "research-quality-v1.json"
DATA = json.loads(FIXTURE.read_text())
RECOVERY_QUERY = "matched sham ramp viability baseline validation"
MOCK_USAGE = Usage(input_tokens=100, output_tokens=80, reasoning_tokens=0)


class Corpus:
    def __init__(self, case, *, distinct=True):
        self.case = case
        self.distinct = distinct
        self.calls = []

    def fetch(self, url: str) -> Fetched:
        self.calls.append(url)
        parsed = urlsplit(url)
        if parsed.hostname == "api.crossref.org":
            query = parse_qs(parsed.query)["query.bibliographic"][0]
            if query == RECOVERY_QUERY:
                keys = (
                    self.case.get("recovery_sources", []) if self.distinct else self.case["sources"]
                )
            elif query == self.case["query"]:
                keys = self.case["sources"]
            elif query == "base64 transport size":
                keys = self.case.get("second_sources", [])
            else:
                keys = []
            items = []
            for key in keys:
                doi, title, abstract = DATA["sources"][key]
                items.append({"DOI": doi, "title": [title], "abstract": abstract})
            response = {"message": {"items": items}}
        else:
            response = {"resultList": {"result": []}}
        return Fetched(
            url, url, canonical(response).encode(), "application/json", CAPTURE_DATE, "fixture"
        )


def cite(source):
    passage = source["excerpt"].removeprefix(source["title"] + ". ")
    return {"source_id": source["source_id"], "quote": passage}


class FrozenResponse(Scripted):
    def __init__(self, role, calls, case):
        super().__init__(role, calls)
        self.case = case

    def generate(self, request: GenerationRequest) -> Generation:
        prompt = json.loads(request.prompt)
        self.calls.append(prompt["task"])
        return Generation(
            text=canonical(self.answer(prompt)),
            provider=self.name,
            model=self.model,
            usage=MOCK_USAGE,
            cost_usd=Decimal(0),
        )

    def answer(self, prompt):
        task = prompt["task"]
        challenge = self.case["challenge"]
        domains = self.case.get("domains", ["preservation", "preservation"])
        if task == "plan":
            plan = _plan()
            plan["directions"][0].update(
                first_domain=domains[0],
                second_domain=domains[1],
                question=self.case["question"],
                query=self.case["query"],
            )
            if self.case.get("second_sources"):
                plan["directions"][1].update(first_domain=domains[0], second_domain=domains[1])
            return plan
        sources = prompt.get("sources", [])
        if task.startswith("extract"):
            findings = []
            for i, source in enumerate(sources):
                citation = cite(source)
                if challenge == "foreign":
                    citation["source_id"] = "source-" + "f" * 64
                findings.append(
                    {
                        "finding_id": f"F-{i:02}",
                        "citation": citation,
                        "location": "abstract",
                        "domain": domains[0 if i == 0 else 1],
                        "method": "Examine the reported study conditions.",
                        "observation": citation["quote"],
                        "limitations": "The captured source is limited to its indexed text.",
                        "independence_group": "same-fibroblast-study"
                        if challenge == "replication"
                        else None,
                    }
                )
            return {
                "findings": findings,
                "gap": "A matched result may be unavailable.",
                "query": self.case.get("extract_query", ""),
            }
        if task.startswith(("review-", "revision-review-")):
            unresolved = challenge == "recover" and "revision" not in task
            substantive_objections = {
                "negated": (
                    "evidence",
                    "The captured comparison explicitly reports no improvement.",
                ),
                "equivalent": (
                    "prior_art",
                    "The captured review describes prior acoustic tool wear work.",
                ),
                "advantage": (
                    "evidence",
                    "A phyllite study does not establish machinery lead time.",
                ),
                "replication": ("evidence", "Both sources describe the same fibroblast trial."),
            }
            category, objection = substantive_objections.get(
                challenge,
                ("evidence", "Check the matched comparator and context."),
            )
            body = {
                "objections": [
                    {
                        "category": category,
                        "issue": objection,
                        "material": unresolved or challenge in substantive_objections,
                        "evidence": [cite(sources[0])]
                        if challenge in substantive_objections
                        else [],
                        "query": RECOVERY_QUERY if unresolved else "",
                        "expected_information": 5,
                        "effort": 1,
                    }
                ],
                "falsification_test": "Preregister paired outcomes and reject at zero effect.",
            }
            if "proposal" in prompt:
                prior = (
                    "equivalent"
                    if challenge == "equivalent"
                    else "close"
                    if (challenge == "recover" and "revision" in task)
                    else "unknown"
                )
                body.update(
                    claim_assessments=[
                        {
                            "claim_index": 0,
                            "judgment": "contradicts" if challenge == "negated" else "supports",
                            "rationale": "The comparison is assessed against the captured passage.",
                        }
                    ],
                    prior_art_status=prior,
                    prior_art_evidence=(
                        [cite(source) for source in sources]
                        if prior == "equivalent"
                        else [cite(sources[0])]
                        if prior == "close"
                        else []
                    ),
                )
            return body
        findings = prompt.get("findings")
        if findings == []:
            return {"proposal": None, "reason": "No substantive evidence."}
        citations = (
            [item["citation"] for item in findings]
            if findings is not None
            else [cite(source) for source in sources]
        )
        if challenge == "foreign":
            citations[0]["source_id"] = "source-" + "f" * 64
        # Fixed candidate content shared across conditions.
        hypothesis = _hypothesis(
            {
                "task": task,
                "sources": [
                    {"excerpt": citations[0]["quote"], "source_id": citations[0]["source_id"]}
                ],
            }
        )
        claim = {
            "advantage": "Passive acoustic alarms have superior lead time on production wear.",
            "negated": "Warming improved cell viability versus sham.",
            "replication": "Two independent replications established the thaw improvement.",
            "equivalent": "This is the first method to monitor tool wear with acoustic emissions.",
        }.get(challenge, citations[0]["quote"])
        hypothesis.update(
            problem=self.case["question"],
            evidence=citations[:2],
            prior_art=[],
            mechanism=self.case.get("mechanism", f"Test {challenge} mechanism in {task[-1]}."),
            rationale=claim,
            novelty_claim=claim if challenge == "equivalent" else "Novelty unverified.",
            comparator=self.case.get(
                "comparator",
                "Registered sham or conventional baseline under identical loads",
            ),
            metric=self.case.get("metric", "Paired endpoint difference in predefined units"),
            falsifier=self.case.get(
                "falsifier",
                "Disconfirm if paired outcomes fail the preregistered minimum difference.",
            ),
            commercial_test="A synthetic buyer says they would pay $500/mo."
            if challenge == "commercial"
            else "Demand remains unverified.",
        )
        if findings is None:
            return hypothesis
        bridge = None
        if domains[0] != domains[1]:
            bridge = {
                "source_finding_ids": [findings[0]["finding_id"]],
                "source_domain": domains[0],
                "target_domain": domains[1],
                "shared_mechanism": (
                    "Vascular mediators could affect cold-induced peripheral perfusion."
                    if challenge == "historical"
                    else "Material fracture can emit elastic waves detectable by sensors."
                ),
                "domain_mismatches": ["Different populations and operating conditions"],
                "target_evidence_ids": [findings[1]["finding_id"]] if len(findings) > 1 else [],
                "target_outcome_metric": hypothesis["metric"],
                "comparator": hypothesis["comparator"],
                "falsifier": hypothesis["falsifier"],
                "variables": ["Loading or exposure, baseline outcome, confounders"],
                "alternative_explanations": ["A change in background could account for the signal"],
                "existing_approaches": ["Matched control with conventional monitoring"],
                "missing_target_evidence": "No matched target measurement of the proposed effect.",
                "measurable_prediction": "The registered endpoint may improve against baseline.",
            }
        return {
            "proposal": {
                "hypothesis": hypothesis,
                "claims": [
                    {
                        "text": claim,
                        "kind": "empirical",
                        "finding_ids": [item["finding_id"] for item in findings],
                    }
                ],
                "bridge": bridge,
                "established_advantage_claimed": challenge == "advantage",
                "independent_replication_claimed": challenge == "replication",
                "recovery_query": "",
                "minimum_effect_unit": self.case.get("units", "Paired endpoint units"),
            },
            "reason": "",
        }


def run_pipeline(root, case, protocol, *, distinct=True, interrupt=None):
    calls: list[str] = []
    routes: dict[str, list[Provider]] = {
        role: [FrozenResponse(role, calls, case)] for role in ROLES
    }
    corpus = Corpus(case, distinct=distinct)
    lab = Discovery(Router(Store(root), routes), corpus, allow_retrieval=True)
    spec = DiscoverySpec(
        objective="Compare the frozen research-quality sentinel cases.",
        protocol=protocol,
        max_output_tokens=2560,
        retry_limit=0,
    )
    run_id = lab.register(spec, stable=True)
    if interrupt is not None:
        from autodiscover.orchestrator.store import StateError

        with pytest.raises(StateError, match="interrupted"):
            lab.execute(run_id, stop_requested=lambda: interrupt in calls)
    digest, report = lab.execute(run_id)
    before = (len(calls), len(corpus.calls), verify_chain(lab.store))
    with SnapshotStore(root) as store:
        assert replay(store, run_id) == (digest, report)
        assert verify_chain(store) == before[2]
    assert before[:2] == (len(calls), len(corpus.calls))
    return lab, report, calls, corpus


def simple_control(case, evidence):
    """B uses one scripted role, a finding gate and no bridge, recovery or critique."""
    calls = []
    provider = FrozenResponse(ROLES[0], calls, case)
    sources = [source.model_dump(mode="json") for source in evidence]

    def generate(task, instruction, **context):
        return provider.generate(
            GenerationRequest(
                prompt=canonical({"task": task, "instruction": instruction, **context}),
                max_output_tokens=2560,
            )
        ).text

    extraction = Extraction.model_validate_json(
        generate("extract-0", EXTRACTOR_PROMPT_V1, sources=sources)
    )
    gate = screen_evidence(extraction.findings, evidence)
    hypothesis = None
    if gate.eligible_for_critique:
        response = ProposalResponse.model_validate_json(
            generate(
                "hypothesis-0",
                HYPOTHESIS_PROMPT_V1,
                findings=[f.model_dump(mode="json") for f in extraction.findings],
            )
        )
        if response.proposal:
            hypothesis = response.proposal.hypothesis
    return hypothesis, calls


def citation_accuracy(hypothesis, evidence):
    if hypothesis is None:
        return [0, 0]
    excerpts = {source.source_id: source.excerpt for source in evidence}
    citations = hypothesis.evidence + hypothesis.prior_art
    return [sum(c.quote in excerpts.get(c.source_id, "") for c in citations), len(citations)]


@pytest.mark.parametrize("case_id", DATA["cases"])
def test_frozen_abc(tmp_path, case_id):
    case = DATA["cases"][case_id]
    _, a, _, corpus_a = run_pipeline(tmp_path / "a", case, "discovery-v1")
    lab_c, c, calls_c, corpus_c = run_pipeline(tmp_path / "c", case, "discovery-v2")
    a_candidate = next((candidate for candidate in a.candidates if candidate.direction == 0), None)
    c_candidate = next((candidate for candidate in c.candidates if candidate.direction == 0), None)
    a_evidence = [source for receipt in a.searches for source in receipt.evidence]
    c_evidence = [source for receipt in c.searches for source in receipt.evidence]
    b, calls_b = simple_control(case, a.searches[0].evidence)
    assert c.commercial_level == a.commercial_level == case.get("commercial_level", 0)
    assert c.novelty_status == a.novelty_status == "unverified"
    retained = bool(c_candidate and c_candidate.disposition == "external_review_required")
    assert retained == case["expected_retained"]
    assert c.critique_coverage == case.get("critique_coverage", c.critique_coverage)
    if case.get("prior_art_expected"):
        assert c_candidate and c_candidate.scientific_gate.prior_art_identified
    if case_id in {"POS-02", "POS-03"}:
        assert c_candidate and c_candidate.quality and c_candidate.quality.original.proposal
        bridge = c_candidate.quality.original.proposal.bridge
        assert (
            bridge and bridge.missing_target_evidence and not bridge.established_advantage_claimed
        )
    if case_id == "NEG-05":
        assert c_candidate and c_candidate.quality
        groups = {f.independence_group for f in c_candidate.quality.original.extraction.findings}
        assert groups == {"same-fibroblast-study"}
    if case_id == "POS-01":
        assert c_candidate and c_candidate.quality
        assert c_candidate.quality.original.extraction.findings[0].location == "abstract"
    if case_id == "POS-04":
        assert c_candidate and c_candidate.revised and c_candidate.revision_review
        assert "review-revision-0" in calls_c
    if case_id == "NEG-06":
        assert c_candidate and "synthetic buyer" in c_candidate.original.commercial_test
        from autodiscover.research.discovery_validation import (
            CommercialObservation,
            CommercialReview,
            record_commercial_review,
        )

        synthetic = CommercialReview(
            observations=[
                CommercialObservation(
                    citation=c_candidate.original.evidence[0],
                    kind="direct_buyer_or_pilot",
                    buyer_role=c_candidate.original.economic_buyer,
                    interpretation="A synthetic buyer says they would pay.",
                )
            ]
        )
        with pytest.raises(ValueError, match="primary document"):
            record_commercial_review(lab_c.store, c.run_id, 0, synthetic, operator_attested=True)
    trace = c_candidate.quality if c_candidate else (c.quality_closed_directions or {}).get(0)
    a_hypothesis = (a_candidate.revised or a_candidate.original) if a_candidate else None
    c_hypothesis = (c_candidate.revised or c_candidate.original) if c_candidate else None
    rows = {
        "A": (
            bool(a_candidate and a_candidate.disposition == "external_review_required"),
            a_hypothesis,
            a_evidence,
            a.usage["requests"],
            len(corpus_a.calls),
            sum(candidate.original_review is not None for candidate in a.candidates),
            bool(
                a_candidate
                and (
                    a_candidate.scientific_gate.prior_art_identified
                    or (
                        a_candidate.original_review
                        and any(
                            o.category == "prior_art" and o.evidence
                            for o in a_candidate.original_review.objections
                        )
                    )
                )
            ),
            max(0, len(a.searches) - 3),
            bool(a_candidate and a_candidate.revised),
        ),
        "B": (b is not None, b, a.searches[0].evidence, len(calls_b), 0, 0, False, 0, False),
        "C": (
            retained,
            c_hypothesis,
            c_evidence,
            c.usage["requests"],
            len(corpus_c.calls),
            c.critique_coverage,
            bool(c_candidate and c_candidate.scientific_gate.prior_art_identified),
            max(0, len(c.searches) - 3),
            bool(trace and trace.revised and retained),
        ),
    }
    for label, (
        keep,
        hypothesis,
        evidence,
        calls,
        fetches,
        critiques,
        prior,
        searches,
        recovered,
    ) in rows.items():
        print(
            "QUALITY "
            + canonical(
                {
                    "case": case_id,
                    "condition": label,
                    "retained": keep,
                    "expected_retained": case["expected_retained"],
                    "critical_false_acceptance": keep and not case["expected_retained"],
                    "citation_accuracy": citation_accuracy(hypothesis, evidence),
                    "testable_structure_retained": bool(
                        keep
                        and hypothesis
                        and hypothesis.metric.strip()
                        and hypothesis.falsifier.strip()
                        and hypothesis.comparator.strip()
                    ),
                    "requests": calls,
                    "fixture_fetches": fetches,
                    "critique_coverage": critiques,
                    "prior_art_detected": prior,
                    "targeted_searches": searches,
                    "recovered": recovered,
                    "cost_usd": "0",
                    "cache_only_replay": True if label != "B" else None,
                }
            )
        )


def test_v2_recovery_checkpoint_resume_and_no_duplicate_source(tmp_path):
    case = DATA["cases"]["POS-04"]
    lab, report, calls, _ = run_pipeline(
        tmp_path,
        case,
        "discovery-v2",
        distinct=False,
        interrupt="review-0",
    )
    assert calls.count("review-0") == 1
    assert not any("revision" in call for call in calls)
    trace = report.candidates[0].quality
    assert trace and [r.decision.action for r in trace.recovery] == ["retrieve", "inconclusive"]
    assert report.candidates[0].disposition == "rejected"
    assert verify_chain(lab.store)


def test_v2_replay_rejects_invalidated_source(tmp_path):
    from autodiscover.evidence.artifacts import IntegrityError

    lab, report, _, _ = run_pipeline(tmp_path, DATA["cases"]["POS-01"], "discovery-v2")
    source = report.searches[0].evidence[0]
    raw = b"New archived source version after invalidation."
    lab.catalog.add(
        report.run_id,
        Fetched(source.url, source.url, raw, "text/plain", CAPTURE_DATE),
        title="Updated title",
        text=raw.decode(),
        source_kind="primary_document",
    )
    with SnapshotStore(tmp_path) as store, pytest.raises(IntegrityError, match="invalid"):
        replay(store, report.run_id)


def test_v2_strict_provider_wire_and_preflight(tmp_path):
    from dataclasses import replace

    import httpx
    from pydantic import SecretStr

    from autodiscover.models.contracts import ProviderConfig
    from autodiscover.models.providers import MetaProvider
    from autodiscover.research.discovery_cli import preflight

    calls: list[str] = []
    case = DATA["cases"]["POS-04"]
    manifest = Path(__file__).parents[2] / "config" / "discovery-meta.json"
    configs = {
        role: ProviderConfig.model_validate({**value, "live_authorized": True})
        for role, value in json.loads(manifest.read_text()).items()
    }

    def strict(schema):
        if isinstance(schema, list):
            for item in schema:
                strict(item)
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                assert schema["additionalProperties"] is False
                assert set(schema["required"]) == set(schema["properties"])
            for value in schema.values():
                strict(value)

    def respond(request):
        body = json.loads(request.content)
        assert body["max_completion_tokens"] == 2560
        schema = body["response_format"]["json_schema"]
        assert schema["strict"]
        strict(schema["schema"])
        prompt = json.loads(body["messages"][-1]["content"])
        assert prompt["prompt_version"] == "research-quality-v1"
        model = body["model"]
        generated = FrozenResponse(model, calls, case).generate(
            GenerationRequest(prompt=canonical(prompt)),
        )
        return httpx.Response(
            200,
            json={
                "model": model,
                "choices": [{"finish_reason": "stop", "message": {"content": generated.text}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 80,
                    "completion_tokens_details": {"reasoning_tokens": 15},
                },
            },
        )

    class WireCorpus(Corpus):
        def fetch(self, url):
            return replace(super().fetch(url), provenance="live_https")

    routes: dict[str, list[Provider]] = {
        role: [
            MetaProvider(
                config,
                api_key=SecretStr("mock-transport-only"),
                transport=httpx.MockTransport(respond),
            )
        ]
        for role, config in configs.items()
    }
    spec = DiscoverySpec.model_validate_json(
        manifest.with_name("discovery-quality-v1.json").read_text()
    )
    estimate = preflight(spec, configs)
    assert estimate["maximum_attempts"] == 20
    assert estimate["searches_max"] == 4
    corpus = WireCorpus(case)
    lab = Discovery(Router(Store(tmp_path), routes), corpus, allow_retrieval=True)
    digest, report = lab.execute(lab.register(spec))
    assert calls == [
        "plan",
        "extract-0",
        "hypothesis-0",
        "review-0",
        "extract-revision-0",
        "hypothesis-revision-0",
        "review-revision-0",
    ]
    assert report.usage["requests"] == 7
    assert report.usage["reasoning_tokens_reported"] == 105
    assert Decimal(str(report.usage["settled_usd"])) > 0  # simulated tariff ledger
    assert report.critique_coverage == 1
    before = len(calls), len(corpus.calls), verify_chain(lab.store)
    with SnapshotStore(tmp_path) as store:
        assert replay(store, report.run_id) == (digest, report)
        assert verify_chain(store) == before[2]
    assert before[:2] == (len(calls), len(corpus.calls))


def test_v2_two_distinct_eligible_candidates_receive_critique(tmp_path):
    case = {**DATA["cases"]["NEG-08"], "second_sources": ["baseline"]}
    _, report, calls, _ = run_pipeline(tmp_path, case, "discovery-v2")
    assert report.critique_coverage == 2
    assert "review-0" in calls and "review-1" in calls
    assert all(c.disposition == "external_review_required" for c in report.candidates)


def test_v2_title_gap_only_recovers_with_distinct_substantive_evidence(tmp_path):
    case = {
        **DATA["cases"]["NEG-01"],
        "extract_query": RECOVERY_QUERY,
        "recovery_sources": ["study"],
    }
    _, report, calls, _ = run_pipeline(tmp_path, case, "discovery-v2")
    candidate = report.candidates[0]
    assert candidate.quality and candidate.quality.revised
    assert candidate.quality.original.proposal is None
    assert candidate.quality.original.screen.codes == ["title_or_metadata_as_empirical_evidence"]
    assert candidate.quality.revised.extraction_screen
    assert (
        "title_or_metadata_as_empirical_evidence"
        in candidate.quality.revised.extraction_screen.codes
    )
    assert [entry.decision.action for entry in candidate.quality.recovery] == ["retrieve", "revise"]
    assert "hypothesis-0" not in calls and "review-0" not in calls
    assert candidate.original_review and candidate.revised is None
    assert candidate.disposition == "external_review_required"
