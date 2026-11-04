"""Transactional WAL state machine, hash-chained events and fenced expiring claims."""

import hashlib
import json
import re
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from autodiscover.orchestrator.contracts import (
    BACKWARD,
    OUTPUTS,
    STAGES,
    RunStatus,
    Stage,
    StepInput,
)
from autodiscover.orchestrator.durability import append_event, atomic_json, canonical, now
from autodiscover.security.processes import coordinator_alive
from autodiscover.security.redaction import contains_credential


class StateError(RuntimeError):
    pass


class ControlConflict(StateError):
    pass


class Store:
    read_only = False

    def __init__(
        self, root: Path, *, clock: Callable[[], float] = time.time, initialize: bool = True
    ):
        self.root = root
        self.path = root / "lab.sqlite3"
        self.clock = clock
        if initialize:
            self.root.mkdir(parents=True, exist_ok=True)
            self._migrate()
        else:
            with SnapshotStore(root):
                pass  # Existing schema only; HTTP never initializes or migrates storage.

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def _migrate(self) -> None:
        from autodiscover.orchestrator.migrations import MIGRATIONS

        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
        with self.connection(write=True) as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > len(MIGRATIONS):
                raise StateError("Database schema newer than this application")
            for index in range(version, len(MIGRATIONS)):
                for statement in MIGRATIONS[index].split(";"):
                    if statement.strip():
                        db.execute(statement)
                db.execute(f"PRAGMA user_version={index + 1}")

    def _event(
        self, db: sqlite3.Connection, run_id: str, kind: str, payload: dict[str, Any]
    ) -> str:
        previous = db.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else "0" * 64
        event_id, timestamp = str(uuid4()), now()
        body = {
            "id": event_id,
            "run_id": run_id,
            "kind": kind,
            "payload_json": canonical(payload),
            "timestamp": timestamp,
            "previous_hash": previous_hash,
        }
        digest = hashlib.sha256(canonical(body).encode()).hexdigest()
        db.execute(
            """INSERT INTO events(id,run_id,kind,payload_json,timestamp,previous_hash,hash)
                      VALUES(?,?,?,?,?,?,?)""",
            (*body.values(), digest),
        )
        return event_id

    def create_run(
        self,
        topic: str,
        policy: dict[str, Any],
        run_id: str | None = None,
        *,
        discovery_digest: str | None = None,
    ) -> str:
        from autodiscover.config import Limits

        policy = Limits.model_validate(policy).model_dump(mode="json")
        if contains_credential(topic):
            raise ValueError("Credential material is not permitted in research topics")
        if not topic.strip() or len(topic) > 1000:
            raise ValueError("Topic must contain 1–1000 characters")
        run_id = run_id or str(uuid4())
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
            raise ValueError("Unsafe run identifier")
        with self.connection(write=True) as db:
            timestamp = now()
            db.execute(
                """INSERT INTO runs(id,topic,stage,status,created_at,updated_at,policy_json)
                          VALUES(?,?,?,?,?,?,?)""",
                (
                    run_id,
                    topic,
                    Stage.DISCOVER,
                    RunStatus.ACTIVE,
                    timestamp,
                    timestamp,
                    canonical(policy),
                ),
            )
            self._event(
                db,
                run_id,
                "run_created",
                {"policy": policy, "topic_sha256": hashlib.sha256(topic.encode()).hexdigest()},
            )
            if discovery_digest is not None:
                self._event(
                    db, run_id, "discovery_registered", {"artifact_digest": discovery_digest}
                )
        self.checkpoint(run_id)
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self.connection() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise StateError("Unknown run")
        return dict(row)

    def is_discovery(self, run_id: str) -> bool:
        with self.connection() as db:
            return (
                db.execute(
                    "SELECT 1 FROM events WHERE run_id=? AND kind='discovery_registered'", (run_id,)
                ).fetchone()
                is not None
            )

    def list_runs(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM runs ORDER BY created_at,id")]

    def claim(self, run_id: str, owner: str, seconds: float = 30) -> int:
        if not owner or not 0 < seconds <= 300:
            raise ValueError("Nonempty owner and lease 0–300 seconds required")
        with self.connection(write=True) as db:
            previous = db.execute("SELECT owner FROM runs WHERE id=?", (run_id,)).fetchone()
            dead_owner = previous[0] if previous and coordinator_alive(previous[0]) is False else ""
            cursor = db.execute(
                """UPDATE runs SET owner=?,fence=fence+1,lease_until=?
                WHERE id=? AND status=? AND (owner IS NULL OR lease_until<=? OR owner=?)""",
                (owner, self.clock() + seconds, run_id, RunStatus.ACTIVE, self.clock(), dead_owner),
            )
            if cursor.rowcount != 1:
                raise StateError("Run not available for claim")
            fence = db.execute("SELECT fence FROM runs WHERE id=?", (run_id,)).fetchone()[0]
            self._event(db, run_id, "claimed", {"owner": owner, "fence": fence})
        return fence

    def _lease(self, db: sqlite3.Connection, run_id: str, owner: str, fence: int) -> sqlite3.Row:
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if (
            row is None
            or row["status"] != RunStatus.ACTIVE
            or row["owner"] != owner
            or row["fence"] != fence
            or row["lease_until"] <= self.clock()
        ):
            raise StateError("Stale, expired or unauthorized worker")
        return row

    def heartbeat(self, run_id: str, owner: str, fence: int, seconds: float = 30) -> None:
        if not 0 < seconds <= 300:
            raise ValueError("Invalid lease duration")
        with self.connection(write=True) as db:
            self._lease(db, run_id, owner, fence)
            db.execute("UPDATE runs SET lease_until=? WHERE id=?", (self.clock() + seconds, run_id))

    def release(self, run_id: str, owner: str, fence: int) -> None:
        with self.connection(write=True) as db:
            result = db.execute(
                """UPDATE runs SET owner=NULL,lease_until=NULL
                          WHERE id=? AND owner=? AND fence=?""",
                (run_id, owner, fence),
            )
            if result.rowcount:
                self._event(db, run_id, "run_released", {"owner": None, "fence": fence})

    def step_input(self, run_id: str) -> StepInput:
        row = self.get_run(run_id)
        with self.connection() as db:
            predecessor = db.execute(
                """SELECT id FROM events WHERE run_id=?
                AND kind='stage_completed' ORDER BY seq DESC LIMIT 1""",
                (run_id,),
            ).fetchone()
        return StepInput(
            run_id=run_id,
            stage=Stage(row["stage"]),
            version=row["version"],
            predecessor_event=predecessor[0] if predecessor else None,
        )

    def complete_step(
        self,
        run_id: str,
        *,
        owner: str,
        fence: int,
        expected: Stage,
        version: int,
        key: str,
        output: dict[str, Any],
        target: Stage | None = None,
        reason: str | None = None,
        resources: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not key or len(key) > 200:
            raise ValueError("Bounded nonempty idempotency key required")
        validated = OUTPUTS[expected].model_validate(output).model_dump(mode="json")
        request = {
            "expected": expected,
            "version": version,
            "output": validated,
            "target": target,
            "reason": reason,
            "resources": resources or {},
        }
        input_hash = hashlib.sha256(canonical(request).encode()).hexdigest()
        with self.connection(write=True) as db:
            # A lease is always required even on idempotent replay: stale workers cannot act.
            row = self._lease(db, run_id, owner, fence)
            existing = db.execute(
                "SELECT * FROM steps WHERE run_id=? AND idempotency_key=?", (run_id, key)
            ).fetchone()
            if existing:
                if existing["input_hash"] != input_hash:
                    raise StateError("Idempotency key reused with different inputs")
                return json.loads(existing["result_json"])
            if row["stage"] != expected or row["version"] != version:
                raise StateError("Stage/version changed; reload durable state")
            forward = STAGES[STAGES.index(expected) + 1] if expected != Stage.DECIDE else None
            destination = target or forward
            if target is not None and target != forward:
                terminal_failure = False
                if (
                    expected in (Stage.VERIFY, Stage.REPLICATE)
                    and target == Stage.DECIDE
                    and not validated["passed"]
                    and reason
                ):
                    from autodiscover.hypotheses.director import Director

                    references = (
                        [validated["report_digest"]]
                        if expected == Stage.VERIFY
                        else validated["report_digests"]
                    )
                    recorded = any(
                        db.execute(
                            "SELECT 1 FROM branch_results WHERE run_id=? "
                            "AND report_digest=? AND passed=0",
                            (run_id, digest),
                        ).fetchone()
                        for digest in references
                    )
                    terminal_failure = recorded and not Director(self).has_work(run_id)
                if (
                    target not in BACKWARD.get(expected, set()) or not reason
                ) and not terminal_failure:
                    raise StateError("Backward transition needs an allowable target and reason")
            if expected in (Stage.VERIFY, Stage.REPLICATE) and not validated["passed"]:
                if destination not in BACKWARD[expected] and destination != Stage.DECIDE:
                    raise StateError("Failed verification cannot advance")
            if expected == Stage.DECIDE:
                if validated["decision"] == "stop" and target is not None:
                    raise StateError("Stop decision must complete the run")
                if validated["decision"] != "stop" and target is None:
                    raise StateError("Continued research requires an explicit backward action")
            status = RunStatus.COMPLETED if destination is None else RunStatus.ACTIVE
            event_id = self._event(
                db,
                run_id,
                "stage_completed",
                {
                    "stage": expected,
                    "target": destination,
                    "version": version,
                    "output": validated,
                    "resources": resources or {},
                    "reason": reason,
                    "next_allowable_actions": [s.value for s in BACKWARD.get(expected, set())],
                },
            )
            result = {
                "event_id": event_id,
                "stage": destination or expected,
                "version": version + 1,
                "status": status,
            }
            db.execute(
                """INSERT INTO steps VALUES(?,?,?,?,?,?,?,?)""",
                (
                    str(uuid4()),
                    run_id,
                    key,
                    input_hash,
                    expected,
                    destination,
                    canonical(validated),
                    canonical(result),
                ),
            )
            db.execute(
                """UPDATE runs SET stage=?,status=?,version=version+1,updated_at=?,
                       failures=0,last_error=NULL WHERE id=?""",
                (destination or expected, status, now(), run_id),
            )
        self.checkpoint(run_id)
        return result

    def fail_step(self, run_id: str, owner: str, fence: int, error_code: str) -> str:
        # Error codes only; never persist provider exception bodies or credentials.
        if not error_code.replace("_", "").isalnum() or len(error_code) > 100:
            raise ValueError("Failure requires a bounded machine error code")
        with self.connection(write=True) as db:
            row = self._lease(db, run_id, owner, fence)
            failures = row["failures"] + 1
            policy = json.loads(row["policy_json"])
            status = (
                RunStatus.FAILED if failures > policy["max_retries_per_step"] else RunStatus.ACTIVE
            )
            db.execute(
                """UPDATE runs SET failures=?,last_error=?,status=?,updated_at=?
                        WHERE id=?""",
                (failures, error_code, status, now(), run_id),
            )
            self._event(
                db,
                run_id,
                "step_failed",
                {
                    "error_code": error_code,
                    "attempt": failures,
                    "retry_allowed": status == RunStatus.ACTIVE,
                },
            )
        self.checkpoint(run_id)
        return status

    def control(
        self,
        run_id: str,
        action: str,
        *,
        expected_version: int | None = None,
        expected_fence: int | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any] | None:
        guarded = request_id is not None
        guard_fields = (expected_version, expected_fence, request_id)
        if any(value is not None for value in guard_fields) and not all(
            value is not None for value in guard_fields
        ):
            raise ValueError("Operator commands require identity, version and fence together")
        if guarded and not re.fullmatch(r"[a-f0-9-]{36}", request_id or ""):
            raise ValueError("Operator command identity must be a UUID")
        command = {
            "id": request_id,
            "expected_version": expected_version,
            "expected_fence": expected_fence,
        }
        allowed = {
            "pause": (RunStatus.ACTIVE, RunStatus.PAUSED),
            "resume": (RunStatus.PAUSED, RunStatus.ACTIVE),
        }
        with self.connection(write=True) as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise StateError("Unknown run")
            if guarded:
                from autodiscover.evidence.chain import verify_chain

                verify_chain(self)  # Writer lock excludes competing mutations during this audit.
                old = db.execute(
                    "SELECT payload_json FROM events WHERE run_id=? AND kind='control' "
                    "AND json_extract(payload_json,'$.command.id')=?",
                    (run_id, request_id),
                ).fetchone()
                if old:
                    payload = json.loads(old[0])
                    if payload["command"] != command or payload["action"] != action:
                        raise ControlConflict("Command identity reused with different inputs")
                    return {**payload["receipt"], "replayed": True}
                if row["version"] != expected_version or row["fence"] != expected_fence:
                    raise ControlConflict("Run changed; refresh before issuing a command")
            if action == "cancel" and row["status"] in (RunStatus.ACTIVE, RunStatus.PAUSED):
                destination = RunStatus.CANCELLED
            elif action in allowed and row["status"] == allowed[action][0]:
                destination = allowed[action][1]
            else:
                raise ControlConflict("Control not allowed in current status")
            db.execute(
                """UPDATE runs SET status=?,owner=NULL,lease_until=NULL,fence=fence+1,
                        updated_at=? WHERE id=?""",
                (destination, now(), run_id),
            )
            payload: dict[str, Any] = {"action": action, "status": destination}
            receipt = None
            if guarded:
                receipt = {
                    "run_id": run_id,
                    "request_id": request_id,
                    "action": action,
                    "status": destination,
                    "version": row["version"],
                    "fence": row["fence"] + 1,
                }
                payload.update(command=command, receipt=receipt)
            self._event(db, run_id, "control", payload)
        self.checkpoint(run_id)
        return {**receipt, "replayed": False} if receipt is not None else None

    def outputs(self, run_id: str) -> list[dict[str, Any]]:
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM steps WHERE run_id=? ORDER BY rowid", (run_id,)
                )
            ]

    def checkpoint(self, run_id: str) -> None:
        # Derived projection only: SQLite remains authoritative after crash in this write.
        row = self.get_run(run_id)
        with self.connection() as db:
            anchor = db.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        atomic_json(
            self.root / "checkpoints" / f"{run_id}.json",
            {
                "schema_version": 1,
                "run": row,
                "evidence_anchor": dict(anchor) if anchor else None,
                "recovery": "Load authoritative SQLite state and reclaim expired lease",
            },
        )

        append_event(
            self.root / "logs" / "execution.jsonl",
            run_id=run_id,
            task_id=f"stage-{row['stage']}",
            event="checkpoint_saved",
            details={
                "stage": row["stage"],
                "status": row["status"],
                "version": row["version"],
                "evidence_anchor": dict(anchor) if anchor else None,
            },
        )


class SnapshotStore(Store):
    """Existing-schema, query-only SQLite snapshot; never initializes or migrates a root."""

    read_only = True

    def __init__(self, root: Path):
        self.root, self.path, self.clock = root, root / "lab.sqlite3", time.time
        self._db: sqlite3.Connection | None = None

    def __enter__(self) -> "SnapshotStore":
        from autodiscover.orchestrator.migrations import MIGRATIONS

        self._db = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        self._db.row_factory = sqlite3.Row
        try:
            self._db.execute("PRAGMA query_only=ON")
            self._db.execute("BEGIN")
            if self._db.execute("PRAGMA user_version").fetchone()[0] != len(MIGRATIONS):
                raise StateError("Read views require the current schema; initialize using the CLI")
            self._db.execute("SELECT seq FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_args: Any) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        if write:
            raise StateError("Snapshot is read only")
        if self._db is None:
            raise StateError("Snapshot context is closed")
        yield self._db

    def checkpoint(self, run_id: str) -> None:
        raise StateError("Snapshot cannot persist checkpoints")
