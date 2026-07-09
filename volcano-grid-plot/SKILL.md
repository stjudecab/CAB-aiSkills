---
name: volcano-grid-plot
description: >-
  Build publication-ready grids of Volcano and/or MA plots from multiple
  differential gene-expression or differential binding tables (RNA-seq, ChIP-seq,
  ATAC-seq, Cut&Run, multi-omics). Auto-detect or harmonize column names for
  log2FC, p-value/FDR, gene/region IDs, and average expression; highlight genes
  of interest. Use when the user asks for volcano plot grids, MA plot grids,
  multi-panel DE figures, or timecourse differential visualization.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.9+ with pandas, numpy, matplotlib, seaborn. Local filesystem
  only; no network access required.
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "1.0.0"
  status: stable
  last_reviewed: "2026-05-19"
allowed-tools: shell python
---

# Volcano Grid Plot

## Purpose

Produce **publication-ready multi-panel Volcano and/or MA figures** from one or more differential analysis result tables. Panels share axis limits for direct comparison. Supports RNA-seq DEG tables (gene symbols) and differential binding/epigenomics (genomic regions, optional peak-to-gene labeling).

## When to Use

Use this skill when the user asks to:

- Create a **volcano plot grid** or **MA plot grid** from multiple contrasts or timepoints.
- Visualize **differential gene expression** or **differential binding** results side by side.
- Highlight specific **genes** or **regions** on volcano/MA panels.
- Compare **1h vs 2h**, treatment vs control, or any manifest of DE tables in one figure.

## When Not to Use

- Two-file **correlation / concordance** scatter (KDE) — use `kde-correlation-scatter`.
- **Pathway enrichment** from gene lists — use `pathway-enrichment-enrichr`.
- Single-panel volcano with no grid — still usable, but a dedicated single-plot workflow may be simpler.

## Required Inputs

- **Input manifest** (TSV): columns `inputFile` and `sampleLabel` listing each differential table and its panel title. See [references/input-manifest-and-layout.md](references/input-manifest-and-layout.md).
- **Output prefix**: path prefix for figure files (no extension); prefer under `agentResults/volcano-grid-plot-<runId>/`.

## Optional Inputs

- **Grid layout**: `--cols`, `--rows` (see reference).
- **Plot types**: `--plotsToPlot volcano`, `ma`, or `volcano,ma` (default both).
- **Column overrides**: `--fcCol`, `--sigCol`, `--nameCol`, `--aveExprCol` (after header inspection).
- **Thresholds**: `--fcCut` (default `2`), `--fdrCut` (default `0.05`).
- **Labels**: `--labelPoints`, `--plotGeneNames`, `--plotDiffGeneMark`, `--identifyRegionByGeneName`.
- **Axis limits**: `--customAbsMaxFC`, `--customMaxP`, `--customAbsMinAveExpr`, `--customAbsMaxAveExpr` (`auto` or numeric).
- Full list: `python scripts/volcano_ma_grid.py --help`.

## Workflow

### Step 1 — Inventory input tables

1. Confirm every path in the manifest exists.
2. Read **only the header row** (and optionally 2–3 data rows) of each file.
3. Note whether data are **gene-level** (symbols/IDs) or **region-level** (coordinates).

### Step 2 — Map columns in every file

Follow [references/column-identification.md](references/column-identification.md):

- **log2FC** (or equivalent fold-change column)
- **p-value / FDR / q-value** (`--sigCol`) for volcano plots
- **gene or region ID** (`--nameCol`)
- **average expression** (`--aveExprCol`) when MA plots are requested

**Do not assume** default script column names (`q.value`, `Region`, `log2AveExpr`) match the files.

### Step 3 — Cross-file consistency check

Before running the plot script:

1. Verify the **same semantic roles** exist in every file (all must have fc + sig for volcano; + ave expr for MA).
2. If column **names differ** but meanings match (e.g. `geneSymbol` vs `symbol`), either:
   - Harmonize: copy tables to the run directory, rename headers to canonical names, write **`column_renames.tsv`** documenting each change, and update the manifest to point at prepared files; **or**
   - If only one name differs across files, prefer harmonization so a single CLI invocation works.
3. If files disagree on identifier type (genes vs regions) or column mapping is ambiguous, **ask the user** — do not guess.

Record harmonization in the run log and report paths to `column_renames.tsv` in the final summary.

### Step 4 — Build the manifest and CLI

1. Write or validate the manifest TSV (`inputFile`, `sampleLabel`).
2. Set `--cols` / `--rows` to match the requested layout.
3. Set `--plotsToPlot` to `volcano`, `ma`, or `volcano,ma`.
4. Pass detected column names explicitly, e.g.:

```bash
python scripts/volcano_ma_grid.py \
  <manifest.tsv> \
  <outputPrefix> \
  --plotsToPlot volcano,ma \
  --fcCol log2FC --sigCol FDR --nameCol geneSymbol --aveExprCol AveExpr \
  --cols 2 --rows 1 \
  --labelPoints EGR1 \
  --runId <YYYYMMDDTHHMMSSZ> \
  --agentRequestFile agent_request.txt \
  --agentWorkflowFile agent_workflow.md
```

