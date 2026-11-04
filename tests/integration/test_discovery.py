"""End-to-end offline controls using archived RFC excerpts and scripted model responses."""

import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.models.contracts import Generation, GenerationRequest, Provider, Usage
from autodiscover.models.providers import MockProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import SnapshotStore, StateError, Store
from autodiscover.research.discovery import ROLES, Discovery, replay
from autodiscover.research.discovery_cli import preflight
from autodiscover.research.discovery_contracts import Citation, DiscoverySpec, Report, SourceSeed
from autodiscover.research.retrieval import Fetched

FIXTURE = Path(__file__).parents[1] / "fixtures" / "discovery" / "rfc-controls.json"
OBJECTIVE = Path(__file__).parents[2] / "config" / "discovery-objective.json"
CAPTURE_DATE = "2026-11-03T00:00:00+00:00"


class Archive:
    def __init__(self, *, new_evidence: bool = True):
        self.records = json.loads(FIXTURE.read_text())
        self.calls: list[str] = []
        self.new_evidence = new_evidence

    def fetch(self, url: str) -> Fetched:
        self.calls.append(url)
        if urlsplit(url).hostname == "api.crossref.org":
            query = parse_qs(urlsplit(url).query)["query.bibliographic"][0]
            items = []
            if query == "zstandard existing comparable baseline" and self.new_evidence:
                # Synthetic index response points to a known-answer primary-source excerpt.
                data = self.records["rfc8878"]
                items.append(
                    {
                        "DOI": "10.17487/RFC8878",
                        "title": [data["title"]],
                        "abstract": data["excerpt"],
                        "publisher": data["publisher"],
                        "published": {"date-parts": [[2021, 2]]},
                    }
                )
            return Fetched(
                url,
                url,
                canonical({"message": {"items": items}}).encode(),
                "application/json",
                CAPTURE_DATE,
                "fixture",
            )
        if urlsplit(url).hostname == "www.ebi.ac.uk":
            body = canonical({"resultList": {"result": []}}).encode()
            return Fetched(url, url, body, "application/json", CAPTURE_DATE, "fixture")
        record = next(r for r in self.records.values() if r["url"] == url)
        return Fetched(url, url, record["excerpt"].encode(), "text/plain", CAPTURE_DATE, "fixture")


def _plan():
    directions = []
    for index, (question, query, other_domain) in enumerate(
        [
            ("Can archive coding improve telemetry storage?", "telemetry DEFLATE", "telemetry"),
            ("Does Base64 reduce network payload size?", "base64 transport size", "networking"),
            ("Can audio analysis improve plant surveys?", "audio plant surveys", "field ecology"),
        ]
    ):
        directions.append(
            {
                "question": question,
                "first_domain": "signal processing",
                "second_domain": other_domain,
                "query": query,
                "expected_support": "A primary source provides a comparator.",
                "expected_falsifier": "A published implementation already uses this mechanism.",
                "value": 5 - index,
                "uncertainty": 4,
                "search_effort": 1,
            }
        )
    return {"directions": directions}


def _quote(source):
    excerpt = source["excerpt"]
    return {"source_id": source["source_id"], "quote": excerpt[-86:]}


