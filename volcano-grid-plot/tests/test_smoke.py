"""Smoke tests for volcano-grid-plot skill."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "volcano_ma_grid.py"
MANIFEST = SKILL_ROOT / "examples" / "gse202762_1hr_2hr_titles_EGR1_manifest.tsv"


def test_help_exits_zero() -> None:
    """CLI --help should succeed."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "plotsToPlot" in result.stdout


def test_volcano_grid_smoke(tmp_path: Path) -> None:
    """Minimal volcano-only run on bundled examples."""
    prefix = tmp_path / "smoke"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(MANIFEST),
            str(prefix),
            "--plotsToPlot",
            "volcano",
            "--fcCol",
            "log2FC",
            "--sigCol",
            "FDR",
            "--nameCol",
            "geneSymbol",
            "--cols",
            "2",
            "--rows",
            "1",
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "smoke.volcanoGrid.png").is_file()
    assert (tmp_path / "smoke.volcanoGrid.pdf").is_file()
