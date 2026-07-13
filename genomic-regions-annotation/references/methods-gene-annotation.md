# Methods: gene annotation

## Contents

- Purpose
- Scientific approach
- Assignment rules
- Genome / GENCODE versions
- Inputs and outputs
- Manuscript methods text
- Limitations

## Purpose

Annotate epigenetic peaks or genomic regions to nearby genes so that region sets can be interpreted biologically and exported for gene-set enrichment (for example GSEA-ready GMT/RNK files).

This is implemented by `scripts/voom2anno.sh` and orchestrated by `run_genomic_regions_annotation.py` for the gene + genomic-feature branch of this skill.

## Scientific approach

Regions are first assigned to genes when they overlap protein-coding gene promoters (default TSS ± 2 kb). One region may be assigned to multiple genes when it overlaps multiple promoters; these are putative promoter-related regions.

Regions not assigned at the promoter step are then assigned to genes whose TSS falls in the distal window (default TSS−50 kb to TSS−2 kb, or TSS+2 kb to TSS+50 kb). One region may again map to multiple genes (putative enhancer-related regions).

Finally, the closest gene by TSS distance is reported for every region (including distances greater than 50 kb). Closest-gene assignment is one gene per region.

Region operations use BEDTools (Quinlan and Hall, *Bioinformatics* 2010).

## Assignment rules

| Stage | Rule | Multiplicity |
|-------|------|--------------|
| Promoter | Overlap protein-coding gene promoter (default TSS ± 2 kb) | Many genes per region allowed |
| Distal / enhancer window | Distance to TSS within distal cutoff (default 2–50 kb from TSS, excluding promoter) | Many genes per region allowed |
| Closest gene | Minimum absolute distance to any TSS | Exactly one gene per region |

Default windows used by this skill:

- Promoter: TSS ± 2 kb (`--distance1` in the wrapper)
- Distal: 2–50 kb from TSS (`--distance2` in the wrapper)

## Genome / GENCODE versions

Current bundled gene-assignment resources (Gencode Promoter 2 kb / Enhancer 2–50 kb):

| Genome | Resource version used by the skill |
|--------|-------------------------------------|
| hg38 | GENCODE v31 (TSS bed: `gencode.v31.hg38.gtf.bed.sorted.tss`) |
| hg19 | GENCODE v19 (`gencode.v19.hg19.bed.tss`) |
| mm10 | GENCODE vM22 (`gencode.vM22.mm10.gtf.bed.tss`) |
| mm9 | GENCODE vM17 (`gencode.vM17.mm9.gtf.bed.tss`) |
| sacCer3 | Bundled yeast TSS resource |

**Always report the genome build and the TSS annotation file used.** Do not infer or default the genome.

## Inputs and outputs

Inputs are header-free BED (default), gzipped BED, or differential `.vout` tables. See [input-formats-and-genomes.md](input-formats-and-genomes.md).

Gene annotation produces intermediate `*.anno` tables that are later aggregated by `OrganizeAnnotationResults.py` when running the gene/feature pipeline.

## Manuscript methods text

> Genomic regions were annotated to nearby genes using the CAB/St Jude `voom2anno` workflow. Regions overlapping gene promoters (TSS ± 2 kb) were assigned as putative promoter-associated regions (multiple genes allowed). Remaining regions within 2–50 kb of a TSS were assigned as putative enhancer-associated regions (multiple genes allowed). The closest gene by TSS distance was also reported for each region. Annotation used genome build `<genome>` with TSS resource `<tss-file>`. Overlaps and distance calculations used BEDTools.

## Limitations

- Annotation is gene-centric and depends on the chosen gene catalog (GENCODE vs RefSeq differ in coverage and validation).
- Distal assignment is a distance heuristic, not direct experimental enhancer–promoter linkage.
- Multi-gene assignments at promoter/distal stages require careful interpretation when building unique gene lists.
