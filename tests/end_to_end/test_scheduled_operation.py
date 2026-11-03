import subprocess
import sys
import threading
from decimal import Decimal

from autodiscover.config import Limits
from autodiscover.evidence.chain import verify_chain
from autodiscover.models.providers import MockProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.scheduler import Scheduler
from autodiscover.security.budget import Budget


def test_durable_fair_queue_completes_multiple_runs_with_bounded_workers(tmp_path):
    lab = Lab(tmp_path)
    queue = Scheduler(lab.store)
    runs = [lab.store.create_run(f"scheduled research {i}", {}) for i in range(3)]
    for run in runs:
        queue.enqueue(run)
    first = queue.run(max_steps=6, max_seconds=10, concurrency=2)
    assert first["stage_attempts"] == 6 and first["step_limit_reached"]
    assert all(lab.store.get_run(run)["version"] > 0 for run in runs)
    assert all(lab.store.get_run(run)["status"] == "ACTIVE" for run in runs)
    restarted = Scheduler(Lab(tmp_path).store)
    result = restarted.run(max_steps=60, max_seconds=15, concurrency=2)
    assert all(r["status"] == "COMPLETED" for r in result["queue"])
    assert all(lab.report(run)["completed_steps"] == 12 for run in runs)
    assert len(result["jobs"]) == 9
    assert all(j["status"] == "COMPLETED" and j["attempts"] == 1 for j in result["jobs"])
    assert all(lab.report(run)["usage"]["charged_usd"] == "0" for run in runs)
    assert verify_chain(lab.store)["verified_events"] > 50


def test_coordinator_killed_after_queue_claim_is_recovered_without_waiting_for_expiry(tmp_path):
    lab = Lab(tmp_path)
    run = lab.store.create_run("queue recovery", {})
    Scheduler(lab.store).enqueue(run)
    script = """
import os,sys
from pathlib import Path
from autodiscover.orchestrator.store import Store
from autodiscover.orchestrator.scheduler import Scheduler
queue=Scheduler(Store(Path(sys.argv[1])))
assert queue.claim() is not None
os._exit(77)
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], check=False)  # noqa: S603
    assert result.returncode == 77
    assert Scheduler(lab.store).status()[0]["status"] == "RUNNING"
    result = Scheduler(lab.store).run(max_steps=20, max_seconds=10)
    assert result["queue"][0]["status"] == "COMPLETED"
    assert lab.report(run)["completed_steps"] == 12


def test_pause_resume_cancel_and_graceful_stop_preserve_queued_work(tmp_path):
    lab = Lab(tmp_path)
    run = lab.store.create_run("controls", {})
    queue = Scheduler(lab.store)
    queue.enqueue(run)
    queue.run(max_steps=2, max_seconds=5)
    before = lab.store.get_run(run)["version"]
    lab.store.control(run, "pause")
    assert queue.run(max_steps=10, max_seconds=1)["queue"][0]["status"] == "PAUSED"
    assert lab.store.get_run(run)["version"] == before
    lab.store.control(run, "resume")
    stopped = threading.Event()
    stopped.set()
    assert queue.run(max_steps=10, max_seconds=1, stop=stopped)["stage_attempts"] == 0
    assert lab.store.get_run(run)["version"] == before
    lab.store.control(run, "cancel")
    assert queue.run(max_steps=10, max_seconds=1)["queue"][0]["status"] == "CANCELLED"
    assert not lab.jobs.status(run)
    assert verify_chain(lab.store)["verified_events"] > 2


def test_exhausted_budget_stops_before_provider_call_and_preserves_state(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo(limits=Limits(max_cost_per_run_usd=Decimal("0.1")), stop_after=2)
    budget = Budget(lab.store)
    reserved = budget.reserve(run, "accounting-test", "fixture", Decimal("0.1"), "mock", "test")
    budget.settle(reserved, Decimal("0.1"))  # Simulated ledger usage; no actual provider billing.

    class PricedMock(MockProvider):
        def estimate_cost(self, request):
            return Decimal("0.001")

        def generate(self, request):
            raise AssertionError("Exhaustion must reject before a provider call")

    def routing(store):
        return Router(store, {"HYPOTHESIZE": [PricedMock()]})

    queue = Scheduler(lab.store)
    queue.enqueue(run)
    result = queue.run(max_steps=5, max_seconds=5, router_factory=routing)
    assert result["queue"][0]["status"] == "PAUSED"
    assert lab.store.get_run(run)["stage"] == "HYPOTHESIZE"
    assert lab.director.tree(run)["stopped_reason"] == "RUN_BUDGET_EXHAUSTED"
    assert len(lab.store.outputs(run)) == 2


def test_queue_and_worker_cli_resumes_bounded_foreground_work(tmp_path):
    import json

    prefix = [sys.executable, "-m", "autodiscover.cli", "--root", str(tmp_path)]
    enqueued = subprocess.run(  # noqa: S603 - fixed module and temporary fixture arguments
        prefix + ["enqueue", "--topic", "scheduled CLI"], capture_output=True, text=True, check=True
    )  # noqa: S603
    run = json.loads(enqueued.stdout)["run_id"]
    first = subprocess.run(  # noqa: S603 - fixed module and temporary fixture arguments
        prefix + ["workers", "--max-steps", "4", "--max-seconds", "10"],
        capture_output=True,
        text=True,
        check=True,
    )  # noqa: S603
    assert json.loads(first.stdout)["stage_attempts"] == 4
    second = subprocess.run(  # noqa: S603 - fixed module and temporary fixture arguments
        prefix + ["workers", "--max-steps", "20", "--max-seconds", "10"],
        capture_output=True,
        text=True,
        check=True,
    )  # noqa: S603
    assert json.loads(second.stdout)["queue"][0]["status"] == "COMPLETED"
    jobs = subprocess.run(prefix + ["jobs", run], capture_output=True, text=True, check=True)  # noqa: S603
    assert len(json.loads(jobs.stdout)) == 3
    assert Lab(tmp_path).report(run)["completed_steps"] == 12


def test_sigterm_drains_worker_preserves_queue_and_can_resume(tmp_path):
    import json
    import signal
    import time

    import psutil

    lab = Lab(tmp_path / "runtime")
    run = lab.demo(stop_after=6)
    Scheduler(lab.store).enqueue(run)
    ready = tmp_path / "worker-ready.json"
    script = """
