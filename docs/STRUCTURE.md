# Repository Structure

This repository is designed as a dynamic paper repository for Web Agent Security.

```text
.
├── README.md
├── data/
│   ├── papers.json        # Single source of truth for paper metadata
│   └── taxonomy.json      # Taxonomy used by README and future analyses
├── docs/
│   ├── STRUCTURE.md       # Repository design
│   └── TAXONOMY.md        # Human-readable taxonomy notes
├── scripts/
│   ├── generate_readme.py # Regenerates README from data/papers.json
│   └── validate_data.py   # Validates required fields and duplicate ids
└── .github/workflows/
    └── update-readme.yml  # GitHub Actions workflow for validation/generation
```

## Update Model

1. Update `data/papers.json` when adding papers, changing status, or revising metadata.
2. Run `python3 scripts/validate_data.py`.
3. Run `python3 scripts/generate_readme.py`.
4. Commit the changed data and generated README.

The data file is intentionally JSON rather than YAML so the current automation can run with Python's standard library only.
