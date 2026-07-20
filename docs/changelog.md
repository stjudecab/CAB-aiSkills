# Changelog

Newest entries first.

## 2026-07-20

- Added a compact, clickable CBviz output example to the **`colorblind-sim`** README, showing the original figure alongside severity-100 protanopia, deuteranopia, and tritanopia simulations.
- Stored the full-resolution example under `colorblind-sim/examples/` while constraining its rendered README width for readability.
- Ignored generated `*.tss.clean` annotation intermediates repository-wide so genomic-region annotation runs do not appear as untracked source changes.

## 2026-07-16

- Added **`colorblind-sim`** skill: wraps upstream **CBviz** to simulate figure appearance under color vision deficiency (protanopia, deuteranopia, tritanopia, monochrome).
- Persistent reusable **venv** via `scripts/ensure_env.sh` at `~/.cache/cursor-skills/colorblind-sim/venv/` (`requirements.txt` with Pillow, PyMuPDF, commit-pinned CBviz).
- Main CLI `run_colorblind_sim.py` (default `cbviz-fast` grid) plus `convert_to_png.py` for PDF→PNG; SVG/EPS via host `rsvg-convert` or `inkscape` when available.
- Full run audit trail (`run_metadata.json`, `logs/`, agent request/workflow artifacts) per AGENTS.md.
- Bundled references, evaluation prompts, demo PNG, pytest suite; updated README, AUTHORS, and attribution docs.

## 2026-07-14

- **`genomic-set-analysis`**: Synced pairwise significance with in-house `IntervenePeaksCombine`: **fold enrichment** (\(a/(|A||B|/N)\)), **expected overlap**, **enrichment direction**, raw-FE clustermap (not log2), and **`--pairwiseSignificanceUniverse`** (`auto`/`-1` or a positive integer). Updated evaluation prompts for manual universe size. Docs and tests updated.
- **`genomic-set-analysis`**: Added pairwise Fisher exact overlap significance (default on), ported from the in-house `IntervenePeaksCombine` upgrade. New module `scripts/pairwise_significance.py`; flags `--pairwiseSignificance` / `--pairwiseSignificanceFigSize`. BED mode uses `*.fromMerged.bed` + merged-peak universe; GMT mode uses Python sets + gene-union universe. Writes `pairwiseSignificance/` TSV matrices and one clustermap per statistic (Jaccard diagonal masked). Docs and tests updated.

## 2026-07-13 (cleanup)

- Removed accidental macOS AppleDouble `._*` sidecars and a committed matplotlib cache under `genomic-regions-annotation/tmp/`.
- Extended repo and skill `.gitignore` to ignore `._*`, skill-local `tmp/`, and reinforce `.DS_Store` / `.pytest_cache/` exclusions.
- Updated [AUTHORS.md](../AUTHORS.md) so **`genomic-regions-annotation`** lists both **Hasan Al Reza** and **Wojciech Rosikiewicz** as skill packagers / authors.

## 2026-07-13

- Extended **`genomic-regions-annotation`** with a chromatin-state annotation branch (ChromHMM Roadmap, Segway/ENCODE, custom dense BED).
- Added `prepare_chromatin_model.py` (download/preprocess/cache), adapted `BEDinContext.py` (path-resolved models + run metadata), and optional `plot_chromatin_state_heatmap.py`.
- Bundled chromatin metadata, state2name maps, hg19→hg38 chain, model lookup table, and CTCF/POLR2A example inputs; skill-local `cache/` is gitignored.
- Added methods docs for gene, genomic-feature, and chromatin-state annotation; chromatin agent workflow reference; persistent `ensure_env.sh` helpers; env pins for `natsort` and `ucsc-liftover`.
- Chromatin runs must **not** invoke `OrganizeAnnotationResults.py`.
- `BEDinContext.py` keeps region-level summaries as primary top-level outputs; optional bp aggregation (`-a bp` / `-a both`) writes under `<out>/aggregationByBp/`.
- Migration: pass resolved dense BED paths to `BEDinContext.py` (collection codes are prepared via `prepare_chromatin_model.py`, not absolute CombinedChromatinStatesMetadata paths).

## 2026-07-08

- Added **`genomic-set-analysis`** skill: portable, HPC-independent successor to the in-house `IntervenePeaksCombine.py` wrapper for order-independent overlap of genomic region sets or gene sets with **Intervene** (Venn / UpSet / pairwise), a membership matrix, and mutually exclusive per-sector files (`intervene_peaks_combine.py`).
- Delegated annotation to the **`genomic-regions-annotation`** skill and Enrichr pathway enrichment (for **both** intersection sectors and original inputs) to the **`pathway-enrichment-enrichr`** skill; both require an explicitly stated genome build.
- Added gated `expression_summary.py` (seaborn boxplots/heatmaps) requiring an expression matrix plus sample conditions/metadata.
- Removed LSF/`bsub` scheduling; disabled motif enrichment (HOMER) and deeptools modules as planned-but-not-yet-available.
- Added per-run reproducibility record (`run_metadata.json`, `logs/commands.log`) capturing the command, resolved inputs, parameters, and Intervene/BEDTools/pybedtools/pandas/numpy/Python versions.
- Bundled references (methods, inputs/outputs, chaining, citations), example BEDs/GMT/manifest/expression data, evaluation prompts, pytest suite, and skill badge.
- Added `environment.yml` pinning **Python 3.8–3.9** (Intervene 0.6.4 imports `collections.Iterable`, removed in 3.10+) and installing the Intervene/BEDTools binaries alongside the Python dependencies.
- Made the pairwise heatmap step **best-effort**: an upstream Intervene/pandas `DataFrame.ix` incompatibility in the `tribar` heatmap is now logged as a warning and skipped instead of aborting the run; the frac matrix, sectors, Venn/UpSet, and `color`/`pie` heatmaps are still produced.
- Verified end to end on the bundled examples in a dedicated conda env (genomic overlap of 3 BEDs, GMT gene-set overlap, and gated expression summary), plus the pytest suite.
- Added **short set label** policy for agents: derive ≤15-character unique analysis labels when basenames/GMT names are long; pass via `-n` or manifest TSV; write `setLabelsManifest.tsv` mapping `original_label` → `analysis_label`; GMT mode now accepts `-n` for shortened labels.
- Added default **pathway enrichment filter**: unless the user overrides, enrich only the **top 10 intersection sectors with ≥5 genes** and **original sets with ≥5 genes**; bundled `filter_gmt_for_pathway.py` writes filtered GMTs and filter-manifest TSVs before calling `pathway-enrichment-enrichr`.
- Updated [AUTHORS.md](../AUTHORS.md), [README.md](../README.md), and [docs/attribution.md](attribution.md) for the new skill.

## 2026-06-26

- Extended **`custom-ES-plot-GSEApy`** with Broad Institute GSEA desktop output support (`broadGseaInput.py`): replot ES figures from `*.GseaPreranked.*/edb/` artifacts for exact, regex, list-file, or `allGeneSets` selections — including non-significant gene sets omitted from default `plot_top_x` exports.
- Added combined multi-gene-set trace plotting for Broad GSEA replots with optional color maps.
- Updated skill docs, smoke tests, citations, and repository index for dual GSEApy-pickle / Broad-GSEA input modes.

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
