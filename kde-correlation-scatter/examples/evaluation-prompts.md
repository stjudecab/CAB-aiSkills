# Evaluation Prompts

## Contents

- Directional p-value (RNA-seq vs RNA-seq)
- Log2FC scatter (ChIP-seq vs RNA-seq)
- Region-vs-region log2FC (ChIP-seq vs ChIP-seq, no cutoff)
- Region-vs-region log2FC (with weak cutoff)
- Region-vs-region directional p-value
- Rank-vs-rank correlation
- Ambiguous column names (edge case)
- Missing input (failure case)
- Out-of-scope request

---

## 1. Directional p-value (RNA-seq vs RNA-seq)

### User prompt variants

> "I would like you to plot 2D scatter plot for file X and Y, both RNA-seq data based on significance."

> "Plot a 2D scatter for the DEG files X and Y, based on p-value."

> "Generate KDE correlation plot for files X and Y, both RNA-seq data based on directional p."

### Expected agent behavior

1. Recognize this as **anno2anno** mode with **directional p-value transform** (`-dt True`).
2. Read headers of both files. Identify `log2FC` (or equivalent) as metric, `P.Value` (or equivalent) as significance, `geneSymbol` (or equivalent) as gene identifier — independently per file.
3. Set `-dt True`, `-sx <significance_X>`, `-sy <significance_Y>`.
4. Set a p-value threshold, e.g. `-t 0.05`.
5. Infer labels like `"<contrast_X> -log10(p-value)"` and `"<contrast_Y> -log10(p-value)"`.
6. Set `-qd genes`.

### Example command (with bundled test data)

```bash
python scripts/plot_kde_correlation.py \
  -ix examples/RNAseq_clone_vs_CMY.regulation.tsv \
  -mx log2FC \
  -gx geneSymbol \
  -lx "RNAseq_clone_vs_CMY -log10(p-value)" \
  -sx "P.Value" \
  -iy examples/SRM872549_diff.ERCC_clones_vs_ERCC_CMY.regulation.tsv \
  -my log2FC \
  -gy geneSymbol \
  -ly "SRM872549-ERCC_clones_vs_ERCC_CMY -log10(p-value)" \
  -sy "P.Value" \
  -t 0.05 \
  -dt True \
  -p "RNAseq_vs_SRM872549.dirPVal_005"
```

### Unacceptable behavior

- Using log2FC directly without the `-dt True` transformation when the user says "based on significance" or "based on p-value".
- Hardcoding column names without checking the file headers.

---

## 2. Log2FC scatter (ChIP-seq vs RNA-seq, cross-platform)

### User prompt

> "Compare ChIP-seq differential binding file X with RNA-seq DEG file Y using log2 fold-change."

### Expected agent behavior

1. Recognize **anno2anno** mode.
2. For the ChIP-seq file: identify the gene annotation column (e.g. `Gene_2kb`) and set `-mtx True` to expand comma-separated annotations.
3. For the RNA-seq file: identify the gene symbol column.
4. Do NOT set `-dt True` (user asked for fold-change, not p-value).
5. Set `-t 2` (default FC >= 2 cutoff) or ask the user.
6. Set `-qd "peak-2-genes"`.
7. Set `--plotPlain` for publication-ready figures.

### Unacceptable behavior

- Ignoring `-mtx True` when the ChIP-seq gene column has comma-separated names.
- Using `--comparisonMode region2region` when one file is gene-level RNA-seq.

---

## 3. Region-vs-region log2FC (ChIP-seq vs ChIP-seq, no cutoff)

### User prompt

> "Plot correlation of two CUT&RUN differential peak files using log2FC with no significance cutoff."

### Expected agent behavior

1. Recognize **region2region** mode.
2. Identify `Region` columns in both files.
3. Set `--comparisonMode region2region`.
4. Set `-t 1` (or `-t 0` for truly no cutoff — clarify with user).
5. Set `-qd regions`.

