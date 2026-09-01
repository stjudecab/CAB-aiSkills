# Input formats and genome resources

## Contents

- Supported inputs
- BED handling
- VOUT handling
- Genome support
- Annotation resource checks
- Agent checklist

## Supported inputs

The wrapper scans `--input-dir` for files matching `--bed-glob` and `--vout-glob`.

| Input | Default glob | Input kind | `voom2anno.sh` mode |
|-------|--------------|------------|---------------------|
| BED | `*.bed` | `bed` | `bed6i0` by default |
| Gzipped BED | `*.bed.gz` | `bed` | Decompress to `.bed`, then `bed6i0` by default |
| VOUT / peak-test output | `*.vout` | `vout` | `pktesth1` |

Hidden files are skipped. Files ending in `.anno` are skipped to avoid reprocessing generated annotation tables.

## BED handling

- BED inputs are treated as **header-free** by default.
- Use `--bed-has-header` only when every BED input has one header line.
- `*.bed.gz` files are decompressed into the timestamped output directory before annotation.
- A gzipped input named `sample.bed.gz` stages as `sample.bed`.
- If two inputs would stage to the same output filename, stop and resolve the collision before running.

## VOUT handling

- VOUT files are processed with `voom2anno.sh` mode `pktesth1`.
- Do not pass `--bed-has-header` expecting it to affect VOUT parsing.
- Mixed BED and VOUT runs are allowed by the wrapper, but report the mixed input types clearly because their upstream meanings differ.

## Genome support

`--genome` is required. Do not infer or default to `hg38`.

| Genome | TSS annotation file |
|--------|---------------------|
| `hg38` | `gencode.v31.hg38.gtf.bed.sorted.tss` |
| `hg19` | `gencode.v19.hg19.bed.tss` |
| `mm10` | `gencode.vM22.mm10.gtf.bed.tss` |
| `mm9` | `gencode.vM17.mm9.gtf.bed.tss` |
| `sacCer3` | `sacCer3.shiftedBy125.flank375.bed.tss` |

Gene-body references for `inGeneBody` annotation (`annotateGenomicFeatures.py`):

| Genome | Gene-body BED file |
|--------|---------------------|
| `hg38`, `hg38_rDNA` | `AllGenes.hg38_v31.level_gene.feature_body.bed` |
| `hg19` | `AllGenes.hg19_v19.level_gene.feature_body.bed` |
| `mm10` | `AllGenes.mm10_vM22.level_gene.feature_body.bed` |

These live at the top level of `--annotations-dir` alongside the TSS files.

## Annotation resource checks

Before running, validate:

1. `--annotations-dir` exists.
2. The TSS file for `--genome` exists under `--annotations-dir`.
3. The feature annotation directory exists. By default this is `--annotations-dir`; use `--feature-anno-dir` only for a compatible alternate resource root.
4. Feature annotation subdirectories exist for the selected genome.
5. When gene-body annotation is enabled, the gene-body BED for `--genome` exists under `--annotations-dir`.

Expected feature files for human/mouse genomes:

```text
annotations/<genome>/
|-- 2kb.promoter.up.bed
|-- 2kb.promoter.down.bed
|-- 2kb.promoter.bed
|-- 2kb.exon.bed
|-- 2kb.intron.bed
|-- 2kb.tes.bed
|-- 2kb.dis5.bed
|-- 2kb.dis3.bed
|-- 2kb.intergenic.bed
`-- 2kb.lst
```

For `sacCer3`, the bundled feature set uses `1kb.*` files plus yeast-specific background and label files.

## Agent checklist

1. Ask for the genome build if it is missing.
2. List matched BED/BED.GZ/VOUT files before a large run.
3. Confirm whether BED files are header-free or use `--bed-has-header` when the user explicitly says they have a header.
4. Run `--dry-run` first unless the user explicitly asks to execute immediately.
5. Report the genome build, TSS annotation file, and whether bundled or custom feature resources were used.
