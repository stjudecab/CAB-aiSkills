# Evaluation prompts: custom-ES-plot-GSEApy

## Contents

- Standard success cases
- Edge cases
- Missing-input cases
- Out-of-scope cases

## Standard success — list-only regex preview

**User request:** Which SOS_peaks gene sets are in my RNA prerank pickle?

**Expected agent behavior:**

1. Run with `--geneSetName 'SOS_peaks.*' --listOnly`.
2. Report the gene set names from the log (or from `gene_sets.list.txt` if `--outputDir` was used).
3. Do not generate plots unless the user then asks to plot them.

## Standard success — confirm exact gene set exists

**User request:** Is `SOS_peaks.1bp.c_2p5.g_100.l_300.closest` in my pickle?

**Expected agent behavior:**

1. Run `--geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest --listOnly`.
2. If resolved, confirm presence; if not, report warning from log.

## Standard success — exact gene set

**User request:** Plot enrichment for `SOS_peaks.1bp.c_2p5.g_100.l_300.closest` from `GSEApy_prerank.pre_res.RNA.SynGR303_48h_vs_DMSO_48h.pkl`.

**Expected agent behavior:**

1. Confirm pickle path and that `gseapy` is available (offer Conda env if not).
2. Run `plotGseapyPrerankEnrichment.py` with exact `--geneSetName`.
3. Report PNG, PDF, TXT paths and key stats from the TXT file.
4. Point to `run_metadata.json`.

**Unacceptable:** Re-run prerank GSEA from scratch when a valid pickle is provided.

## Standard success — regex subset

**User request:** Plot all SOS_peaks gene sets from my RNA prerank pickle.

**Expected agent behavior:**

1. Resolve pickle path from user or cwd.
2. Use `--geneSetName 'SOS_peaks.*'`.
3. Write to `agentResults/custom-ES-plot-GSEApy-<runId>/` unless user specifies otherwise.
4. Report three plots if the pickle contains three SOS_peaks terms.

## Edge case — comma-separated with one missing name

**User request:** Plot `NOT_A_REAL_SET` and `SOS_peaks.1bp.c_2p5.g_100.l_300.closest`.

**Expected agent behavior:**

1. Run with comma-separated `--geneSetName`.
2. Log will warn about `NOT_A_REAL_SET`.
3. Still produce outputs for the valid gene set.
4. Inform user about the missing name.

## Missing input — pickle path unknown

**User request:** Make GSEApy enrichment plots for HALLMARK_APOPTOSIS.

**Expected agent behavior:**

1. Ask for the `--inPKL` path if not inferable from context.
2. Do not guess pickle filenames silently.

## Out of scope — Enrichr from gene list

**User request:** Run pathway enrichment on my DEG list with Enrichr.

**Expected agent behavior:**

1. Do **not** use this skill.
2. Direct to `pathway-enrichment-enrichr`.

## Out of scope — no pickle, only RNK + GMT

**User request:** Run prerank GSEA and plot SOS_peaks from my RNK file.

**Expected agent behavior:**

1. Explain this skill plots from existing `pre_res` pickles.
2. User must run GSEApy prerank first (or use their existing pipeline), then invoke this skill.
