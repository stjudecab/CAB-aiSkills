"""Smoke tests for volcano-grid-plot skill."""

from __future__ import annotations

import json
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
    assert "agentRequest" in result.stdout


def test_volcano_grid_smoke(tmp_path: Path) -> None:
    """Minimal volcano-only run on bundled examples."""
    run_dir = tmp_path / "volcano-grid-plot-test"
    run_dir.mkdir()
    prefix = run_dir / "smoke"
    agent_request = run_dir / "agent_request.txt"
    agent_request.write_text("Smoke test user request.\n", encoding="utf-8")
    agent_workflow = run_dir / "agent_workflow.md"
    agent_workflow.write_text("# Workflow\n\nDetected log2FC, FDR, geneSymbol.\n", encoding="utf-8")

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
            "--runId",
            "20990101T000000Z",
            "--agentRequestFile",
            str(agent_request),
            "--agentWorkflowFile",
            str(agent_workflow),
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert (run_dir / "smoke.volcanoGrid.png").is_file()
    assert (run_dir / "smoke.volcanoGrid.pdf").is_file()
    assert (run_dir / "logs" / "volcano_ma_grid.log").is_file()
    assert (run_dir / "logs" / "commands.log").is_file()
    assert (run_dir / "agent_request.txt").is_file()
    assert (run_dir / "agent_workflow.md").is_file()

    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["run_id"] == "20990101T000000Z"
    assert metadata["skill"] == "volcano-grid-plot"
    assert metadata["tool_versions"]["python"].startswith("3")
    assert metadata["agent_request_file"].endswith("agent_request.txt")
    assert metadata["summary"]["n_panels"] == 2
    assert len(metadata["outputs"]) >= 2
