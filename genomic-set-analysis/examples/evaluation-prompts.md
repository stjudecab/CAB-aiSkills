# Evaluation prompts

Expected agent behavior for representative and edge-case requests. Bundled example inputs live in
this folder (`peaksFactorA/B/C.bed`, `geneSets.gmt`, `inputManifest.tsv`, `expressionMatrix.tsv`,
`expressionMetadata.tsv`).

## 1. Standard success — overlap only

**Prompt:** "Overlap the three BED files in `genomic-set-analysis/examples` and make a Venn and
UpSet plot."

**Expected:** Run `intervene_peaks_combine.py -i examples/peaksFactorA.bed,peaksFactorB.bed,peaksFactorC.bed
-o factorOverlap --outputDir agentResults --toPlot venn,upset`. Report sector counts, output paths,
and Intervene/BEDTools versions from `run_metadata.json`. Do not run annotation or pathway steps.

## 2. Overlap + annotation + pathway (genome provided)

**Prompt:** "Overlap those three BEDs, annotate against hg38, and run pathway enrichment for each
intersection and for the original files."

**Expected:** Run the overlap; then chain `genomic-regions-annotation` on `setsCounted/` and on
`originalInputs/` with `--genome hg38`; filter GMTs with `filter_gmt_for_pathway.py` (default:
top 10 intersections with ≥5 genes; originals with ≥5 genes only); then chain
`pathway-enrichment-enrichr` on the filtered GMTs, writing `pathwayEnrichment_intersections/`
and `pathwayEnrichment_originalFiles/` inside the intervene directory. Confirm Enrichr network
access. Record commands, versions, the genome build, and which sectors were included/excluded.

## 3. Missing genome build (ambiguity)

**Prompt:** "Overlap these peaks and tell me the shared pathways."

**Expected:** Run the overlap, but **ask which genome build** before annotation/pathway. Do not
assume hg38. State that pathway enrichment needs the genome for annotation.

## 4. Motif enrichment requested (out of scope)

**Prompt:** "Also run HOMER motif enrichment on each intersection."

**Expected:** Explain that motif enrichment is **not available yet** in this skill and is planned;
do not run HOMER as a workaround. Offer the available steps instead.

## 5. deeptools requested (out of scope)

**Prompt:** "Make deeptools tornado plots for the top intersections."

**Expected:** Explain deeptools heatmaps are **not available yet** (planned); do not improvise.

## 6. Expression without conditions (missing input)

**Prompt:** "Show expression of the genes in each intersection using `expressionMatrix.tsv`."

**Expected:** Ask for a **per-sample condition** definition (or `expressionMetadata.tsv`) before
running `expression_summary.py`; do not guess conditions.

## 7. GMT input mode

**Prompt:** "Overlap the gene sets in `examples/geneSets.gmt` and run Enrichr on each intersection
and each original set."

**Expected:** Run the overlap in gene-set mode (produces `intersections.gmt` and `originalSets.gmt`),
filter with `filter_gmt_for_pathway.py` (top 10 intersections with ≥5 genes; originals with
≥5 genes), then chain `pathway-enrichment-enrichr` on the filtered GMTs (no annotation needed).
No genome build required.

## 8. Single BED (invalid)

**Prompt:** "Overlap `examples/peaksFactorA.bed`."

**Expected:** Refuse: overlap needs ≥2 region files, or a GMT/TSV. Ask for more inputs.

## 9. Long filenames — agent should shorten labels

**Prompt:** "Overlap
`GSE202762_DMSO_48h_rep1_peaks.bed`, `GSE202762_DMSO_48h_rep2_peaks.bed`, and
`GSE202762_EGF_48h_rep1_peaks.bed`."

**Expected:** Recognize that auto labels would be too long. Derive short unique analysis labels
(e.g. `DMSO_r1`, `DMSO_r2`, `EGF_r1` or `DMSO1`, `DMSO2`, `EGF1`), pass them via `-n` or a
manifest TSV, run the overlap, and point the user to `setLabelsManifest.tsv` showing
`original_label` → `analysis_label`.

## 10. Pathway enrichment — user overrides default filter

**Prompt:** "Run pathway enrichment on **all** intersection sectors, even small ones."

**Expected:** Skip the default top-10 / ≥5-gene filter (or set `--minGenes 1 --topN 0`), tell the
user you are overriding the default policy, and record that override in the summary.

## 11. Pairwise significance with manual universe size

**Prompt:** "Overlap the example BEDs and test whether pairwise overlaps are significant. Use
a background population of 50000 regions for the Fisher / fold-enrichment calculations."

**Expected:** Run `intervene_peaks_combine.py` with `--pairwiseSignificance True` (default) and
**`--pairwiseSignificanceUniverse 50000`**. Confirm `pairwiseSignificance/` contains fold
enrichment / direction / Fisher matrices and that `pairwise.summary.long.tsv` records
`universe_N=50000` with `universe_source=manual`. Report over- vs underrepresented pairs from
`enrichment_direction`. Do not invent a genome-wide N if the user did not give one — default is
`auto` (analysis union).

## 12. Pairwise significance — default auto universe

**Prompt:** "Are any of these gene sets significantly overlapping each other?"

**Expected:** Run GMT/BED overlap with pairwise significance left at default
(`--pairwiseSignificanceUniverse auto`). Explain that N is the analysis union (merged peaks or
unique genes across inputs), point to `pairwiseSignificance/`, and summarize significant
pairs (FDR) plus fold enrichment / direction. Mention the user can pass a known background size
via `--pairwiseSignificanceUniverse <integer>` if they have one.
