# Citations and attribution - genomic-regions-annotation

## Contents

- Layer 1: Skill package
- Layer 2: Bundled code
- Layer 3: Scientific methods and resources
- Citation keys
- Copy-paste examples

## Layer 1: Skill package

| Field | Value |
|-------|-------|
| **Role** | Skill author / packager (workflow, wrapper, documentation, and agent instructions) |
| **Skill author(s)** | Named in [AUTHORS.md](../../AUTHORS.md) (Skills table) and `SKILL.md` -> `metadata.author` |
| **Collection** | CAB-aiSkills skill `genomic-regions-annotation` |
| **License** | [CC BY-NC-SA 4.0](../../LICENSE.txt) for skill packaging and files covered by repository licensing |

**When to credit:** Referencing the agent skill, `run_genomic_regions_annotation.py`, or the reproducible workflow packaging.

**Repository policy:** [docs/attribution.md](../../docs/attribution.md)

## Layer 2: Bundled code

| Script | Copyright / author (see file header) |
|--------|--------------------------------------|
| `run_genomic_regions_annotation.py` | Hasan Al Reza && St Jude |
| `scripts/voom2anno.sh` | Beisi Xu && St Jude |
| `scripts/tabit.sh`, `scripts/tabnNA.sh`, `scripts/region2bed.sh`, `scripts/bed2region.sh`, `scripts/winandgroup.sh` | Beisi Xu and/or St Jude where stated in script headers |
| `scripts/annotateGenomicFeatures.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/OrganizeAnnotationResults.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/wcn.sh`, `scripts/gene2nomicro.awk` | Helper scripts; preserve in-file notices where present |

**When to credit Layer 2:** Software availability notes, code reuse, or methods details naming the CAB/St Jude annotation scripts.

## Layer 3: Scientific methods and resources

This skill wraps an in-house CAB/St Jude genomic region annotation workflow rather than a single external method paper. For publications and reports:

- Report the **genome build** used: `hg38`, `hg19`, `mm10`, `mm9`, or `sacCer3`.
- Report the bundled **TSS annotation file** selected by `--genome`.
- Report the genomic feature annotation directory, especially if `--feature-anno-dir` overrides bundled resources.
- Cite external tools used by the workflow when relevant:

| Resource / tool | Use when | Citation / URL |
|-----------------|----------|----------------|
| BEDTools | Region intersection, window, closest, or grouping operations are part of the described method | Quinlan AR, Hall IM. BEDTools: a flexible suite of utilities for comparing genomic features. *Bioinformatics* 2010. doi:10.1093/bioinformatics/btq033 |
| ENCODE | Inputs or annotation resources come from ENCODE | https://www.encodeproject.org/ |
| GSEA / MSigDB | Downstream GSEA-ready GMT/RNK exports are used for enrichment analysis | https://www.gsea-msigdb.org/ |
| GENCODE | Gene annotation resources are described as GENCODE-derived | https://www.gencodegenes.org/ |

## Citation keys

Stable keys for run metadata and automated reports:

| Key | Layer | Meaning |
|-----|-------|---------|
| `cab_aiskills_genomic_regions_annotation` | 1 | This skill package |
| `cab_stjude_genomic_region_annotation_scripts` | 2 | Bundled CAB/St Jude annotation scripts |
| `bedtools_quinlan_2010_bioinformatics` | 3 | BEDTools method paper |
| `gencode_annotation_resource` | 3 | GENCODE-derived annotation resources |
| `encode_resource` | 3 | ENCODE data/resource attribution, when applicable |
| `gsea_msigdb_resource` | 3 | GSEA/MSigDB resource attribution, when downstream exports are used |

## Copy-paste examples

**Short:**

> Genomic regions were annotated with CAB/St Jude genomic region annotation scripts via CAB-aiSkills `genomic-regions-annotation`; genome build and annotation resources are recorded with the run.

**Methods (recommended):**

> Genomic regions were annotated using the CAB/St Jude genomic region annotation workflow (`voom2anno.sh`, `annotateGenomicFeatures.py`, and `OrganizeAnnotationResults.py`; authors per file headers) via the CAB-aiSkills `genomic-regions-annotation` skill. The analysis used genome build `<genome>` with TSS annotation `<annotation-file>` and bundled or specified genomic feature BED resources. Region operations used BEDTools where applicable (Quinlan and Hall, *Bioinformatics* 2010).
