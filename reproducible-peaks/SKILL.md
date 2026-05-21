---
name: reproducible-peaks
description: >-
  Generate reproducible ChIP-seq or ATAC-seq peaks across replicates with ChIP-R
  from narrowPeak, broadPeak, or SICER BED inputs. Infers MACS2 with/without
  control (noC_), broad peaks, and SICER conversion; logs commands and environment
  for reproducibility. Use when the user asks for reproducible peaks, ChIP-R,
  ChIP-seq replicate overlap, narrowPeak/broadPeak merging, or CTCF/histone
  replicate peak sets.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires ChIP-R (conda bioconda::chip-r or pip install ChIP-R), Python 3.9+,
  rich. Local filesystem only; no network required for analysis after install.
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "0.1.0"
  status: draft
  last_reviewed: "2026-05-20"
allowed-tools: shell python
---

# Reproducible Peaks (ChIP-R)

## Purpose

Run **ChIP-R** on replicate peak files to produce a **reproducible peak set** with full audit logging (commands, parameters, package versions, and input decisions). Supports MACS2 **narrowPeak** (with or without control), **broadPeak**, and **SICER BED** (converted to broadPeak first).

## When to Use

- User asks for **reproducible peaks**, **ChIP-R**, or **chipr** on ChIP-seq / ATAC-seq replicates.
- Inputs are **narrowPeak**, **broadPeak**, or **SICER** `.bed` files.
- User names a **target** (e.g. CTCF) and a folder of peak files.

## When Not to Use

- **Peak calling** from BAMs (use MACS2/SICER pipelines first).
- **IDR** specifically requested (different tool; mention ChIP-R as an alternative only if appropriate).
- **Differential binding** between conditions (not replicate concordance).
- Merging peaks across **different conditions** without explicit user approval.

## Required Inputs

- **Replicate peak files** (≥2 recommended): paths to existing files in narrowPeak, broadPeak, or SICER BED format.
- **Scope**: one biological condition and one target per run (see sanity checks).

## Optional Inputs

- **`--minEntries`**: ChIP-R `-m` (default **`n - 1`** for `n` input files, `n ≥ 2`).
- **`--rankMethod`**: override `pvalue` / `qvalue` / `signalvalue`.
- **`--callingStrategy`**: `auto`, `withControl`, `noControl`, `broadPeak`, `sicer`.
- **`--outputDir`**: run directory (prefer `agentResults/reproducible-peaks-<runId>/`).
- **`--outputPrefix`**: ChIP-R output prefix (default `reproducible_peaks`).
- **`--dryRun`**: validate and log only.

## Workflow

### Step 1 — Inventory and confirm files

1. List peak files in the user directory (or paths they gave).
2. Filter to the requested **target** and **condition** (e.g. CTCF only, one treatment).
3. Apply [references/file-selection-and-sanity-checks.md](references/file-selection-and-sanity-checks.md):
   - Warn on duplicate replicate IDs across different conditions.
   - If ambiguous, **ask the user** which files to include before running.

### Step 2 — Detect format and calling strategy

Read [references/chipr-methods.md](references/chipr-methods.md):

| Situation | Strategy | ChIP-R notes |
|-----------|----------|--------------|
| narrowPeak, MACS2 **with** control | `withControl` | `--rankmethod pvalue` (default) |
| narrowPeak, **`noC_`** or user says no control | `noControl` | `--rankmethod signalvalue` |
| broadPeak / 9 columns | `broadPeak` | default rank `pvalue` |
| SICER BED | `sicer` | convert → broadPeak, then ChIP-R |

Inspect headers/sample rows; do not assume `.bed` is narrowPeak without checking column count.

### Step 3 — Set parameters

- **`-m`**: default **`n - 1`** for `n` replicate files unless the user specifies (do not use `-m 3` unless requested).
- Review [readme_chipr.md](../../readme_chipr.md) (repository copy) for `minentries`, `size`, and rank options.
- Record decisions in the run log.

### Step 4 — Run the CLI

From the skill root (`reproducible-peaks/`):

