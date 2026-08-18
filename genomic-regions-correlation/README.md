<p align="center">
  <img src="assets/CAB-aiSkills_genomic_regions_correlation.svg" alt="genomic regions annotation skill badge" width="520" />
</p>

# Genomic Regions Correlation

This skill runs GenometriCorr on two genomic-region BED files and produces reciprocal PDF reports and visualizations for `hg19`, `hg38`, or `mm10`. The operational instructions are in [SKILL.md](SKILL.md).

## Environment

The bundled `environment/genomic_regions_correlation.yml` defines the default conda environment. Create it with:

```bash
conda env create -f environment/genomic_regions_correlation.yml
```

The environment provides modern R/Bioconductor dependencies. When
`--createCondaEnv` is used, the wrapper installs upstream GenometriCorr 1.1.24
from GitHub because the available Bioconda recipe requires obsolete R 3.1.
The environment must provide `Rscript`, `GenomicRanges`, `rtracklayer`, and the
TxDb package for the requested genome.

## Quick Start

```bash
python run_genomic_regions_correlation.py \
  --inputDir regions \
  --query gained.bed \
  --reference lost.bed \
  --genome hg38 \
  --outputRoot agentResults \
  --outputPrefix gained_vs_lost \
  --run
```

Omit `--run` to validate inputs and print the command only. Outputs are written to a timestamped directory under `agentResults`.

Use an existing environment prefix or submit through LSF with:

```bash
python run_genomic_regions_correlation.py \
  --inputDir regions --query gained.bed --reference lost.bed --genome hg38 \
  --outputRoot agentResults --outputPrefix gained_vs_lost \
  --condaPrefix /path/to/genomic_regions_correlation --run
```

```bash
python run_genomic_regions_correlation.py \
  --inputDir regions --query gained.bed --reference lost.bed --genome hg38 \
  --outputRoot agentResults --outputPrefix gained_vs_lost \
  --executor bsub --queue cab_auto --proc 8 --mem 128000 --run
```

## Directory Structure

```text
genomic-regions-correlation/
├── SKILL.md
├── README.md
├── LICENSE
├── run_genomic_regions_correlation.py
├── agents/openai.yaml
├── references/workflow-and-inputs.md
├── scripts/GC.sh
├── scripts/genometriCorr.r
├── environment/genomic_regions_correlation.yml
└── tests/test_genomic_regions_correlation_cli.py
```

## User-facing prompt examples

| User prompt | Interpretation |
|---|---|
| "Compare gained.bed and lost.bed with GenometriCorr using hg38." | Run a dry run, then execute when requested or confirmed. |
| "Are these two BED region sets spatially correlated?" | Ask for the two BED paths and genome build if they are not supplied. |
| "Run genomic region correlation on the symlinked BED files in regions/." | Resolve the symlinks, validate both files, and require the genome build. |
| "Use my existing R environment for the correlation." | Add `--noConda` and validate `Rscript` and required R packages. |
| "Submit the GenometriCorr job with bsub." | Use `--executor bsub` and retain the submitted command in metadata. |
| "Create the conda environment if it is missing, then run the comparison." | Use `--createCondaEnv --condaYaml ... --run`; show the dry-run plan first. |
| "Keep copies of the two BED inputs with the results." | Use `--copyInputs` instead of symlinking them into `linkedInputs/`. |
| "Annotate these peaks with nearby genes." | Do not use this skill; use `genomic-regions-annotation`. |

## Testing

Run the focused smoke tests without requiring R packages:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## License

CC BY-NC-SA 4.0. See [LICENSE](LICENSE).
