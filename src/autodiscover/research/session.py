"""Persistent, foreground controller for bounded Discovery-v2 branches."""

import hashlib
import json
import re
import sqlite3
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.models.contracts import ProviderError
from autodiscover.orchestrator.durability import canonical, now
from autodiscover.orchestrator.store import StateError, Store
from autodiscover.research.discovery import Discovery, _journal, _usage, replay
from autodiscover.research.discovery_contracts import (
    Evidence,
    QualityProposal,
    Report,
    SessionContext,
)
from autodiscover.research.session_contracts import BranchIntent, BranchOutcome, SessionProfile
from autodiscover.security.budget import BudgetError
from autodiscover.security.processes import coordinator_alive, local_owner
from autodiscover.security.redaction import contains_credential

LANES = (
    "Investigate consequential unanswered questions and inefficient methods across industries.",
    "Look for conflicting findings and useful mechanisms that might transfer across disciplines.",
    "Investigate emerging methods and plausible applications with an existing comparison.",
    "Pursue an unresolved evidence gap from prior work or explore a distinct research direction.",
    "Explore creative, consumer, entertainment or other applications if evidence warrants.",
)
EVENTS = """
    SELECT kind,payload_json,timestamp FROM events WHERE run_id=?
    AND (kind LIKE 'session_%' OR kind='control') ORDER BY seq
"""


def words(text: str) -> list[str]:
    return sorted(set(re.findall(r"[^\W_]+", text.casefold())))


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _similar(candidate: list[str], previous: list[str]) -> bool:
    a, b = set(candidate), set(previous)
    return bool(a and b and (a == b or (len(a & b) >= 5 and len(a & b) / len(a | b) >= 0.82)))


def _events(db: sqlite3.Connection, session_id: str) -> list[tuple[str, dict, str]]:
    return [(r[0], json.loads(r[1]), r[2]) for r in db.execute(EVENTS, (session_id,))]


def _read(store: Store, session_id: str) -> list[tuple[str, dict, str]]:
    with store.connection() as db:
        events = _events(db, session_id)
    if not events or events[0][0] != "session_registered":
        raise StateError("Unknown research session")
    return events


