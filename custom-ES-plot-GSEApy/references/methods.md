# Methods: GSEA enrichment plotting (GSEApy pickle & Broad GSEA)

## Contents

- Input modes
- How each mode works
- Input requirements
- CLI reference
- Gene-set name resolution
- Output artifacts
- Edge cases
- Environment setup

## Input modes

The CLI accepts **one** input source per run. Choose the mode that matches how prerank GSEA was originally run:

| Mode | Flag | When to use | Primary source artifacts |
|------|------|-------------|--------------------------|
| GSEApy pickle | `--inPKL` | Prerank GSEA was run with **GSEApy** and a `pre_res` pickle was saved | `GSEApy_prerank.pre_res.*.pkl` |
| Broad GSEA desktop | `--inGseaDir` | Prerank GSEA was run with **Broad Institute GSEA desktop** software | Output folder with `edb/results.edb`, `edb/*.rnk`, `edb/gene_sets.gmt` |

`--inPKL` and `--inGseaDir` are mutually exclusive.

## How each mode works

### GSEApy pickle mode (`--inPKL`)

1. Load the serialized `gseapy.gsea.Prerank` object from the pickle.
2. Resolve requested gene sets against names in `pre_res.res2d` (or `gmt` / `results` fallbacks).
3. Plot each gene set with `pre_res.plot(...)`, using the ranked list, RES curve, hits, and statistics already stored in the pickle.
4. Write companion `.txt` statistics from `pre_res.res2d`.

This mode does **not** read Broad `results.edb`. It uses only the GSEApy pickle produced by your prerank run.

### Broad GSEA desktop mode (`--inGseaDir`)

1. Parse `edb/results.edb` for per-gene-set ES, NES, p-values, FDR, and hit indices.
2. Load the collapsed ranked list from `edb/*.rnk` and gene sets from `edb/gene_sets.gmt`.
3. Recompute the running enrichment score (RES) curve with GSEApy for each selected gene set.
4. Render ES plots with `gseapy.gseaplot`.
5. Write companion `.txt` statistics from `results.edb`, optionally enriched with Broad report TSV fields (Tag %, Gene %, leading edge).

This mode does **not** require a GSEApy pickle. It reads the Broad GSEA desktop output directory directly.

Both modes support plotting gene sets **regardless of significance** or default top-set figure limits (`graph_num` in GSEApy, `plot_top_x` in Broad GSEA).

## Input requirements

### GSEApy pickle (`--inPKL`)

- Must be a GSEApy prerank **`pre_res`** object serialized with `pickle`.
- Typical naming: `GSEApy_prerank.pre_res.<assay>.<contrast>.pkl`.
- The object must expose gene-set results via `res2d`, `gmt`, or `results` (the script prefers `res2d['Term']`).
- Gene-set inventory for `--geneSetName` resolution comes from the pickle (`res2d['Term']`, else `gmt` keys, else `results` keys).

### Broad GSEA directory (`--inGseaDir`)

- Must be the **GSEA desktop output folder** for one preranked run (for example `48h.GseaPreranked.<timestamp>/`).
- Required files under `edb/`:
  - `results.edb` — per-gene-set ES, NES, p-values, FDR, hit indices
  - `*.rnk` — collapsed ranked gene list used in the run
  - `gene_sets.gmt` — gene sets filtered to the dataset
- Optional but useful:
  - `gsea_report_for_na_pos_*.tsv` / `gsea_report_for_na_neg_*.tsv` — Tag %, Gene %, leading-edge summary for statistics TXT files
  - `*.rpt` — run parameters; used to infer weighted scoring (`weight=1.0` when `scoring_scheme=weighted`)
- Gene-set inventory for `--geneSetName` resolution comes from all terms in `edb/results.edb`.

### Runtime

- **`gseapy` must be importable** for both modes (pickle unpickling in GSEApy mode; RES computation and plotting in Broad mode).
- Use a GSEApy version compatible with the environment that created the pickle when possible.

## CLI reference

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--inPKL` | one-of-two | — | Path to GSEApy `pre_res` pickle |
| `--inGseaDir` | one-of-two | — | Path to Broad GSEA desktop output directory |
| `--geneSetName` | yes | — | Gene set selection (see below) |
| `--listOnly` | no | `False` | List resolved gene sets without plotting |
| `--outputDir` | no | `plots/enrichment/<input_stem>/<run_id>/` (plot mode) | Output directory |
| `--weight` | no | infer / `1.0` | Broad GSEA weighted score exponent (`0`, `1`, `1.5`, `2`); **ignored in GSEApy pickle mode** |
| `--figWidth` | no | `6.0` | Plot width (inches) |
| `--figHeight` | no | `7.0` | Plot height (inches) |
| `--combineTrace` | no | `False` | Write combined multi-pathway trace plots via `gseapy.gseaplot2`, grouped by trailing suffix (e.g. `TOP500_UP`, `TOP500_DOWN`) |
| `--combineTraceOnly` | no | `False` | With `--combineTrace`, skip per-gene-set figures and write only combined trace plots |
| `--logLevel` | no | `INFO` | Logging level |

## Gene-set name resolution

The script resolves `--geneSetName` in this order:

1. **List file**: if the argument is an existing path ending in `.lst` or `.txt`, read one specification per line (skip blank lines and `#` comments).
2. **`allGeneSets`**: if the entire argument equals `allGeneSets`, select every gene set available in the active input mode.
3. **Comma-separated tokens**: otherwise split on commas and resolve each token independently.

