"""Transactional nano-USD accounting and durable request reservations."""


import hashlib
import json
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from typing import Any
from uuid import uuid4

from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store

NANO = Decimal(1000000000)


class BudgetError(RuntimeError):
    pass


def nano(amount: Decimal) -> int:
    if not amount.is_finite() or amount < 0:
        raise ValueError("Finite nonnegative money required")
    return int((amount * NANO).to_integral_value(rounding=ROUND_CEILING))


class Budget:
    def __init__(self, store: Store):
        self.store = store

    def reserve(
        self,
        run_id: str,
        key: str,
        fingerprint: str,
        amount: Decimal,
        provider: str,
        model: str,
    ) -> str:
        reserved = nano(amount)
        day = datetime.fromtimestamp(self.store.clock(), UTC).date().isoformat()
        with self.store.connection(write=True) as db:
            row = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None or row["status"] != "ACTIVE":
                raise BudgetError("Run not active")
            existing = db.execute(
                "SELECT * FROM reservations WHERE run_id=? AND request_key=?", (run_id, key)
            ).fetchone()
            if existing:
                raise BudgetError("Request already reserved; reconcile rather than replay")
            identifier = str(uuid4())
            db.execute(
                """INSERT INTO reservations(id,run_id,request_key,fingerprint,day,
              provider,model,reserved_nano,charged_nano,status)
              VALUES(?,?,?,?,?,?,?,?,?,'RESERVED')""",
                (identifier, run_id, key, fingerprint, day, provider, model, reserved, reserved),
            )
            self.store._event(
                db,
                run_id,
                "cost_reserved",
                {
                    "reservation": identifier,
                    "provider": provider,
                    "model": model,
                    "amount_nano": reserved,
                },
            )
        return identifier

    def settle(
        self,
        identifier: str,
        actual: Decimal | None,
        *,
        usage: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        with self.store.connection(write=True) as db:
            row = db.execute("SELECT * FROM reservations WHERE id=?", (identifier,)).fetchone()
            if row is None or row["status"] != "RESERVED":
                raise BudgetError("Reservation not open")
            amount = row["reserved_nano"] if actual is None else nano(actual)
            status = "UNCERTAIN" if actual is None else "SETTLED"
            db.execute(
                "UPDATE reservations SET charged_nano=?,status=?,usage_json=?,result_json=? "
                "WHERE id=?",
                (
                    amount,
                    status,
                    canonical(usage or {}),
                    canonical(result) if result else None,
                    identifier,
                ),
            )
            self.store._event(
                db,
                row["run_id"],
                "cost_settled",
                {
                    "reservation": identifier,
                    "charged_nano": amount,
                    "status": status,
                    "usage": usage or {},
                },
            )

    def cached(self, run_id: str, key: str, fingerprint: str) -> dict[str, Any] | None:
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT * FROM reservations WHERE run_id=? AND request_key LIKE ?",
                (run_id, key + ":%"),
            ).fetchall()
        for row in rows:
            # Prefix SQL LIKE is followed by an exact base-key check (keys may contain %/_).
            if row["request_key"].rsplit(":", 1)[0] != key:
                continue
            if row["fingerprint"] != fingerprint:
                raise BudgetError("Request identity conflict")
            if row["result_json"]:
                return json.loads(row["result_json"])
        if any(r["request_key"].rsplit(":", 1)[0] == key for r in rows):
            raise BudgetError(
                "Prior request incomplete or failed; explicit reconciliation required"
            )
        return None

    def totals(self, run_id: str) -> dict[str, Any]:
        with self.store.connection() as db:
            rows = db.execute("SELECT * FROM reservations WHERE run_id=?", (run_id,)).fetchall()
        return {
            "charged_usd": str(Decimal(sum(r["charged_nano"] for r in rows)) / NANO),
            "settled_usd": str(
                Decimal(sum(r["charged_nano"] for r in rows if r["status"] == "SETTLED")) / NANO
            ),
            "reserved_usd": str(
                Decimal(sum(r["charged_nano"] for r in rows if r["status"] == "RESERVED")) / NANO
            ),
            "uncertain_usd": str(
                Decimal(sum(r["charged_nano"] for r in rows if r["status"] == "UNCERTAIN")) / NANO
            ),
            "requests": len(rows),
            "uncertain": sum(r["status"] != "SETTLED" for r in rows),
            "input_tokens": sum(
                json.loads(r["usage_json"] or "{}").get("input_tokens", 0) for r in rows
            ),
            "output_tokens": sum(
                json.loads(r["usage_json"] or "{}").get("output_tokens", 0) for r in rows
            ),
        }


def request_fingerprint(request: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(request).encode()).hexdigest()