```bash
python scripts/reproducible_peaks.py \
  --inputFiles "/abs/rep1.narrowPeak,/abs/rep2.narrowPeak" \
  --outputDir "/abs/agentResults/reproducible-peaks-20260520T120000Z" \
  --outputPrefix "CTCF_reproducible" \
  --overwrite
```

Use **`--dryRun`** first when validating a new file set.

### Step 5 — Verify outputs

1. Exit code **0**.
2. ChIP-R products: `{prefix}_optimal.bed`, `{prefix}_all.bed`, `{prefix}_log.txt`.
3. Skill artifacts: `reproducible_peaks.log`, `run_metadata.json`, `prepared_inputs/`.
4. Summarize peak counts and paths for the user.

## Scripts

| Script | Role |
|--------|------|
| [scripts/reproducible_peaks.py](scripts/reproducible_peaks.py) | Validate inputs, convert SICER if needed, run ChIP-R, write metadata. |
| [scripts/sicer_to_broadpeak.py](scripts/sicer_to_broadpeak.py) | Standalone SICER → broadPeak conversion. |
| [scripts/logging_support.py](scripts/logging_support.py) | Rich console + audit file logging. |

## Output Format

Under `--outputDir`:

| Artifact | Description |
|----------|-------------|
| `{outputPrefix}_optimal.bed` | Primary reproducible peak set (ChIP-R) |
| `{outputPrefix}_all.bed` | All ranked intersected peaks |
| `{outputPrefix}_log.txt` | ChIP-R tier statistics |
| `reproducible_peaks.log` | Full audit trail |
| `run_metadata.json` | Run ID, command, decisions, inputs |
| `prepared_inputs/` | Staged or converted peak files |

## Quality Checks

- All input paths exist and share one calling strategy.
- No non-finite numeric fields in narrow/broad peaks.
- Replicate naming does not suggest mixed conditions (or user confirmed).
- `chipr` available on PATH (or user approved install).
- Log contains command, `-m`, `--rankmethod`, and package versions.

## Failure and Escalation

- Missing/ambiguous files → ask user; do not guess alternate peaks.
- Mixed conditions in replicate IDs → stop and clarify.
- Unknown format → ask user for caller (MACS2 vs SICER) or provide conversion.
- ChIP-R not installed → document install commands; do not claim success.

## Attribution

Report credits in **three layers** (see [references/citations.md](references/citations.md) and [docs/attribution.md](../docs/attribution.md)):

1. **Method:** **ChIP-R** (Newell et al., bioRxiv 2020) — required in Methods for reproducible peak claims.
2. **Skill package:** CAB-aiSkills `reproducible-peaks` — credit **skill author(s)** from [AUTHORS.md](../AUTHORS.md) and `metadata.author` in this file (workflow/orchestration only; **not** the ChIP-R method).
3. **Bundled scripts:** per-file headers in `scripts/` (packager copyright on wrappers).

`run_metadata.json` includes `citation_keys` and an `attribution` block. Do not tell the user to cite only the skill author for the science.

## Resources

- [references/citations.md](references/citations.md) — layered attribution and copy-paste citations.
- [references/chipr-methods.md](references/chipr-methods.md) — strategies and defaults.
- [references/sicer-conversion.md](references/sicer-conversion.md) — SICER → broadPeak.
- [references/file-selection-and-sanity-checks.md](references/file-selection-and-sanity-checks.md) — file picking and warnings.
- [README.md](README.md) — install, examples, prompt table.
- [examples/evaluation-prompts.md](examples/evaluation-prompts.md) — expected agent behavior.

## Examples

Bundled CTCF ENCODE peak files (10-column BED, narrowPeak-like):

- `examples/CTCF.ENCFF412MBV.bed`
- `examples/CTCF.ENCFF507TTK.bed`

Example (two replicates → `-m 1`):

```bash
python scripts/reproducible_peaks.py \
  --inputFiles "examples/CTCF.ENCFF412MBV.bed,examples/CTCF.ENCFF507TTK.bed" \
  --outputDir "agentResults/reproducible-peaks-20260520T120000Z" \
  --outputPrefix "CTCF_ENCFF" \
  --overwrite
```
