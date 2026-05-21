# Citations and attribution — reproducible-peaks

## Contents

- Layer 1: Skill package
- Layer 2: Bundled code
- Layer 3: Scientific method (ChIP-R)
- Optional upstream tools
- Citation keys
- Copy-paste examples

## Layer 1: Skill package

| Field | Value |
|-------|--------|
| **Role** | Skill author / packager (workflow, documentation, CLI wrappers — **not** the ChIP-R method) |
| **Skill author(s)** | Named in [AUTHORS.md](../../AUTHORS.md) (Skills table) and `SKILL.md` → `metadata.author` |
| **Affiliation** | St Jude Children's Research Hospital (when citing packagers from this collection) |
| **Collection** | CAB-aiSkills skill `reproducible-peaks` |
| **License** | [CC BY-NC-SA 4.0](../../LICENSE.txt) for skill packaging and scripts listed in [AUTHORS.md](../../AUTHORS.md) |

**When to credit:** Referencing the agent skill, repository workflow, or `reproducible_peaks.py` orchestration.

**Repository policy:** [docs/attribution.md](../../docs/attribution.md)

## Layer 2: Bundled code

| Script | Copyright / author (see file header) |
|--------|--------------------------------------|
| `scripts/reproducible_peaks.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/sicer_to_broadpeak.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/logging_support.py` | Wojciech Rosikiewicz && St Jude |

These scripts **invoke** ChIP-R; they do not replace citation of the ChIP-R method.

## Layer 3: Scientific method (ChIP-R)

**Cite this layer** for reproducible peak calling in Methods / supplementary methods.

| Field | Value |
|-------|--------|
| **Tool** | ChIP-R ("chipper") |
| **Software** | [https://github.com/rhysnewell/ChIP-R](https://github.com/rhysnewell/ChIP-R) |
| **Install** | `conda install bioconda::chip-r` or `pip install ChIP-R` |
| **Preprint** | Newell R, Piper M, Boden M, Essebier A, et al. **ChIP-R: a reproducible peak calling pipeline for ChIP-seq data.** *bioRxiv* 2020. [doi:10.1101/2020.11.24.396960](https://doi.org/10.1101/2020.11.24.396960) |

**Suggested Methods wording:**

> Reproducible peaks across replicates were defined with **ChIP-R** (Newell et al., bioRxiv 2020, doi:10.1101/2020.11.24.396960) from MACS2/SICER peak inputs in ENCODE narrowPeak or broadPeak format. Parameters are recorded in `run_metadata.json` and `reproducible_peaks.log`.

Record the **ChIP-R version** from run logs when publishing (e.g. `ChIP-R==1.2.0` from `pip show` or conda list).

## Optional upstream tools

Peak **inputs** are often from MACS2 or SICER. Cite those callers **only if** your manuscript describes peak calling, not only ChIP-R merging:

- **MACS2:** Zhang Y, et al. Model-based Analysis of ChIP-Seq (MACS). *Genome Biol.* 2008.
- **SICER:** Zang C, et al. A clustering approach for identification of enriched domains. *Nat Methods.* 2009.

## Citation keys

Stable keys for `run_metadata.json` and automated reports:

| Key | Layer | Meaning |
|-----|-------|---------|
| `cab_aiskills_reproducible_peaks` | 1 | This skill package |
| `chipr_newell_2020_biorxiv` | 3 | ChIP-R method (required for scientific claims) |

## Copy-paste examples

**Short (figure legend):**

> Reproducible peaks: ChIP-R (Newell et al., bioRxiv 2020). Workflow: CAB-aiSkills `reproducible-peaks` (skill author(s); see AUTHORS.md).

**Methods (recommended):**

> Peak reproducibility across replicates was assessed with ChIP-R v.X (Newell et al., bioRxiv 2020, doi:10.1101/2020.11.24.396960). Inputs were narrowPeak files from MACS2. The analysis workflow used the CAB-aiSkills `reproducible-peaks` skill (skill author(s) per AUTHORS.md; repository URL) for parameter logging and reproducibility; skill authors are not authors of the ChIP-R method.
