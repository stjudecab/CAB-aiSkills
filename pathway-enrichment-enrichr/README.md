
<p align="center">
  <img src="assets/CAB-aiSkills_pathway-enrichment-enrichr.svg" alt="pathway-enrichment-enrichr skill badge" width="520" />
</p>

# Pathway enrichment (Enrichr) — Agent Skill

Portable skill package for **Enrichr** pathway enrichment with **Excel** summaries, **PDF** bar charts, and (for multiple gene lists) **summary heatmaps** and **dot plots**, using the same core behavior as the historical `sjcab_custom_pathwayEnrichment` scripts. Agent instructions live in [SKILL.md](SKILL.md).

## Environment

- **Python** 3.9 or newer
- **Network**: HTTPS access to `https://maayanlab.cloud` (Enrichr)
- **Python packages** (install from the skill root):

```bash
pip install -r requirements.txt
```

## Install in Cursor / agent clients

- **Project skill**: copy or symlink this folder to `.cursor/skills/pathway-enrichment-enrichr/` in a repository, or add the directory to your agent’s skill path per product documentation.
- **Invoke** by name: `pathway-enrichment-enrichr`, or ask the agent to run Enrichr pathway enrichment as described in [SKILL.md](SKILL.md).

## Quick start — one gene list

```bash
python scripts/run_pathway_enrichment.py \
  --mode single \
  --outputDir /path/to/out \
  --genes /path/to/genes.txt \
  --outPrefix MyRun \
  --libraryPreset stjudehg \
  --engine Enrichr
```

Results land in `/path/to/out/<UTC_runId>/`: merged TSVs (`MyRun.sum.*`), Excel workbooks, and top-pathway bar PDFs.

## Quick start — GMT (multiple sets)

```bash
python scripts/run_pathway_enrichment.py \
  --mode gmt \
  --outputDir /path/to/out \
  --gmt /path/to/sets.gmt \
  --outPrefix batch01 \
  --libraryPreset stjudehg
```

Per-set outputs, combined summaries, heatmaps, and dot plots are written under `/path/to/out/<UTC_runId>/batch01/`.

## Quick start — many separate list files (manifest)

Create a TSV with headers `file` and `label` (see [examples/sample_manifest.tsv](examples/sample_manifest.tsv)):

```bash
python scripts/run_pathway_enrichment.py \
  --mode manifest \
  --outputDir /path/to/out \
  --manifest /path/to/gene_list_manifest.tsv \
  --outPrefix batch01
```

The helper builds a temporary GMT under the run folder, then runs the same pipeline as **gmt** mode.

## Run layout and metadata

- Each execution creates **`<outputDir>/<runId>/`** (default `runId` = UTC `YYYYMMDDTHHMMSSZ`).
- **`run_metadata.json`** in that folder records mode, engine, library preset, and important paths.
- Reuse an existing run directory only with **`--overwrite`** (off by default).

## Layout

- [assets/](assets/) — CAB aiSkills logo and this skill’s badge (for standalone README rendering)
- [SKILL.md](SKILL.md) — when to use, agent workflow, outputs
- [scripts/run_pathway_enrichment.py](scripts/run_pathway_enrichment.py) — recommended entrypoint
- [scripts/enrichr_api.py](scripts/enrichr_api.py) — Enrichr client and GMT batch logic
- [scripts/pathway_dotplot.py](scripts/pathway_dotplot.py) — cross-sample dot plots (GMT batch)
- [references/methods.md](references/methods.md) — formats and behavior details
- [examples/](examples/) — minimal manifest / gene list samples

## Testing

From this directory:

```bash
python scripts/run_pathway_enrichment.py --help
python -m pytest tests/
```

## License

Skill packaging and orchestration scripts: **[CC BY-NC-SA 4.0](../LICENSE.txt)** (see [AUTHORS.md](../AUTHORS.md) and [SKILL.md](SKILL.md)). The bundled `enrichr_api.py` retains its original upstream notice (Beisi Xu && St Jude) in-file.
