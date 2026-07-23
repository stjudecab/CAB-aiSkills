# Evaluation prompts — bioinformatics-reporting

## Should trigger

- Create a bioinformatics report from these ATAC-seq and RNA-seq results under `agentResults/`.
- Summarize the outputs of the differential expression and pathway enrichment skills into one HTML report.
- Generate an HTML and PDF report from this results directory.
- Combine these QC, differential analysis, and enrichment results into a scientific report.
- Update the existing analysis report with the new overlap analysis outputs.

## Should not trigger

- Run DESeq2 on this count matrix.
- Call peaks from these BAM files.
- Make a volcano plot grid from these tables. (use `volcano-grid-plot`)

## Edge cases

- No manifest present: expect discovery inventory with confidence labels before rendering.
- Missing genome build: expect warning, not invented build.
- Quarto missing: expect HTML bundle + `sphinx-source/`; PDF skipped when pdflatex/TeX packages are unavailable, not a false PDF claim.
