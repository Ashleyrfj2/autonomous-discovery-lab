"""Durable source metadata, quote-backed claims, knowledge retrieval and transitive invalidation."""

import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store
from autodiscover.research.retrieval import Fetched


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=2000)
    url: str = Field(min_length=1, max_length=3000)
    retrieved_at: str
    published_on: str | None = None
    doi: str | None = None
    source_kind: Literal["publication_metadata", "primary_document"]
    raw_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    text_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_type: str
    retrieval_url: str
    limitations: str


class Catalog:
    def __init__(self, store: Store):
        self.store = store
        self.artifacts = Artifacts(store.root / "artifacts")
        # The URL index is derived and rebuilt for sources registered before migration 4.
        with store.connection() as db:
            missing = db.execute(
                "SELECT id,artifact_digest FROM research_nodes WHERE kind='source' "
                "AND id NOT IN (SELECT source_id FROM source_locations)"
            ).fetchall()
        for row in missing:
            if row["id"] != "source-" + row["artifact_digest"]:
                raise IntegrityError("Source index identity mismatch")
            record = Source.model_validate(self.artifacts.get_json(row["artifact_digest"]))
            with store.connection(write=True) as db:
                db.execute(
                    "INSERT OR IGNORE INTO source_locations VALUES(?,?,?,?)",
                    (record.url, row["id"], record.raw_digest, record.retrieved_at),
                )

    def add(
        self,
        run_id: str,
        fetched: Fetched,
        *,
        title: str,
        text: str,
        source_kind: Literal["publication_metadata", "primary_document"],
        url: str | None = None,
        published_on: str | None = None,
        doi: str | None = None,
    ) -> str:
        raw = self.artifacts.put(fetched.body)
        extracted = self.artifacts.put(text.encode())
        source = Source(
            title=title,
            url=url or fetched.final_url,
            retrieved_at=fetched.retrieved_at,
            published_on=published_on,
            doi=doi,
            source_kind=source_kind,
            raw_digest=raw,
            text_digest=extracted,
            content_type=fetched.content_type,
            retrieval_url=fetched.final_url,
            limitations=(
                "Untrusted source content; metadata/quoted statements are not independent proof"
            ),
        )
        digest = self.artifacts.put_json(source.model_dump(mode="json"))
        identifier = "source-" + digest
        with self.store.connection(write=True) as db:
            prior = db.execute(
                "SELECT l.source_id FROM source_locations l JOIN research_nodes n "
                "ON n.id=l.source_id WHERE l.url=? AND l.raw_digest<>? AND n.valid=1",
                (source.url, raw),
            ).fetchall()
            affected: set[str] = set()
            for previous in prior:
                affected.update(
                    r[0]
                    for r in db.execute(
                        """WITH RECURSIVE affected(id) AS (
                  SELECT ? UNION SELECT e.child FROM research_edges e
                  JOIN affected a ON e.parent=a.id) SELECT id FROM affected""",
                        (previous[0],),
                    )
                )
            if affected:
                db.executemany(
                    "UPDATE research_nodes SET valid=0 WHERE id=?", [(i,) for i in affected]
                )
                self.store._event(
                    db,
                    run_id,
                    "source_updated",
                    {"url": source.url, "affected": sorted(affected), "new_source": identifier},
                )
            existing = db.execute(
                "SELECT valid FROM research_nodes WHERE id=?", (identifier,)
            ).fetchone()
            if existing is not None and not existing[0]:
                raise IntegrityError("Previously invalidated evidence cannot be silently restored")
            if (
                db.execute("SELECT 1 FROM research_nodes WHERE id=?", (identifier,)).fetchone()
                is None
            ):
                db.execute(
                    "INSERT INTO research_nodes(id,kind,artifact_digest,valid,summary) "
                    "VALUES(?,'source',?,1,?)",
                    (identifier, digest, title),
                )
            db.execute(
                "INSERT OR IGNORE INTO source_locations VALUES(?,?,?,?)",
                (source.url, identifier, raw, source.retrieved_at),
            )
            db.execute("INSERT OR IGNORE INTO run_sources VALUES(?,?)", (run_id, identifier))
            self.store._event(
                db,
                run_id,
                "source_registered",
                {
                    "source_id": identifier,
                    "metadata_digest": digest,
                    "raw_digest": raw,
                    "text_digest": extracted,
                },
            )
        return identifier

    def source(self, identifier: str) -> tuple[Source, str]:
        with self.store.connection() as db:
            row = db.execute(
                "SELECT * FROM research_nodes WHERE id=? AND kind='source'", (identifier,)
            ).fetchone()
        if row is None or not row["valid"] or identifier != "source-" + row["artifact_digest"]:
            raise IntegrityError("Source invalid or missing")
        source = Source.model_validate(self.artifacts.get_json(row["artifact_digest"]))
        self.artifacts.get(source.raw_digest)
        return source, self.artifacts.get(source.text_digest).decode()

    def sources(self, run_id: str) -> list[str]:
        with self.store.connection() as db:
            return [
                r[0]
                for r in db.execute(
                    "SELECT source_id FROM run_sources WHERE run_id=? ORDER BY source_id", (run_id,)
                )
            ]

    def claim(
        self,
        run_id: str,
        statement: str,
        *,
        supports: list[str],
        quotes: dict[str, str] | None = None,
        kind: Literal["source_statement", "interpretation"] = "source_statement",
    ) -> str:
        if not statement.strip() or len(statement) > 4000 or not supports:
            raise ValueError("Bounded statement and supporting evidence required")
        quotes = quotes or {}
        for support in supports:
            with self.store.connection() as db:
                node = db.execute(
                    "SELECT kind,valid FROM research_nodes WHERE id=?", (support,)
                ).fetchone()
            if node is None or not node["valid"]:
                raise IntegrityError("Claim support invalid or missing")
            if kind == "source_statement" and node["kind"] != "source":
                raise IntegrityError("Extractive statements require original sources")
            if node["kind"] == "source" and kind == "source_statement":
                _, text = self.source(support)
                quote = quotes.get(support, "")
                if (
                    not quote
                    or len(quote) > 1000
                    or quote not in text
                    or statement.strip() != quote.strip()
                ):
                    raise IntegrityError("Claim quote absent from actual source")
        record = {
            "schema_version": 1,
            "run_id": run_id,
            "claim_id": str(uuid4()),
            "statement": statement,
            "supports": supports,
            "quotes": quotes,
            "kind": kind,
            "verification": "source attribution only"
            if kind == "source_statement"
            else "interpretation, not independently verified",
        }
        digest = self.artifacts.put_json(record)
        identifier = "claim-" + digest
        with self.store.connection(write=True) as db:
            # Recheck inside the write transaction to prevent racing invalidation.
            for support in supports:
                if not db.execute(
                    "SELECT valid FROM research_nodes WHERE id=?", (support,)
                ).fetchone()[0]:
                    raise IntegrityError("Claim support invalidated concurrently")
            db.execute(
                "INSERT INTO research_nodes VALUES(?,'claim',?,1,?)",
                (identifier, digest, statement),
            )
            for support in supports:
                db.execute("INSERT INTO research_edges VALUES(?,?)", (support, identifier))
            self.store._event(
                db,
                run_id,
                "claim_registered",
                {
                    "claim_id": identifier,
                    "artifact_digest": digest,
                    "supports": supports,
                    "kind": kind,
                },
            )
        return identifier

    def invalidate(self, run_id: str, identifier: str, *, reason: str) -> list[str]:
        if not reason.strip() or len(reason) > 500:
            raise ValueError("Bounded invalidation reason required")
        with self.store.connection(write=True) as db:
            if (
                db.execute("SELECT 1 FROM research_nodes WHERE id=?", (identifier,)).fetchone()
                is None
            ):
                raise IntegrityError("Unknown evidence node")
            affected = [
                r[0]
                for r in db.execute(
                    """WITH RECURSIVE affected(id) AS (
                SELECT ? UNION SELECT e.child FROM research_edges e
                JOIN affected a ON e.parent=a.id)
                SELECT id FROM affected""",
                    (identifier,),
                )
            ]
            db.executemany("UPDATE research_nodes SET valid=0 WHERE id=?", [(i,) for i in affected])
            self.store._event(
                db,
                run_id,
                "evidence_invalidated",
                {"root": identifier, "affected": affected, "reason": reason},
            )
        return affected

    def search(self, query: str, *, include_invalid: bool = False) -> list[dict[str, Any]]:
        if not query.strip() or len(query) > 200:
            raise ValueError("Bounded search term required")
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT * FROM research_nodes WHERE instr(lower(summary),lower(?))>0 "
                "AND (valid=1 OR ?) ORDER BY id LIMIT 50",
                (query, include_invalid),
            ).fetchall()
        return [dict(r) for r in rows]

    def node(self, identifier: str) -> dict[str, Any]:
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM research_nodes WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise IntegrityError("Evidence node missing")
        record = dict(row)
        record["content"] = json.loads(self.artifacts.get(row["artifact_digest"]))
        return record

    def context(self, run_id: str, *, max_characters: int = 10000) -> str:
        items = []
        for identifier in self.sources(run_id)[:5]:
            source, text = self.source(identifier)
            items.append(
                {
                    "source_id": identifier,
                    "title": source.title,
                    "doi": source.doi,
                    "untrusted_excerpt": text[:1200],
                    "kind": source.source_kind,
                }
            )
        return canonical(
            {
                "untrusted_sources": items,
                "novelty": "unknown",
                "limitations": "Bounded retrieval; absence is not proof of novelty",
            }
        )[:max_characters]
