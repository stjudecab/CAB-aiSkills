<p align="center">
  <img src="assets/CAB-aiSkills_custom-ES-plot-GSEApy.svg" alt="custom-ES-plot-GSEApy skill badge" width="520" />
</p>

# Custom ES plot (GSEApy prerank & Broad GSEA) — Agent Skill

Portable skill package for generating **GSEA enrichment score plots** and **companion statistics** from either:

- saved **GSEApy prerank `pre_res` pickle** files, or
- **Broad Institute GSEA desktop output directories** (folders containing `edb/`).

Agent instructions live in [SKILL.md](SKILL.md).

## Environment

- **Python** 3.10 or newer (3.10–3.12 recommended for Conda)
- **GSEApy** must be importable (required for pickle unpickling and Broad ES replotting)
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
- **Invoke** by name: `custom-ES-plot-GSEApy`, or ask the agent to plot GSEA enrichment from a pickle or Broad GSEA output directory as described in [SKILL.md](SKILL.md).

## Input modes

Choose **one** input source per run (`--inPKL` and `--inGseaDir` are mutually exclusive):

| Mode | Flag | When to use |
|------|------|-------------|
| **GSEApy pickle** | `--inPKL` | You ran GSEApy prerank and saved `GSEApy_prerank.pre_res.*.pkl`. |
| **Broad GSEA** | `--inGseaDir` | You ran Broad GSEA desktop preranked GSEA and have the output folder (e.g. `48h.GseaPreranked.<timestamp>/`). |

Both modes support the same **`--geneSetName`** selection grammar (exact names, regex, list files, `allGeneSets`) and **`--listOnly`** preview mode. Broad mode additionally accepts optional **`--weight`** (defaults to infer from the Broad `.rpt` file or `1.0`).

## Quick start — GSEApy pickle, one gene set

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName CTCF_peaks.1bp.c_2p5.g_100.l_300.closest
```

## Quick start — Broad GSEA, one gene set

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName REACTOME_HEME_SIGNALING
```

## Quick start — Broad GSEA, regex subset

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName 'CHIP.EP300.*48H.*UP'
```

## Quick start — GSEApy pickle, regex subset

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName 'CTCF_peaks.*'
```

## Quick start — list file

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName examples/gene_sets_ctcf_peaks.lst
```

## Quick start — list gene sets only (no plots)

Preview which gene sets match a regex in a Broad GSEA directory:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName 'REACTOME_.*' \
  --listOnly
```

Confirm that one gene set exists in a GSEApy pickle:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inPKL /path/to/GSEApy_prerank.pre_res.RNA.contrast.pkl \
  --geneSetName SOS_peaks.1bp.c_2p5.g_100.l_300.closest \
  --listOnly
```

Write the full gene-set inventory to a file:

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h.GseaPreranked.1781298215614 \
  --geneSetName allGeneSets \
  --listOnly \
  --outputDir ./tmp/gene_set_inventory
```

With `--outputDir`, list-only runs also write `gene_sets.list.txt` and `run_metadata.json`.

## Quick start — combined multi-pathway trace plot (Broad GSEA)

Overlay several gene sets in one figure (for example all `TOP500_UP` and all `TOP500_DOWN` ChIP sets):

```bash
python scripts/plotGseapyPrerankEnrichment.py \
  --inGseaDir /path/to/48h_10k.GseaPreranked.1781533878697 \
  --geneSetName 'CHIP.*48H.*FCPRANK.*TOP.*500.*' \
  --combineTrace \
  --combineTraceOnly
```

This writes `combined_trace_TOP500_UP.{png,pdf}` and `combined_trace_TOP500_DOWN.{png,pdf}` using `gseapy.gseaplot2`.

## Run layout and metadata

- Default output: `plots/enrichment/<input_stem>/<run_id>/` next to the input pickle or Broad GSEA directory.
- Each run writes `run_metadata.json` with UTC run ID, `input_source` (`gseapyPkl` or `broadGsea`), and plotted gene sets.
- Agent runs should prefer `agentResults/custom-ES-plot-GSEApy-<runId>/` as `--outputDir`.

