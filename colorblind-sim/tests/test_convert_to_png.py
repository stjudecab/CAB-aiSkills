#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `colorblind-sim` skill.
"""Tests for convert_to_png helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("COLORBLIND_SIM_SKIP_ENV_BOOTSTRAP", "1")

from convert_to_png import (  # noqa: E402
    convertToPng,
    detectFormat,
    findSvgConverter,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def testDetectFormatFromSuffix() -> None:
    """Detect format labels from file suffixes."""
    assert detectFormat(Path("a.PNG"), "") == "png"
    assert detectFormat(Path("a.pdf"), "") == "pdf"
    assert detectFormat(Path("a.fig"), "svg") == "svg"


def testConvertPngCopy(tmp_path: Path) -> None:
    """Copy PNG without re-encoding when force is false."""
    src = EXAMPLES / "demo.png"
    assert src.is_file()
    dest = tmp_path / "out.png"
    summary = convertToPng(src, dest, formatName="png", page=1, dpi=72, force=False)
    assert summary["method"] == "copy"
    assert dest.is_file()
    assert dest.stat().st_size > 0


def testConvertRasterForce(tmp_path: Path) -> None:
    """Force Pillow re-encode of a PNG."""
    src = EXAMPLES / "demo.png"
    dest = tmp_path / "forced.png"
    summary = convertToPng(src, dest, formatName="png", page=1, dpi=72, force=True)
    assert summary["method"] == "pillow"
    assert dest.is_file()


def testConvertPdfToPng(tmp_path: Path) -> None:
    """Rasterize a one-page PDF created from the demo PNG."""
    pytest.importorskip("fitz")
    from PIL import Image

    pdfPath = tmp_path / "demo.pdf"
    png = Image.open(EXAMPLES / "demo.png").convert("RGB")
    png.save(pdfPath, "PDF")
    out = tmp_path / "from_pdf.png"
    summary = convertToPng(pdfPath, out, formatName="pdf", page=1, dpi=72, force=False)
    assert summary["method"] == "pymupdf"
    assert out.is_file()
    assert out.stat().st_size > 0


def testUnsupportedFormatRaises(tmp_path: Path) -> None:
    """Reject proprietary formats with a clear error."""
    bad = tmp_path / "x.psd"
    bad.write_bytes(b"not-a-real-psd")
    with pytest.raises(ValueError, match="Unsupported"):
        convertToPng(bad, tmp_path / "y.png", formatName="psd", page=1, dpi=72, force=False)


def testSvgConverterDiscoveryIsOptional() -> None:
    """SVG host tools may or may not be present; discovery must not crash."""
    found = findSvgConverter()
    assert found is None or found[0] in {"rsvg-convert", "inkscape"}
