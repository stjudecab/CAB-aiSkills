# Citations: custom-ES-plot-GSEApy

## Contents

- Layer 1 — Skill package
- Layer 2 — Bundled script
- Layer 3 — Scientific methods
- Copy-paste methods text

## Layer 1 — Skill package

When referencing the **CAB-aiSkills workflow** (agent instructions, orchestration, run metadata):

- Credit the skill author in [AUTHORS.md](../../AUTHORS.md) and `metadata.author` in [SKILL.md](../SKILL.md).
- Name the skill: **`custom-ES-plot-GSEApy`**.

This credits packaging and orchestration, not GSEA or GSEApy authorship.

## Layer 2 — Bundled script

When referencing **`plotGseapyPrerankEnrichment.py`**:

- **Wojciech Rosikiewicz** (see script copyright header).

## Layer 3 — Scientific methods

When describing **how enrichment plots were generated** in a paper, grant, or methods section:

### GSEA (preranked mode)

> Subramanian A, Tamayo P, Mootha VK, et al. Gene set enrichment analysis: a knowledge-based approach for interpreting genome-wide expression profiles. *Proc Natl Acad Sci U S A*. 2005;102(43):15545-15550. doi:[10.1073/pnas.0506580102](https://doi.org/10.1073/pnas.0506580102)

### GSEApy

> Fang Z, Liu X, Peltz G. GSEApy: a comprehensive package for performing gene set enrichment analysis in Python. *Bioinformatics*. 2022;btac757. doi:[10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)

## Copy-paste methods text

> Prerank GSEA enrichment plots were generated from saved GSEApy prerank results using GSEApy (Fang et al., 2022) following the GSEA method (Subramanian et al., 2005), with post-processing via the CAB-aiSkills `custom-ES-plot-GSEApy` helper (skill author per repository AUTHORS.md).

Do not cite the skill packager as the author of GSEA or GSEApy.
