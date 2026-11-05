"""Bounded bibliography search and registered public document capture."""

import json
import re
from dataclasses import replace
from html.parser import HTMLParser
from typing import Any, Literal
from urllib.parse import quote, urlencode, urlsplit

from autodiscover.orchestrator.durability import canonical
from autodiscover.research.catalog import Catalog
from autodiscover.research.discovery_contracts import Evidence, SearchReceipt, SourceSeed
from autodiscover.research.retrieval import Fetched, RetrievalError, SourceFetcher, crossref_search
from autodiscover.security.cancellation import cancellation_requested
from autodiscover.security.redaction import contains_credential, sanitize

EUROPE_PMC_HOST = "www.ebi.ac.uk"
_DOI = re.compile(r"10\.\d{4,9}/[^\s]{1,200}")


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _extract(value: str, *, markup: bool) -> str:
    if markup:
        parser = _VisibleText()
        parser.feed(value)
        value = " ".join(parser.parts)
    return " ".join(value.split())


def seed_host(seed: SourceSeed) -> str:
    parts = urlsplit(seed.url)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.port not in (None, 443)
        or parts.fragment
        or parts.query
        or contains_credential(canonical(seed.model_dump(mode="json")))
    ):
        raise ValueError("Seed must be a credential-free public HTTPS URL without query parameters")
    return parts.hostname


def _date(item: dict[str, Any]) -> str | None:
    try:
        parts = item["published"]["date-parts"][0]
        if 1 <= len(parts) <= 3 and all(type(p) is int for p in parts):
            return "-".join(
                f"{part:04d}" if i == 0 else f"{part:02d}" for i, part in enumerate(parts)
            )
    except (KeyError, IndexError, TypeError):
        pass
    return None


def _excerpt(text: str, query: str) -> str:
    if len(text) <= 850:
        return text
    terms = {word.lower() for word in re.findall(r"[A-Za-z0-9]{4,}", query)}
    offsets = range(0, min(len(text) - 850, 80_000) + 1, 425)
    offset = max(offsets, key=lambda i: sum(term in text[i : i + 850].lower() for term in terms))
    return text[offset : offset + 850]


# Conservative lexical triage for billable capability sessions. This is NOT a
# semantic relevance proof. Non-matches remain discoverable via new queries.
_RELEVANCE_STOPWORDS = {
    "about", "across", "against", "analysis", "application", "applications",
    "approach", "approaches", "based", "comparative", "comparison",
    "effects", "evidence", "evaluation", "existing", "framework",
    "impact", "investigation", "methods", "models", "outcomes",
    "research", "review", "studies", "study", "system", "systems",
    "technology", "using", "verified", "with",
}


def _query_relevant(title: str, abstract: str, query: str) -> bool:
    """Conservatively filter obvious off-topic bibliography hits.

    Prefer precision to admitting papers with only an incidental shared word.
    A single matching term in an abstract is insufficient. A title-only hit
    needs two distinct query anchors; it can never establish an empirical fact.
    """
    def anchors(value: str) -> set[str]:
        return {
            word[:5] if len(word) >= 6 else word
            for word in re.findall(r"[a-z]{4,}", value.casefold())
            if word not in _RELEVANCE_STOPWORDS
        }

    query_terms = anchors(query)
    if len(query_terms) < 2:
        return True  # Insufficient anchors: do not accidentally suppress everything.
    title_hits = len(query_terms & anchors(title))
    combined_hits = len(query_terms & anchors(title + " " + abstract))
    if not abstract.strip():
        return title_hits >= 2
    return title_hits >= 2 or (title_hits >= 1 and combined_hits >= 2)


def _europe_pmc(fetcher: SourceFetcher, query: str) -> tuple[Fetched, list[dict[str, Any]]]:
    if not query.strip() or sanitize(query) != query or len(query) > 220:
        raise RetrievalError("UNSAFE_EUROPE_PMC_QUERY")
    url = f"https://{EUROPE_PMC_HOST}/europepmc/webservices/rest/search?" + urlencode(
        {
            "query": query,
            "resultType": "core",
            "pageSize": 3,
            "format": "json",
        }
    )
    response = fetcher.fetch(url)
    try:
        results = json.loads(response.body)["resultList"]["result"]
        if not isinstance(results, list) or len(results) > 3:
            raise ValueError("Unexpected result count")
        return response, [item for item in results if isinstance(item, dict)]
    except (ValueError, KeyError, TypeError):
        raise RetrievalError("INVALID_EUROPE_PMC_METADATA") from None


