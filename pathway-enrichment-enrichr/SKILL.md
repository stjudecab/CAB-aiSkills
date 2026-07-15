---
name: pathway-enrichment-enrichr
description: >-
  Runs Pathway Enrichment via the public Enrichr API for one gene list or many lists (GMT file or TSV manifest), writes formatted Excel summaries and PDF bar plots for top pathways, and for multi-list runs produces combined summary tables, heatmaps, and dot plots consistent with the enrichr_api GMT workflow. Use when the user asks for Enrichr pathway enrichment, GO/KEGG/Reactome enrichment tables, GMT batch enrichment, multi-sample pathway dot plots or heatmaps, or exporting enrichment results to Excel/PDF.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.9+ with pandas, numpy, requests, matplotlib, seaborn, xlsxwriter; optional rich for pathway_dotplot logging. Needs outbound HTTPS network access to maayanlab.cloud (Enrichr). Writes outputs under a user-specified directory (timestamped run folder by default).
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "1.0.1"
  status: stable
  last_reviewed: "2026-07-15"
---

# Pathway enrichment (Enrichr)

## Purpose

Run a reproducible Enrichr-based pathway enrichment analysis and generate the same classes of artifacts as the historical `sjcab_custom_pathwayEnrichment` automation: merged result tables, Excel workbooks, per-list bar plots, and (for more than one gene list) cross-sample heatmaps and dot plots.

## When to use

- The user provides a **single** plain-text gene list and wants **Excel + PDF** summaries.
- The user provides **multiple** lists via a **GMT** file or a **TSV manifest** of list paths, and wants **batch tables plus comparative figures**.
- The user mentions **Enrichr**, **GO/KEGG/Reactome** style enrichment with **Overlap / Odds Ratio / Combined Score** outputs.

## When not to use

- Offline-only environments with no access to the Enrichr service.
- GSEA preranked / score-based enrichment without a gene list (use a different workflow).
- Requests that only need interpretation of existing tables without rerunning the pipeline.

## Required inputs

- **`outputDir`**: writable directory for outputs (the runner creates `<outputDir>/<runId>/`).
- **`mode`**:
  - **`single`**: `--genes` (one gene per line), `--outPrefix` (safe basename).
  - **`gmt`**: `--gmt` path, `--outPrefix` (batch directory name inside the run folder).
  - **`manifest`**: TSV with **`file`** (or `path`) and **`label`** (or `sample`) columns listing gene list paths and short labels, plus **`outPrefix`**.

## Workflow