def _hypothesis(prompt, *, bad: bool = False, revised: bool = False):
    citation = _quote(prompt["sources"][0])
    if bad:
        citation["quote"] = "Base64 always compresses arbitrary binary data."
    return {
        "problem": "Archive telemetry payloads may waste storage.",
        "evidence": [citation],
        "mechanism": (
            "Compare negotiated binary framing"
            if prompt["task"] == "hypothesis-1"
            else "Use per-stream dictionary selection"
            if revised
            else "Apply a new LZ77 codec"
        ),
        "rationale": "Repeated keys may yield longer backreferences.",
        "novelty_claim": "Unverified: isolate the selection policy from existing codecs.",
        "alternatives": ["DEFLATE", "Zstandard"],
        "prior_art": [citation] if not bad else [],
        "counterargument": "A tuned Zstandard configuration may already match the improvement.",
        "falsifier": "Reject if paired savings versus tuned Zstandard are below 5 percent.",
        "validation": "Compare held-out telemetry with paired file sizes and CPU time.",
        "metric": "Relative reduction in bytes",
        "comparator": "Tuned Zstandard without selector",
        "minimum_effect": 0.05,
        "uncertainty": "CPU cost and robustness require an external test.",
        "target_user": "Telemetry infrastructure team",
        "economic_buyer": "Infrastructure budget owner",
        "workaround_and_cost": "Existing codecs are a workaround. Cost and frequency are unknown.",
        "adoption_obstacles": "Verify retention policies and decoder rollout.",
        "commercial_test": "Check storage spend and seek independently documented pilot interest.",
    }


class Scripted(MockProvider):
    def __init__(
        self,
        name: str,
        calls: list[str],
        *,
        reject_revision: bool = False,
        flawed_candidate: bool = True,
    ):
        super().__init__()
        self.name = name
        self.model = name
        self.calls = calls
        self.reject_revision = reject_revision
        self.flawed_candidate = flawed_candidate

    def generate(self, request: GenerationRequest) -> Generation:
        prompt = json.loads(request.prompt)
        task = prompt["task"]
        self.calls.append(task)
        if task == "plan":
            body = _plan()
        elif task.startswith(("review-", "revision-review-")):
            material = task == "review-0" or self.reject_revision
            body = {
                "objections": [
                    {
                        "category": "prior_art",
                        "issue": (
                            "DEFLATE already uses LZ77."
                            if task == "review-0"
                            else "The source offers a comparator. Benefit is untested."
                        ),
                        "material": material,
                        "evidence": [_quote(prompt["sources"][0])],
                        "query": "zstandard existing comparable baseline",
                        "expected_information": 5,
                        "effort": 1,
                    }
                ],
                "falsification_test": "Compare paired storage reduction against tuned Zstandard.",
            }
        else:
            body = _hypothesis(
                prompt,
                bad=task == "hypothesis-1" and self.flawed_candidate,
                revised=task == "revision-0",
            )
        return Generation(
            text=canonical(body),
            provider=self.name,
            model=self.model,
            usage=Usage(input_tokens=100, output_tokens=80, reasoning_tokens=0),
            cost_usd=Decimal(0),
        )


def setup(
    root: Path,
    *,
    mode: str = "reviewed",
    new_evidence: bool = True,
    reject_revision: bool = False,
    flawed_candidate: bool = True,
):
    calls: list[str] = []
    models = [
        Scripted(
            f"fixture-{i}",
            calls,
            reject_revision=reject_revision,
            flawed_candidate=flawed_candidate,
        )
        for i in range(3 if mode == "reviewed" else 1)
    ]
    routes: dict[str, list[Provider]] = {
        role: [models[i % len(models)]] for i, role in enumerate(ROLES)
    }
    archive = Archive(new_evidence=new_evidence)
    discovery = Discovery(Router(Store(root), routes), archive, allow_retrieval=True)
    default = DiscoverySpec.model_validate_json(OBJECTIVE.read_text())
    spec = DiscoverySpec.model_validate(
        {
            **default.model_dump(),
            "mode": mode,
            "sources": [
                SourceSeed(
                    **{k: v for k, v in archive.records[name].items() if k != "excerpt"},
                    category="technical",
                    direction=i,
                )
                for i, name in enumerate(("rfc1951", "rfc4648"))
            ],
        }
    )
    return discovery, spec, calls, archive


