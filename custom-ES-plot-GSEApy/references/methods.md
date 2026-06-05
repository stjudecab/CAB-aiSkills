# Methods: GSEApy prerank enrichment plotting

## Contents

- Input requirements
- CLI reference
- Gene-set name resolution
- Output artifacts
- Edge cases
- Environment setup

## Input requirements

### Pickle file (`--inPKL`)

- Must be a GSEApy prerank **`pre_res`** object serialized with `pickle`.
- Typical naming: `GSEApy_prerank.pre_res.<assay>.<contrast>.pkl`.
- The object must expose gene-set results via `res2d`, `gmt`, or `results` (the script prefers `res2d['Term']`).

### Runtime

- **`gseapy` must be importable** before unpickling. Pickles store a `gseapy.gsea.Prerank` instance; unpickling fails without the package.
- Use a GSEApy version compatible with the environment that created the pickle when possible.

## CLI reference

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--inPKL` | yes | — | Path to input `pre_res` pickle |
| `--geneSetName` | yes | — | Gene set selection (see below) |
| `--listOnly` | no | `False` | List resolved gene sets without plotting |
| `--outputDir` | no | `plots/enrichment/<pkl_stem>/<run_id>/` (plot mode) | Output directory |
| `--figWidth` | no | `6.0` | Plot width (inches) |
| `--figHeight` | no | `7.0` | Plot height (inches) |
| `--logLevel` | no | `INFO` | Logging level |

## Gene-set name resolution

The script resolves `--geneSetName` in this order:

1. **List file**: if the argument is an existing path ending in `.lst` or `.txt`, read one specification per line (skip blank lines and `#` comments).
2. **`allGeneSets`**: if the entire argument equals `allGeneSets`, plot every gene set in the pickle.
3. **Comma-separated tokens**: otherwise split on commas and resolve each token independently.

Per token:

1. Exact match against available gene sets → add that set.
2. Else compile as a **regular expression** and match with `re.search` against all available terms → add all matches.
3. Else log a **warning** that the gene set was not found.

Matched gene sets are de-duplicated while preserving order.

### Examples

| `--geneSetName` | Result |
|-----------------|--------|
| `HALLMARK_APOPTOSIS` | Single exact match |
| `SOS_peaks.*,HALLMARK_APOPTOSIS` | All SOS_peaks terms plus HALLMARK if present |
| `examples/gene_sets_sos_peaks.lst` | Lines from list file |
| `allGeneSets` | All terms in pickle |

## List-only mode (`--listOnly`)

When `--listOnly` is enabled:

- Gene sets are resolved the same way as plot mode.
- Each match is logged at INFO (`Gene set: <term>`).
- No PNG, PDF, or per-gene-set statistics files are written.
- If `--outputDir` is set, writes `gene_sets.list.txt` (one name per line) and `run_metadata.json` with `list_only: true`.
- If `--outputDir` is omitted, output is log-only (no run directory created).

## Output artifacts

### Plot mode (default)

For each plotted gene set `<term>`:

- `<term>.png` — enrichment plot (300 DPI)
- `<term>.pdf` — vector enrichment plot
- `<term>.txt` — statistics from `pre_res.res2d`:

  - `ES`, `NES`
  - `NOM p-val`, `FDR q-val`, `FWER p-val`
  - `Tag %`, `Gene %`
  - `Lead_genes`

Run directory also contains:

- `run_metadata.json` — run ID, input pickle path, plotted gene sets, gseapy version

Working directory receives `plotGseapyPrerankEnrichment.log`.

### List-only mode

- Log lines for each resolved gene set
- Optional `gene_sets.list.txt` and `run_metadata.json` when `--outputDir` is provided

## Edge cases

- **Dotted gene set names**: output files use `f"{term}.png"` (not `Path.with_suffix`) so names like `SOS_peaks.1bp.c_2p5.g_100.l_300.closest` are preserved.
- **Partial failures**: missing tokens log warnings; script exits non-zero only if **no** gene sets resolve.
- **`allGeneSets` on large libraries**: can produce hundreds of plots; confirm with the user when invoked by an agent.

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
