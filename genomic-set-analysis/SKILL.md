---
name: genomic-set-analysis
description: >-
  Order-independent overlap and combinatorial analysis of genomic region sets (ChIP-seq,
  ATAC-seq, CUT&Tag, CUT&RUN, narrowPeak/broadPeak/BED) or gene sets (GMT) using Intervene
  (Venn / UpSet / pairwise). Builds a union of elements, a membership matrix, and mutually
  exclusive per-sector files, then optionally chains the genomic-regions-annotation skill
  for nearby-gene annotation and the pathway-enrichment-enrichr skill for Enrichr pathway
  enrichment of both the intersection sectors and the original inputs, plus gated expression
  summaries. Agents should assign short unique analysis labels (≤15 chars when possible) when
  basenames or GMT names are long, and record the mapping in setLabelsManifest.tsv. Use when the user asks to overlap peaks/regions, make a Venn or UpSet of BED
  files, combine intersecting peak sets, run "IntervenePeaksCombine", or analyze which genes
  and pathways are shared between factors/conditions. Requires an explicitly stated genome
  build for any annotation or pathway step.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.8-3.9 (Intervene 0.6.4 imports collections.Iterable, removed in 3.10+) with
  the Intervene CLI (bioconda::intervene), bedtools, pybedtools, pandas, numpy. On first run,
  `scripts/ensure_env.sh` creates a persistent Conda/micromamba prefix at
  `~/.cache/ai-skills-env/genomic-set-analysis/conda-env/` from `environment.yml` and reuses it
  on later runs (not recreated each time). Expression summaries additionally need scipy, seaborn,
  and matplotlib. Chained pathway enrichment needs xlsxwriter and requests. Annotation and
  pathway enrichment are delegated to sibling skills. Local filesystem for overlap; network only
  for Enrichr.
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "0.1.0"
  status: draft
  last_reviewed: "2026-07-08"
allowed-tools: shell python
---

# Genomic Set Analysis (Intervene wrapper)

## Purpose