def evaluate_control(report: Report) -> dict:
    by_direction = {c.direction: c for c in report.candidates}
    source_ids = {s.source_id: s for r in report.searches for s in r.evidence}
    proposal_citations = [
        citation
        for candidate in report.candidates
        for hypothesis in (candidate.original, candidate.revised)
        if hypothesis
        for citation in hypothesis.evidence + hypothesis.prior_art
    ]
    supported = sum(
        c.source_id in source_ids and c.quote in source_ids[c.source_id].excerpt
        for c in proposal_citations
    )
    known_prior_art = by_direction[0].original_review
    return {
        "proposal_quotes_verified": supported,
        "proposal_quote_count": len(proposal_citations),
        "invalid_quotes_advanced": sum(
            1 for c in report.candidates if c.direction == 1 and c.disposition != "rejected"
        ),
        "correct_prior_art_objection": bool(
            known_prior_art
            and any(
                o.category == "prior_art"
                and o.material
                and any(
                    "rfc1951" in source_ids[e.source_id].url
                    and "LZ77 algorithm" in source_ids[e.source_id].excerpt
                    for e in o.evidence
                )
                for o in known_prior_art.objections
            )
        ),
        "flawed_candidate_rejected": by_direction[1].disposition == "rejected",
        "comparator_and_falsifier": all(
            c.original.comparator and c.original.falsifier and c.original.minimum_effect > 0
            for c in report.candidates
        ),
        "distinct_mechanisms": len(
            {(c.revised or c.original).mechanism for c in report.candidates}
        ),
        "commercial_level": report.commercial_level,
        "usage": report.usage,
        "external_review_required": ["semantic support", "novelty", "usefulness", "market demand"],
    }


@pytest.mark.parametrize("mode", ["reviewed", "single_model"])
def test_offline_control_and_cache_only_replay(tmp_path, mode):
    discovery, spec, calls, archive = setup(tmp_path, mode=mode)
    run_id = discovery.register(spec)
    digest, report = discovery.execute(run_id)
    count = len(calls), len(archive.calls)
    evidence = verify_chain(discovery.store)
    with SnapshotStore(tmp_path) as store:
        assert replay(store, run_id) == (digest, report)
        assert verify_chain(store) == evidence
    assert count == (6, 7)
    assert count == (len(calls), len(archive.calls))
    result = evaluate_control(report)
    assert result["proposal_quotes_verified"] == 4
    assert result["proposal_quote_count"] == 5
    assert result["flawed_candidate_rejected"]
    assert result["correct_prior_art_objection"]
    assert result["commercial_level"] == 0
    assert result["invalid_quotes_advanced"] == 0
    assert report.candidates[0].revised and report.candidates[0].revision_review
    assert report.candidates[0].disposition == "external_review_required"
    assert report.novelty_status == "unverified"
    assert report.technical_status == "not_executed"


def test_recovery_after_dispatch_reuses_cached_plan(tmp_path):
    discovery, spec, calls, archive = setup(tmp_path)
    run_id = discovery.register(spec)
    with pytest.raises(StateError, match="interrupted"):
        discovery.execute(run_id, stop_requested=lambda: bool(calls))
    assert calls == ["plan"]
    assert not archive.calls
    recovered, _, retry_calls, _ = setup(tmp_path)
    _, report = recovered.execute(run_id)
    assert "plan" not in retry_calls
    assert report.usage["requests"] == 6


def test_no_new_evidence_closes_all_candidates(tmp_path):
    discovery, spec, calls, _ = setup(tmp_path, new_evidence=False)
    run_id = discovery.register(spec)
    _, report = discovery.execute(run_id)
    assert all(c.disposition == "rejected" for c in report.candidates)
    assert not any(call.startswith("revision") for call in calls)


def test_replay_rejects_invalidated_evidence(tmp_path):
    discovery, spec, _, _ = setup(tmp_path)
    run_id = discovery.register(spec)
    _, report = discovery.execute(run_id)
    source = report.searches[0].evidence[0]
    fetched = Fetched(
        source.url,
        source.url,
        b"New evidence snapshot with contradictory text.",
        "text/plain",
        CAPTURE_DATE,
    )
    discovery.catalog.add(
        run_id,
        fetched,
        title="New revision",
        text=fetched.body.decode(),
        source_kind="primary_document",
    )
    with SnapshotStore(tmp_path) as store, pytest.raises(IntegrityError, match="invalid"):
        replay(store, run_id)


