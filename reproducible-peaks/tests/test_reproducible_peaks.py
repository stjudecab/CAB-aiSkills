"""Tests for reproducible-peaks CLI and helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from reproducible_peaks import (
    defaultMinEntries,
    detectPeakFormat,
    inferCallingStrategy,
    rankMethodForStrategy,
    replicateIdsFromNames,
    resolveChiprExecutable,
)

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "reproducible_peaks.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
REP1 = FIXTURES / "CTCF_rep1.subset.bed"
REP2 = FIXTURES / "CTCF_rep2.subset.bed"


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
    assert "inputFiles" in result.stdout


def test_default_min_entries() -> None:
    """Default -m follows n-1 for multiple replicates."""
    assert defaultMinEntries(1) == 1
    assert defaultMinEntries(2) == 1
    assert defaultMinEntries(4) == 3


def test_detect_narrowpeak_examples() -> None:
    """Bundled CTCF BED files are 10-column narrowPeak-like."""
    assert detectPeakFormat(REP1) == "narrowPeak"
    assert detectPeakFormat(REP2) == "narrowPeak"


def test_infer_with_control() -> None:
    """ENCFF CTCF names infer with-control strategy."""
    strategy = inferCallingStrategy([REP1, REP2], "narrowPeak")
    assert strategy == "withControl"


def test_infer_no_control_prefix() -> None:
    """noC_ prefix selects noControl strategy."""
    paths = [Path("noC_sample_rep1.narrowPeak"), Path("noC_sample_rep2.narrowPeak")]
    assert inferCallingStrategy(paths, "narrowPeak") == "noControl"


def test_rank_method_no_control() -> None:
    """noControl strategy uses signalvalue unless overridden."""
    assert rankMethodForStrategy("noControl", None) == "signalvalue"
    assert rankMethodForStrategy("withControl", None) == "pvalue"


def test_replicate_id_warning_pattern() -> None:
    """Replicate tokens are parsed from stems."""
    ids = replicateIdsFromNames(
        [Path("sample_rep1.narrowPeak"), Path("sample_rep2.narrowPeak")]
    )
    assert ids == ["1", "2"]


def test_dry_run_writes_metadata(tmp_path: Path) -> None:
    """Dry run validates inputs and writes run_metadata.json."""
    out = tmp_path / "dryrun"
    spec = f"{REP1},{REP2}"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--inputFiles",
            spec,
            "--outputDir",
            str(out),
            "--dryRun",
            "--overwrite",
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    meta = out / "run_metadata.json"
    assert meta.is_file()
    payload = json.loads(meta.read_text(encoding="utf-8"))
    assert payload["decisions"]["min_entries"] == 1
    assert payload["decisions"]["rank_method"] == "pvalue"
    assert "chipr_newell_2020_biorxiv" in payload["citation_keys"]
    assert "attribution" in payload


@pytest.mark.skipif(
    shutil.which("chipr") is None,
    reason="ChIP-R (chipr) not installed on PATH",
)
def test_chipr_integration_subset(tmp_path: Path) -> None:
    """Run ChIP-R on small fixture subsets when chipr is available."""
    out = tmp_path / "integration"
    spec = f"{REP1},{REP2}"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--inputFiles",
            spec,
            "--outputDir",
            str(out),
            "--outputPrefix",
            "ctcf_test",
            "--overwrite",
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    assert (out / "ctcf_test_optimal.bed").is_file()
    assert (out / "run_metadata.json").is_file()
    resolveChiprExecutable()
