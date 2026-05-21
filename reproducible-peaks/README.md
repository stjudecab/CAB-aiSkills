
<p align="center">
  <img src="assets/CAB-aiSkills_reproducible-peaks.svg" alt="reproducible-peaks skill badge" width="520" />
</p>

# Reproducible Peaks (ChIP-R) — Agent Skill

Portable **Agent Skill** for generating **reproducible ChIP-seq / ATAC-seq peak sets** across biological replicates using **[ChIP-R](https://github.com/rhysnewell/ChIP-R)**. Supports **narrowPeak** and **broadPeak** (MACS2) and **SICER BED** (converted automatically), with audit logging aligned with other CAB-aiSkills CLI tools. Agent-facing instructions are in [SKILL.md](SKILL.md).

## Environment

- **Python** 3.9 or newer
- **ChIP-R** on `PATH` (`chipr`, `chip-r`, or `ChIP-R`)
- **Dependencies:**

```bash
cd reproducible-peaks
pip install -r requirements.txt
```

Recommended install for ChIP-R:

```bash
conda install bioconda::chip-r
```

## Install for Cursor or other agent clients

- **Project skill:** Copy or symlink this folder so the client discovers a directory named `reproducible-peaks` containing `SKILL.md` (for example `.cursor/skills/reproducible-peaks/`).
- **Invoke** by skill name `reproducible-peaks` or by asking the agent to generate reproducible ChIP-seq peaks with ChIP-R, as described in [SKILL.md](SKILL.md).

## Quick start

Run from **this directory** (`reproducible-peaks`) unless you pass absolute paths.

### CTCF example (bundled ENCODE peaks)

```bash
python scripts/reproducible_peaks.py \
  --inputFiles "examples/CTCF.ENCFF412MBV.bed,examples/CTCF.ENCFF507TTK.bed" \
  --outputDir "agentResults/reproducible-peaks-$(date -u +%Y%m%dT%H%M%SZ)" \
  --outputPrefix "CTCF_ENCFF" \
  --overwrite
```

With two replicates, the default **`-m`** is **`1`** (`n - 1`). Outputs include `CTCF_ENCFF_optimal.bed` and `reproducible_peaks.log`.

### Dry run (validate only)

```bash
python scripts/reproducible_peaks.py \
  --inputFiles "examples/CTCF.ENCFF412MBV.bed,examples/CTCF.ENCFF507TTK.bed" \
  --outputDir "tmp/reproducible-peaks-dryrun" \
  --dryRun \
  --overwrite
```

### SICER → broadPeak only

```bash
python scripts/sicer_to_broadpeak.py \
  --input /path/to/sample.sicer.filter.bed \
  --output /path/to/sample.broadPeak
```

### No-control narrowPeak (`noC_`)

```bash
python scripts/reproducible_peaks.py \
  --inputFiles "/path/noC_rep1.narrowPeak,/path/noC_rep2.narrowPeak" \
  --outputDir "agentResults/reproducible-peaks-20260520T120000Z" \
  --callingStrategy noControl \
  --overwrite
```

## Layout

| Path | Role |
|------|------|
| [assets/](assets/) | Skill badge SVG |
| [SKILL.md](SKILL.md) | Agent workflow and safety |
| [scripts/reproducible_peaks.py](scripts/reproducible_peaks.py) | Main ChIP-R wrapper |
| [scripts/sicer_to_broadpeak.py](scripts/sicer_to_broadpeak.py) | SICER conversion utility |
| [references/](references/) | Methods, citations, SICER conversion, file-selection checks |
| [examples/](examples/) | CTCF peak BEDs and evaluation prompts |
| [tests/](tests/) | Pytest suite |

## User-facing prompt examples

Example prompts a user might type and how the agent should interpret them.
See [examples/evaluation-prompts.md](examples/evaluation-prompts.md) for detailed expected behavior.

| User prompt | Interpretation |
|---|---|
| "Generate reproducible peaks for CTCF using files in `CAB-aiSkills/reproducible-peaks/examples`" | List both CTCF `.bed` files; confirm no extra conditions; run `reproducible_peaks.py` with default `-m 1`, strategy `withControl` unless user says no control |
| "Run ChIP-R on my H3K27ac narrowPeak replicates in `./peaks`" | Inventory `*.narrowPeak`; group by condition; ask if multiple conditions present; then run CLI with logged metadata |
| "These MACS2 peaks were called without Input — file names start with `noC_`" | Use `--callingStrategy noControl` or auto-detect; `--rankMethod signalvalue` |
| "Merge SICER broad peaks from rep1 and rep2 into reproducible peaks" | Detect `.sicer.` BED; convert to broadPeak; run ChIP-R with `-m n-1` |
| "Use ChIP-R with `-m 2` on my four replicate narrowPeak files" | Honor user `-m 2` via `--minEntries 2`; still verify single condition |
| "Make reproducible peaks from everything in my peaks folder" | **Ambiguous** — list files, infer targets/conditions, ask user which subset before running |
| "Call peaks from my BAMs then get reproducible peaks" | **Out of scope** — run MACS2/SICER first; suggest this skill after peak files exist |

## Testing

```bash
cd reproducible-peaks
pip install -r requirements.txt
python scripts/reproducible_peaks.py --help
python -m pytest tests -q
```

Integration tests that invoke ChIP-R are skipped if `chipr` is not on `PATH`.

## Citation

Use [layered attribution](../docs/attribution.md); do not cite only the skill author for the science.

| Layer | Credit |
|-------|--------|
| **Skill package** | Skill author(s) in [AUTHORS.md](../AUTHORS.md); CAB-aiSkills `reproducible-peaks` (workflow and CLI) |
| **Method** | **ChIP-R** — Newell R, et al. bioRxiv 2020. [doi:10.1101/2020.11.24.396960](https://doi.org/10.1101/2020.11.24.396960) |

Full wording and citation keys: [references/citations.md](references/citations.md).

**Methods (one sentence):**

> Reproducible peaks were called with ChIP-R (Newell et al., bioRxiv 2020, doi:10.1101/2020.11.24.396960). The run used the CAB-aiSkills `reproducible-peaks` skill (skill author(s) per [AUTHORS.md](../AUTHORS.md)) for orchestration and logging.

## Maintainer

Toolbox curator and current skill author(s): [AUTHORS.md](../AUTHORS.md). St Jude Children's Research Hospital.

**License:** [CC BY-NC-SA 4.0](../LICENSE.txt).
