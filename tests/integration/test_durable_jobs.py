import subprocess
import sys
import time
from typing import Any

import psutil
import pytest

from autodiscover.config import Limits
from autodiscover.evidence.chain import verify_chain
from autodiscover.experiments import runner
from autodiscover.experiments.allocation_contracts import AllocationPlan
from autodiscover.experiments.contracts import Plan
from autodiscover.hypotheses.allocation import allocation_demo_proposal
from autodiscover.orchestrator.jobs import Jobs, ResourceBusy
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.store import Store


def owned(store, topic="job", limits=None):
    run = store.create_run(topic, (limits or Limits()).model_dump(mode="json"))
    fence = store.claim(run, topic)
    return run, fence


def test_completed_subjob_is_cached_without_a_second_worker(tmp_path, monkeypatch):
    store = Store(tmp_path)
    run, fence = owned(store)
    jobs = Jobs(store)
    plan = Plan(hypothesis_id="job-cache")
    arguments: dict[str, Any] = dict(
        owner="job", run_fence=fence, stage_version=0, plan=plan, limits=Limits()
    )
    first = jobs.execute(run, **arguments)

    def forbid(*args, **kwargs):
        raise AssertionError("Completed work must not execute twice")

    monkeypatch.setattr(runner, "run", forbid)
    assert Jobs(Store(tmp_path)).execute(run, **arguments) == first
    assert len(jobs.status(run)) == 1
    assert jobs.status(run)[0]["attempts"] == 1
    assert verify_chain(store)["verified_events"] >= 4


def test_global_admission_respects_lowest_active_policy(tmp_path):
    store = Store(tmp_path)
    a, fa = owned(store, "one", Limits(max_concurrent_experiments=1))
    b, fb = owned(store, "two", Limits(max_concurrent_experiments=2))
    jobs = Jobs(store)
    jobs.acquire(
        a, owner="one", run_fence=fa, stage_version=0, plan=Plan(hypothesis_id="a"), replication=0
    )
    with pytest.raises(ResourceBusy, match="CONCURRENCY"):
        jobs.acquire(
            b,
            owner="two",
            run_fence=fb,
            stage_version=0,
            plan=Plan(hypothesis_id="b"),
            replication=0,
        )
    assert len([r for r in jobs.status() if r["status"] == "RUNNING"]) == 1


@pytest.mark.parametrize("action", ["pause", "cancel"])
@pytest.mark.parametrize("plan_type", [Plan, AllocationPlan])
def test_controls_terminate_active_worker_without_recording_false_failure(
    tmp_path, monkeypatch, action, plan_type
):
    store = Store(tmp_path)
    run, fence = owned(store)
    jobs = Jobs(store)
    real_runner = runner.run
    seen = []

    def controlled(plan, limits, **kwargs):
        started = kwargs["on_started"]

        def after_started(pid, created):
            started(pid, created)
            seen.append(pid)
            store.control(run, action)

        kwargs["on_started"] = after_started
        return real_runner(plan, limits, **kwargs)

    monkeypatch.setattr(runner, "run", controlled)
    with pytest.raises(runner.WorkInterrupted):
        jobs.execute(
            run,
            owner="job",
            run_fence=fence,
            stage_version=0,
            plan=plan_type(hypothesis_id="control"),
            limits=Limits(),
        )
    assert seen and not psutil.pid_exists(seen[0])
    assert jobs.status(run)[0]["status"] == "ABANDONED"
    assert jobs.status(run)[0]["error_count"] == 0
    assert store.get_run(run)["status"] == ("PAUSED" if action == "pause" else "CANCELLED")
    assert verify_chain(store)["verified_events"] > 3


