# Repository Structure

This repository is designed as a dynamic paper repository for Web Agent Security.

```text
.
├── README.md
├── data/
│   ├── papers.json        # Single source of truth for paper metadata
│   ├── discovery_config.json
│   ├── candidates/        # Bot-generated candidate papers for human review
│   └── taxonomy.json      # Taxonomy used by README and future analyses
├── docs/
│   ├── DISCOVERY.md       # Weekly discovery workflow
│   ├── STRUCTURE.md       # Repository design
│   └── TAXONOMY.md        # Human-readable taxonomy notes
├── scripts/
│   ├── discover_papers.py # Finds candidate papers without editing papers.json
│   ├── generate_readme.py # Regenerates README from data/papers.json
│   ├── promote_candidates.py
│   └── validate_data.py   # Validates required fields and duplicate ids
└── .github/workflows/
    ├── weekly-discovery.yml
    └── update-readme.yml  # GitHub Actions workflow for validation/generation
```

## Update Model

1. Update `data/papers.json` when adding papers, changing status, or revising metadata.
2. Run `python3 scripts/validate_data.py`.
3. Run `python3 scripts/generate_readme.py`.
4. Commit the changed data and generated README.

The data file is intentionally JSON rather than YAML so the current automation can run with Python's standard library only.

## Discovery Model

1. GitHub Actions runs `scripts/discover_papers.py` weekly.
2. New candidates are written to `data/candidates/latest.json`.
3. A pull request is opened for human review.
4. Accepted candidates are promoted with `scripts/promote_candidates.py`.