Per token:

1. Exact match against available gene sets → add that set.
2. Else compile as a **regular expression** and match with `re.search` against all available terms → add all matches.
3. Else log a **warning** that the gene set was not found.

Available gene sets depend on the input mode:

| Input mode | Gene-set name source |
|------------|----------------------|
| GSEApy pickle | `pre_res.res2d['Term']`, else `gmt` keys, else `results` keys |
| Broad GSEA | All terms parsed from `edb/results.edb` |

Matched gene sets are de-duplicated while preserving order.

### Examples

| `--geneSetName` | Result |
|-----------------|--------|
| `HALLMARK_APOPTOSIS` | Single exact match |
| `SOS_peaks.*,HALLMARK_APOPTOSIS` | All SOS_peaks terms plus HALLMARK if present |
| `examples/gene_sets_sos_peaks.lst` | Lines from list file |
| `allGeneSets` | All terms available in the active input |

## List-only mode (`--listOnly`)

When `--listOnly` is enabled:

- Gene sets are resolved the same way as plot mode (from the pickle or Broad `results.edb`, depending on input).
- Each match is logged at INFO (`Gene set: <term>`).
- No PNG, PDF, or per-gene-set statistics files are written.
- If `--outputDir` is set, writes `gene_sets.list.txt` (one name per line) and `run_metadata.json` with `list_only: true`.
- If `--outputDir` is omitted, output is log-only (no run directory created).

## Output artifacts

### Plot mode (default)

For each plotted gene set `<term>`:

- `<term>.png` — enrichment plot (300 DPI)
- `<term>.pdf` — vector enrichment plot
- `<term>.txt` — statistics:

  - **GSEApy pickle mode**: from `pre_res.res2d` (`ES`, `NES`, `NOM p-val`, `FDR q-val`, `FWER p-val`, `Tag %`, `Gene %`, `Lead_genes`)
  - **Broad GSEA mode**: from `results.edb` plus optional report TSV fields when present

Run directory also contains:

- `combined_trace_<suffix>.png` / `.pdf` — when `--combineTrace` is set, one multi-pathway trace figure per trailing suffix group (for example `combined_trace_TOP500_UP`)
- `combined_trace_color_map.tsv` — default ChIP factor palette used for combined trace plots (`EP300`, `CBP`, `H3K27AC`, `BRD4` in plot order)
- `combined_trace_gene_set_colors.tsv` — per gene-set color assignment for the combined trace plots in that run
- `run_metadata.json` — run ID, `input_source` (`gseapyPkl` or `broadGsea`), input path, plotted gene sets, gseapy version; Broad runs also record `broad_weight` and optional `combined_trace_stems`

Working directory receives `plotGseapyPrerankEnrichment.log`.

### List-only mode

- Log lines for each resolved gene set
- Optional `gene_sets.list.txt` and `run_metadata.json` when `--outputDir` is provided

## Edge cases

- **Dotted gene set names**: output files use `f"{term}.png"` (not `Path.with_suffix`) so names like `SOS_peaks.1bp.c_2p5.g_100.l_300.closest` are preserved.
- **Partial failures**: missing tokens log warnings; script exits non-zero only if **no** gene sets resolve.
- **`allGeneSets` on large libraries**: can produce hundreds of plots; confirm with the user when invoked by an agent.
- **GSEApy non-significant gene sets**: present in `pre_res.res2d` and plottable even when omitted from default GSEApy `graph_num` exports.
- **Broad non-significant gene sets**: present in `results.edb` and plottable even when omitted from default Broad ES figure exports (`plot_top_x`).
- **Gene sets rejected during Broad filtering**: absent from `results.edb`; list-only or plot requests log a warning and skip them.
- **Wrong input mode**: a GSEApy pickle cannot be passed to `--inGseaDir`, and a Broad output directory cannot be passed to `--inPKL`.

## Environment setup

Conda:

```bash
conda env create -f environment.yml
conda activate gsea-prerank-plot
```

Pip:

```bash
pip install -r requirements.txt
```
