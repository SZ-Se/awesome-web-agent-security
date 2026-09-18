#!/usr/bin/env python3
"""Require every discovered paper to have an explicit review decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_DECISIONS = {"accept", "reject"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path}: top-level value must be an object")
    return data


def validate_file(path: Path) -> tuple[int, int]:
    data = load_json(path)
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        fail(f"{path}: candidates must be a list")

    invalid: list[str] = []
    accepted = 0
    rejected = 0
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            invalid.append(f"item {index} is not an object")
            continue
        title = candidate.get("title") or f"item {index}"
        decision = candidate.get("decision")
        if decision not in ALLOWED_DECISIONS:
            invalid.append(f"{title}: decision is {decision!r}")
        elif decision == "accept":
            accepted += 1
        else:
            rejected += 1

    if invalid:
        details = "\n  - ".join(invalid)
        fail(
            f"{path}: every candidate must be reviewed as accept or reject."
            f"\n  - {details}"
        )

    return accepted, rejected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_files", type=Path, nargs="+")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total_accepted = 0
    total_rejected = 0
    for path in args.candidate_files:
        accepted, rejected = validate_file(path)
        total_accepted += accepted
        total_rejected += rejected
        print(f"OK: {path}: {accepted} accepted, {rejected} rejected")

    print(
        f"OK: reviewed {total_accepted + total_rejected} candidates "
        f"({total_accepted} accepted, {total_rejected} rejected)"
    )


if __name__ == "__main__":
    main()
