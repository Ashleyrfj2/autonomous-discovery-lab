"""Retrieval adapters and provenance-preserving synthesis, comparisons and conflict candidates."""

import re
from typing import Any

from autodiscover.research.catalog import Catalog
from autodiscover.research.retrieval import RetrievalError, SourceFetcher, crossref_search


def retrieve_publications(
    catalog: Catalog, run_id: str, fetcher: SourceFetcher, query: str, *, count: int = 3
) -> list[str]:
    fetched, items = crossref_search(fetcher, query, count=count)
    ids = []
    for item in items:
        titles, doi = item.get("title", []), item.get("DOI")
        if not titles or not isinstance(titles[0], str) or not isinstance(doi, str):
            continue
        dates = item.get("published", {}).get("date-parts", [])
        published = (
            "-".join(str(n) for n in dates[0]) if dates and isinstance(dates[0], list) else None
        )
        title = titles[0][:2000]
        text = f"Title: {title}\nDOI: {doi}\nPublished: {published or 'unknown'}"
        ids.append(
            catalog.add(
                run_id,
                fetched,
                title=title,
                text=text,
                source_kind="publication_metadata",
                url="https://doi.org/" + doi,
                published_on=published,
                doi=doi,
            )
        )
    if not ids:
        raise RetrievalError("NO_VALID_PUBLICATION_METADATA")
    return ids


def synthesize(catalog: Catalog, source_ids: list[str], question: str) -> dict[str, Any]:
    source_evidence = []
    for identifier in source_ids:
        source, text = catalog.source(identifier)
        source_evidence.append(
            {
                "source_id": identifier,
                "title": source.title,
                "url": source.url,
                "kind": source.source_kind,
                "excerpt": text[:500],
            }
        )
    return {
        "question": question,
        "source_evidence": source_evidence,
        "interpretation": "These retrieved records are prior-art candidates requiring substantive "
        "method comparison; titles and metadata alone cannot prove findings.",
        "novelty": "unknown",
        "coverage": {"sources": len(source_ids), "exhaustive": False},
        "limitations": "Sources are untrusted, possibly incomplete or contradictory. "
        "No inference of novelty from missing matches.",
    }


def compare_methods(
    catalog: Catalog, sources: list[str], methods: list[str]
) -> list[dict[str, Any]]:
    comparisons = []
    for identifier in sources:
        source, text = catalog.source(identifier)
        for method in methods:
            position = text.casefold().find(method.casefold())
            if position >= 0:
                comparisons.append(
                    {
                        "source_id": identifier,
                        "method": method,
                        "quote": text[max(0, position - 60) : position + len(method) + 120],
                        "status": "text mention; performance comparison not established",
                        "source_kind": source.source_kind,
                    }
                )
    return comparisons


def contradiction_candidates(catalog: Catalog, source_ids: list[str]) -> list[dict[str, Any]]:
    # Conservative sentence pattern; candidates are not proven contradictions.
    observations: dict[str, list[dict[str, str]]] = {}
    pattern = re.compile(
        r"([A-Za-z][A-Za-z ]{2,60})\s+(increases|decreases)\s+"
        r"([A-Za-z][A-Za-z ]{2,60})[.!]",
        re.I,
    )
    for identifier in source_ids:
        _, text = catalog.source(identifier)
        for match in pattern.finditer(text):
            key = match[1].strip().casefold() + ":" + match[3].strip().casefold()
            observations.setdefault(key, []).append(
                {"source_id": identifier, "direction": match[2].casefold(), "quote": match[0]}
            )
    candidates = []
    for key, rows in observations.items():
        if len({r["direction"] for r in rows}) > 1 and len({r["source_id"] for r in rows}) > 1:
            candidates.append(
                {
                    "subject_metric": key,
                    "observations": rows,
                    "status": "possible conflict; check study conditions and populations",
                }
            )
    return candidates


def questions(topic: str, domains: list[str]) -> list[dict[str, str]]:
    return [
        {
            "domain": domain,
            "question": f"Which measurable limitation in {topic} affects {domain}, "
            "and can a method from another field improve it against a baseline?",
        }
        for domain in domains[:5]
    ]
