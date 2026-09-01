# Workflow and outputs

## Contents

- Command flow
- Runtime modes
- Output layout
- Key artifacts
- Quality checks
- Troubleshooting cues

## Command flow

For each staged input, the wrapper runs:

```text
input .bed/.vout
  -> voom2anno.sh
  -> <input>.anno
  -> annotateGenomicFeatures.py
  -> feature-annotated .anno outputs (FeatureAssignment + inGeneBody)
  -> extractRegionsPerFeature.py
  -> <input>.byFeature/ (feature BEDs, combined GMT, manifests)
```

After all inputs are processed, the wrapper runs `OrganizeAnnotationResults.py` unless `--skip-organize` is set.

## Runtime modes

| Option | Behavior |
|--------|----------|
| No `--run` | Behaves like a dry run; validates and prints commands |
| `--dry-run` | Validates inputs, resources, runtime, helper scripts, and commands without execution |
| `--run` | Executes the workflow |
| `--use-current-python` | Uses the active Python and PATH |
| `--python-bin <path>` | Uses an explicit Python interpreter |
| `--conda-prefix <path>` | Uses an existing Conda environment prefix |
| `--create-conda-env` | Creates `--conda-env` from `--conda-yaml` when missing |
| `--gene-body-annotation off` | Skip `inGeneBody` annotation in annotateGenomicFeatures.py |
| `--skip-feature-extraction` | Skip extractRegionsPerFeature.py |
| `--fdr-threshold 0.05` | FDR cutoff for voom-mode feature extraction |
| `--log2fc-threshold 0.0` | Absolute log2FC cutoff for voom-mode feature extraction |
| `--skip-organize` | Do not run OrganizeAnnotationResults.py |

The default Conda environment name is `epi_anno_env`; the default YAML is `environment/epi_anno_env.yml`.

## Output layout

The wrapper appends a UTC timestamp suffix to the final component of `--out-dir`:

```text
<out-dir>-YYYYMMDDTHHMMSSZ/
|-- finalReports/
|-- allOtherFiles/
|-- bedFileAnnotations/
|-- GenomicFeaturesAnnotation/
`-- <input>.byFeature/            # per-input feature BEDs + GMT (default)
    |-- *.bed or *.up.bed / *.down.bed
    |-- *.byFeature.genesets.gmt
    |-- extraction_manifest.json
    `-- extraction_manifest.tsv
```

The default output root is `annotation_output`, producing paths like:

```text
annotation_output-20260615T180000Z/
```

## Key artifacts

Depending on input type and downstream organization results, outputs can include:

- Nearby-gene annotated `*.anno` tables
- Genomic feature annotation tables with `FeatureAssignment` and `inGeneBody`
- Per-feature BED exports under `<input>.byFeature/`
- Combined GMT gene-set files (`*.byFeature.genesets.gmt`)
- Feature extraction manifests (`extraction_manifest.json`, `extraction_manifest.tsv`)
- Excel annotation workbooks
- BED exports
- GMT files for GSEA-style downstream analysis
- RNK files
- MA plots
- Volcano plots
- PCA plots
- Heatmaps
- Genomic feature summary plots
- Combined final reports

## Quality checks

After a run:

1. Confirm the timestamped output directory exists.
2. Confirm every input has a corresponding staged file in the output/work directory.
3. Confirm every input produced a non-empty `*.anno` file unless `--skip-existing-anno` intentionally skipped it.
4. Confirm `<input>.byFeature/` exists with BED/GMT outputs unless `--skip-feature-extraction` was used.
5. Confirm `finalReports/` exists when organization was not skipped.
6. Inspect stderr or terminal output for failed helper commands.
7. For publication/reporting, record `--genome`, TSS annotation file, `--feature-anno-dir` if used, gene-body setting, extraction thresholds, and runtime environment choice.

## Troubleshooting cues

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `wcn.sh: command not found` | Helper scripts are not on PATH | Ensure `scripts/` exists and wrapper prepends it to PATH |
| `Missing CAB helper scripts` | Required helper file absent or not discoverable | Restore helper scripts or set `--scripts-dir` |
| Missing TSS annotation error | `--genome` and `--annotations-dir` do not match resources | Use a supported genome or correct `--annotations-dir` |
| `KeyError: '2kb.promoter.up.bed'` | Feature annotation directory lacks expected BED files | Use bundled annotations or a compatible `--feature-anno-dir` |
| Conda environment not found | `epi_anno_env` is absent | Use `--create-conda-env`, `--conda-prefix`, or `--use-current-python` |
| First BED region missing | Header-free BED was processed as headered | Omit `--bed-has-header` for header-free BED files |