def test_interrupted_replication_reuses_committed_first_replica(tmp_path, monkeypatch):
    lab = Lab(tmp_path)
    run = lab.demo(stop_after=8)
    script = """
import os,sys
from pathlib import Path
from autodiscover.orchestrator.lab import Lab
lab=Lab(Path(sys.argv[1]))
original=lab.jobs.execute
def crash(run_id,**kwargs):
 if kwargs.get('replication')==2: os._exit(75)
 return original(run_id,**kwargs)
lab.jobs.execute=crash
lab.resume(sys.argv[2])
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path), run], check=False)  # noqa: S603
    assert result.returncode == 75
    assert [r["replication"] for r in lab.jobs.status(run) if r["status"] == "COMPLETED"] == [0, 1]
    recovered = Lab(tmp_path)
    real_runner = runner.run
    replicas = []

    def tracked(plan, limits, **kwargs):
        replicas.append(kwargs.get("replication", 0))
        return real_runner(plan, limits, **kwargs)

    monkeypatch.setattr(runner, "run", tracked)
    recovered.resume(run)
    assert replicas == [2]
    assert recovered.report(run)["status"] == "COMPLETED"
    assert [r["attempts"] for r in recovered.jobs.status(run)] == [1, 1, 1]


@pytest.mark.parametrize("family", ["encoding-v1", "allocation-v1"])
def test_worker_start_crash_is_reconciled_and_retried_explicitly(tmp_path, family):
    lab = Lab(tmp_path)
    if family == "allocation-v1":
        policy = Limits(explore_existing_candidates=True)
        run = lab.store.create_run("allocation recovery", policy.model_dump(mode="json"))
        lab.director.configure(run)
        lab.director.register(run, allocation_demo_proposal())
        lab.resume(run, stop_after=6)
    else:
        run = lab.demo(stop_after=6)
    script = """
import os,sys
from pathlib import Path
from autodiscover.orchestrator.lab import Lab
from autodiscover.experiments import runner
lab=Lab(Path(sys.argv[1]))
original=runner.run
def crash(plan,limits,**kwargs):
 started=kwargs['on_started']
 def terminate(pid,created):
  started(pid,created)
  os._exit(76)
 kwargs['on_started']=terminate
 return original(plan,limits,**kwargs)
