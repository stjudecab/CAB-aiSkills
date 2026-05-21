"""Tests for SICER to broadPeak conversion."""

from __future__ import annotations

from pathlib import Path

from sicer_to_broadpeak import convertSicerToBroadpeak, parseSicerLine

SICER_LINE = (
    "chr1\t858800\t875799\t3413004_H3K27me3_dom_2_\t4254\t+\t"
    "0.0\t3.8057777584267543\t0.0\t1355"
)


def test_parse_sicer_line_maps_nine_columns() -> None:
    """SICER row maps to nine broadPeak fields."""
    fields = SICER_LINE.split("\t")
    broad = parseSicerLine(fields, 1, Path("test.sicer.bed"))
    assert len(broad) == 9
    assert abs(float(broad[6]) - 3.8057777584267543) < 1e-9
    assert broad[7] == "0"
    assert broad[8] == "0"


def test_convert_writes_rows(tmp_path: Path) -> None:
    """Converter writes one broadPeak row per SICER data line."""
    src = tmp_path / "in.sicer.bed"
    dst = tmp_path / "out.broadPeak"
    src.write_text(SICER_LINE + "\n", encoding="utf-8")
    count = convertSicerToBroadpeak(src, dst)
    assert count == 1
    out_line = dst.read_text(encoding="utf-8").strip()
    assert len(out_line.split("\t")) == 9
