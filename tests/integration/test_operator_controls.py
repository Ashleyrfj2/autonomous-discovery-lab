from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.experiments import runner
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.store import Store
from autodiscover.reporting.web import create_app

ORIGIN = "http://127.0.0.1:8765"


def operator(tmp_path, stop_after=7):
    lab = Lab(tmp_path)
    run = lab.demo(stop_after=stop_after)
    phrase = SecretStr(str(uuid4()))
    client = TestClient(create_app(tmp_path, phrase), base_url=ORIGIN, client=("127.0.0.1", 54321))
    assert (
        client.post(
            "/api/session", json={"password": phrase.get_secret_value()}, headers={"Origin": ORIGIN}
        ).status_code
        == 200
    )
    headers = {"Origin": ORIGIN, "X-CSRF-Token": client.get("/api/session").json()["csrf_token"]}
    return lab, run, client, headers


def command(lab, run, action):
    row = lab.store.get_run(run)
    return {
        "request_id": str(uuid4()),
        "action": action,
        "expected_version": row["version"],
        "expected_fence": row["fence"],
        "confirm_run_id": run if action == "cancel" else None,
    }


def test_controls_are_versioned_idempotent_and_never_launch_work(tmp_path):
    lab, run, client, headers = operator(tmp_path)
    path = f"/api/runs/{run}/control"
    original = lab.store.outputs(run)
    pause = command(lab, run, "pause")
    first = client.post(path, json=pause, headers=headers)
    assert first.status_code == 200 and not first.json()["replayed"]
    assert lab.store.get_run(run)["status"] == "PAUSED"
    assert client.post(path, json=pause, headers=headers).json()["replayed"]
    reused = {**pause, "action": "cancel", "confirm_run_id": run}
    assert client.post(path, json=reused, headers=headers).status_code == 409
    stale = {**pause, "request_id": str(uuid4())}
    assert client.post(path, json=stale, headers=headers).status_code == 409
    assert client.post(path, json=command(lab, run, "resume"), headers=headers).status_code == 200
    assert lab.store.get_run(run)["status"] == "ACTIVE"
    assert lab.store.outputs(run) == original  # Resume makes work eligible; never runs a stage.
    assert client.post(path, json=pause, headers=headers).json()["replayed"]
    assert lab.store.get_run(run)["status"] == "ACTIVE"  # A lost old response cannot re-pause it.
    cancel = command(lab, run, "cancel")
    assert (
        client.post(path, json={**cancel, "confirm_run_id": "wrong"}, headers=headers).status_code
        == 422
    )
    assert client.post(path, json=cancel, headers=headers).status_code == 200
    assert lab.store.get_run(run)["status"] == "CANCELLED"
    assert client.post(path, json=command(lab, run, "resume"), headers=headers).status_code == 409
    assert verify_chain(lab.store)["verified_events"] > 7


def test_control_endpoint_rejects_csrf_role_and_policy_overrides_before_mutation(tmp_path):
    lab, run, client, headers = operator(tmp_path)
    path = f"/api/runs/{run}/control"
    body = command(lab, run, "pause")
    before = lab.store.get_run(run)
    assert client.post(path, json=body, headers={"Origin": ORIGIN}).status_code == 403
    for change in (
        {"actor_kind": "human"},
        {"allow_live_inference": True},
        {"expected_fence": True},
        {"action": "execute"},
    ):
        assert client.post(path, json={**body, **change}, headers=headers).status_code == 422
    assert lab.store.get_run(run) == before


def test_concurrent_identical_commands_commit_one_event_and_recover_lost_response(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo(stop_after=2)
    body = command(lab, run, "pause")
    args = {k: v for k, v in body.items() if k != "confirm_run_id"}
    action = args.pop("action")

    def apply(_index):
        return Store(tmp_path, initialize=False).control(run, action, **args)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(apply, range(2)))
    assert all(r is not None for r in results)
    assert sorted(r["replayed"] for r in results if r is not None) == [False, True]
    with lab.store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='control'").fetchone()[0] == 1
    assert verify_chain(lab.store)["verified_events"] > 2


def test_guarded_control_audits_before_mutation_and_rejects_partial_preconditions(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo(stop_after=2)
    with pytest.raises(ValueError):
        lab.store.control(run, "pause", expected_version=2)
    body = command(lab, run, "pause")
    with lab.store.connection(write=True) as db:
        db.execute("UPDATE runs SET topic='forged' WHERE id=?", (run,))
    with pytest.raises(IntegrityError):
        lab.store.control(
            run,
            "pause",
            expected_version=body["expected_version"],
            expected_fence=body["expected_fence"],
            request_id=body["request_id"],
        )
    assert lab.store.get_run(run)["status"] == "ACTIVE"


def test_lost_checkpoint_after_commit_does_not_duplicate_operator_command(tmp_path, monkeypatch):
    lab = Lab(tmp_path)
    run = lab.demo(stop_after=2)
    body = command(lab, run, "pause")
    args = {k: v for k, v in body.items() if k not in ("confirm_run_id", "action")}

    def interrupted(_run):
        raise RuntimeError("test interruption after accepted command")

    monkeypatch.setattr(lab.store, "checkpoint", interrupted)
    with pytest.raises(RuntimeError):
        lab.store.control(run, "pause", **args)
    receipt = Store(tmp_path, initialize=False).control(run, "pause", **args)
    assert receipt is not None and receipt["replayed"]
    with lab.store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='control'").fetchone()[0] == 1


def test_authenticated_pause_interrupts_native_worker_then_resume_preserves_stage(
    tmp_path, monkeypatch
):
    lab, run, client, headers = operator(tmp_path, stop_after=6)
    real_runner = runner.run

    def pause_at_worker_start(plan, limits, **kwargs):
        started = kwargs["on_started"]

        def pause(pid, created):
            started(pid, created)
            result = client.post(
                f"/api/runs/{run}/control", json=command(lab, run, "pause"), headers=headers
            )
            assert result.status_code == 200, result.text

        kwargs["on_started"] = pause
        return real_runner(plan, limits, **kwargs)

    monkeypatch.setattr(runner, "run", pause_at_worker_start)
    lab.resume(run)
    assert lab.store.get_run(run)["status"] == "PAUSED"
    assert lab.store.get_run(run)["version"] == 6
    assert lab.jobs.status(run)[0]["status"] == "ABANDONED"
    assert lab.jobs.status(run)[0]["error_count"] == 0
    assert (
        client.post(
            f"/api/runs/{run}/control", json=command(lab, run, "resume"), headers=headers
        ).status_code
        == 200
    )
    monkeypatch.setattr(runner, "run", real_runner)
    lab.resume(run)
    assert lab.report(run)["status"] == "COMPLETED"
    assert len(lab.jobs.status(run)) == 3
    assert lab.jobs.status(run)[0]["attempts"] == 2
