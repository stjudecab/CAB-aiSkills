
<p align="center">
  <img src="assets/CAB-aiSkills_kde-correlation-scatter.svg" alt="kde-correlation-scatter skill badge" width="520" />
</p>

# KDE Correlation Scatter — Agent Skill

Portable **Agent Skill** for generating publication-quality **2D scatter plots with KDE density background** comparing two differential experiments (RNA-seq, ChIP-seq, ATAC-seq, Cut&Run, or mixed multi-omics). Computes Pearson and Spearman correlations, displays quadrant counts, and exports per-quadrant gene/region lists. Agent-facing instructions are in [SKILL.md](SKILL.md).

## Environment

- **Python** 3.9 or newer
- **Dependencies:**

```bash
cd kde-correlation-scatter
pip install -r requirements.txt
```

**Note:** `pybedtools` requires `bedtools` to be installed on the system and available on `$PATH`. It is only needed for `region2region` and region-based `rank2rank` modes. For `anno2anno` mode, `pybedtools` is imported but not exercised.

## Install for Cursor or other agent clients

- **Project skill:** Copy or symlink this folder so the client discovers a directory named `kde-correlation-scatter` containing `SKILL.md` (for example `.cursor/skills/kde-correlation-scatter/`).
- **Invoke** by skill name `kde-correlation-scatter` or by asking the agent to plot a 2D scatter, KDE correlation, or compare two differential result files, as described in [SKILL.md](SKILL.md).

## Quick start examples

Run from **this directory** (`kde-correlation-scatter`) unless you pass absolute paths.

### RNA-seq vs RNA-seq — directional p-value

```bash
python scripts/plot_kde_correlation.py \
  -ix examples/RNAseq_clone_vs_CMY.regulation.tsv \
  -mx log2FC -gx geneSymbol \
  -lx "RNAseq_clone_vs_CMY -log10(p-value)" \
  -sx "P.Value" \
  -iy examples/SRM872549_diff.ERCC_clones_vs_ERCC_CMY.regulation.tsv \
  -my log2FC -gy geneSymbol \
  -ly "SRM872549-ERCC_clones_vs_ERCC_CMY -log10(p-value)" \
  -sy "P.Value" \
  -t 0.05 -dt True \
  -p "RNAseq_vs_SRM872549.dirPVal_005"
```

### RNA-seq vs RNA-seq — log2FC

```bash
python scripts/plot_kde_correlation.py \
  -ix examples/RNAseq_clone_vs_CMY.regulation.tsv \
  -mx log2FC -gx geneSymbol \
  -iy examples/SRM872549_diff.ERCC_clones_vs_ERCC_CMY.regulation.tsv \
  -my log2FC -gy geneSymbol \
  -t 2 \
  -p "RNAseq_vs_SRM872549.log2FC"
```

### ChIP-seq vs RNA-seq — log2FC with gene annotation expansion

```bash
python scripts/plot_kde_correlation.py \
  -ix <chipseq_diff_file.tsv> \
  -mx log2FC -gx Gene_2kb \
  -lx "[ChIP-seq] contrast log2FC" \
  -mtx True \
  -iy <rnaseq_deg_file.tsv> \
  -my logFC -gy symbol \
  -ly "[RNA-seq] contrast log2FC" \
  -t 2 -qd "peak-2-genes" \
  -p "ChIPseq_vs_RNAseq" \
  --plotPlain
```

### Region-vs-region — ChIP-seq differential peaks

```bash
python scripts/plot_kde_correlation.py \
  -ix <chipseq_file_1.tsv> -mx log2FC -gx Region \
  -lx "Contrast1 log2FC" \
  -iy <chipseq_file_2.tsv> -my log2FC -gy Region \
  -ly "Contrast2 log2FC" \
  -t 1 --comparisonMode region2region \
  -qd "regions" \
  -p "ChIP1_vs_ChIP2.log2FC"
```

