# Input Manifest and Grid Layout

## Contents

- Manifest format
- Panel order and titles
- Grid geometry flags
- Plot types
- Output artifacts

## Manifest format

The script expects a **tab-separated** file with exactly these columns:

| Column | Description |
|--------|-------------|
| `inputFile` | Absolute or relative path to one differential result table (TSV/TXT, tab-delimited) |
| `sampleLabel` | Short label used as the **subplot title** (e.g. `1h`, `2h`, contrast name) |

Example (`examples/gse202762_timecourse_manifest.tsv`):

```tsv
inputFile	sampleLabel
examples/GSE202762.DMSO_EGF_10min_vs_DMSO_UT.regulation.tsv	10min
examples/GSE202762.DMSO_EGF_20min_vs_DMSO_UT.regulation.tsv	20min
examples/GSE202762.DMSO_EGF_1hr_vs_DMSO_UT.regulation.tsv	1hr
examples/GSE202762.DMSO_EGF_2hr_vs_DMSO_UT.regulation.tsv	2hr
examples/GSE202762.DMSO_EGF_4hr_vs_DMSO_UT.regulation.tsv	4hr
```

**Panel order** follows manifest row order: left-to-right, then top-to-bottom (`divmod(index, numFigCol)`).

## Grid geometry

| Flag | Meaning |
|------|---------|
| `--cols N` | Number of subplot columns |
| `--rows N` | Number of subplot rows |

If both omitted, the script uses roughly square layout: `cols = ceil(sqrt(n))`, `rows = ceil(n / cols)`.

Examples:

| Request | Panels | Flags |
|---------|--------|-------|
| 2 columns × 1 row | 2 | `--cols 2 --rows 1` |
| 1 column × 2 rows | 2 | `--cols 1 --rows 2` |
| Single row, two timepoints | 2 | `--rows 1` (cols auto = 2) or `--cols 2 --rows 1` |

Unused subplot cells are turned off automatically.

## Plot types

`--plotsToPlot` comma-separated list:

- `volcano` — Volcano grid only
- `ma` — MA grid only
- `volcano,ma` — both figures (default)

Shared axis limits are computed across **all** panels in a grid for direct comparison.

## Highlighting features

| Flag | Purpose |
|------|---------|
| `--labelPoints GENE1,GENE2` | Highlight IDs present in `--nameCol` (or regions mapped via `Gene_2kb` when `--identifyRegionByGeneName Yes`) |
| `--plotGeneNames Yes\|No` | Draw text labels (default Yes; use No for many points) |
| `--plotDiffGeneMark Yes\|No` | Append (↑)/(↓)/(≈) to labels from differential status |

## Thresholds

| Flag | Default | Meaning |
|------|---------|---------|
| `--fcCut` | `2` | Linear fold-change cutoff; compared as `log2(fcCut)` when fc column name contains `log2` |
| `--fdrCut` | `0.05` | Significance cutoff on raw `--sigCol` scale (volcano only) |

## Output artifacts

Given manifest `inputs.tsv` and prefix `out/run1`:

| File | Description |
|------|-------------|
| `out/run1.volcanoGrid.png`, `.pdf` | Volcano grid (300 DPI PNG + vector PDF) |
| `out/run1.MAgrid.png`, `.pdf` | MA grid |
| `out/run1.volcanoGrid.gmt`, `.gmt.txt` | Up/down gene sets per panel (volcano) |
| `out/run1.MAgrid.gmt`, `.gmt.txt` | Up/down sets per panel (MA) |
| `out/run1.volcanoGrid.<label>.labelPoints.tsv` | Region–gene mapping when `--identifyRegionByGeneName Yes` |
| `volcano_ma_grid.log` | Execution log in working directory |

Prefer run-scoped output:

```text
agentResults/volcano-grid-plot-<YYYYMMDDTHHMMSSZ>/
```
