<p align="center">
  <img src="assets/CAB-aiSkills_genomic-set-analysis.svg" alt="genomic-set-analysis skill badge" width="520" />
</p>

# Genomic Set Analysis (Intervene wrapper) — Agent Skill

Portable **Agent Skill** for **order-independent overlap and combinatorial analysis** of genomic
region sets (ChIP-seq, ATAC-seq, CUT&Tag, CUT&RUN, narrowPeak/broadPeak/BED) or gene sets (GMT)
using **[Intervene](https://github.com/asntech/intervene)** (Venn / UpSet / pairwise). It builds a
union of elements, a membership matrix, and mutually exclusive per-sector files, then optionally
chains the **`genomic-regions-annotation`** skill for nearby-gene annotation and the
**`pathway-enrichment-enrichr`** skill for Enrichr pathway enrichment of **both** the intersection
sectors and the original inputs, plus gated expression summaries. Agent instructions are in
[SKILL.md](SKILL.md).

This is the portable, HPC-independent successor to the in-house `IntervenePeaksCombine.py` wrapper.
LSF/`bsub` scheduling has been removed; annotation and pathway enrichment are delegated to sibling
skills, and motif enrichment / deeptools heatmaps are **planned but not yet available**.

## Environment

This skill depends on **Bioconda binaries** (`intervene`, `bedtools`) plus Python packages, so it
uses a **persistent Conda/micromamba prefix**—not a plain venv and not a global install.

On first run, `scripts/ensure_env.sh` creates the environment once under your home cache and
reuses it on later runs:

| Item | Path |
|------|------|
| Cache root | `~/.cache/ai-skills-env/genomic-set-analysis/` |
| Environment prefix | `~/.cache/ai-skills-env/genomic-set-analysis/conda-env/` |

```bash
cd genomic-set-analysis
bash scripts/ensure_env.sh                     # create if missing; no-op if ready
bash scripts/run_with_skill_env.sh scripts/intervene_peaks_combine.py --help
# or invoke Python scripts directly (they auto-bootstrap via scripts/skill_env.py):
python scripts/intervene_peaks_combine.py --help
```

**Force a clean rebuild** after `environment.yml` changes or if the env is corrupted:

```bash
bash scripts/ensure_env.sh --force-rebuild
# or:
rm -rf ~/.cache/ai-skills-env/genomic-set-analysis
```

- **Python 3.8–3.9 is required.** Intervene 0.6.4 imports `collections.Iterable`, which was removed
  in Python 3.10, so the interpreter must stay `<3.10`. `environment.yml` pins this for you.
- **Prerequisite:** micromamba, mamba, or conda on `PATH` (the helper picks micromamba first when
  available, otherwise mamba, then conda).
- **Manual install** (only if you cannot use the cache helper):

```bash
conda env create -p ~/.cache/ai-skills-env/genomic-set-analysis/conda-env -f environment.yml
```

- **Python-only packages** (into an existing Python 3.8/3.9 env without Bioconda tools):

```bash
pip install -r requirements.txt
```

> On headless machines, point matplotlib/fontconfig at writable cache dirs to silence font
> warnings, e.g. `export MPLCONFIGDIR="$PWD/tmp/mplcache"`.

- **Sibling skills** (for the add-ons): `genomic-regions-annotation` (annotation) and
  `pathway-enrichment-enrichr` (Enrichr; needs HTTPS to `maayanlab.cloud`).

## Install for Cursor or other agent clients

- **Project skill:** copy or symlink this folder so the client discovers a directory named
  `genomic-set-analysis` containing `SKILL.md` (for example `.cursor/skills/genomic-set-analysis/`).
- **Invoke** by skill name `genomic-set-analysis`, or ask the agent to overlap peaks / make a Venn
  or UpSet of BED files / run "IntervenePeaksCombine".

## Quick start

Run from **this directory** (`genomic-set-analysis`) unless you pass absolute paths.

### Overlap three peak sets (Venn + UpSet)

```bash
python scripts/intervene_peaks_combine.py \
  -i examples/peaksFactorA.bed,examples/peaksFactorB.bed,examples/peaksFactorC.bed \
  -n FactorA,FactorB,FactorC \
  -o factorOverlap \
  --outputDir agentResults \
  --toPlot venn,upset
```

Outputs land in `agentResults/factorOverlap.intervene/` (matrix, merged BEDs, plots, `sets/`,
`setsCounted/`, `originalInputs/`, `setLabelsManifest.tsv`, `run_metadata.json`).

### Overlap gene sets from a GMT

```bash
python scripts/intervene_peaks_combine.py \
  -i examples/geneSets.gmt \
  -o geneSetOverlap \
  --outputDir agentResults \
  --toPlot venn,upset
```

Also writes `intersections.gmt` and `originalSets.gmt` for direct pathway enrichment.

### Short labels for long file or set names

Labels are embedded in many output filenames. When basenames or GMT set names are long, the agent
should derive short unique analysis labels (target ≤15 characters) and pass them via `-n` or a
manifest TSV. The script writes `setLabelsManifest.tsv` mapping `original_label` →
`analysis_label`. Skip shortening when the user already supplied short names or labels are already
≤15 characters and unique. See [SKILL.md](SKILL.md#short-set-labels-important).

### Gated expression summary

```bash
python scripts/expression_summary.py \
  --geneSetsGmt agentResults/geneSetOverlap.intervene/intersections.gmt \
  --exprMatrixFile examples/expressionMatrix.tsv \
  --exprGeneNameCol geneSymbol \
  --metadataFile examples/expressionMetadata.tsv \
  --exprYaxis TPM \
  --outputDir agentResults/geneSetOverlap.intervene/expressionSummary
```

### Annotation and pathway enrichment (chained skills)

See [references/addons-and-chaining.md](references/addons-and-chaining.md). Annotation and
pathway enrichment require an **explicitly stated genome build**; the agent will ask if missing.
Unless the user overrides, pathway enrichment runs only on the **top 10 intersection sectors with
≥5 genes** and on **original sets with ≥5 genes**, using `scripts/filter_gmt_for_pathway.py` to
write filtered GMTs and filter-manifest TSVs before calling Enrichr.

## Add-on availability

| Module | Status |
|--------|--------|
| Overlap + Venn/UpSet/pairwise + matrix + sectors | Available (local) |
| Nearby-gene annotation | Available via `genomic-regions-annotation` |
| Pathway enrichment (intersections + originals) | Available via `pathway-enrichment-enrichr`; default filter: top 10 intersections with ≥5 genes, originals with ≥5 genes |
| Expression summaries | Available, gated on matrix + conditions |
| Motif enrichment (HOMER) | Planned — not available |
| deeptools heatmaps / tornado | Planned — not available |

## Layout

| Path | Role |
|------|------|
| [SKILL.md](SKILL.md) | Agent workflow, genome-build safety, chaining, outputs |
| [scripts/ensure_env.sh](scripts/ensure_env.sh) | Persistent Conda env under `~/.cache/ai-skills-env/genomic-set-analysis/` |
| [scripts/run_with_skill_env.sh](scripts/run_with_skill_env.sh) | Run commands inside the cached skill env |
| [scripts/skill_env.py](scripts/skill_env.py) | Python bootstrap for CLI scripts |
| [scripts/intervene_peaks_combine.py](scripts/intervene_peaks_combine.py) | Core overlap wrapper |
| [scripts/filter_gmt_for_pathway.py](scripts/filter_gmt_for_pathway.py) | Filter GMTs before Enrichr (default ≥5 genes; top 10 intersections) |
| [scripts/expression_summary.py](scripts/expression_summary.py) | Gated expression boxplots/heatmaps |
| [references/](references/) | Methods, inputs/outputs, chaining, citations |
| [examples/](examples/) | Example BEDs, GMT, manifest, expression matrix, evaluation prompts |
| [tests/](tests/) | Pytest suite (GMT-mode + helpers; no external binaries needed) |
| [assets/](assets/) | Skill badge SVG |

## Testing

```bash
cd genomic-set-analysis
bash scripts/ensure_env.sh
GENOMIC_SET_ANALYSIS_SKIP_ENV_BOOTSTRAP=1 python -m pytest tests -q
python scripts/intervene_peaks_combine.py --help
python scripts/expression_summary.py --help
```

Tests that would need the Intervene/BEDTools binaries are avoided; GMT mode runs with plotting
disabled, so the suite passes without external tools. The full workflow (genomic overlap, GMT
overlap, and expression summary) has been verified end to end on the bundled `examples/` data.

## Reproducibility

Every run writes `run_metadata.json` with a UTC run ID, the exact command, resolved inputs and
parameters, and the versions of Intervene, BEDTools, pybedtools, pandas, numpy, and Python; the
executed Intervene commands are mirrored in `logs/commands.log`. Report the genome build used for
any annotation/pathway step. Do not overwrite an existing run directory without `--overwrite`.

## Citation

Use [layered attribution](../docs/attribution.md); do not cite only the skill author for the science.

| Layer | Credit |
|-------|--------|
| **Skill package** | Skill author(s) in [AUTHORS.md](../AUTHORS.md); CAB-aiSkills `genomic-set-analysis` |
| **Method** | **Intervene** — Khan & Mathelier, *BMC Bioinformatics* 2017 ([doi:10.1186/s12859-017-1708-7](https://doi.org/10.1186/s12859-017-1708-7)); **BEDTools** — Quinlan & Hall 2010 |

Full wording and chained-skill citations: [references/citations.md](references/citations.md).

**Methods (one sentence):**

> Genomic region sets were overlapped in an order-independent manner with Intervene (Khan &
> Mathelier, 2017) and BEDTools/pybedtools, via the CAB-aiSkills `genomic-set-analysis` skill
> (skill author(s) per [AUTHORS.md](../AUTHORS.md)); annotation and Enrichr pathway enrichment used
> the `genomic-regions-annotation` and `pathway-enrichment-enrichr` skills with the stated genome build.

## Maintainer

Toolbox curator and current skill author(s): [AUTHORS.md](../AUTHORS.md). St Jude Children's Research Hospital.

**License:** [CC BY-NC-SA 4.0](../LICENSE.txt).