### Rank-vs-rank correlation

```bash
python scripts/plot_kde_correlation.py \
  -ix <scores_X.rnk> \
  -lx "Contrast_X [pi-value]" \
  -iy <scores_Y.rnk> \
  -ly "Contrast_Y [pi-value]" \
  -t 0 --comparisonMode rank2rank \
  -qd "regions" \
  -p "rank2rank_correlation"
```

## How the agent uses this skill

When a user asks for a 2D scatter or KDE correlation plot, the agent:

1. **Reads** the SKILL.md to understand the workflow.
2. **Inspects file headers** of both input files to auto-detect column names for fold-change, significance, and gene/region identifiers (see [references/column-identification.md](references/column-identification.md)).
3. **Selects the comparison mode** based on data type (see [references/comparison-modes.md](references/comparison-modes.md)).
4. **Infers axis labels** from filenames and the chosen metric.
5. **Asks the user** if any column assignment is ambiguous.
6. **Constructs and runs** the `plot_kde_correlation.py` command.
7. **Reports** the output files, correlation statistics, and quadrant counts.

## Layout

| Path | Role |
|------|------|
| [assets/](assets/) | CAB aiSkills logo and this skill’s badge (for standalone README rendering) |
| [SKILL.md](SKILL.md) | Agent instructions: when to use, workflow, safety, outputs |
| [scripts/plot_kde_correlation.py](scripts/plot_kde_correlation.py) | CLI: read two differential files, merge, correlate, produce scatter plots |
| [references/column-identification.md](references/column-identification.md) | Auto-detection rules for column roles (metric, significance, identifier) |
| [references/comparison-modes.md](references/comparison-modes.md) | Guide to anno2anno, region2region, rank2rank modes |
| [examples/evaluation-prompts.md](examples/evaluation-prompts.md) | Realistic user prompts with expected agent behavior |
| [examples/](examples/) | Example input data files |
| [tests/](tests/) | Test suite (placeholder) |

## Outputs

| File pattern | Description |
|--------------|-------------|
| `*.KDE.pdf` | Main 2D scatter with KDE density background |
| `*.plain.pdf`, `*.plain.svg` | Plain scatter (with `--plotPlain`) |
| `*.PreprocessedData_all.tsv` | All merged data points |
| `*.PlottedData.tsv` | Threshold-filtered plotted data |
| `*.PlottedData_N1–N4.tsv` (or `.bed`) | Per-quadrant identifier lists |
| `*.log` | Execution log with full parameter record |

## User-facing prompt examples

Below are example prompts a user might type and how the agent should interpret them. See [examples/evaluation-prompts.md](examples/evaluation-prompts.md) for detailed expected behavior.

| User prompt | Interpretation |
|---|---|
| "Plot 2D scatter for file X and Y, both RNA-seq, based on significance" | anno2anno, `-dt True`, directional p-value |
| "Plot 2D scatter for the DEG files X and Y, based on p-value" | anno2anno, `-dt True`, directional p-value |
| "Generate KDE correlation plot for files X and Y based on directional p" | anno2anno, `-dt True`, directional p-value |
| "Compare ChIP-seq binding and RNA-seq expression using log2FC" | anno2anno, `-mtx True` on ChIP side, log2FC |
| "Plot log2FC correlation for two ChIP-seq differential peak files" | region2region, log2FC |
| "Plot directional p-value for two CUT&RUN differential results" | region2region, `-dt True` |
| "Generate rank-rank correlation plot for X.rnk and Y.rnk" | rank2rank |
| "Compare these two differential files" | Examine files, ask if unclear about mode/metric |

## Testing

```bash
python scripts/plot_kde_correlation.py --help
```

## License

Packaging, documentation, and scripts: **[CC BY-NC-SA 4.0](../LICENSE.txt)**. See [AUTHORS.md](../AUTHORS.md) and [SKILL.md](SKILL.md) frontmatter.
