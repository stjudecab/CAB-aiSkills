# Methods: genomic feature annotation

## Contents

- Purpose
- Scientific approach
- Priority order (exclusive assignment)
- Feature BED resources
- Inputs and outputs
- Manuscript methods text
- Limitations

## Purpose

Assign each genomic region to exactly one genomic context class (promoter, exon, intron, intergenic, and related classes). This provides a structural sanity check (for example H3K4me3 peaks should enrich at promoters; H3K36me3 at gene bodies).

Implemented by `scripts/annotateGenomicFeatures.py` after gene annotation in the gene/feature branch. Gene-body overlap (`inGeneBody`) is added by default using reference BEDs from `annotations/`.

Per-feature BED and GMT exports are produced by `scripts/extractRegionsPerFeature.py` (enabled by default in the wrapper after feature annotation).

## Scientific approach

Regions are overlapped with predefined feature BED files **one by one in a fixed priority order** using BEDTools. After a region is assigned to a feature class, it is removed from the remaining pool. Each region is therefore assigned to **exactly one** feature class (exclusive cascading assignment).

## Priority order (exclusive assignment)

1. Promoter.Up (upstream promoter flank)
2. Promoter.Down (downstream promoter flank)
3. Exon
4. Intron
5. TES (transcription end site window)
6. Dis5 (5′ distal regions)
7. Dis3 (3′ distal regions)
8. Intergenic

Higher-priority classes take precedence. For example, a region overlapping both an exon and an intron is counted as Exon.

## Feature BED resources

Bundled under `annotations/<genome>/` with 2 kb windows for mammalian genomes (1 kb windows for sacCer3). Expected mammalian files include:

```text
2kb.promoter.up.bed
2kb.promoter.down.bed
2kb.exon.bed
2kb.intron.bed
2kb.tes.bed
2kb.dis5.bed
2kb.dis3.bed
2kb.intergenic.bed
```

Feature assignment GENCODE resource labels used historically for CAB peak annotation:

| Genome | Feature assignment version label |
|--------|----------------------------------|
| hg38 | hg38v31 |
| mm10 | mm10vM22 |
| hg19 | hg19v24lift37 / related lift resources |
| mm9 | mm9vM17lift |

## Inputs and outputs

Inputs are the `*.anno` tables from gene annotation (or compatible region tables). Outputs include feature-annotated tables with `FeatureAssignment` and `inGeneBody`, summary pie/bar plots consumed by `OrganizeAnnotationResults.py`, and optional per-feature BED/GMT exports under `<input>.byFeature/`.

### Gene-body annotation (`inGeneBody`)

After exclusive feature assignment, peaks are overlapped with bundled gene-body BED references (`annotations/AllGenes.*.feature_body.bed`) using pybedtools. Overlapping gene symbols are listed comma-separated in `inGeneBody`; regions with no overlap receive `.`.

Supported genomes: `hg38`, `hg19`, `mm10` (and `hg38_rDNA` when passed explicitly to annotateGenomicFeatures.py).

### Per-feature extraction

`extractRegionsPerFeature.py` groups annotated peaks by `FeatureAssignment` and writes:

- **BED mode** (non-differential inputs): one `<feature>.bed` per feature
- **Voom mode** (differential inputs): `<feature>.up.bed` and `<feature>.down.bed` after FDR/log2FC filtering
- One combined GMT with deduplicated gene sets parsed from `inGeneBody`

## Manuscript methods text

> Each region was assigned to a single genomic feature class by exclusive cascading BEDTools overlaps against predefined promoter, exon, intron, TES, distal, and intergenic BED sets, in that priority order. Once assigned, a region was excluded from subsequent feature classes. Feature definitions used the bundled `<genome>` annotation windows (default 2 kb flanks for mammalian genomes).

## Limitations

- Exclusive priority can hide secondary overlaps (a promoter-overlapping peak is never counted as exon even if it also overlaps an exon).
- Feature BEDs are genome-build specific; mixing peak coordinates and feature BEDs from different builds is invalid.
- Intergenic is a residual class after all higher-priority overlaps fail.
