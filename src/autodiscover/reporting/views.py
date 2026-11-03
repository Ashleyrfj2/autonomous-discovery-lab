"""Bounded typed operator reads from a single verified, query-only snapshot per response."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from autodiscover.commercial.service import CommercialError, Market
from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.evidence.chain import verify_chain
from autodiscover.hypotheses.director import Director, SearchPolicy
from autodiscover.orchestrator.contracts import AssessResult, RunStatus, Stage
from autodiscover.orchestrator.store import SnapshotStore
from autodiscover.reporting.reports import build_report
from autodiscover.security.budget import Budget


class View(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageRequest(View):
    limit: int = Field(default=25, ge=1, le=100, strict=True)
    offset: int = Field(default=0, ge=0, le=1000000, strict=True)
    at_cursor: int | None = Field(default=None, ge=0, strict=True)


DEFAULT_PAGE = PageRequest()


class Cursor(View):
    seq: int = Field(ge=0)
    hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class Page[Item](View):
    cursor: Cursor
    items: list[Item]
    next_offset: int | None


class UsageView(View):
    charged_usd: Decimal
    settled_usd: Decimal
    reserved_usd: Decimal
    uncertain_usd: Decimal
    requests: int
    uncertain: int
    input_tokens: int
    output_tokens: int


class RunSummary(View):
    run_id: str
    topic: str
    status: RunStatus
    stage: Stage
    version: int
    fence: int
    completed_steps: int
    technical_success: bool | None
    novelty: Literal["unknown", "supported", "not_new"]
    market_level: int | None = Field(ge=0, le=4)
    market_validated: bool | None
    usage: UsageView
    allowed_controls: list[Literal["pause", "resume", "cancel"]]


class RunDetail(View):
    cursor: Cursor
    summary: RunSummary
    assessment: AssessResult | None
    commercial: dict[str, JsonValue] | None
    limitations: list[str]
    policy: Limits


class JobView(View):
    id: str
    run_id: str
    stage_version: int
    replication: int
    plan_digest: str
    status: Literal["RUNNING", "COMPLETED", "ABANDONED", "FAILED"]
    owner: str | None
    fence: int
    lease_until: float | None
    attempts: int
    error_count: int
    worker_pid: int | None
    worker_created_at: float | None
    artifact_digest: str | None
    last_error: str | None


class EvidenceView(View):
    id: str
    kind: Literal["source", "claim"]
    valid: bool
    artifact_digest: str
    content: dict[str, JsonValue]


class StageView(View):
    stage: Stage
    output: dict[str, JsonValue]
    version: int


class HypothesisNode(View):
    id: str
    run_id: str
    identity: str
    parent_id: str | None
    depth: int
    domain: str
    kind: Literal["encoding", "allocation", "theoretical"]
    status: str
    revision_evidence: str | None
    score: float | None


class Allocation(View):
    run_id: str
    step_key: str
    hypothesis_id: str
    mode: str
    ordinal: int


class SearchView(View):
    nodes: list[HypothesisNode]
    allocations: list[Allocation]
    policy: SearchPolicy | None
    stopped_reason: str | None
    novelty: Literal["unknown"]
    commercial_validation: Literal["unvalidated"]


class TreeView(View):
    cursor: Cursor
    tree: SearchView


class QueueView(View):
    run_id: str
    status: str
    owner: str | None
    fence: int
    lease_until: float | None
    available_at: float
    attempts: int
    completed_steps: int
    last_error: str | None
    updated_at: str


class ReadConflict(ValueError):
    pass


class ReadService:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @contextmanager
    def snapshot(
        self, request: PageRequest | None = None
    ) -> Iterator[tuple[SnapshotStore, Cursor]]:
        with SnapshotStore(self.root) as store:
            checked = verify_chain(store)
            cursor = Cursor(seq=checked["seq"], hash=checked["hash"])
            if request and request.at_cursor is not None and request.at_cursor != cursor.seq:
                raise ReadConflict("Research changed; refresh before requesting another page")
            yield store, cursor

    @staticmethod
    def _page[Item](cursor: Cursor, items: list[Item], request: PageRequest) -> Page[Item]:
        return Page(
            cursor=cursor,
            items=items[: request.limit],
            next_offset=request.offset + request.limit if len(items) > request.limit else None,
        )

    @staticmethod
    def _summary(store: SnapshotStore, run_id: str) -> tuple[RunSummary, dict[str, Any]]:
        row = store.get_run(run_id)
        report = build_report(store, run_id)
        assessment, market = report["assessment"], report["commercial"]
        controls: dict[str, list[Literal["pause", "resume", "cancel"]]] = {
            "ACTIVE": ["pause", "cancel"],
            "PAUSED": ["resume", "cancel"],
        }
        summary = RunSummary(
            run_id=run_id,
            topic=row["topic"],
            status=row["status"],
            stage=row["stage"],
            version=row["version"],
            fence=row["fence"],
            completed_steps=report["completed_steps"],
            technical_success=assessment["technical_success"] if assessment else None,
            novelty=assessment["novelty"] if assessment else "unknown",
            market_level=market["level"] if market else None,
            market_validated=market["validated"] if market else None,
            usage=UsageView.model_validate(report["usage"]),
            allowed_controls=controls.get(row["status"], []),
        )
        return summary, report

    def runs(self, request: PageRequest = DEFAULT_PAGE) -> Page[RunSummary]:
        with self.snapshot(request) as (store, cursor), store.connection() as db:
            rows = db.execute(
                "SELECT id FROM runs ORDER BY created_at,id LIMIT ? OFFSET ?",
                (request.limit + 1, request.offset),
            ).fetchall()
            return self._page(cursor, [self._summary(store, row[0])[0] for row in rows], request)

    def detail(self, run_id: str) -> RunDetail:
        with self.snapshot() as (store, cursor):
            summary, report = self._summary(store, run_id)
            return RunDetail(
                cursor=cursor,
                summary=summary,
                assessment=report["assessment"],
                commercial=report["commercial"],
                policy=Limits.model_validate_json(store.get_run(run_id)["policy_json"]),
                limitations=[
                    "Trusted encoding workers only; novelty and demand are separate",
                    "Resource observations are sampled; software budgets are conservative",
                ],
            )

    def jobs(self, run_id: str, request: PageRequest = DEFAULT_PAGE) -> Page[JobView]:
        with self.snapshot(request) as (store, cursor), store.connection() as db:
            store.get_run(run_id)
            rows = db.execute(
                "SELECT * FROM experiment_jobs WHERE run_id=? ORDER BY rowid LIMIT ? OFFSET ?",
                (run_id, request.limit + 1, request.offset),
            ).fetchall()
            return self._page(cursor, [JobView.model_validate(dict(row)) for row in rows], request)

    def stages(self, run_id: str, request: PageRequest = DEFAULT_PAGE) -> Page[StageView]:
        with self.snapshot(request) as (store, cursor), store.connection() as db:
            store.get_run(run_id)
            rows = db.execute(
                "SELECT * FROM steps WHERE run_id=? ORDER BY rowid LIMIT ? OFFSET ?",
                (run_id, request.limit + 1, request.offset),
            ).fetchall()
            return self._page(
                cursor,
                [
                    StageView(
                        stage=r["stage"],
                        output=json.loads(r["output_json"]),
                        version=json.loads(r["result_json"])["version"],
                    )
                    for r in rows
                ],
                request,
            )

    def evidence(self, run_id: str, request: PageRequest = DEFAULT_PAGE) -> Page[EvidenceView]:
        with self.snapshot(request) as (store, cursor), store.connection() as db:
            store.get_run(run_id)
            # Direct sources and claims registered to this run; never expose another run's claims.
            rows = db.execute(
                "SELECT * FROM research_nodes WHERE id IN "
                "(SELECT source_id FROM run_sources WHERE run_id=? UNION "
                "SELECT json_extract(payload_json,'$.claim_id') FROM events "
                "WHERE run_id=? AND kind='claim_registered') ORDER BY id LIMIT ? OFFSET ?",
                (run_id, run_id, request.limit + 1, request.offset),
            ).fetchall()
            artifacts = Artifacts(store.root / "artifacts", read_only=True)
            return self._page(
                cursor,
                [
                    EvidenceView(
                        id=r["id"],
                        kind=r["kind"],
                        valid=bool(r["valid"]),
                        artifact_digest=r["artifact_digest"],
                        content=artifacts.get_json(r["artifact_digest"]),
                    )
                    for r in rows
                ],
                request,
            )

    def tree(self, run_id: str) -> TreeView:
        with self.snapshot() as (store, cursor):
            store.get_run(run_id)
            return TreeView(
                cursor=cursor, tree=SearchView.model_validate(Director(store).tree(run_id))
            )

    def queue(self, request: PageRequest = DEFAULT_PAGE) -> Page[QueueView]:
        with self.snapshot(request) as (store, cursor), store.connection() as db:
            rows = db.execute(
                "SELECT * FROM work_queue ORDER BY updated_at,run_id LIMIT ? OFFSET ?",
                (request.limit + 1, request.offset),
            ).fetchall()
            return self._page(cursor, [QueueView.model_validate(dict(r)) for r in rows], request)

    def usage(self, run_id: str) -> UsageView:
        with self.snapshot() as (store, _cursor):
            store.get_run(run_id)
            return UsageView.model_validate(Budget(store).totals(run_id))

    def report(self, run_id: str) -> dict[str, Any]:
        with self.snapshot() as (store, _cursor):
            return build_report(store, run_id)

    def market(self, opportunity_id: str, request: PageRequest = DEFAULT_PAGE) -> dict[str, Any]:
        with self.snapshot(request) as (store, cursor), store.connection() as db:
            market = Market(store)
            run_id, profile = market.opportunity(opportunity_id)
            rows = db.execute(
                "SELECT id FROM market_evidence WHERE opportunity_id=? "
                "ORDER BY id LIMIT ? OFFSET ?",
                (opportunity_id, request.limit + 1, request.offset),
            ).fetchall()
            contexts = []
            for row in rows[: request.limit]:
                _owner, evidence = market.evidence(row[0])
                source_digest = None
                try:
                    source_digest, _url = market._external_source(evidence)
                except (CommercialError, IntegrityError):
                    pass
                contexts.append(
                    {
                        "evidence_id": row[0],
                        "evidence": evidence.model_dump(mode="json"),
                        "source_digest": source_digest,
                        "confirmation_text": f"REVIEW {row[0]} {source_digest}"
                        if source_digest
                        else None,
                    }
                )
            return {
                "cursor": cursor.model_dump(),
                "run_id": run_id,
                "opportunity": profile.model_dump(mode="json"),
                "assessment": market.assess(opportunity_id),
                "items": contexts,
                "next_offset": request.offset + request.limit
                if len(rows) > request.limit
                else None,
            }
