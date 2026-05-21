---
name: pathway-enrichment-enrichr
description: >-
  Runs Pathway Enrichment via the public Enrichr API for one gene list or many lists (GMT file or TSV manifest), writes formatted Excel summaries and PDF bar plots for top pathways, and for multi-list runs produces combined summary tables, heatmaps, and dot plots consistent with the enrichr_api GMT workflow. Use when the user asks for Enrichr pathway enrichment, GO/KEGG/Reactome enrichment tables, GMT batch enrichment, multi-sample pathway dot plots or heatmaps, or exporting enrichment results to Excel/PDF.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.9+ with pandas, numpy, requests, matplotlib, seaborn, xlsxwriter; optional rich for pathway_dotplot logging. Needs outbound HTTPS network access to maayanlab.cloud (Enrichr). Writes outputs under a user-specified directory (timestamped run folder by default).
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "1.0.0"
  status: stable
  last_reviewed: "2026-05-01"
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
3. Run the helper: `python scripts/run_pathway_enrichment.py` (see [README.md](README.md) for examples).
4. For **`single`**, the helper calls `enrichr_api.py` with `api,sum`, then writes **GenesLists** + **FDR / nominal p** Excel files and **top-10 bar PDFs** next to the merged TSVs.
5. For **`gmt`** or **`manifest`**, the helper uses the existing **`gmt,api,sum`** path; `enrichr_api.py` writes the **multi-sample Excel pack**, **summary TSVs**, **heatmaps**, and invokes **`pathway_dotplot.py`** when present.
6. Return the **run root** path, list key deliverables, and point to `run_metadata.json` for the exact command context.

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
- **GMT / manifest batch**: directory `<outPrefix>/` under the run root with per-set tables, `*.summary_pvals.tsv`, `*.summary_FDRs.tsv`, heatmap PDFs, and dotplot PDF/PNG when `pathway_dotplot.py` is available (shipped next to `enrichr_api.py` in this skill).

## Quality checks

- Non-zero exit from the helper is a failure; read stderr / `enrichr_api.*.log` in the run directory.
- Confirm `run_metadata.json` records the mode, engine, and library preset.
- For multi-list runs, confirm at least one of `summary_pvals.tsv` or per-sample `*.sum.all` exists when enrichment returned results.

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