### Example command pattern

```bash
python scripts/plot_kde_correlation.py \
  -ix <chipseq_file_1> \
  -mx log2FC -gx Region \
  -lx "<contrast_1> log2FC" \
  -iy <chipseq_file_2> \
  -my log2FC -gy Region \
  -ly "<contrast_2> log2FC" \
  -t 1 \
  --comparisonMode region2region \
  -qd "regions" \
  -p "<output_prefix>"
```

---

## 4. Region-vs-region log2FC (with weak cutoff)

### User prompt

> "Generate a 2D scatter for these two ATAC-seq differential files with a fold-change cutoff of 1.5."

### Expected agent behavior

Same as above, but set `-t 1.5`. The script internally converts this to `log2(1.5) ≈ 0.585` on the log2 scale.

---

## 5. Region-vs-region directional p-value

### User prompt

> "Plot directional p-value correlation between these two ChIP-seq differential peak results."

### Expected agent behavior

1. Use `region2region` mode with `-dt True`.
2. Identify metric, significance, and region columns.
3. Set `-sx`, `-sy` to the significance column names.
4. Set `-t 0.05` (or as specified).
5. Labels should read `"<contrast> -log10(p-value)"`.

### Example command pattern

```bash
python scripts/plot_kde_correlation.py \
  -ix <file1> -mx log2FC -gx Region \
  -lx "<contrast_1> -log10(p-value)" -sx "p.value" \
  -iy <file2> -my log2FC -gy Region \
  -ly "<contrast_2> -log10(p-value)" -sy "p.value" \
  -t 0.05 -dt True \
  --comparisonMode region2region \
  -qd "regions" \
  -p "<output_prefix>"
```

---

## 6. Rank-vs-rank correlation

### User prompt

> "Generate rank-rank correlation plot for files X.rnk and Y.rnk."

### Expected agent behavior

1. Recognize **rank2rank** mode from the `.rnk` extension or user mention of "rank".
2. Set `--comparisonMode rank2rank`.
3. Do NOT set `-mx`, `-my`, `-sx`, `-sy`, `-gx`, `-gy`, `-dt` (they are ignored).
4. Set `-t 0` if no cutoff is desired.
5. Infer labels from filenames with `(score)` suffix.

### Example command

```bash
python scripts/plot_kde_correlation.py \
  -ix <file_X>.rnk \
  -lx "<contrast_X> [score]" \
  -iy <file_Y>.rnk \
  -ly "<contrast_Y> [score]" \
  -t 0 \
  --comparisonMode rank2rank \
  -qd "regions" \
  -p "<output_prefix>"
```

### Unacceptable behavior

- Attempting to specify metric or gene columns for `.rnk` files.
- Using `anno2anno` or `region2region` mode for `.rnk` files.

---

## 7. Ambiguous column names (edge case)

### User prompt

> "Plot 2D scatter for these two DEG files."

### File X headers

`gene  value  score  pval  adjusted_pval`

### Expected agent behavior

1. Identify `gene` as the identifier column (reasonable match).
2. `value` and `score` are both ambiguous for the metric role — ask the user: "I found columns `value` and `score` in file X. Which one is the fold-change metric?"
3. `pval` is a reasonable match for significance.
4. Proceed only after user confirms the metric column.

---

## 8. Missing input file (failure case)

### User prompt

> "Plot KDE correlation for nonexistent_file.tsv and another_file.tsv."

### Expected agent behavior

- Check that both files exist before running the script.
- Report: "File `nonexistent_file.tsv` was not found. Please provide the correct path."
- Do NOT run the script with a missing file.

---

## 9. Out-of-scope request

### User prompt

> "Plot a volcano plot for my DEG file."

### Expected agent behavior

- Recognize this is a single-file visualization (volcano), not a two-file correlation scatter.
- Respond: "This skill generates 2D scatter plots comparing two differential files. For a volcano plot of a single file, a different tool or script is needed."
