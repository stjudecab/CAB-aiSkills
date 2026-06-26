---
name: custom-ES-plot-GSEApy
description: >-
  Generates GSEA enrichment score (ES) plots and companion statistics text files
  from saved GSEApy prerank pre_res pickle files or Broad Institute GSEA desktop
  output directories. Supports exact gene-set names, comma-separated lists,
  .lst/.txt list files, regex patterns such as SOS_peaks.*, allGeneSets, and
  list-only mode via --listOnly. Use when the user asks to plot GSEApy prerank
  enrichment from a pre_res pickle, replot Broad GSEA ES figures from a GSEA
  output directory, running enrichment score figures, list gene sets in a
  pre_res pickle or Broad GSEA output, preview regex gene-set matches, or
  post-process GSEApy_prerank.pre_res.*.pkl or *.GseaPreranked.* output for
  selected gene sets. Useful to visualize results omitted from default top-set
  figure exports (GSEApy graph_num or Broad plot_top_x), including
  non-significant gene sets.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.10+ with gseapy, pandas, matplotlib, and rich. GSEApy must be
  importable for both input modes (pickle unpickling and Broad ES replotting).
  Local filesystem only; no network required after environment setup. Conda env
  from environment.yml recommended.
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "1.2.0"
  status: stable
  last_reviewed: "2026-06-15"
allowed-tools: shell python
---

# Custom ES plot (GSEApy prerank & Broad GSEA)

## Purpose

Produce enrichment score plots (PNG + PDF) and plain-text statistics for user-selected gene sets from either:

1. a saved **GSEApy prerank `pre_res` pickle**, or
2. a **Broad Institute GSEA desktop output directory** (the folder that contains `edb/`).

## When to Use

- The user has **`GSEApy_prerank.pre_res.*.pkl`** and wants enrichment plots for specific gene sets.
- The user has a **Broad GSEA output directory** (for example `48h.GseaPreranked.<timestamp>/`) and wants ES plots for gene sets beyond the default `plot_top_x` figures.
- The user mentions **GSEApy prerank**, **Broad GSEA**, **running enrichment score**, or **ES plot** for selected gene sets.
- The user wants plots for a **regex subset** (e.g. `SOS_peaks.*`) or a **list file** of gene sets.
- The user wants to **list or preview gene sets** without plotting — use **`--listOnly`**.

## When Not to Use

- The user needs to **run prerank GSEA from scratch** (ranked gene list + GMT) — run GSEApy prerank or Broad GSEA first, then use this skill.
- The user wants **Enrichr over-representation** from a plain gene list — use `pathway-enrichment-enrichr`.
- For GSEApy pickle mode: the pickle is not a GSEApy `Prerank` object or GSEApy cannot be imported.
- For Broad mode: the directory lacks `edb/results.edb`, `edb/*.rnk`, or `edb/gene_sets.gmt`.

## Required Inputs

Choose **one** input source (mutually exclusive):

| Input mode | Flag | Description |
|------------|------|-------------|
| GSEApy pickle | **`--inPKL`** | Path to a GSEApy prerank `pre_res` pickle file. |
| Broad GSEA | **`--inGseaDir`** | Path to a Broad GSEA desktop output directory (must contain `edb/`). |

Always required:

- **`--geneSetName`**: gene set selection (exact name, comma-separated names/patterns, `.lst`/`.txt` file, `allGeneSets`, or regex).

## Optional Inputs

- **`--outputDir`**: writable output directory. Default: `plots/enrichment/<input_stem>/<run_id>/` next to the input pickle or Broad GSEA directory.
- **`--figWidth`**, **`--figHeight`**: figure size in inches (defaults `6.0`, `7.0`).
- **`--weight`**: Broad GSEA weighted score exponent (`0`, `1`, `1.5`, `2`). Default: infer from the Broad `.rpt` file or `1.0`. Ignored for GSEApy pickle mode.
- **`--listOnly`**: list resolved gene sets without plotting (default `False`). Logs each match; optionally writes `gene_sets.list.txt` when `--outputDir` is set.
- **`--logLevel`**: logging level (default `INFO`).

When an **agent** runs this skill, prefer:

```text
agentResults/custom-ES-plot-GSEApy-<YYYYMMDDTHHMMSSZ>/
```

as `--outputDir` unless the user specifies another path.

## Workflow

1. Determine the input mode:
   - **`--inPKL`** when the user provides a GSEApy `pre_res` pickle.
   - **`--inGseaDir`** when the user provides a Broad GSEA output folder.
2. Confirm the input path exists and **`gseapy` is installed**.
3. Parse the user's gene-set request into `--geneSetName` (exact, comma list, list file, regex, or `allGeneSets`).
4. If the user wants to **preview or verify gene sets without plotting**, add **`--listOnly`** and report the logged names (and `gene_sets.list.txt` if `--outputDir` was used).
5. Warn the user if they request **`allGeneSets`** plotting on a large library (many plots). For inventory only, use **`--listOnly`** instead.
6. Run from the skill root:

