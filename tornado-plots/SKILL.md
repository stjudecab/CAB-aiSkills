---
name: tornado-plots
description: >-
  Create deepTools tornado plots and heatmaps from BED region files and BigWig signal tracks. Use when asked to stage input files with symlinks, run computeMatrix reference-point, run plotHeatmap, submit the workflow through local shell or LSF bsub, or generate ChIP-seq/CUT&Tag/CUT&RUN style tornado plots from up/down regulated genomic regions.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.10+, bash, GNU/Unix command-line utilities, and a conda environment named tornado_env containing deepTools computeMatrix/plotHeatmap by default. LSF bsub is optional for cluster submission; the default execution backend is local. No network access required. Writes outputs under a UTC timestamped run directory.
metadata:
  author: Hasan Al Reza <hasan.al.reza.bd@gmail.com>
  version: "0.3.0"
  status: draft
  last_reviewed: "2026-07-24"
---

# Tornado Plots

## Purpose

Generate reproducible tornado plots from genomic region BED files and BigWig signal tracks using a wrapper that stages inputs with symlinks, runs deepTools `computeMatrix reference-point`, and renders `plotHeatmap` output.

## When to Use

Use this skill when the user provides BED region files, BigWig signal tracks, input locations, and an output destination for a tornado plot or deepTools heatmap.

## When Not to Use

Do not use this skill for genomic feature annotation, motif enrichment, peak calling, differential peak testing, or non-genomic tornado/sensitivity charts.

## Required Inputs

- `regions`: one or more BED files for `computeMatrix -R`.
- `signals`: one or more BigWig files for `computeMatrix -S`.
- `inputDir`, `regionsDir`, or `signalsDir`: location for relative filenames.
- `outputPrefix`: prefix for the matrix and tornado plot output files.

## Optional Inputs

- `regionLabels`: labels for BED region groups; defaults to the `Up2FC` / `Down2FC` token when a filename contains it, such as `Empty.Up2FC.Region.bed`. When two unlabeled region sets match those tokens, the wrapper orders them as `Up2FC` first and `Down2FC` second. The shell helper wraps labels at underscores with literal newline characters before passing them to `plotHeatmap`.
- `sampleLabels`: labels for BigWig tracks; defaults to the sample name only, with technical suffixes like `.singleRep` removed. Compound labels such as `XPO1-AB_HEK293T_Empty` are passed as multiple display lines to prevent overlap.
- `labelRotation`: `plotHeatmap` label rotation; defaults to `45`.
- `outputRoot`: root directory for run outputs; defaults to `agentResults`.
- `executor`: `local` or `bsub`; defaults to `local`.
- `condaEnv`: conda environment for deepTools execution; defaults to `tornado_env`.
- `noConda`: run deepTools from the current `PATH` instead of conda only when the user explicitly requests it.
- deepTools options: `referencePoint`, `before`, `after`, `binSize`, `sortRegions`, `sortUsing`, `sortUsingSamples`, `heatmapHeight`, `heatmapWidth`, `colorMap`, `zMin`, `zMax`.
- LSF options for `bsub`: `proc`, `mem`, `queue`, `project`, and `jobName`.

## Workflow

1. Confirm the user supplied region BED files, signal BigWig files, and the input location for relative filenames.
2. Read `references/workflow-and-inputs.md` if input roles, output layout, LSF options, or interpretation details are unclear.
3. Run a dry run first with `run-tornado-plots.py` to validate file paths and inspect the exact `link.sh` and `plot.sh` commands.
4. Use `--run` only when the user asked to execute the workflow or confirmed the dry-run plan.
5. Report the run directory, expected matrix, plot PDF, symlink manifest, and metadata JSON.

## Scripts

- `run-tornado-plots.py`: wrapper that resolves filenames and locations, creates a timestamped run plan, calls `scripts/link.sh`, and calls `scripts/plot.sh` with `--executor local` and `--condaEnv tornado_env` by default.
- `scripts/link.sh`: creates symlinks for explicit files or pattern-matched inputs and records an input manifest.
- `scripts/plot.sh`: builds and executes the deepTools `computeMatrix reference-point` and `plotHeatmap` commands locally or with `bsub -L /bin/bash`.
- `link.sh` and `plot.sh`: root compatibility dispatchers for the generalized scripts under `scripts/`.

## Standard Invocation

```bash
python run-tornado-plots.py \
  --inputDir /path/to/inputs \
  --regions Empty.Up2FC.Region.bed Empty.Down2FC.Region.bed \
  --signals XPO1-AB_Mut.singleRep.bw XPO1-AB_WT.singleRep.bw \
  --regionLabels Up2FC Down2FC \
  --outputRoot agentResults \
  --outputPrefix xpo1_demo \
  --dryRun
```

Add `--run` after reviewing the dry-run plan. Use `--noConda` only when `computeMatrix` and `plotHeatmap` should come from the current shell environment instead of `tornado_env`.

## Output Format

Each execution writes to:

```text
<outputRoot>/tornado-plots-YYYYMMDDTHHMMSSZ/
├── linkedInputs/
├── input-symlinks.tsv
├── <outputPrefix>_matrix.gz
├── <outputPrefix>_tornado.pdf
└── tornado-plots-run-metadata.json
```

For `--executor bsub`, the run directory also contains the submitted command script generated by `scripts/plot.sh`.

## Quality Checks

Before finishing, verify:

- all referenced BED and BigWig inputs exist,
- label counts match the corresponding file counts,
- input basenames are unique for symlink staging,
- dry-run commands contain the expected `-R` region order and `-S` signal order,
- `--run` was used only when execution was intended,
- outputs are reported with absolute or clearly rooted paths.

## Failure and Escalation

If required filenames, directories, or labels are missing, ask the minimum clarifying question. If `conda`, the `tornado_env` environment, `computeMatrix`, `plotHeatmap`, or `bsub` are unavailable, report the missing dependency and preserve the dry-run command so the user can run it in the correct environment.
