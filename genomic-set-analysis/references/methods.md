# Methods and algorithm

## Contents

- Scientific intent
- Order-independence and its caveat
- Region (BED) mode
- Gene-set (GMT) mode
- Manifest (TSV) mode
- Pairwise Fisher overlap significance
- Bundled scripts
- Expression module details
- Numerical policy

## Scientific intent

Given two or more peak/region sets or gene sets, define **combinatorial sets** (A-only, A∩B,
A∩B∩C, …), visualize the overlap structure (Venn / UpSet / pairwise), test whether each
**pairwise** overlap is surprising under a discrete universe (Fisher exact), and enable
downstream questions such as *which genes and pathways are active near regions shared by
factor X and Y but not Z?*

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
3. Optionally (default on) run pairwise Fisher significance on the `*.fromMerged.bed` files →
   `pairwiseSignificance/` (see below).
4. Run Intervene `venn` (≤6 inputs), `upset`, and/or `pairwise` on the `*.fromMerged.bed` files
   with `--type genomic --save-overlaps`.
5. Copy Intervene's per-sector `sets/` into `setsCounted/` with a zero-padded region-count prefix
   (`000000123__<name>.bed`) so the largest sectors sort first and selection is deterministic.
6. Stage the original inputs into `originalInputs/` (copies, never modifying the source) so the
   annotation and pathway add-ons can operate on the originals as well as the sectors.

## Gene-set (GMT) mode

Triggered when `-i` is a single `*.gmt`. Each row is `setName <tab> description <tab> gene1 gene2 …`.
The script builds the union of genes, writes a membership matrix, optionally runs pairwise Fisher
significance (default on), runs Intervene with `--type list`, copies `sets/` to `setsCounted/`, and
writes two convenience files for pathway enrichment:

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

## Pairwise Fisher overlap significance

Controlled by `--pairwiseSignificance` (default **`True`**), `--pairwiseSignificanceFigSize`
(default `10,8`), and `--pairwiseSignificanceUniverse` (default **`auto`**, also `-1`).

This is **independent** of Intervene `--toPlot pairwise` (descriptive overlap **fractions** only).

### Algorithm

1. Universe size \(N\):
   - `auto` / `-1`: BED = `|mergedPeaks_all|`; GMT = unique genes across input sets.
   - Positive integer: user-supplied background (e.g. all protein-coding genes).
2. For each unordered pair \((A, B)\):
   - BED: count \(a = |A \cap B|\) with `pybedtools` `intersect(wa=True, u=True)` on **`fromMerged`** BEDs.
   - GMT: \(a\) via Python `set` intersection.
   - Contingency: \(b=\|A\|-a\), \(c=\|B\|-a\), \(d=N-\|A\|-\|B\|+a\).
   - `scipy.stats.fisher_exact([[a,b],[c,d]], alternative="two-sided")` → odds ratio and p-value.
   - Expected \(E=\|A\|\|B\|/N\); fold enrichment \(\mathrm{FE}=a/E\); direction from FE
     (`overrepresented` / `underrepresented` / `equal`).
   - Jaccard \(= a / \|A \cup B\|\).
3. Benjamini–Hochberg FDR over unique unordered pairs \(n(n-1)/2\); fill a symmetric matrix.
4. Write TSVs and one clustermap per statistic under `pairwiseSignificance/`.

### Clustermap transforms

| Plot file | Values shown |
|-----------|--------------|
| `pairwise.overlap_count.clustermap.*` | Raw overlap counts |
| `pairwise.jaccard.clustermap.*` | Jaccard; **diagonal masked** |
| `pairwise.log2_odds_ratio.clustermap.*` | \(\log_2(\mathrm{OR})\); OR clipped; diagonal = 0; RdBu_r centered at 0 |
| `pairwise.fold_enrichment.clustermap.*` | **Raw** fold enrichment \(a/E\) (not log2); diagonal masked |
| `pairwise.fisher_pvalue.clustermap.*` | \(-\log_{10}(p)\); diagonal = 0 |
| `pairwise.fisher_fdr.clustermap.*` | \(-\log_{10}(\mathrm{FDR})\); diagonal = 0 |

Interpretation: FE > 1 / positive \(\log_2(\mathrm{OR})\) = enrichment; FE < 1 / negative
\(\log_2(\mathrm{OR})\) = depletion. Large \(-\log_{10}(\mathrm{FDR})\) = more surprising after BH.

### Limitations

- Default universe is the analysis-specific merged-peak or gene union, not the full genome /
  curated gene background, unless the user sets `--pairwiseSignificanceUniverse`.
- BED tests count **merged intervals**, matching Intervene’s `fromMerged` view.
- Pairwise set-vs-set only (not combinatorial Upset-sector enrichment).

## Bundled scripts

### `intervene_peaks_combine.py`

- **Args:** `-i/--inputPeaks` (required), `-n/--names`, `-o/--outputPrefix`, `--outputDir`,
  `--figSize`, `--toPlot`, `--mbColor`, `--sbColor`, `--pairwiseSignificance`,
  `--pairwiseSignificanceFigSize`, `--pairwiseSignificanceUniverse`, `--overwrite`, `--dryRun`.
- **Outputs:** membership matrix, merged/`fromMerged` BEDs, Intervene plots, `pairwiseSignificance/`,
  `sets/`, `setsCounted/`,
  `originalInputs/` (BED mode) or `intersections.gmt`/`originalSets.gmt` (GMT mode), `logs/commands.log`,
  and `run_metadata.json` (UTC run ID, command, inputs, params, tool versions).
- **Dependencies:** Intervene CLI + BEDTools for plotting; `pybedtools` for BED merge/intersect;
  `pandas`, `numpy`, `scipy`, `seaborn`, `matplotlib` (significance clustermaps). GMT mode with
  `--toPlot ignore` needs neither Intervene nor pybedtools for the matrix step; significance still
  needs scipy (and seaborn for plots).
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