**GSEApy pickle mode:**

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL <path/to/pre_res.pkl> \
  --geneSetName '<selection>' \
  [--listOnly] \
  [--outputDir <output_dir>]
```

**Broad GSEA mode:**

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir <path/to/GseaPreranked.output_dir> \
  --geneSetName '<selection>' \
  [--listOnly] \
  [--outputDir <output_dir>] \
  [--weight 1]
```

7. Read the log for **warnings** about gene sets that were not found; the script continues with valid matches.
8. Return plotted or listed gene sets, output paths, and `run_metadata.json` when an output directory was written.

## Gene-set selection rules

| User intent | `--geneSetName` value |
|---|---|
| One gene set | exact `Term` name from `pre_res.res2d` (GSEApy pickle) or `results.edb` (Broad GSEA) |
| Several gene sets | comma-separated names and/or regex tokens |
| File of gene sets | path to `.lst` or `.txt` (one spec per line) |
| All gene sets in input | `allGeneSets` |
| Pattern match | regex such as `SOS_peaks.*` |

Resolution order per token: exact match → regex match → log warning if nothing matches.

See [references/methods.md](references/methods.md) for details and edge cases.

## Usage examples

Run from the skill root (`scripts/plotGseapyPrerankEnrichment.py`).

### GSEApy pickle — one gene set

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest
```

### Broad GSEA — one gene set (significant or not)

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName REACTOME_HEME_SIGNALING
```

### Broad GSEA — regex subset

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName 'CHIP.BRD4.*48H.*UP'
```

### List-only mode (`--listOnly`)

Preview regex matches in a Broad GSEA directory:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName 'REACTOME_.*' \
  --listOnly
```

## Scripts

| Script | Role |
|--------|------|
| [scripts/plotGseapyPrerankEnrichment.py](scripts/plotGseapyPrerankEnrichment.py) | CLI entrypoint: resolve gene sets, plot enrichment or list matches (`--listOnly`), write statistics TXT and run metadata. |
| [scripts/broadGseaInput.py](scripts/broadGseaInput.py) | Parse Broad GSEA `edb/` artifacts and render ES plots via GSEApy. |

## Output Format

### Plot mode (default)

For each plotted gene set `<term>` under `<outputDir>/`:

| File | Description |
|------|-------------|
| `<term>.png` | Enrichment plot (300 DPI raster) |
| `<term>.pdf` | Enrichment plot (vector) |
| `<term>.txt` | ES, NES, nominal p-value, FDR, FWER, Tag %, Gene %, Lead_genes (when available) |
| `run_metadata.json` | Run ID, input source (`gseapyPkl` or `broadGsea`), plotted gene sets, gseapy version |
| `plotGseapyPrerankEnrichment.log` | Audit log in the working directory |

Gene set names may contain dots; output filenames preserve the full `Term` string.

### List-only mode (`--listOnly`)

- Logs each resolved gene set at INFO level.
- Does **not** write PNG, PDF, or per-gene-set statistics files.
- With `--outputDir`: writes `gene_sets.list.txt` and `run_metadata.json` (`list_only: true`).

## Quality Checks

- Script exits with code 0 and at least one gene set resolved.
- Plot mode: `run_metadata.json` lists plotted gene sets; each has `.png`, `.pdf`, and `.txt`.
- List-only mode: gene set names appear in the log; optional `gene_sets.list.txt` when `--outputDir` is set.
- Log contains warnings for any non-matching `--geneSetName` tokens.
- Non-zero exit when no gene sets resolve.

## Failure and Escalation

- **`ModuleNotFoundError: gseapy`**: create the Conda env from [environment.yml](environment.yml) or `pip install -r requirements.txt`.
- **No gene sets resolved**: verify `Term` names against the pickle (`pre_res.res2d['Term']`) or Broad `results.edb` / report TSV files.
- **Broad directory missing `edb/`**: confirm the user passed the GSEA output folder, not only the parent `out` directory.
- **`allGeneSets` on a large library**: confirm with the user before plotting hundreds of gene sets.

## Attribution

Report credits in three layers (see [references/citations.md](references/citations.md) and [docs/attribution.md](../docs/attribution.md)). Use the **GSEApy pickle** or **Broad GSEA** copy-paste methods paragraph that matches the input mode actually used:

1. **Method:** **GSEA / prerank GSEA** — Subramanian et al., *PNAS* 2005; **GSEApy** — Fang et al., *Bioinformatics* 2022 (doi:[10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)).
2. **Bundled scripts:** `plotGseapyPrerankEnrichment.py`, `broadGseaInput.py` — Wojciech Rosikiewicz (see script headers).
3. **Skill package:** CAB-aiSkills `custom-ES-plot-GSEApy` — skill author in `metadata.author` (orchestration only).

## Further Reading

- [references/methods.md](references/methods.md) — CLI flags, input modes, gene-set resolution, outputs.
- [references/citations.md](references/citations.md) — layered attribution; separate copy-paste methods text for GSEApy pickle vs Broad GSEA input.
- [README.md](README.md) — install, quick start, user prompt examples.
