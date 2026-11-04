"""Durable fair queue with bounded foreground workers and graceful cooperative shutdown."""

import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.experiments.runner import ExecutionError
from autodiscover.models.contracts import ProviderError
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import now
from autodiscover.orchestrator.jobs import Jobs
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.store import StateError, Store
from autodiscover.security.processes import coordinator_alive, local_owner


class Scheduler:
    def __init__(self, store: Store):
        self.store, self.owner = store, local_owner()

    def enqueue(self, run_id: str) -> None:
        if self.store.is_session(run_id):
            raise ValueError("Use session resume for research sessions")
        if self.store.is_discovery(run_id):
            raise ValueError("Use discover --run-id for discovery runs")
        verify_chain(self.store)
        with self.store.connection(write=True) as db:
            run = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
            if run is None or run[0] != "ACTIVE":
                raise StateError("Only active runs can enter the work queue")
            if db.execute("SELECT 1 FROM work_queue WHERE run_id=?", (run_id,)).fetchone():
                return
            db.execute(
                "INSERT INTO work_queue VALUES(?,'READY',NULL,0,NULL,?,0,0,NULL,?)",
                (run_id, self.store.clock(), now()),
            )
            self.store._event(
                db,
                run_id,
                "queue_enqueued",
                {
                    "status": "READY",
                    "fence": 0,
                    "attempts": 0,
                    "completed_steps": 0,
                    "last_error": None,
                },
            )

    def sync(self) -> None:
        verify_chain(self.store)
        with self.store.connection(write=True) as db:
            rows = db.execute(
                "SELECT q.*,r.status AS run_status FROM work_queue q JOIN runs r ON r.id=q.run_id"
            ).fetchall()
            for row in rows:
                target = None
                reason = None
                if row["run_status"] != "ACTIVE" and row["status"] != row["run_status"]:
                    target, reason = row["run_status"], "RUN_CONTROL_OR_COMPLETION"
                elif row["run_status"] == "ACTIVE" and row["status"] == "PAUSED":
                    target, reason = "READY", "RUN_RESUMED"
                elif row["status"] == "RUNNING" and (
                    row["lease_until"] <= self.store.clock()
                    or coordinator_alive(row["owner"]) is False
                ):
                    target, reason = "READY", "COORDINATOR_INTERRUPTED"
                if target is not None:
                    db.execute(
                        "UPDATE work_queue SET status=?,owner=NULL,fence=fence+1,lease_until=NULL,"
                        "available_at=?,last_error=?,updated_at=? WHERE run_id=?",
                        (target, self.store.clock(), reason, now(), row["run_id"]),
                    )
                    self.store._event(
                        db,
                        row["run_id"],
                        "queue_synchronized",
                        {
                            "status": target,
                            "owner": None,
                            "fence": row["fence"] + 1,
                            "attempts": row["attempts"],
                            "completed_steps": row["completed_steps"],
                            "last_error": reason,
                        },
                    )

    def claim(self) -> tuple[str, int] | None:
        self.sync()
        with self.store.connection(write=True) as db:
            rows = db.execute(
                "SELECT q.*,r.owner AS run_owner,r.lease_until AS run_lease "
                "FROM work_queue q JOIN runs r ON r.id=q.run_id "
                "WHERE q.status='READY' AND q.available_at<=? AND r.status='ACTIVE' "
                "ORDER BY q.updated_at,q.run_id",
                (self.store.clock(),),
            ).fetchall()
            row = next(
                (
                    r
                    for r in rows
                    if r["run_owner"] is None
                    or r["run_lease"] <= self.store.clock()
                    or coordinator_alive(r["run_owner"]) is False
                ),
                None,
            )
            if row is None:
                return None
            fence = row["fence"] + 1
            db.execute(
                "UPDATE work_queue SET status='RUNNING',owner=?,fence=?,lease_until=?,"
                "attempts=attempts+1,updated_at=? WHERE run_id=?",
                (self.owner, fence, self.store.clock() + 300, now(), row["run_id"]),
            )
            self.store._event(
                db,
                row["run_id"],
                "queue_claimed",
                {
                    "status": "RUNNING",
                    "owner": self.owner,
                    "fence": fence,
                    "attempts": row["attempts"] + 1,
                    "completed_steps": row["completed_steps"],
                    "last_error": row["last_error"],
                },
            )
            return row["run_id"], fence

    def _finish(self, run_id: str, fence: int, before_version: int, error_code: str | None) -> None:
        with self.store.connection(write=True) as db:
            row = db.execute("SELECT * FROM work_queue WHERE run_id=?", (run_id,)).fetchone()
            if row["owner"] != self.owner or row["fence"] != fence:
                return
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            status = "READY" if run["status"] == "ACTIVE" else run["status"]
            progress = max(0, run["version"] - before_version)
            completed = row["completed_steps"] + progress
            delay = min(0.25 * 2 ** run["failures"], 5) if error_code else (0 if progress else 0.1)
            db.execute(
                "UPDATE work_queue SET status=?,owner=NULL,lease_until=NULL,available_at=?,"
                "completed_steps=?,last_error=?,updated_at=? WHERE run_id=?",
                (status, self.store.clock() + delay, completed, error_code, now(), run_id),
            )
            self.store._event(
                db,
                run_id,
                "queue_step_finished",
                {
                    "status": status,
                    "owner": None,
                    "fence": fence,
                    "attempts": row["attempts"],
                    "completed_steps": completed,
                    "last_error": error_code,
                    "stage": run["stage"],
                    "version": run["version"],
                },
            )

    def _step(
        self,
        run_id: str,
        fence: int,
        stop: threading.Event,
        router_factory: Callable[[Store], Router] | None,
    ) -> None:
        lab = Lab(self.store.root)
        before = lab.store.get_run(run_id)["version"]
        error_code = None
        try:
            lab.resume(
                run_id,
                stop_after=1,
                stop_requested=stop.is_set,
                router=router_factory(lab.store) if router_factory else None,
            )
        except (ExecutionError, ProviderError) as error:
            code = error.code if isinstance(error, ProviderError) else str(error)
            error_code = (
                code
                if code.replace("_", "").isalnum() and code.isupper()
                else "STAGE_EXECUTION_FAILED"
            )
        except StateError:
            error_code = "RUN_LEASE_BUSY"
        except IntegrityError:
            error_code = "EVIDENCE_INTEGRITY_FAILURE"
            if lab.store.get_run(run_id)["status"] == "ACTIVE":
                lab.store.control(run_id, "pause")
        except Exception:
            # Never persist raw exception/source/provider bodies or repeat unknown failures forever.
            error_code = "UNEXPECTED_STAGE_FAILURE"
            if lab.store.get_run(run_id)["status"] == "ACTIVE":
                lab.store.control(run_id, "pause")
        finally:
            self._finish(run_id, fence, before, error_code)

    def run(
        self,
        *,
        max_steps: int = 100,
        max_seconds: float = 60,
        concurrency: int = 1,
        stop: threading.Event | None = None,
        router_factory: Callable[[Store], Router] | None = None,
    ) -> dict[str, Any]:
        if not 1 <= max_steps <= 10000 or not 0 < max_seconds <= 86400 or not 1 <= concurrency <= 8:
            raise ValueError("Bounded scheduling steps/time/concurrency required")
        stop = stop or threading.Event()
        deadline = time.monotonic() + max_seconds
        admitted = 0
        futures: set[Future] = set()
        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="adl-stage") as pool:
            while True:
                if time.monotonic() >= deadline:
                    stop.set()
                while not stop.is_set() and admitted < max_steps and len(futures) < concurrency:
                    claim = self.claim()
                    if claim is None:
                        break
                    run_id, fence = claim
                    futures.add(pool.submit(self._step, run_id, fence, stop, router_factory))
                    admitted += 1
                if futures:
                    done, futures = wait(futures, timeout=0.1, return_when=FIRST_COMPLETED)
                    for future in done:
                        future.result()
                else:
                    self.sync()
                    if stop.is_set() or admitted >= max_steps:
                        break
                    with self.store.connection() as db:
                        pending = db.execute(
                            "SELECT 1 FROM work_queue q JOIN runs r ON r.id=q.run_id "
                            "WHERE q.status='READY' AND r.status='ACTIVE' LIMIT 1"
                        ).fetchone()
                    if pending is None:
                        break
                    stop.wait(0.05)
            self.sync()
        return {
            "stage_attempts": admitted,
            "stopped": stop.is_set(),
            "step_limit_reached": admitted >= max_steps,
            "queue": self.status(),
            "jobs": Jobs(self.store).status(),
            "qualification": "Bounded foreground operation; no background service installed",
        }

    def status(self) -> list[dict[str, Any]]:
        with self.store.connection() as db:
            return [
                dict(r) for r in db.execute("SELECT * FROM work_queue ORDER BY updated_at,run_id")
            ]
