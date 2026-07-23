# Output layout and verification schema

## Contents

- Run directory tree
- Authoritative verification record
- `run_metadata.json` fields
- Manifest status coupling

## Run directory tree

```text
agentResults/bioinformatics-reporting-<YYYYMMDDTHHMMSSZ>/
├── bioinformatics-report.qmd
├── bioinformatics-report.html
├── bioinformatics-report.pdf              # when Quarto + PDF engine succeed
├── report.scss
├── report-model.json
├── report_narrative.yaml                  # optional agent-authored prose
├── report_manifest.yaml
├── report_verification.json               # authoritative verification record
├── artifact_inventory.tsv                 # when staging was used
├── figures/
├── tables/
├── pdf_pages/                             # optional rasterized PDF pages
├── agent_request.txt
├── agent_workflow.md
├── run_metadata.json
└── logs/
    ├── render_report.log
    └── commands.log
```

## Authoritative verification record

`report_verification.json` is written during rendering and re-used by `verify_report.py`.
Do not claim PDF or HTML success unless this file reports `valid: true` for the requested deliverables.

Minimum fields:

| Field | Meaning |
|-------|---------|
| `valid` | Overall pass/fail for required deliverables |
| `errors` | Fatal issues (missing QMD/HTML, broken links, unresolved placeholders) |
| `warnings` | Non-fatal issues (missing PDF, external image URLs) |
| `deliverables` | Resolved paths for QMD, HTML, PDF, and rasterized pages |
| `render` | Quarto command logs and staged artifact metadata |

## `run_metadata.json` fields

See repository [AGENTS.md](../AGENTS.md) for the shared reproducibility contract. Reporting scripts additionally record:

- resolved Quarto and PDF engine versions under `tool_versions`
- staged artifact counts under `summary`
- verification validity under `summary.verification_valid` after rendering

## Manifest status coupling

`report_manifest.yaml` includes:

```yaml
render_status:
  valid: true
  errors: []
  warnings: []
```

Values are copied from `report_verification.json` at render time so manifest and verification cannot drift.
