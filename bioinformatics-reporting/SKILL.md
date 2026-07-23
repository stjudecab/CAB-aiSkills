---
name: bioinformatics-reporting
description: >-
  Inspect, validate, interpret, and combine outputs from bioinformatics skills or
  pipelines into polished, reproducible scientific reports (Quarto QMD source, self-contained
  HTML, print-ready PDF when Quarto and pdflatex are available, report manifest, and verification
  bundle). Use when asked to create a bioinformatics report from results, summarize RNA-seq/ATAC-seq/ChIP-seq/CUT&RUN
  outputs, generate HTML and PDF from a results directory, combine QC/differential/enrichment
  results, prepare a scientific report from pipeline outputs, merge multi-omics result collections,
  or update an existing analysis report with new results. Do not use for upstream analysis alone.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.10+ with pandas, PyYAML, openpyxl, Pillow, Jinja2. Persistent venv via
  scripts/ensure_env.sh at ~/.cache/cursor-skills/bioinformatics-reporting/venv/. Host Quarto CLI
  required for HTML/PDF rendering; pdflatex or xelatex for PDF. Local filesystem only.
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "1.0.0"
  status: draft
  last_reviewed: "2026-07-22"
allowed-tools: shell python
---

# Bioinformatics Reporting

## Purpose

Compose evidence-grounded scientific reports from **existing** bioinformatics results. Discover or
validate artifacts, build a normalized report model with provenance-backed metrics, render Quarto
HTML/PDF, and verify deliverables. Never invent findings, thresholds, sample annotations, or software versions.

## When to Use

Use when the user asks to:

- create a bioinformatics report from results,
- summarize outputs from RNA-seq, ATAC-seq, ChIP-seq, CUT&RUN/CUT&Tag, methylation, enrichment, or overlap analyses,
- generate HTML and PDF from a results directory,
- combine QC, differential, and enrichment outputs,
- prepare or update a scientific report from pipeline or skill outputs.

## When Not to Use

- run upstream differential expression, peak calling, alignment, enrichment, or motif discovery **without** report generation,
- replace a focused plotting/export skill when only one figure or table is requested.

## Input modes

| Mode | When | Action |
|------|------|--------|
| **1. Explicit manifest** (preferred) | YAML/JSON manifest exists or upstream skill wrote one | Validate with `validate_manifest.py`, then build/render |
| **2. Results-directory discovery** | No manifest | Run `discover_artifacts.py`, review confidence labels, export manifest or ask user about ambiguities |
| **3. Direct artifact list** | User lists files + roles | Convert to manifest internally before building the report model |

Read [references/artifact-contract.md](references/artifact-contract.md) for the manifest schema and artifact roles.

## Required inputs

- A **results directory**, **manifest**, or **explicit artifact list**.
- For genomic interpretation: an explicitly supplied **genome build** when region-level claims are needed (warn if missing; never invent).

## Optional inputs

- `report_narrative.yaml` with agent-authored executive summary and biological themes.
- Manifest/report overrides under `report:` (title, colors, PDF toggle) — see [references/visual-style.md](references/visual-style.md).
- `--baseDir` when artifact paths are relative to a directory other than the manifest parent.

## Persistent runtime environment (CRITICAL)

Run once before the first script invocation:

```bash
bash scripts/ensure_env.sh
```

| Item | Location |
|------|----------|
| Cache root | `~/.cache/cursor-skills/bioinformatics-reporting/` |
| Venv prefix | `~/.cache/cursor-skills/bioinformatics-reporting/venv/` |
| Shell wrapper | `bash scripts/run_with_skill_env.sh <command>` |

Force rebuild: `bash scripts/ensure_env.sh --force-rebuild`

Python CLIs auto-bootstrap via `scripts/skill_env.py`.

## Workflow

1. **Inspect inputs safely** — inventory paths; read headers/metadata only as needed; never modify source results.
2. **Choose input mode** — manifest, discovery, or direct list (see table above).
3. **Validate** — fatal errors (missing primary files, invalid explicit manifest) must stop the run; warnings go into the report.
4. **Create run directory** — `agentResults/bioinformatics-reporting-<YYYYMMDDTHHMMSSZ>/`.
5. **Write agent artifacts** — `agent_request.txt` (verbatim prompt) and `agent_workflow.md` (mapping, manifest path, exact CLI).
6. **Discover / profile (optional)** — `discover_artifacts.py`, `profile_artifacts.py`, `stage_artifacts.py` when portable copies or batch profiling are needed.
7. **Build report model** — profile tables and assemble provenance-backed metrics. Upstream `run_metadata.json` files are scanned **only inside the requested results directory**.

```bash
python scripts/build_report_model.py \
  --manifest path/to/manifest.yaml \
  --output agentResults/.../report-model.json \
  --baseDir path/to/results \
  --outputDir agentResults/.../ \
  --runId <YYYYMMDDTHHMMSSZ> \
  --agentRequestFile agent_request.txt \
  --agentWorkflowFile agent_workflow.md
```