## Layout

- [SKILL.md](SKILL.md) — when to use, agent workflow, outputs
- [scripts/plotGseapyPrerankEnrichment.py](scripts/plotGseapyPrerankEnrichment.py) — CLI entrypoint
- [scripts/broadGseaInput.py](scripts/broadGseaInput.py) — Broad GSEA `edb/` parsing and plotting helpers
- [references/methods.md](references/methods.md) — flags, input modes (GSEApy pickle vs Broad GSEA), gene-set resolution, outputs
- [references/citations.md](references/citations.md) — GSEA / GSEApy attribution
- [examples/evaluation-prompts.md](examples/evaluation-prompts.md) — evaluation scenarios
- [environment.yml](environment.yml) / [requirements.txt](requirements.txt) — dependencies

## User-facing prompt examples

Example prompts a user might type and how the agent should interpret them.
See [examples/evaluation-prompts.md](examples/evaluation-prompts.md) for detailed expected behavior.

| User prompt | Interpretation |
|---|---|
| "Plot the GSEApy enrichment for SOS_peaks closest from my RNA prerank pickle." | `--inPKL` = user pickle; `--geneSetName` = exact `SOS_peaks...closest` term (confirm spelling from pickle if needed). |
| "Replot ES plots for REACTOME_HEME_SIGNALING from my Broad GSEA 48h output folder." | `--inGseaDir` = Broad output directory; `--geneSetName REACTOME_HEME_SIGNALING`. |
| "Make ES plots for all SOS_peaks gene sets in `GSEApy_prerank.pre_res.RNA.SynGR303_48h_vs_DMSO_48h.pkl`." | `--inPKL` + `--geneSetName 'SOS_peaks.*'`; set `--outputDir` under `agentResults/custom-ES-plot-GSEApy-<runId>/`. |
| "Plot all CHIP.EP300 48h UP gene sets from my Broad GSEA run, even if not significant." | `--inGseaDir` + `--geneSetName 'CHIP.EP300.*48H.*UP'`; significance is not required. |
| "Which SOS_peaks gene sets are in my prerank pickle?" | `--inPKL` + `--geneSetName 'SOS_peaks.*' --listOnly` (no plots); report logged names. |
| "List all gene sets tested in my Broad GSEA 48h folder." | `--inGseaDir` + `--geneSetName allGeneSets --listOnly`. |
| "Does `HALLMARK_APOPTOSIS` exist in this pre_res pkl?" | `--inPKL` + `--geneSetName HALLMARK_APOPTOSIS --listOnly`; warn if not found. |
| "Generate enrichment plots for the gene sets listed in `my_sets.lst` from this Broad GSEA output." | `--inGseaDir` + `--geneSetName my_sets.lst` if path exists and ends in `.lst` or `.txt`. |
| "Plot enrichment for every gene set in the pickle." | `--inPKL` + `--geneSetName allGeneSets`; warn about large output before running unless user confirms. |
| "I only have a handful of ES plots from Broad GSEA — can you replot specific gene sets?" | `--inGseaDir` pointing at the GSEA output folder; Broad stores all tested sets in `edb/results.edb`. For GSEApy runs, use `--inPKL` with the `pre_res` pickle instead. |
| "I have a prerank pkl but no gseapy installed — can you still plot?" | Explain GSEApy is required; offer `conda env create -f environment.yml` then rerun. |
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
| **Bundled scripts** | `plotGseapyPrerankEnrichment.py`, `broadGseaInput.py` — Wojciech Rosikiewicz (see file headers) |
| **Method** | **GSEA** — Subramanian et al., *PNAS* 2005; **GSEApy** — Fang et al., *Bioinformatics* 2022 ([doi:10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)) |

Full wording: [references/citations.md](references/citations.md) (separate copy-paste methods text for GSEApy pickle and Broad GSEA inputs).

## License

Skill packaging and orchestration scripts: **[CC BY-NC-SA 4.0](../LICENSE.txt)** (see [AUTHORS.md](../AUTHORS.md) and [SKILL.md](SKILL.md)).
