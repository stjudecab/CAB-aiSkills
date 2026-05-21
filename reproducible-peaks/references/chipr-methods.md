# ChIP-R methods for reproducible peaks

## Contents

- Tool overview
- Installation
- Input formats
- Calling strategies (four workflows)
- Default parameters
- Outputs
- Attribution and citations

## Tool overview

[ChIP-R](https://github.com/rhysnewell/ChIP-R) ("chipper") combines replicate ChIP-seq (or ATAC-seq) peak sets using a rank-product style statistic over fragmented peak intervals. Inputs must be **ENCODE narrowPeak** or **broadPeak** (see [readme_chipr.md](../../../readme_chipr.md) in the repository root copy).

Entrypoints (any one on `PATH`): `chipr`, `chip-r`, `ChIP-R`.

## Installation

```bash
conda install bioconda::chip-r
# or
pip install ChIP-R
```

## Input formats

| Format | Columns | Typical source |
|--------|---------|----------------|
| narrowPeak | 10 | MACS2 with control (Input/IgG) |
| broadPeak | 9 | MACS2 broad peaks |
| SICER BED | 10 (non-ENCODE semantics) | SICER — **convert before ChIP-R** |

Column definitions follow ENCODE:

- **narrowPeak**: chrom, start, end, name, score, strand, signalValue, pValue, qValue, peak
- **broadPeak**: chrom, start, end, name, score, strand, signalValue, pValue, qValue

## Calling strategies (four workflows)

Choose **one strategy per run** (one target / one condition). Do not mix replicates from different treatments unless the user explicitly requests that design.

### 1. narrowPeak with control (Input/IgG)

- **When**: MACS2 peaks called with control; filenames often lack `noC_`.
- **ChIP-R**: default `--rankmethod pvalue`
- **`-m` (minentries)**: default **`n - 1`** for `n` replicate files (e.g. two replicates → `-m 1`). User may override; avoid `-m 3` unless they ask for very stringent overlap.
- **Note**: Historical lab notes used `-m 3` for extra stringency with control-based narrow peaks; the skill default is **`n - 1`**.

### 2. narrowPeak without control (`noC_`)

- **When**: MACS2 **without** Input/IgG; in-house files often prefixed with `noC_`.
- **ChIP-R**: `--rankmethod signalvalue`
- **`-m`**: default **`n - 1`** unless the user specifies otherwise.

If filenames lack `noC_` but the user states peaks were called without control, use **`noControl`** and confirm.

### 3. broadPeak (MACS2 broad)

- **When**: `.broadPeak` or 9-column MACS2 broad output.
- **ChIP-R**: default `--rankmethod pvalue` (unless user overrides).
- **`-m`**: default **`n - 1`**.

### 4. SICER BED → broadPeak

- **When**: `.sicer.` in the filename or SICER-style 10-column BED (e.g. `...-W200-G600_dom_2_` in the name field).
- **Pre-step**: convert with [scripts/sicer_to_broadpeak.py](../scripts/sicer_to_broadpeak.py) or let [scripts/reproducible_peaks.py](../scripts/reproducible_peaks.py) stage `prepared_inputs/`.
- **ChIP-R**: treat as **broadPeak** after conversion.

See [sicer-conversion.md](sicer-conversion.md) for column mapping.

## Default parameters

| Parameter | Skill default | ChIP-R CLI flag |
|-----------|---------------|-----------------|
| minentries | `n - 1` for n ≥ 2 inputs | `-m` |
| rank method | `pvalue`, or `signalvalue` for no-control narrow | `--rankmethod` |
| alpha | 0.05 | `-a` |
| min peak size | 20 | `-s` |
| dup handling | average | `--duphandling` |

## Outputs

ChIP-R writes files prefixed with `-o` (example prefix `ctcf_rep`):

| File | Role |
|------|------|
| `{prefix}_all.bed` | All intersected peaks (rank-ordered) |
| `{prefix}_optimal.bed` | Optimal / reproducible peak set |
| `{prefix}_log.txt` | Tier counts |

The skill also writes:

- `reproducible_peaks.log` — audit log (commands, decisions, versions)
- `run_metadata.json` — machine-readable run record
- `prepared_inputs/` — staged or converted peak files

## Attribution and citations

Layered attribution (skill packager vs ChIP-R method vs bundled scripts) is defined in [citations.md](citations.md) and [docs/attribution.md](../../docs/attribution.md).

**Scientific method (cite in publications):** ChIP-R — Newell et al., bioRxiv 2020, [doi:10.1101/2020.11.24.396960](https://doi.org/10.1101/2020.11.24.396960). Do not cite the skill author as the ChIP-R method author.
