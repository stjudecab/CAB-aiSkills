"""Smoke checks for custom-ES-plot-GSEApy scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_plot_gseapy_prerank_enrichment_help() -> None:
    """CLI prints help and exits zero."""
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "plotGseapyPrerankEnrichment.py"
    )
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "--inPKL" in proc.stdout
    assert "--geneSetName" in proc.stdout
    assert "--listOnly" in proc.stdout
