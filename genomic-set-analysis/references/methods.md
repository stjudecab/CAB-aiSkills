# Methods and algorithm

## Contents

- Scientific intent
- Order-independence and its caveat
- Region (BED) mode
- Gene-set (GMT) mode
- Manifest (TSV) mode
- Bundled scripts
- Expression module details
- Numerical policy

## Scientific intent

Given two or more peak/region sets or gene sets, define **combinatorial sets** (A-only, A∩B,
A∩B∩C, …), visualize the overlap structure (Venn / UpSet / pairwise), and enable downstream
questions such as *which genes and pathways are active near regions shared by factor X and Y
but not Z?*

## Order-independence and its caveat

Naive pairwise intersection with tools like BEDTools/Intervene is **order-dependent**: "regions
of A that overlap B" can differ in count from "regions of B that overlap A" because one region
can overlap several regions in the other set. To make the result independent of input order,
this workflow first builds a **union** of all inputs (via `pybedtools` `cat(..., postmerge=True)`),
then marks which original inputs each union region belongs to.

**Caveat:** because analysis is on the union of merged regions, the total number of regions can be
**smaller** than any single pairwise overlap count. This is expected and must be kept in mind when
interpreting absolute numbers. It is a deliberate trade-off for reproducibility.

## Region (BED) mode

Triggered when `-i` lists ≥2 region files (or a TSV manifest resolves to them).

1. Merge all inputs into `<prefix>.mergedPeaks_all.bed` (union).
2. For each input, intersect the union with that input (`wa=True, u=True`) → `<prefix>.<label>.fromMerged.bed`,
   and set the membership flag in `<prefix>.mergedPeaks_matrix.tsv` (1 = present, 0 = absent).
3. Run Intervene `venn` (≤6 inputs), `upset`, and/or `pairwise` on the `*.fromMerged.bed` files
   with `--type genomic --save-overlaps`.
4. Copy Intervene's per-sector `sets/` into `setsCounted/` with a zero-padded region-count prefix
   (`000000123__<name>.bed`) so the largest sectors sort first and selection is deterministic.
5. Stage the original inputs into `originalInputs/` (copies, never modifying the source) so the
   annotation and pathway add-ons can operate on the originals as well as the sectors.

## Gene-set (GMT) mode

Triggered when `-i` is a single `*.gmt`. Each row is `setName <tab> description <tab> gene1 gene2 …`.
The script builds the union of genes, writes a membership matrix, runs Intervene with `--type list`,
copies `sets/` to `setsCounted/`, and writes two convenience files for pathway enrichment:

- `intersections.gmt` — one entry per combinatorial sector (from Intervene `sets/`).
- `originalSets.gmt` — the original input gene sets.

## Manifest (TSV) mode

Triggered when `-i` is a single `*.tsv`: two columns `path <tab> label` (no header; `#` comments
ignored). Paths are resolved to absolute, existence-checked, and labels override `--names`. Prefer
short labels in the manifest when basenames are long; see `SKILL.md` and `setLabelsManifest.tsv`.

### Short analysis labels

Labels feed directly into output filenames and combinatorial sector names. Agents should shorten
long basenames or GMT set names to ≤15 characters when they are not already short and unique,
passing them via `-n` or the manifest. The script writes `setLabelsManifest.tsv` with
`original_label` and `analysis_label` for every run. GMT mode accepts `-n` to remap long GMT set
names to short analysis labels while preserving originals in the manifest.

## Bundled scripts

### `intervene_peaks_combine.py`

- **Args:** `-i/--inputPeaks` (required), `-n/--names`, `-o/--outputPrefix`, `--outputDir`,
  `--figSize`, `--toPlot`, `--mbColor`, `--sbColor`, `--overwrite`, `--dryRun`.
- **Outputs:** membership matrix, merged/`fromMerged` BEDs, Intervene plots, `sets/`, `setsCounted/`,
  `originalInputs/` (BED mode) or `intersections.gmt`/`originalSets.gmt` (GMT mode), `logs/commands.log`,
  and `run_metadata.json` (UTC run ID, command, inputs, params, tool versions).
- **Dependencies:** Intervene CLI + BEDTools for plotting; `pybedtools` for BED merge/intersect;
  `pandas`, `numpy`. GMT mode with `--toPlot ignore` needs neither Intervene nor pybedtools.
- **Safety:** fails fast on missing inputs, single-BED input, mismatched labels, malformed figure
  size, non-zero Intervene exit, or an existing output directory without `--overwrite`.

### `expression_summary.py`

Portable, seaborn-based reimplementation of the historical PyComplexHeatmap expression worker
(documented behavior change: lighter heatmap engine, no LSF).

- **Args:** `--geneSetsGmt` (required), `--exprMatrixFile` (required), `--outputDir` (required),
  `--exprGeneNameCol`, `--exprColumnsToDrop`, `--exprSampleCondition` **or** `--metadataFile`
  (one is required), `--exprMinMeanExpression`, `--exprYaxis`, `--exprPalette`, `--exprFigSize`,
  `--overwrite`.
- **Outputs:** per-flavor expression TSVs (`exprMatrix`, `exprMatrixLog10`, `exprMatrixZ`), boxplots
  (hue-by-condition and merged `noHue`), clustered heatmaps (raw and z), `geneSetMembershipCounts.tsv`,
  `run_metadata.json`.

## Expression module details

Region-level sectors are mutually exclusive, but nearby-gene annotation occurs after the region
split, so one gene can belong to several sectors. Rows are duplicated across sectors and renamed
`<gene>.<set>` so every membership is preserved in tables and figures. Units/scale:

- `exprMatrix` — raw values in the units named by `--exprYaxis` (e.g. TPM/FPKM), linear space.
- `exprMatrixLog10` — `log10(x + 1)`.
- `exprMatrixZ` — per-gene z-score of the log10 values (each gene standardized independently across samples).

Zero-variance rows are dropped before clustering (no dendrogram signal); this is a display step,
not silent data coercion.

## Numerical policy

The expression module treats NaN/Inf in the parsed matrix as a hard error (`assertFinite`) and
reports how many rows are affected instead of coercing them. The only intentional
zero-fill is on the per-gene z-score of constant rows (mathematically undefined), matching the
original tool's behavior and documented here.
