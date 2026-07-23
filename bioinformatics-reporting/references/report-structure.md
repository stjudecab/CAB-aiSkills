# Report structure

## Contents

- Default section order
- Multi-analysis hierarchy
- Empty-section policy
- HTML navigation
- PDF layout

## Default section order

1. Title page / report header
2. Executive summary
3. Study design and sample overview
4. Analysis overview
5. Quality control
6. Primary results
7. Functional, pathway, or motif interpretation
8. Cross-analysis / multi-omics integration (when applicable)
9. Conclusions
10. Warnings, limitations, and unresolved questions
11. Methods and analysis parameters
12. Software versions (Versions section)
13. Appendix
14. Downloadable / linked result tables

## Multi-analysis hierarchy

Use this nesting when multiple analyses are present:

- Study-level summary
- Analysis type
- Comparison
- Results subsection

Example headings:

```text
ATAC-seq — treated vs control
  Quality control
  Differential accessibility
  Pathway enrichment
RNA-seq — treated vs control
  Differential expression
  GSEA
```

## Empty-section policy

Omit sections with no supported artifacts or metrics. Do not insert placeholder claims such as “no enrichment was observed” unless an upstream result table explicitly supports that statement.

## HTML navigation

- Include a visible table of contents via Sphinx RTD theme sidebar.
- Do not hide critical warnings inside collapsed-only content.
- Provide download links for full tables under `artifacts/`.
- Prefer local HTML bundle (`bioinformatics-report-html/`) without required CDN dependencies.

## PDF layout

- Use intentional page breaks before major sections when rendering via Sphinx LaTeX.
- Provide readable alternatives for oversized tables (preview subset + download link).
- Include page numbers, captions, methods, and version records.