Run from the **skill root** (`volcano-grid-plot/`). Use absolute paths in the manifest when the working directory may vary.

### Step 5 — Execute and verify

1. Create `agentResults/volcano-grid-plot-<YYYYMMDDTHHMMSSZ>/`.
2. Write **`agent_request.txt`** with the verbatim user prompt and **`agent_workflow.md`** documenting column mapping, harmonization (if any), manifest path, and the exact CLI you will run.
3. Run the script; pass `--runId`, `--agentRequestFile`, and `--agentWorkflowFile` (or inline `--agentRequest` / `--agentWorkflow`).
4. Confirm exit code **0**.
5. Check for expected `.volcanoGrid.pdf` / `.png` and, if requested, `.MAgrid.pdf` / `.png`.
6. Confirm **`run_metadata.json`**, **`logs/volcano_ma_grid.log`**, and **`logs/commands.log`** exist in the run directory.
7. Scan the log for WARNING/ERROR.
8. Report output paths, thresholds used, column mapping, harmonization, and point to `run_metadata.json` for reproducibility.

## Reproducibility and documentation (CRITICAL)

Every skill run must leave a complete audit trail under the run directory:

1. **`run_metadata.json`** — written by the script: UTC run ID, exact command, resolved inputs, parameters, tool versions (Python, pandas, numpy, matplotlib, seaborn), per-panel up/down counts, and output paths.
2. **`logs/volcano_ma_grid.log`** — full script execution log (no longer written to the working directory).
3. **`logs/commands.log`** — append-only record of the plotting command.
4. **`agent_request.txt`** — verbatim user prompt (via `--agentRequest`, `--agentRequestFile`, or `VOLCANO_GRID_AGENT_REQUEST`).
5. **`agent_workflow.md`** — agent-produced steps: header inspection, column roles, harmonization/`column_renames.tsv`, manifest creation, CLI invocation.
6. **`column_renames.tsv`** / **`prepared/*.tsv`** — when columns were harmonized (agent-produced).

In your summary to the user, list the run directory, key figures, thresholds, column mapping, and **method + versions** from `run_metadata.json`.

## Scripts

| Script | Role |
|--------|------|
| [scripts/volcano_ma_grid.py](scripts/volcano_ma_grid.py) | CLI: read manifest, harmonized tables, draw Volcano and/or MA grids, export GMT gene lists. |

## Output Format

See [references/input-manifest-and-layout.md](references/input-manifest-and-layout.md).

Additionally, when columns were renamed:

| File | Description |
|------|-------------|
| `column_renames.tsv` | Per-file original → canonical column mapping (agent-produced) |
| `prepared/*.tsv` | Optional harmonized copies used for plotting |

Every run also produces a reproducibility bundle (see [references/input-manifest-and-layout.md](references/input-manifest-and-layout.md)):

| File | Description |
|------|-------------|
| `run_metadata.json` | UTC run ID, command, inputs, parameters, tool versions, outputs |
| `logs/volcano_ma_grid.log` | Full script log |
| `logs/commands.log` | Executed command record |
| `agent_request.txt` | Verbatim user prompt (when provided) |
| `agent_workflow.md` | Agent workflow notes (when provided) |

## Quality Checks

Before finishing, verify:

- All input paths existed and were tab-delimited tables.
- Column roles were identified or confirmed by the user.
- Cross-file column semantics are consistent (or harmonized with documented renames).
- Requested plot files exist at 300 DPI (PNG) and PDF.
- Highlighted genes (`--labelPoints`) were found (check log for match counts).
- `run_metadata.json` and `logs/volcano_ma_grid.log` exist in the run directory.
- No CRITICAL errors in `logs/volcano_ma_grid.log`.

## Failure and Escalation

- Missing manifest columns → fix manifest; do not proceed.
- Missing required data columns → report file name and header; ask user or suggest harmonization.
- Zero label matches → warn user; check `--nameCol` vs gene symbol spelling or use `--identifyRegionByGeneName` for peak tables.
- Mixed gene/region identifier types across panels → ask user how to proceed.

## Resources

- [references/column-identification.md](references/column-identification.md): detect fc, p-value, gene/region, ave expr, peak annotation.
- [references/input-manifest-and-layout.md](references/input-manifest-and-layout.md): manifest schema, grid layout, outputs.
- [examples/evaluation-prompts.md](examples/evaluation-prompts.md): example user requests and expected behavior.

## Examples

Bundled RNA-seq tables (GSE202762 EGF timecourse): `examples/GSE202762.DMSO_EGF_*_vs_DMSO_UT.regulation.tsv`. Manifests: `examples/gse202762_timecourse_manifest.tsv`, `examples/gse202762_1hr_2hr_titles_EGR1_manifest.tsv`.

Typical columns: `geneSymbol`, `log2FC`, `FDR`, `AveExpr`.

```bash
--fcCol log2FC --sigCol FDR --nameCol geneSymbol --aveExprCol AveExpr
```
