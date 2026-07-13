# Inputs and outputs

## Contents

- Input modes
- Output directory layout
- Membership matrix schema
- Per-sector files
- Reproducibility record

## Input modes

| `-i` value | Mode | Notes |
|------------|------|-------|
| ≥2 comma-separated `.bed`/`.narrowPeak`/`.broadPeak` | genomic | Order does not matter. Analysis labels from `-n` or `auto`. |
| single `*.gmt` | gene-set | Rows `name <tab> desc <tab> genes…`; ≥2 non-empty sets required. Use `-n` for short analysis labels. |
| single `*.tsv` | manifest → genomic | Two columns `path <tab> label`; no header; `#` comments ignored; labels override `-n`. Prefer short labels in column 2. |

A single BED file is rejected (nothing to overlap). More than 6 inputs disables the Venn diagram
(UpSet still works).

## Output directory layout

All artifacts live under `<outputDir>/<outputPrefix>.intervene/`:

```text
<outputPrefix>.intervene/
├── <outputPrefix>.mergedPeaks_all.bed        # union of all inputs (BED mode)
├── <outputPrefix>.mergedPeaks_matrix.tsv     # membership matrix (BED mode)
├── <outputPrefix>.matrix.tsv                 # membership matrix (GMT mode)
├── <outputPrefix>.<label>.fromMerged.bed     # union regions per input (BED mode)
├── <outputPrefix>.intervene_venn.pdf         # Intervene Venn (if enabled)
├── <outputPrefix>.intervene_upset.pdf        # Intervene UpSet (if enabled)
├── <outputPrefix>.intervene_pairwise_frac.*  # Intervene pairwise (if enabled)
├── sets/                                     # per-sector files from Intervene
├── setsCounted/                              # sets/ prefixed with zero-padded counts
├── originalInputs/                           # staged copies of the original BEDs (BED mode)
├── setLabelsManifest.tsv                     # original_label → analysis_label mapping
├── intersections.gmt                         # per-sector gene sets (GMT mode)
├── originalSets.gmt                          # original gene sets (GMT mode)
├── agent_request.txt                         # verbatim user prompt (when provided)
├── agent_workflow.md                         # agent workflow notes (when provided)
├── run_metadata.json                         # reproducibility record
└── logs/
    ├── intervene_peaks_combine.log           # full script execution log
    └── commands.log                          # Python CLI + every Intervene command
```

Add-on results are placed **inside** this directory when the agent chains the sibling skills:

```text
<outputPrefix>.intervene/
├── setsAnno-<UTC>/                    # genomic-regions-annotation of setsCounted/
├── originalInputsAnno-<UTC>/          # genomic-regions-annotation of originalInputs/
├── pathwayEnrichment_intersections/  # pathway-enrichment-enrichr on filtered intersections
├── pathwayEnrichment_originalFiles/  # pathway-enrichment-enrichr on filtered originals
├── intersections_forPathway.gmt        # filtered GMT fed to Enrichr (intersections)
├── originalFiles_forPathway.gmt        # filtered GMT fed to Enrichr (originals)
├── pathwayEnrichment_intersections_filterManifest.tsv
├── pathwayEnrichment_originalFiles_filterManifest.tsv
└── expressionSummary/                # expression_summary.py output (gated)
```

## Membership matrix schema

BED mode (`<outputPrefix>.mergedPeaks_matrix.tsv`):

| Column | Meaning |
|--------|---------|
| `chrm`, `start`, `end` | Union region coordinates (0-based half-open, BED convention). |
| one column per label | `1` if the region overlaps that input, else `0`. |

GMT mode (`<outputPrefix>.matrix.tsv`): first column `ElementID` (gene), then one 0/1 column per set.

## Per-sector files

Intervene writes one file per combinatorial sector into `sets/`. `setsCounted/` mirrors them with a
`NNNNNNNNN__` prefix giving the region/gene count, so the largest sectors sort first. Use
`setsCounted/` as the input directory when chaining the annotation skill.

## Set label manifest

`setLabelsManifest.tsv` is written for every run:

| Column | Meaning |
|--------|---------|
| `input_index` | 1-based index aligned to input order. |
| `input_identifier` | BED path (genomic mode) or GMT file path (gene-set mode). |
| `original_label` | Label before agent shortening (basename, GMT set name, or manifest label). |
| `analysis_label` | Short label used in filenames, matrices, and Intervene plots. |
| `labels_unchanged` | `true` when `original_label` equals `analysis_label`. |

Agents should shorten long labels before the run (see `SKILL.md`) unless labels are already ≤15
characters and unique, or the user supplied short names.

## Reproducibility record

`run_metadata.json` captures: `run_id` (UTC `YYYYMMDDTHHMMSSZ`), `timestamp_utc`, exact `command`,
`working_directory`, `mode`, resolved `inputs`, `labels` (analysis labels), `original_labels`,
`set_labels_manifest`, `parameters`, `tool_versions`
(Python, Intervene, BEDTools, pybedtools, pandas, numpy), `outputs`, `agent_request_file`,
`agent_workflow_file`, `logs`, a mode-specific `summary`, and an `attribution` block with
`citation_keys`. Pass `--runId`, `--agentRequestFile`, and `--agentWorkflowFile` for a complete
audit trail. Report the genome build separately when annotation/pathway steps run (it is recorded
by those skills' own metadata).

Expression summaries under `expressionSummary/` use the same pattern with
`logs/expression_summary.log` and reproducibility CLI flags on `expression_summary.py`.
