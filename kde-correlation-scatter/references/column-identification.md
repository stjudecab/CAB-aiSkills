# Column Identification Reference

## Contents

- Overview
- Fold-change / metric column detection
- Significance / p-value column detection
- Gene / identifier column detection
- Region column detection
- Rank file (RNK) validation
- Ambiguity resolution protocol
- Examples

## Overview

When the user provides differential analysis files, the agent must examine the header row of each file independently and map columns to the three key roles:

1. **Metric column** — the fold-change or effect-size measure.
2. **Significance column** — the statistical significance measure (only needed when `-dt True`).
3. **Gene/identifier column** — the biological identifier used to join the two files.

Column names vary widely across tools (DESeq2, edgeR, limma, HOMER, DiffBind, custom pipelines). The agent must use case-insensitive pattern matching and biological context to identify the correct columns.

## Fold-Change / Metric Column Detection

Search for columns matching any of these patterns (case-insensitive):

| Pattern | Common source |
|---------|---------------|
| `log2FC` | limma, edgeR, custom |
| `logFC` | edgeR |
| `log2FoldChange` | DESeq2 |
| `log2(fold_change)` | Cuffdiff |
| `FC` | generic |
| `foldChange` | generic |
| `fold_change` | generic |
| `lfc` | shorthand |
| `log2_fold_change` | underscore variant |
| `log2ratio` | some ChIP-seq tools |
| `Fold` | DiffBind |

Priority: prefer `log2FC` > `logFC` > `log2FoldChange` > others. If multiple candidates exist, pick the one most likely to be a log2 fold-change. If still ambiguous, ask the user.

## Significance / P-Value Column Detection

Search for columns matching (case-insensitive):

| Pattern | Common source | Notes |
|---------|---------------|-------|
| `P.Value` | limma | Raw p-value |
| `PValue`, `pvalue`, `p_value` | generic | |
| `p` | minimal headers | Only use if no better match |
| `pval` | shorthand | |
| `P.value`, `p.value` | case variants | |
| `padj` | DESeq2 | Adjusted p-value |
| `FDR` | edgeR, limma | False discovery rate |
| `q.value`, `qvalue` | generic | |
| `adj.P.Val` | limma (topTable) | Adjusted |
| `p.value` | HOMER, custom | |

When the user says "p-value" or "significance", prefer raw p-values (`P.Value`, `pvalue`) over adjusted (`FDR`, `padj`) unless the user specifically says "FDR" or "adjusted". If both raw and adjusted are present, default to raw p-value for the directional transform, because `-log10(raw p)` typically gives better visual spread.

## Gene / Identifier Column Detection

Search for columns matching (case-insensitive):

| Pattern | Typical use | Notes |
|---------|-------------|-------|
| `geneSymbol` | RNA-seq standard | |
| `gene_symbol` | underscore variant | |
| `gene` | generic, minimal | Confirm it contains gene names not IDs |
| `Gene` | capitalized variant | |
| `symbol` | edgeR, short | |
| `geneName`, `gene_name` | some pipelines | |
| `GeneSymbol` | CamelCase | |
| `transcript` | transcript-level | |
| `external_gene_name` | BioMart | |
| `hgnc_symbol` | BioMart | |
| `Gene_2kb` | ChIP-seq peak annotation | Comma-separated gene names — use `-mtx True` |
| `Gene_1kb`, `Gene_5kb` | ChIP-seq annotation variants | Comma-separated |
| `Nearest_Gene` | ChIP-seq annotation | |
| `Region` | ChIP-seq, ATAC-seq | Genomic coordinates `<chrom>:<start>-<end>` |
| `Peak` | DiffBind | |
| `geneID`, `gene_id` | Ensembl-style IDs | Usable but less human-readable |

For RNA-seq data, prefer gene symbol columns over gene ID columns when both are present. For ChIP/ATAC-seq region-level data, prefer `Region` or `Peak` columns.

## Region Column Detection

If the identifier column contains values in the format `<chrom>:<start>-<end>` (e.g. `chr1:1000-2000`), the data is region-based. In this case:

- Suggest `--comparisonMode region2region` if both files have region identifiers.
- If one file has region identifiers and the other has gene symbols, suggest `anno2anno` with `-mtx True` on the region side (if the region file also has a gene annotation column).

## Rank File (RNK) Validation

For `rank2rank` mode, validate that:

1. The file extension is `.rnk` (case-insensitive).
2. The file has exactly two columns (or a header row followed by two-column data).
3. The second column is numeric (scores/ranks).
4. The first column contains identifiers (gene names or genomic regions).

If identifiers in both RNK files look like genomic regions, they will be paired via bedtools intersection. Otherwise, exact string match is used.

## Ambiguity Resolution Protocol

When the agent cannot confidently assign a column role:

1. List the candidate columns and their first few values.
2. State which role is ambiguous (metric, significance, or identifier).
3. Ask the user: "I found these columns in `<filename>`: `[col1, col2, ...]`. Which column should I use as the [metric/significance/identifier]?"
4. Do not proceed with plotting until the user confirms.

Situations that trigger this protocol:

- Zero candidates found for a required role.
- Multiple equally plausible candidates.
- Column name is a single generic word like `value`, `score`, `name`.
- The file has non-standard or domain-specific column names.

## Examples

### Standard RNA-seq (limma output)

Headers: `geneID  geneSymbol  log2FC  AveExpr  t.Statistic  P.Value  FDR  ...`

- Metric: `log2FC`
- Significance: `P.Value`
- Gene: `geneSymbol`

### DESeq2 output

Headers: `baseMean  log2FoldChange  lfcSE  stat  pvalue  padj`

- Metric: `log2FoldChange`
- Significance: `pvalue` (raw) or `padj` (adjusted — ask if user intent is unclear)
- Gene: row names (index) — may need the user to specify or the file may have a `gene` column

### edgeR output

Headers: `symbol  logFC  logCPM  LR  PValue  FDR`

- Metric: `logFC`
- Significance: `PValue`
- Gene: `symbol`

### ChIP-seq differential peak (with annotation)

Headers: `Region  log2FC  p.value  FDR  Gene_2kb  Gene_1kb  ...`

- Metric: `log2FC`
- Significance: `p.value`
- Gene/Region: `Region` for region2region mode, or `Gene_2kb` with `-mtx True` for anno2anno cross-comparison with RNA-seq