def acquire(
    catalog: Catalog,
    run_id: str,
    fetcher: SourceFetcher,
    question: str,
    query: str,
    seeds: list[SourceSeed],
    *,
    require_live: bool,
    lease: tuple[str, int] | None = None,
    relevance_gate: bool = False,
) -> SearchReceipt:
    evidence: dict[str, Evidence] = {}
    failures: list[str] = []
    existing = {}
    for source_id in catalog.sources(run_id):
        source, text = catalog.source(source_id)
        title_only = source.source_kind == "publication_metadata" and text == source.title
        if not title_only or source.url not in existing:
            existing[source.url] = source_id, title_only

    def add(
        fetched: Fetched,
        url: str,
        title: str,
        publisher: str | None,
        date: str | None,
        text: str,
        category: str,
        limitation: str,
        scope: Literal["title", "abstract", "document"],
        doi: str | None = None,
    ) -> None:
        if (
            cancellation_requested()
            or (require_live and fetched.provenance != "live_https")
            or contains_credential(canonical([title, publisher, date, text, url]))
            or contains_credential(fetched.body.decode("utf-8", errors="replace"))
            or len(text) < 15
        ):
            failures.append("SOURCE_NOT_ELIGIBLE")
            return
        if url in evidence and (scope != "abstract" or evidence[url].scope != "title"):
            return
        archived = existing.get(url)
        if archived and not (archived[1] and scope == "abstract"):
            source_id = archived[0]
            previous, previous_text = catalog.source(source_id)
            if previous.source_kind == "publication_metadata":
                scope = "title" if previous_text == previous.title else "abstract"
                limitation = f"Reused the archived {scope}. Full text was unavailable."
            else:
                scope = "document"
                limitation = "Reused a registered public document excerpt."
            publisher = None if previous.raw_digest != fetched.digest else publisher
        else:
            source_id = catalog.add(
                run_id,
                fetched,
                title=title,
                text=text,
                source_kind="primary_document" if scope == "document" else "publication_metadata",
                url=url,
                published_on=date,
                doi=doi,
                supersede=scope == "document",
                lease=lease,
            )
        source, archived_text = catalog.source(source_id)
        existing[url] = source_id, scope == "title"
        if require_live and source.retrieval_provenance != "live_https":
            failures.append("SOURCE_NOT_ELIGIBLE")
            return
        evidence[url] = Evidence(
            source_id=source_id,
            title=source.title,
            url=url,
            publisher=publisher,
            published_on=source.published_on,
            retrieved_at=source.retrieved_at,
            excerpt=_excerpt(archived_text, query) if scope == "document" else archived_text[:850],
            category=category,
            provenance=source.retrieval_provenance,
            limitation=limitation,
            scope=scope,
        )

    if not cancellation_requested():
        try:
            response, items = crossref_search(fetcher, query)
        except RetrievalError as error:
            failures.append(str(error))
        else:
            for item in items:
                if not isinstance(item, dict):
                    failures.append("INVALID_BIBLIOGRAPHIC_ITEM")
                    continue
                doi = item.get("DOI")
                titles = item.get("title")
                if (
                    not isinstance(doi, str)
                    or not _DOI.fullmatch(doi)
                    or not isinstance(titles, list)
                    or not titles
                    or not isinstance(titles[0], str)
                    or not titles[0].strip()
                ):
                    failures.append("INVALID_BIBLIOGRAPHIC_ITEM")
                    continue
                doi = doi.lower()
                url = "https://doi.org/" + quote(doi, safe="/")
                title = _extract(titles[0][:2000], markup=True)
                abstract = item.get("abstract")
                abstract = (
                    _extract(abstract[:16000], markup=True) if isinstance(abstract, str) else ""
                )
                publisher = item.get("publisher")
                if not title:
                    failures.append("INVALID_BIBLIOGRAPHIC_ITEM")
                    continue
                if relevance_gate and not _query_relevant(title, abstract, query):
                    if "BIBLIOGRAPHIC_LOW_RELEVANCE" not in failures:
                        failures.append("BIBLIOGRAPHIC_LOW_RELEVANCE")
                    continue
                # Archive an individual record to avoid changing the DOI snapshot
                # when the same publication is returned by another search.
                captured = replace(
                    response,
                    body=canonical(
                        {
                            key: item[key]
                            for key in (
                                "DOI",
                                "title",
                                "abstract",
                                "publisher",
                                "published",
                                "author",
                                "type",
                            )
                            if key in item
                        }
                    ).encode(),
                )
                add(
                    captured,
                    url,
                    title,
                    publisher[:500] if isinstance(publisher, str) else None,
                    _date(item),
                    title + (f". {abstract}" if abstract else ""),
                    "publication",
                    "Crossref abstract excerpt. Full text was unavailable."
                    if abstract
                    else "Title metadata only. Findings and full text were unavailable.",
                    "abstract" if abstract else "title",
                    doi,
                )

    for seed in seeds:
        if cancellation_requested():
            break
        try:
            fetched = fetcher.fetch(seed.url)
            mime = fetched.content_type.split(";", 1)[0].strip().lower()
            if mime not in {"text/plain", "text/html", "application/json", "text/csv"}:
                failures.append("UNSUPPORTED_SOURCE_FORMAT")
                continue
            text = _extract(fetched.body.decode("utf-8"), markup=mime == "text/html")
        except RetrievalError as error:
            failures.append(str(error))
            continue
        except UnicodeError:
            failures.append("UNSUPPORTED_SOURCE_ENCODING")
            continue
        add(
            fetched,
            fetched.final_url,
            seed.title,
            seed.publisher,
            seed.published_on,
            text,
            seed.category,
            "Excerpt from a registered public document. Scope and claims "
            "require independent assessment.",
            "document",
        )

    if (
        not any(item.scope != "title" for item in evidence.values())
        and not cancellation_requested()
    ):
        try:
            response, items = _europe_pmc(fetcher, query)
        except RetrievalError as error:
            failures.append(str(error))
        else:
            for item in items:
                title, abstract = item.get("title"), item.get("abstractText")
                if not isinstance(title, str) or not isinstance(abstract, str):
                    continue
                title = _extract(title[:2000], markup=True)
                abstract = _extract(abstract[:16000], markup=True)
                if relevance_gate and not _query_relevant(title, abstract, query):
                    if "BIBLIOGRAPHIC_LOW_RELEVANCE" not in failures:
                        failures.append("BIBLIOGRAPHIC_LOW_RELEVANCE")
                    continue
                origin, identifier, doi = item.get("source"), item.get("id"), item.get("doi")
                if not title or not abstract:
                    continue
                doi = doi.lower() if isinstance(doi, str) and _DOI.fullmatch(doi) else None
                if doi:
                    url = "https://doi.org/" + quote(doi, safe="/")
                elif (
                    isinstance(origin, str)
                    and re.fullmatch(r"[A-Z]{2,6}", origin)
                    and isinstance(identifier, str)
                    and re.fullmatch(r"[A-Za-z0-9.-]{1,40}", identifier)
                ):
                    url = f"https://europepmc.org/article/{origin}/{identifier}"
                else:
                    continue
                date, journal = item.get("firstPublicationDate"), item.get("journalTitle")
                captured = replace(
                    response,
                    body=canonical(
                        {
                            "title": title,
                            "abstractText": abstract,
                            "id": identifier,
                            "source": origin,
                            "doi": doi,
                            "firstPublicationDate": date,
                            "journalTitle": journal,
                            "authorString": item.get("authorString"),
                        }
                    ).encode(),
                )
                add(
                    captured,
                    url,
                    title,
                    journal[:500] if isinstance(journal, str) else None,
                    date[:30] if isinstance(date, str) else None,
                    f"{title}. {abstract}",
                    "publication",
                    "Europe PMC abstract excerpt. Full text was unavailable.",
                    "abstract",
                    doi,
                )

    # Identical public text syndicated at different URLs counts as one result.
    unique = {item.excerpt: item for item in reversed(tuple(evidence.values()))}
    return SearchReceipt(
        question=question, query=query, evidence=list(unique.values()), failures=failures
    )
