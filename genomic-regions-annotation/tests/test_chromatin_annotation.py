"""Unit tests for chromatin-state preprocess helpers and offline annotation smoke."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

os.environ["GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP"] = "1"

from chromatin_model_utils import (  # noqa: E402
    convertSegwayBed,
    convertSegwayBedLine,
    mergeAdjacentSameState,
    rewriteRoadmapDenseBed,
    stripRoadmapStateColumn,
)


def test_example_chromatin_bed_resources_exist() -> None:
    """Bundled K562 CTCF/POLR2A example BEDs must ship with the skill."""
    chromatinDir = SKILL_ROOT / "example_input" / "chromatin"
    ctcf = chromatinDir / "CTCF_K562_ENCFF396BZQ.bed"
    polr2a = chromatinDir / "POLR2A_K562_ENCFF285MBX.bed"
    lst = chromatinDir / "exampleInput.lst"
    assert ctcf.is_file() and ctcf.stat().st_size > 0
    assert polr2a.is_file() and polr2a.stat().st_size > 0
    assert lst.is_file()
    listed = [
        line.strip()
        for line in lst.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert listed == [
        "example_input/chromatin/CTCF_K562_ENCFF396BZQ.bed",
        "example_input/chromatin/POLR2A_K562_ENCFF285MBX.bed",
    ]
    for rel in listed:
        assert (SKILL_ROOT / rel).is_file()


def test_aggregation_output_directory_layout() -> None:
    from chromatin_model_utils import aggregationOutputDirectory

    assert aggregationOutputDirectory("/tmp/out", "regions") == "/tmp/out"
    assert aggregationOutputDirectory("/tmp/out", "bp") == "/tmp/out/aggregationByBp"


def test_strip_roadmap_state_column() -> None:
    assert stripRoadmapStateColumn("9_Het") == "9"
    assert stripRoadmapStateColumn("15_Quies") == "15"
    assert stripRoadmapStateColumn("7") == "7"


def test_rewrite_roadmap_dense_bed(tmp_path: Path) -> None:
    out = tmp_path / "rewritten.bed"
    n = rewriteRoadmapDenseBed(FIX / "roadmap_raw_snippet.bed", out)
    assert n == 3
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("track")
    assert lines[1].split("\t")[3] == "9"
    assert lines[2].split("\t")[3] == "15"


def test_convert_segway_line_and_merge() -> None:
    fields = "chr1\t1000\t2000\t6_Quiescent\t1000\t.\t1000\t2000\t192,192,192".split("\t")
    converted = convertSegwayBedLine(fields)
    assert converted is not None
    assert converted[3] == "1"
    merged = mergeAdjacentSameState(
        [
            "chr1\t1000\t2000\t1\t0\t.\t1000\t2000\t192,192,192",
            "chr1\t2000\t3000\t1\t0\t.\t2000\t3000\t192,192,192",
            "chr1\t3000\t4000\t5\t0\t.\t3000\t4000\t255,0,0",
        ]
    )
    assert len(merged) == 2
    assert merged[0].split("\t")[2] == "3000"


def test_convert_segway_bed_file(tmp_path: Path) -> None:
    out = tmp_path / "segway_dense.bed"
    n = convertSegwayBed(
        FIX / "segway_raw_snippet.bed",
        out,
        trackName="test",
        trackDescription="test desc",
    )
    assert n == 3
    assert out.read_text(encoding="utf-8").splitlines()[0].startswith("track")


def test_bed_in_context_help() -> None:
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "BEDinContext.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP": "1"},
    )
    assert proc.returncode == 0
    assert "statesFile" in proc.stdout


def test_prepare_help() -> None:
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "prepare_chromatin_model.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP": "1"},
    )
    assert proc.returncode == 0
    assert "--collection" in proc.stdout


@pytest.mark.skipif(
    os.environ.get("GENOMIC_REGIONS_ANNOTATION_RUN_BEDTOOLS") != "1",
    reason="Set GENOMIC_REGIONS_ANNOTATION_RUN_BEDTOOLS=1 when bedtools/pybedtools are available.",
)
def test_bed_in_context_toy_smoke(tmp_path: Path) -> None:
    import subprocess

    lst = tmp_path / "peaks.lst"
    lst.write_text(str(FIX / "toy_peaks.bed") + "\n", encoding="utf-8")
    runDir = tmp_path / "run"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "BEDinContext.py"),
            "-r",
            str(lst),
            "-s",
            str(FIX / "toy_dense.bed"),
            "-o",
            "BEDinContext",
            "--state2name",
            str(FIX / "toy_state2name.tsv"),
            "--outputDir",
            str(runDir),
            "--runId",
            "20260713T000000Z",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP": "1"},
        cwd=str(SKILL_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert (runDir / "BEDinContext" / "statsCombined.num.tsv").is_file()
    assert (runDir / "run_metadata.json").is_file()