import json,sys,time
from pathlib import Path
from autodiscover.experiments import runner
from autodiscover.cli import main
marker=Path(sys.argv[1]);root=sys.argv[2]
original=runner.run
def delayed(plan,limits,**kwargs):
 started=kwargs['on_started']
 def ready(pid,created):
  started(pid,created)
  marker.write_text(json.dumps({'pid':pid,'created':created}))
  time.sleep(.3)
 kwargs['on_started']=ready
 return original(plan,limits,**kwargs)
runner.run=delayed
sys.argv=['autodiscover','--root',root,'workers','--max-steps','20','--max-seconds','10']
main()
"""
    process = subprocess.Popen(  # noqa: S603 - fixed trusted lifecycle test script
        [sys.executable, "-c", script, str(ready), str(lab.store.root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), "Worker did not reach the verified active-worker checkpoint"
        worker = json.loads(ready.read_text())
        process.send_signal(signal.SIGTERM)
        output, error = process.communicate(timeout=5)
        assert process.returncode == 0, error
        report = json.loads(output)
        assert report["stopped"]
        assert report["queue"][0]["status"] == "READY"
        assert report["jobs"][0]["status"] == "ABANDONED"
        assert not psutil.pid_exists(worker["pid"])
        resumed = Scheduler(lab.store).run(max_steps=20, max_seconds=10)
        assert resumed["queue"][0]["status"] == "COMPLETED"
        assert lab.jobs.status(run)[0]["attempts"] == 2
        assert lab.jobs.status(run)[0]["error_count"] == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_stage_cancellation_callbacks_bind_versions_across_iterations_and_resume(
    tmp_path, monkeypatch
):
    from contextlib import contextmanager

    from autodiscover.orchestrator import lab as lab_module
    from autodiscover.security.cancellation import cancellation_scope

    lab = Lab(tmp_path)
    run = lab.store.create_run("stage callback identities", {})
    callbacks = []

    @contextmanager
    def capture(check):
        callbacks.append(check)
        assert not check(), "The current stage must retain its authority"
        assert all(previous() for previous in callbacks[:-1]), "Older stages must be interrupted"
        with cancellation_scope(check):
            yield

    monkeypatch.setattr(lab_module, "cancellation_scope", capture)
    lab.resume(run, stop_after=2)
    assert len(callbacks) == 2 and all(check() for check in callbacks)
    lab.store.control(run, "pause")
    assert all(check() for check in callbacks)
    lab.store.control(run, "resume")
    lab.resume(run, stop_after=2)
    assert len(callbacks) == 4 and all(check() for check in callbacks)
    lab.store.control(run, "cancel")
    assert all(check() for check in callbacks)
    assert lab.store.get_run(run)["version"] == 4
    assert verify_chain(lab.store)["verified_events"] > 4


def test_scheduler_deadline_interrupts_active_worker_and_releases_admission(tmp_path, monkeypatch):
    import time

    from autodiscover.experiments import runner

    lab = Lab(tmp_path)
    run = lab.demo(stop_after=6)
    queue = Scheduler(lab.store)
    queue.enqueue(run)
    real = runner.run

    def hold_until_deadline(plan, limits, **kwargs):
        started = kwargs["on_started"]

        def hold(pid, created):
            started(pid, created)
            time.sleep(0.15)

        kwargs["on_started"] = hold
        return real(plan, limits, **kwargs)

    monkeypatch.setattr(runner, "run", hold_until_deadline)
    result = queue.run(max_steps=10, max_seconds=0.1)
    assert result["stopped"]
    assert result["queue"][0]["status"] == "READY"
    assert result["jobs"][0]["status"] == "ABANDONED"
    assert result["jobs"][0]["error_count"] == 0
    assert lab.store.get_run(run)["version"] == 6
    assert verify_chain(lab.store)["verified_events"] > 6
