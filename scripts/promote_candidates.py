#!/usr/bin/env python3
"""Promote human-accepted discovery candidates into data/papers.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAPERS_PATH = ROOT / "data" / "papers.json"

PAPER_FIELDS = [
    "id",
    "title",
    "venue",
    "year",
    "paper_type",
    "category",
    "web_agent_relevance",
    "status",
    "url",
    "topic_tags",
    "summary",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def unique_id(base_id: str, existing_ids: set[str]) -> str:
    if base_id not in existing_ids:
        return base_id
    index = 2
    while f"{base_id}-{index}" in existing_ids:
        index += 1
    return f"{base_id}-{index}"


def to_paper(candidate: dict[str, Any], existing_ids: set[str]) -> dict[str, Any]:
    candidate = dict(candidate)
    candidate["id"] = unique_id(candidate["id"], existing_ids)
    candidate["status"] = "tracked"
    paper = {field: candidate.get(field, "") for field in PAPER_FIELDS}
    paper["topic_tags"] = candidate.get("topic_tags") or []
    paper["web_agent_relevance"] = int(candidate.get("web_agent_relevance") or 3)
    paper["year"] = int(candidate.get("year") or datetime.now(timezone.utc).year)
    return paper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_file", type=Path)
    parser.add_argument("--papers", type=Path, default=PAPERS_PATH)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    papers_data = load_json(args.papers)
    candidates_data = load_json(args.candidate_file)
    existing_ids = {paper["id"] for paper in papers_data.get("papers", [])}
    existing_titles = {paper["title"].strip().lower() for paper in papers_data.get("papers", [])}

    accepted = []
    for candidate in candidates_data.get("candidates", []):
        if candidate.get("decision") != "accept":
            continue
        if candidate.get("duplicate_of"):
            print(f"Skipping duplicate candidate: {candidate['title']}")
            continue
        if candidate["title"].strip().lower() in existing_titles:
            print(f"Skipping existing title: {candidate['title']}")
            continue
        paper = to_paper(candidate, existing_ids)
        accepted.append(paper)
        existing_ids.add(paper["id"])
        existing_titles.add(paper["title"].strip().lower())

    if not accepted:
        print("No accepted candidates to promote.")
        return

    papers_data["papers"].extend(accepted)
    papers_data["papers"].sort(key=lambda item: (item["year"], item["venue"], item["title"]))
    papers_data["project"]["last_reviewed"] = datetime.now(timezone.utc).date().isoformat()

    if args.dry_run:
        print(f"Would promote {len(accepted)} candidates:")
        for paper in accepted:
            print(f"- {paper['title']} ({paper['venue']} {paper['year']})")
        return

    write_json(args.papers, papers_data)
    print(f"Promoted {len(accepted)} candidates into {display_path(args.papers)}")


if __name__ == "__main__":
    main()
