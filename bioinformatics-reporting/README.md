
<p align="center">
  <img src="assets/CAB-aiSkills_bioinformatics-reporting.svg" alt="bioinformatics-reporting skill badge" width="520" />
</p>

# Bioinformatics Reporting — Agent Skill

Portable **Agent Skill** for turning **existing** bioinformatics result directories into polished,
evidence-grounded **Quarto HTML/PDF reports** with a complete reproducibility bundle. The skill
discovers or validates artifacts, builds a normalized report model with provenance-backed metrics,
renders self-contained HTML (and PDF when Quarto and a TeX engine are available), and verifies
deliverables. Agent-facing instructions are in [SKILL.md](SKILL.md).

Primary rendering stack is **Quarto only** (no Sphinx/RST compatibility layer). Source result
directories are read-only; portable copies land under `figures/` and `tables/` inside the run
directory.

## Environment

This skill uses a **persistent Python venv** under your home cache plus **host binaries** for
rendering:

| Item | Location |
|------|----------|
| Cache root | `~/.cache/cursor-skills/bioinformatics-reporting/` |
| Venv | `~/.cache/cursor-skills/bioinformatics-reporting/venv/` |
| Spec | [requirements.txt](requirements.txt) |
| Setup | `bash scripts/ensure_env.sh` |
| Rebuild | `bash scripts/ensure_env.sh --force-rebuild` |
| Backend | `python -m venv` (pure-Python deps) |

```bash
cd bioinformatics-reporting
bash scripts/ensure_env.sh
bash scripts/ensure_env.sh --print-python
```

**Host tools** (not installed by the skill):

| Tool | Role |
|------|------|
| **Quarto** | Required for HTML/PDF rendering |
| **pdflatex** or **xelatex** | Required for PDF output |
| **pdftoppm** | Optional; rasterizes PDF pages into `pdf_pages/` |

Python CLIs auto-bootstrap via [scripts/skill_env.py](scripts/skill_env.py). Use
[scripts/run_with_skill_env.sh](scripts/run_with_skill_env.sh) to run commands inside the cached
venv.

## Install for Cursor or other agent clients

- **Project skill:** Copy or symlink this folder so the client discovers a directory named
  `bioinformatics-reporting` containing `SKILL.md` (for example `.cursor/skills/bioinformatics-reporting/`).
- **Invoke** by skill name `bioinformatics-reporting`, or ask the agent to create a scientific
  report from existing RNA-seq, ATAC-seq, ChIP-seq, enrichment, or overlap results, as described in
  [SKILL.md](SKILL.md).

## Quick start

Run from **this directory** (`bioinformatics-reporting`) unless you pass absolute paths.

### Validate a manifest, then render HTML

```bash
bash scripts/ensure_env.sh
python scripts/validate_manifest.py tests/fixtures/differential_manifest.yaml --baseDir tests/fixtures
python scripts/render_report.py \
  --manifest tests/fixtures/differential_manifest.yaml \
  --outputDir /tmp/bioinformatics-report-smoke \
  --baseDir tests/fixtures \
  --formats html
```

### Full pipeline from multi-module fixtures

```bash
python scripts/build_report_model.py \
  --manifest tests/fixtures/multi_module/manifest.yaml \
  --output /tmp/bioinformatics-report/report-model.json \
  --baseDir tests/fixtures/multi_module \
  --outputDir /tmp/bioinformatics-report

python scripts/render_report.py \
  --reportModel /tmp/bioinformatics-report/report-model.json \
  --outputDir /tmp/bioinformatics-report \
  --baseDir tests/fixtures/multi_module \
  --formats html,pdf

python scripts/verify_report.py --reportDir /tmp/bioinformatics-report --outputDir /tmp/bioinformatics-report
```

### Discover artifacts when no manifest exists

```bash
python scripts/discover_artifacts.py \
  --resultsDir /path/to/agentResults/some-run \
  --output /tmp/artifact_inventory.tsv
```

Review confidence labels, resolve ambiguities with the user, then export or hand-build a manifest
before rendering.

## Example output

Bundled sample report generated from the multi-module fixtures (RNA-seq DEG + ATAC differential
accessibility):

- [examples/sample-report/bioinformatics-report.html](examples/sample-report/bioinformatics-report.html) — self-contained HTML
- [examples/sample-report/bioinformatics-report.qmd](examples/sample-report/bioinformatics-report.qmd) — reproducible Quarto source
- [examples/sample-report/report_verification.json](examples/sample-report/report_verification.json) — authoritative verification record

## How the agent uses this skill

1. Read [SKILL.md](SKILL.md) and inspect the results directory or manifest.
2. Choose input mode — explicit manifest (preferred), discovery, or direct artifact list — per
   [references/artifact-contract.md](references/artifact-contract.md).
3. Validate with [scripts/validate_manifest.py](scripts/validate_manifest.py); stop on fatal errors.
4. Create `agentResults/bioinformatics-reporting-<YYYYMMDDTHHMMSSZ>/` and write `agent_request.txt`
   plus `agent_workflow.md`.
5. Build [scripts/build_report_model.py](scripts/build_report_model.py) output; optionally stage
   portable copies with [scripts/stage_artifacts.py](scripts/stage_artifacts.py).
