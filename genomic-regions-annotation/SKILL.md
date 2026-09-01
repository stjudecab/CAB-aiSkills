---
name: genomic-regions-annotation
description: >-
  Annotate genomic regions from epigenetic NGS (ATAC-seq, ChIP-seq, CUT&Tag,
  CUT&RUN, differential peaks) to nearby genes, genomic features, and/or
  chromatin states (ChromHMM Roadmap, Segway/ENCODE, or custom dense BED models).
  Use for peak-to-gene annotation, genomic feature assignment, ChromHMM/Segway
  state annotation, closest chromatin-state model lookup, header-free BED, VOUT,
  reporting, visualization, and GSEA-ready exports. Requires an explicitly stated
  genome build.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.10+ with bedtools, pybedtools, pandas, numpy, scipy,
  matplotlib, seaborn, scikit-learn, plotly, python-kaleido, xlsxwriter,
  adjusttext, natsort; ucsc-liftover for Segway hg19→hg38. Persistent Conda env via
  scripts/ensure_env.sh at ~/.cache/cursor-skills/genomic-regions-annotation/.
  Network needed to download Roadmap/ENCODE models. Chromatin models cached under
  skill-local cache/ (gitignored). Gene/feature runs write timestamped outputs;
  chromatin runs write under agentResults/genomic-regions-annotation-<runId>/.
metadata:
  author: Hasan Al Reza <hasan.al.reza.bd@gmail.com>; Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "1.3.1"
  status: stable
  last_reviewed: "2026-09-01"
allowed-tools: shell python
---

# Genomic Regions Annotation

## Purpose

Annotate epigenetic genomic regions in three complementary modes:

1. **Nearby genes** (`voom2anno.sh`)
2. **Genomic features** (`annotateGenomicFeatures.py`) including **gene-body overlap** (`inGeneBody`) with report aggregation (`OrganizeAnnotationResults.py`)
3. **Per-feature BED + GMT export** (`extractRegionsPerFeature.py`) — enabled by default in Workflow A after feature annotation
4. **Chromatin states** (`prepare_chromatin_model.py` + `BEDinContext.py`) — separate branch; do **not** run OrganizeAnnotationResults

Methods details: [methods-gene-annotation.md](references/methods-gene-annotation.md), [methods-genomic-features.md](references/methods-genomic-features.md), [methods-chromatin-states.md](references/methods-chromatin-states.md).

## When to Use

- Peak/region annotation for ATAC, ChIP, CUT&Tag/CUT&RUN, or differential region tables
- Gene or genomic-feature context reports / GSEA exports
- ChromHMM / Segway / Roadmap / ENCODE chromatin-state annotation
- “Which chromatin model is closest to my cell type?” lookup
- Custom ChromHMM dense BED annotation

## When Not to Use

- Pure RNA-seq DEG analysis without genomic intervals (use other skills)
- Building ChromHMM models from scratch (supply finished dense BED instead)
- Chromatin branch should not be mixed with OrganizeAnnotationResults

## Required Inputs

- Input BED / BED.GZ / VOUT directory or explicit BED paths
- **Genome build** (required; never default — ask if missing)
- For chromatin: Collection ID (`E123` / `ENCFF*`) **or** custom dense BED + state2name

## Persistent runtime environment (CRITICAL)

```bash
bash scripts/ensure_env.sh
```

- Cache: `~/.cache/cursor-skills/genomic-regions-annotation/conda-env/`
- Rebuild: `bash scripts/ensure_env.sh --force-rebuild`
- Python CLIs auto-bootstrap via `skill_env.bootstrap()` unless `GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP=1`

## Workflow A — Genes + genomic features

1. Ensure env.
2. Require `--genome`.
3. Dry-run then run wrapper:

```bash
python run_genomic_regions_annotation.py \
  --input-dir peaks \
  --genome hg38 \
  --run
```

4. Flow: `voom2anno.sh` → `annotateGenomicFeatures.py` → `extractRegionsPerFeature.py` → `OrganizeAnnotationResults.py`
5. See [workflow-and-outputs.md](references/workflow-and-outputs.md) and [input-formats-and-genomes.md](references/input-formats-and-genomes.md).

Gene-body annotation (`inGeneBody`) and per-feature BED/GMT extraction are **on by default**. Disable with `--gene-body-annotation off` or `--skip-feature-extraction` on the wrapper.

