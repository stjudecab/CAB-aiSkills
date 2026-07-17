# Attribution and citation policy (CAB-aiSkills)

## Contents

- Three layers
- Where each layer is documented
- Resolving skill authors (Layer 1)
- What to cite in publications
- Agent reporting rules
- Adding attribution to new skills

## Three layers

CAB-aiSkills separates **packaging** from **bundled code** from **scientific methods**. Each layer answers a different question and must not be merged into a single credit line.

| Layer | Question it answers | Typical credit |
|-------|---------------------|----------------|
| **1. Skill package** | Who built the agent workflow, docs, wrappers, and tests? | **Skill author(s)** for that skill (see [AUTHORS.md](../AUTHORS.md) and the skill’s `SKILL.md` → `metadata.author`) |
| **2. Bundled code** | Who wrote a specific script with its own copyright header? | Named author(s) in that file (e.g. `enrichr_api.py`) |
| **3. Method / external tool** | What algorithm or service produced the scientific result? | Primary publication and tool URL (see per-skill `references/citations.md`) |

**Copyright** (license, file headers, `AUTHORS.md`) is not the same as a **methods citation** (DOI, journal). Both are required where applicable.

## Where each layer is documented

| Layer | Repository location |
|-------|---------------------|
| Toolbox maintainer & script copyrights | [AUTHORS.md](../AUTHORS.md) |
| External methods & tools | `<skill>/references/citations.md` |
| Copy-paste text for users | `<skill>/README.md` → **Citation** section |
| Agent behavior | `<skill>/SKILL.md` → **Attribution** section |
| Reproducibility runs | `run_metadata.json` → `attribution` / `citation_keys` |

## Resolving skill authors (Layer 1)

Layer 1 depends on **what you are citing**:

### A. A specific skill (usual case)

Credit the **skill author(s)** for that skill—not a single toolbox-wide name.

1. Open [AUTHORS.md](../AUTHORS.md) → **Skills** table → column **Skill author / packager**.
2. Confirm `SKILL.md` frontmatter `metadata.author` (should match or list co-packagers). If they disagree, **AUTHORS.md wins** for publications.
3. Write: **“CAB-aiSkills `<skill-name>` skill”** + named skill author(s) + repository URL.

### B. The CAB-aiSkills collection as a whole

Use this only when you refer to the **toolbox/repository** in general and **not** to one skill’s workflow (e.g. “analyses used several CAB-aiSkills agent skills” without naming each).

Credit the **toolbox curator / maintainer** from the top of [AUTHORS.md](../AUTHORS.md) (currently **Wojciech Rosikiewicz**, Center for Applied Bioinformatics, St Jude Children's Research Hospital) and the repository URL.

As more contributors join, update the Skills table for per-skill credits; the collection maintainer line in AUTHORS.md may still list the curator even when individual skills have other packagers.

## What to cite in publications

Use **multiple sentences or bullets**, not one vague credit.

**Example (reproducible peaks):**

> Reproducible peaks were identified with **ChIP-R** (Newell et al., bioRxiv 2020; see `reproducible-peaks/references/citations.md`). Analysis was run via the **CAB-aiSkills** `reproducible-peaks` skill (skill author(s) listed in [AUTHORS.md](../AUTHORS.md); repository URL).

**Example (pathway enrichment):**

> Pathway enrichment used the **Enrichr** web service (Chen et al., 2013; Kuleshov et al., 2016) through the bundled **Enrichr API client** (`enrichr_api.py`; authors per file header) and the **CAB-aiSkills** `pathway-enrichment-enrichr` skill (skill author(s) in [AUTHORS.md](../AUTHORS.md); repository URL).

**Example (genomic regions annotation):**

> Genomic regions were annotated with CAB/St Jude genomic region annotation scripts (`voom2anno.sh`, `annotateGenomicFeatures.py`, `OrganizeAnnotationResults.py`; script authors per file headers and [AUTHORS.md](../AUTHORS.md)) using the stated genome build and annotation resources. Analysis was run via the **CAB-aiSkills** `genomic-regions-annotation` skill (skill author(s) in [AUTHORS.md](../AUTHORS.md); repository URL).

**Example (genomic set analysis / overlap):**

> Genomic region sets were overlapped in an order-independent manner with **Intervene** (Khan & Mathelier, *BMC Bioinformatics* 2017) and **BEDTools**/pybedtools (Quinlan & Hall, 2010; see `genomic-set-analysis/references/citations.md`). Analysis was run via the **CAB-aiSkills** `genomic-set-analysis` skill (skill author(s) in [AUTHORS.md](../AUTHORS.md); repository URL); chained annotation and Enrichr pathway enrichment used the `genomic-regions-annotation` and `pathway-enrichment-enrichr` skills with the stated genome build.

**Example (colorblind simulation):**

> Figure appearance under color vision deficiency was simulated with **CBviz** (Flynn; https://github.com/wflynny/cbviz) using **colorspacious** transforms (see `colorblind-sim/references/citations.md`). Analysis was run via the **CAB-aiSkills** `colorblind-sim` skill (skill author(s) in [AUTHORS.md](../AUTHORS.md); repository URL).

**Do not** cite skill author(s) as the inventor of Intervene, ChIP-R, Enrichr, CBviz, or other third-party methods.
## Agent reporting rules

When a skill run completes, the agent should report:

1. **Method** — name + pointer to `references/citations.md` (e.g. ChIP-R, Enrichr).
2. **Skill package** — skill name + **skill author(s)** from AUTHORS.md / `metadata.author` (workflow only).
3. **Bundled script** — only when relevant (e.g. results produced via `enrichr_api.py`).

Do not imply the skill author(s) invented the underlying method.

## Adding attribution to new skills

For each new skill:

1. Add a row to [AUTHORS.md](../AUTHORS.md) (packager + any upstream script rows).
2. Create `references/citations.md` with Layer 3 entries only (papers, tools, URLs).
3. Add **Citation** to `README.md` and **Attribution** to `SKILL.md`.
4. Include `citation_keys` in `run_metadata.json` when the skill writes run metadata.

Skills that only wrap in-house analysis (no external method paper) still document Layer 1 in `citations.md` with a short “no external method citation required” note.
