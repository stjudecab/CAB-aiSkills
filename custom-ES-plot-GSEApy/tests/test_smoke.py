"""Smoke checks for custom-ES-plot-GSEApy scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "plotGseapyPrerankEnrichment.py"
WORKSPACE_GSEA_DIR = (
    Path(__file__).resolve().parents[4] / "48h.GseaPreranked.1781298215614"
)


def test_plot_gseapy_prerank_enrichment_help() -> None:
    """CLI prints help and exits zero."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "--inPKL" in proc.stdout
    assert "--inGseaDir" in proc.stdout
    assert "--geneSetName" in proc.stdout
    assert "--listOnly" in proc.stdout
    assert "--weight" in proc.stdout


def test_broad_gsea_list_only_smoke() -> None:
    """Broad GSEA directory resolves gene sets in list-only mode."""
    if not WORKSPACE_GSEA_DIR.is_dir():
        return

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--inGseaDir",
            str(WORKSPACE_GSEA_DIR),
            "--geneSetName",
            "REACTOME_HEME_SIGNALING",
            "--listOnly",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    combined = (proc.stdout + proc.stderr).replace("\n", "").replace(" ", "")
    assert "REACTOME_HEME_SIGNALING" in combined
