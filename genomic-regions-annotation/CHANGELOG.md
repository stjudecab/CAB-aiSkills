# Changelog

All notable changes to the `genomic-regions-annotation` skill are documented here.

## [1.3.1] - 2026-09-01

### Changed

- Gene-body reference BEDs moved from `sjcab_std_anno_report/` to `annotations/` (alongside TSS and feature BED resources).
- `annotateGenomicFeatures.py` now resolves gene-body references from `../annotations/`.

## [1.3.0] - 2026-09-01

### Added

- Gene-body overlap annotation (`inGeneBody` column) in `scripts/annotateGenomicFeatures.py`, enabled by default via `--geneBodyAnnotation on|off`.
- Bundled gene-body reference BEDs under `annotations/` for `hg38`, `hg19`, and `mm10`.
- New `scripts/extractRegionsPerFeature.py` to split annotated peaks into feature-specific BED files and one combined GMT gene-set file.
- Wrapper integration (`run_genomic_regions_annotation.py`) runs feature extraction by default after genomic feature annotation in Workflow A (voom2anno branch).
- Wrapper flags: `--gene-body-annotation {on,off}`, `--skip-feature-extraction`, `--fdr-threshold`, `--log2fc-threshold`.
- Unit tests for feature extraction in `tests/test_extract_regions_per_feature.py`.
- `openpyxl` dependency for `.xlsx` inputs in `environment/epi_anno_env.yml`.

### Changed

- Workflow A command flow is now: `voom2anno.sh` → `annotateGenomicFeatures.py` → `extractRegionsPerFeature.py` → `OrganizeAnnotationResults.py`.
- Updated skill documentation for gene-body annotation, per-feature BED/GMT exports, and new wrapper options.

## [1.2.0] - 2026-07-13

- Stable release with gene/feature and chromatin-state branches, persistent conda env, and reproducibility metadata.
