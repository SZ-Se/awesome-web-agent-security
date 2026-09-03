#!/usr/bin/env python3
"""Validate the paper repository data files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS_PATH = ROOT / "data" / "papers.json"

REQUIRED_PAPER_FIELDS = {
    "id",
    "title",
    "venue",
    "year",
    "paper_type",
    "category",
    "web_agent_relevance",
    "status",
    "topic_tags",
    "summary",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    data = json.loads(PAPERS_PATH.read_text(encoding="utf-8"))
    papers = data.get("papers")
    if not isinstance(papers, list) or not papers:
        fail("papers must be a non-empty list")

    seen_ids: set[str] = set()
    for item in papers:
        missing = REQUIRED_PAPER_FIELDS - item.keys()
        if missing:
            fail(f"{item.get('title', '<unknown>')} is missing fields: {sorted(missing)}")

        paper_id = item["id"]
        if not isinstance(paper_id, str) or not paper_id.strip():
            fail(f"{item['title']} has an invalid id: {paper_id!r}")
        if paper_id in seen_ids:
            fail(f"duplicate paper id: {paper_id}")
        seen_ids.add(paper_id)

        year = item["year"]
        if not isinstance(year, int) or not 1900 <= year <= 2100:
            fail(f"{item['title']} has invalid year: {year!r}")

        relevance = item["web_agent_relevance"]
        if not isinstance(relevance, int) or not 1 <= relevance <= 5:
            fail(f"{item['title']} has invalid web_agent_relevance: {relevance!r}")

        tags = item["topic_tags"]
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            fail(f"{item['title']} has invalid topic_tags")

    print(f"OK: validated {len(papers)} papers")


if __name__ == "__main__":
    main()
