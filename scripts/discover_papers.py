#!/usr/bin/env python3
"""Discover possible new Web Agent Security papers for human review.

This script writes candidate files only. It never edits data/papers.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "discovery_config.json"
PAPERS_PATH = ROOT / "data" / "papers.json"
CANDIDATES_DIR = ROOT / "data" / "candidates"

ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"
DBLP_API = "https://dblp.org/search/publ/api"
OPENALEX_API = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
USER_AGENT = "awesome-web-agent-security-discovery/0.1 (mailto:please-configure@example.com)"


@dataclass
class RawPaper:
    source: str
    title: str
    year: int | None
    venue: str
    url: str
    abstract: str
    authors: list[str]
    published: str
    doi: str = ""
    arxiv_id: str = ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_title(title: str) -> str:
    text = title.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def slugify(title: str, year: int | None) -> str:
    words = normalize_title(title).split()[:8]
    suffix = str(year) if year else "unknown"
    return "-".join(words + [suffix])


def request_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def arxiv_query_string(query: str, categories: list[str]) -> str:
    category_expr = " OR ".join(f"cat:{category}" for category in categories)
    phrase_query = query.replace('"', "")
    terms = [term.strip() for term in re.split(r"\s+AND\s+", phrase_query, flags=re.I)]
    all_terms = " AND ".join(f'all:"{term}"' for term in terms if term)
    if all_terms:
        return f"({all_terms}) AND ({category_expr})"
    return category_expr


def fetch_arxiv(query: str, config: dict[str, Any], since: datetime) -> list[RawPaper]:
    params = {
        "search_query": arxiv_query_string(query, config["arxiv_categories"]),
        "start": "0",
        "max_results": str(config["max_results_per_query"]),
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    xml_text = request_text(url)
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    papers: list[RawPaper] = []

    for entry in root.findall("atom:entry", ns):
        title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = clean_text(entry.findtext("atom:summary", default="", namespaces=ns))
        published = entry.findtext("atom:published", default="", namespaces=ns)
        updated = entry.findtext("atom:updated", default="", namespaces=ns)
        when = parse_datetime(updated or published)
        if when and when < since:
            continue

        entry_id = entry.findtext("atom:id", default="", namespaces=ns)
        arxiv_id = entry_id.rstrip("/").split("/")[-1]
        authors = [
            clean_text(author.findtext("atom:name", default="", namespaces=ns))
            for author in entry.findall("atom:author", ns)
        ]
        year = when.year if when else None
        doi = entry.findtext("arxiv:doi", default="", namespaces=ns)
        papers.append(
            RawPaper(
                source="arxiv",
                title=title,
                year=year,
                venue="arXiv",
                url=entry_id,
                abstract=abstract,
                authors=[author for author in authors if author],
                published=published[:10],
                doi=doi,
                arxiv_id=arxiv_id,
            )
        )
    return papers


def fetch_crossref(query: str, config: dict[str, Any], since: datetime) -> list[RawPaper]:
    params = {
        "query.bibliographic": query,
        "rows": str(config["max_results_per_query"]),
        "sort": "published",
        "order": "desc",
        "filter": f"from-pub-date:{since.date().isoformat()}",
    }
    url = f"{CROSSREF_API}?{urllib.parse.urlencode(params)}"
    data = request_json(url)
    papers: list[RawPaper] = []

    for item in data.get("message", {}).get("items", []):
        titles = item.get("title") or []
        if not titles:
            continue
        title = clean_text(titles[0])
        container = item.get("container-title") or []
        venue = clean_text(container[0]) if container else "Unknown"
        date_parts = (
            item.get("published-print", {}).get("date-parts")
            or item.get("published-online", {}).get("date-parts")
            or item.get("published", {}).get("date-parts")
            or []
        )
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        authors = []
        for author in item.get("author", []):
            name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
            if name:
                authors.append(name)
        abstract = clean_text(strip_html(item.get("abstract", "")))
        papers.append(
            RawPaper(
                source="crossref",
                title=title,
                year=year,
                venue=canonical_venue(venue, config),
                url=item.get("URL", ""),
                abstract=abstract,
                authors=authors,
                published=str(year or ""),
                doi=item.get("DOI", ""),
            )
        )
    return papers


def fetch_dblp(query: str, config: dict[str, Any], since: datetime) -> list[RawPaper]:
    params = {
        "q": query.replace('"', ""),
        "format": "json",
        "h": str(config["max_results_per_query"]),
        "f": "0",
    }
    url = f"{DBLP_API}?{urllib.parse.urlencode(params)}"
    data = request_json(url)
    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    papers: list[RawPaper] = []

    for hit in hits:
        info = hit.get("info", {})
        title = clean_text(strip_html(info.get("title", "")))
        if not title:
            continue
        year = parse_year(info.get("year"))
        if year and year < since.year:
            continue
        venue = canonical_venue(clean_text(info.get("venue", "")), config)
        authors = parse_dblp_authors(info.get("authors", {}))
        papers.append(
            RawPaper(
                source="dblp",
                title=title,
                year=year,
                venue=venue,
                url=info.get("ee") or info.get("url", ""),
                abstract="",
                authors=authors,
                published=str(year or ""),
                doi=extract_doi(info.get("ee", "")),
            )
        )
    return papers


def fetch_openalex(query: str, config: dict[str, Any], since: datetime) -> list[RawPaper]:
    clean_query = query.replace('"', "")
    filters = [
        f"from_publication_date:{since.date().isoformat()}",
        f"title_and_abstract.search:{clean_query}",
    ]
    params = {
        "filter": ",".join(filters),
        "per-page": str(config["max_results_per_query"]),
        "sort": "publication_date:desc",
    }
    openalex_mailto = os.environ.get("OPENALEX_MAILTO") or config.get("openalex_mailto")
    if openalex_mailto:
        params["mailto"] = openalex_mailto
    url = f"{OPENALEX_API}?{urllib.parse.urlencode(params)}"
    data = request_json(url)
    papers: list[RawPaper] = []

    for item in data.get("results", []):
        title = clean_text(item.get("display_name", ""))
        if not title:
            continue
        year = parse_year(item.get("publication_year"))
        venue = openalex_venue(item, config)
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in item.get("authorships", [])
        ]
        papers.append(
            RawPaper(
                source="openalex",
                title=title,
                year=year,
                venue=venue,
                url=item.get("doi") or item.get("id", ""),
                abstract=openalex_abstract(item.get("abstract_inverted_index")),
                authors=[author for author in authors if author],
                published=item.get("publication_date") or str(year or ""),
                doi=normalize_doi(item.get("doi", "")),
            )
        )
    return papers


def fetch_semantic_scholar(query: str, config: dict[str, Any], since: datetime) -> list[RawPaper]:
    current_year = datetime.now(timezone.utc).year
    year_range = f"{since.year}-{current_year + 1}"
    fields = "title,year,venue,url,abstract,authors,externalIds,publicationDate"
    params = {
        "query": query.replace('"', ""),
        "limit": str(min(int(config["max_results_per_query"]), 100)),
        "year": year_range,
        "fields": fields,
    }
    url = f"{SEMANTIC_SCHOLAR_API}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}
    semantic_scholar_api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or config.get("semantic_scholar_api_key")
    if semantic_scholar_api_key:
        headers["x-api-key"] = semantic_scholar_api_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    papers: list[RawPaper] = []
    for item in data.get("data", []):
        title = clean_text(item.get("title", ""))
        if not title:
            continue
        year = parse_year(item.get("year"))
        authors = [author.get("name", "") for author in item.get("authors", [])]
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI", "")
        arxiv_id = external_ids.get("ArXiv", "")
        papers.append(
            RawPaper(
                source="semantic_scholar",
                title=title,
                year=year,
                venue=canonical_venue(clean_text(item.get("venue", "")), config),
                url=item.get("url", ""),
                abstract=clean_text(item.get("abstract", "")),
                authors=[author for author in authors if author],
                published=item.get("publicationDate") or str(year or ""),
                doi=doi,
                arxiv_id=arxiv_id,
            )
        )
    return papers


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_year(value: Any) -> int | None:
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    if 1900 <= year <= 2100:
        return year
    return None


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "")


def extract_doi(value: str) -> str:
    match = re.search(r"10\.\d{4,9}/\S+", value or "", flags=re.I)
    return normalize_doi(match.group(0)) if match else ""


def normalize_doi(value: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", value or "", flags=re.I).strip()


def parse_dblp_authors(authors: Any) -> list[str]:
    if not authors:
        return []
    author_items = authors.get("author", []) if isinstance(authors, dict) else authors
    if isinstance(author_items, str):
        return [author_items]
    if isinstance(author_items, dict):
        return [clean_text(author_items.get("text", ""))]
    parsed = []
    for author in author_items:
        if isinstance(author, dict):
            parsed.append(clean_text(author.get("text", "")))
        elif isinstance(author, str):
            parsed.append(clean_text(author))
    return [author for author in parsed if author]


def openalex_venue(item: dict[str, Any], config: dict[str, Any]) -> str:
    location = item.get("primary_location") or {}
    source = location.get("source") or {}
    display_name = source.get("display_name") or item.get("host_venue", {}).get("display_name", "")
    return canonical_venue(clean_text(display_name), config)


def openalex_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions:
            words.append((position, word))
    return " ".join(word for _, word in sorted(words))


def canonical_venue(venue: str, config: dict[str, Any]) -> str:
    venue_lower = venue.lower()
    for canonical, aliases in config.get("venue_aliases", {}).items():
        if any(alias.lower() in venue_lower for alias in aliases):
            return canonical
    return venue or "Unknown"


def contains_term(haystack: str, term: str) -> bool:
    escaped = re.escape(term.lower()).replace(r"\ ", r"\s+")
    return re.search(rf"\b{escaped}\b", haystack) is not None


def score_paper(paper: RawPaper, config: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    haystack = f"{paper.title} {paper.abstract} {paper.venue}".lower()
    matched: list[str] = []
    reasons: list[str] = []
    score = 0

    for keyword in config["positive_keywords"]:
        if contains_term(haystack, keyword):
            matched.append(keyword)
            score += 2 if " " in keyword else 1

    context_hit = any(contains_term(haystack, keyword) for keyword in config["required_context_keywords"])
    if context_hit:
        score += 2
        reasons.append("matches required agent/web/tool context")
    else:
        score -= 6
        reasons.append("missing required agent/web/tool context")

    security_hit = any(contains_term(haystack, keyword) for keyword in config["required_security_keywords"])
    if security_hit:
        score += 2
        reasons.append("matches required security/safety/privacy context")
    else:
        score -= 6
        reasons.append("missing required security/safety/privacy context")

    if paper.venue in config.get("venue_aliases", {}):
        score += 2
        reasons.append(f"matches target venue: {paper.venue}")

    for keyword in config["negative_keywords"]:
        if contains_term(haystack, keyword):
            score -= 4
            reasons.append(f"negative keyword: {keyword}")

    return score, sorted(set(matched)), reasons


def existing_index(papers_data: dict[str, Any]) -> list[dict[str, str]]:
    index = []
    for paper in papers_data.get("papers", []):
        index.append(
            {
                "id": paper["id"],
                "title": paper["title"],
                "normalized_title": normalize_title(paper["title"]),
                "url": paper.get("url", ""),
            }
        )
    return index


def duplicate_of(raw: RawPaper, existing: list[dict[str, str]]) -> str:
    normalized = normalize_title(raw.title)
    for item in existing:
        if normalized == item["normalized_title"]:
            return item["id"]
        if raw.url and raw.url == item.get("url"):
            return item["id"]
        if raw.doi and raw.doi.lower() in item.get("url", "").lower():
            return item["id"]
        if SequenceMatcher(None, normalized, item["normalized_title"]).ratio() >= 0.92:
            return item["id"]
    return ""


def candidate_record(raw: RawPaper, config: dict[str, Any], duplicate: str) -> dict[str, Any]:
    score, matched, reasons = score_paper(raw, config)
    year = raw.year or datetime.now(timezone.utc).year
    return {
        "id": slugify(raw.title, year),
        "title": raw.title,
        "venue": raw.venue,
        "year": year,
        "paper_type": "Unknown",
        "category": "Needs Review",
        "web_agent_relevance": min(5, max(1, round(score / 3))),
        "status": "pending_review",
        "url": raw.url,
        "doi": raw.doi,
        "arxiv_id": raw.arxiv_id,
        "source": raw.source,
        "published": raw.published,
        "authors": raw.authors[:12],
        "topic_tags": matched[:8],
        "summary": raw.abstract[:700],
        "discovery_score": score,
        "discovery_reasons": reasons,
        "duplicate_of": duplicate,
        "decision": "pending",
        "review_notes": ""
    }


def discover(config: dict[str, Any], no_network: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    papers_data = load_json(PAPERS_PATH)
    existing = existing_index(papers_data)
    since = datetime.now(timezone.utc) - timedelta(days=int(config["lookback_days"]))
    seen_titles: set[str] = set()
    candidates: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    current_year = datetime.now(timezone.utc).year

    if no_network:
        return candidates, duplicates

    for query in config["queries"]:
        source = query["source"]
        query_text = query["query"]
        try:
            if source == "arxiv":
                raw_papers = fetch_arxiv(query_text, config, since)
                time.sleep(int(config.get("arxiv_request_delay_seconds", 10)))
            elif source == "crossref":
                raw_papers = fetch_crossref(query_text, config, since)
                time.sleep(int(config.get("crossref_request_delay_seconds", 1)))
            elif source == "dblp":
                raw_papers = fetch_dblp(query_text, config, since)
                time.sleep(int(config.get("dblp_request_delay_seconds", 1)))
            elif source == "openalex":
                raw_papers = fetch_openalex(query_text, config, since)
                time.sleep(int(config.get("openalex_request_delay_seconds", 1)))
            elif source == "semantic_scholar":
                raw_papers = fetch_semantic_scholar(query_text, config, since)
                time.sleep(int(config.get("semantic_scholar_request_delay_seconds", 1)))
            else:
                print(f"Skipping unsupported source: {source}", file=sys.stderr)
                continue
        except Exception as exc:  # Network sources should not fail the whole run.
            print(f"WARNING: {source} query failed: {query_text}: {exc}", file=sys.stderr)
            continue

        for raw in raw_papers:
            if raw.year and raw.year > current_year + 1:
                continue
            normalized = normalize_title(raw.title)
            if not normalized or normalized in seen_titles:
                continue
            seen_titles.add(normalized)

            duplicate = duplicate_of(raw, existing)
            record = candidate_record(raw, config, duplicate)
            if duplicate:
                duplicates.append(record)
            elif record["discovery_score"] >= int(config["min_score"]):
                candidates.append(record)

    candidates.sort(key=lambda item: (-item["discovery_score"], item["year"], item["title"]))
    duplicates.sort(key=lambda item: (item["duplicate_of"], item["title"]))
    return candidates, duplicates


def write_output(candidates: list[dict[str, Any]], duplicates: list[dict[str, Any]], output: Path) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "review_instructions": [
            "This file is generated by scripts/discover_papers.py.",
            "Set decision to accept or reject after human review.",
            "Run scripts/promote_candidates.py <candidate-file> to append accepted candidates to data/papers.json."
        ],
        "candidates": candidates,
        "duplicates": duplicates,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-network", action="store_true", help="Validate configuration without contacting external sources.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json(args.config)
    output = args.output or CANDIDATES_DIR / f"{datetime.now(timezone.utc).date().isoformat()}.json"
    candidates, duplicates = discover(config, no_network=args.no_network)
    write_output(candidates, duplicates, output)
    print(f"Wrote {len(candidates)} candidates and {len(duplicates)} duplicates to {display_path(output)}")


if __name__ == "__main__":
    main()
