# Tornado Plots Workflow and Inputs

## Contents

- Input roles
- Wrapper behavior
- Shell script behavior
- Conda environment
- Execution modes
- Output layout
- Interpretation notes
- Common failures

## Input Roles

`regions` are BED files passed to deepTools `computeMatrix -R`. Use one BED file for a single region set or multiple BED files for grouped heatmap sections such as upregulated and downregulated regions.

When the wrapper receives two unlabeled region sets that resolve to `Up2FC` and `Down2FC`, it orders them as `Up2FC` first and `Down2FC` second before staging inputs and building `plotHeatmap --regionsLabel` values. The wrapper also strips technical suffixes like `.singleRep` from BigWig sample filenames so labels default to the sample name only. The plot helper inserts literal newline characters after underscores before invoking `plotHeatmap`, allowing long region and sample labels to render on multiple lines.

`signals` are BigWig files passed to `computeMatrix -S`. Use one or more BigWig files in the exact sample order desired in the final heatmap.

Relative input filenames are resolved from `--regionsDir` for BED files, `--signalsDir` for BigWig files, or `--inputDir` when both input types live in one directory. Absolute file paths do not require an input directory.

Input basenames must be unique because the wrapper stages all selected files as symlinks in one `linkedInputs/` directory before plotting.

## Wrapper Behavior

The main wrapper is:

```text
run-tornado-plots.py
```

It performs these steps:

1. Validate BED and BigWig input paths.
2. Validate label counts when labels are supplied.
3. Create a UTC run ID in `YYYYMMDDTHHMMSSZ` format.
4. Plan a run directory named `tornado-plots-<runId>`.
5. Build the `scripts/link.sh` command.
6. Build the `scripts/plot.sh` command with `--executor local` and `--condaEnv tornado_env` by default.
7. Execute both commands only when `--run` is supplied.
8. Write `tornado-plots-run-metadata.json` after a successful run or LSF submission.

The wrapper defaults to dry-run behavior. A dry run validates source files and prints the commands, but does not create the run directory or submit deepTools.

## Shell Script Behavior

`scripts/link.sh` creates symlinks for explicit files or pattern matches. It writes `input-symlinks.tsv` with source and staged-link paths. Use `--force` only when replacing existing staged paths is intentional.

`scripts/plot.sh` runs:

```text
computeMatrix reference-point
plotHeatmap
```

Default deepTools values match the original tornado-plot workflow:

| Option | Default |
|---|---|
| `referencePoint` | `center` |
| `before` | `2000` |
| `after` | `2000` |
| `binSize` | `25` |
| `missingDataAsZero` | enabled |
| `sortRegions` | `descend` |
| `sortUsing` | `mean` |
| `sortUsingSamples` | `1` |
| `labelRotation` | `45` |
| `heatmapHeight` | `15` |
| `heatmapWidth` | `4` |

## Conda Environment

The default deepTools runtime is:

```text
tornado_env
```

The wrapper passes `--condaEnv tornado_env` to `scripts/plot.sh` unless the user supplies another environment with `--condaEnv` or explicitly disables conda with `--noConda`.

For local execution, `scripts/plot.sh` runs:

```text
conda run -n tornado_env computeMatrix ...
conda run -n tornado_env plotHeatmap ...
```

For LSF execution, the submitted command script also uses `conda run -n tornado_env`, so the compute node must have the `conda` executable available on `PATH`.

## Execution Modes

Use `--executor local` by default when you want the helper to run the deepTools commands in the current shell. Use `--executor bsub` only when you explicitly want cluster submission. Use `--noConda` only when `computeMatrix` and `plotHeatmap` should be resolved directly from `PATH`.

Use `--executor bsub` on an LSF cluster. The plot script writes a command script into the run directory and submits it with `bsub -L /bin/bash` so the job starts in a login bash shell. LSF options include `--proc`, `--mem`, `--queue`, `--project`, and `--jobName`.

## Output Layout

The wrapper writes run artifacts under:

```text
<outputRoot>/tornado-plots-YYYYMMDDTHHMMSSZ/
```

Expected files:

| File | Description |
|---|---|
| `linkedInputs/` | Symlinked BED and BigWig inputs. |
| `input-symlinks.tsv` | Source-to-link manifest. |
| `<outputPrefix>_matrix.gz` | deepTools matrix from `computeMatrix`. |
| `<outputPrefix>_tornado.pdf` | heatmap/tornado plot from `plotHeatmap`. |
| `tornado-plots-run-metadata.json` | Reproducibility metadata and command vectors. |
| `<jobName>.commands.sh` | LSF command script when using `--executor bsub`. |

## Interpretation Notes

The plot shows signal intensity around each region reference point. Rows correspond to genomic regions, columns correspond to genomic bins around the reference point, and panels correspond to BigWig samples. Sort order and sample used for sorting are controlled by `--sortRegions`, `--sortUsing`, and `--sortUsingSamples`.

State that tornado plots summarize signal enrichment around selected regions; they do not establish causality, differential binding, or statistical significance without the upstream analysis that produced the BED files.

## Common Failures

- Missing input file: verify the filename and the correct `--inputDir`, `--regionsDir`, or `--signalsDir`.
- Duplicate basenames: rename or stage inputs with unique filenames before running.
- Label mismatch: provide one `regionLabels` value per region BED and one `sampleLabels` value per signal BigWig.
- Missing conda environment: create or activate `tornado_env`, or pass a different environment with `--condaEnv`.
- Missing deepTools: install deepTools inside `tornado_env`, or use `--noConda` only when `computeMatrix` and `plotHeatmap` are already on `PATH`.
- Missing LSF: use `--executor local` or run on a cluster login node where `bsub` is available.
