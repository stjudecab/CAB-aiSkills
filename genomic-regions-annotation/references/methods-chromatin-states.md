# Methods: chromatin-state annotation

## Contents

- Purpose
- Background (ChromHMM and Segway)
- Assignment approach
- Aggregation modes
- Precalculated vs custom models
- Download and preprocessing
- Cache and run reproducibility
- Outputs
- Optional heatmap post-processing
- Manuscript methods text
- Limitations

## Purpose

Annotate peaks or genomic intervals to chromatin states that summarize combinatorial histone-mark patterns. Unlike gene or feature annotation, this context depends on the **cell type / biosample** of the chosen segmentation model and does **not** use GENCODE gene structure.

Chromatin-state annotation is a **separate skill branch**. After running `BEDinContext.py`, do **not** run `OrganizeAnnotationResults.py`.

## Background (ChromHMM and Segway)

### Roadmap / ChromHMM

The Roadmap Epigenomics Project modeled chromatin states across 127 human epigenomes with ChromHMM (multivariate HMM) using five core histone marks (H3K4me1, H3K4me3, H3K36me3, H3K9me3, H3K27me3), producing 15 core states (for example Active TSS, Enhancers, Quiescent/Low). Roadmap dense BED browser files are available for hg19 and hg38-lifted coordinates.

State labels used by this skill for Roadmap models are stored in `references/chromatin-states/state2name.tsv` (E1–E15).

### ENCODE / Segway

Segway annotations for many human cell types are available from ENCODE (see Libbrecht et al., PMID:31462275). Native Segway BED files use hg19 coordinates and state labels such as `6_Quiescent`. This skill converts them to ChromHMM-compatible dense BED (integer state IDs, optional liftOver to hg38, merge of adjacent same-state intervals). Friendly names are in `references/chromatin-states/ENCODE_state2name.tsv` (E1–E9).

### Choosing a biologically relevant model

Use `references/chromatin-states/availableModelsLookup.tsv` (plus Roadmap/Segway metadata) to recommend the closest ChromHMM (`E###`) and/or Segway (`ENCFF*`) collection for the user’s sample description. Prefer careful biological reasoning; confirm with the user before annotating. Empty fields are marked `---`.

If no model matches, select the closest tissue/lineage reference, and consider multi-biosample browsers such as Epilogos for exploratory comparison.

## Assignment approach

Peaks of interest (POI) are overlapped with all intervals in the selected chromatin-state collection.

If a peak overlaps more than one state, the peak is assigned to the state with the **largest cumulative overlapping base-pair length**.

Per-peak state assignments are written as `*.bed2states.bed`. Summary tables count either peaks (`regions`) or overlapped base pairs (`bp`).

## Aggregation modes

| Mode | Behavior | Output location |
|------|----------|-----------------|
| `regions` (**default**) | Each input interval is assigned once to its best (largest bp overlap) state, then counted. Primary peak-level summary. | Top of `-o` (e.g. `BEDinContext/`) |
| `bp` | Sum all overlapping base pairs per state across intervals (no squashing). Secondary. | `<out>/aggregationByBp/` |
| `both` | Write both summaries / plots | regions at top level; bp under `aggregationByBp/` |

Agent default: omit `-a` (or pass `-a regions`). Do not use `-a both` unless requested. Base-pair outputs are isolated in `aggregationByBp/` so they are not mistaken for peak counts. Per-peak `*.bed2states.bed` files always remain at the top level of `-o`.

## Precalculated vs custom models

| Source | Genome | Agent action |
|--------|--------|--------------|
| Roadmap ChromHMM (`E001`…`E129`) | hg19 or hg38 (ask user) | `prepare_chromatin_model.py --collection E123 --genome hg38` |
| Segway ENCODE (`ENCFF*`) | native hg19; request hg38 → liftOver | `prepare_chromatin_model.py --collection ENCFF089AXD --genome hg38` |
| Custom user ChromHMM dense BED | any (as-is) | Skip prepare; pass user dense BED + `--state2name` |

