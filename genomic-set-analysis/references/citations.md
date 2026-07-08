# Citations and layered attribution

## Contents

- Layer 1 — skill package
- Layer 2 — bundled scripts
- Layer 3 — methods and external tools
- Chained skills
- Copy-paste methods text

Follow the repository three-layer policy: [../../docs/attribution.md](../../docs/attribution.md).

## Layer 1 — skill package

CAB-aiSkills `genomic-set-analysis` skill — credit the **skill author(s)** in
[../../AUTHORS.md](../../AUTHORS.md) and `metadata.author` in [SKILL.md](../SKILL.md). This credits
workflow orchestration and packaging only, **not** the underlying methods.

## Layer 2 — bundled scripts

- `scripts/intervene_peaks_combine.py` — Copyright Wojciech Rosikiewicz && St Jude (see file header).
- `scripts/expression_summary.py` — Copyright Wojciech Rosikiewicz && St Jude (see file header).

## Layer 3 — methods and external tools

| Tool | Citation | Key |
|------|----------|-----|
| **Intervene** | Khan A, Mathelier A. *Intervene: a tool for intersection and visualization of multiple gene or genomic region sets.* BMC Bioinformatics 2017;18:287. [doi:10.1186/s12859-017-1708-7](https://doi.org/10.1186/s12859-017-1708-7) | `intervene` |
| **BEDTools** | Quinlan AR, Hall IM. *BEDTools: a flexible suite of utilities for comparing genomic features.* Bioinformatics 2010;26(6):841–842. [doi:10.1093/bioinformatics/btq033](https://doi.org/10.1093/bioinformatics/btq033) | `bedtools` |
| **pybedtools** | Dale RK, Pedersen BS, Quinlan AR. *pybedtools: a flexible Python library for manipulating genomic datasets and annotations.* Bioinformatics 2011;27(24):3423–3424. [doi:10.1093/bioinformatics/btr539](https://doi.org/10.1093/bioinformatics/btr539) | `pybedtools` |

## Chained skills

When annotation or pathway enrichment is run, also cite those skills' Layer 3 methods:

- **genomic-regions-annotation** — CAB/St Jude annotation workflow (`voom2anno.sh` etc.); report the
  GENCODE annotation build for the genome used. See that skill's `references/citations.md`.
- **pathway-enrichment-enrichr** — **Enrichr** (Kuleshov et al., *NAR* 2016; Chen et al., *BMC
  Bioinformatics* 2013). See that skill's `references/citations.md`.

## Copy-paste methods text

> Genomic region sets were overlapped in an order-independent manner using Intervene (Khan &
> Mathelier, BMC Bioinformatics 2017) with BEDTools/pybedtools (Quinlan & Hall 2010; Dale et al.
> 2011), via the CAB-aiSkills `genomic-set-analysis` skill (skill author(s) per AUTHORS.md;
> repository URL). Combinatorial sectors were annotated to nearby genes with the
> `genomic-regions-annotation` skill using the <GENOME_BUILD> GENCODE annotation, and pathway
> over-representation of both the intersection sectors and the original inputs was computed with
> Enrichr (Kuleshov et al., 2016; Chen et al., 2013) via the `pathway-enrichment-enrichr` skill.
> Exact commands and tool versions are recorded in each step's `run_metadata.json`.

Do not cite the skill author(s) as inventors of Intervene, BEDTools, Enrichr, or the annotation method.
