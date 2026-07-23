#!/usr/bin/env python3
"""Unit tests for report_common utilities."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from report_common import (  # noqa: E402
    classifyArtifact,
    countSignificantFeatures,
    discoverArtifacts,
    escapeHtml,
    linkRedundantArtifacts,
    profileTable,
    redactSampleIds,
    validateManifest,
)
from report_common import loadStructuredFile  # noqa: E402


def testEscapeHtml() -> None:
    """HTML special characters are escaped."""
    assert "&lt;tag&gt;" in escapeHtml("<tag>")


def testValidateGoodManifest() -> None:
    """Valid fixture manifest passes validation."""
    manifest = loadStructuredFile(FIXTURES / "differential_manifest.yaml")
    report = validateManifest(manifest, FIXTURES)
    assert report["valid"] is True
    assert report["readable_artifact_count"] >= 3


def testValidateBrokenManifest() -> None:
    """Missing artifact paths produce fatal validation errors."""
    manifest = loadStructuredFile(FIXTURES / "broken_manifest.yaml")
    report = validateManifest(manifest, FIXTURES)
    assert report["valid"] is False


def testDiscoveryClassifiesVolcano(tmp_path: Path) -> None:
    """Discovery assigns high-confidence volcano role from filename."""
    fig = tmp_path / "my_volcano_plot.png"
    fig.write_bytes(b"png")
    inventory = discoverArtifacts(tmp_path)
    roles = [item["role"] for item in inventory["artifacts"]]
    assert "volcano_plot" in roles


def testProfileLargeTable() -> None:
    """Large tables are profiled with partial-read warning."""
    profile = profileTable(FIXTURES / "large_table.tsv", maxRows=1000, previewRows=5)
    assert profile["readable"] is True
    assert profile["row_count"] == 1000
    assert len(profile["preview"]["rows"]) == 5
    assert any("profiling row cap" in item for item in profile["warnings"])


def testSignificantFeatureCounts() -> None:
    """Significant up/down counts respect supplied thresholds."""
    path = FIXTURES / "results" / "differential_peaks.tsv"
    profile = profileTable(path)
    summary = countSignificantFeatures(
        path,
        profile,
        {"fdr_threshold": 0.05, "absolute_log2_fold_change_threshold": 1.0},
    )
    assert summary is not None
    assert summary["significant_features"]["value"] == 4
    assert summary["upregulated_features"]["value"] == 2
    assert summary["downregulated_features"]["value"] == 2


def testRedactSampleIds() -> None:
    """Personal-looking sample IDs are redacted with warning."""
    redacted, warning = redactSampleIds(["patient_001", "patient_002"])
    assert redacted == ["sample_1", "sample_2"]
    assert warning is not None


def testClassifyTentativeCsv() -> None:
    """Unknown CSV files receive tentative supplementary role."""
    role, confidence = classifyArtifact(Path("mystery_folder/dataset.csv"))
    assert role in {"supplementary_table", "unknown"}
    assert confidence in {"tentative inference", "unknown"}


def testLinkRedundantOverlapTableToVenn() -> None:
    """Overlap tables are linked to Venn/UpSet figures instead of duplicated."""
    figures = [
        {
            "analysis_id": "overlap",
            "role": "venn_plot",
            "path": "figures/venn.png",
        }
    ]
    tables = [
        {
            "analysis_id": "overlap",
            "role": "overlap_results",
            "path": "results/overlap.tsv",
        },
        {
            "analysis_id": "overlap",
            "role": "primary_results",
            "path": "results/primary.tsv",
        },
    ]
    figures_out, tables_out, omitted = linkRedundantArtifacts(figures, tables)
    assert figures_out[0].get("linked_table", {}).get("path") == "results/overlap.tsv"
    assert len(tables_out) == 1
    assert tables_out[0]["path"] == "results/primary.tsv"
    assert omitted and omitted[0]["role"] == "overlap_results"
