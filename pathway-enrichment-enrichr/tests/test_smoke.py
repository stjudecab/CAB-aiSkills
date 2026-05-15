"""Smoke checks for pathway-enrichment-enrichr scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_pathway_enrichment_help() -> None:
    """CLI prints help and exits zero."""
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_pathway_enrichment.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "run_pathway_enrichment.py" in proc.stdout or "--mode" in proc.stdout
