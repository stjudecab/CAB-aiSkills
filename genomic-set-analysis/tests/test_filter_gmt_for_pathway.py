"""Tests for filter_gmt_for_pathway.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import filter_gmt_for_pathway as filterGmt  # noqa: E402


def test_select_sets_for_pathway_top_ten_and_min_genes():
    """Default policy keeps top 10 eligible sets with at least five genes."""
    geneSets = filterGmt.OrderedDict(
        (f"Set{i}", [f"G{j}" for j in range(i)]) for i in range(1, 16)
    )
    filtered, manifestRows = filterGmt.selectSetsForPathway(geneSets, minGenes=5, topN=10)
    assert len(filtered) == 10
    assert "Set15" in filtered
    assert "Set4" not in filtered
    excluded = [row for row in manifestRows if row["included"] == "false"]
    assert any(row["reason"] == "below_minGenes_5" for row in excluded)
    assert any(row["reason"] == "outside_top_10" for row in excluded)


def test_select_sets_for_pathway_originals_no_top_cap():
    """Original sets use minGenes only when topN is zero."""
    geneSets = filterGmt.OrderedDict(
        {
            "Small": ["G1", "G2"],
            "Medium": ["G1", "G2", "G3", "G4", "G5"],
            "Large": [f"G{i}" for i in range(12)],
        }
    )
    filtered, _ = filterGmt.selectSetsForPathway(geneSets, minGenes=5, topN=0)
    assert set(filtered.keys()) == {"Medium", "Large"}


def test_filter_script_cli(tmp_path):
    """CLI writes filtered GMT and manifest."""
    gmt = tmp_path / "in.gmt"
    gmt.write_text(
        "\n".join(
            f"Set{i}\tdesc\t" + "\t".join(f"G{j}" for j in range(i))
            for i in range(1, 8)
        )
        + "\n"
    )
    outGmt = tmp_path / "filtered.gmt"
    manifest = tmp_path / "manifest.tsv"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "filter_gmt_for_pathway.py"),
            "--gmt",
            str(gmt),
            "--output",
            str(outGmt),
            "--manifest",
            str(manifest),
            "--minGenes",
            "5",
            "--topN",
            "2",
            "--overwrite",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert result.returncode == 0, result.stdout.decode()
    assert outGmt.is_file()
    assert manifest.is_file()
    assert outGmt.read_text().count("\n") == 2


def test_filter_script_rejects_empty_result(tmp_path):
    """Filtering that removes every set exits with an error."""
    gmt = tmp_path / "tiny.gmt"
    gmt.write_text("A\tdesc\tG1\nB\tdesc\tG2\n")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "filter_gmt_for_pathway.py"),
            "--gmt",
            str(gmt),
            "--output",
            str(tmp_path / "out.gmt"),
            "--minGenes",
            "5",
            "--topN",
            "10",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert result.returncode != 0
