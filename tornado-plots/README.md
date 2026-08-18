<p align="center">
  <img src="assets/CAB-aiSkills_tornado_plots.svg" alt="tornado plots skill badge" width="520" />
</p>

# Tornado Plots Agent Skill

Portable skill package for generating deepTools tornado plots from BED region files and BigWig signal tracks. Agent instructions live in [SKILL.md](SKILL.md).

The wrapper defaults to `local` execution and `tornado_env` for deepTools. Region labels default to `Up2FC` and `Down2FC` when filenames contain those tokens, BigWig sample labels default to the sample name only, and compound labels are wrapped at underscores with literal newline characters before being passed to `plotHeatmap`. `plotHeatmap` label rotation defaults to `45`. Use `--executor bsub` when you want cluster submission.

## Environment

- Python 3.10 or newer
- bash
- Conda environment `tornado_env` containing deepTools with `computeMatrix` and `plotHeatmap`
- LSF `bsub` for cluster submission

No network access is required.

The wrapper uses `tornado_env` by default:

```bash
conda create -n tornado_env -c conda-forge -c bioconda deeptools
```

Use `--condaEnv <name>` to choose a different environment, or `--noConda` only when `computeMatrix` and `plotHeatmap` should be resolved directly from `PATH`.

## Install in Agent Clients

- Copy or symlink this `tornado-plots/` directory into the agent skill path.
- Preserve `run-tornado-plots.py`, `scripts/`, `references/`, and `examples/`.
- Invoke by name or ask the agent to create a tornado plot from BED and BigWig inputs.

## Quick Start

Dry-run the workflow first:

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

Execute after reviewing the plan:

```bash
python run-tornado-plots.py \
  --inputDir /path/to/inputs \
  --regions Empty.Up2FC.Region.bed Empty.Down2FC.Region.bed \
  --signals XPO1-AB_Mut.singleRep.bw XPO1-AB_WT.singleRep.bw \
  --regionLabels Up2FC Down2FC \
  --outputRoot agentResults \
  --outputPrefix xpo1_demo \
  --run
```

Submit through LSF:

```bash
python run-tornado-plots.py \
  --inputDir /path/to/inputs \
  --regions Empty.Up2FC.Region.bed Empty.Down2FC.Region.bed \
  --signals XPO1-AB_Mut.singleRep.bw XPO1-AB_WT.singleRep.bw \
  --outputRoot agentResults \
  --outputPrefix xpo1_demo \
  --executor bsub \
  --queue cab_auto \
  --project tp_XPO1 \
  --proc 8 \
  --mem 128000 \
  --run
```

## Directory Structure

```text
tornado-plots/
├── SKILL.md
├── README.md
├── LICENSE
├── run-tornado-plots.py
├── link.sh
├── plot.sh
├── agents/
│   └── openai.yaml
├── assets/
│   └── CAB-aiSkills_tornado_plots.svg
├── examples/
│   └── evaluation-prompts.md
├── references/
│   └── workflow-and-inputs.md
├── scripts/
│   ├── link.sh
│   └── plot.sh
└── tests/
    └── test_tornado_plots_cli.py
```

## Outputs

Each execution writes a run-scoped directory:

```text
<outputRoot>/tornado-plots-YYYYMMDDTHHMMSSZ/
├── linkedInputs/
├── input-symlinks.tsv
├── <outputPrefix>_matrix.gz
├── <outputPrefix>_tornado.pdf
└── tornado-plots-run-metadata.json
```

For `--executor bsub`, the run directory also contains `<jobName>.commands.sh`.

## User-facing prompt examples

Example prompts a user might type and how the agent should interpret them.
See [examples/evaluation-prompts.md](examples/evaluation-prompts.md) for detailed expected behavior.

| User prompt | Interpretation |
|---|---|
| "Make a tornado plot from up.bed and down.bed using control.bw and treated.bw in /data/chipseq." | Use `--inputDir /data/chipseq`, two `--regions`, two `--signals`, dry-run first. |
| "Make a tornado plot from Empty.Up2FC.Region.bed and Empty.Down2FC.Region.bed using XPO1-AB_Mut.singleRep.bw and XPO1-AB_WT.singleRep.bw in /data/chipseq." | Use `--inputDir /data/chipseq`, keep the default region order as `Up2FC` then `Down2FC`, and let sample labels default to `XPO1-AB_Mut` and `XPO1-AB_WT`. |
| "Run the XPO1 tornado plot with bsub on cab_auto, project tp_XPO1." | Use `--executor bsub --queue cab_auto --project tp_XPO1` with default `--condaEnv tornado_env`; ask for missing BED/BigWig filenames if absent. |
| "My BED files are in regions/ and BigWigs are in mergedCoverage/. Plot gain and loss regions." | Use `--regionsDir regions --signalsDir mergedCoverage`; validate exact filenames. |
| "Use 5 kb around peak centers and 50 bp bins for the tornado plot." | Set `--before 5000 --after 5000 --binSize 50` with the supplied input files. |
| "Create tornado plots for my ChIP tracks." | Ambiguous; ask for BED region filenames, BigWig filenames, and input location. |
| "Call peaks and find motifs in the gained peaks." | Out of scope; this skill expects precomputed BED and BigWig files. |

## Testing

Run the focused smoke tests:

```bash
python -m pytest tests
```

Check CLI help manually:

```bash
python run-tornado-plots.py --help
bash scripts/link.sh --help
bash scripts/plot.sh --help
```

## License

This skill package is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. See [LICENSE](LICENSE).

## Maintainer

Maintainer metadata follows [SKILL.md](SKILL.md). Confirm copyright and author lines before release when maintainership changes.
