# Citations: custom-ES-plot-GSEApy

## Contents

- Layer 1 — Skill package
- Layer 2 — Bundled scripts
- Layer 3 — Scientific methods
- Copy-paste methods text — GSEApy pickle input
- Copy-paste methods text — Broad GSEA desktop input

## Layer 1 — Skill package

When referencing the **CAB-aiSkills workflow** (agent instructions, orchestration, run metadata):

- Credit the skill author in [AUTHORS.md](../../AUTHORS.md) and `metadata.author` in [SKILL.md](../SKILL.md).
- Name the skill: **`custom-ES-plot-GSEApy`**.

This credits packaging and orchestration, not GSEA or GSEApy authorship.

## Layer 2 — Bundled scripts

When referencing **`plotGseapyPrerankEnrichment.py`** or **`broadGseaInput.py`**:

- **Wojciech Rosikiewicz** (see script copyright headers).

## Layer 3 — Scientific methods

When describing **how enrichment plots were generated** in a paper, grant, or methods section, cite the underlying GSEA method and GSEApy. Then describe the **input source you actually used**:

| Input used | What to state in methods |
|------------|--------------------------|
| GSEApy `pre_res` pickle (`--inPKL`) | Prerank GSEA was run with GSEApy; ES plots for selected gene sets were generated from the saved `pre_res` pickle. |
| Broad GSEA desktop output (`--inGseaDir`) | Prerank GSEA was run with Broad Institute GSEA desktop software; ES plots for selected gene sets were regenerated from the saved output directory (`edb/results.edb`, ranked list, and gene sets). |

Both plotting workflows use GSEApy for figure rendering. Only the **upstream analysis source** differs.

### GSEA (preranked mode)

> Subramanian A, Tamayo P, Mootha VK, et al. Gene set enrichment analysis: a knowledge-based approach for interpreting genome-wide expression profiles. *Proc Natl Acad Sci U S A*. 2005;102(43):15545-15550. doi:[10.1073/pnas.0506580102](https://doi.org/10.1073/pnas.0506580102)

### GSEApy

> Fang Z, Liu X, Peltz G. GSEApy: a comprehensive package for performing gene set enrichment analysis in Python. *Bioinformatics*. 2022;btac757. doi:[10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)

## Copy-paste methods text — GSEApy pickle input

Use this wording when enrichment was computed with **GSEApy prerank** and plots were made from a saved **`pre_res` pickle** (`--inPKL`):

> Prerank gene set enrichment analysis was performed with GSEApy (Fang et al., 2022) using the GSEA method (Subramanian et al., 2005). Enrichment score plots for selected gene sets were generated from the saved GSEApy prerank `pre_res` pickle using GSEApy's built-in plotting on the stored ranked list, enrichment statistics (`res2d`), and gene-set definitions. This allowed visualization of gene sets regardless of whether they were included in the default `graph_num` / top-set figure export. Post-processing and batch plotting were performed with the CAB-aiSkills `custom-ES-plot-GSEApy` helper (skill author per repository AUTHORS.md).

## Copy-paste methods text — Broad GSEA desktop input

Use this wording when enrichment was computed with **Broad Institute GSEA desktop software** and plots were made from the **GSEA output directory** (`--inGseaDir`):

> Prerank gene set enrichment analysis was performed with Broad Institute GSEA desktop software following the GSEA method (Subramanian et al., 2005). Enrichment score plots for selected gene sets were regenerated from the saved GSEA output directory: per-gene-set statistics and hit indices were read from `edb/results.edb`, the ranked gene list from `edb/*.rnk`, and gene-set membership from `edb/gene_sets.gmt`. Running enrichment score curves were rendered with GSEApy (Fang et al., 2022). This allowed visualization of gene sets regardless of FDR significance or the default `plot_top_x` figure export. Post-processing and batch plotting were performed with the CAB-aiSkills `custom-ES-plot-GSEApy` helper (skill author per repository AUTHORS.md).

Do not cite the skill packager as the author of GSEA or GSEApy.
