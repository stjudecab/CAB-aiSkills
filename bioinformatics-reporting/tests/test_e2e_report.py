#!/usr/bin/env python3
"""CLI and end-to-end report generation tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
ENV = {**os.environ, "BIOINFORMATICS_REPORTING_SKIP_ENV_BOOTSTRAP": "1"}


def runScript(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a skill script and return the completed process."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=str(cwd or SCRIPTS.parent),
        capture_output=True,
        text=True,
        env=ENV,
        check=False,
    )


def testHelpScripts() -> None:
    """All CLI scripts expose --help."""
    for script in [
        "discover_artifacts.py",
        "validate_manifest.py",
        "profile_table.py",
        "profile_artifacts.py",
        "stage_artifacts.py",
        "build_report_model.py",
        "render_report.py",
        "verify_report.py",
    ]:
        completed = runScript(script, "--help")
        assert completed.returncode == 0, completed.stderr


def testEndToEndHtmlReport(tmp_path: Path) -> None:
    """Generate a real HTML report from the differential-analysis fixture."""
    outDir = tmp_path / "report"
    manifest = FIXTURES / "differential_manifest.yaml"
    modelPath = outDir / "report-model.json"

    build = runScript(
        "build_report_model.py",
        "--manifest",
        str(manifest),
        "--output",
        str(modelPath),
        "--baseDir",
        str(FIXTURES),
        "--outputDir",
        str(outDir),
    )
    assert build.returncode == 0, build.stderr + build.stdout

    render = runScript(
        "render_report.py",
        "--reportModel",
        str(modelPath),
        "--outputDir",
        str(outDir),
        "--baseDir",
        str(FIXTURES),
        "--formats",
        "html",
    )
    if shutil.which("quarto") is None:
        pytest.skip("Quarto CLI not installed")
    assert render.returncode == 0, render.stderr + render.stdout

    htmlPath = outDir / "bioinformatics-report.html"
    qmdPath = outDir / "bioinformatics-report.qmd"
    manifestPath = outDir / "report_manifest.yaml"
    verificationPath = outDir / "report_verification.json"
    assert qmdPath.is_file(), render.stderr + render.stdout
    assert htmlPath.is_file(), render.stderr + render.stdout
    assert manifestPath.is_file()
    assert verificationPath.is_file()

    html = htmlPath.read_text(encoding="utf-8")
    assert "<script>alert" not in html
    assert "Treated versus control" in html
    assert "{{" not in html

    verify = runScript(
        "verify_report.py",
        "--reportDir",
        str(outDir),
        "--outputDir",
        str(outDir),
    )
    assert verify.returncode == 0, verify.stderr + verify.stdout

    model = json.loads((outDir / "report-model.json").read_text(encoding="utf-8"))
    assert model["study"]["genome"] == "hg38"
    assert any(item.get("value") == 4 for item in model.get("metrics") or [])


def testHtmlSpecialCharactersEscaped(tmp_path: Path) -> None:
    """HTML-special metadata values are escaped in rendered HTML."""
    if shutil.which("quarto") is None:
        pytest.skip("Quarto CLI not installed")
    outDir = tmp_path / "html_report"
    completed = runScript(
        "render_report.py",
        "--manifest",
        str(FIXTURES / "html_special_manifest.yaml"),
        "--outputDir",
        str(outDir),
        "--baseDir",
        str(FIXTURES),
        "--formats",
        "html",
    )
    assert completed.returncode == 0, completed.stderr
    html = (outDir / "bioinformatics-report.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html


def testBrokenManifestRenderFails(tmp_path: Path) -> None:
    """Rendering from an invalid manifest exits non-zero."""
    outDir = tmp_path / "broken"
    completed = runScript(
        "render_report.py",
        "--manifest",
        str(FIXTURES / "broken_manifest.yaml"),
        "--outputDir",
        str(outDir),
        "--baseDir",
        str(FIXTURES),
    )
    assert completed.returncode == 2


def testDiscoveryExport(tmp_path: Path) -> None:
    """Discovery mode exports a reusable inventory file."""
    inventoryPath = tmp_path / "discovered.yaml"
    completed = runScript(
        "discover_artifacts.py",
        str(FIXTURES),
        "--output",
        str(inventoryPath),
        "--outputDir",
        str(tmp_path),
    )
    assert completed.returncode == 0, completed.stderr
    assert inventoryPath.is_file()


def testProfileArtifactsBatch(tmp_path: Path) -> None:
    """Batch profiling writes combined JSON for manifest tables."""
    outputPath = tmp_path / "profiles.json"
    completed = runScript(
        "profile_artifacts.py",
        "--manifest",
        str(FIXTURES / "differential_manifest.yaml"),
        "--baseDir",
        str(FIXTURES),
        "--output",
        str(outputPath),
        "--outputDir",
        str(tmp_path),
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(outputPath.read_text(encoding="utf-8"))
    assert payload["table_count"] >= 2


def testStageArtifactsFromManifest(tmp_path: Path) -> None:
    """Staging copies portable artifacts with checksum inventory."""
    stageDir = tmp_path / "staged"
    completed = runScript(
        "stage_artifacts.py",
        "--manifest",
        str(FIXTURES / "differential_manifest.yaml"),
        "--baseDir",
        str(FIXTURES),
        "--stageDir",
        str(stageDir),
        "--outputDir",
        str(tmp_path),
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert (stageDir / "figures" / "volcano.png").is_file()
    assert (stageDir / "tables" / "differential_peaks.tsv").is_file()
    assert (stageDir / "artifact_inventory.tsv").is_file()


@pytest.mark.skipif(shutil.which("quarto") is None or shutil.which("pdflatex") is None, reason="Quarto/pdflatex not installed")
def testPdfWhenLatexAvailable(tmp_path: Path) -> None:
    """Optional PDF rendering when Quarto and pdflatex are installed."""
    outDir = tmp_path / "pdf_report"
    completed = runScript(
        "render_report.py",
        "--manifest",
        str(FIXTURES / "differential_manifest.yaml"),
        "--outputDir",
        str(outDir),
        "--baseDir",
        str(FIXTURES),
        "--formats",
        "html,pdf",
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    pdf_path = outDir / "bioinformatics-report.pdf"
    if not pdf_path.is_file():
        pytest.skip("Quarto/pdflatex present but PDF was not produced (TeX packages may be incomplete).")
    assert pdf_path.is_file()