runner.run=crash
lab.resume(sys.argv[2])
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path), run], check=False)  # noqa: S603
    assert result.returncode == 76
    unknown = lab.jobs.status(run)[0]
    assert unknown["status"] == "RUNNING" and unknown["worker_pid"]
    recovered = Lab(tmp_path)
    recovered.resume(run)
    assert recovered.report(run)["status"] == "COMPLETED"
    assert recovered.report(run)["assessment"]["technical_success"] is True
    assert recovered.plan(run).implementation == family
    assert verify_chain(recovered.store)["verified_events"] > 12
    first = recovered.jobs.status(run)[0]
    assert first["attempts"] == 2 and first["error_count"] == 1
    assert first["status"] == "COMPLETED"
    with recovered.store.connection() as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM events WHERE run_id=? AND kind='job_reconciled'", (run,)
            ).fetchone()[0]
            == 1
        )
    try:
        original = psutil.Process(unknown["worker_pid"])
        assert (
            original.create_time() != unknown["worker_created_at"]
            or original.status() == psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        pass


def test_caller_cannot_expand_durable_run_limits(tmp_path):
    store = Store(tmp_path)
    run, fence = owned(store, limits=Limits(max_experiment_seconds=1))
    with pytest.raises(ValueError, match="durable run policy"):
        Jobs(store).execute(
            run,
            owner="job",
            run_fence=fence,
            stage_version=0,
            plan=Plan(hypothesis_id="wrong-authority"),
            limits=Limits(),
        )
    assert Jobs(store).status(run) == []


def test_two_authorized_workers_run_concurrently_and_release_both_slots(tmp_path, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    store = Store(tmp_path)
    policy = Limits(max_concurrent_experiments=2)
    a, fa = owned(store, "alpha", policy)
    b, fb = owned(store, "beta", policy)
    jobs = Jobs(store)
    barrier = threading.Barrier(2)
    real_runner = runner.run
    observed = []

    def synchronized(plan, limits, **kwargs):
        start = kwargs["on_started"]

        def track(pid, created):
            start(pid, created)
            barrier.wait(timeout=5)
            observed.append(len([j for j in jobs.status() if j["status"] == "RUNNING"]))
            barrier.wait(timeout=5)

        kwargs["on_started"] = track
        return real_runner(plan, limits, **kwargs)

    monkeypatch.setattr(runner, "run", synchronized)

    def execute(item):
        run, fence, owner = item
        return jobs.execute(
            run,
            owner=owner,
            run_fence=fence,
            stage_version=0,
            plan=Plan(hypothesis_id=owner),
            limits=policy,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outputs = list(pool.map(execute, [(a, fa, "alpha"), (b, fb, "beta")]))
    assert observed == [2, 2]
    assert len(outputs) == 2
    assert all(j["status"] == "COMPLETED" for j in jobs.status())
    assert verify_chain(store)["verified_events"] > 4


def test_expired_job_never_kills_a_reused_process_identity(tmp_path):
    store = Store(tmp_path)
    run, fence = owned(store)
    jobs = Jobs(store)
    job, job_fence, _ = jobs.acquire(
        run,
        owner="job",
        run_fence=fence,
        stage_version=0,
        plan=Plan(hypothesis_id="pid-reuse"),
        replication=0,
    )
    process = subprocess.Popen(["/bin/sleep", "20"])  # noqa: S603 - owned disposable test process
    try:
        wrong_creation = psutil.Process(process.pid).create_time() - 1000
        with store.connection(write=True) as db:
            db.execute(
                "UPDATE experiment_jobs SET worker_pid=?,worker_created_at=? WHERE id=?",
                (process.pid, wrong_creation, job),
            )
            store._event(
                db,
                run,
                "job_worker_started",
                {
                    "job_id": job,
                    "fence": job_fence,
                    "worker_pid": process.pid,
                    "worker_created_at": wrong_creation,
                },
            )
        store.clock = lambda: time.time() + 301
        assert jobs.reconcile() == 1
        assert process.poll() is None
        assert jobs.status(run)[0]["status"] == "ABANDONED"
    finally:
        process.kill()
        process.wait()


def test_reconciliation_rechecks_renewed_lease_before_killing_worker(tmp_path, monkeypatch):
    from autodiscover.evidence import chain

    store = Store(tmp_path)
    run, fence = owned(store)
    jobs = Jobs(store)
    job, job_fence, _ = jobs.acquire(
        run,
        owner="job",
        run_fence=fence,
        stage_version=0,
        plan=Plan(hypothesis_id="renewal-race"),
        replication=0,
    )
    process = subprocess.Popen(["/bin/sleep", "20"])  # noqa: S603 - owned disposable test process
    try:
        with store.connection(write=True) as db:
            created = psutil.Process(process.pid).create_time()
            db.execute(
                "UPDATE experiment_jobs SET worker_pid=?,worker_created_at=? WHERE id=?",
                (process.pid, created, job),
            )
            store._event(
                db,
                run,
                "job_worker_started",
                {
                    "job_id": job,
                    "fence": job_fence,
                    "worker_pid": process.pid,
                    "worker_created_at": created,
                },
            )
        store.clock = lambda: time.time() + 181
        verify = chain.verify_chain

        def audit_then_renew(*args, **kwargs):
            result = verify(*args, **kwargs)
            with store.connection(write=True) as db:
                db.execute(
                    "UPDATE experiment_jobs SET lease_until=? WHERE id=?",
                    (store.clock() + 180, job),
                )
            return result

        monkeypatch.setattr(chain, "verify_chain", audit_then_renew)
        assert jobs.reconcile() == 0
        assert process.poll() is None
        assert jobs.status(run)[0]["status"] == "RUNNING"
    finally:
        process.kill()
        process.wait()


def test_replaced_run_owner_fences_old_job_and_preserves_recovery(tmp_path, monkeypatch):
    store = Store(tmp_path)
    run, fence = owned(store)
    jobs = Jobs(store)
    real_runner = runner.run
    replacement = []

    def displaced(plan, limits, **kwargs):
        started = kwargs["on_started"]

        def replace_owner(pid, created):
            started(pid, created)
            store.control(run, "pause")
            store.control(run, "resume")
            replacement.append(store.claim(run, "replacement"))

        kwargs["on_started"] = replace_owner
        return real_runner(plan, limits, **kwargs)

    monkeypatch.setattr(runner, "run", displaced)
    plan = Plan(hypothesis_id="stale-owner")
    with pytest.raises(runner.WorkInterrupted):
        jobs.execute(run, owner="job", run_fence=fence, stage_version=0, plan=plan, limits=Limits())
    assert jobs.status(run)[0]["artifact_digest"] is None
    assert store.get_run(run)["version"] == 0
    monkeypatch.setattr(runner, "run", real_runner)
    jobs.execute(
        run,
        owner="replacement",
        run_fence=replacement[0],
        stage_version=0,
        plan=plan,
        limits=Limits(),
    )
    row = jobs.status(run)[0]
    assert row["status"] == "COMPLETED" and row["attempts"] == 2
    with store.connection() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM events WHERE kind='job_completed'").fetchone()[0] == 1
        )
    assert verify_chain(store)["verified_events"] > 5
