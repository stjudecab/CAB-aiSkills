# Evaluation prompts — reproducible-peaks

## Contents

- Standard success (CTCF examples)
- noControl narrowPeak
- SICER conversion
- Ambiguous directory
- Mixed conditions (must ask)
- Out of scope

## Standard success (CTCF examples)

**User:** I would like to generate the reproducible peaks for CTCF target, using the files from `CAB-aiSkills/reproducible-peaks/examples`.

**Available inputs:** `CTCF.ENCFF412MBV.bed`, `CTCF.ENCFF507TTK.bed`.

**Expected behavior:**

1. Confirm exactly two replicate files for one target (CTCF).
2. Detect 10-column narrowPeak-like BED; strategy `withControl` (no `noC_` prefix).
3. Default `-m 1` (two replicates, `n - 1`).
4. Run `reproducible_peaks.py` with outputs under `agentResults/reproducible-peaks-<runId>/`.
5. Report `*_optimal.bed` path and log/metadata locations.

**Unacceptable:** Including unrelated peak files from the same folder without confirmation.

## noControl narrowPeak

**User:** Reproducible peaks from `noC_H3K4me3_rep1.narrowPeak` and `noC_H3K4me3_rep2.narrowPeak`.

**Expected:** `--callingStrategy noControl` (or auto), rank method `signalvalue`, `-m 1`.

## SICER conversion

**User:** ChIP-R on two `*.sicer.filter.bed` replicates.

**Expected:** Convert each to broadPeak in `prepared_inputs/`; run ChIP-R; document conversion in log.

## Ambiguous directory

**User:** Run reproducible peaks on all files in `~/peaks/`.

**Expected:** Table of files grouped by target/condition; **ask** which group to use; no run until clarified.

## Mixed conditions (must ask)

**User:** Use `CTCF_DMSO_rep1`, `CTCF_DMSO_rep2`, `CTCF_EGF_rep1`, `CTCF_EGF_rep2`.

**Expected:** Detect two conditions; ask whether to run DMSO only, EGF only, or two separate ChIP-R jobs. Do not merge all four in one run unless user explicitly requests.

## Out of scope

**User:** Call MACS2 on my BAMs and then ChIP-R.

**Expected:** Explain peak calling is prerequisite; offer MACS2 guidance or ask for existing peak paths; do not claim reproducible peaks without input BED/narrowPeak files.
