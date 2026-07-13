<p align="center">
  <img src="assets/CAB-aiSkills_genomic_regions_annotation.svg" alt="genomic regions annotation skill badge" width="520" />
</p>

# Genomic Regions Annotation Pipeline — Agent Skill

Portable skill for annotating genomic regions from epigenetic NGS (ATAC-seq, ChIP-seq, CUT&Tag, CUT&RUN, differential peaks) to:

1. **Nearby genes**
2. **Genomic features** (exclusive cascading assignment)
3. **Chromatin states** (ChromHMM Roadmap, Segway/ENCODE, or custom dense BED)

Agent instructions: [SKILL.md](SKILL.md).

| Mode | Methods | Primary scripts |
|------|---------|-----------------|
| Genes | [references/methods-gene-annotation.md](references/methods-gene-annotation.md) | `voom2anno.sh` via wrapper |
| Genomic features | [references/methods-genomic-features.md](references/methods-genomic-features.md) | `annotateGenomicFeatures.py` → `OrganizeAnnotationResults.py` |
| Chromatin states | [references/methods-chromatin-states.md](references/methods-chromatin-states.md) | `prepare_chromatin_model.py` → `BEDinContext.py` (**no** OrganizeAnnotationResults) |

Chromatin ops checklist: [references/chromatin-states-workflow.md](references/chromatin-states-workflow.md).

---

## Environment

### Persistent Conda cache (preferred)

```bash
bash scripts/ensure_env.sh
```

| Item | Location |
|------|----------|
| Env prefix | `~/.cache/cursor-skills/genomic-regions-annotation/conda-env/` |
| Spec | `environment/epi_anno_env.yml` |
| Force rebuild | `bash scripts/ensure_env.sh --force-rebuild` |

Requires host `micromamba`, `mamba`, or `conda`. Includes `bedtools`, `pybedtools`, `natsort`, `ucsc-liftover`, plotly/kaleido, etc.

Legacy wrapper flags (`--create-conda-env`, `--conda-prefix`) still work for the gene/feature pipeline.

### Chromatin model cache (skill-local, gitignored)

Prepared dense BEDs live under `cache/{collection}_{genome}_dense.bed` (not committed). Only final model files are kept.

---

## Install in Cursor / Agent Clients

- Copy or symlink this skill directory into your agent skill path.
- Preserve `scripts/`, `annotations/`, `environment/`, and `references/`.
- `cache/` is created at runtime and gitignored.
- `tmp/` (e.g. matplotlib config cache) is also gitignored and must not be committed.

---

## Directory layout

```text
genomic-regions-annotation/
├── SKILL.md
├── README.md
├── run_genomic_regions_annotation.py
├── scripts/
│   ├── voom2anno.sh
│   ├── annotateGenomicFeatures.py
│   ├── OrganizeAnnotationResults.py
│   ├── prepare_chromatin_model.py
│   ├── BEDinContext.py
│   ├── plot_chromatin_state_heatmap.py
│   ├── ensure_env.sh
│   ├── skill_env.py
│   └── ...
├── annotations/          # TSS + feature BEDs
├── references/
│   ├── methods-*.md
│   ├── chromatin-states-workflow.md
│   └── chromatin-states/ # metadata, state2name, chain
├── example_input/
│   └── chromatin/        # CTCF_K562_ENCFF396BZQ.bed, POLR2A_K562_ENCFF285MBX.bed, exampleInput.lst
├── cache/                # gitignored prepared models
├── tmp/                  # gitignored local runtime cache
├── tests/fixtures/
└── environment/epi_anno_env.yml
```

---

## Quick Start — Genes + genomic features

```bash
bash scripts/ensure_env.sh
python run_genomic_regions_annotation.py \
  --input-dir peaks \
  --genome hg38 \
  --run
```

Flow: BED/VOUT → `voom2anno.sh` → `annotateGenomicFeatures.py` → `OrganizeAnnotationResults.py`.

BED inputs are header-free by default. Genome is **required** (never defaulted).

---

## Quick Start — Chromatin states

```bash
bash scripts/ensure_env.sh
# 1) prepare (downloads once into cache/)
python scripts/prepare_chromatin_model.py --collection E123 --genome hg38
# 2) annotate (pass the printed/cached dense BED path)
python scripts/BEDinContext.py \
  -r example_input/chromatin/exampleInput.lst \
  -s cache/E123_hg38_dense.bed \
  -o BEDinContext \
  --state2name references/chromatin-states/state2name.tsv \
  --outputDir /path/to/agentResults/genomic-regions-annotation-<runId> \
  --runId <runId>
```

Default aggregation is **regions** (peak counts). Those primary tables and plots
live directly under the `-o` directory (for example `BEDinContext/`).

