---
name: genomic-regions-annotation
description: >-
  Runs annotation and interpretation of genomic regions from epigenetic NGS datasets including ATAC-seq, ChIP-seq, CUT&Tag, CUT&RUN, and differential region analyses. Use for genomic region annotation, header-free BED files, gzipped BED files, VOUT files, nearby-gene annotation, genomic feature assignment, reporting, visualization, and GSEA-ready exports. Requires an explicitly stated genome build for annotation.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.10+ with bedtools, pybedtools, pandas, numpy, scipy, matplotlib, seaborn, scikit-learn, plotly, python-kaleido, xlsxwriter, and adjusttext. Needs outbound HTTPS network access to maayanlab.cloud (Enrichr). Writes outputs under a UTC timestamp-suffixed directory rooted at --out-dir.
metadata:
  author: Hasan Al Reza <hasan.al.reza.bd@gmail.com>
  version: "1.1.0"
  status: stable
  last_reviewed: "2026-06-05"
---

# SKILL: Genomic Regions Annotation Pipeline

## Overview

This skill provides a unified workflow for annotating genomic regions from epigenetic NGS datasets including:

- ATAC-seq
- ChIP-seq
- CUT&Tag
- CUT&RUN
- Differential accessibility analyses
- Differential peak analyses
- Differential methylation region analyses

The workflow is executed through a single Python wrapper:

```text
run_genomic_regions_annotation.py
```

The wrapper orchestrates:

1. Nearby-gene annotation
2. Genomic feature annotation
3. Result aggregation
4. Visualization
5. GSEA-ready output generation
6. Conda environment management
7. Helper-script validation

---

# Project Structure

```text
project/
├── run_genomic_regions_annotation.py
│
├── scripts/
│   ├── voom2anno.sh
│   ├── annotateGenomicFeatures.py
│   ├── OrganizeAnnotationResults.py
│   ├── wcn.sh
│   ├── tabit.sh
│   ├── tabnNA.sh
│   ├── region2bed.sh
│   ├── bed2region.sh
│   ├── winandgroup.sh
│   └── gene2nomicro.awk
│
├── annotations/
│   ├── gencode.v31.hg38.gtf.bed.sorted.tss
│   ├── gencode.v19.hg19.bed.tss
│   ├── gencode.vM22.mm10.gtf.bed.tss
│   ├── gencode.vM17.mm9.gtf.bed.tss
│   ├── sacCer3.shiftedBy125.flank375.bed.tss
│   ├── hg38/
│   ├── hg19/
│   ├── mm10/
│   ├── mm9/
│   └── sacCer3/
│
├── references/
│   ├── citations.md
│   ├── input-formats-and-genomes.md
│   └── workflow-and-outputs.md
│
└── environment/
    └── epi_anno_env.yml
```

---

# Main Pipeline

## File

```text
run_genomic_regions_annotation.py
```

## Responsibilities

The wrapper:

- detects input type automatically
- selects the correct voom2anno mode
- runs gene annotation
- runs genomic feature assignment
- generates plots and reports
- validates helper scripts
- injects helper scripts into PATH
- manages conda environments
- supports dry-run execution

---

# Supported Inputs

| Input Type | voom2anno Mode |
|------------|----------------|
| `*.bed` | `bed6i0` by default for header-free BED files |
| `*.bed.gz` | Decompressed to `.bed`, then processed as `bed6i0` by default |
| `*.vout` | `pktesth1` |

No manual mode selection is required.

BED inputs are treated as header-free by default so the first genomic region is annotated instead of being interpreted as a header. Use `--bed-has-header` only when BED inputs contain one header line.

The genome build is required for every annotation or dry-run. Do not infer or default to `hg38`; if the user does not state the genome, ask for it before running the wrapper or annotation script.

For detailed input, staging, and genome-resource rules, read [references/input-formats-and-genomes.md](references/input-formats-and-genomes.md).

---

# Workflow

```text
Input File
      ↓
voom2anno.sh
      ↓
*.anno
      ↓
annotateGenomicFeatures.py
      ↓
Feature-annotated .anno
      ↓
OrganizeAnnotationResults.py
      ↓
Final reports + GSEA outputs
```

---

# Genome Support

| Genome | Annotation File |
|----------|----------|
| hg38 | gencode.v31.hg38.gtf.bed.sorted.tss |
| hg19 | gencode.v19.hg19.bed.tss |
| mm10 | gencode.vM22.mm10.gtf.bed.tss |
| mm9 | gencode.vM17.mm9.gtf.bed.tss |
| sacCer3 | sacCer3.shiftedBy125.flank375.bed.tss |

---

# Genomic Feature Annotation

Expected structure:

```text
annotations/
└── hg38/
    ├── 2kb.promoter.up.bed
    ├── 2kb.promoter.down.bed
    ├── 2kb.exon.bed
    ├── 2kb.intron.bed
    ├── 2kb.tes.bed
    ├── 2kb.dis5.bed
    ├── 2kb.dis3.bed
    └── 2kb.intergenic.bed
```

Equivalent structures are expected for all supported genomes.

---

# Helper Script Validation

The wrapper validates:

```text
wcn.sh
tabit.sh
tabnNA.sh
region2bed.sh
bed2region.sh
winandgroup.sh
gene2nomicro.awk
```

and automatically prepends:

```text
scripts/
```

to PATH during execution.

---

# Conda Environment Support

The workflow ships with a default environment YAML:

