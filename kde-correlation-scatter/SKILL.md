---
name: kde-correlation-scatter
description: >-
  Generate a publication-quality 2D scatter plot with KDE density background
  comparing two differential experiments (RNA-seq, ChIP-seq, ATAC-seq, Cut&Run,
  or mixed multi-omics). Supports annotation-vs-annotation, region-vs-region,
  and rank-vs-rank comparison modes with Pearson/Spearman correlation and
  quadrant counts. Use when the user asks to plot a 2D scatter, KDE correlation,
  directional p-value plot, rank-rank correlation, or compare two differential
  gene-expression / differential-binding result files.
license: Apache-2.0
compatibility: >-
  Requires Python 3.9+ with pandas, numpy, scipy, matplotlib, seaborn;
  pybedtools required only for region2region or rank2rank with genomic regions.
  Local filesystem only; no network access required.
metadata:
  author: kde-correlation-scatter maintainers
  version: "1.0.0"
  status: stable
  last_reviewed: "2026-05-13"
allowed-tools: shell python
---

# KDE Correlation Scatter

## Purpose

Compare two differential-analysis result files (e.g. DEG tables, differential binding tables, or RNK score files) by producing a 2D scatter plot with optional KDE density background, correlation statistics, quadrant counts, and per-quadrant gene/region lists. The tool is designed for publication-ready figures in multi-omics research.

## When to Use

Use this skill when the user asks to:

- Plot a **2D scatter plot** comparing two differential experiments.
- Generate a **KDE correlation plot** for two DEG or differential-binding files.
- Produce a **directional p-value plot** (`-log10(p)` signed by fold-change direction).
- Create a **rank-rank correlation plot** from `.rnk` files.
- Compare **RNA-seq vs RNA-seq**, **ChIP-seq vs RNA-seq**, **ChIP-seq vs ChIP-seq**, or any similar differential results.
- Visualize **concordance or discordance** between two contrasts.

## When Not to Use

- The user wants a volcano plot (single experiment) — use a volcano-plot skill instead.
- The user needs pathway enrichment from gene lists — use the `pathway-enrichment-enrichr` skill.
- The data is not from differential analysis (e.g. raw counts, FPKM matrices without fold-change or significance).

## Required Inputs

- **File X** (`-ix`): path to the first differential result file (tab-separated) or `.rnk` file.
- **File Y** (`-iy`): path to the second differential result file (tab-separated) or `.rnk` file.

## Optional Inputs

- **Labels** (`-lx`, `-ly`): axis labels. Default `auto` infers from filename and metric.
- **Threshold** (`-t`): fold-change or score cutoff for quadrant filtering. Default `2`.
- **Scale** (`-scale`): `linear`, `log2`, or `log10`. Default `log2`.
- **Directional transform** (`-dt`): when `True`, computes `direction * -log10(significance)`.
- **Comparison mode** (`--comparisonMode`): `anno2anno`, `region2region`, or `rank2rank`.
- **Plain plot** (`--plotPlain`): also produce a plain black-dot scatter (publication-ready).
- **Mark genes** (`--markGenes`): highlight specific genes/regions on the plain scatter.
- **Quadrant description** (`-qd`): label for counts, e.g. `genes`, `peaks`, `regions`.
- See `scripts/plot_kde_correlation.py --help` for the full flag list.

## Workflow

### Step 1 — Determine comparison mode

Decide from the user's request and file types:

| User says / file type | Mode |
|---|---|
| Two DEG tables, RNA-seq, gene-level | `anno2anno` |
| ChIP-seq vs RNA-seq, peak annotation to gene | `anno2anno` with `-mtx True` |
| Two ChIP/ATAC/CnR region-level files | `region2region` |
| Two `.rnk` files | `rank2rank` |

### Step 2 — Read file headers and auto-detect columns

**This is the most critical step.** Read the first few rows of each input file and identify the columns. Follow the rules in [references/column-identification.md](references/column-identification.md).

Key principles:

1. **Examine each file independently** — column names may differ between files.
2. Use case-insensitive fuzzy matching to identify:
   - **Metric column** (fold-change): `log2FC`, `logFC`, `log2FoldChange`, `FC`, `foldChange`, etc.
   - **Significance column** (p-value): `P.Value`, `pvalue`, `p`, `PValue`, `p.value`, `padj`, `FDR`, `q.value`, `adj.P.Val`, etc.
   - **Gene/identifier column**: `geneSymbol`, `gene`, `gene_symbol`, `symbol`, `Gene`, `transcript`, `Gene_2kb`, `Region`, etc.