Optional `-a bp` or `-a both` also writes a secondary **base-pair** summary under:

```text
<out>/aggregationByBp/
├── statsCombined.num.tsv
├── statsCombined.frc.tsv
├── statsCombined.list.tsv
├── statsCombined.stackedBar.[png|pdf|html]
└── <peakPrefix>.[barPlot|piePlot].[png|pdf]
```

Treat `aggregationByBp/` as supplementary; do not present it as the primary
peak-distribution result. Per-peak best-state assignments (`*.bed2states.bed`)
always stay at the top level of `-o`.
Custom models: pass your dense BED and state2name; skip `prepare_chromatin_model.py`.

Segway + hg38: `--collection ENCFF089AXD --genome hg38` (liftOver inside prepare).

---

## Supported genomes (gene / feature)

| Genome | TSS annotation |
|--------|----------------|
| hg38 | gencode.v31.hg38.gtf.bed.sorted.tss |
| hg19 | gencode.v19.hg19.bed.tss |
| mm10 | gencode.vM22.mm10.gtf.bed.tss |
| mm9 | gencode.vM17.mm9.gtf.bed.tss |
| sacCer3 | sacCer3.shiftedBy125.flank375.bed.tss |

Precalculated chromatin models are human hg19/hg38 only. Custom chromatin models are used as-is.

---

## Testing

```bash
# Help smoke
python scripts/prepare_chromatin_model.py --help
python scripts/BEDinContext.py --help
python scripts/plot_chromatin_state_heatmap.py --help

# Offline fixture tests
GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP=1 python -m pytest tests -q

# Gene/feature dry-run
python run_genomic_regions_annotation.py --input-dir peaks --genome hg38 --dry-run
```

---

## Citation

See [references/citations.md](references/citations.md).

| Layer | Credit |
|-------|--------|
| Skill package | Hasan Al Reza; Wojciech Rosikiewicz — CAB-aiSkills `genomic-regions-annotation` ([AUTHORS.md](../AUTHORS.md)) |
| Gene / feature scripts | Per file headers (`voom2anno`, annotateGenomicFeatures, OrganizeAnnotationResults) |
| Chromatin | `BEDinContext.py` / prepare helpers; Roadmap ChromHMM; ENCODE Segway; BEDTools; UCSC liftOver |

---

## User-facing prompt examples

| User prompt | Interpretation |
|---|---|
| "Run genomic region annotation on `peaks/` for hg38 BED files." | Gene+feature wrapper; dry-run first unless asked to execute. |
| "Annotate my header-free BED files in `peaks/` using hg38." | Default BED handling; no `--bed-has-header`. |
| "Annotate gzipped BED files in `peaks/` for mm10." | Decompress `.bed.gz` then annotate. |
| "Annotate differential ATAC results in `differential_results/` with hg19." | VOUT auto-detect; `--genome hg19`. |
| "Only assign peaks to genomic features (skip gene lists)." | Feature path still goes through wrapper/anno pipeline; clarify if they want feature summaries only. |
| "Annotate these peaks to genes only for hg38." | Gene+feature wrapper is the supported path; reports include both unless customized. |
| "What ChromHMM / Segway models are available for K562?" | Lookup `availableModelsLookup.tsv` → E123 / ENCFF089AXD; do not annotate until confirmed. |
| "What is the closest chromatin model to CD35+ / follicular dendritic cells?" | Biological matching via lookup + metadata; suggest E032/E031 (primary B cells) with rationale; wait for confirmation. |
| "Annotate `peaks/*.bed` to Roadmap E123 on hg38." | `prepare_chromatin_model.py --collection E123 --genome hg38` then `BEDinContext.py`; copy models into run dir; **no** OrganizeAnnotationResults. |
| "Annotate CTCF and POLR2A K562 peaks to Segway for hg38." | Use example BEDs or user paths; prepare ENCFF089AXD (or confirmed Segway ID) with `--genome hg38`. |
| "Use my custom ChromHMM dense BED and state2name.tsv." | Skip prepare; pass paths to `BEDinContext.py --state2name`; document genome as as-is. |
| "List available Roadmap collections that look like primary B cells." | Filter Roadmap metadata / lookup; present E031/E032 names. |
| "Make a heatmap from the chromatin fraction matrix." | `plot_chromatin_state_heatmap.py` on `statsCombined.frc.tsv`. |
| "Run genomic region annotation on `peaks/`." | Ask for genome first. |
| "Build a new deterministic production workflow for repeated paid API calls." | Out of scope. |

---

## License

Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (`CC-BY-NC-SA-4.0`). Follow notices for bundled scripts and annotation resources.