8. **Write evidence-grounded narrative** — save optional `report_narrative.yaml` using [references/interpretation-guidelines.md](references/interpretation-guidelines.md). Distinguish observations, interpretations, and hypotheses; cite source artifacts.
9. **Render deliverables**:

```bash
python scripts/render_report.py \
  --reportModel agentResults/.../report-model.json \
  --outputDir agentResults/.../ \
  --baseDir path/to/results \
  --formats html,pdf \
  --narrative agentResults/.../report_narrative.yaml \
  --runId <YYYYMMDDTHHMMSSZ> \
  --agentRequestFile agent_request.txt \
  --agentWorkflowFile agent_workflow.md
```

10. **Verify**:

```bash
python scripts/verify_report.py --reportDir agentResults/.../ --outputDir agentResults/.../
```

11. **Report to user** — run directory, QMD/HTML/PDF paths, warnings, PDF engine status from `run_metadata.json` and `report_verification.json`.

## Scripts

| Script | Purpose |
|--------|---------|
| [scripts/discover_artifacts.py](scripts/discover_artifacts.py) | Read-only recursive discovery + role/confidence classification |
| [scripts/validate_manifest.py](scripts/validate_manifest.py) | Schema/path validation; errors vs warnings |
| [scripts/profile_table.py](scripts/profile_table.py) | Safe single-table profiling |
| [scripts/profile_artifacts.py](scripts/profile_artifacts.py) | Batch table profiling from manifest or inventory |
| [scripts/stage_artifacts.py](scripts/stage_artifacts.py) | Portable artifact copies with SHA-256 checksums |
| [scripts/build_report_model.py](scripts/build_report_model.py) | Normalized JSON report model with provenance metrics |
| [scripts/render_report.py](scripts/render_report.py) | Quarto QMD, self-contained HTML, optional PDF |
| [scripts/verify_report.py](scripts/verify_report.py) | Deliverable/link/PDF page checks |

## Output format

Primary deliverables in the run directory:

- `bioinformatics-report.qmd` — reproducible Quarto source
- `bioinformatics-report.html` — self-contained HTML report
- `bioinformatics-report.pdf` — when Quarto and a PDF engine succeed
- `report.scss` — bundled theme copied into the run directory
- `figures/`, `tables/` — portable staged subsets with provenance
- `report_manifest.yaml` — artifacts, warnings, software, verification status
- `report-model.json` — normalized model used for rendering
- `report_narrative.yaml` — optional agent-authored narrative sections
- `report_verification.json` — **authoritative** render/verification record
- `pdf_pages/` — rasterized PDF pages for agent inspection when available
- `artifact_inventory.tsv` — when staging was performed

See [references/report-structure.md](references/report-structure.md) and [references/output-layout.md](references/output-layout.md).

## Reproducibility and documentation (CRITICAL)

Every run must leave:

1. `run_metadata.json`
2. `logs/<scriptName>.log`
3. `logs/commands.log`
4. `agent_request.txt`
5. `agent_workflow.md`

Pass `--runId`, `--outputDir`, `--agentRequestFile`, and `--agentWorkflowFile` to scripts that write derived artifacts.

## Resources

- [references/artifact-contract.md](references/artifact-contract.md) — manifest schema and artifact roles
- [references/output-layout.md](references/output-layout.md) — run directory tree and verification schema
- [references/report-structure.md](references/report-structure.md) — default sections and hierarchy
- [references/interpretation-guidelines.md](references/interpretation-guidelines.md) — evidence rules and prohibited claims
- [references/analysis-modules.md](references/analysis-modules.md) — QC, differential, enrichment, overlap modules
- [references/visual-style.md](references/visual-style.md) — colors, layout, report config
- [examples/evaluation-prompts.md](examples/evaluation-prompts.md) — trigger and regression prompts

## Quality checks

Before finishing, verify:

- manifest validated (or discovery inventory reviewed with user when ambiguous),
- `report-model.json` exists and metrics have provenance,
- `bioinformatics-report.qmd` and HTML exist; PDF only claimed when actually rendered,
- `report_verification.json` reports `valid: true` (or document expected warnings),
- warnings visible in the report,
- no unresolved template variables,
- source inputs unchanged,
- `run_metadata.json` and logs present.

## Failure and escalation

| Symptom | Action |
|---------|--------|
| `Quarto CLI not found` | Deliver QMD + staged artifacts; record exact render command in logs |
| `pdflatex not installed` | Deliver QMD/HTML; PDF skipped with warning |
| Invalid manifest / all files missing | Stop; list errors; do not fabricate content |
| Tentative artifact roles | Label in report or ask user when interpretation depends on role |
| Missing genome build | Warn when region-level interpretation requires it |
| Large tables | Use preview subset + download link (automatic via profiler) |

## What this skill must never do

- invent scientific findings, thresholds, sample metadata, significance, or software versions,
- rerun major upstream analyses silently,
- upload result directories or use external CDNs/analytics by default,
- execute code from result directories,
- modify source result files.
