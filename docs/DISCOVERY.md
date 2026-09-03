# Weekly Paper Discovery

The repository supports weekly discovery of possible new Web Agent Security papers. Discovery is intentionally separated from promotion:

1. `scripts/discover_papers.py` searches external sources and writes candidate files under `data/candidates/`.
2. A maintainer reviews candidates and changes `decision` from `pending` to `accept` or `reject`.
3. `scripts/promote_candidates.py` appends accepted candidates to `data/papers.json`.
4. `scripts/generate_readme.py` regenerates the public README.

The bot never edits `data/papers.json` directly.

## Sources

The current implementation uses only Python's standard library and queries:

- arXiv API for recent preprints
- Crossref Works API for proceedings and journal metadata

The discovery configuration is in `data/discovery_config.json`. It contains search queries, venue aliases, positive keywords, negative keywords, target arXiv categories, and the minimum discovery score.

The venue aliases include the four major security conferences:

- IEEE S&P
- USENIX Security
- ACM CCS
- NDSS

They also include AI/NLP venues and related top journals that may publish relevant agent-security work.

## Run Locally

```bash
python3 scripts/discover_papers.py
```

This writes a dated candidate file such as:

```text
data/candidates/2026-09-03.json
```

To validate configuration without network access:

```bash
python3 scripts/discover_papers.py --no-network --output /tmp/discovery-test.json
```

## Human Review

Open the candidate file and review each item:

```json
"decision": "pending"
```

Change accepted papers to:

```json
"decision": "accept"
```

Rejected papers can be marked:

```json
"decision": "reject"
```

Then promote accepted candidates:

```bash
python3 scripts/promote_candidates.py data/candidates/latest.json
python3 scripts/validate_data.py
python3 scripts/generate_readme.py
```

## GitHub Actions

`.github/workflows/weekly-discovery.yml` runs every Monday at 02:00 UTC. If candidates are found, it opens a pull request containing `data/candidates/latest.json` for manual review.
