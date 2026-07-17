# Inputs and outputs

## Contents

- Accepted input formats
- Conversion rules
- Run directory layout
- `run_metadata.json` fields
- CLI flags

## Accepted input formats

CBviz loads images with `matplotlib.pyplot.imread` and keeps the first three channels (RGB).

| Format | CBviz native? | Skill behavior |
|--------|---------------|----------------|
| PNG | Yes | Pass through |
| JPEG / JPG, TIFF, BMP, GIF | Yes (with Pillow) | Pass through |
| PDF | No | Convert via PyMuPDF → `prepared/<stem>.png` |
| SVG, EPS | No | Convert via host `rsvg-convert` or `inkscape` |
| Other | No | Fail with an actionable error |

## Conversion rules

- Never overwrite the user's original file in place.
- Write converted rasters under `<outputDir>/prepared/`.
- Default PDF page is **1** (`--page`); default DPI is **300**.
- `--forceConvert` re-encodes rasters to PNG even when CBviz could read them.

Standalone converter:

```bash
python scripts/convert_to_png.py --input figure.pdf --outputDir <runDir>
```

## Run directory layout

```text
agentResults/colorblind-sim-<YYYYMMDDTHHMMSSZ>/
├── <prefix>.png                 # primary simulation figure (mode=fast)
├── prepared/                    # optional converted inputs
│   └── <stem>.png
├── run_metadata.json
├── agent_request.txt
├── agent_workflow.md
└── logs/
    ├── run_colorblind_sim.log
    └── commands.log
```

With `--individualPlots`, additional files `outfile.<cvd-type>.png` appear beside the prefix.

## `run_metadata.json` fields

Minimum fields follow the repository AGENTS.md contract: `skill`, `script`, `run_id`, `command`, `inputs`, `parameters`, `tool_versions`, `summary`, `outputs`, `logs`, `attribution`, plus `citation_keys` (`cbviz`, `colorspacious`).

## CLI flags (main wrapper)

| Flag | Default | Meaning |
|------|---------|---------|
| `--input` | required | Figure path |
| `--outputPrefix` | required | CBviz outfile / prefix |
| `--mode` | `fast` | `fast` = cbviz-fast; `simulate` = full CLI |
| `--types` | `protan,deuteran,tritan` | simulate-mode CVD types |
| `--severity` | `100` | 0–100 |
| `--all` | off | simulate `-a` |
| `--individualPlots` | off | one file per type |
| `--noOriginal` | off | omit original panel |
| `--forceConvert` | off | force PNG normalization |
| `--page` / `--dpi` | `1` / `300` | PDF/SVG conversion |
| `--outputDir` / `--runId` / agent flags | see `--help` | audit trail |
