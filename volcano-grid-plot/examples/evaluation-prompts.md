# Evaluation Prompts

## Timecourse — natural chronological order

**User:** Plot a volcano grid for all GSE202762 EGF timepoints in natural order (10min, 20min, 1hr, 2hr, 4hr).

**Expected agent behavior:**

1. Load skill; read headers of all `examples/GSE202762.*.regulation.tsv`.
2. Map: `log2FC`, `FDR`, `geneSymbol`.
3. Build [gse202762_timecourse_manifest.tsv](gse202762_timecourse_manifest.tsv) with `sampleLabel` = `10min`, `20min`, `1hr`, `2hr`, `4hr` in that order.
4. Run `--plotsToPlot volcano --rows 1` (five columns auto).
5. Outputs: `*.volcanoGrid.pdf` and `.png`.

## Custom titles and EGR1 — volcano + MA

**User:** Volcano and MA grids for GSE202762 1h and 2h with readable contrast titles; highlight EGR1.

**Expected:**

- [gse202762_1hr_2hr_titles_EGR1_manifest.tsv](gse202762_1hr_2hr_titles_EGR1_manifest.tsv) with titles such as `EGF 1h vs DMSO UT`.
- `--plotsToPlot volcano,ma --cols 1 --rows 2 --labelPoints EGR1 --aveExprCol AveExpr`.
- Both `volcanoGrid` and `MAgrid` artifacts; log confirms EGR1 found in each panel.

## Two-panel volcano 2×1

**User:** Create a volcano grid with two columns and one row from two GSE202762 regulation tables.

**Expected:**

- Manifest with two files; `--cols 2 --rows 1`; volcano only.

## Missing column ambiguity

**User:** Plot these three DESeq2 files (headers differ: `log2FoldChange` vs `log2FC`).

**Expected:**

- Detect mismatch; harmonize to canonical `log2FC` in `prepared/` copies.
- Write `column_renames.tsv`; explain to user before plotting.

## Region labeling by gene

**User:** Highlight TP53 on ChIP peak differential table (regions as IDs).

**Expected:**

- `--nameCol Region` (or reconstructed region column).
- `--identifyRegionByGeneName Yes --labelPoints TP53`.
- Verify `Gene_2kb` (or documented equivalent) exists; else ask user.

## Out of scope

**User:** Correlate two RNA-seq files with KDE scatter.

**Expected:** Do not use this skill; suggest `kde-correlation-scatter`.
