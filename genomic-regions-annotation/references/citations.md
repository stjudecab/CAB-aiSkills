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

**When to credit:** Referencing the agent skill, `run_genomic_regions_annotation.py`, chromatin helpers, or the reproducible workflow packaging.

**Repository policy:** [docs/attribution.md](../../docs/attribution.md)

## Layer 2: Bundled code

| Script | Copyright / author (see file header) |
|--------|--------------------------------------|
| `run_genomic_regions_annotation.py` | Hasan Al Reza && St Jude |
| `scripts/voom2anno.sh` | Beisi Xu && St Jude |
| `scripts/tabit.sh`, `scripts/tabnNA.sh`, `scripts/region2bed.sh`, `scripts/bed2region.sh`, `scripts/winandgroup.sh` | Beisi Xu and/or St Jude where stated in script headers |
| `scripts/annotateGenomicFeatures.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/OrganizeAnnotationResults.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/BEDinContext.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/prepare_chromatin_model.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/plot_chromatin_state_heatmap.py` | Wojciech Rosikiewicz && St Jude |
| `scripts/wcn.sh`, `scripts/gene2nomicro.awk` | Helper scripts; preserve in-file notices where present |

**When to credit Layer 2:** Software availability notes, code reuse, or methods details naming the CAB/St Jude annotation scripts.

## Layer 3: Scientific methods and resources

This skill wraps in-house CAB/St Jude genomic region annotation workflows rather than a single external method paper. For publications and reports:

- Report the **genome build** used.
- Report the bundled **TSS annotation file** or feature BED directory for gene/feature runs.
- Report the **chromatin collection ID**, biosample name, preprocess steps, and aggregation mode for chromatin runs.
- Cite external tools/resources when relevant:

| Resource / tool | Use when | Citation / URL |
|-----------------|----------|----------------|
| BEDTools | Region intersection / overlap | Quinlan AR, Hall IM. BEDTools: a flexible suite of utilities for comparing genomic features. *Bioinformatics* 2010. doi:10.1093/bioinformatics/btq033 |
| ChromHMM | Chromatin-state models / Roadmap segmentations | Ernst J, Kellis M. ChromHMM: automating chromatin-state discovery and characterization. *Nat Methods* 2012. |
| Roadmap Epigenomics | Precalculated ChromHMM 15-state models | http://www.roadmapepigenomics.org/ ; dense BEDs from egg2.wustl.edu chromhmmSegmentations |
| Segway / ENCODE chromatin states | Segway annotations | Libbrecht et al. PMID:31462275; https://www.encodeproject.org/ |
| UCSC liftOver | Segway hg19→hg38 conversion | https://genome.ucsc.edu/cgi-bin/hgLiftOver |
| GENCODE | Gene annotation resources | https://www.gencodegenes.org/ |
| GSEA / MSigDB | Downstream GMT/RNK enrichment | https://www.gsea-msigdb.org/ |

## Citation keys

| Key | Layer | Meaning |
|-----|-------|---------|
| `cab_aiskills_genomic_regions_annotation` | 1 | This skill package |
| `cab_stjude_genomic_region_annotation_scripts` | 2 | Bundled CAB/St Jude annotation scripts |
| `cab_stjude_bed_in_context` | 2 | BEDinContext chromatin annotation script |
| `bedtools_quinlan_2010_bioinformatics` | 3 | BEDTools |
| `chromhmm_ernst_kellis_2012` | 3 | ChromHMM |
| `roadmap_epigenomics_resource` | 3 | Roadmap models |
| `segway_encode_libbrecht_2019` | 3 | Segway ENCODE annotations |
| `ucsc_liftover_resource` | 3 | liftOver |
| `gencode_annotation_resource` | 3 | GENCODE |
| `encode_resource` | 3 | ENCODE |
| `gsea_msigdb_resource` | 3 | GSEA/MSigDB |

## Copy-paste examples

**Short:**

> Genomic regions were annotated with CAB/St Jude scripts via CAB-aiSkills `genomic-regions-annotation`; genome build and annotation resources are recorded with the run.

**Methods (gene + features):**

> Genomic regions were annotated using the CAB/St Jude genomic region annotation workflow (`voom2anno.sh`, `annotateGenomicFeatures.py`, and `OrganizeAnnotationResults.py`) via CAB-aiSkills `genomic-regions-annotation`. The analysis used genome build `<genome>` with TSS annotation `<annotation-file>`. Region operations used BEDTools (Quinlan and Hall, *Bioinformatics* 2010).

**Methods (chromatin states):**

> Peaks were annotated to chromatin states by overlapping each peak with a ChromHMM (Roadmap) or Segway (ENCODE) segmentation for `<biosample>` (collection `<Collection>`, genome `<hg19|hg38>`). Peaks overlapping multiple states were assigned to the state with the largest overlapping base-pair length using `BEDinContext.py` (CAB/St Jude) via CAB-aiSkills `genomic-regions-annotation`. Roadmap dense BEDs were preprocessed to numeric state IDs; Segway hg19 annotations were converted, optionally lifted to hg38 with UCSC liftOver, and adjacent same-state intervals were merged before annotation.
