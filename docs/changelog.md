# Changelog

Newest entries first.

## 2026-06-15

- Added **`genomic-regions-annotation`** skill: genomic region annotation and interpretation for ATAC-seq, ChIP-seq, CUT&Tag, CUT&RUN, and differential region inputs.
- Added workflow coverage for header-free BED, gzipped BED, and VOUT inputs with explicit genome-build selection.
- Bundled the genomic annotation wrapper, helper scripts, annotation resources, example input, visual assets, and Conda environment specification.
- Added skill references for citations, input formats/genomes, and workflow outputs.
- Updated [AUTHORS.md](../AUTHORS.md), [README.md](../README.md), and [docs/attribution.md](attribution.md) for the new skill.

## 2026-06-05

- Added **`custom-ES-plot-GSEApy`** skill: GSEApy prerank enrichment score (ES) plots and statistics from saved `pre_res` pickle files (`plotGseapyPrerankEnrichment.py`).
- Added **`--listOnly`** to list or preview resolved gene sets without plotting (exact names, regex, list files, `allGeneSets`).
- Bundled Conda (`environment.yml`) and pip (`requirements.txt`) dependency files for the new skill.
- Corrected GSEApy method citation to Fang et al., *Bioinformatics* 2022 (doi:10.1093/bioinformatics/btac757).
- Updated [AUTHORS.md](../AUTHORS.md) and [README.md](../README.md) skill index.

## 2026-05-21

- Added **`reproducible-peaks`** skill: reproducible ChIP-seq / ATAC-seq peak sets across replicates with **ChIP-R** (`reproducible_peaks.py`, `sicer_to_broadpeak.py`).
- Added SICER BED → broadPeak conversion path, audit logging, and run metadata.
- Added [docs/attribution.md](attribution.md) describing the three-layer attribution policy (skill packaging, bundled scripts, scientific methods).
- Extended **`pathway-enrichment-enrichr`** with `references/citations.md` and cross-links to attribution docs.
- Updated [AUTHORS.md](../AUTHORS.md) and [README.md](../README.md).

## 2026-05-20

- Added **`volcano-grid-plot`** skill: publication-ready grids of Volcano and/or MA plots from multiple differential tables (`volcano_ma_grid.py`), with GSE202762 example data and smoke tests.
- Added [AUTHORS.md](../AUTHORS.md) with per-skill authorship table; aligned script headers and skill docs with main CAB code-repo license conventions.
- Fine-tuned `volcano-grid-plot` README and evaluation prompts.
- Minor README affiliation wording update.

## 2026-05-15

- Initial public release of **CAB-aiSkills** repository ([`stjudecab/CAB-aiSkills`](https://github.com/stjudecab/CAB-aiSkills)).
- Added first three skills:
  - **`pathway-enrichment-enrichr`** — Enrichr over-representation, Excel/PDF/heatmap outputs.
  - **`tables-to-excel`** — merge CSV/TSV/TXT into a multi-sheet `.xlsx` with `NameDictionary` provenance.
  - **`kde-correlation-scatter`** — KDE density scatter plots comparing two differential experiments.
- Added repository [LICENSE.txt](../LICENSE.txt) (CC BY-NC-SA 4.0).
- Added shared branding assets under `assets/` and per-skill SVG logos; standardized README logo paths across skills.
