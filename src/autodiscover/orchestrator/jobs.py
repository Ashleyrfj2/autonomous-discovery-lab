"""Durable sub-jobs, fencing, global admission and interrupted-worker reconciliation."""

import hashlib
import time
from collections.abc import Callable
from typing import Any

import psutil

from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.experiments import runner
from autodiscover.experiments.contracts import Plan
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import StateError, Store
from autodiscover.security.processes import coordinator_alive


class ResourceBusy(RuntimeError):
    pass


class Jobs:
    def __init__(self, store: Store):
        self.store, self.artifacts = (
            store,
            Artifacts(store.root / "artifacts", read_only=store.read_only),
        )

    def reconcile(self) -> int:
        from autodiscover.evidence.chain import verify_chain

        with self.store.connection() as db:
            expired = [
                dict(r)
                for r in db.execute("SELECT * FROM experiment_jobs WHERE status='RUNNING'")
                if r["lease_until"] <= self.store.clock() or coordinator_alive(r["owner"]) is False
            ]
        if not expired:
            return 0
        verify_chain(self.store)
        recovered = 0
        for candidate in expired:
            with self.store.connection(write=True) as db:
                row = db.execute(
                    "SELECT * FROM experiment_jobs WHERE id=?", (candidate["id"],)
                ).fetchone()
                if (
                    row is None
                    or row["status"] != "RUNNING"
                    or row["fence"] != candidate["fence"]
                    or not (
                        row["lease_until"] <= self.store.clock()
                        or coordinator_alive(row["owner"]) is False
                    )
                ):
                    continue
                job = dict(row)
                # PID creation time binds this record to the original worker, not a reused PID.
                if job["worker_pid"] is not None:
                    try:
                        process = psutil.Process(job["worker_pid"])
                        if abs(process.create_time() - job["worker_created_at"]) < 0.001:
                            process.kill()
                            try:
                                process.wait(timeout=2)
                            except psutil.TimeoutExpired:
                                if process.status() != psutil.STATUS_ZOMBIE:
                                    raise ResourceBusy("ORPHAN_WORKER_NOT_TERMINATED") from None
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.AccessDenied:
                        raise ResourceBusy("ORPHAN_WORKER_PERMISSION_FAILURE") from None
                result = db.execute(
                    "UPDATE experiment_jobs SET status='ABANDONED',"
                    "error_count=error_count+1,last_error='INTERRUPTED_OUTCOME_UNKNOWN',"
                    "owner=NULL,lease_until=NULL WHERE id=? AND status='RUNNING' AND fence=? "
                    "AND (lease_until<=? OR owner=?)",
                    (
                        job["id"],
                        job["fence"],
                        self.store.clock(),
                        job["owner"] if coordinator_alive(job["owner"]) is False else "",
                    ),
                )
                if result.rowcount:
                    self.store._event(
                        db,
                        job["run_id"],
                        "job_reconciled",
                        {
                            "job_id": job["id"],
                            "fence": job["fence"],
                            "status": "ABANDONED",
                            "error_count": job["error_count"] + 1,
                            "reason": "INTERRUPTED_OUTCOME_UNKNOWN",
                            "next_action": "Retry pure trusted computation within limits",
                        },
                    )
                    recovered += 1
        return recovered

    def acquire(
        self,
        run_id: str,
        *,
        owner: str,
        run_fence: int,
        stage_version: int,
        plan: Plan,
        replication: int,
    ) -> tuple[str, int, dict[str, Any] | None]:
        from autodiscover.evidence.chain import verify_chain

        verify_chain(self.store)
        self.reconcile()
        if self.artifacts.put_json(plan.model_dump(mode="json")) != plan.digest:
            raise IntegrityError("Preregistration content address mismatch")
        identifier = hashlib.sha256(
            canonical(
                {"run_id": run_id, "stage_version": stage_version, "replication": replication}
            ).encode()
        ).hexdigest()
        with self.store.connection(write=True) as db:
            try:
                run = self.store._lease(db, run_id, owner, run_fence)
            except StateError:
                raise runner.WorkInterrupted("RUN_CONTROL_OR_LEASE_CHANGED") from None
            if run["version"] != stage_version:
                raise runner.WorkInterrupted("STALE_STAGE_VERSION")
            limits = Limits.model_validate_json(run["policy_json"])
            previous = db.execute(
                "SELECT * FROM experiment_jobs WHERE id=?", (identifier,)
            ).fetchone()
            if previous and previous["plan_digest"] != plan.digest:
                raise IntegrityError("Sub-job identity reused for a different preregistration")
            if previous and previous["status"] == "COMPLETED":
                return (
                    identifier,
                    previous["fence"],
                    self.artifacts.get_json(previous["artifact_digest"]),
                )
            if previous and previous["status"] == "RUNNING":
                raise ResourceBusy("SUBJOB_ALREADY_CLAIMED")
            if previous and previous["error_count"] > limits.max_retries_per_step:
                raise runner.ExecutionError("SUBJOB_RETRY_LIMIT")
            active = db.execute(
                "SELECT j.id,r.policy_json FROM experiment_jobs j "
                "JOIN runs r ON r.id=j.run_id WHERE j.status='RUNNING'"
            ).fetchall()
            ceiling = min(
                [limits.max_concurrent_experiments]
                + [
                    Limits.model_validate_json(r["policy_json"]).max_concurrent_experiments
                    for r in active
                ]
            )
            if len(active) >= ceiling:
                raise ResourceBusy("GLOBAL_EXPERIMENT_CONCURRENCY_LIMIT")
            fence = previous["fence"] + 1 if previous else 1
            attempts = previous["attempts"] + 1 if previous else 1
            if previous:
                db.execute(
                    "UPDATE experiment_jobs SET status='RUNNING',owner=?,fence=?,"
                    "lease_until=?,attempts=?,worker_pid=NULL,worker_created_at=NULL,"
                    "last_error=NULL "
                    "WHERE id=?",
                    (owner, fence, self.store.clock() + 180, attempts, identifier),
                )
            else:
                db.execute(
                    """INSERT INTO experiment_jobs(id,run_id,stage_version,replication,
                  plan_digest,status,owner,fence,lease_until,attempts,error_count)
                  VALUES(?,?,?,?,?,'RUNNING',?,?,?,1,0)""",
                    (
                        identifier,
                        run_id,
                        stage_version,
                        replication,
                        plan.digest,
                        owner,
                        fence,
                        self.store.clock() + 180,
                    ),
                )
            self.store._event(
                db,
                run_id,
                "job_claimed",
                {
                    "job_id": identifier,
                    "stage_version": stage_version,
                    "replication": replication,
                    "plan_digest": plan.digest,
                    "owner": owner,
                    "fence": fence,
                    "attempts": attempts,
                    "error_count": previous["error_count"] if previous else 0,
                    "concurrency_ceiling": ceiling,
                },
            )
        return identifier, fence, None

    def execute(
        self,
        run_id: str,
        *,
        owner: str,
        run_fence: int,
        stage_version: int,
        plan: Plan,
        limits: Limits,
        replication: int = 0,
        stop_requested: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        authorized_limits = Limits.model_validate_json(self.store.get_run(run_id)["policy_json"])
        if limits != authorized_limits:
            raise ValueError("Execution limits must match durable run policy")
        identifier, fence, cached = self.acquire(
            run_id,
            owner=owner,
            run_fence=run_fence,
            stage_version=stage_version,
            plan=plan,
            replication=replication,
        )
        if cached is not None:
            return cached
        last_heartbeat = [0.0]

        def guard() -> None:
            if stop_requested and stop_requested():
                raise runner.WorkInterrupted("WORKER_SHUTDOWN_REQUESTED")
            with self.store.connection() as db:
                try:
                    lease = self.store._lease(db, run_id, owner, run_fence)
                    if lease["version"] != stage_version:
                        raise StateError("Stage changed")
                except StateError:
                    raise runner.WorkInterrupted("RUN_CONTROL_OR_LEASE_CHANGED") from None
                job = db.execute(
                    "SELECT * FROM experiment_jobs WHERE id=?", (identifier,)
                ).fetchone()
                if (
                    job["owner"] != owner
                    or job["fence"] != fence
                    or job["status"] != "RUNNING"
                    or job["lease_until"] <= self.store.clock()
                ):
                    raise runner.WorkInterrupted("SUBJOB_LEASE_CHANGED")
            if time.monotonic() - last_heartbeat[0] >= 0.5:
                with self.store.connection(write=True) as db:
                    try:
                        self.store._lease(db, run_id, owner, run_fence)
                    except StateError:
                        raise runner.WorkInterrupted("RUN_CONTROL_OR_LEASE_CHANGED") from None
                    db.execute(
                        "UPDATE experiment_jobs SET lease_until=? WHERE id=? AND fence=?",
                        (self.store.clock() + 180, identifier, fence),
                    )
                    db.execute(
                        "UPDATE runs SET lease_until=? WHERE id=?",
                        (self.store.clock() + 180, run_id),
                    )
                last_heartbeat[0] = time.monotonic()

        def started(pid: int, created_at: float) -> None:
            guard()
            with self.store.connection(write=True) as db:
                result = db.execute(
                    "UPDATE experiment_jobs SET worker_pid=?,worker_created_at=? "
                    "WHERE id=? AND fence=? AND owner=? AND status='RUNNING'",
                    (pid, created_at, identifier, fence, owner),
                )
                if result.rowcount != 1:
                    raise runner.WorkInterrupted("SUBJOB_LEASE_CHANGED")
                self.store._event(
                    db,
                    run_id,
                    "job_worker_started",
                    {
                        "job_id": identifier,
                        "fence": fence,
                        "worker_pid": pid,
                        "worker_created_at": created_at,
                    },
                )

        try:
            raw = runner.run(plan, limits, replication=replication, guard=guard, on_started=started)
            digest = self.artifacts.put_json(raw)
            guard()
            with self.store.connection(write=True) as db:
                try:
                    self.store._lease(db, run_id, owner, run_fence)
                except StateError:
                    raise runner.WorkInterrupted("RUN_CONTROL_OR_LEASE_CHANGED") from None
                result = db.execute(
                    "UPDATE experiment_jobs SET status='COMPLETED',artifact_digest=?,"
                    "owner=NULL,lease_until=NULL WHERE id=? AND fence=? "
                    "AND owner=? AND status='RUNNING'",
                    (digest, identifier, fence, owner),
                )
                if result.rowcount != 1:
                    raise runner.WorkInterrupted("SUBJOB_LEASE_CHANGED")
                self.store._event(
                    db,
                    run_id,
                    "job_completed",
                    {
                        "job_id": identifier,
                        "fence": fence,
                        "artifact_digest": digest,
                        "elapsed_seconds": raw["elapsed_seconds"],
                        "peak_rss_bytes": raw["peak_rss_bytes"],
                    },
                )
            return raw
        except (runner.ExecutionError, runner.WorkInterrupted) as error:
            interrupted = isinstance(error, runner.WorkInterrupted)
            with self.store.connection(write=True) as db:
                result = db.execute(
                    "UPDATE experiment_jobs SET status=?,error_count=error_count+?,"
                    "last_error=?,owner=NULL,lease_until=NULL WHERE id=? AND fence=? AND owner=? "
                    "AND status='RUNNING'",
                    (
                        "ABANDONED" if interrupted else "FAILED",
                        int(not interrupted),
                        str(error),
                        identifier,
                        fence,
                        owner,
                    ),
                )
                if result.rowcount:
                    row = db.execute(
                        "SELECT error_count FROM experiment_jobs WHERE id=?", (identifier,)
                    ).fetchone()
                    self.store._event(
                        db,
                        run_id,
                        "job_interrupted" if interrupted else "job_failed",
                        {
                            "job_id": identifier,
                            "fence": fence,
                            "status": "ABANDONED" if interrupted else "FAILED",
                            "error_count": row[0],
                            "reason": str(error),
                        },
                    )
            raise

    def status(self, run_id: str | None = None) -> list[dict[str, Any]]:
        with self.store.connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM experiment_jobs WHERE (? IS NULL OR run_id=?) ORDER BY rowid",
                    (run_id, run_id),
                )
            ]
