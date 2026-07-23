# Interpretation guidelines

## Contents

- Evidence rules
- Observed vs interpreted language
- Thresholds and significance
- Genomic results
- QC and limitations
- Prohibited claims

## Evidence rules

Every numerical claim in the narrative must trace to:

- a source artifact named in the manifest, or
- a deterministic calculation recorded in `report-model.json` with provenance.

If a value is unavailable, state that it is unavailable. Do not estimate.

## Observed vs interpreted language

Use cautious language:

- **Observed:** “412 regions passed FDR < 0.05 and |log2FC| ≥ 1.0 in the supplied differential table.”
- **Interpretation:** “These regions may reflect treatment-associated chromatin remodeling; functional follow-up is needed.”

Avoid causal language from association-only results.

## Thresholds and significance

- Report the multiple-testing metric used (`FDR`, `padj`, `q-value`, etc.) when present in the table.
- Respect thresholds supplied in `analyses[].parameters`.
- If applying an additional display threshold for readability, label it clearly as a reporting filter.
- State tested-feature counts and significant-feature counts separately when available.
- For gene-set analyses, identify method family when known (`ORA`, preranked `GSEA`, `ssGSEA`, etc.).

## Genomic results

- Preserve comparison direction (`numerator` vs `denominator`).
- Preserve chromosome strings exactly (`chr1`, `1`, etc.).
- State genome build for region-level results when known.
- Distinguish gene-level tables from region-level tables.

## QC and limitations

Mention, when supported by artifacts or manifest warnings:

- low replicate count,
- batch effects,
- outliers,
- weak QC metrics,
- missing metadata,
- tentative artifact classification,
- absent adjusted p-value columns.

## Prohibited claims

Never:

- invent sample annotations, parameters, software versions, or significance,
- diagnose disease or recommend treatment,
- infer protected/clinical characteristics not explicitly provided,
- rerun major upstream analyses silently to fill narrative gaps.

If a conclusion requires a missing upstream analysis, name the missing step and recommend the appropriate sibling skill.

## Report clarity

- Prefer one clear visual plus a download link over duplicate sections that repeat the same information (for example Venn diagrams with companion overlap tables).
- Methods text should be concise, manuscript-ready prose from upstream skills used in the **target results directory** only.
- Software versions belong in the **Versions** section, aggregated from manifest fields and JSON metadata (`tool_versions`, `software`) found under the results directory.
