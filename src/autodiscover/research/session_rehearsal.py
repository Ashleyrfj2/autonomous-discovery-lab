"""Deterministic session rehearsal using a short public RFC 1951 passage."""

import json
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from autodiscover.models.contracts import Generation, GenerationRequest, Provider, Usage
from autodiscover.models.providers import MockProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store
from autodiscover.research.discovery import ROLES, Discovery
from autodiscover.research.retrieval import Fetched

RFC_PASSAGE = "The data format is a combination of the LZ77 algorithm and Huffman coding."


class Archive:
    def fetch(self, url: str) -> Fetched:
        parsed = urlsplit(url)
        if parsed.hostname == "api.crossref.org":
            query = parse_qs(parsed.query)["query.bibliographic"][0]
            items = (
                [
                    {
                        "DOI": "10.17487/RFC1951",
                        "title": ["DEFLATE Compressed Data Format Specification version 1.3"],
                        "abstract": RFC_PASSAGE,
                    }
                ]
                if "deflate" in query.casefold()
                else []
            )
            body = {"message": {"items": items}}
        else:
            body = {"resultList": {"result": []}}
        return Fetched(
            url,
            url,
            canonical(body).encode(),
            "application/json",
            "2026-11-04T00:00:00Z",
            "fixture",
        )


class RehearsalProvider(MockProvider):
    def __init__(self, name: str, branch: int):
        super().__init__()
        self.name = self.model = name
        self.branch = branch

    def generate(self, request: GenerationRequest) -> Generation:
        prompt = json.loads(request.prompt)
        return Generation(
            text=canonical(self.answer(prompt)),
            provider=self.name,
            model=self.model,
            usage=Usage(input_tokens=100, output_tokens=80, reasoning_tokens=15),
            cost_usd=Decimal(0),
        )

    def answer(self, prompt: dict) -> dict:
        task = prompt["task"]
        if task == "plan":
            return {
                "directions": [
                    {
                        "question": question,
                        "first_domain": "compression",
                        "second_domain": "telemetry",
                        "query": query,
                        "expected_support": "A documented coding baseline",
                        "expected_falsifier": "No measured benefit on a held-out comparison",
                        "value": 5 - index,
                        "uncertainty": 4,
                        "search_effort": 1,
                    }
                    for index, (question, query) in enumerate(
                        [
                            (
                                "Would dictionary selection reduce telemetry storage?",
                                f"deflate compression telemetry alternative {self.branch % 3}",
                            ),
                            ("What is a comparable monitoring workflow?", "monitoring baseline"),
                            (
                                "What evidence would disconfirm adoption?",
                                "adoption disconfirmation",
                            ),
                        ]
                    )
                ],
            }
        if task.startswith("extract"):
            source = prompt["sources"][0]
            return {
                "findings": [
                    {
                        "finding_id": "rfc-method",
                        "citation": {"source_id": source["source_id"], "quote": RFC_PASSAGE},
                        "location": "abstract",
                        "domain": "compression",
                        "method": "Combine dictionary matching with entropy coding.",
                        "observation": RFC_PASSAGE,
                        "limitations": "A format specification supplies no telemetry effect size.",
                    }
                ],
                "gap": "No measurements on held-out telemetry.",
                "query": "",
            }
        if task.startswith("review"):
            return {
                "objections": [
                    {
                        "category": "evidence",
                        "issue": "The proposed comparison remains untested.",
                        "material": False,
                        "evidence": [],
                        "query": "",
                        "expected_information": 3,
                        "effort": 2,
                    }
                ],
                "claim_assessments": [
                    {
                        "claim_index": 0,
                        "judgment": "supports",
                        "rationale": "The captured RFC passage names both components.",
                    }
                ],
                "prior_art_status": "close",
                "prior_art_evidence": [prompt["findings"][0]["citation"]],
                "falsification_test": "Compare held-out storage ratios at fixed CPU limits.",
            }
        citation = prompt["findings"][0]["citation"]
        return {
            "reason": "",
            "proposal": {
                "claims": [
                    {
                        "text": RFC_PASSAGE,
                        "kind": "empirical",
                        "finding_ids": ["rfc-method"],
                    }
                ],
                "bridge": {
                    "source_finding_ids": ["rfc-method"],
                    "source_domain": "compression",
                    "target_domain": "telemetry",
                    "shared_mechanism": "Repeated fields can produce more dictionary matches.",
                    "domain_mismatches": ["Traffic mix and latency differ from generic inputs."],
                    "target_outcome_metric": "Relative encoded bytes",
                    "comparator": "Fixed DEFLATE configuration",
                    "falsifier": "Gain below 5 percent",
                    "variables": ["Repetition rate", "Encoder time"],
                    "alternative_explanations": ["Framing overhead could dominate."],
                    "missing_target_evidence": "No paired telemetry data or timed benchmark.",
                    "existing_approaches": ["Fixed DEFLATE", "Fixed Zstandard"],
                    "measurable_prediction": "Reduce encoded bytes at a fixed CPU limit.",
                },
                "established_advantage_claimed": False,
                "independent_replication_claimed": False,
                "minimum_effect_unit": "relative fraction",
                "recovery_query": "",
                "hypothesis": {
                    "problem": "Reduce repetitive telemetry storage at fixed CPU cost.",
                    "evidence": [citation],
                    "prior_art": [citation],
                    "mechanism": "Select per-stream dictionary configurations for repeated fields.",
                    "rationale": "Longer repeated fields could improve backreference rates.",
                    "novelty_claim": "Unknown; compare established compression strategies.",
                    "alternatives": ["Fixed DEFLATE", "Fixed Zstandard"],
                    "counterargument": "Existing tuned encoders could already match the gain.",
                    "falsifier": "Reject when savings are below the predefined 5 percent.",
                    "validation": "Run paired blinded measurements on held-out telemetry.",
                    "metric": "Relative encoded bytes",
                    "comparator": "Fixed DEFLATE configuration",
                    "minimum_effect": 0.05,
                    "uncertainty": "No measured target evidence yet.",
                    "target_user": "Telemetry operators",
                    "economic_buyer": "Storage budget owner",
                    "workaround_and_cost": "Fixed encoding; economic impact unknown.",
                    "adoption_obstacles": "Throughput and decoder rollout.",
                    "commercial_test": "Seek independently documented operating costs.",
                },
            },
        }


def rehearsal(store: Store, branch: int) -> Discovery:
    routes: dict[str, list[Provider]] = {role: [RehearsalProvider(role, branch)] for role in ROLES}
    return Discovery(Router(store, routes), Archive(), allow_retrieval=True)