def _pause_pending(db: sqlite3.Connection, session_id: str) -> bool:
    row = db.execute(
        "SELECT kind FROM events WHERE run_id=? "
        "AND kind IN ('session_pause_requested','session_resumed') ORDER BY seq DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    return row is not None and row[0] == "session_pause_requested"


def _paused(events: list[tuple[str, dict, str]]) -> bool:
    return next(
        (
            kind == "session_pause_requested"
            for kind, _, _ in reversed(events)
            if kind in ("session_pause_requested", "session_resumed")
        ),
        False,
    )


def _portfolio(
    events: list[tuple[str, dict, str]],
) -> tuple[list[BranchIntent], list[BranchOutcome]]:
    intents = [
        BranchIntent.model_validate(p) for kind, p, _ in events if kind == "session_branch_admitted"
    ]
    outcomes = [
        BranchOutcome.model_validate(p) for kind, p, _ in events if kind == "session_branch_closed"
    ]
    by_number = {intent.number: intent for intent in intents}
    if (
        list(by_number) != list(range(len(intents)))
        or len(by_number) != len(intents)
        or len({o.number for o in outcomes}) != len(outcomes)
        or any(
            o.number not in by_number or by_number[o.number].child_id != o.child_id
            for o in outcomes
        )
    ):
        raise IntegrityError("Session branch history is inconsistent")
    return intents, outcomes


def _aggregate(store: Store, intents: list[BranchIntent]) -> tuple[dict[str, Any], list[dict]]:
    totals: dict[str, Any] = {
        "requests": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens_reported": 0,
        "attempts_reporting_reasoning": 0,
        "uncertain": 0,
        "charged_usd": "0",
        "settled_usd": "0",
        "reserved_usd": "0",
        "uncertain_usd": "0",
    }
    unresolved = []
    with store.connection() as db:
        for intent in intents:
            for row in db.execute(
                "SELECT id,request_key,provider,model,status,usage_json,charged_nano "
                "FROM reservations WHERE run_id=?",
                (intent.child_id,),
            ):
                totals["requests"] += 1
                usage = json.loads(row["usage_json"] or "{}")
                for key in ("input_tokens", "output_tokens"):
                    totals[key] += usage.get(key, 0)
                if "reasoning_tokens" in usage:
                    totals["attempts_reporting_reasoning"] += 1
                    totals["reasoning_tokens_reported"] += usage["reasoning_tokens"]
                charged = Decimal(row["charged_nano"]) / Decimal(1_000_000_000)
                for key in ("charged_usd", row["status"].lower() + "_usd"):
                    totals[key] = str(Decimal(totals[key]) + charged)
                if row["status"] != "SETTLED":
                    totals["uncertain"] += 1
                    unresolved.append(
                        {
                            "child_id": intent.child_id,
                            **{
                                k: row[k]
                                for k in ("id", "request_key", "provider", "model", "status")
                            },
                        }
                    )
    return totals, unresolved


def _provider_streak(db: sqlite3.Connection, session_id: str) -> int:
    rows = db.execute(
        """SELECT request.kind FROM events AS intent JOIN events AS request
        ON request.run_id=json_extract(intent.payload_json,'$.child_id')
        WHERE intent.run_id=? AND intent.kind='session_branch_admitted'
          AND request.kind IN ('provider_failed','provider_selected')
        ORDER BY request.seq DESC""",
        (session_id,),
    )
    count = 0
    for row in rows:
        if row[0] == "provider_selected":
            break
        count += 1
    return count


def registration(store: Store, session_id: str) -> dict[str, Any]:
    digest = _read(store, session_id)[0][1]["artifact_digest"]
    return Artifacts(store.root / "artifacts", read_only=True).get_json(digest)


def create_session(store: Store, profile: SessionProfile, plan: dict, *, live: bool) -> str:
    verify_chain(store)
    if contains_credential(canonical(profile.model_dump(mode="json"))):
        raise ValueError("Session profile contains credential material")
    manifest = {
        "profile": profile.model_dump(mode="json"),
        "admission": plan,
        "live": live,
    }
    digest = Artifacts(store.root / "artifacts").put_json(manifest)
    return store.create_run(
        profile.discovery.objective,
        Limits().model_dump(),
        "session-" + uuid4().hex,
        session_digest=digest,
    )


def _summarize(
    intent: BranchIntent,
    digest: str,
    packet: Report,
    history: list[BranchOutcome],
) -> BranchOutcome:
    fingerprints = [signature for old in history for signature in old.candidates]
    candidates: list[list[str]] = []
    duplicates, qualified = [], []
    for candidate in packet.candidates:
        hypothesis = candidate.revised or candidate.original
        signature = words(hypothesis.mechanism + " " + hypothesis.problem)
        if any(_similar(signature, old) for old in fingerprints + candidates):
            duplicates.append(candidate.direction)
        elif candidate.disposition == "external_review_required":
            qualified.append(candidate.direction)
        candidates.append(signature)
    sources = [source for search in packet.searches for source in search.evidence]
    substantive = [s for s in sources if s.scope != "title"]
    negatives = [candidate.issues[0] for candidate in packet.candidates if candidate.issues]
    negatives.extend(
        trace.original.extraction.gap
        for trace in (packet.quality_closed_directions or {}).values()
        if trace.original.extraction.gap
    )
    question = packet.plan.directions[0].question
    note = f"{question} First unresolved issue: {negatives[0]}" if negatives else question
    if substantive:
        note += f" Captured source {substantive[0].source_id}."
    return BranchOutcome(
        number=intent.number,
        child_id=intent.child_id,
        packet_digest=digest,
        searched=len(packet.searches),
        proposed=len(packet.candidates),
        reviewed=packet.critique_coverage or 0,
        rejected=sum(c.disposition == "rejected" for c in packet.candidates),
        revised=sum(bool(c.quality and c.quality.revised) for c in packet.candidates),
        prior_art=sum(c.scientific_gate.prior_art_identified for c in packet.candidates),
        duplicate_queries=sum("SESSION_DUPLICATE_QUERY" in s.failures for s in packet.searches),
        source_failures=sum(
            len(set(s.failures) - {"SESSION_DUPLICATE_QUERY"}) for s in packet.searches
        ),
        source_ids=sorted({s.source_id for s in sources}),
        publications=sorted({s.url.casefold().rstrip("/") for s in substantive}),
        excerpts=sorted(
            {
                fingerprint(" ".join(words(s.excerpt.removeprefix(s.title + ". "))))
                for s in substantive
            }
        ),
        candidates=candidates,
        qualified_directions=qualified,
        duplicate_directions=duplicates,
        next_evidence=note[:700],
    )


def _progress(outcomes: list[BranchOutcome]) -> tuple[list[dict], int, int]:
    series, stagnant, errors = [], 0, 0
    publications: set[str] = set()
    excerpts: set[str] = set()
    for outcome in outcomes:
        new_publications = set(outcome.publications) - publications
        new_excerpts = set(outcome.excerpts) - excerpts
        publications.update(outcome.publications)
        excerpts.update(outcome.excerpts)
        progress = bool((new_publications and new_excerpts) or outcome.qualified_directions)
        stagnant = 0 if progress else stagnant + 1
        errors = errors + 1 if outcome.provider_error else 0
        series.append(
            {
                "branch": outcome.number,
                "new_publications": len(new_publications),
                "new_substantive_excerpts": len(new_excerpts),
                "provisional_candidates": len(outcome.qualified_directions),
                "stagnant": not progress,
            }
        )
    return series, stagnant, errors


def request_pause(store: Store, session_id: str) -> None:
    verify_chain(store)
    with store.connection(write=True) as db:
        events = _events(db, session_id)
        row = db.execute("SELECT status FROM runs WHERE id=?", (session_id,)).fetchone()
        if not events or events[0][0] != "session_registered" or not row or row[0] != "ACTIVE":
            raise StateError("Only an active session can pause")
        if not _paused(events):
            store._event(db, session_id, "session_pause_requested", {})
    store.checkpoint(session_id)


class Session:
    def __init__(
        self,
        store: Store,
        factory: Callable[[int], Discovery],
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.store, self.factory, self.monotonic = store, factory, monotonic

    def execute(
        self,
        session_id: str,
        *,
        stop: threading.Event | None = None,
        resume: bool = False,
    ) -> None:
        store = self.store
        verify_chain(store)
        registered = registration(store, session_id)
        profile = SessionProfile.model_validate(registered["profile"])
        events = _read(store, session_id)
        intents, _outcomes = _portfolio(events)
        _, unresolved = _aggregate(store, intents)
        status = store.get_run(session_id)["status"]
        if resume and status == "PAUSED":
            if unresolved:
                raise StateError("Session has ambiguous reservations; reconciliation required")
            store.control(session_id, "resume")
        owner = local_owner()
        fence = store.claim(session_id, owner, 300)
        stop = stop or threading.Event()
        unsafe = threading.Event()
        try:
            with store.connection(write=True) as db:
                store._lease(db, session_id, owner, fence)
                events = _events(db, session_id)
                previous = next((p for k, p, _ in events if k == "session_started"), None)
                started = previous["started"] if previous else store.clock()
                deadline = started + profile.duration_seconds
                if previous is None:
                    store._event(db, session_id, "session_started", {"started": started})
                elif resume and not _paused(events):
                    store._event(db, session_id, "session_resumed", {})
                elif resume and status == "PAUSED":
                    store._event(db, session_id, "session_resumed", {})
            monotonic_deadline = self.monotonic() + max(0.0, deadline - store.clock())

            def expired() -> bool:
                return store.clock() >= deadline or self.monotonic() >= monotonic_deadline

            def hard_stop() -> bool:
                if unsafe.is_set() or expired():
                    return True
                row = store.get_run(session_id)
                return row["status"] != "ACTIVE" or row["owner"] != owner or row["fence"] != fence

            def soft_stop() -> bool:
                with store.connection() as db:
                    return stop.is_set() or _pause_pending(db, session_id)

            def guard(db: sqlite3.Connection, _run_id: str) -> None:
                store._lease(db, session_id, owner, fence)
                if expired() or unsafe.is_set() or stop.is_set() or _pause_pending(db, session_id):
                    raise StateError("Session is no longer admitting external work")

            def worker(
                intent: BranchIntent,
            ) -> tuple[BranchIntent, str | None, Report | None, str | None, bool]:
                lab = self.factory(intent.number)

                def reserve_guard(db: sqlite3.Connection, run_id: str) -> None:
                    guard(db, run_id)
                    if _provider_streak(db, session_id) >= profile.max_consecutive_errors:
                        raise ProviderError("SESSION_PROVIDER_ERROR_LIMIT", known_zero_cost=True)
                    attempts = db.execute(
                        "SELECT count(*) FROM reservations WHERE run_id=?", (run_id,)
                    ).fetchone()[0]
                    if run_id != intent.child_id or attempts >= registered["admission"]["attempts"]:
                        raise BudgetError("Branch reservation bound reached")

                lab.router.budget.admission = reserve_guard

                def query_allowed(key: str, query: str) -> bool:
                    query_digest = fingerprint(" ".join(words(query)))
                    with store.connection(write=True) as db:
                        guard(db, intent.child_id)
                        old = db.execute(
                            "SELECT payload_json FROM events WHERE run_id=? "
                            "AND kind='session_query' AND json_extract(payload_json,'$.query')=?",
                            (session_id, query_digest),
                        ).fetchone()
                        if old:
                            entry = json.loads(old[0])
                            return entry["child_id"] == intent.child_id and entry["key"] == key
                        store._event(
                            db,
                            session_id,
                            "session_query",
                            {
                                "query": query_digest,
                                "child_id": intent.child_id,
                                "key": key,
                            },
                        )
                    return True

                def proposal_allowed(
                    key: str,
                    proposal: QualityProposal,
                    evidence: list[Evidence],
                ) -> bool:
                    h = proposal.hypothesis
                    signature = words(h.mechanism + " " + h.problem)
                    cited = {citation.source_id for citation in h.evidence}
                    inputs = sorted(
                        {
                            fingerprint(" ".join(words(s.excerpt.removeprefix(s.title + ". "))))
                            for s in evidence
                            if s.source_id in cited and s.scope != "title"
                        }
                    )
                    with store.connection(write=True) as db:
                        guard(db, intent.child_id)
                        rows = db.execute(
                            "SELECT payload_json FROM events WHERE run_id=? "
                            "AND kind='session_proposal' ORDER BY seq",
                            (session_id,),
                        ).fetchall()
                        for row in rows:
                            old = json.loads(row[0])
                            if old["child_id"] == intent.child_id and old["key"] == key:
                                return old["allowed"]
                        prior = [
                            old
                            for row in rows
                            if (old := json.loads(row[0]))["allowed"]
                            and _similar(signature, old["signature"])
                            and not (
                                old["child_id"] == intent.child_id
                                and old["key"].removeprefix("revision-")
                                == key.removeprefix("revision-")
                            )
                        ]
                        allowed = not prior or (
                            len(prior) == 1 and bool(set(inputs) - set(prior[0]["inputs"]))
                        )
                        store._event(
                            db,
                            session_id,
                            "session_proposal",
                            {
                                "child_id": intent.child_id,
                                "key": key,
                                "signature": signature,
                                "inputs": inputs,
                                "allowed": allowed,
                                "prior_branch": prior[0]["child_id"] if prior else None,
                            },
                        )
                        return allowed

                try:
                    child = lab.register(intent.specification, stable=True)
                    if child != intent.child_id:
                        raise IntegrityError("Branch registration differs from its session intent")
                    digest, packet = lab.execute(
                        child,
                        stop_requested=hard_stop,
                        boundary_stop=soft_stop,
                        search_admission=query_allowed,
                        session_id=session_id,
                        proposal_admission=proposal_allowed,
                    )
                    return intent, digest, packet, None, False
                except ProviderError as exc:
                    if exc.uncertain or _usage(store, intent.child_id)["uncertain"]:
                        unsafe.set()
                    code = (
                        exc.code
                        if re.fullmatch(r"[A-Z][A-Z0-9_]{1,99}", exc.code)
                        else "PROVIDER_ERROR"
                    )
                    return intent, None, None, code, True
                except BudgetError:
                    unsafe.set()
                    return intent, None, None, "REQUEST_RECONCILIATION_REQUIRED", True
                except StateError:
                    if hard_stop() or soft_stop():
                        return intent, None, None, None, False
                    return intent, None, None, "BRANCH_TIME_OR_LEASE_LIMIT", False

            with ThreadPoolExecutor(max_workers=profile.concurrency) as pool:
                while True:
                    history = _read(store, session_id)
                    intents, outcomes = _portfolio(history)
                    _, pending = _aggregate(store, intents)
                    _, stagnant, errors = _progress(outcomes)
                    with store.connection() as db:
                        errors = max(errors, _provider_streak(db, session_id))
                    open_branches = [
                        i for i in intents if i.number not in {o.number for o in outcomes}
                    ]
                    reason = self._stop_reason(
                        profile,
                        registered["admission"],
                        len(intents),
                        bool(open_branches),
                        bool(pending) or unsafe.is_set(),
                        expired(),
                        soft_stop(),
                        stagnant,
                        errors,
                    )
                    if hard_stop() and not expired() and not unsafe.is_set():
                        break
                    if (
                        reason is None
                        and profile.pause_after_first_branch
                        and len(outcomes) == 1
                        and not any(
                            k == "session_stopped" and p["reason"] == "QUALIFICATION_CHECKPOINT"
                            for k, p, _ in history
                        )
                    ):
                        reason = ("PAUSED", "QUALIFICATION_CHECKPOINT")
                    if reason:
                        self._finish(session_id, owner, fence, *reason)
                        break
                    store.heartbeat(session_id, owner, fence, 300)
                    batch = open_branches[: profile.concurrency]
                    if not batch:
                        for _ in range(profile.concurrency):
                            if self._admission_stop(profile, registered["admission"], len(intents)):
                                break
                            try:
                                intent = self._admit(session_id, profile, intents, outcomes, guard)
                            except StateError:
                                if hard_stop() or soft_stop():
                                    break
                                raise
                            intents.append(intent)
                            batch.append(intent)
                    if not batch:
                        continue
                    for intent, digest, packet, error, provider_error in pool.map(worker, batch):
                        if packet and digest:
                            outcome = _summarize(intent, digest, packet, outcomes)
                        elif error:
                            outcome = BranchOutcome(
                                number=intent.number,
                                child_id=intent.child_id,
                                error=error,
                                provider_error=provider_error,
                            )
                        else:
                            continue
                        with store.connection(write=True) as db:
                            try:
                                store._lease(db, session_id, owner, fence)
                            except StateError:
                                break
                            store._event(
                                db,
                                session_id,
                                "session_branch_closed",
                                outcome.model_dump(mode="json"),
                            )
                        outcomes.append(outcome)
                        store.checkpoint(session_id)
        finally:
            store.release(session_id, owner, fence)
            store.checkpoint(session_id)

    def _admit(
        self,
        session_id: str,
        profile: SessionProfile,
        intents: list[BranchIntent],
        outcomes: list[BranchOutcome],
        guard: Callable[[sqlite3.Connection, str], None],
    ) -> BranchIntent:
        number = len(intents)
        memory = [item.next_evidence for item in reversed(outcomes) if item.next_evidence][:3]
        context = SessionContext(
            session_id=session_id,
            branch=number,
            investigation=LANES[number % len(LANES)],
            recent_evidence=memory,
        )
        spec = profile.discovery.model_copy(update={"session_context": context})
        lab = self.factory(number)
        digest = fingerprint(canonical(lab._registration(spec)))
        intent = BranchIntent(number=number, child_id=f"discovery-{digest}", specification=spec)
        with self.store.connection(write=True) as db:
            guard(db, intent.child_id)
            self.store._event(
                db, session_id, "session_branch_admitted", intent.model_dump(mode="json")
            )
        return intent

    @staticmethod
    def _admission_stop(profile: SessionProfile, plan: dict, admitted: int) -> str | None:
        count = admitted + 1
        if count > profile.max_branches:
            return "BRANCH_LIMIT"
        if count * plan["attempts"] > profile.max_model_calls:
            return "MODEL_CALL_LIMIT"
        if count * plan["tokens"] > profile.max_total_tokens:
            return "TOKEN_LIMIT"
        cost = count * Decimal(plan["gross_usd"])
        if (
            profile.aggregate_cost_ceiling_usd is not None
            and cost > profile.aggregate_cost_ceiling_usd
        ):
            return "AGGREGATE_COST_LIMIT"
        return None

    def _stop_reason(
        self,
        profile: SessionProfile,
        plan: dict,
        admitted: int,
        open_branches: bool,
        unresolved: bool,
        expired: bool,
        pause: bool,
        stagnant: int,
        errors: int,
    ) -> tuple[str, str] | None:
        if unresolved:
            return "PAUSED", "REQUEST_RECONCILIATION_REQUIRED"
        if expired:
            return "COMPLETED", "SESSION_DEADLINE"
        if pause:
            return "PAUSED", "OPERATOR_PAUSE_OR_SIGNAL"
        if errors >= profile.max_consecutive_errors:
            return "COMPLETED", "CONSECUTIVE_PROVIDER_ERRORS"
        if stagnant >= profile.max_stagnant_branches:
            return "COMPLETED", "RESEARCH_STAGNATION"
        reason = self._admission_stop(profile, plan, admitted)
        return ("COMPLETED", reason) if reason and not open_branches else None

    def _finish(self, session_id: str, owner: str, fence: int, status: str, reason: str) -> None:
        with self.store.connection(write=True) as db:
            try:
                self.store._lease(db, session_id, owner, fence)
            except StateError:
                return  # A concurrent cancel already revoked authority.
            self.store._event(
                db,
                session_id,
                "session_stopped",
                {
                    "status": status,
                    "reason": reason,
                    "clock": self.store.clock(),
                },
            )
            db.execute(
                "UPDATE runs SET status=?,updated_at=? WHERE id=?", (status, now(), session_id)
            )


def session_report(store: Store, session_id: str, *, dossiers: bool = True) -> dict[str, Any]:
    chain = verify_chain(store)
    events = _read(store, session_id)
    row = store.get_run(session_id)
    intents, outcomes = _portfolio(events)
    totals, unresolved = _aggregate(store, intents)
    series, stagnant, errors = _progress(outcomes)
    with store.connection() as db:
        errors = max(errors, _provider_streak(db, session_id))
    started = next((p["started"] for k, p, _ in events if k == "session_started"), store.clock())
    terminal = next((p for k, p, _ in reversed(events) if k == "session_stopped"), {})
    status = row["status"]
    ended = store.clock()
    if status == "CANCELLED":
        ended = datetime.fromisoformat(row["updated_at"]).timestamp()
    elif status in {"COMPLETED", "PAUSED"}:
        ended = terminal.get("clock", ended)
    useful = sum(len(o.qualified_directions) for o in outcomes)
    result = {
        "session_id": session_id,
        "status": status,
        "objective": row["topic"],
        "pause_requested": status == "ACTIVE" and _paused(events),
        "worker_attached": coordinator_alive(row["owner"]) is True,
        "worker_lease_recorded": row["owner"] is not None,
        "elapsed_seconds": max(0.0, ended - started),
        "stop_reason": (
            "OPERATOR_CANCEL"
            if status == "CANCELLED"
            else terminal.get("reason")
            if status != "ACTIVE"
            else None
        ),
        "branches_admitted": len(intents),
        "branches_closed": len(outcomes),
        "pending_branches": [
            i.child_id for i in intents if i.number not in {o.number for o in outcomes}
        ],
        "consecutive_stagnant_branches": stagnant,
        "consecutive_provider_errors": errors,
        "directions_explored": sum(o.searched - o.duplicate_queries for o in outcomes),
        "distinct_source_records": len({s for o in outcomes for s in o.source_ids}),
        "distinct_substantive_publications": len({s for o in outcomes for s in o.publications}),
        "hypotheses_generated": sum(o.proposed for o in outcomes),
        "hypotheses_rejected": sum(o.rejected for o in outcomes),
        "hypotheses_revised": sum(o.revised for o in outcomes),
        "falsifiable_candidates_requiring_external_review": useful,
        "critiques_completed": sum(o.reviewed for o in outcomes),
        "prior_art_signals": sum(o.prior_art for o in outcomes),
        "duplicate_queries": sum(o.duplicate_queries for o in outcomes),
        "duplicate_hypotheses": sum(len(o.duplicate_directions) for o in outcomes),
        "source_failures": sum(o.source_failures for o in outcomes),
        "usage": totals,
        "unresolved_reservations": unresolved,
        "calculated_usd_per_provisional_candidate": (
            str(Decimal(totals["charged_usd"]) / useful) if useful else None
        ),
        "provider_confirmed_billing": None,
        "admission": registration(store, session_id)["admission"],
        "scientific_validation": "external_review_required",
        "commercial_level": 0,
        "evidence_anchor": chain,
    }
    if dossiers:
        packets = []
        for outcome in outcomes:
            if outcome.packet_digest:
                try:
                    digest, packet = replay(store, outcome.child_id)
                except IntegrityError:
                    # An invalidated child may still be audited through its original CAS digest.
                    packets.append({"child_id": outcome.child_id, "evidence": "integrity_failure"})
                    continue
                if digest != outcome.packet_digest:
                    raise IntegrityError("Session branch packet digest mismatch")
                packets.append({"digest": digest, "packet": packet.model_dump(mode="json")})
        result.update(
            progress=series,
            branches=[o.model_dump(mode="json") for o in outcomes],
            controls=[
                {"event": k, "record": p, "timestamp": t}
                for k, p, t in events
                if k
                in {
                    "session_started",
                    "session_pause_requested",
                    "session_resumed",
                    "session_stopped",
                    "control",
                }
            ],
            dossiers=packets,
            incomplete_dossiers=[
                {
                    "child_id": intent.child_id,
                    "branch": intent.number,
                    "checkpoint_digests": _journal(store, intent.child_id)[0],
                }
                for intent in intents
                if not any(
                    outcome.child_id == intent.child_id and outcome.packet_digest
                    for outcome in outcomes
                )
                and store.is_discovery(intent.child_id)
            ],
            next_research=[o.next_evidence for o in outcomes[-3:] if o.next_evidence],
        )
    return result
