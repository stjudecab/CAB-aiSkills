"""Unit tests for threshold-aware stepped colormaps."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from significance_colormap import (  # noqa: E402
    build_color_boundaries,
    make_significance_colormap,
    neg_log10_threshold,
)


def test_default_boundaries() -> None:
    b = build_color_boundaries()
    assert b[0] == 0.0
    assert abs(b[1] - (-math.log10(0.05))) < 1e-12
    assert b[2] == 1.5
    assert b[-1] == 5.0
    # regular 0.5 steps after 1.5
    assert b[3:] == [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]


def test_threshold_maps_to_first_significant_bin() -> None:
    cmap, norm, _ = make_significance_colormap("oranges")
    thr = neg_log10_threshold(0.05)
    assert int(norm(np.array([thr - 1e-12]))[0]) == 0
    assert int(norm(np.array([thr]))[0]) == 1
    assert int(norm(np.array([1.4]))[0]) == 1
    assert int(norm(np.array([1.5]))[0]) == 2
    assert cmap.N == 9


def test_colorbar_tick_one_decimal() -> None:
    from significance_colormap import format_boundary_tick

    assert format_boundary_tick(1.3010299956639813) == "1.3"
    assert format_boundary_tick(0.0) == "0.0"
    assert format_boundary_tick(5.0) == "5.0"


def test_custom_threshold() -> None:
    b = build_color_boundaries(significance_threshold=0.01, first_significant_edge=1.5)
    # -log10(0.01)=2.0, so first_significant_edge 1.5 is skipped
    assert abs(b[1] - 2.0) < 1e-12
    assert b[2] == 2.5
