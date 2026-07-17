# Citations and layered attribution

## Contents

- Layer 1 — skill package
- Layer 2 — bundled scripts
- Layer 3 — methods and external tools
- Copy-paste methods text

Follow the repository three-layer policy: [../../docs/attribution.md](../../docs/attribution.md).

## Layer 1 — skill package

CAB-aiSkills `colorblind-sim` skill — credit the **skill author(s)** in
[../../AUTHORS.md](../../AUTHORS.md) and `metadata.author` in [SKILL.md](../SKILL.md).
This credits workflow orchestration and packaging only, **not** the underlying methods.

## Layer 2 — bundled scripts

- `scripts/run_colorblind_sim.py`, `scripts/convert_to_png.py`, `scripts/run_logging.py`,
  `scripts/skill_env.py` — Copyright Wojciech Rosikiewicz && St Jude (see file headers).

## Layer 3 — methods and external tools

| Tool | Citation | Key |
|------|----------|-----|
| **CBviz** | Flynn W. *CBviz*: simple simulator for colorblindness. GitHub repository. [https://github.com/wflynny/cbviz](https://github.com/wflynny/cbviz) | `cbviz` |
| **colorspacious** | Smith NJ et al. *colorspacious*: a powerful, accurate, and easy-to-use Python library for colorspace conversions. [https://colorspacious.readthedocs.io/](https://colorspacious.readthedocs.io/) | `colorspacious` |

## Copy-paste methods text

> Figure appearance under color vision deficiency was simulated with **CBviz**
> (Flynn; https://github.com/wflynny/cbviz) using **colorspacious** transforms, via the
> CAB-aiSkills `colorblind-sim` skill (skill author(s) per AUTHORS.md; repository URL).
> Exact commands, severity, CVD types, and tool versions are recorded in `run_metadata.json`.

Do not cite the skill author(s) as inventors of CBviz or colorspacious.
