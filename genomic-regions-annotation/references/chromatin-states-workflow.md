# Chromatin-state workflow (agent operations)

## Contents

- When to use this branch
- Required inputs
- Model lookup
- Persistent environment
- Run directory layout
- Prepare model
- Annotate
- Optional heatmap
- Quality checks
- Failure modes

## When to use this branch

Use when the user asks to annotate peaks/regions to ChromHMM, Segway, Roadmap, ENCODE chromatin states, or custom emission dense BED models.

Do **not** run `run_genomic_regions_annotation.py` or `OrganizeAnnotationResults.py` for this branch.

## Required inputs

- One or more BED files (or an `.lst` listing them)
- Explicit genome build (`hg19` or `hg38` for precalculated models; custom models are as-is)
- Either:
  - a Collection ID (`E123` or `ENCFF…`), or
  - a custom dense BED + state2name TSV

If genome or collection is missing, ask before downloading or annotating.

### Bundled example BED resources

For demo and regression runs, use the packaged K562 peak sets under
`example_input/chromatin/` (see that directory’s README):

- `CTCF_K562_ENCFF396BZQ.bed`
- `POLR2A_K562_ENCFF285MBX.bed`
- `exampleInput.lst` (skill-root-relative paths to both files)

Prefer these for ChromHMM E123 / Segway K562 demos. Use `tests/fixtures/toy_*.bed`
only for offline unit/smoke tests that must not require network or large inputs.

## Model lookup

1. Read `references/chromatin-states/availableModelsLookup.tsv`.
2. Cross-check Roadmap (`RoadmapCollectionsMetadata.tsv`) and Segway (`Segway_annotations_ENCODE_metadata.tsv`) names/sample types.
3. Recommend Collection ID(s) with a short biological rationale.
4. Wait for user confirmation before prepare/annotate.

## Persistent environment

```bash
bash scripts/ensure_env.sh
```

Cache: `~/.cache/cursor-skills/genomic-regions-annotation/conda-env/`. Force rebuild with `--force-rebuild`.

## Run directory layout

```text
agentResults/genomic-regions-annotation-<YYYYMMDDTHHMMSSZ>/
├── agent_request.txt
├── agent_workflow.md
├── models/                          # copies of dense BED + state2name + model_meta
├── BEDinContext/                    # annotation outputs (-o)
├── run_metadata.json
└── logs/
    ├── prepare_chromatin_model.log  # when prepare writes here
    ├── BEDinContext.log
    └── commands.log
```

## Prepare model

```bash
python scripts/prepare_chromatin_model.py \
  --collection E123 \
  --genome hg38 \
  --copyToRunDir agentResults/genomic-regions-annotation-<runId>/models \
  --outputDir agentResults/genomic-regions-annotation-<runId> \
  --runId <runId> \
  --agentRequestFile agentResults/.../agent_request.txt \
  --agentWorkflowFile agentResults/.../agent_workflow.md
```

Stdout prints the absolute cached dense BED path. Reuses `cache/<collection>_<genome>_dense.bed` when present.

For Segway + hg38, the helper runs liftOver automatically.

For custom models, skip prepare; copy the user dense BED and state2name into `models/`.

## Annotate

Build an absolute-path `.lst` of input BEDs. Choose state2name:

- Roadmap → `references/chromatin-states/state2name.tsv`
- Segway → `references/chromatin-states/ENCODE_state2name.tsv`
- Custom → user-provided TSV

```bash
python scripts/BEDinContext.py \
  -r /abs/path/to/regions.lst \
  -s /abs/path/to/cache/E123_hg38_dense.bed \
  -o BEDinContext \
  --state2name references/chromatin-states/state2name.tsv \
  --outputDir agentResults/genomic-regions-annotation-<runId> \
  --runId <runId> \
  --agentRequestFile .../agent_request.txt \
  --agentWorkflowFile .../agent_workflow.md
```

Use the default aggregation (**regions**): each peak is assigned once to the state with the largest overlapping base-pair length, then counted. Primary tables/plots stay at the top of `-o`. Only add `-a bp` or `-a both` if the user explicitly wants base-pair summaries; those secondary outputs are written under `<out>/aggregationByBp/` and must not be presented as the primary peak-distribution result.
## Optional heatmap

```bash
python scripts/plot_chromatin_state_heatmap.py \
  --inputFile .../BEDinContext/statsCombined.frc.tsv \
  --outputPrefix .../chromatin_fractions_heatmap \
  --outputDir ... \
  --runId <runId>
```

## Quality checks

- Exit code 0
- `statsCombined.num.tsv` and `statsCombined.frc.tsv` exist
- Model copies exist under `models/`
- `run_metadata.json` and `logs/BEDinContext.log` exist
- No unexpected ERROR/CRITICAL in logs
- Confirm genome build and collection name reported to the user

## Failure modes

| Error | Fix |
|-------|-----|
| `statesFile ... was not found` | Run `prepare_chromatin_model.py` or pass a real dense BED path |
| `UCSC liftOver was not found` | `bash scripts/ensure_env.sh --force-rebuild` (needs `ucsc-liftover`) |
| `Collection ... was not found` | Check metadata TSVs; verify E### / ENCFF ID |
| Download failures | Retry network; verify Roadmap/ENCODE URL still valid |
| Missing genome | Ask user; never default |