3. **If uncertain about any column assignment, ask the user before proceeding.** Do not guess silently.
4. For `rank2rank` mode, column identification is less critical (only two columns: identifier and score), but verify the file looks like a valid RNK.

### Step 3 — Infer axis labels

When labels are set to `auto`, construct them from the input filename and the final plotted metric:

- For directional p-value mode: `"<contrast_from_filename> -log10(p-value)"`
- For log2FC mode: `"<contrast_from_filename> log2FC"`
- For rank2rank: `"<contrast_from_filename> [score]"`

Extract the contrast description from the filename by stripping extensions and replacing separators. For example, `SRM196663.N_vs_N_C.regulation.tsv` becomes `SRM196663-N_vs_N_C`.

### Step 4 — Build and validate the command

Construct the `plot_kde_correlation.py` command with the identified parameters. Double-check:

- Column names match actual headers (case-sensitive after identification).
- Directional transform (`-dt True`) is set when the user asks for p-value-based plots.
- Significance columns (`-sx`, `-sy`) are specified when `-dt True`.
- The threshold (`-t`) is appropriate for the scale (e.g. `0.05` for p-value mode, `2` for FC cutoff meaning FC >= 2).
- `--comparisonMode` is set correctly.
- `-qd` matches the data type (`genes` for RNA-seq, `peaks` or `regions` for ChIP/ATAC-seq).

### Step 5 — Execute the script

Run from the skill root:

```
python scripts/plot_kde_correlation.py \
  -ix <file_X> -iy <file_Y> \
  -mx <metric_X> -my <metric_Y> \
  -gx <gene_X> -gy <gene_Y> \
  [remaining flags...] \
  -p <output_prefix>
```

Prefer writing outputs under `agentResults/<runId>/` per repository conventions.

### Step 6 — Verify and report

- Confirm the script exited with code 0.
- Check that `.KDE.pdf` (and optionally `.plain.pdf`, `.plain.svg`) were created.
- Report the correlation coefficients from the log.
- Report quadrant counts (N1–N4) and their meaning.
- List all output files.

## Scripts

| Script | Role |
|--------|------|
| [scripts/plot_kde_correlation.py](scripts/plot_kde_correlation.py) | CLI: read two differential files, merge by identifier, compute correlation, produce KDE scatter plot, plain scatter, quadrant gene/region lists. |

## Output Format

| File | Description |
|------|-------------|
| `<prefix>.KDE.pdf` | Main 2D scatter with KDE density background, quadrant lines, correlation in title. |
| `<prefix>.plain.pdf` | Plain black-dot scatter (when `--plotPlain`). Publication-ready. |
| `<prefix>.plain.svg` | SVG version of plain scatter. |
| `<prefix>.PreprocessedData_all.tsv` | All matched data points before threshold filtering. |
| `<prefix>.PlottedData.tsv` | Data points that passed the threshold and were plotted. |
| `<prefix>.PlottedData_N1.tsv` (or `.bed`) | Identifiers in quadrant N1 (X-down, Y-up). |
| `<prefix>.PlottedData_N2.tsv` (or `.bed`) | Identifiers in quadrant N2 (X-up, Y-up). |
| `<prefix>.PlottedData_N3.tsv` (or `.bed`) | Identifiers in quadrant N3 (X-down, Y-down). |
| `<prefix>.PlottedData_N4.tsv` (or `.bed`) | Identifiers in quadrant N4 (X-up, Y-down). |
| `<prefix>.log` | Detailed execution log. |

Quadrant files are saved as `.bed` when identifiers are genomic regions (`<chrom>:<start>-<end>`), otherwise as `.tsv`.

## Quality Checks

Before finishing, verify:

- Both input files exist and are readable.
- Column names were correctly identified (or confirmed by the user).
- The script produced at least the `.KDE.pdf` output.
- Correlation values are finite (not NaN).
- Quadrant counts are non-negative and their sum is plausible.
- The log file does not contain ERROR-level messages.

## Failure and Escalation

- If column names cannot be confidently identified, **ask the user** which columns correspond to fold-change, significance, and gene identifier.
- If both files have zero overlapping identifiers after merging, warn the user: the gene/region naming conventions may be incompatible between files.
- If pybedtools is not installed and `region2region` or region-based `rank2rank` is needed, inform the user and suggest installing it.

## Resources

- [references/column-identification.md](references/column-identification.md): detailed rules for auto-detecting column roles from headers.
- [references/comparison-modes.md](references/comparison-modes.md): when and how to use each comparison mode.

## Examples

- [examples/evaluation-prompts.md](examples/evaluation-prompts.md): realistic user prompts and expected agent behavior.
