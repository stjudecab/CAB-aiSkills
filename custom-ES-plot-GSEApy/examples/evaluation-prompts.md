# Evaluation prompts: custom-ES-plot-GSEApy

## Contents

- Standard success cases — GSEApy pickle
- Standard success cases — Broad GSEA
- Edge cases
- Missing-input cases
- Out-of-scope cases

## Standard success — list-only regex preview (GSEApy pickle)

**User request:** Which SOS_peaks gene sets are in my RNA prerank pickle?

**Expected agent behavior:**

1. Run with `--inPKL <pickle>` and `--geneSetName 'SOS_peaks.*' --listOnly`.
2. Report the gene set names from the log (or from `gene_sets.list.txt` if `--outputDir` was used).
3. Do not generate plots unless the user then asks to plot them.

## Standard success — Broad GSEA, non-significant gene set

**User request:** Replot the ES plot for `REACTOME_HEME_SIGNALING` from my Broad GSEA 48h output folder, even though it is not significant.

**Expected agent behavior:**

1. Use `--inGseaDir` pointing at the Broad output directory (must contain `edb/`).
2. Run with exact `--geneSetName REACTOME_HEME_SIGNALING`.
3. Report PNG, PDF, TXT paths and key stats from the TXT file.
4. Explain that Broad stores all tested gene sets in `edb/results.edb`, not only `plot_top_x` figures. Do **not** suggest the user needs a GSEApy pickle for this workflow.

**Unacceptable:** Re-run prerank GSEA from scratch when a valid Broad output directory is provided.

## Standard success — Broad GSEA, regex subset

**User request:** Plot all CHIP.EP300 48h UP gene sets from my Broad GSEA run.

**Expected agent behavior:**

1. Resolve Broad output directory from user or cwd.
2. Use `--inGseaDir` and `--geneSetName 'CHIP.EP300.*48H.*UP'`.
3. Write to `agentResults/custom-ES-plot-GSEApy-<runId>/` unless user specifies otherwise.
4. Report how many gene sets matched and their output paths.

## Standard success — confirm exact gene set exists

**User request:** Is `SOS_peaks.1bp.c_2p5.g_100.l_300.closest` in my pickle?

**Expected agent behavior:**

1. Run `--inPKL <pickle>` with `--geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest --listOnly`.
2. If resolved, confirm presence; if not, report warning from log.

## Standard success — exact gene set (GSEApy pickle)

**User request:** Plot enrichment for `SOS_peaks.1bp.c_2p5.g_100.l_300.closest` from `GSEApy_prerank.pre_res.RNA.SynGR303_48h_vs_DMSO_48h.pkl`.

**Expected agent behavior:**

1. Confirm pickle path and that `gseapy` is available (offer Conda env if not).
2. Run `plotGseapyPrerankEnrichment.py` with `--inPKL` and exact `--geneSetName`.
3. Report PNG, PDF, TXT paths and key stats from the TXT file.
4. Point to `run_metadata.json` (`input_source: gseapyPkl`). Do **not** suggest Broad `results.edb` is involved.

**Unacceptable:** Re-run prerank GSEA from scratch when a valid pickle is provided.

## Standard success — regex subset (GSEApy pickle)

**User request:** Plot all SOS_peaks gene sets from my RNA prerank pickle.

**Expected agent behavior:**

1. Resolve pickle path from user or cwd.
2. Use `--inPKL` and `--geneSetName 'SOS_peaks.*'`.
3. Write to `agentResults/custom-ES-plot-GSEApy-<runId>/` unless user specifies otherwise.
4. Report three plots if the pickle contains three SOS_peaks terms.

## Edge case — comma-separated with one missing name

**User request:** Plot `NOT_A_REAL_SET` and `SOS_peaks.1bp.c_2p5.g_100.l_300.closest`.

**Expected agent behavior:**

1. Run with comma-separated `--geneSetName` (pickle or Broad mode as appropriate).
2. Log will warn about `NOT_A_REAL_SET`.
3. Still produce outputs for the valid gene set.
4. Inform user about the missing name.

## Missing input — input path unknown

**User request:** Make GSEApy enrichment plots for HALLMARK_APOPTOSIS.

**Expected agent behavior:**

1. Ask whether the user has a GSEApy `pre_res` pickle or a Broad GSEA output directory.
2. Ask for `--inPKL` or `--inGseaDir` if not inferable from context.
3. Do not guess input paths silently.

## Out of scope — Enrichr from gene list

**User request:** Run pathway enrichment on my DEG list with Enrichr.

**Expected agent behavior:**

1. Do **not** use this skill.
2. Direct to `pathway-enrichment-enrichr`.

## Out of scope — no pickle or Broad output, only RNK + GMT

**User request:** Run prerank GSEA and plot SOS_peaks from my RNK file.

**Expected agent behavior:**

1. Explain this skill plots from existing GSEApy pickles or Broad GSEA output directories.
2. User must run GSEApy prerank or Broad GSEA first, then invoke this skill.
