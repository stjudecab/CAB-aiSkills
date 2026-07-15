#!/usr/bin/env python
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
# Author: Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: significance_colormap.py
# Description:
# Shared threshold-aware stepped colormaps for Enrichr heatmaps and dot plots.
#########################################################################

"""Threshold-aware stepped colormaps shared by enrichr_api heatmaps and pathway_dotplot.

Design (defaults: significanceThreshold=0.05, colorVmin=0, colorVmax=5,
firstSignificantEdge=1.5, colorStep=0.5):

* Values with -log10(sig) below -log10(threshold) map to neutral grey.
* The first significant color spans [threshold_nl, firstSignificantEdge).
* Subsequent bins use regular ``colorStep`` edges up to ``colorVmax``.

Both figures should call :func:`make_significance_colormap` so the color key matches.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

# Same grey used historically as the first stop of enrichr_api heatmaps.
GREY_RGB = (208 / 255.0, 206 / 255.0, 206 / 255.0)
# Soft grey for "missing" pathway cells on the dot plot (optional).
NONSIGNIFICANT_FACE_COLOR = "#9e9e9e"

# Historic 9 non-grey stops (Oranges / Reds / rocket_r) from enrichr_api.getCmaps().
ORANGES_SIGNAL: List[Tuple[float, float, float]] = [
    (0.9969242599000384, 0.914648212226067, 0.8323721645520954),
    (0.9937254901960785, 0.8501960784313726, 0.7043137254901961),
    (0.9921568627450981, 0.7644444444444445, 0.5524029219530949),
    (0.9921568627450981, 0.6564705882352941, 0.3827450980392157),
    (0.9914186851211073, 0.550726643598616, 0.23277201076509035),
    (0.9545098039215686, 0.44, 0.10666666666666666),
    (0.8871510957324106, 0.3320876585928489, 0.03104959630911188),
    (0.7709803921568628, 0.2541176470588235, 0.007058823529411764),
    (0.6179930795847751, 0.19907727797001154, 0.012610534409842366),
]

REDS_SIGNAL: List[Tuple[float, float, float]] = [
    (0.9969242599000384, 0.8961937716262975, 0.8489042675893886),
    (0.9913725490196079, 0.7913725490196079, 0.7082352941176471),
    (0.9882352941176471, 0.6715417147251057, 0.5605382545174933),
    (0.9874509803921568, 0.5411764705882353, 0.41568627450980394),
    (0.9835755478662053, 0.4127950788158401, 0.28835063437139563),
    (0.9466666666666667, 0.26823529411764707, 0.19607843137254902),
    (0.8503344867358708, 0.14686658977316416, 0.13633217993079583),
    (0.7364705882352941, 0.08, 0.10117647058823528),
    (0.5946174548250673, 0.04613610149942329, 0.07558631295655516),
]

ROCKET_SIGNAL: List[Tuple[float, float, float]] = [
    (0.96739773, 0.77451297, 0.65057302),
    (0.96298491, 0.6126247, 0.45145074),
    (0.95165009, 0.44224144, 0.30214494),
    (0.90848638, 0.24568473, 0.24598324),
    (0.79085854, 0.10184672, 0.313391),
    (0.63139686, 0.10067417, 0.35664819),
    (0.45809049, 0.12142996, 0.34540024),
    (0.29977678, 0.11356089, 0.29254823),
    (0.14633406, 0.07973393, 0.1986151),
]

_PALETTE_MAP = {
    "oranges": ORANGES_SIGNAL,
    "reds": REDS_SIGNAL,
    "rocket": ROCKET_SIGNAL,
}


def neg_log10_threshold(significance_threshold: float) -> float:
    """Return -log10(significance_threshold) with a floor for non-positive values."""
    t = float(significance_threshold)
    if not np.isfinite(t) or t <= 0:
        raise ValueError(
            "significance_threshold must be a positive finite value; got {!r}".format(t)
        )
    return float(-math.log10(t))


def build_color_boundaries(
    vmin: float = 0.0,
    vmax: float = 5.0,
    significance_threshold: float = 0.05,
    first_significant_edge: float = 1.5,
    color_step: float = 0.5,
) -> List[float]:
    """Build -log10 boundaries: grey up to threshold, then stepped colors.

    Args:
        vmin: Color scale minimum (typically 0).
        vmax: Color scale maximum (typically 5).
        significance_threshold: Raw p/FDR cutoff; values with -log10 below
            -log10(threshold) are grey.
        first_significant_edge: Preferred end of the first significant bin
            (default 1.5). Used only when it lies strictly above the grey end
            and below vmax.
        color_step: Regular bin width after the first significant edge.

    Returns:
        Strictly increasing list of boundary edges for :class:`BoundaryNorm`.
    """
    vmin = float(vmin)
    vmax = float(vmax)
    color_step = float(color_step)
    first_significant_edge = float(first_significant_edge)
    if vmax <= vmin:
        raise ValueError("colorVmax must be greater than colorVmin")
    if color_step <= 0:
        raise ValueError("colorStep must be positive")

    grey_end = neg_log10_threshold(significance_threshold)
    # Clamp grey end into (vmin, vmax]; if threshold is so strict that
    # -log10(thresh) >= vmax, the whole scale is grey (single bin).
    if grey_end <= vmin:
        # Threshold weaker than vmin display floor — no grey bin.
        boundaries = [vmin]
        cursor = vmin
        if first_significant_edge > vmin and first_significant_edge < vmax:
            boundaries.append(first_significant_edge)
            cursor = first_significant_edge
        while cursor + color_step < vmax - 1e-12:
            cursor += color_step
            boundaries.append(cursor)
        if boundaries[-1] < vmax - 1e-12:
            boundaries.append(vmax)
        return boundaries

    if grey_end >= vmax:
        return [vmin, vmax]

    boundaries = [vmin, grey_end]
    cursor = grey_end

    if grey_end < first_significant_edge < vmax:
        boundaries.append(first_significant_edge)
        cursor = first_significant_edge
    else:
        # Align next edge to the next multiple of color_step above grey_end.
        next_edge = math.ceil(grey_end / color_step) * color_step
        if next_edge <= grey_end + 1e-12:
            next_edge = grey_end + color_step
        if next_edge < vmax - 1e-12:
            boundaries.append(next_edge)
            cursor = next_edge

    while cursor + color_step < vmax - 1e-12:
        cursor += color_step
        boundaries.append(cursor)
    if boundaries[-1] < vmax - 1e-12:
        boundaries.append(vmax)
    return boundaries


def _pick_signal_colors(
    palette: Sequence[Tuple[float, float, float]], n: int
) -> List[Tuple[float, float, float]]:
    """Select ``n`` colors from a finite palette (even spacing if n < len)."""
    if n <= 0:
        return []
    palette = list(palette)
    if n == 1:
        return [palette[0]]
    if n >= len(palette):
        # Prefer keeping the full historic set; pad by repeating the darkest.
        out = list(palette)
        while len(out) < n:
            out.append(palette[-1])
        return out
    idx = np.linspace(0, len(palette) - 1, n)
    return [palette[int(round(i))] for i in idx]


def make_significance_colormap(
    palette: str = "oranges",
    vmin: float = 0.0,
    vmax: float = 5.0,
    significance_threshold: float = 0.05,
    first_significant_edge: float = 1.5,
    color_step: float = 0.5,
) -> Tuple[ListedColormap, BoundaryNorm, List[float]]:
    """Build a ListedColormap + BoundaryNorm for -log10 significance values.

    Args:
        palette: ``oranges`` (p-value), ``reds`` (FDR), or ``rocket``.
        vmin / vmax / significance_threshold / first_significant_edge / color_step:
            See :func:`build_color_boundaries`.

    Returns:
        (cmap, norm, boundaries)
    """
    key = str(palette).lower().strip()
    if key not in _PALETTE_MAP:
        raise ValueError(
            "Unknown palette {!r}; expected one of {}".format(
                palette, sorted(_PALETTE_MAP)
            )
        )
    boundaries = build_color_boundaries(
        vmin=vmin,
        vmax=vmax,
        significance_threshold=significance_threshold,
        first_significant_edge=first_significant_edge,
        color_step=color_step,
    )
    n_bins = len(boundaries) - 1
    n_signal = max(0, n_bins - 1)
    colors: List[Tuple[float, float, float]] = [GREY_RGB]
    colors.extend(_pick_signal_colors(_PALETTE_MAP[key], n_signal))
    if len(colors) != n_bins:
        raise RuntimeError(
            "Internal error: {} colors for {} bins".format(len(colors), n_bins)
        )
    cmap = ListedColormap(colors, name="sig_{}_{}".format(key, n_bins))
    # BoundaryNorm maps value in [b_i, b_{i+1}) to color i; last boundary inclusive.
    norm = BoundaryNorm(boundaries, ncolors=cmap.N, clip=True)
    return cmap, norm, boundaries


def colorbar_label_for_column(significance_column: str) -> str:
    """Return the colorbar label for a pathway_dotplot significance column name."""
    if significance_column == "adjustedPvalue":
        return "-log10(FDR)"
    if significance_column == "pvalue":
        return "-log10(p-value)"
    return "-log10({})".format(significance_column)


def palette_for_column(significance_column: str) -> str:
    """Choose oranges (P) vs reds (FDR) to match historic enrichr_api heatmaps."""
    if significance_column == "adjustedPvalue":
        return "reds"
    return "oranges"


def format_boundary_tick(value: float, decimals: int = 1) -> str:
    """Format a color-scale boundary tick (default one decimal place, e.g. 1.3)."""
    return "{:.{prec}f}".format(float(value), prec=int(decimals))


def apply_boundary_colorbar_ticks(
    cbar,
    boundaries: Sequence[float],
    decimals: int = 1,
) -> None:
    """Set colorbar ticks to the BoundaryNorm edges with fixed decimal formatting.

    Args:
        cbar: Matplotlib colorbar instance.
        boundaries: -log10 edges from :func:`make_significance_colormap`.
        decimals: Number of decimal places on tick labels (default 1 → ``1.3``).
    """
    ticks = [float(b) for b in boundaries]
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([format_boundary_tick(b, decimals=decimals) for b in ticks])