## Workflow B — Chromatin states (separate branch)

Full steps: [chromatin-states-workflow.md](references/chromatin-states-workflow.md).

1. Ensure env; ask genome (`hg19`/`hg38` for precalculated).
2. If user asks for closest model: read `references/chromatin-states/availableModelsLookup.tsv` (+ metadata); reason carefully; confirm before annotate.
3. Create `agentResults/genomic-regions-annotation-<YYYYMMDDTHHMMSSZ>/` with `agent_request.txt` and `agent_workflow.md`.
4. Prepare model (skip for custom dense BED):

```bash
python scripts/prepare_chromatin_model.py \
  --collection E123 --genome hg38 \
  --copyToRunDir <runDir>/models \
  --outputDir <runDir> --runId <runId> \
  --agentRequestFile <runDir>/agent_request.txt \
  --agentWorkflowFile <runDir>/agent_workflow.md
```

5. Annotate with resolved dense BED path (stdout from prepare / cache path):

```bash
python scripts/BEDinContext.py \
  -r <regions.lst> -s <cache_or_models_dense.bed> \
  -o BEDinContext --state2name references/chromatin-states/state2name.tsv \
  --outputDir <runDir> --runId <runId> \
  --agentRequestFile <runDir>/agent_request.txt \
  --agentWorkflowFile <runDir>/agent_workflow.md
```

Default aggregation is **regions** (one state per peak by largest bp overlap). Do **not** pass `-a both` or `-a bp` unless the user explicitly asks for base-pair summaries. When requested, bp tables/plots go under `<out>/aggregationByBp/` and are **not** the primary peak-distribution view.
Use `ENCODE_state2name.tsv` for Segway. Copy model files into each run’s `models/`.
6. **Do not** run `OrganizeAnnotationResults.py`.
7. Optional heatmap: `scripts/plot_chromatin_state_heatmap.py` on `statsCombined.frc.tsv`.

### Reproducibility and documentation (CRITICAL)

Every chromatin (and preferably gene/feature) derived-artifact run must leave:

1. `run_metadata.json`
2. `logs/<scriptName>.log` and `logs/commands.log`
3. `agent_request.txt` (verbatim) and `agent_workflow.md`
4. For chromatin: copies of the exact dense BED + state2name (+ model_meta) used

## Scripts

| Script | Role |
|--------|------|
| `run_genomic_regions_annotation.py` | Gene + feature pipeline wrapper |
| `scripts/voom2anno.sh` | Nearby-gene annotation |
| `scripts/annotateGenomicFeatures.py` | Exclusive genomic-feature assignment + gene-body overlap (`inGeneBody`) |
| `scripts/extractRegionsPerFeature.py` | Per-feature BED files and combined GMT export |
| `scripts/OrganizeAnnotationResults.py` | Reports / GSEA exports (gene/feature only) |
| `scripts/prepare_chromatin_model.py` | Download/preprocess/cache ChromHMM or Segway dense BED |
| `scripts/BEDinContext.py` | Overlap peaks with chromatin states |
| `scripts/plot_chromatin_state_heatmap.py` | Optional fraction heatmap |
| `scripts/ensure_env.sh` / `skill_env.py` / `run_with_skill_env.sh` | Persistent env |

## Resources

- [methods-gene-annotation.md](references/methods-gene-annotation.md)
- [methods-genomic-features.md](references/methods-genomic-features.md)
- [methods-chromatin-states.md](references/methods-chromatin-states.md)
- [chromatin-states-workflow.md](references/chromatin-states-workflow.md)
- `references/chromatin-states/` — metadata, state2name, liftOver chain
- `example_input/chromatin/` — bundled K562 CTCF (`ENCFF396BZQ`) and POLR2A (`ENCFF285MBX`) BED examples + `exampleInput.lst`
- [citations.md](references/citations.md)

## Quality Checks

- Genome stated explicitly
- Correct branch chosen (gene/feature vs chromatin)
- Chromatin: model in cache or prepared; copies in run `models/`; no OrganizeAnnotationResults
- Exit 0; expected tables/plots; `run_metadata.json` + logs present; scan logs for ERROR

## Failure and Escalation

- Missing genome → ask
- Unknown collection → show lookup table / metadata options
- Missing liftOver → rebuild env
- Ambiguous cell-type match → present top candidates with rationale; wait for confirmation

## Attribution

See [citations.md](references/citations.md).
