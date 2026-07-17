#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `colorblind-sim` skill.
"""Tests for run_colorblind_sim CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("COLORBLIND_SIM_SKIP_ENV_BOOTSTRAP", "1")

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(SCRIPTS))

from run_colorblind_sim import buildCbvizCommand, buildParser  # noqa: E402


def testBuildParserDefaults() -> None:
    """Default mode is fast with severity 100."""
    parser = buildParser()
    args = parser.parse_args(
        ["--input", "a.png", "--outputPrefix", "out/fig"]
    )
    assert args.mode == "fast"
    assert args.severity == 100
    assert args.types == "protan,deuteran,tritan"


def testBuildCbvizFastCommand() -> None:
    """fast mode invokes cbviz-fast when available."""
    if not shutil.which("cbviz-fast"):
        pytest.skip("cbviz-fast not on PATH")
    cmd = buildCbvizCommand(
        mode="fast",
        infile=Path("in.png"),
        outfile=Path("out.png"),
        severity=100,
        types="protan,deuteran,tritan",
        runAll=False,
        individualPlots=False,
        noOriginal=False,
    )
    assert cmd[0].endswith("cbviz-fast") or "cbviz-fast" in cmd[0]
    assert cmd[-2:] == ["in.png", "out.png"]


def testHelpExitsZero() -> None:
    """--help must succeed without bootstrapping env creation."""
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_colorblind_sim.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "COLORBLIND_SIM_SKIP_ENV_BOOTSTRAP": "1"},
    )
    assert completed.returncode == 0
    assert "CBviz" in completed.stdout or "color" in completed.stdout.lower()


def testSmokeFastMode(tmp_path: Path) -> None:
    """End-to-end fast-mode simulation on the bundled demo PNG."""
    if not shutil.which("cbviz-fast"):
        pytest.skip("cbviz-fast not on PATH; run bash scripts/ensure_env.sh first")
    outDir = tmp_path / "run"
    outDir.mkdir()
    prefix = outDir / "demo.cb"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "run_colorblind_sim.py"),
            "--input",
            str(EXAMPLES / "demo.png"),
            "--outputPrefix",
            str(prefix),
            "--outputDir",
            str(outDir),
            "--mode",
            "fast",
            "--runId",
            "TEST20260101T000000Z",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "COLORBLIND_SIM_SKIP_ENV_BOOTSTRAP": "1"},
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert (outDir / "run_metadata.json").is_file()
    assert (outDir / "logs" / "run_colorblind_sim.log").is_file()
    # Prefixes without a known image suffix become ``<prefix>.png`` (e.g. demo.cb.png).
    outfile = Path(str(prefix) + ".png")
    assert outfile.is_file()
    assert outfile.stat().st_size > 0
