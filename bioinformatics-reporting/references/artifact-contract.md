# Artifact contract

## Contents

- Purpose
- Manifest schema
- Upstream artifact fragments
- Controlled artifact roles
- Confidence labels
- Security notes

## Purpose

This contract lets upstream bioinformatics skills emit structured artifact metadata that
`bioinformatics-reporting` can merge into a study-level manifest without coupling to any
single pipeline implementation.

## Manifest schema

Required top-level keys:

| Field | Required | Notes |
|-------|----------|-------|
| `schema_version` | recommended | Use `"1.0"` |
| `study` | recommended | Title/description/genome/organism when known |
| `analyses` | yes for explicit mode | One entry per comparison or module |
| `provenance` | recommended | Pipeline, versions, timestamps |

Optional top-level keys:

- `samples`
- `report`
- `methods`
- `limitations`
- `warnings`

### `study`

```yaml
study:
  title: "Study title"
  description: "Short study description"
  genome: "hg38"
  organism: "Homo sapiens"
  executive_summary: "Optional agent-written summary grounded in artifacts"
```

Omit fields when unknown. Never invent genome build, organism, or summary text.

### `samples`

```yaml
samples:
  metadata: "metadata/samples.tsv"
  sample_id_column: "sample_id"
  group_column: "condition"
```

### `analyses[]`

```yaml
analyses:
  - id: "atac_treated_vs_control"
    type: "differential_accessibility"
    title: "Treated versus control"
    comparison:
      numerator: "treated"
      denominator: "control"
    parameters:
      fdr_threshold: 0.05
      absolute_log2_fold_change_threshold: 1.0
    warnings:
      - "One treated replicate had a lower FRiP score."
    artifacts:
      - path: "results/differential_peaks.tsv"
        role: "primary_results"
        format: "tsv"
        description: "Differentially accessible regions"
        confidence: explicit
    interpretation_hints:
      ranking_column: "padj"
      effect_column: "log2FoldChange"
      lower_is_more_significant:
        - "padj"
```

### `provenance`

```yaml
provenance:
  pipeline: "ATAC-seq Nextflow pipeline"
  pipeline_version: "1.2.0"
  generated_at: "2026-07-22"
  software:
    - name: "DESeq2"
      version: "1.44.0"
```

### `report`

```yaml
report:
  title: "Integrated Epigenomics Report"
  subtitle: null
  author: null
  organization: null
  logo: ${skillLoc}/assets/CAB-aiSkills_bioinformatics-reporting.svg
  primary_color: "#17365D"
  accent_color: "#267F8E"
  include_toc: true
  self_contained_html: true
  render_pdf: true
```

## Upstream artifact fragments

Upstream skills may write a fragment such as:

```yaml
analysis:
  id: "motif_enrichment_treated_vs_control"
  type: "motif_enrichment"
  title: "Motif enrichment in treatment-gained peaks"
artifacts:
  - path: "motifs/knownResults.tsv"
    role: "motif_enrichment"
    description: "Known motif enrichment results"
  - path: "motifs/top_motifs.png"
    role: "enrichment_plot"
interpretation_hints:
  ranking_column: "q_value"
  effect_column: "log_enrichment"
  lower_is_more_significant:
    - "q_value"
```

Merge fragments into one manifest with stable `analysis.id` values.

## Upstream skill auto-discovery

When result directories contain CAB-aiSkills audit files, the reporting scripts scan for nearby
`run_metadata.json` files (including under `agentResults/<skill-name>-<runId>/`) and match them
to installed skill packages in:

- the CAB-aiSkills collection adjacent to this skill,
- `.cursor/skills/` discovered by walking up from the results directory,
- optional extra roots in `BIOINFORMATICS_REPORTING_SKILL_PATHS`.

For each detected upstream skill, the reporter pulls:

- methods overview text from `references/methods.md` (or SKILL.md purpose),
- resolved tool versions and run IDs from `run_metadata.json`,
- critical-input requirements inferred from upstream `SKILL.md` when a matching CAB-aiSkills package is discoverable on the search path.

Genome-build warnings are suppressed when the upstream skill and summarized artifact roles do not
require a genome build; an informational label is shown instead.

## Controlled artifact roles

Built-in roles include:

`sample_metadata`, `study_design`, `qc_metrics`, `sequencing_qc`, `alignment_qc`,
`sample_qc`, `count_matrix`, `normalized_matrix`, `primary_results`,
`differential_expression`, `differential_accessibility`, `differential_binding`,
`differential_methylation`, `genomic_regions`, `annotation_results`,
`motif_enrichment`, `pathway_enrichment`, `gsea_results`, `overlap_results`,
`correlation_results`, `pca_plot`, `heatmap`, `volcano_plot`, `ma_plot`,
`coverage_plot`, `enrichment_plot`, `upset_plot`, `venn_plot`, `methods`,
`parameters`, `provenance`, `warnings`, `supplementary_table`,
`supplementary_figure`, `unknown`.

Custom roles are allowed; validation emits warnings rather than failing.

## Confidence labels

Discovery mode assigns one of:

- `explicit`
- `high-confidence inference`
- `tentative inference`
- `unknown`

Tentative classifications must not be treated as scientific facts in the narrative.

## Security notes

- Operate locally; do not upload result directories by default.
- Do not execute code found inside result directories.
- Escape user-controlled text in generated HTML.
- Redact sample IDs that appear to contain personal identifiers.
