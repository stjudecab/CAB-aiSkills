# Workflow And Inputs

## Contents

- Input requirements
- Genome and sequence compatibility
- Labels and outputs
- Runtime and execution options
- Staging and metadata
- Environment troubleshooting
- Interpretation limits

## Input Requirements

The runner accepts exactly two BED files: `--query` and `--reference`. Relative
paths are resolved under `--inputDir`. Symlinks are accepted when their targets
exist and are regular files. The files should contain genomic intervals with
consistent chromosome naming, for example both using `chr1` rather than one
using `1`.

The wrapper does not infer the genome build from filenames. `--genome` is
required because TxDb sequence information is applied before GenometriCorr.

## Genome And Sequence Compatibility

Supported builds are:

| Build | TxDb package |
|---|---|
| `hg19` | `TxDb.Hsapiens.UCSC.hg19.knownGene` |
| `hg38` | `TxDb.Hsapiens.UCSC.hg38.knownGene` |
| `mm10` | `TxDb.Mmusculus.UCSC.mm10.knownGene` |

Use a TxDb whose chromosome names match the BED files. A mismatch can result
in dropped intervals or errors while assigning `seqinfo`; investigate before
interpreting the result.

## Labels And Outputs

By default, labels are the BED basenames with the final `.bed` suffix removed.
Set `--queryLabel` and `--referenceLabel` when basenames are too long or contain
characters that are unsuitable for filenames. The R script produces both query
versus reference and reference versus query reports, including projection and
visualization PDFs.

The wrapper writes a run directory named
`genomic-regions-correlation-YYYYMMDDTHHMMSSZ`. It stages the original BED
files into `linkedInputs/` as symlinks by default and records source and staged
paths in `input-symlinks.tsv`. Use `--copyInputs` when the run must be
self-contained without links. Local runs fail if any of the four expected PDFs
are missing. A user-supplied `--runId` is accepted only in
`YYYYMMDDTHHMMSSZ` form and cannot overwrite an existing run directory.

## Runtime And Execution Options

The default behavior is a dry run. `--run` creates the run directory and
executes locally. `--noConda` uses `Rscript` from the current `PATH`;
`--condaPrefix` uses an existing environment directly; and
`--createCondaEnv --condaYaml FILE` creates a missing named environment.

For `--executor bsub`, the wrapper writes `<jobName>.commands.sh`, submits it
with `bsub -L /bin/bash`, and records the scheduler response. The wrapper does
not wait for asynchronous LSF output files; inspect the job and run directory
after submission.

## Staging And Metadata

`genomic-regions-correlation-run-metadata.json` records the run ID, status,
original and staged inputs, labels, genome, runtime/resource parameters,
commands, expected outputs, and LSF submission output when applicable. This
file is written only for an executed local run or a successful LSF submission;
dry runs do not create artifacts.

## Environment Troubleshooting

The wrapper uses the named conda environment by default and can create it from
the bundled YAML when `mamba` or `conda` is available. The YAML deliberately
does not depend on the stale Bioconda `r-genometricorr` recipe, which requires
R 3.1. With `--createCondaEnv`, the wrapper installs GenometriCorr 1.1.24 from
the upstream `favorov/GenometriCorr` repository after creating the modern R
environment. `--noConda` bypasses that lookup and requires `Rscript` plus all R
packages on `PATH`/`.libPaths()`.

The bundled R script does not install packages during execution. Install the
required packages in advance, preferably in the environment described by the
YAML. Do not mix genome TxDb packages from a different build.

## Interpretation Limits

GenometriCorr evaluates spatial relationships between region sets; it does not
establish biological causation, differential activity, or peak quality. Review
the generated reports alongside the region-generation method, genome build,
and any filtering or length thresholds used upstream.