6. Write evidence-grounded prose in optional `report_narrative.yaml` using
   [references/interpretation-guidelines.md](references/interpretation-guidelines.md).
7. Render with [scripts/render_report.py](scripts/render_report.py); verify with
   [scripts/verify_report.py](scripts/verify_report.py).
8. Report deliverable paths and warnings from `report_verification.json` and `run_metadata.json`
   only — do not claim PDF success unless verification passes.

## Layout

| Path | Role |
|------|------|
| [assets/](assets/) | Skill badge SVG, Quarto SCSS theme, QMD template |
| [SKILL.md](SKILL.md) | Agent workflow, safety, and output contract |
| [scripts/ensure_env.sh](scripts/ensure_env.sh) | Persistent venv under `~/.cache/cursor-skills/bioinformatics-reporting/` |
| [scripts/discover_artifacts.py](scripts/discover_artifacts.py) | Read-only artifact discovery and role classification |
| [scripts/validate_manifest.py](scripts/validate_manifest.py) | Manifest schema and path validation |
| [scripts/build_report_model.py](scripts/build_report_model.py) | Normalized JSON report model with provenance metrics |
| [scripts/render_report.py](scripts/render_report.py) | Quarto QMD, self-contained HTML, optional PDF |
| [scripts/verify_report.py](scripts/verify_report.py) | Deliverable, link, and PDF page checks |
| [references/](references/) | Manifest schema, report structure, interpretation, output layout |
| [examples/](examples/) | Evaluation prompts and bundled [sample-report/](examples/sample-report/) |
| [tests/](tests/) | Pytest suite and sanitized fixtures |

## Outputs

Every run writes under `agentResults/bioinformatics-reporting-<YYYYMMDDTHHMMSSZ>/` (or a user-specified
directory). See [references/output-layout.md](references/output-layout.md) for the full tree.

| File / directory | Description |
|------------------|-------------|
| `bioinformatics-report.qmd` | Reproducible Quarto source |
| `bioinformatics-report.html` | Self-contained HTML report |
| `bioinformatics-report.pdf` | Print-ready PDF when Quarto and a PDF engine succeed |
| `report-model.json` | Normalized model with provenance-backed metrics |
| `report_narrative.yaml` | Optional agent-authored executive summary and themes |
| `report_manifest.yaml` | Artifacts, warnings, software, render status |
| `report_verification.json` | **Authoritative** verification record (`valid`, errors, deliverables) |
| `figures/`, `tables/` | Portable staged subsets with provenance |
| `pdf_pages/` | Optional rasterized PDF pages for agent inspection |
| `run_metadata.json` | UTC run ID, command, inputs, tool versions |
| `logs/` | Per-script logs and `commands.log` |
| `agent_request.txt`, `agent_workflow.md` | Verbatim prompt and agent preparation notes |

`report_verification.json` is written during rendering and re-used by verification. Do not claim HTML
or PDF success unless this file reports `valid: true` for the requested deliverables.
`report_manifest.yaml` copies render status from verification so the two cannot drift.

## Reproducibility

Every run must leave `run_metadata.json`, `logs/commands.log`, `agent_request.txt`, and
`agent_workflow.md`. Pass `--runId`, `--outputDir`, `--agentRequestFile`, and `--agentWorkflowFile`
to scripts that write derived artifacts. Upstream `run_metadata.json` files are scanned **only**
inside the requested results directory. Warnings (missing genome build, skipped PDF, tentative
artifact roles) must appear in the report rather than being silently dropped.

## User-facing prompt examples

Example prompts a user might type and how the agent should interpret them. See
[examples/evaluation-prompts.md](examples/evaluation-prompts.md) for trigger, regression, and edge-case
prompts.

| User prompt | Interpretation |
|---|---|
| "Create a bioinformatics report from these ATAC-seq and RNA-seq results under `agentResults/`" | Inventory results; validate or discover manifest; build model; render HTML/PDF; verify |
| "Summarize differential expression and pathway enrichment outputs into one HTML report" | Combine multi-skill artifacts; explicit roles in manifest; evidence-grounded narrative |
| "Generate HTML and PDF from this results directory" | Discovery or manifest; `--formats html,pdf`; report PDF engine status from verification |
| "Update the existing analysis report with new overlap analysis outputs" | Extend manifest; rebuild model; re-render; preserve provenance to source artifacts |
| "Run DESeq2 on this count matrix" | **Out of scope** — use upstream DE skill; this skill consumes existing results |
| "Make a volcano plot grid from these tables" | **Out of scope** — use `volcano-grid-plot` |

## Testing

```bash
export BIOINFORMATICS_REPORTING_SKIP_ENV_BOOTSTRAP=1
bash scripts/ensure_env.sh
python -m pytest tests -q
```

End-to-end tests that invoke Quarto are skipped when the Quarto CLI is not on `PATH`.

## Maintainer

Toolbox curator and current skill author(s): [AUTHORS.md](../AUTHORS.md). St Jude Children's Research Hospital.

**License:** [CC BY-NC-SA 4.0](../LICENSE.txt).

Changelog: [../docs/changelog.md](../docs/changelog.md).