def test_review_role_identity_and_live_preflight(tmp_path):
    from autodiscover.models.contracts import ProviderConfig

    discovery, spec, _, _ = setup(tmp_path, mode="single_model")
    with pytest.raises(ValueError, match="route identities"):
        discovery.register(spec.model_copy(update={"mode": "reviewed"}))
    manifest = OBJECTIVE.with_name("discovery-meta.json")
    configs = {
        k: ProviderConfig.model_validate(v) for k, v in json.loads(manifest.read_text()).items()
    }
    estimate = preflight(DiscoverySpec.model_validate_json(OBJECTIVE.read_text()), configs)
    assert estimate["maximum_attempts"] == 14
    assert estimate["conservative_gross_usd_estimate"] == "1.052544"


def test_remaining_material_flaw_rejects_revision(tmp_path):
    discovery, spec, calls, _ = setup(tmp_path, reject_revision=True)
    _, report = discovery.execute(discovery.register(spec))
    assert report.candidates[0].revised is not None
    assert report.candidates[0].scientific_gate.review_has_material_objection
    assert all(c.disposition == "rejected" for c in report.candidates)
    assert calls.count("revision-0") == 1


def test_claimed_run_cannot_dispatch_and_legacy_resume_is_blocked(tmp_path):
    from autodiscover.orchestrator.lab import Lab
    from autodiscover.orchestrator.scheduler import Scheduler
    from autodiscover.security.processes import local_owner

    discovery, spec, calls, archive = setup(tmp_path)
    run_id = discovery.register(spec)
    with pytest.raises(ValueError, match="discovery runs"):
        Lab(tmp_path).resume(run_id)
    with pytest.raises(ValueError, match="discovery"):
        Scheduler(discovery.store).enqueue(run_id)
    owner = local_owner()
    fence = discovery.store.claim(run_id, owner)
    try:
        other, _, other_calls, _ = setup(tmp_path)
        with pytest.raises(StateError, match="not available"):
            other.execute(run_id)
        assert not other_calls and not calls and not archive.calls
    finally:
        discovery.store.release(run_id, owner, fence)


def test_commercial_gate_requires_attestation_and_non_fixture_primary_source(tmp_path):
    from autodiscover.research.discovery_validation import (
        CommercialObservation,
        CommercialReview,
        record_commercial_review,
    )

    discovery, spec, _, _ = setup(tmp_path)
    run_id = discovery.register(spec)
    _, report = discovery.execute(run_id)
    cited = report.candidates[0].original.evidence[0]
    synthetic = CommercialObservation(
        citation=cited,
        kind="problem",
        interpretation="Scripted observations cannot count.",
    )
    with pytest.raises(ValueError, match="attestation"):
        record_commercial_review(
            discovery.store,
            run_id,
            0,
            CommercialReview(observations=[synthetic]),
            operator_attested=False,
        )
    with pytest.raises(ValueError, match="primary document"):
        record_commercial_review(
            discovery.store,
            run_id,
            0,
            CommercialReview(observations=[synthetic]),
            operator_attested=True,
        )
    quote = "A documented and externally attested observation for this case."
    url = "operator://test-evidence"
    captured = Fetched(url, url, quote.encode(), "text/plain", CAPTURE_DATE, "operator_document")
    source = discovery.catalog.add(
        run_id,
        captured,
        title="Test operator evidence",
        text=quote,
        source_kind="primary_document",
    )
    buyer = report.candidates[0].original.economic_buyer
    kinds = ("problem", "spending", "direct_buyer_or_pilot", "paid_commitment")
    levels = [
        CommercialObservation(
            citation=Citation(source_id=source, quote=quote),
            kind=kind,
            buyer_role=buyer if index >= 2 else None,
            amount=Decimal(100) if index == 3 else None,
            currency="USD" if index == 3 else None,
            interpretation="Fixture simulates a human reviewer reading the original record.",
        )
        for index, kind in enumerate(kinds)
    ]
    for index in range(4):
        observation = CommercialReview(observations=levels[: index + 1])
        record = record_commercial_review(
            discovery.store,
            run_id,
            0,
            observation,
            operator_attested=True,
        )
        assert record["commercial_level"] == index + 1
    observation = CommercialReview(observations=levels)
    record = record_commercial_review(
        discovery.store,
        run_id,
        0,
        observation,
        operator_attested=True,
    )
    before = verify_chain(discovery.store)
    assert (
        record_commercial_review(
            discovery.store,
            run_id,
            0,
            observation,
            operator_attested=True,
        )
        == record
    )
    assert verify_chain(discovery.store) == before
    assert replay(discovery.store, run_id)[1].commercial_level == 0


