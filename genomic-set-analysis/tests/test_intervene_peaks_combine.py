"""Tests for the genomic-set-analysis core overlap script.

These tests exercise the parts that do not require the external Intervene / BEDTools
binaries: input resolution, gene-set (GMT) mode with plotting disabled, the counted-sets
helper, and the reproducibility metadata. Region (BED) mode is covered only when
``pybedtools`` and ``intervene`` are importable/available.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import intervene_peaks_combine as core  # noqa: E402


def test_help_runs():
    """The CLI ``--help`` exits successfully without heavy optional dependencies."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "intervene_peaks_combine.py"), "--help"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    assert result.returncode == 0
    assert b"Intervene" in result.stdout


def test_resolve_inputs_rejects_single_bed(tmp_path):
    """A single BED file is rejected with an actionable error."""
    bed = tmp_path / "only.bed"
    bed.write_text("chr1\t1\t2\n")
    with pytest.raises(ValueError):
        core.resolveInputs(str(bed), "auto")


def test_resolve_inputs_gmt_mode(tmp_path):
    """A single GMT file is parsed into gene-set mode with per-set gene lists."""
    gmt = tmp_path / "sets.gmt"
    gmt.write_text("SetA\tdesc\tG1\tG2\nSetB\tdesc\tG2\tG3\n")
    inputList, gmtMode, gmtContent, labels, originalLabels = core.resolveInputs(str(gmt), "auto")
    assert gmtMode is True
    assert labels == ["SetA", "SetB"]
    assert originalLabels == ["SetA", "SetB"]
    assert gmtContent["SetA"] == ["G1", "G2"]


def test_resolve_inputs_gmt_short_names(tmp_path):
    """GMT mode accepts short analysis labels via -n while preserving originals."""
    gmt = tmp_path / "sets.gmt"
    gmt.write_text(
        "VeryLongConditionA_name\tdesc\tG1\tG2\nVeryLongConditionB_name\tdesc\tG2\tG3\n"
    )
    inputList, gmtMode, gmtContent, labels, originalLabels = core.resolveInputs(
        str(gmt), "CondA,CondB"
    )
    assert labels == ["CondA", "CondB"]
    assert originalLabels == ["VeryLongConditionA_name", "VeryLongConditionB_name"]
    assert gmtContent["CondA"] == ["G1", "G2"]


def test_labels_are_short_enough():
    """labelsAreShortEnough enforces length and uniqueness."""
    assert core.labelsAreShortEnough(["A", "BB", "CCC"])
    assert not core.labelsAreShortEnough(["A", "A"])
    assert not core.labelsAreShortEnough(["this_label_is_too_long"])


def test_write_set_labels_manifest(tmp_path):
    """writeSetLabelsManifest records original and analysis labels."""
    outDir = tmp_path / "demo.intervene"
    outDir.mkdir()
    manifest = core.writeSetLabelsManifest(
        interveneDir=outDir,
        mode="genomic",
        inputSource="a.bed,b.bed",
        inputList=["/data/a.bed", "/data/b.bed"],
        originalLabels=["LongNameA", "LongNameB"],
        analysisLabels=["A", "B"],
    )
    text = manifest.read_text()
    assert "original_label" in text
    assert "LongNameA" in text
    assert "\tA\t" in text or "\tA\n" in text


def test_gene_set_mode_end_to_end(tmp_path):
    """GMT mode with plotting disabled writes the matrix, GMTs, and metadata."""
    gmt = tmp_path / "in.gmt"
    gmt.write_text("SetA\td\tG1\tG2\tG3\nSetB\td\tG2\tG3\tG4\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "intervene_peaks_combine.py"),
         "-i", str(gmt), "-o", "demo", "--outputDir", str(tmp_path),
         "--toPlot", "ignore", "--overwrite"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    assert result.returncode == 0, result.stdout.decode()
    outDir = tmp_path / "demo.intervene"
    assert (outDir / "demo.matrix.tsv").is_file()
    assert (outDir / "originalSets.gmt").is_file()
    assert (outDir / "setLabelsManifest.tsv").is_file()
    metadata = json.loads((outDir / "run_metadata.json").read_text())
    assert metadata["mode"] == "geneSet"
    assert metadata["tool_versions"]["python"].startswith("3")
    assert "intervene" in metadata["citation_keys"]


def test_build_sets_counted(tmp_path):
    """buildSetsCounted prefixes each file with a zero-padded region/gene count."""
    setsDir = tmp_path / "sets"
    setsDir.mkdir()
    (setsDir / "a.txt").write_text("g1\ng2\ng3\n")
    countedDir = tmp_path / "setsCounted"
    created = core.buildSetsCounted(setsDir, countedDir)
    assert created == 1
    names = [p.name for p in countedDir.iterdir()]
    assert names == ["000000003__a.txt"]


def test_overwrite_guard(tmp_path):
    """Re-running without --overwrite fails when the output directory exists."""
    gmt = tmp_path / "in.gmt"
    gmt.write_text("SetA\td\tG1\tG2\nSetB\td\tG2\tG3\n")
    common = [sys.executable, str(SCRIPTS / "intervene_peaks_combine.py"),
              "-i", str(gmt), "-o", "demo", "--outputDir", str(tmp_path), "--toPlot", "ignore"]
    first = subprocess.run(common + ["--overwrite"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert first.returncode == 0
    second = subprocess.run(common, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert second.returncode != 0
    assert b"already exists" in second.stdout
