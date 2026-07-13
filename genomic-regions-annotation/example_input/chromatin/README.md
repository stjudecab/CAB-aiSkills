# Example chromatin-state inputs

Realistic ENCODE peak BEDs for chromatin-state annotation smoke/demo runs (K562).

| File | Description | Approx. size |
|------|-------------|--------------|
| `CTCF_K562_ENCFF396BZQ.bed` | CTCF peaks from ENCODE accession ENCFF396BZQ (K562) | ~3.4 MB |
| `POLR2A_K562_ENCFF285MBX.bed` | POLR2A peaks from ENCODE accession ENCFF285MBX (K562) | ~2.4 MB |
| `exampleInput.lst` | Manifest listing both BEDs (paths relative to skill root) |

These files are packaged with the skill for future agent and pytest runs. Prefer them for ChromHMM/Segway demos (for example Roadmap **E123** K562) rather than the tiny `tests/fixtures/toy_*.bed` set, which is offline-only.

## Usage from skill root

```bash
bash scripts/ensure_env.sh

# After preparing E123 (or another confirmed collection):
python scripts/BEDinContext.py \
  -r example_input/chromatin/exampleInput.lst \
  -s cache/E123_hg38_dense.bed \
  -o BEDinContext \
  --state2name references/chromatin-states/state2name.tsv \
  --outputDir /path/to/agentResults/genomic-regions-annotation-<runId> \
  --runId <runId>
```

When the agent builds a run-scoped `.lst`, rewrite entries to **absolute paths** so the cwd does not matter.