Custom models must match the dense BED layout shown in `tests/fixtures/toy_dense.bed` (track header + chrom/start/end/state/score/strand/thickStart/thickEnd/itemRgb) and a two-column state2name TSV (`E1\tName`).

## Download and preprocessing

### Roadmap ChromHMM

1. Download `{Collection}_15_coreMarks_hg38lift_dense.bed.gz` or `{Collection}_15_coreMarks_dense.bed.gz` using URLs in `RoadmapCollectionsMetadata.tsv`.
2. Rewrite column 4 from `9_Het` / `15_Quies` to numeric `9` / `15` (required by `BEDinContext.py`).
3. Cache as `cache/{Collection}_{genome}_dense.bed` plus `.model_meta.json`.

### Segway ENCODE

1. Download the accession’s `.bed.gz` (File download / S3 / Azure URL).
2. Map Segway state names to integer IDs 1–9.
3. If target genome is hg38, liftOver with `references/chromatin-states/hg19ToHg38.over.chain` (`ucsc-liftover`).
4. Merge adjacent intervals with identical state and color.
5. Cache as `cache/{ENCFF*}_{genome}_dense.bed`.

Only final dense BED (+ metadata sidecar) are retained in `cache/` (gitignored). Intermediates are discarded.

## Cache and run reproducibility

- Skill-local cache: `cache/{collection}_{genome}_dense.bed`
- Each annotation run under `agentResults/genomic-regions-annotation-<runId>/` must copy the **exact model dense BED**, `state2name` file, and model metadata used for that run.
- Scripts write `run_metadata.json`, `logs/<script>.log`, and `logs/commands.log`.
- Record genome build, collection ID, friendly biosample name, preprocess steps, and aggregation mode.

## Outputs

From `BEDinContext.py` (under the chosen `-o` directory inside the run dir):

| Artifact | Meaning |
|----------|---------|
| `*.bed2states.bed` | Per-peak best state assignment (top-level `-o` only) |
| `statsCombined.num.tsv` | Absolute region counts per state × input BED |
| `statsCombined.frc.tsv` | Column-normalized region fractions |
| `statsCombined.list.tsv` | Long-form counts with percentages (from stacked-bar prep) |
| `*.piePlot.[pdf,png]` | Per-file pie chart (region counts) |
| `*.barPlot.[pdf,png]` | Per-file bar chart (region counts) |
| `statsCombined.stackedBar.[pdf,png,html]` | Multi-file stacked bar (HTML semi-interactive) |
| `aggregationByBp/*` | Optional bp-aggregation mirrors of the TSV/plot set above (only with `-a bp` or `-a both`) |

Optional: `plot_chromatin_state_heatmap.py` on `statsCombined.frc.tsv` for a publication heatmap.

## Optional heatmap post-processing

```bash
python scripts/plot_chromatin_state_heatmap.py \
  --inputFile <runDir>/BEDinContext/statsCombined.frc.tsv \
  --outputPrefix <runDir>/chromatin_state_fractions \
  --outputDir <runDir> \
  --runId <runId>
```

## Manuscript methods text

> Peaks were annotated to chromatin states by overlapping each peak with a ChromHMM (Roadmap Epigenomics) or Segway (ENCODE) segmentation for biosample `<Name>` (collection `<Collection>`, genome `<hg19|hg38>`). When a peak overlapped multiple states, it was assigned to the state with the largest overlapping base-pair length. Summary tables reported the number of peaks (and/or overlapping base pairs) per state. Roadmap dense BED files were preprocessed so that the fourth column contained numeric state IDs only. Segway annotations (hg19) were converted to integer state IDs, lifted to hg38 when required with UCSC liftOver, and adjacent same-state intervals were merged before annotation. Annotation used BEDTools intersections via pybedtools.

## Limitations

- Chromatin state is biosample-specific; a mismatched cell-type model can mislead interpretation.
- Largest-overlap assignment discards secondary overlaps for the primary peak label.
- Segway liftOver can leave unmapped intervals; report unmapped counts when relevant.
- Precalculated models are human-only (hg19/hg38). Custom models are used as-is for other species/builds.
