# Comparison Modes Reference

## Contents

- Overview
- anno2anno (annotation vs annotation)
- region2region (genomic region overlap)
- rank2rank (ranked score files)
- Mode selection decision tree
- Cross-comparison (ChIP-seq vs RNA-seq)

## Overview

The script supports three comparison modes that control how data points from the two input files are paired:

| Mode | Pairing method | Typical use |
|------|---------------|-------------|
| `anno2anno` | Exact string match on gene/annotation names | RNA-seq vs RNA-seq, ChIP-seq vs RNA-seq (via gene annotation) |
| `region2region` | Genomic region overlap via pybedtools intersection | ChIP-seq vs ChIP-seq, ATAC-seq vs ATAC-seq |
| `rank2rank` | Two-column `.rnk` files; string match or region intersection | Pre-computed ranked scores, pi-values |

## anno2anno (Annotation vs Annotation)

**Default mode.** Data points are paired by exact string match on the gene/annotation identifier columns (`-gx` and `-gy`).

### When to use

- Both files have a shared gene-symbol column (e.g. two RNA-seq DEG tables).
- One file is ChIP-seq with gene annotation and the other is RNA-seq — use `-mtx True` on the ChIP-seq side to expand comma-separated gene annotations.

### Key flags

- `-gx`, `-gy`: identifier columns (default `geneSymbol`).
- `-mtx True`: if the X-axis file has comma-separated gene names in the identifier column (e.g. `Gene_2kb` from peak annotation), this expands them into separate rows for matching.
- `-mx`, `-my`: metric columns.
- `-sx`, `-sy`: significance columns (only used with `-dt True`).
- `-dt True`: apply directional p-value transformation: `sign(log2FC) * -log10(p-value)`.

### Directional p-value transformation

When `-dt True` is set, the plotted metric becomes `direction * -log10(significance)` where direction is the sign of the fold-change. This is used to plot directional significance rather than raw fold-change. The scale is automatically overridden to `log10` internally.

The threshold (`-t`) in this mode represents a p-value cutoff (e.g. `-t 0.05` means only show data where `p < 0.05` on both axes, corresponding to `-log10(0.05) ≈ 1.3` on the transformed scale).

## region2region (Genomic Region Overlap)

Data points are paired by genomic region overlap using pybedtools. The identifier columns must contain coordinates in `<chrom>:<start>-<end>` format.

### When to use

- Both files are region-based differential results (e.g. two ChIP-seq or ATAC-seq differential peak analyses).
- The regions between the two files may not have identical coordinates but do overlap.

### Key flags

- `-gx`, `-gy`: should point to the column containing `<chrom>:<start>-<end>` strings (typically `Region`).
- `--comparisonMode region2region`: must be explicitly set.
- `-qd regions` or `-qd peaks`: set the quadrant label appropriately.

### Requirements

- `pybedtools` must be installed.
- Both identifier columns must contain parseable region strings.

### Output

Quadrant files are saved as `.bed` format (tab-separated: chrom, start, end, metricX, metricY) when region identifiers are detected.

## rank2rank (Ranked Score Files)

Both inputs are `.rnk` files — two-column files where column 1 is an identifier and column 2 is a numeric score (e.g. a pi-value, combined rank, or enrichment score).

### When to use

- The user already has pre-computed ranked scores and wants to correlate them.
- The data has been processed into a single summary score per gene/region.
- The user mentions "rank-rank correlation" or provides `.rnk` files.

### Behavior

- Flags `-sx`, `-mx`, `-sy`, `-my`, `-dt`, `-scale`, `-gx`, `-gy`, `-mtx` are **ignored**.
- Scale is forced to `linear`.
- Directional transform is forced to `False`.
- Labels default to `"<filename> (score)"` when set to `auto`.
- If both RNK files have genomic region identifiers, pairing is done via pybedtools intersection. Otherwise, exact string match is used.

### File format

```
geneA    0.543
geneB   -1.200
geneC    2.001
```

Two columns, tab or whitespace separated. Optional header row (auto-detected).

## Mode Selection Decision Tree

```
User provides two files
├── Both are .rnk files?
│   └── YES → rank2rank
├── Both have Region/Peak identifiers (chrom:start-end)?
│   └── YES → region2region
├── One has gene annotations, other has gene symbols?
│   └── YES → anno2anno (possibly with -mtx True on the annotated side)
├── Both have gene-symbol columns?
│   └── YES → anno2anno
└── Unclear → ask the user
```

## Cross-Comparison (ChIP-seq vs RNA-seq)

When comparing ChIP-seq differential peaks with RNA-seq differential genes:

1. Use `anno2anno` mode.
2. Set `-gx` to the ChIP-seq gene annotation column (e.g. `Gene_2kb`).
3. Set `-mtx True` to expand comma-separated gene lists.
4. Set `-gy` to the RNA-seq gene symbol column.
5. Set `-qd "peak-2-genes"` or similar descriptive label.

The fold-change columns (`-mx`, `-my`) and significance columns (`-sx`, `-sy`) are configured independently per file as usual.
