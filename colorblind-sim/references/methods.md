# Methods — CVD simulation with CBviz

## Contents

- Background
- Deficiency types
- Severity
- CBviz modes used by this skill
- Limitations

## Background

Color vision deficiency (CVD) arises from altered or absent cone photoreceptor function. CBviz uses the **colorspacious** library to transform sRGB images into simulated CVD appearance and back to sRGB for display.

## Deficiency types

| Family | Cone | Typical CLI tokens |
|--------|------|--------------------|
| Protan | L (long / “red”) | `protan`, `protanopia`, … |
| Deuteran | M (medium / “green”) | `deuteran`, `deuteranopia`, … |
| Tritan | S (short / “blue”) | `tritan`, `tritanopia`, … |
| Mono | luminance only | `mono`, `monochrome`, … |

CBviz validates types by prefix (`protan*`, `deuteran*`, `tritan*`, `mono*`).

## Severity

`--severity` / `-s` is an integer **0–100** (0 = no deficiency, 100 = complete *opia). With `--all`, CBviz also shows anomalous panels at an alternate severity (50 when severity is 100, else 100).

## CBviz modes used by this skill

| Skill `--mode` | Upstream tool | Default panels |
|----------------|---------------|----------------|
| `fast` (default) | `cbviz-fast` | Original + protan + deuteran + tritan |
| `simulate` | `cbviz simulate` | Controlled by `--types` / `--all` |

Upstream `cbviz test` is **not** used: the author documents that the friendliness test does not work reliably.

## Limitations

- Simulation is a model of dichromatic/anomalous perception, not a clinical diagnosis.
- Rasterization of PDF/SVG can change fine line weights; use ≥300 DPI for publication figures.
- Alpha channels are dropped (RGB only), matching CBviz `load_image` behavior.
