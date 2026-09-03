#!/usr/bin/env python3
"""Generate README.md from data/papers.json."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS_PATH = ROOT / "data" / "papers.json"
README_PATH = ROOT / "README.md"

def stars(value: int) -> str:
    return "★" * value + "☆" * (5 - value)


def paper_link(item: dict) -> str:
    title = item.get("short_name") or item["title"]
    url = item.get("url")
    if url:
        return f"[{title}]({url})"
    return title


def table_row(item: dict) -> str:
    tags = ", ".join(f"`{tag}`" for tag in item["topic_tags"][:4])
    return (
        f"| {paper_link(item)} | {item['venue']} {item['year']} | "
        f"{item['paper_type']} | {stars(item['web_agent_relevance'])} | "
        f"{item['category']} | {tags} |"
    )


def grouped_by_category(papers: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in papers:
        grouped[item["category"]].append(item)

    lines: list[str] = []
    for category in sorted(grouped):
        lines.append(f"### {category}")
        lines.append("")
        for item in sorted(grouped[category], key=lambda x: (x["year"], x["title"])):
            lines.append(f"- {paper_link(item)} ({item['venue']} {item['year']})")
        lines.append("")
    return "\n".join(lines).rstrip()


def stats_line(papers: list[dict]) -> str:
    latest_year = max((item["year"] for item in papers), default="N/A")
    return f"Corpus size: **{len(papers)} papers** · latest year: **{latest_year}**."


def render(data: dict) -> str:
    project = data["project"]
    papers = sorted(data["papers"], key=lambda x: (x["year"], x["venue"], x["title"]))
    generated = date.today().isoformat()

    lines = [
        f"# {project['title']}",
        "",
        project["description"],
        "",
        f"> Generated from `data/papers.json` on {generated}. Last corpus review: {project['last_reviewed']}.",
        "",
        stats_line(papers),
        "",
        "## Papers",
        "",
        "| Paper | Venue | Type | Web Agent Relevance | Category | Tags |",
        "|---|---|---|---:|---|---|",
    ]
    lines.extend(table_row(item) for item in papers)

    lines.extend(
        [
            "",
            "## Taxonomy View",
            "",
            grouped_by_category(papers),
            "",
            "## Repository Update Workflow",
            "",
            "1. Edit `data/papers.json` to add papers or update metadata.",
            "2. Run `python3 scripts/validate_data.py`.",
            "3. Run `python3 scripts/generate_readme.py`.",
            "4. Commit the data and generated README.",
            "",
            "## Weekly Discovery",
            "",
            "Weekly discovery is configured in `data/discovery_config.json` and implemented by `scripts/discover_papers.py`. The bot writes candidate papers to `data/candidates/` for human review; it does not edit `data/papers.json` directly.",
            "",
            "See `docs/STRUCTURE.md` and `docs/TAXONOMY.md` for the repository design.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    data = json.loads(PAPERS_PATH.read_text(encoding="utf-8"))
    README_PATH.write_text(render(data), encoding="utf-8")
    print(f"Generated {README_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
