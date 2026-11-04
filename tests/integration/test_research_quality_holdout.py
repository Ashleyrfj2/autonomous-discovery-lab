"""Check independently labeled SciFact holdout spans without leaking gold into prompts."""

import hashlib
import json
import os
import tarfile
from pathlib import Path

import pytest

from autodiscover.research.discovery_contracts import AtomicFinding, Citation, Evidence
from autodiscover.research.quality import screen_evidence

ARCHIVE = os.environ.get("ADL_SCIFACT_ARCHIVE")
MANIFEST = json.loads(
    (Path(__file__).parents[1] / "fixtures/discovery/scifact-dev-holdout.json").read_text()
)


@pytest.mark.parametrize("label", ["support", "contradict"])
def test_external_labels_stay_separate_from_source_binding(label):
    if not ARCHIVE:
        pytest.skip("ADL_SCIFACT_ARCHIVE is required for the externally annotated holdout")
    with Path(ARCHIVE).open("rb") as source_file:
        assert hashlib.file_digest(source_file, "sha256").hexdigest() == MANIFEST["sha256"]
    with tarfile.open(ARCHIVE) as archive:
        claim_rows = archive.extractfile("data/claims_dev.jsonl")
        document_rows = archive.extractfile("data/corpus.jsonl")
        assert claim_rows and document_rows
        claims = list(map(json.loads, claim_rows))
        documents = {row["doc_id"]: row for row in map(json.loads, document_rows)}
    matched = [
        claim
        for claim in claims
        if any(
            item["label"] == label.upper() for items in claim["evidence"].values() for item in items
        )
    ]
    selected = sorted(matched, key=lambda claim: claim["id"])[:4]
    assert [claim["id"] for claim in selected] == MANIFEST[label]
    for claim in selected:
        document_id, sentence_index = next(
            (int(document_id), item["sentences"][0])
            for document_id, annotations in claim["evidence"].items()
            for item in annotations
            if item["label"] == label.upper()
        )
        doc = documents[document_id]
        passage = doc["abstract"][sentence_index]
        source_id = "source-" + hashlib.sha256(str(document_id).encode()).hexdigest()
        source = Evidence(
            source_id=source_id,
            title=doc["title"],
            url="https://github.com/allenai/scifact",
            publisher=None,
            published_on=None,
            retrieved_at="frozen SciFact release",
            excerpt=passage,
            category="publication",
            provenance="fixture",
            scope="abstract",
            limitation="An externally annotated sentence from the abstract.",
        )
        finding = AtomicFinding(
            finding_id=f"scifact-{claim['id']}",
            citation=Citation(source_id=source_id, quote=passage[:360]),
            location="abstract",
            domain="biomedical literature",
            method="Capture a gold rationale sentence",
            observation=claim["claim"],
            limitations="Semantic judgment withheld from this check.",
        )
        result = screen_evidence([finding], [source])
        assert result.eligible_for_critique
        assert result.semantic_entailment == "independent_review_required"
