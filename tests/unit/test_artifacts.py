import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.evidence.chain import export_snapshot, verify_chain, verify_events
from autodiscover.orchestrator.store import Store


def test_content_addressed_concurrent_dedup_and_tamper(tmp_path):
    artifacts = Artifacts(tmp_path / "artifacts", max_bytes=100)
    with ThreadPoolExecutor(max_workers=8) as pool:
        addresses = list(pool.map(lambda i: artifacts.put(b"content"), range(20)))
    assert len(set(addresses)) == 1
    digest = addresses[0]
    assert artifacts.get(digest) == b"content"
    artifacts.path(digest).write_bytes(b"modified")
    with pytest.raises(IntegrityError):
        artifacts.get(digest)
    with pytest.raises(IntegrityError):
        artifacts.put(b"content")
    with pytest.raises(IntegrityError):
        artifacts.put(b"x" * 101)
    with pytest.raises(IntegrityError):
        artifacts.get("../../host-file")


def test_chain_detects_edit_delete_and_independent_anchor(tmp_path):
    store = Store(tmp_path / "runtime")
    store.create_run("chain", {})
    anchor = export_snapshot(store, tmp_path / "retained" / "snapshot.json")
    assert verify_chain(store, anchor)["verified_events"] == 1
    with pytest.raises(FileExistsError):
        export_snapshot(store, tmp_path / "retained" / "snapshot.json")
    snapshot = json.loads((tmp_path / "retained" / "snapshot.json").read_text())
    assert verify_events(snapshot["events"], anchor)["hash"] == anchor["hash"]
    with store.connection(write=True) as db:
        db.execute("UPDATE events SET payload_json='{}'")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        verify_chain(store, anchor)
    with store.connection(write=True) as db:
        db.execute("DELETE FROM events")
    with pytest.raises(IntegrityError, match="truncated"):
        verify_chain(store, anchor)


def test_artifact_symlink_refused(tmp_path):
    artifacts = Artifacts(tmp_path / "artifacts")
    digest = artifacts.put(b"data")
    path = artifacts.path(digest)
    path.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"private")
    path.symlink_to(outside)
    with pytest.raises(IntegrityError, match="symlink"):
        artifacts.get(digest)
