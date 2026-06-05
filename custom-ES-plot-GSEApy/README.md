<p align="center">
  <img src="assets/CAB-aiSkills_custom-ES-plot-GSEApy.svg" alt="custom-ES-plot-GSEApy skill badge" width="520" />
</p>

# Custom ES plot (GSEApy prerank) — Agent Skill

Portable skill package for generating **GSEApy prerank enrichment score plots** and **companion statistics** from saved `pre_res` pickle files. Agent instructions live in [SKILL.md](SKILL.md).

## Environment

- **Python** 3.10 or newer (3.10–3.12 recommended for Conda)
- **GSEApy** must be importable when loading pickles (stores `gseapy.gsea.Prerank` objects)
- **Local filesystem** only after setup; no network required at plot time

### Conda (recommended)

```bash
conda env create -f environment.yml
conda activate gsea-prerank-plot
```

### Pip fallback

```bash
pip install -r requirements.txt
```

## Install in Cursor / agent clients

- **Project skill**: copy or symlink this folder to `.cursor/skills/custom-ES-plot-GSEApy/`.
- **Invoke** by name: `custom-ES-plot-GSEApy`, or ask the agent to plot GSEApy prerank enrichment from a pickle as described in [SKILL.md](SKILL.md).

## Quick start — one gene set

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest
```

## Quick start — regex subset

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName 'SOS_peaks.*'
```

## Quick start — list file

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName examples/gene_sets_sos_peaks.lst
```

## Quick start — list gene sets only (no plots)

Preview which gene sets match a regex:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName 'SOS_peaks.*' \
  --listOnly
```

Confirm that one gene set exists in the pickle:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest \
  --listOnly
```

Write the full gene-set inventory to a file:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName allGeneSets \
  --listOnly \
  --outputDir ./tmp/gene_set_inventory
```

With `--outputDir`, list-only runs also write `gene_sets.list.txt` and `run_metadata.json`.

## Run layout and metadata

- Default output: `plots/enrichment/<pkl_stem>/<run_id>/` next to the input pickle.
- Each run writes `run_metadata.json` with UTC run ID, input path, and plotted gene sets.
- Agent runs should prefer `agentResults/custom-ES-plot-GSEApy-<runId>/` as `--outputDir`.

## Layout

- [SKILL.md](SKILL.md) — when to use, agent workflow, outputs
- [scripts/plotGseapyPrerankEnrichment.py](scripts/plotGseapyPrerankEnrichment.py) — CLI entrypoint
- [references/methods.md](references/methods.md) — flags, gene-set resolution, outputs
- [references/citations.md](references/citations.md) — GSEA / GSEApy attribution
- [examples/evaluation-prompts.md](examples/evaluation-prompts.md) — evaluation scenarios
- [environment.yml](environment.yml) / [requirements.txt](requirements.txt) — dependencies

## User-facing prompt examples

Example prompts a user might type and how the agent should interpret them.
See [examples/evaluation-prompts.md](examples/evaluation-prompts.md) for detailed expected behavior.

| User prompt | Interpretation |
|---|---|
| "Plot the GSEApy enrichment for SOS_peaks closest from my RNA prerank pickle." | `--inPKL` = user pickle; `--geneSetName` = exact `SOS_peaks...closest` term (confirm spelling from pickle if needed). |
| "Make ES plots for all SOS_peaks gene sets in `GSEApy_prerank.pre_res.RNA.SynGR303_48h_vs_DMSO_48h.pkl`." | `--geneSetName 'SOS_peaks.*'`; set `--outputDir` under `agentResults/custom-ES-plot-GSEApy-<runId>/`. |
| "Which SOS_peaks gene sets are in my prerank pickle?" | `--geneSetName 'SOS_peaks.*' --listOnly` (no plots); report logged names. |
| "Does `HALLMARK_APOPTOSIS` exist in this pre_res pkl?" | `--geneSetName HALLMARK_APOPTOSIS --listOnly`; warn if not found. |
| "Generate enrichment plots for the gene sets listed in `my_sets.lst` from this pre_res pkl." | `--geneSetName my_sets.lst` if path exists and ends in `.lst` or `.txt`. |
| "Plot enrichment for every gene set in the pickle." | `--geneSetName allGeneSets`; warn about large output before running unless user confirms. |
| "I have a prerank pkl but no gseapy installed — can you still plot?" | Explain GSEApy is required to unpickle; offer `conda env create -f environment.yml` then rerun. |
| "Run Enrichr on my DEG list and make pathway bar charts." | Out of scope; use `pathway-enrichment-enrichr`, not this skill. |

## Testing

From this directory:

```bash
python scripts/plotGseapyPrerankEnrichment.py --help
python -m pytest tests/
```

## Citation

Use [layered attribution](../docs/attribution.md).

| Layer | Credit |
|-------|--------|
| **Skill package** | Skill author in [AUTHORS.md](../AUTHORS.md); CAB-aiSkills `custom-ES-plot-GSEApy` |
| **Bundled script** | `plotGseapyPrerankEnrichment.py` — Wojciech Rosikiewicz (see file header) |
| **Method** | **GSEA** — Subramanian et al., *PNAS* 2005; **GSEApy** — Fang et al., *Bioinformatics* 2022 ([doi:10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)) |

Full wording: [references/citations.md](references/citations.md).

## License

Skill packaging and orchestration scripts: **[CC BY-NC-SA 4.0](../LICENSE.txt)** (see [AUTHORS.md](../AUTHORS.md) and [SKILL.md](SKILL.md)).
