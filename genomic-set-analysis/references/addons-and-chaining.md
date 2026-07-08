# Add-ons and skill chaining

## Contents

- Overview
- Genome build requirement
- Annotation (genomic-regions-annotation)
- Pathway enrichment (pathway-enrichment-enrichr)
- Expression summaries
- Motif enrichment and deeptools (not available)
- What "mimics the original add-ons" means

## Overview

The original `IntervenePeaksCombine.py` scheduled annotation, motif enrichment, deeptools, and
expression as dependent HPC (LSF) jobs. This skill replaces those couplings:

| Original add-on | Now |
|-----------------|-----|
| `voom2anno.sh` annotation job | Chain the **`genomic-regions-annotation`** skill (it wraps `voom2anno.sh`). |
| Pathway enrichment (new) | Chain the **`pathway-enrichment-enrichr`** skill (intersections + originals). |
| Expression LSF worker | Run `expression_summary.py` locally (gated on matrix + conditions). |
| HOMER motif enrichment | **Not available — planned.** |
| deeptools heatmaps/tornado | **Not available — planned.** |

Only chain a sibling skill if it is actually available in the environment. If it is missing, tell
the user which skill/tool to install and stop that step; do not improvise a replacement.

## Genome build requirement

Annotation, pathway enrichment (BED mode), and BED-based expression all depend on the genome
assembly. **Never assume it.** If the user has not stated `hg38` / `hg19` / `mm10` / `mm9` /
`sacCer3`, ask before running these steps. Record the build used in your summary.

## Annotation (genomic-regions-annotation)

Run the annotation skill **twice** so both the intersection sectors and the original inputs get
nearby genes and GSEA-ready GMT files. Point `--out-dir` inside the intervene results directory:

```bash
# Intersection sectors
python /path/to/genomic-regions-annotation/run_genomic_regions_annotation.py \
  --input-dir  agentResults/factorOverlap.intervene/setsCounted \
  --genome     hg38 \
  --out-dir    agentResults/factorOverlap.intervene/setsAnno \
  --run

# Original inputs
python /path/to/genomic-regions-annotation/run_genomic_regions_annotation.py \
  --input-dir  agentResults/factorOverlap.intervene/originalInputs \
  --genome     hg38 \
  --out-dir    agentResults/factorOverlap.intervene/originalInputsAnno \
  --run
```

That skill appends a UTC suffix to `--out-dir` (e.g. `setsAnno-20260708T161200Z`). Capture the
resulting paths. The GSEA/GMT file it writes under `finalReports/` is the input to pathway
enrichment. Do **not** call `voom2anno.sh` directly.

## Pathway enrichment (pathway-enrichment-enrichr)

After annotation (or directly in GMT mode), **filter** gene sets before Enrichr unless the user
asks to enrich all sets or specifies different thresholds.

### Default selection policy (unless user overrides)

| Target | Rule |
|--------|------|
| Intersection sectors | **≥5 genes** and **top 10** by gene count (descending). |
| Original input sets | **≥5 genes** only (`--topN 0`; no cap). |

Use `scripts/filter_gmt_for_pathway.py` to write a filtered GMT and a manifest TSV documenting
included/excluded sets and the reason (`below_minGenes_5`, `outside_top_10`, `selected`).

```bash
# Intersections (default)
python scripts/filter_gmt_for_pathway.py \
  --gmt agentResults/factorOverlap.intervene/setsAnno-<UTC>/finalReports/<combined>.gmt \
  --output agentResults/factorOverlap.intervene/intersections_forPathway.gmt \
  --manifest agentResults/factorOverlap.intervene/pathwayEnrichment_intersections_filterManifest.tsv \
  --minGenes 5 --topN 10 --overwrite

# Original files (>=5 genes, no top-N cap)
python scripts/filter_gmt_for_pathway.py \
  --gmt agentResults/factorOverlap.intervene/originalInputsAnno-<UTC>/finalReports/<combined>.gmt \
  --output agentResults/factorOverlap.intervene/originalFiles_forPathway.gmt \
  --manifest agentResults/factorOverlap.intervene/pathwayEnrichment_originalFiles_filterManifest.tsv \
  --minGenes 5 --topN 0 --overwrite
```

Then run the pathway skill on each **filtered** GMT, depositing results inside the intervene
directory in **two** folders:

```bash
# Intersections
python /path/to/pathway-enrichment-enrichr/scripts/run_pathway_enrichment.py \
  --mode gmt \
  --gmt        agentResults/factorOverlap.intervene/intersections_forPathway.gmt \
  --outputDir  agentResults/factorOverlap.intervene/pathwayEnrichment_intersections \
  --outPrefix  intersections \
  --libraryPreset stjudehg

# Original files
python /path/to/pathway-enrichment-enrichr/scripts/run_pathway_enrichment.py \
  --mode gmt \
  --gmt        agentResults/factorOverlap.intervene/originalFiles_forPathway.gmt \
  --outputDir  agentResults/factorOverlap.intervene/pathwayEnrichment_originalFiles \
  --outPrefix  originalFiles \
  --libraryPreset stjudehg
```

The pathway skill creates a UTC run subfolder under each `--outputDir` and needs HTTPS access to
`maayanlab.cloud` (Enrichr). Confirm the library preset with the user.

**GMT input mode (no annotation):** filter Step-1 convenience files with the same defaults, then
feed the filtered GMTs to the pathway skill — `intersections.gmt` with `--topN 10` and
`originalSets.gmt` with `--topN 0`, both with `--minGenes 5`.

## Expression summaries

Gated: only run when the user supplies an expression matrix **and** a per-sample condition
mapping. The gene-set GMT is the annotation `finalReports` GMT (BED mode) or `intersections.gmt`
(GMT mode). See the `expression_summary.py` usage in [SKILL.md](../SKILL.md) Step 4.

## Motif enrichment and deeptools (not available)

These modules from the original wrapper are **not packaged** in this skill and are planned for a
future release. If asked, say so plainly and do not attempt a substitute (e.g. do not hand-run
HOMER or deeptools as a workaround).

## What "mimics the original add-ons" means

Like the original wrapper, results from each add-on are deposited **inside** the
`<outputPrefix>.intervene/` results directory (as `setsAnno*/`, `pathwayEnrichment_*/`,
`expressionSummary/`), and pathway enrichment runs **after** annotation, consuming its gene-level
output — the same dependency ordering the original tool used for expression after annotation.
