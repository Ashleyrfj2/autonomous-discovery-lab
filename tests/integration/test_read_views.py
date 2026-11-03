import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.store import SnapshotStore, StateError, Store
from autodiscover.reporting.reports import build_report
from autodiscover.reporting.views import PageRequest, ReadConflict, ReadService
from autodiscover.research.catalog import Catalog
from autodiscover.research.retrieval import Fetched


def durable_state(root: Path):
    with Store(root).connection() as db:
        database = list(db.iterdump())
    files = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ("artifacts", "reports", "checkpoints", "logs")
        for p in (root / folder).rglob("*")
        if p.is_file()
    }
    return database, files


def test_all_read_views_preserve_state_reports_artifacts_and_cli_parity(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo()
    expected = json.loads((tmp_path / "reports" / f"{run}.json").read_text())
    before = durable_state(tmp_path)
    reads = ReadService(tmp_path)
    assert reads.report(run) == expected == lab.report(run, persist=False)
    summary = reads.runs().items[0]
    assert summary.run_id == run and summary.technical_success is True
    assert summary.novelty == "unknown" and summary.market_level == 0
    assert not summary.market_validated and summary.allowed_controls == []
    assert reads.detail(run).summary == summary
    assert len(reads.jobs(run).items) == 3
    assert len(reads.stages(run).items) == 12
    assert reads.evidence(run).items == []
    assert reads.usage(run).charged_usd == 0
    assert reads.tree(run).tree.nodes
    assert reads.queue().items == []
    assert durable_state(tmp_path) == before
    (tmp_path / "reports" / f"{run}.json").unlink()
    lab.report(run, persist=False)
    assert not (tmp_path / "reports" / f"{run}.json").exists()
    lab.report(run)
    assert json.loads((tmp_path / "reports" / f"{run}.json").read_text()) == expected


def test_snapshot_consistent_while_writer_advances_and_cursors_reject_mixed_pages(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo(stop_after=2)
    reads = ReadService(tmp_path)
    first = reads.runs(PageRequest(limit=1))
    with SnapshotStore(tmp_path) as snapshot:
        initial = build_report(snapshot, run)
        lab.store.control(run, "pause")
        assert build_report(snapshot, run) == initial
        assert snapshot.get_run(run)["status"] == "ACTIVE"
        assert verify_chain(snapshot)["seq"] == first.cursor.seq
    assert reads.detail(run).summary.status == "PAUSED"
    assert reads.detail(run).cursor.seq > first.cursor.seq
    with pytest.raises(ReadConflict):
        reads.runs(PageRequest(limit=1, at_cursor=first.cursor.seq))


def test_snapshot_and_artifacts_fail_closed_on_writes_and_missing_root(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(sqlite3.OperationalError):
        ReadService(missing).runs()
    assert not missing.exists()
    root = tmp_path / "existing"
    store = Store(root)
    run = store.create_run("empty initialized root", {})
    assert not (root / "artifacts").exists()
    with SnapshotStore(root) as snapshot:
        with pytest.raises(StateError, match="read only"):
            snapshot.control(run, "pause")
        with snapshot.connection() as db, pytest.raises(sqlite3.OperationalError):
            db.execute("DELETE FROM runs")
        with pytest.raises(StateError):
            snapshot.checkpoint(run)
        with pytest.raises(IntegrityError):
            Artifacts(root / "artifacts", read_only=True).put(b"forbidden")
    ReadService(root).detail(run)
    assert not (root / "artifacts").exists()


def test_bounded_pagination_empty_unknown_and_schema_validation(tmp_path):
    store = Store(tmp_path)
    reads = ReadService(tmp_path)
    assert reads.runs().items == []
    ids = [store.create_run(f"queued {i}", {}) for i in range(3)]
    first = reads.runs(PageRequest(limit=2))
    assert [r.run_id for r in first.items] == ids[:2] and first.next_offset == 2
    last = reads.runs(PageRequest(limit=2, offset=2, at_cursor=first.cursor.seq))
    assert [r.run_id for r in last.items] == ids[2:] and last.next_offset is None
    with pytest.raises(StateError):
        reads.detail("unknown")
    for arguments in ({"limit": 101}, {"offset": -1}, {"limit": True}, {"at_cursor": -1}):
        with pytest.raises(ValidationError):
            PageRequest.model_validate(arguments)


def test_source_claim_ownership_invalidation_and_index_backfill_are_read_only(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("source owner", {})
    other = store.create_run("another run", {})
    catalog = Catalog(store)
    quote = "A source statement retained for attribution only."
    source = catalog.add(
        run,
        Fetched(
            "https://example.com/a",
            "https://example.com/a",
            quote.encode(),
            "text/plain",
            "2026-11-03T00:00:00Z",
        ),
        title="Local fixture",
        text=quote,
        source_kind="primary_document",
    )
    claim = catalog.claim(run, quote, supports=[source], quotes={source: quote})
    with store.connection(write=True) as db:
        db.execute("DELETE FROM source_locations")
    reads = ReadService(tmp_path)
    before = durable_state(tmp_path)
    nodes = reads.evidence(run).items
    assert {n.id for n in nodes} == {source, claim}
    assert reads.evidence(other).items == []
    assert durable_state(tmp_path) == before
    catalog.invalidate(run, source, reason="Source withdrawn")
    assert all(not node.valid for node in reads.evidence(run).items)


def test_projection_tampering_blocks_reads_without_repairing_or_persisting_reports(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo(stop_after=2)
    with lab.store.connection(write=True) as db:
        db.execute("UPDATE runs SET status='COMPLETED' WHERE id=?", (run,))
    before = durable_state(tmp_path)
    with pytest.raises(IntegrityError):
        ReadService(tmp_path).detail(run)
    assert durable_state(tmp_path) == before


def test_current_market_review_updates_reads_without_rewriting_recorded_history(tmp_path):
    from autodiscover.commercial.contracts import HumanReview, MarketEvidence
    from autodiscover.commercial.service import Market

    lab = Lab(tmp_path / "runtime")
    run = lab.demo()
    market = Market(lab.store)
    opportunity = lab.report(run)["commercial"]["opportunity_id"]
    document = tmp_path / "operator-fixture.txt"
    quote = "A local contract fixture states a real workflow problem."
    document.write_text(quote)
    source = market.add_document(run, document, title="Test fixture, not real market evidence")
    record, _ = market.catalog.source(source)
    evidence = market.add_evidence(
        opportunity,
        MarketEvidence(
            origin="external",
            kind="problem_report",
            source_id=source,
            quote=quote,
        ),
    )
    review = HumanReview(
        accepted=True,
        facts=["real_problem"],
        rationale="Local contract fixture only",
        source_digest=record.raw_digest,
    )
    market.review(evidence, review, actor_kind="human")
    reads = ReadService(lab.store.root)
    current = reads.detail(run)
    assert current.summary.market_level == 1 and current.commercial is not None
    assert current.commercial["recorded_level"] == 0
    assessment = current.assessment
    market.review(evidence, review.model_copy(update={"accepted": False}), actor_kind="human")
    before = durable_state(lab.store.root)
    withdrawn = reads.detail(run)
    assert withdrawn.summary.market_level == 0
    assert withdrawn.assessment == assessment and withdrawn.summary.novelty == "unknown"
    assert durable_state(lab.store.root) == before