Overlap two or more genomic region sets (or gene sets) in an **order-independent** way and
characterize what is shared. The bundled `intervene_peaks_combine.py` script wraps the
[Intervene](https://github.com/asntech/intervene) tool: it merges all inputs into one
union, marks per-input membership, splits the union into mutually exclusive combinatorial
sectors (A-only, A∩B, A∩B∩C, …), and draws Venn / UpSet / pairwise plots. The agent then
optionally chains two sibling skills for nearby-gene **annotation** and **pathway
enrichment**, and can produce gated **expression summaries**.

This skill is the portable, HPC-independent successor to the in-house `IntervenePeaksCombine.py`
wrapper. All scheduling (LSF/`bsub`) has been removed; every step runs locally or via a sibling skill.

## When to use

- The user wants to **overlap peaks/regions** across factors, conditions, or replicates and
  see a **Venn / UpSet / pairwise** plot (ChIP-seq, ATAC-seq, CUT&Tag, CUT&RUN, differential BED).
- The user asks for **order-independent** intersections or mentions **IntervenePeaksCombine** / Intervene.
- The user wants the **genes** or **pathways** shared by an intersection, or an **expression**
  readout of genes linked to each sector.
- The input is a single **GMT** (overlap gene sets, e.g. GSEA signatures) or a **TSV manifest** of BEDs.

## When not to use

- **Peak calling** from BAMs (run MACS2/SICER first) or **reproducible peaks across replicates**
  (use `reproducible-peaks`).
- **Differential binding/expression** statistics (use the appropriate DE skill).
- Simple annotation of one region set without overlap (use `genomic-regions-annotation` directly).

## Required inputs

- **Region files** (`-i`): ≥2 comma-separated `.bed`/`.narrowPeak`/`.broadPeak` paths; **or** a
  single `*.gmt` (gene-set mode); **or** a single `*.tsv` manifest (`path <tab> label`, no header).
- **Genome build** — **mandatory and never assumed** whenever annotation, pathway enrichment,
  or expression-from-BED is requested. See [Genome build safety](#genome-build-safety-critical).

## Optional inputs

- **`-n/--names`**: short **analysis labels** aligned to `-i` (default `auto` strips BED suffixes;
  for GMT, use to supply shortened labels while preserving original set names in
  `setLabelsManifest.tsv`; ignored for TSV-manifest input where labels come from the manifest).
  See [Short set labels](#short-set-labels-important).
- **`-o/--outputPrefix`**, **`--outputDir`** (point at `agentResults/` for skill runs).
- **`--toPlot`** (`venn,upset`, add `pairwise`, or `ignore`), **`--figSize`**, **`--mbColor`**, **`--sbColor`**.
- Expression: an **expression matrix** (`--exprMatrixFile`) **and** a condition mapping
  (`--exprSampleCondition` or `--metadataFile`). Both are required to plot expression.

## Genome build safety (CRITICAL)

Do **not** infer or default the genome build. Annotating regions to the wrong assembly
(e.g. hg38 vs hg19 vs mm10) silently produces wrong genes and false-positive pathways. If the
user requests annotation, pathway enrichment, or BED-based expression and has **not** stated the
genome, **ask for it before running those steps**. The overlap/plot step itself does not need a
genome and may proceed. Supported builds are those of the annotation skill: `hg38`, `hg19`,
`mm10`, `mm9`, `sacCer3`.

## Persistent runtime environment (CRITICAL)

Do **not** run `conda env create -f environment.yml` on every skill invocation. The bundled
helper creates a **reusable** Conda/micromamba prefix once and reuses it:

| Item | Location / command |
|------|------------------|
| Cache root | `~/.cache/ai-skills-env/genomic-set-analysis/` |
| Environment prefix | `~/.cache/ai-skills-env/genomic-set-analysis/conda-env/` |
| Setup helper | `scripts/ensure_env.sh` |
| Shell wrapper | `scripts/run_with_skill_env.sh <script> [args…]` |

**Agent procedure:**

1. Before the first overlap/filter/expression command, run `bash scripts/ensure_env.sh` once (or
   call the Python scripts directly—they bootstrap automatically via `scripts/skill_env.py`).
2. On later runs, reuse the same cache; **do not** recreate the environment unless
   `environment.yml` changed or the user asks for a clean rebuild.
3. For shell commands, prefer either direct Python script invocation (auto-bootstrap) or
   `bash scripts/run_with_skill_env.sh scripts/intervene_peaks_combine.py …`.

**Force a clean rebuild** when dependencies change or the env is corrupted:

```bash
bash scripts/ensure_env.sh --force-rebuild
# or delete manually:
rm -rf ~/.cache/ai-skills-env/genomic-set-analysis
```

**Why Conda/micromamba (not venv):** this skill depends on Bioconda binaries (`intervene`,
`bedtools`) in addition to Python packages. A plain venv cannot install those tools.

Set `GENOMIC_SET_ANALYSIS_SKIP_ENV_BOOTSTRAP=1` only for pytest or when intentionally using a
pre-activated dev environment.

## Reproducibility and documentation (CRITICAL)

Every skill run must leave a complete audit trail. For the overlap step:

1. Create `agentResults/genomic-set-analysis-<YYYYMMDDTHHMMSSZ>/` (or a project-specific grouping under `agentResults/`).
2. Write **`agent_request.txt`** (verbatim user prompt) and **`agent_workflow.md`** (input inventory, label shortening, manifest, exact CLI) before executing.
3. Run `intervene_peaks_combine.py` with `--runId`, `--agentRequestFile`, and `--agentWorkflowFile` (or inline `--agentRequest` / `--agentWorkflow`).
4. The script writes under `<outputDir>/<outputPrefix>.intervene/`:
   - **`run_metadata.json`** — UTC run ID, exact command, inputs, parameters, tool versions (Intervene, BEDTools, pybedtools, pandas, numpy, Python), outputs, and log paths.
   - **`logs/intervene_peaks_combine.log`** — full execution log.
   - **`logs/commands.log`** — append-only record of the Python CLI and every Intervene shell command.
   - **`agent_request.txt`** / **`agent_workflow.md`** — copied into the output directory when provided.
5. When you invoke sibling skills (annotation, pathway, expression), **record their commands and versions** (each writes its own metadata). Report the **genome build** used.
6. In your summary to the user, list the run directory, key deliverables, parameters, and method + versions from `run_metadata.json`.

Expression summaries (`expression_summary.py`) follow the same contract under their `--outputDir` with `logs/expression_summary.log` and reproducibility flags.

## Availability of add-on modules

| Module | Status in this skill | How it runs |
|--------|----------------------|-------------|
| Overlap + Venn/UpSet/pairwise + matrix + sectors | Available | `intervene_peaks_combine.py` (local) |
| Nearby-gene annotation | Available | Chain the **`genomic-regions-annotation`** skill |
| Pathway enrichment (intersections + originals) | Available | Chain **`pathway-enrichment-enrichr`** after filtering (default: top 10 intersections with ≥5 genes; originals with ≥5 genes). |
| Expression summaries | Available, **gated** | `expression_summary.py` (needs matrix + conditions) |
| Motif enrichment analysis (HOMER MEA) | **Not available — planned** | Do not offer; tell the user it is planned |
| deeptools enrichment heatmaps / tornado plots | **Not available — planned** | Do not offer; tell the user it is planned |

If the user asks for **motif enrichment** or **deeptools** heatmaps, explain that these modules
are not yet packaged and are planned for a future release; do not attempt a workaround.

## Short set labels (IMPORTANT)

Set labels become part of many output paths and filenames
(`<prefix>.<label>.fromMerged.bed`, combinatorial sector names in `sets/`, matrix column headers,
staged `originalInputs/<label>.bed`, etc.). Long or redundant names quickly produce unmanagable
paths. **Before running the overlap**, inspect how each set would be labeled and shorten when needed.

### When to shorten

**Do not shorten** when either is true:

- the user already supplied short names (`-n`, or a manifest/TSV with short labels), **or**
- every candidate label is already **≤15 characters** and **unique** among the sets.

Otherwise, derive the shortest **unique, still informative** analysis label per set.

### How to shorten (agent procedure)

1. **Collect candidate original labels** from BED basenames (`-n auto`), GMT set names, or manifest
   column 2.
2. **Strip shared prefixes/suffixes** across all names (e.g.
   `GSE202762_EGF_6h_MACS2_peaks` and `GSE202762_EGF_24h_MACS2_peaks` → `EGF_6h`, `EGF_24h`; or
   `6h`, `24h` when the shared stem makes the timepoint unambiguous).
3. **Keep the token that distinguishes** conditions, factors, treatments, genotypes, or replicates.
4. **Target ≤15 characters** per label (hard cap **20** if needed for uniqueness).
5. **Ensure uniqueness**; if two labels collide after shortening, extend minimally until distinct.
6. **Pass shortened labels** via:
   - **`-n Short1,Short2,...`** for comma-separated BED lists or a single GMT file, **or**
   - a **TSV manifest** (`path <tab> short_label`) when there are many files.
7. **Tell the user** which short labels you chose and why, and point them to `setLabelsManifest.tsv`.

The script always writes **`setLabelsManifest.tsv`** in the intervene output directory with columns
`input_index`, `input_identifier`, `original_label`, `analysis_label`, `labels_unchanged`. This
records the mapping for reproducibility even when labels were already short.

## Workflow

### Step 0 — Resolve short analysis labels (before overlap)

Inspect inputs and apply [Short set labels](#short-set-labels-important). Only skip shortening when
labels are already short and unique or the user supplied short names.

### Step 1 — Run the overlap (always)

1. Create the run directory under `agentResults/` (e.g. `agentResults/genomic-set-analysis-<runId>/`).
2. Write `agent_request.txt` and `agent_workflow.md` documenting inputs, label choices, and the CLI below.
3. Execute from the skill root (or with absolute paths). Scripts auto-bootstrap the persistent
   env at `~/.cache/ai-skills-env/genomic-set-analysis/conda-env/`; do not recreate Conda envs
   each run:

```bash
python scripts/intervene_peaks_combine.py \
  -i examples/peaksFactorA.bed,examples/peaksFactorB.bed,examples/peaksFactorC.bed \
  -n FactorA,FactorB,FactorC \
  -o factorOverlap \
  --outputDir agentResults/genomic-set-analysis-<runId> \
  --toPlot venn,upset \
  --runId <YYYYMMDDTHHMMSSZ> \
  --agentRequestFile agent_request.txt \
  --agentWorkflowFile agent_workflow.md
```

This creates `agentResults/factorOverlap.intervene/` with the membership matrix, merged BED,
`*.fromMerged.bed`, Intervene plots, `sets/`, `setsCounted/`, staged `originalInputs/`,
`setLabelsManifest.tsv`, and `run_metadata.json`. In GMT mode it also writes `intersections.gmt`
and `originalSets.gmt`.
See [references/inputs-and-outputs.md](references/inputs-and-outputs.md).

### Step 2 — Annotation (only if requested; needs genome build)

Confirm the genome build, then chain the **`genomic-regions-annotation`** skill twice so that
both the intersection sectors and the original inputs get nearby genes (and GSEA-ready GMT files):

- Intersection sectors: annotate `…/factorOverlap.intervene/setsCounted`
  → write under `…/factorOverlap.intervene/setsAnno`.
- Original inputs: annotate `…/factorOverlap.intervene/originalInputs`
  → write under `…/factorOverlap.intervene/originalInputsAnno`.

The annotation skill wraps `voom2anno.sh` internally; do **not** call `voom2anno.sh` yourself.
It appends a UTC suffix to `--out-dir`; capture the resulting directory names.
See [references/addons-and-chaining.md](references/addons-and-chaining.md).

### Step 3 — Pathway enrichment (only if requested; two output folders)

After annotation completes (or immediately in GMT mode), **filter** the gene-set GMT before
calling Enrichr unless the user explicitly asks to enrich **all** intersections/sets or gives
different thresholds.

#### Default pathway selection policy (unless user overrides)

Unless the user states otherwise:

| Target | Default filter |
|--------|----------------|
| **Intersection sectors** | Keep only sets with **≥5 genes**, ranked by gene count descending, then take the **top 10**. Skip sectors with &lt;5 genes. |
| **Original input sets** | Keep only sets with **≥5 genes** (no top-10 cap; there are usually few originals). |

If the user asks for **all intersections**, a different minimum gene count, or a different top-*N*,
follow their instruction instead and record the override in your summary.

Filter with the bundled helper (writes a filtered GMT plus an auditable manifest):

```bash
# Intersections — default top 10 with >=5 genes
python scripts/filter_gmt_for_pathway.py \
  --gmt agentResults/factorOverlap.intervene/setsAnno-<UTC>/finalReports/<combined>.gmt \
  --output agentResults/factorOverlap.intervene/intersections_forPathway.gmt \
  --manifest agentResults/factorOverlap.intervene/pathwayEnrichment_intersections_filterManifest.tsv \
  --minGenes 5 --topN 10 --overwrite

# Original files — >=5 genes only, no top-N cap
python scripts/filter_gmt_for_pathway.py \
  --gmt agentResults/factorOverlap.intervene/originalInputsAnno-<UTC>/finalReports/<combined>.gmt \
  --output agentResults/factorOverlap.intervene/originalFiles_forPathway.gmt \
  --manifest agentResults/factorOverlap.intervene/pathwayEnrichment_originalFiles_filterManifest.tsv \
  --minGenes 5 --topN 0 --overwrite
```

In **GMT input mode** (no annotation), filter `intersections.gmt` with `--topN 10` and
`originalSets.gmt` with `--topN 0` using the same `--minGenes 5` default.

Then chain the **`pathway-enrichment-enrichr`** skill on the **filtered** GMT files, depositing
results inside the intervene directory:

- **Intersections** → `…/factorOverlap.intervene/pathwayEnrichment_intersections/`
- **Original files** → `…/factorOverlap.intervene/pathwayEnrichment_originalFiles/`

```bash
python /path/to/pathway-enrichment-enrichr/scripts/run_pathway_enrichment.py \
  --mode gmt \
  --gmt agentResults/factorOverlap.intervene/intersections_forPathway.gmt \
  --outputDir agentResults/factorOverlap.intervene/pathwayEnrichment_intersections \
  --outPrefix intersections \
  --libraryPreset stjudehg
```

Confirm Enrichr network access and library preset with the user. Tell the user which intersection
sectors were enriched, which were skipped (and why), and point to the filter manifest TSV(s). See
[references/addons-and-chaining.md](references/addons-and-chaining.md).

### Step 4 — Expression summaries (only if matrix + conditions supplied)

Only run when the user provides an **expression matrix** and a **clear per-sample condition
definition** (a `--exprSampleCondition` list or a `--metadataFile`, or a description you can turn
into one). If either is missing, ask for it; do not guess conditions.

```bash
python scripts/expression_summary.py \
  --geneSetsGmt agentResults/factorOverlap.intervene/setsAnno-<UTC>/finalReports/<combined>.gmt \
  --exprMatrixFile /abs/expression_TPM.tsv \
  --exprGeneNameCol geneSymbol \
  --metadataFile examples/expressionMetadata.tsv \
  --exprYaxis TPM --exprPalette Set1 \
  --outputDir agentResults/factorOverlap.intervene/expressionSummary
```

The gene-set GMT comes from Step 2 (BED mode) or from `intersections.gmt` (GMT mode).

### Step 5 — Report

Summarize sector counts, output paths, the genome build used, and the method + versions for each
step (Intervene/BEDTools, annotation/GENCODE build, Enrichr libraries). Point the user to the
`run_metadata.json` files.

## Scripts

| Script | Role |
|--------|------|
| [scripts/ensure_env.sh](scripts/ensure_env.sh) | Create/reuse persistent Conda env under `~/.cache/ai-skills-env/genomic-set-analysis/` |
| [scripts/skill_env.py](scripts/skill_env.py) | Python bootstrap used by CLI entrypoints |
| [scripts/run_with_skill_env.sh](scripts/run_with_skill_env.sh) | Shell wrapper to run any command in the skill env |
| [scripts/intervene_peaks_combine.py](scripts/intervene_peaks_combine.py) | Core overlap: union, matrix, sectors, Intervene plots, staging, metadata. |
| [scripts/filter_gmt_for_pathway.py](scripts/filter_gmt_for_pathway.py) | Filter GMTs before pathway enrichment (default ≥5 genes; top 10 intersections). |
| [scripts/expression_summary.py](scripts/expression_summary.py) | Gated boxplots/heatmaps for genes per sector from a GMT + matrix + conditions. |

Both use `argparse`, `--help`, `camelCase` flags, fail-fast validation, and write machine-readable
metadata. Details: [references/methods.md](references/methods.md).

## Output format

Everything is written under `<outputDir>/<outputPrefix>.intervene/`; annotation and pathway
results are placed **inside** it as subdirectories (see Step 2–3). See
[references/inputs-and-outputs.md](references/inputs-and-outputs.md) for the full layout and schema.

## Quality checks

Before finishing verify:

- ≥2 region files (or a valid GMT/TSV); all paths exist; labels match inputs.
- Analysis labels are short (≤15 chars when possible), unique, and recorded in `setLabelsManifest.tsv`.
- The overlap step exited 0 and produced the matrix, `sets/`, `run_metadata.json`, and `logs/intervene_peaks_combine.log`.
- `agent_request.txt` and `agent_workflow.md` exist when the agent prepared them (or were passed via CLI flags).
- If annotation/pathway/expression ran, the **genome build was explicitly confirmed** and recorded.
- Pathway enrichment used the default filter (top 10 intersections with ≥5 genes; originals with
  ≥5 genes) unless the user overrode it; filter manifest TSV(s) exist.
- Motif/deeptools were **not** attempted (they are planned, not available).
- Tool versions and executed commands are captured for reproducibility.
- No NaN/Inf slipped through expression inputs (the expression script fails fast on non-finite values).

## Failure and escalation

- **Only one BED given** → ask for ≥2 files or a GMT/TSV; do not proceed.
- **Long auto-derived labels** → shorten per [Short set labels](#short-set-labels-important) before
  running; do not pass verbose basenames/GMT names through to filenames when shorter unique labels
  are obvious.
- **Genome build missing** for annotation/pathway/expression → ask; do not assume.
- **Intervene/BEDTools not installed** → run `bash scripts/ensure_env.sh` once (creates
  `~/.cache/ai-skills-env/genomic-set-analysis/conda-env/`). If that fails, install micromamba,
  mamba, or conda. Do not fake plots.
- **`ImportError: cannot import name 'Iterable' from 'collections'`** → the env is on Python ≥3.10;
  Intervene 0.6.4 needs Python 3.8–3.9. Recreate the env pinned to `python<3.10`.
- **Pairwise plot warns `DataFrame object has no attribute 'ix'`** → a known Intervene/pandas
  incompatibility in the `tribar` heatmap only. The overlap treats pairwise as best-effort: the
  matrix, sectors, Venn/UpSet, and the `*_pairwise_frac_matrix.txt` are still produced, and the
  `color`/`pie` heatmaps usually still render. Do not treat this as a run failure.
- **Motif / deeptools requested** → explain they are planned and unavailable.
- **Expression requested without a matrix or conditions** → ask for both; do not invent conditions.
- **Enrichr unreachable** → report the network requirement; do not fabricate enrichment tables.

## Attribution

Report credits in **three layers** (see [references/citations.md](references/citations.md) and
[docs/attribution.md](../docs/attribution.md)):

1. **Method:** **Intervene** (Khan & Mathelier, *BMC Bioinformatics* 2017) and **BEDTools**
   (Quinlan & Hall 2010); plus the method of any chained skill (GENCODE/voom2anno for annotation,
   Enrichr for pathways).
2. **Skill package:** CAB-aiSkills `genomic-set-analysis` — credit **skill author(s)** from
   [AUTHORS.md](../AUTHORS.md) and `metadata.author` (orchestration only).
3. **Bundled scripts:** per-file headers in `scripts/`.

`run_metadata.json` includes `citation_keys` and an `attribution` block. Do not cite the skill
author as the inventor of Intervene, Enrichr, or the annotation method.

## Resources

- [references/methods.md](references/methods.md) — algorithm, order-independence caveat, script details.
- [references/inputs-and-outputs.md](references/inputs-and-outputs.md) — input modes, output layout, schema.
- [references/addons-and-chaining.md](references/addons-and-chaining.md) — how to chain the annotation and pathway skills.
- [references/citations.md](references/citations.md) — layered attribution and copy-paste citations.
- [README.md](README.md) — install, examples, prompt table.
- [examples/evaluation-prompts.md](examples/evaluation-prompts.md) — expected agent behavior.
