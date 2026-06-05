---
name: custom-ES-plot-GSEApy
description: >-
  Generates GSEApy prerank GSEA enrichment score (ES) plots and companion
  statistics text files from saved pre_res pickle files. Supports exact gene-set
  names, comma-separated lists, .lst/.txt list files, regex patterns such as
  SOS_peaks.*, allGeneSets, and list-only mode via --listOnly. Use when the user
  asks to plot GSEApy prerank enrichment, ES plots, running enrichment score
  figures, list gene sets in a pre_res pickle, preview regex gene-set matches,
  or post-process GSEApy_prerank.pre_res.*.pkl outputs for selected gene sets.
  Its useful to visualize even the results that were not significant, and thus
  not by deafult included in the original GSEApy results.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.10+ with gseapy, pandas, matplotlib, and rich. GSEApy must be
  importable to unpickle pre_res objects. Local filesystem only; no network
  required after environment setup. Conda env from environment.yml recommended.
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "1.1.0"
  status: stable
  last_reviewed: "2026-06-05"
allowed-tools: shell python
---

# Custom ES plot (GSEApy prerank)

## Purpose

Load a saved GSEApy prerank `pre_res` pickle and produce enrichment score plots (PNG + PDF) plus plain-text statistics for user-selected gene sets.

## When to Use

- The user has **`GSEApy_prerank.pre_res.*.pkl`** (or similar) and wants **enrichment plots** for one or more gene sets.
- The user mentions **GSEApy prerank**, **running enrichment score**, **ES plot**, or **NES plot** from a saved pickle.
- The user wants plots for a **regex subset** (e.g. `SOS_peaks.*`) or a **list file** of gene sets.
- The user wants to **list or preview gene sets** in a pickle (regex match, full inventory, or confirm a name exists) without plotting — use **`--listOnly`**.

## When Not to Use

- The user needs to **run prerank GSEA from scratch** (ranked gene list + GMT) — run GSEApy prerank first, then use this skill on the pickle.
- The user wants **Enrichr over-representation** from a plain gene list — use `pathway-enrichment-enrichr`.
- The pickle is not a GSEApy `Prerank` object or GSEApy cannot be imported in the runtime environment.

## Required Inputs

- **`--inPKL`**: path to a GSEApy prerank `pre_res` pickle file.
- **`--geneSetName`**: gene set selection (exact name, comma-separated names/patterns, `.lst`/`.txt` file, `allGeneSets`, or regex).

## Optional Inputs

- **`--outputDir`**: writable output directory. Default: `plots/enrichment/<pkl_stem>/<run_id>/` next to the pickle.
- **`--figWidth`**, **`--figHeight`**: figure size in inches (defaults `6.0`, `7.0`).
- **`--listOnly`**: list resolved gene sets without plotting (default `False`). Logs each match; optionally writes `gene_sets.list.txt` when `--outputDir` is set.
- **`--logLevel`**: logging level (default `INFO`).

When an **agent** runs this skill, prefer:

```text
agentResults/custom-ES-plot-GSEApy-<YYYYMMDDTHHMMSSZ>/
```

as `--outputDir` unless the user specifies another path.

## Workflow

1. Confirm the pickle path exists and **`gseapy` is installed** (required for unpickling).
2. Parse the user's gene-set request into `--geneSetName` (exact, comma list, list file, regex, or `allGeneSets`).
3. If the user wants to **preview or verify gene sets without plotting**, add **`--listOnly`** and report the logged names (and `gene_sets.list.txt` if `--outputDir` was used).
4. Warn the user if they request **`allGeneSets`** plotting on a large pickle (many plots). For inventory only, use **`--listOnly`** instead.
5. Run from the skill root:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL <path/to/pre_res.pkl> \
  --geneSetName '<selection>' \
  [--listOnly] \
  [--outputDir <output_dir>]
```

6. Read the log for **warnings** about gene sets that were not found; the script continues with valid matches.
7. Return plotted or listed gene sets, output paths, and `run_metadata.json` when an output directory was written.

## Gene-set selection rules

| User intent | `--geneSetName` value |
|---|---|
| One gene set | exact `Term` name from `pre_res.res2d` |
| Several gene sets | comma-separated names and/or regex tokens |
| File of gene sets | path to `.lst` or `.txt` (one spec per line) |
| All gene sets in pickle | `allGeneSets` |
| Pattern match | regex such as `SOS_peaks.*` |

Resolution order per token: exact match → regex match → log warning if nothing matches.

See [references/methods.md](references/methods.md) for details and edge cases.

## Usage examples

Run from the skill root (`scripts/plotGseapyPrerankEnrichment.py`). Replace `/path/to/pre_res.pkl` with the user's pickle path.

### Plot mode

One gene set:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest
```

Regex subset:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName 'SOS_peaks.*'
```

### List-only mode (`--listOnly`)

Preview regex matches (no plots):

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName 'SOS_peaks.*' \
  --listOnly
```

Confirm one gene set exists:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest \
  --listOnly
```

Full inventory written to `gene_sets.list.txt`:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName allGeneSets \
  --listOnly \
  --outputDir ./tmp/gene_set_inventory
```

## Scripts

| Script | Role |
|--------|------|
| [scripts/plotGseapyPrerankEnrichment.py](scripts/plotGseapyPrerankEnrichment.py) | Load pickle, resolve gene sets, plot enrichment or list matches (`--listOnly`), write statistics TXT and run metadata. |

## Output Format

### Plot mode (default)

For each plotted gene set `<term>` under `<outputDir>/`:

| File | Description |
|------|-------------|
| `<term>.png` | Enrichment plot (300 DPI raster) |
| `<term>.pdf` | Enrichment plot (vector) |
| `<term>.txt` | ES, NES, nominal p-value, FDR, FWER, Tag %, Gene %, Lead_genes |
| `run_metadata.json` | Run ID, input pickle, plotted gene sets, gseapy version |
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
- **No gene sets resolved**: verify `Term` names against the pickle (inspect `pre_res.res2d['Term']` or ask the user for the exact name).
- **`allGeneSets` on a large library**: confirm with the user before plotting hundreds of gene sets.

## Attribution

Report credits in three layers (see [references/citations.md](references/citations.md) and [docs/attribution.md](../docs/attribution.md)):

1. **Method:** **GSEA / prerank GSEA** — Subramanian et al., *PNAS* 2005; **GSEApy** — Fang et al., *Bioinformatics* 2022 (doi:[10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)).
2. **Bundled script:** `plotGseapyPrerankEnrichment.py` — Wojciech Rosikiewicz (see script header).
3. **Skill package:** CAB-aiSkills `custom-ES-plot-GSEApy` — skill author in `metadata.author` (orchestration only).

## Further Reading

- [references/methods.md](references/methods.md) — CLI flags, gene-set resolution, outputs.
- [references/citations.md](references/citations.md) — layered attribution and copy-paste citations.
- [README.md](README.md) — install, quick start, user prompt examples.
