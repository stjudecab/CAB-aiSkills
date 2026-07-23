# bioinformatics-reporting

Standalone Agent Skill for turning **existing** bioinformatics result directories into polished,
evidence-grounded **Quarto HTML/PDF reports** with a complete reproducibility bundle.

## Quick start

```bash
bash scripts/ensure_env.sh
python scripts/validate_manifest.py tests/fixtures/differential_manifest.yaml --baseDir tests/fixtures
python scripts/render_report.py \
  --manifest tests/fixtures/differential_manifest.yaml \
  --outputDir /tmp/bioinformatics-report-smoke \
  --baseDir tests/fixtures \
  --formats html
```

## Directory layout

```text
bioinformatics-reporting/
├── SKILL.md
├── README.md
├── requirements.txt
├── assets/                 # Quarto SCSS theme, logo
├── references/             # manifest schema, interpretation, output layout
├── examples/               # evaluation prompts and bundled sample outputs
├── scripts/                # discovery, model build, Quarto render, verification
└── tests/                  # pytest suite and sanitized fixtures
```

## Environment

| Item | Location |
|------|----------|
| Cache root | `~/.cache/cursor-skills/bioinformatics-reporting/` |
| Venv | `~/.cache/cursor-skills/bioinformatics-reporting/venv/` |
| Force rebuild | `bash scripts/ensure_env.sh --force-rebuild` |

Host tools:

- **Quarto** — required for HTML/PDF rendering
- **pdflatex** or **xelatex** — required for PDF output
- **pdftoppm** — optional; rasterizes PDF pages into `pdf_pages/`

## Testing

```bash
export BIOINFORMATICS_REPORTING_SKIP_ENV_BOOTSTRAP=1
bash scripts/ensure_env.sh
python -m pytest tests -q
```

## Maintainer notes

- Primary rendering stack is **Quarto only** (no Sphinx/RST compatibility layer).
- `report_verification.json` is the authoritative verification record; `report_manifest.yaml` derives status from it.
- Source result directories are read-only; staging copies land under `figures/` and `tables/` inside the run directory.

Changelog: [../docs/changelog.md](../docs/changelog.md)