def test_live_wire_simulation_exercises_every_nested_schema(tmp_path):
    from dataclasses import replace

    import httpx
    from pydantic import SecretStr

    from autodiscover.models.contracts import ProviderConfig
    from autodiscover.models.providers import MetaProvider

    def strict_shape(schema):
        if isinstance(schema, list):
            for item in schema:
                strict_shape(item)
        elif isinstance(schema, dict):
            if schema.get("type") == "object":
                assert schema["additionalProperties"] is False
                assert set(schema["required"]) == set(schema["properties"])
            for value in schema.values():
                strict_shape(value)

    calls = []

    def respond(request):
        assert str(request.url) == "https://api.meta.ai/v1/chat/completions"
        body = json.loads(request.content)
        assert body["max_completion_tokens"] == 1536
        assert body["reasoning_effort"] in {"minimal", "low"}
        schema = body["response_format"]["json_schema"]
        assert schema["strict"]
        strict_shape(schema["schema"])
        config = body["model"]
        scripted = Scripted(config, calls)
        generated = scripted.generate(GenerationRequest(prompt=body["messages"][-1]["content"]))
        return httpx.Response(
            200,
            json={
                "model": config,
                "choices": [{"finish_reason": "stop", "message": {"content": generated.text}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 80,
                    "completion_tokens_details": {"reasoning_tokens": 15},
                },
            },
        )

    class SimulatedPublicArchive(Archive):
        def fetch(self, url):
            return replace(super().fetch(url), provenance="live_https")

    manifest = OBJECTIVE.with_name("discovery-meta.json")
    routes: dict[str, list[Provider]] = {
        role: [
            MetaProvider(
                ProviderConfig.model_validate({**value, "live_authorized": True}),
                api_key=SecretStr("mock-transport-only"),
                transport=httpx.MockTransport(respond),
            )
        ]
        for role, value in json.loads(manifest.read_text()).items()
    }
    _, spec, _, _ = setup(tmp_path / "fixture")
    public = SimulatedPublicArchive()
    discovery = Discovery(Router(Store(tmp_path / "wire"), routes), public, allow_retrieval=True)
    _, report = discovery.execute(discovery.register(spec))
    assert len(calls) == 6
    assert report.usage["reasoning_tokens_reported"] == 90
    assert report.usage["attempts_reporting_reasoning"] == 6
    assert report.usage["settled_usd"] == "0.00586"


def test_stable_registration_reuses_the_same_run(tmp_path):
    discovery, spec, calls, _ = setup(tmp_path)
    run_id = discovery.register(spec, stable=True)
    digest, report = discovery.execute(run_id)
    other, _, other_calls, other_archive = setup(tmp_path)
    assert other.register(spec, stable=True) == run_id
    assert other.execute(run_id) == (digest, report)
    assert len(calls) == 6
    assert not other_calls and not other_archive.calls
    assert len(other.store.list_runs()) == 1


def test_abrupt_process_exit_after_plan_dispatch(tmp_path):
    import subprocess
    import sys

    discovery, spec, _, _ = setup(tmp_path)
    run_id = discovery.register(spec)
    body = """
import os, runpy, sys
from pathlib import Path
controls = runpy.run_path(sys.argv[1])
lab, _, calls, _ = controls["setup"](Path(sys.argv[2]))
lab.execute(sys.argv[3], stop_requested=lambda: os._exit(73) if calls else False)
"""
    child = subprocess.run(  # noqa: S603
        [sys.executable, "-c", body, str(Path(__file__).resolve()), str(tmp_path), run_id],
        timeout=15,
        check=False,
    )
    assert child.returncode == 73
    assert discovery.store.get_run(run_id)["owner"] is not None
    resumed, _, calls, _ = setup(tmp_path)
    _, report = resumed.execute(run_id)
    assert "plan" not in calls
    assert report.usage["requests"] == 6


def test_two_distinct_candidates_receive_independent_reviews(tmp_path):
    discovery, spec, calls, _ = setup(tmp_path, flawed_candidate=False)
    _, report = discovery.execute(discovery.register(spec))
    assert len(calls) == 7
    assert all(
        c.original_review and c.scientific_gate.evidence_binding == "passed"
        for c in report.candidates
    )
    assert len({(c.revised or c.original).mechanism for c in report.candidates}) == 2


def test_abstract_fallback_replaces_title_only_evidence_without_invalidating_it(tmp_path):
    from autodiscover.research.discovery_sources import acquire

    class MetadataArchive:
        def fetch(self, url):
            if urlsplit(url).hostname == "api.crossref.org":
                data = {
                    "message": {
                        "items": [
                            {
                                "DOI": "10.17487/RFC8878",
                                "title": ["Zstandard compression specification"],
                            }
                        ]
                    },
                }
            else:
                data = {
                    "resultList": {
                        "result": [
                            {
                                "doi": "10.17487/RFC8878",
                                "title": "Zstandard compression specification",
                                "abstractText": "This fixture supplies abstract text.",
                            }
                        ]
                    },
                }
            return Fetched(url, url, canonical(data).encode(), "application/json", CAPTURE_DATE)

    discovery, spec, _, _ = setup(tmp_path)
    run_id = discovery.register(spec)
    for _ in range(2):
        receipt = acquire(
            discovery.catalog,
            run_id,
            MetadataArchive(),
            "Question about coding",
            "zstandard compression",
            [],
            require_live=False,
        )
        assert len(receipt.evidence) == 1
        assert receipt.evidence[0].scope == "abstract"
    assert len(discovery.catalog.sources(run_id)) == 2
    verify_chain(discovery.store)


def test_stale_source_writer_cannot_attach_evidence(tmp_path):
    from autodiscover.security.processes import local_owner

    discovery, spec, _, _ = setup(tmp_path)
    run_id = discovery.register(spec)
    owner = local_owner()
    fence = discovery.store.claim(run_id, owner)
    discovery.store.release(run_id, owner, fence)
    url = "https://www.rfc-editor.org/rfc/rfc1951.txt"
    captured = Fetched(url, url, b"Archived but stale source.", "text/plain", CAPTURE_DATE)
    with pytest.raises(StateError, match="Stale"):
        discovery.catalog.add(
            run_id,
            captured,
            title="Stale source",
            text=captured.body.decode(),
            source_kind="primary_document",
            lease=(owner, fence),
        )
    assert discovery.catalog.sources(run_id) == []


def test_cache_only_replay_rejects_usage_mismatch(tmp_path):
    discovery, spec, _, _ = setup(tmp_path)
    run_id = discovery.register(spec)
    discovery.execute(run_id)
    with discovery.store.connection(write=True) as db:
        db.execute("UPDATE reservations SET charged_nano=1 WHERE run_id=?", (run_id,))
    with SnapshotStore(tmp_path) as store, pytest.raises(IntegrityError, match="request ledger"):
        replay(store, run_id)
