"""Matched scripted comparison; reasoning quality is deliberately held constant."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from test_capability_discovery import Mutation, specification

from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store
from autodiscover.research.capability_rehearsal import (
    PRIOR,
    SOURCE,
    TARGET,
    CapabilityArchive,
    rehearsal,
)
from autodiscover.research.discovery import ROLES
from autodiscover.research.retrieval import Fetched

CASES = [
    "positive",
    "title",
    "advantage",
    "ordinary",
    "prior_art",
    "no_need",
    "no_bridge",
    "critic_no_ai",
    "critic_no_bridge",
    "irrelevant",
]


class MatchedCorpus(CapabilityArchive):
    def fetch(self, url):
        query = parse_qs(urlsplit(url).query).get("query.bibliographic", [""])[0]
        if query.startswith("sensor conflicts case"):
            items = [
                {
                    "DOI": f"10.0000/synthetic-{k}",
                    "title": [f"Synthetic {k} fixture"],
                    "abstract": text,
                }
                for k, text in [("source", SOURCE), ("target", TARGET), ("prior", PRIOR)]
            ]
            return Fetched(
                url,
                url,
                canonical({"message": {"items": items}}).encode(),
                "application/json",
                "2026-11-04T00:00:00Z",
                "fixture",
            )
        return super().fetch(url)


class BaselineProjection(Mutation):
    def answer(self, prompt):
        task = prompt["task"]
        if task.startswith("hypothesis"):
            gap = super().answer({**prompt, "task": "gap-projection"})
            prompt = {**prompt, "gap_analysis": gap}
        result = super().answer(prompt)
        if task == "plan":
            result["directions"] = [
                {
                    k: v
                    for k, v in d.items()
                    if k
                    in {
                        "question",
                        "first_domain",
                        "second_domain",
                        "query",
                        "expected_support",
                        "expected_falsifier",
                        "value",
                        "uncertainty",
                        "search_effort",
                    }
                }
                for d in result["directions"]
            ]
        if task.startswith("hypothesis"):
            result["proposal"].pop("opportunity")
        if task.startswith("review"):
            for key in [
                "ai_necessity",
                "bridge_plausibility",
                "need_support",
                "capability_rationale",
            ]:
                result.pop(key)
            # Preserve independent prior-art findings across schema projections.
            if self.scenario == "prior_art":
                result.update(
                    prior_art_status="equivalent",
                    prior_art_evidence=[prompt["findings"][0]["citation"]],
                )
            if self.scenario == "critic_no_bridge":
                result["objections"][0].update(
                    material=True, issue="No defensible shared mechanism.", query=""
                )
        return result


@pytest.mark.parametrize("scenario", CASES)
def test_matched_capability_abc(tmp_path, scenario):
    records = []
    for condition in ["A", "B", "C"]:
        store = Store(tmp_path / condition)
        lab = rehearsal(store, 0)
        lab.fetcher = MatchedCorpus()
        calls = []
        for role in ROLES:
            provider = (BaselineProjection if condition == "A" else Mutation)(role, 0)
            provider.scenario, provider.seen = scenario, calls
            lab.router.routes[role] = [provider]
        spec = specification()
        assert spec.capability
        spec = spec.model_copy(
            update={"capability": spec.capability.model_copy(update={"tracks": ["ai_native"]})}
        )
        if condition == "A":
            spec = spec.model_copy(
                update={"capability": None, "seconds": 240, "max_output_tokens": 2560}
            )
        elif condition == "B":
            assert spec.capability
            spec = spec.model_copy(
                update={
                    "capability": spec.capability.model_copy(
                        update={
                            "stages": {
                                k: v.model_copy(update={"reasoning_effort": "low"})
                                for k, v in spec.capability.stages.items()
                            }
                        }
                    )
                }
            )
        _, packet = lab.execute(lab.register(spec))
        kept = sum(c.disposition == "external_review_required" for c in packet.candidates)
        if scenario == "positive":
            assert kept == 1  # An all-rejecting implementation fails.
        if scenario in {"title", "advantage", "no_bridge", "irrelevant"}:
            assert kept == 0
        if condition != "A" and scenario != "positive":
            assert kept == 0  # An all-accepting implementation fails.
        assert packet.novelty_status == "unverified" and packet.commercial_level == 0
        records.append(
            {
                "condition": condition,
                "case": scenario,
                "retained": kept,
                "reviewed": packet.critique_coverage,
                "calls": len(calls),
                "searches": len(packet.searches),
                "usage": packet.usage,
                "semantic_review": "authored_fixture_not_independent",
            }
        )
    assert records[1]["retained"] == records[2]["retained"]
    print(json.dumps(records, sort_keys=True))
