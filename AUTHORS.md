# Authors and attribution

## Toolbox

| Role | Name | Contact |
|------|------|---------|
| **Curator / maintainer** | Wojciech Rosikiewicz | rosikiewicz [at] gmail {dot} com |
| **Curator / maintainer** | Hasan Al Reza | hasan.al.reza.bd@gmail.com |
| **Affiliation** | St Jude Children's Research Hospital | |

**License:** [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](LICENSE.txt) (CC BY-NC-SA 4.0) for skill packaging, documentation, and scripts unless noted otherwise in-file.

**Attribution policy (three layers):** [docs/attribution.md](docs/attribution.md) — separates skill packaging, bundled script authors, and scientific method citations.

---

## Skills

| Skill | Skill author / packager | Core scripts | Script attribution notes |
|-------|-------------------------|--------------|---------------------------|
| [volcano-grid-plot](volcano-grid-plot/README.md) | Wojciech Rosikiewicz | `volcano_ma_grid.py` | Copyright Wojciech Rosikiewicz && St Jude (see script header) |
| [kde-correlation-scatter](kde-correlation-scatter/README.md) | Wojciech Rosikiewicz | `plot_kde_correlation.py` | Copyright Wojciech Rosikiewicz && St Jude (see script header) |
| [tables-to-excel](tables-to-excel/README.md) | Wojciech Rosikiewicz | `tables_to_excel.py`, `logging_support.py` | Copyright Wojciech Rosikiewicz && St Jude (see script headers) |
| [pathway-enrichment-enrichr](pathway-enrichment-enrichr/README.md) | Wojciech Rosikiewicz | `run_pathway_enrichment.py`, `enrichment_postprocess.py`, `pathway_dotplot.py` | Copyright Wojciech Rosikiewicz && St Jude (see script headers) |
| [pathway-enrichment-enrichr](pathway-enrichment-enrichr/README.md) | — (upstream) | `enrichr_api.py` | Copyright Beisi Xu && St Jude (2016–); contributions Wojciech Rosikiewicz (2020–); **do not reassign** — see in-file header |
| [reproducible-peaks](reproducible-peaks/README.md) | Wojciech Rosikiewicz | `reproducible_peaks.py`, `sicer_to_broadpeak.py`, `logging_support.py` | Copyright Wojciech Rosikiewicz && St Jude (see script headers) |
| [custom-ES-plot-GSEApy](custom-ES-plot-GSEApy/README.md) | Wojciech Rosikiewicz | `plotGseapyPrerankEnrichment.py` | Copyright Wojciech Rosikiewicz && St Jude (see script header) |
| [genomic-regions-annotation](genomic-regions-annotation/README.md) | Hasan Al Reza | `run_genomic_regions_annotation.py`, `voom2anno.sh`, `annotateGenomicFeatures.py`, `OrganizeAnnotationResults.py` | Copyright Hasan Al Reza && St Jude (2025-) ; contributions Beisi Xu (2016–) && Wojciech Rosikiewicz (2020–) (see script headers) |

---

## How to cite or credit

Use **all applicable layers**; do not collapse them into a single author line.

### Layer 1 — CAB-aiSkills skill package

When referencing the **toolbox or a skill workflow** (agent instructions, wrappers, reproducibility logs):

- Credit the **skill author(s)** named in the Skills table below for that skill (and in the skill’s `SKILL.md` → `metadata.author`), plus a link to this repository.
- This credits **packaging and orchestration**, not external scientific methods. As new contributors ship skills, add or update rows in the Skills table—general docs refer to “skill author(s)” rather than a single fixed name.

### Layer 2 — Bundled scripts

When referencing **specific code files**:

| File | Credit |
|------|--------|
| `pathway-enrichment-enrichr/scripts/enrichr_api.py` | **Beisi Xu** (primary author per file header); note contributions from Wojciech Rosikiewicz where stated in-header |
| Other skill `scripts/*.py` | Author(s) named in that file’s copyright header (often matches the skill’s packager in the table above) |

### Layer 3 — Scientific methods and external tools

When describing **how results were computed** in a paper, grant, or methods section, cite the **primary tool papers**, not the skill packager:

| Skill | Method citation (canonical detail) |
|-------|----------------------------------|
| [reproducible-peaks](reproducible-peaks/references/citations.md) | **ChIP-R** — Newell et al., bioRxiv 2020 ([doi:10.1101/2020.11.24.396960](https://doi.org/10.1101/2020.11.24.396960)) |
| [pathway-enrichment-enrichr](pathway-enrichment-enrichr/references/citations.md) | **Enrichr** — Kuleshov et al., *NAR* 2016; Chen et al., *BMC Bioinformatics* 2013 |
| [custom-ES-plot-GSEApy](custom-ES-plot-GSEApy/references/citations.md) | **GSEA** — Subramanian et al., *PNAS* 2005; **GSEApy** — Fang et al., *Bioinformatics* 2022 ([doi:10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)) |
| [genomic-regions-annotation](genomic-regions-annotation/references/citations.md) | **CAB/St Jude genomic region annotation workflow** — credit bundled scripts per file headers and report the genome build / annotation resources used |

Per-skill copy-paste examples: each skill’s `references/citations.md` and README **Citation** section.

### Agents and automated reports

Report Layer 3 (method) and Layer 1 (skill) separately. See [docs/attribution.md](docs/attribution.md).
