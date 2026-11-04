"""Prepare blinded review cases from pinned SciFact and saved Discovery packets."""

import argparse
import hashlib
import json
import random
import tarfile
from pathlib import Path
from uuid import uuid4

from autodiscover.orchestrator.durability import atomic_json
from autodiscover.orchestrator.store import SnapshotStore
from autodiscover.research.discovery import replay
from autodiscover.research.discovery_contracts import Report
from autodiscover.security.redaction import contains_credential

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "tests/fixtures/discovery/scifact-dev-holdout.json"
HISTORICAL = "discovery-9d86dedf2a48c9f787c13e5284e81b1a8e38e495ccfdbdd9e435723a8f144c4e"
RUBRIC = {
    "citation_relevance": "direct / context_only / irrelevant / cannot_assess",
    "passage_entailment": "supports / contradicts / insufficient",
    "negation_or_conflict": "respected / overlooked / not_applicable / cannot_assess",
    "causality": "supported / overstated / not_applicable / cannot_assess",
    "transfer": "plausible_unverified / unsupported / not_applicable / cannot_assess",
    "prior_art_overlap": "equivalent / close / none_in_packet / cannot_assess",
    "measurement": "falsifiable / underspecified / not_applicable / cannot_assess",
    "disposition": "retain_for_investigation / reject / inconclusive",
    "explanation": "Name the relevant passage, scope or missing evidence and explain the rating.",
}


def scifact(archive_path: Path) -> list[tuple[dict, dict]]:
    manifest = json.loads(GOLD.read_text())
    with archive_path.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != manifest["sha256"]:
            raise ValueError("SciFact archive digest differs from frozen manifest")
    with tarfile.open(archive_path) as archive:
        claims = archive.extractfile("data/claims_dev.jsonl")
        docs = archive.extractfile("data/corpus.jsonl")
        if claims is None or docs is None:
            raise ValueError("Required SciFact files are missing")
        corpus = {document["doc_id"]: document for document in map(json.loads, docs)}
        rows = sorted(map(json.loads, claims), key=lambda row: row["id"])
    result = []
    for label in ("support", "contradict"):
        matching = [
            (
                row,
                [
                    (doc, entry)
                    for doc, entries in row["evidence"].items()
                    for entry in entries
                    if entry["label"] == label.upper()
                ],
            )
            for row in rows
        ]
        selected = [(row, matches) for row, matches in matching if matches][:6]
        if [row["id"] for row, _ in selected[:4]] != manifest[label]:
            raise ValueError("SciFact baseline IDs differ from frozen manifest")
        for index, (row, matches) in enumerate(selected):
            doc_id, _first = matches[0]
            document = corpus[int(doc_id)]
            result.append(
                (
                    {
                        "claims": [row["claim"]],
                        "sources": [
                            {
                                "title": document["title"],
                                "access": "abstract",
                                "sentences": document["abstract"],
                            }
                        ],
                    },
                    {
                        "origin": "SciFact development split",
                        "claim_id": row["id"],
                        "document_id": doc_id,
                        "external_gold": label,
                        "rationales": [
                            entry["sentences"] for doc, entry in matches if doc == doc_id
                        ],
                        "previously_selected": index < 4,
                    },
                )
            )
    return result


def candidates(packet: Report, condition: str) -> list[tuple[dict, dict]]:
    evidence = {s.source_id: s for search in packet.searches for s in search.evidence}
    items = []
    for candidate in packet.candidates:
        for phase, hypothesis, attempt in (
            (
                "original",
                candidate.original,
                candidate.quality.original if candidate.quality else None,
            ),
            (
                "revised",
                candidate.revised,
                candidate.quality.revised if candidate.quality else None,
            ),
        ):
            if hypothesis is None:
                continue
            citations = hypothesis.evidence + hypothesis.prior_art
            cited = {citation.source_id for citation in citations}
            sources = [
                {
                    "title": source.title,
                    "url": source.url,
                    "access": source.scope,
                    "passage": source.excerpt,
                    "quoted_spans": [
                        citation.quote
                        for citation in citations
                        if citation.source_id == source.source_id
                    ],
                }
                for source in evidence.values()
                if source.source_id in cited
            ]
            items.append(
                (
                    {
                        "question": packet.plan.directions[candidate.direction].question,
                        "claims": [c.text for c in attempt.proposal.claims]
                        if attempt and attempt.proposal
                        else [hypothesis.rationale],
                        "mechanism": hypothesis.mechanism,
                        "novelty_claim": hypothesis.novelty_claim,
                        "comparison": {
                            "metric": hypothesis.metric,
                            "comparator": hypothesis.comparator,
                            "minimum_effect": hypothesis.minimum_effect,
                            "falsifier": hypothesis.falsifier,
                        },
                        "sources": sources,
                        "unbound_quote_count": sum(c.source_id not in evidence for c in citations),
                    },
                    {
                        "origin": condition,
                        "run_id": packet.run_id,
                        "direction": candidate.direction,
                        "attempt": phase,
                        "system_disposition": candidate.disposition,
                    },
                )
            )
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scifact", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path)
    parser.add_argument("--packet", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = scifact(args.scifact)
    if args.historical_root:
        with SnapshotStore(args.historical_root) as store:
            _digest, packet = replay(store, HISTORICAL)
        rows.extend(candidates(packet, "historical live discovery-v1"))
    for path in args.packet:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("artifact_digest", None)
        rows.extend(candidates(Report.model_validate(data), path.name))
    random.SystemRandom().shuffle(rows)
    cases, key = [], {}
    for case, metadata in rows:
        identifier = uuid4().hex[:16]
        cases.append({"candidate_id": identifier, **case})
        key[identifier] = metadata
    if contains_credential(json.dumps(cases)):
        raise ValueError("Review material contains a recognizable credential pattern")
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    atomic_json(
        args.output / "review-packet.json",
        {
            "instructions": "Score independently. Use cannot_assess when evidence is insufficient.",
            "rubric": RUBRIC,
            "cases": cases,
        },
    )
    atomic_json(
        args.output / "record-scores.json",
        {
            "reviewer": "",
            "scores": [
                {"candidate_id": case["candidate_id"], **dict.fromkeys(RUBRIC)} for case in cases
            ],
        },
    )
    atomic_json(args.output / "private-key-map.json", key)
    print(json.dumps({"case_count": len(cases), "output": str(args.output)}))


if __name__ == "__main__":
    main()
