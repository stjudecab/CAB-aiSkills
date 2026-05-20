# Column Identification Reference

## Contents

- Overview
- Fold-change column detection
- Significance column detection
- Gene / region identifier column detection
- Average-expression column (MA plots)
- Gene annotation for peak labeling (differential binding)
- Region coordinate reconstruction
- Cross-file column consistency
- Ambiguity resolution protocol
- Examples

## Overview

Before running `volcano_ma_grid.py`, examine the **header row of every input table** and map columns to the roles required by the script:

| Role | CLI flag | Required when |
|------|----------|---------------|
| Fold-change | `--fcCol` | Always |
| Significance (p / FDR / q) | `--sigCol` | Volcano plots |
| Feature ID | `--nameCol` | Always (gene symbol, Ensembl ID, or genomic region) |
| Average expression | `--aveExprCol` | MA plots (`--plotsToPlot` includes `ma`) |
| Peak-to-gene annotation | hard-coded `Gene_2kb` in script when `--identifyRegionByGeneName Yes` | Labeling genes on peak/region tables |

Column names **do not need to match defaults** (`log2FC`, `q.value`, `Region`, `log2AveExpr`). The agent must detect the correct columns and pass them explicitly on the CLI.

## Fold-change column detection

Search case-insensitively (priority order):

| Pattern | Notes |
|---------|--------|
| `log2FC` | limma, edgeR, common custom |
| `logFC` | edgeR |
| `log2FoldChange` | DESeq2 |
| `log2(fold_change)` | Cuffdiff |
| `FC`, `foldChange`, `fold_change` | May be linear FC — confirm scale before plotting |
| `lfc`, `log2_fold_change`, `log2ratio` | shorthand variants |

Prefer log2-scaled fold-change columns when multiple candidates exist. If the column name contains `log2`, the script compares values to `log2(--fcCut)` (default `fcCut=2` → threshold ±1 on the axis).

## Significance column detection

Search case-insensitively:

| Pattern | Notes |
|---------|--------|
| `P.Value`, `PValue`, `pvalue`, `p_value`, `p.value` | Raw p-value |
| `p`, `pval` | Use only if no better match |
| `FDR`, `padj`, `adj.P.Val`, `q.value`, `qvalue` | Adjusted significance |

**Default script value is `q.value`.** Many RNA-seq tables use `FDR` or `P.Value` instead — always set `--sigCol` to the column actually present.

Volcano y-axis is **`-log10(sigCol)`** on the raw values in the table (including strings like `<1e-08`). `--fdrCut` is compared on the **same scale** as the column (e.g. `0.05` for FDR, not log-transformed).

When both raw and adjusted columns exist, prefer **adjusted** (`FDR`, `padj`, `q.value`) unless the user asks for raw p-values.

## Gene / region identifier column detection

### RNA-seq / DEG (gene-level)

| Pattern | Notes |
|---------|--------|
| `geneSymbol`, `gene_symbol`, `GeneSymbol` | Preferred for human-readable labels |
| `gene`, `Gene`, `geneName`, `gene_name` | Confirm values look like symbols, not Ensembl IDs |
| `symbol` | edgeR |
| `transcript`, `external_gene_name` | transcript-level |
| `geneID`, `gene_id` | Ensembl IDs — usable but less readable |

Prefer **gene symbol** over Ensembl ID when both exist.

### Differential binding / epigenomics (region-level)

| Pattern | Notes |
|---------|--------|
| `Region`, `region`, `Peak`, `peak` | Values like `chr1:1000-2000` or `chr1:1000:2000` |
| `locus`, `interval`, `site` | May hold coordinates |

If no single region column exists but **chromosome + start (+ end)** columns are present, reconstruct a region ID (see below) and either add a derived column or copy the file with a new `Region` column before plotting.

## Average-expression column (MA plots)

| Pattern | Notes |
|---------|--------|
| `log2AveExpr`, `AveExpr`, `baseMean`, `logCPM`, `log2BaseMean` | x-axis for MA |
| `meanExpr`, `average_expression` | confirm log vs linear scale |

Set `--aveExprCol ignore` to skip MA even if listed in `--plotsToPlot`.

## Gene annotation for peak labeling

When the user asks to **highlight gene symbols** on **differential binding** tables (regions as row IDs), use:

```bash
--identifyRegionByGeneName Yes --labelPoints GENE1,GENE2
```

The script matches `labelPoints` against the **`Gene_2kb`** column (comma-separated gene lists per peak). Equivalent columns may be named `Gene_1kb`, `Gene_5kb`, `Nearest_Gene`, `gene_annotation`, etc. — if not `Gene_2kb`, either rename in a prepared copy (document in `column_renames.tsv`) or ask the user which annotation column to use.

## Region coordinate reconstruction

If values are **not** already `chrom:start-end` but separate columns exist:

1. Detect chromosome: `chr`, `chrom`, `Chromosome`, `seqnames`, etc.
2. Detect start: `start`, `Start`, `begin`, etc.
3. Detect end: `end`, `End`, `stop` (optional but preferred).

Build:

```text
{chrom}:{start}-{end}
```

If only start is available, use `{chrom}:{start}-{start}` or ask the user.

Validate a sample of rows with a regex such as `^chr[\w]+:\d+[-:]\d+`.

## Cross-file column consistency

When multiple files are listed in the input manifest:

1. Map columns **independently** per file first.
2. Compare resolved roles across files:
   - All files must have an equivalent **fc** column (names may differ).
   - All files must have an equivalent **sig** column for volcano grids.
   - All files must use the **same semantic** for `--nameCol` (all genes or all regions).
   - MA requires an equivalent **average expression** column in each file.

3. If names differ but semantics match (e.g. file A: `geneSymbol`, file B: `symbol`), the agent may:
   - Copy inputs to a run directory and rename headers to a **common canonical name**, **or**
   - Pass per-file processing is **not** supported by one CLI call — **one** `--fcCol`, `--sigCol`, `--nameCol` applies to **all** files.

   Therefore harmonize by creating renamed copies under `agentResults/volcano-grid-plot-<runId>/prepared/` and point the manifest at those paths.

4. Write **`column_renames.tsv`** in the output directory:

   | source_file | original_column | canonical_column | role |
   |-------------|-----------------|------------------|------|

5. Log every rename in the run log and tell the user explicitly.

6. If equivalence is unclear or roles conflict (gene vs region mix), **stop and ask the user**.

## Ambiguity resolution protocol

1. List candidate columns and 2–3 example values.
2. State which role is ambiguous.
3. Ask: *Which column should be used as [fold-change / significance / gene or region ID / average expression]?*
4. Do not run the plot script until resolved.

Triggers:

- Zero candidates for a required role.
- Multiple equally plausible candidates.
- Inconsistent identifier types across files in one grid.
- Non-numeric fold-change or significance columns.

## Examples

### limma-style RNA-seq (bundled examples)

Headers: `geneID  geneSymbol  log2FC  AveExpr  P.Value  FDR  ...`

- `--fcCol log2FC`
- `--sigCol FDR` (or `P.Value` if user wants raw p)
- `--nameCol geneSymbol`
- `--aveExprCol AveExpr`

### DESeq2

- `--fcCol log2FoldChange`
- `--sigCol padj`
- `--nameCol` from gene column or row names

### ChIP-seq peaks

- `--fcCol log2FC`
- `--sigCol p.value` or `FDR`
- `--nameCol Region`
- Label genes: `--identifyRegionByGeneName Yes` with `Gene_2kb` present
