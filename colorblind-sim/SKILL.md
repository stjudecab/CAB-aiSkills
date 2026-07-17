---
name: colorblind-sim
description: >-
  Simulate how figures look under color vision deficiency (CVD) using CBviz
  (protanopia, deuteranopia, tritanopia, monochrome). Accepts PNG/JPEG/TIFF
  directly; converts PDF/SVG/EPS to PNG when needed. Use when asked for
  colorblind simulation, CVD preview, colorblindness check on plots, CBviz,
  protanopia/deuteranopia/tritanopia figure panels, or accessibility preview
  of scientific figures.
license: CC-BY-NC-SA-4.0
compatibility: >-
  Requires Python 3.10+ and a persistent venv via scripts/ensure_env.sh at
  ~/.cache/cursor-skills/colorblind-sim/venv/ (numpy, matplotlib, colorspacious,
  Pillow, pymupdf, cbviz). SVG/EPS conversion needs host rsvg-convert or
  inkscape. Local filesystem only after env install (network needed once to
  create the venv).
metadata:
  author: Wojciech Rosikiewicz <rosikiewicz@gmail.com>
  version: "0.1.0"
  status: draft
  last_reviewed: "2026-07-16"
allowed-tools: shell python
---

# Colorblind simulation (CBviz)

## Purpose

