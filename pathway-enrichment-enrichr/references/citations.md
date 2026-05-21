# Citations and attribution — pathway-enrichment-enrichr

## Contents

- Layer 1: Skill package
- Layer 2: Bundled code
- Layer 3: Scientific method (Enrichr)
- Citation keys
- Copy-paste examples

## Layer 1: Skill package

| Field | Value |
|-------|--------|
| **Role** | Skill author / packager (orchestration, Excel/bar post-processing, manifest mode — **not** the Enrichr method or API design) |
| **Skill author(s)** | Named in [AUTHORS.md](../../AUTHORS.md) (Skills table) and `SKILL.md` → `metadata.author` |
| **Affiliation** | St Jude Children's Research Hospital (when citing packagers from this collection) |
| **Collection** | CAB-aiSkills skill `pathway-enrichment-enrichr` |
| **License** | [CC BY-NC-SA 4.0](../../LICENSE.txt) for packaging scripts in [AUTHORS.md](../../AUTHORS.md) |

**When to credit:** Referencing the agent skill, `run_pathway_enrichment.py`, or batch figure workflow.

**Repository policy:** [docs/attribution.md](../../docs/attribution.md)

## Layer 2: Bundled code

| Script | Copyright / author (see file header) |
|--------|--------------------------------------|
| `scripts/enrichr_api.py` | **Beisi Xu** && St Jude (2016–); contributions **Wojciech Rosikiewicz** && St Jude (2020–). **Do not reassign** authorship. |
| `scripts/run_pathway_enrichment.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/enrichment_postprocess.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/pathway_dotplot.py` | Wojciech Rosikiewicz && St Jude |

**When to credit Layer 2:** Software availability notes, code reuse, or describing the St Jude Enrichr API client used for queries.

## Layer 3: Scientific method (Enrichr)

**Cite this layer** for enrichment results in Methods. The public service is hosted at [Ma'ayan Lab Enrichr](https://maayanlab.cloud/Enrichr/).

| Publication | Use when |
|-------------|----------|
| **Kuleshov MV**, et al. Enrichr: a comprehensive gene set enrichment analysis web server 2016 update. *Nucleic Acids Res.* 2016;44(W1):W90–W97. [doi:10.1093/nar/gkw377](https://doi.org/10.1093/nar/gkw377) | **Primary** citation for API / web-server enrichment (recommended default) |
| **Chen EY**, et al. Enrichr: interactive and collaborative HTML5 gene list enrichment analysis tool. *BMC Bioinformatics* 2013;14:128. [doi:10.1186/1471-2105-14-128](https://doi.org/10.1186/1471-2105-14-128) | Original Enrichr tool; cite together with 2016 update if reviewers expect the first paper |

**Suggested Methods wording:**

> Pathway enrichment was performed with the **Enrichr** web service (Kuleshov et al., NAR 2016; Chen et al., BMC Bioinformatics 2013) via HTTPS API. Gene lists were submitted with library preset X (documented in `run_metadata.json`). Batch tables and figures were produced with the CAB-aiSkills `pathway-enrichment-enrichr` skill (skill author(s) per AUTHORS.md; repository URL).

**Service URL at run time:** `https://maayanlab.cloud` (see `enrichr_api.py`).

## Citation keys

| Key | Layer | Meaning |
|-----|-------|---------|
| `cab_aiskills_pathway_enrichment_enrichr` | 1 | This skill package |
| `enrichr_api_xu_stjude` | 2 | Bundled API client script |
| `enrichr_kuleshov_2016_nar` | 3 | Enrichr web server (primary method) |
| `enrichr_chen_2013_bmc` | 3 | Enrichr original tool (optional second cite) |

## Copy-paste examples

**Short:**

> Pathway enrichment: Enrichr (Kuleshov et al., 2016). Workflow: CAB-aiSkills `pathway-enrichment-enrichr`; API client: `enrichr_api.py` (Xu B).

**Methods (recommended):**

> Gene-set enrichment used Enrichr (Kuleshov MV et al., Nucleic Acids Res 2016, doi:10.1093/nar/gkw377; Chen EY et al., BMC Bioinformatics 2013, doi:10.1186/1471-2105-14-128) through the Ma'ayan Lab API. Queries were executed with the bundled Enrichr API client (`enrichr_api.py`; authors per file header, including Beisi Xu). Orchestration, Excel summaries, and batch plots used the CAB-aiSkills `pathway-enrichment-enrichr` skill (skill author(s) per AUTHORS.md; repository URL); skill authors are not authors of Enrichr.
