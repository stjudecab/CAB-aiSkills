# Analysis modules

## Contents

- Module design
- Quality control
- Differential feature analysis
- Enrichment analysis
- Genomic-region results
- Overlap analysis
- Generic supplementary artifacts
- Future extensions

## Module design

Each module specifies:

- recognized artifact roles,
- useful columns,
- safe summary metrics,
- recommended report components,
- common warnings,
- interpretation boundaries.

Modules are selected from manifest `analyses[].type` and artifact roles.

## Quality control

**Roles:** `qc_metrics`, `sequencing_qc`, `alignment_qc`, `sample_qc`, `pca_plot`, `sample_metadata`

**Useful columns:** sample identifiers, read counts, alignment rates, duplication, FRiP/NSC, library size

**Safe metrics:** per-sample metric cards, missing metadata warnings, replicate count

**Warnings:** low QC, outlier samples, missing sample sheet

**Boundaries:** do not declare pass/fail without explicit thresholds from upstream QC artifacts

## Differential feature analysis

**Roles:** `primary_results`, `differential_expression`, `differential_accessibility`, `differential_binding`, `differential_methylation`, `volcano_plot`, `ma_plot`

**Useful columns:** identifier, log2FC, padj/FDR, baseMean/average signal

**Safe metrics:** tested count, significant count, up/down counts using supplied thresholds

**Warnings:** missing padj column, unclear comparison direction, empty result table

**Boundaries:** do not reinterpret raw p-values as FDR unless column names support it

## Enrichment analysis

**Roles:** `pathway_enrichment`, `gsea_results`, `motif_enrichment`, `enrichment_plot`

**Useful columns:** term/name, p-value, FDR/q-value, NES, gene count, motif score

**Safe metrics:** number of significant terms at supplied threshold, top-ranked preview rows with stated ranking column

**Warnings:** unknown enrichment method, missing gene universe metadata

**Boundaries:** do not claim pathway activation without direction/evidence from the table

## Genomic-region results

**Roles:** `genomic_regions`, `annotation_results`, `coverage_plot`

**Useful columns:** chromosome, start, end, annotation/gene link, score/log2FC

**Safe metrics:** region counts, preview of top rows by supplied ranking column

**Warnings:** missing genome build, coordinate prefix inconsistencies

**Boundaries:** do not convert regions to genes unless an annotation artifact supports the mapping

## Overlap analysis

**Roles:** `overlap_results`, `upset_plot`, `venn_plot`

**Useful columns:** set names, overlap sizes, sector membership tables

**Safe metrics:** intersection sizes, sector counts copied from result tables

**Warnings:** order-dependent overlap tools mislabeled as order-independent

**Boundaries:** overlap size is not automatically biological concordance

When a `venn_plot` or `upset_plot` is present, do **not** also render a separate results subsection for the companion `overlap_results` table. Link the table next to the figure instead. Apply the same rule for `enrichment_plot` figures paired with `pathway_enrichment` or `gsea_results` tables.

## Generic supplementary artifacts

**Roles:** `supplementary_table`, `supplementary_figure`, `methods`, `parameters`, `provenance`, `unknown`

Use appendix-style placement with source paths and minimal descriptive captions.

## Future extensions

Planned module families (not required in v0.1.0):

- RNA-seq / ATAC-seq / ChIP-seq assay-specific QC bundles
- methylation calling summaries
- single-cell metadata and marker tables
- Hi-C contact summaries
- multi-omics integration blocks

Add new modules by extending role/type mapping and reference documentation only; avoid hard-coding a single upstream pipeline.