Produce **color vision deficiency (CVD) simulations** of scientific figures so authors can preview how plots appear under protanopia, deuteranopia, tritanopia, and related conditions. The skill wraps upstream **CBviz** ([wflynny/cbviz](https://github.com/wflynny/cbviz)) and adds format conversion plus a full run audit trail.

## When to Use

- Simulate **colorblind / CVD** appearance of a figure or plot.
- Preview **protanopia**, **deuteranopia**, **tritanopia**, or **monochrome**.
- User mentions **CBviz**, **cbviz-fast**, or accessibility of figure colors.
- Input is PNG/JPEG/TIFF/PDF/SVG and the goal is a simulation grid (not palette design).

## When Not to Use

- Designing a new colorblind-safe palette from scratch (use palette guidance tools separately).
- Claiming an automated **pass/fail “colorblind-friendly” test** — upstream CBviz `test` is broken and is **not** exposed by this skill.
- Editing vector source art for print production beyond raster simulation.

## Required Inputs

- **Figure path** (`--input`): PNG, JPEG, TIFF, BMP, GIF (native with Pillow), or PDF / SVG / EPS (converted to PNG first).
- **Output prefix** (`--outputPrefix`): path for the CBviz outfile (prefer under `agentResults/colorblind-sim-<runId>/`).

## Optional Inputs

- `--mode fast|simulate` (default **`fast`**: original + protan + deuteran + tritan).
- `--types` (simulate mode): comma-separated `protan*`, `deuteran*`, `tritan*`, `mono*`.
- `--severity` 0–100 (default 100).
- `--all` (simulate): *opic + anomalous panels.
- `--individualPlots`, `--noOriginal`.
- `--forceConvert`, `--page`, `--dpi` for conversion.
- Reproducibility: `--runId`, `--outputDir`, `--agentRequestFile`, `--agentWorkflowFile`.

See [references/inputs-and-outputs.md](references/inputs-and-outputs.md).

## Persistent runtime environment (CRITICAL)

| Item | Value |
|------|-------|
| Cache | `~/.cache/cursor-skills/colorblind-sim/venv/` |
| Setup helper | `bash scripts/ensure_env.sh` |
| Force rebuild | `bash scripts/ensure_env.sh --force-rebuild` |
| Backend | `python -m venv` (pure-Python; no Conda required) |

1. Before the first run, execute `bash scripts/ensure_env.sh` once (Python scripts also auto-bootstrap via `skill_env.py`).
2. Reuse the cache on later runs; do **not** recreate the venv every invocation.
3. Prefer `python scripts/run_colorblind_sim.py …` or `bash scripts/run_with_skill_env.sh …`.

## Reproducibility and documentation (CRITICAL)

Every run that writes artifacts must leave an audit trail under the run directory:

1. **`run_metadata.json`** — command, inputs, parameters, tool versions, outputs.
2. **`logs/run_colorblind_sim.log`** (or `logs/convert_to_png.log`) — full script log.
3. **`logs/commands.log`** — append-only CLI record.
4. **`agent_request.txt`** — verbatim user prompt.
5. **`agent_workflow.md`** — agent inspection / conversion / CLI decisions.
6. Optional **`prepared/*.png`** — converted inputs.

Deposit runs under repository-local **`agentResults/colorblind-sim-<YYYYMMDDTHHMMSSZ>/`**.

## Workflow

1. Validate the figure path and format ([references/inputs-and-outputs.md](references/inputs-and-outputs.md)).
2. Ensure the persistent env (`bash scripts/ensure_env.sh` or rely on auto-bootstrap).
3. Create `agentResults/colorblind-sim-<runId>/`, write `agent_request.txt` and `agent_workflow.md`.
4. Run:

```bash
python scripts/run_colorblind_sim.py \
  --input /path/to/figure.png \
  --outputPrefix agentResults/colorblind-sim-<runId>/figure.cb \
  --mode fast \
  --runId <runId> \
  --outputDir agentResults/colorblind-sim-<runId> \
  --agentRequestFile agentResults/colorblind-sim-<runId>/agent_request.txt \
  --agentWorkflowFile agentResults/colorblind-sim-<runId>/agent_workflow.md
```

5. For PDF/SVG, the wrapper converts into `prepared/` automatically (SVG needs `rsvg-convert` or `inkscape` on PATH).
6. Verify exit code 0, deliverable PNG(s), `run_metadata.json`, and logs; scan logs for WARNING/ERROR.
7. Report run directory, key figures, mode/severity/types, and versions from `run_metadata.json`.

## Scripts

| Script | Role |
|--------|------|
| [scripts/ensure_env.sh](scripts/ensure_env.sh) | Create/reuse venv under `~/.cache/cursor-skills/colorblind-sim/` |
| [scripts/skill_env.py](scripts/skill_env.py) | Auto-bootstrap / re-exec with cached Python |
| [scripts/run_with_skill_env.sh](scripts/run_with_skill_env.sh) | Shell wrapper for any command in the env |
| [scripts/run_colorblind_sim.py](scripts/run_colorblind_sim.py) | Main CBviz wrapper + conversion + metadata |
| [scripts/convert_to_png.py](scripts/convert_to_png.py) | Standalone PDF/SVG/EPS/(raster) → PNG |
| [scripts/run_logging.py](scripts/run_logging.py) | Shared audit-trail helpers |

## Output Format

- Default (`--mode fast`): one multi-panel PNG (original + three CVD types).
- `--mode simulate --individualPlots`: `outfile.<cvd-type>.png` files.
- Always: `run_metadata.json` and `logs/` under `--outputDir`.

## Attribution

Report separately:

1. **Method** — CBviz + colorspacious ([references/citations.md](references/citations.md)).
2. **Skill package** — CAB-aiSkills `colorblind-sim` (AUTHORS.md / `metadata.author`).

Do not credit the skill author as the inventor of CBviz or colorspacious.

## Quality Checks

- Required inputs present; format supported or converted.
- `run_metadata.json` and `logs/<script>.log` exist.
- Deliverable image(s) exist and are non-empty.
- No unexpected WARNING/ERROR in the script log.
- SVG failures clearly cite missing `rsvg-convert` / `inkscape`.

## Failure and Escalation

- **`cbviz` / `cbviz-fast` not found** → `bash scripts/ensure_env.sh` (needs network on first create).
- **SVG/EPS conversion failed** → install `rsvg-convert` (librsvg) or Inkscape, or supply a PNG/PDF.
- **PDF page out of range** → fix `--page`.
- **Unsupported format** → convert externally or ask the user for PNG/PDF.

## Resources

- [references/inputs-and-outputs.md](references/inputs-and-outputs.md) — formats, run layout, metadata.
- [references/methods.md](references/methods.md) — CVD types and CBviz behavior.
- [references/citations.md](references/citations.md) — layered attribution.
- [examples/evaluation-prompts.md](examples/evaluation-prompts.md) — evaluation cases.
- [README.md](README.md) — maintainer setup and smoke tests.