```text
environment/epi_anno_env.yml
```

Default environment name:

```text
epi_anno_env
```

Create and use the bundled environment:

```bash
python run_genomic_regions_annotation.py \
    --input-dir peaks \
    --genome hg38 \
    --create-conda-env \
    --run
```

Use a custom environment YAML:

```bash
python run_genomic_regions_annotation.py \
    --input-dir peaks \
    --genome hg38 \
    --conda-yaml /path/to/custom_env.yml \
    --conda-env custom_epi_env \
    --create-conda-env \
    --run
```

Use an existing conda environment prefix:

```bash
python run_genomic_regions_annotation.py \
    --input-dir peaks \
    --genome hg38 \
    --conda-prefix /path/to/env \
    --run
```

---

# Common Usage

## Dry Run

```bash
python run_genomic_regions_annotation.py \
    --input-dir peaks \
    --genome hg38 \
    --dry-run
```

## BED Files

```bash
python run_genomic_regions_annotation.py \
    --input-dir peaks \
    --genome hg38 \
    --run
```

## Differential Peak Files

```bash
python run_genomic_regions_annotation.py \
    --input-dir differential_results \
    --genome hg19 \
    --run
```

## Custom Output Directory

```bash
python run_genomic_regions_annotation.py \
    --input-dir peaks \
    --genome hg38 \
    --out-dir annotation_results \
    --run
```

This writes to a directory such as `annotation_results-20260605T153012Z`.

---

# Command Line Arguments

| Argument | Description |
|-----------|-----------|
| `--input-dir` | Directory containing `.bed`, `.bed.gz`, and/or `.vout` files |
| `--out-dir` | Output directory root. The wrapper appends a UTC timestamp suffix (`YYYYMMDDTHHMMSSZ`) to the final directory name for each run |
| `--bed-glob` | Comma-separated BED file patterns. Default: `*.bed,*.bed.gz` |
| `--vout-glob` | VOUT file pattern |
| `--copy-inputs` | Copy instead of symlink inputs |
| `--bed-has-header` | Treat BED and BED.GZ inputs as having one header line. Omit for header-free BED files |
| `--base-dir` | Base project directory |
| `--scripts-dir` | Directory containing scripts and helper utilities |
| `--annotations-dir` | Directory containing TSS and feature annotations |
| `--feature-anno-dir` | Override genomic feature annotation directory |
| `--genome` | Required genome build. Supported values: `hg38`, `hg19`, `mm10`, `mm9`, `sacCer3` |
| `--distance1` | Proximal annotation window |
| `--distance2` | Distal annotation window |
| `--python-bin` | Python interpreter override |
| `--conda-yaml` | Conda YAML file. Defaults to `environment/epi_anno_env.yml` |
| `--conda-env` | Conda environment name |
| `--conda-prefix` | Explicit conda environment prefix |
| `--create-conda-env` | Create environment if missing |
| `--use-current-python` | Use current Python environment |
| `--skip-existing-anno` | Skip existing annotation files |
| `--skip-organize` | Skip final report generation |
| `--dry-run` | Validate commands only |
| `--run` | Execute workflow |

---

# Outputs

```text
<out-dir>-YYYYMMDDTHHMMSSZ/
├── finalReports/
├── allOtherFiles/
├── bedFileAnnotations/
└── GenomicFeaturesAnnotation/
```

Including:

- annotated region tables
- Excel annotation workbooks
- BED exports
- GSEA GMT files
- GSEA RNK files
- MA plots
- Volcano plots
- PCA plots
- Heatmaps
- Genomic feature summaries
- Combined annotation reports

For detailed runtime behavior, output layout, and post-run checks, read [references/workflow-and-outputs.md](references/workflow-and-outputs.md).

---

# Best Practices

- Use absolute paths for reproducibility.
- Keep all helper utilities under `scripts/`.
- Keep all annotation resources under `annotations/`.
- Keep the default environment file at `environment/epi_anno_env.yml`.
- Use `--create-conda-env` to create the bundled environment.
- Use `--conda-prefix` for pre-existing shared environments.
- Use `--dry-run` before large analyses.
- Keep genome versions consistent and require users to state the genome explicitly.
- Version-control the wrapper and annotation resources.

---

# Troubleshooting

## Missing Helper Script

Example:

```text
wcn.sh: command not found
```

Verify:

```bash
which wcn.sh
```

and ensure the script exists under:

```text
scripts/
```

## Missing Genomic Feature BEDs

Example:

```text
KeyError: '2kb.promoter.up.bed'
```

Verify:

```text
annotations/hg38/2kb.promoter.up.bed
```

exists and that `--feature-anno-dir` points to the parent annotation directory.

## Default Environment YAML Not Found

Verify:

```bash
ls environment/epi_anno_env.yml
```

or provide:

```bash
--conda-yaml /path/to/env.yml
```

## Conda Environment Not Found

Use:

```bash
--conda-prefix /path/to/env
```

or:

```bash
--create-conda-env --conda-yaml env.yml
```

---

# Attribution

For citation layers, bundled script authorship, and copy-paste methods text, read [references/citations.md](references/citations.md). Report the skill package separately from bundled script authors and external resources.

# References

- ENCODE: https://www.encodeproject.org/
- BEDTools: https://bedtools.readthedocs.io/
- Bioconductor: https://bioconductor.org/
- GSEA: https://www.gsea-msigdb.org/