1. Confirm network access to Enrichr is acceptable and paths exist.
2. Choose **`libraryPreset`** (default `stjudehg`) or an explicit comma-separated list of Enrichr library names; set **`engine`** to `YeastEnrichr` for yeast.
3. **Record expected list count \(N\)** before running: how many gene lists / GMT sets / manifest rows will be enriched (see [Expected list count](#expected-list-count-n)).
4. Run the helper: `python scripts/run_pathway_enrichment.py` (see [README.md](README.md) for examples).
5. For **`single`**, the helper calls `enrichr_api.py` with `api,sum`, then writes **GenesLists** + **FDR / nominal p** Excel files and **top-10 bar PDFs** next to the merged TSVs.
6. For **`gmt`** or **`manifest`**, the helper uses the existing **`gmt,api,sum`** path; `enrichr_api.py` writes the **multi-sample Excel pack**, **summary TSVs**, **heatmaps**, and invokes **`pathway_dotplot.py`** when present.
7. **Post-run sanity check** (required): list the output directory and verify deliverables match \(N\) and mode ([Post-run sanity check](#post-run-sanity-check)). Do not tell the user the run succeeded until this check passes or gaps are explicitly reported.
8. Return the **run root** path, list key deliverables, point to `run_metadata.json`, and briefly state the sanity-check result (\(N=…\), what was verified).

## Expected list count \(N\)

Determine \(N\) from the inputs **before** enrichment finishes:

| Mode | How to get \(N\) |
|------|------------------|
| **`single`** | Always \(N = 1\). |
| **`gmt`** | Count non-empty data rows in the GMT (one set per line). |
| **`manifest`** | Count data rows in the TSV (one gene-list file per row). |

If the user filters GMTs (e.g. genomic-set-analysis pathway filter), use the **filtered** GMT / filtered list count as \(N\), not the unfiltered source.

## Post-run sanity check

After the helper exits 0, **inspect the files on disk** under the run folder (and the GMT `<outPrefix>/` batch directory when applicable). Do not rely only on logs.

### Always

- `run_metadata.json` exists and records mode, engine, and library preset.
- Non-zero exit / empty stderr alone is not enough; missing per-list artifacts are still a failure.

### Single mode (\(N = 1\))

Expect under the run root (prefix = `--outPrefix`):

- Merged tables: `{outPrefix}.sum.p5`, `{outPrefix}.sum.q5`, `{outPrefix}.sum.all`
- Excel: `{excelStem}.GenesLists.xlsx`, `{excelStem}.fc_q0.05.xlsx`, `{excelStem}.fc_p0.05.xlsx` (or stems documented in metadata)
- Bar PDFs when there were significant rows: `{outPrefix}.sum.p5.pdf`, `{outPrefix}.sum.q5.pdf`
- **Do not** require cross-sample heatmaps or multi-list dotplots (they are not part of single mode).

### GMT / manifest mode (\(N \ge 1\))

Expect a batch directory `<outPrefix>/` under the run root. From a directory listing, verify:

1. **Per-list enrichment tables:** roughly \(N\) samples enriched — e.g. \(N\) `*.sum.all` files (or \(N\) matching sample prefixes). Also expect corresponding `*.sum.p5` / `*.sum.q5` when Enrichr returned hits (empty hit tables can leave sparse `p5`/`q5`; treat missing `*.sum.all` for a listed set as a hard gap).
2. **Combined summaries:** `{gmtStem}.summary_pvals.tsv` and `{gmtStem}.summary_FDRs.tsv` — each should have one column (or clearly labeled field) per list; confirm the number of sample/list columns matches \(N\).
3. **Figures depend on \(N\):**
   - **\(N = 1\)**: per-list bar/Excel-style outputs may exist; **cross-sample heatmaps and multi-sample dotplots are optional / usually absent** — do not fail solely for missing `*.heatmap.pdf` or `*.dotplot.pdf` when only one list was run.
   - **\(N \ge 2\)**: expect comparative figures when enrichment returned usable pathways:
     - Heatmaps: `*.summary_pvals.top10.heatmap.pdf` and `*.summary_FDRs.top10.heatmap.pdf` (and Up/Down variants only if that analysis produced separate up/down columns).
     - Dotplots (if `pathway_dotplot.py` is present): matching `*.summary_*.top10.dotplot.pdf` / `.png`.
4. **Spot-check contents:** for any required heatmap/dotplot, confirm non-trivial file size (>0) and that companion TSVs such as `*.plotted_plot_status.tsv` (dotplot) or summary TSVs list all \(N\) samples when \(N \ge 2\).

### How to report failures

If any required artifact is missing or \(N\) does not match (e.g. only 3 `*.sum.all` when \(N=5\)):

1. State the expected \(N\) and which files/columns were checked.
2. List the missing or mismatched paths.
3. Do **not** present the run as complete; offer to re-run or diagnose (Enrichr empty results vs true pipeline skip).

## Scripts (authoritative)

| Script | Role |
|--------|------|
| [scripts/run_pathway_enrichment.py](scripts/run_pathway_enrichment.py) | Modes, run-scoped output directory, single-list Excel/bar post-processing, manifest→GMT conversion. |
| [scripts/enrichr_api.py](scripts/enrichr_api.py) | Enrichr upload, per-library download, `sum` merge, GMT orchestration, multi-sample figures. |
| [scripts/pathway_dotplot.py](scripts/pathway_dotplot.py) | Cross-sample dot plots (invoked from GMT batch flow). |
| [scripts/enrichment_postprocess.py](scripts/enrichment_postprocess.py) | Single-sample Excel + bar plots only. |

## Output layout

- **Run root**: `<outputDir>/<runId>/` (UTC timestamp by default) contains `run_metadata.json`.
- **Single mode**: `<outPrefix>.sum.p5`, `.sum.q5`, `.sum.all`, Excel `*.GenesLists.xlsx`, `*.fc_q0.05.xlsx`, `*.fc_p0.05.xlsx`, bar PDFs `*.sum.p5.pdf`, `*.sum.q5.pdf`.
- **GMT / manifest batch**: directory `<outPrefix>/` under the run root with per-set tables, `*.summary_pvals.tsv`, `*.summary_FDRs.tsv`, heatmap PDFs (`*.summary_*.top10.heatmap.pdf`), and dotplot PDF/PNG when `pathway_dotplot.py` is available (shipped next to `enrichr_api.py` in this skill). Heatmaps and dot plots share a threshold-aware stepped colormap (`significance_colormap.py`; grey below `--significanceThreshold`).

## Quality checks

- Non-zero exit from the helper is a failure; read stderr / `enrichr_api.*.log` in the run directory.
- Confirm `run_metadata.json` records the mode, engine, and library preset.
- **Always run the [Post-run sanity check](#post-run-sanity-check)** against directory listings: expected list count \(N\) must match per-list outputs; for \(N \ge 2\) require combined summary tables and heatmap/dotplot figures when pathways were enriched; for \(N = 1\) do not require cross-sample heatmaps/dotplots.
- For multi-list runs, confirm `*.summary_pvals.tsv` / `*.summary_FDRs.tsv` exist and their sample columns equal \(N\), and that there are \(N\) per-list `*.sum.all` (or equivalent) files when enrichment returned results.

## Safety and limitations

- **Do not** run with `--overwrite` unless the user explicitly wants to reuse a run directory.
- Enrichr is a **public** service; do not send patient-identifiable or otherwise sensitive data without user approval.
- Large GMT batches can be **slow** and **rate-limited**; keep runs scoped.
- Result interpretation (biology) is out of scope unless the user asks for a readout of the tables only.

## Attribution

Report credits in **three layers** (see [references/citations.md](references/citations.md) and [docs/attribution.md](../docs/attribution.md)):

1. **Method:** **Enrichr** web service — Kuleshov et al., *NAR* 2016 (primary); Chen et al., *BMC Bioinformatics* 2013 (original tool).
2. **Bundled API client:** `enrichr_api.py` — **Beisi Xu** (primary author per file header); contributions from Wojciech Rosikiewicz as noted in-header.
3. **Skill package:** CAB-aiSkills `pathway-enrichment-enrichr` — credit **skill author(s)** from [AUTHORS.md](../AUTHORS.md) and `metadata.author` in this file (orchestration only; **not** Enrichr).

`run_metadata.json` includes `citation_keys` and an `attribution` block. Do not cite the skill packager as the author of Enrichr.

## Further reading

- [references/citations.md](references/citations.md) — layered attribution and copy-paste citations.
- Method and file-format notes: [references/methods.md](references/methods.md)
- Human-oriented install and command examples: [README.md](README.md)
