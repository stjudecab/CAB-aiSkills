#!/usr/bin/env python
"""Dot plot for pathway enrichment tables aligned across samples."""

from __future__ import annotations

import argparse
import inspect
import json
import logging
import os
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import cm
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
import seaborn as sns

try:
    from rich.logging import RichHandler
except ImportError:
    RichHandler = None  # type: ignore

# Axes (data) panel fill; white ring in GSEApy-style dots stays visible against this grey.
RING_PANEL_FACE_COLOR = "#F2F3F5"
# Matplotlib figure canvas behind axes (margins, colorbar area outside axes patch stay white).
FIGURE_CANVAS_FACE_COLOR = "white"
# Nonsignificant (p > threshold) and missing-pathway cells when enabled; same fill for both.
NONSIGNIFICANT_FACE_COLOR = "#9e9e9e"


def configureLogging(
    analysisPrefix: str = Path(__file__).stem,
    logLevel: str = "INFO",
) -> None:
    """Configure root logging with Rich console and plain file handlers.

    Args:
        analysisPrefix (str): Base name for the log file (without directory).
        logLevel (str): Logging level name.
    """
    logger = logging.getLogger()
    logger.disabled = False
    logger.handlers = []
    logger.setLevel(getattr(logging, str(logLevel).upper(), logging.INFO))

    if RichHandler is not None:
        streamhdlr = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_level=True,
            show_path=True,
        )
    else:
        streamhdlr = logging.StreamHandler(sys.stderr)
    filehdlr = logging.FileHandler(f"{analysisPrefix}.log")

    logger.addHandler(streamhdlr)
    logger.addHandler(filehdlr)

    streamhdlr.setLevel(getattr(logging, str(logLevel).upper(), logging.INFO))
    filehdlr.setLevel(getattr(logging, str(logLevel).upper(), logging.INFO))

    lgr_plain_format = logging.Formatter(
        "###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s"
    )
    filehdlr.setFormatter(lgr_plain_format)


def str2bool(value: Union[str, bool]) -> bool:
    """Parse a string or bool into a boolean."""
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("yes", "true", "t", "y", "1"):
        return True
    if str(value).lower() in ("no", "false", "f", "n", "0"):
        return False
    lgr.critical(
        "Unrecognized parameter was set for boolean argument: %r. Aborting.", value
    )
    sys.exit(1)


def convertRgbToUnit(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """Convert 0-255 RGB to 0-1 floats for matplotlib."""
    return (r / 255.0, g / 255.0, b / 255.0)


def getHeatmapStyleColormaps() -> Tuple[ListedColormap, ListedColormap, ListedColormap]:
    """Build the same grey-anchored palettes used in enrichr_api heatmaps.

    Returns:
        Tuple of ListedColormap: (rocket_r style, Oranges for -log10 P, Reds for -log10 FDR).
    """
    grey = convertRgbToUnit(208, 206, 206)
    cmap_grey_rocket_r = sns.color_palette(
        [
            grey,
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
    )
    cmap_grey_oranges = sns.color_palette(
        [
            grey,
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
    )
    cmap_grey_reds = sns.color_palette(
        [
            grey,
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
    )
    return (
        ListedColormap(cmap_grey_rocket_r),
        ListedColormap(cmap_grey_oranges),
        ListedColormap(cmap_grey_reds),
    )


def negLog10Safe(value: float, floor: float = 1e-10) -> float:
    """Return -log10(p) with a floor on extremely small p to avoid +inf.

    Args:
        value (float): Raw p-value in (0, 1].
        floor (float): Minimum p-value used before log transform.

    Returns:
        float: -log10(max(value, floor)).
    """
    v = float(value)
    if v <= 0 or not np.isfinite(v):
        raise ValueError(f"Invalid p-value for -log10: {value!r}")
    return float(-np.log10(max(v, floor)))


def overlapStringToRatio(overlap: str) -> float:
    """Parse Overlap strings like '28/1618' to the ratio overlap_count / background.

    Args:
        overlap (str): Enrichr overlap field.

    Returns:
        float: Gene ratio in [0, 1] (or 0 if denominator is zero).
    """
    s = str(overlap).strip()
    if "/" not in s:
        raise ValueError(f"Overlap must contain '/': {overlap!r}")
    num_s, den_s = s.split("/", 1)
    num = float(num_s)
    den = float(den_s)
    if den == 0:
        raise ValueError(f"Overlap denominator is zero: {overlap!r}")
    ratio = num / den
    if not np.isfinite(ratio):
        raise ValueError(f"Non-finite overlap ratio from: {overlap!r}")
    return float(ratio)


def readInputManifest(path: Path) -> pd.DataFrame:
    """Read two-column TSV: file path and sample label.

    Args:
        path (Path): Path to manifest TSV (header: file, label).

    Returns:
        pd.DataFrame: Columns ``file``, ``label``.
    """
    df = pd.read_csv(path, sep="\t", dtype=str)
    colmap = {str(c).lower(): c for c in df.columns}
    if "file" not in colmap or "label" not in colmap:
        raise ValueError(
            "Manifest must include columns 'file' and 'label' (case-insensitive); "
            f"got {list(df.columns)}"
        )
    out = pd.DataFrame(
        {
            "file": df[colmap["file"]].astype(str).str.strip(),
            "label": df[colmap["label"]].astype(str).str.strip(),
        }
    )
    return out


def readEnrichmentFile(path: Path) -> pd.DataFrame:
    """Load one Enrichr-style enrichment TSV.

    Args:
        path (Path): Path to enrichment table.

    Returns:
        pd.DataFrame: Parsed table with required numeric columns coerced.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Enrichment file not found: {path}")
    df = pd.read_csv(path, sep="\t", float_precision="high")
    required = [
        "Term",
        "Overlap",
        "P-value",
        "Adjusted P-value",
        "Odds Ratio",
        "Combined Score",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    for col in ("P-value", "Adjusted P-value", "Odds Ratio", "Combined Score"):
        df[col] = pd.to_numeric(df[col], errors="raise")
    df["Term"] = df["Term"].astype(str)
    return df


def parsePathwaysOfInterest(
    path: Path,
) -> List[Tuple[str, str]]:
    """Read pathways of interest: one column (term only) or two (term, display label).

    Args:
        path (Path): TSV without header.

    Returns:
        List of (original_term, display_label). If one column, display_label == original.
    """
    rows: List[Tuple[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) == 1:
                term = parts[0].strip()
                rows.append((term, term))
            elif len(parts) >= 2:
                term = parts[0].strip()
                disp = parts[1].strip()
                rows.append((term, disp))
            else:
                raise ValueError(f"Empty line at {path}:{line_no}")
    if not rows:
        raise ValueError(f"No pathways parsed from {path}")
    return rows


def buildLogMatrix(
    manifest: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Merge per-sample -log10(P) and -log10(FDR) on Term (outer join, fill 0).

    Mirrors enrichr_api summary construction for ranking.

    Args:
        manifest (pd.DataFrame): Columns file, label.

    Returns:
        Tuple of:
            - merged frame indexed by Term with columns ``{label} -log10(P)`` and
              ``{label} -log10(FDR)``,
            - list of P column names,
            - list of FDR column names.
    """
    dfs_list: List[pd.DataFrame] = []
    p_cols: List[str] = []
    fdr_cols: List[str] = []

    for _, row in manifest.iterrows():
        fpath = Path(row["file"]).expanduser()
        label = str(row["label"])
        df = readEnrichmentFile(fpath)
        p_col = f"{label} -log10(P)"
        fdr_col = f"{label} -log10(FDR)"
        p_cols.append(p_col)
        fdr_cols.append(fdr_col)
        work = df[["Term", "P-value", "Adjusted P-value"]].copy()
        work[p_col] = work["P-value"].apply(negLog10Safe)
        work[fdr_col] = work["Adjusted P-value"].apply(negLog10Safe)
        work = work[["Term", p_col, fdr_col]]
        dfs_list.append(work)

    if not dfs_list:
        raise ValueError("Manifest has no rows.")

    from functools import reduce

    merged = reduce(
        lambda left, right: pd.merge(left, right, on="Term", how="outer"),
        dfs_list,
    )
    merged = merged.fillna(0.0)
    merged = merged.set_index("Term", drop=True)
    return merged, p_cols, fdr_cols


def selectTopTermsByRankingSum(
    merged: pd.DataFrame,
    p_cols: Sequence[str],
    fdr_cols: Sequence[str],
    use_fdr_for_ranking: bool,
    top_n: int,
) -> List[str]:
    """Pick top_n terms by sum of absolute -log10 columns (enrichr_api strategy).

    Args:
        merged (pd.DataFrame): Output of buildLogMatrix (Term index).
        p_cols (Sequence[str]): Column names for -log10(P).
        fdr_cols (Sequence[str]): Column names for -log10(FDR).
        use_fdr_for_ranking (bool): If True, rank by sum of FDR columns; else P columns.
        top_n (int): Number of pathways to keep.

    Returns:
        List[str]: Term names, descending ranking.
    """
    cols = list(fdr_cols) if use_fdr_for_ranking else list(p_cols)
    ranking = merged[cols].apply(lambda x: np.sum(np.abs(x)), axis=1)
    order = ranking.sort_values(ascending=False).head(int(top_n))
    return list(order.index)


def sizeMetricForRow(row: pd.Series, metric: str) -> float:
    """Compute numeric size metric from one enrichment row."""
    if metric == "oddsRatio":
        return float(row["Odds Ratio"])
    if metric == "combinedScore":
        return float(row["Combined Score"])
    if metric == "overlap":
        return overlapStringToRatio(str(row["Overlap"]))
    raise ValueError(f"Unknown size metric: {metric}")


def collectPlotRecords(
    manifest: pd.DataFrame,
    terms_order: Sequence[str],
    term_to_display: Mapping[str, str],
    significance: str,
    size_metric: str,
    lgr: logging.Logger,
    significance_threshold: float,
    mark_missing_like_nonsignificant: bool,
) -> pd.DataFrame:
    """Build long-form data for scatter: one row per (term, sample) when found or when flagged.

    Logs missing pathways per input file at WARNING. If ``mark_missing_like_nonsignificant``
    is true, missing pathway×sample cells still produce a row with ``plot_status`` ``missing``.

    Args:
        manifest (pd.DataFrame): file, label columns.
        terms_order (Sequence[str]): Canonical Term strings to include.
        term_to_display (Mapping[str, str]): Term -> y-axis label.
        significance (str): ``adjustedPvalue`` or ``pvalue``.
        size_metric (str): oddsRatio, combinedScore, or overlap.
        lgr (logging.Logger): Logger.
        significance_threshold (float): Raw p-value cutoff; above = nonsignificant styling.
        mark_missing_like_nonsignificant (bool): Plot missing cells like nonsignificant grey.

    Returns:
        pd.DataFrame: Columns include Term, display, sample, neg_log10, size_value,
        plot_status (significant | nonsignificant | missing), source_file.
    """
    p_col_name = "Adjusted P-value" if significance == "adjustedPvalue" else "P-value"
    color_label = (
        "-log10(adjusted P-value)" if significance == "adjustedPvalue" else "-log10(P-value)"
    )

    records: List[Dict[str, Any]] = []

    for term in terms_order:
        for _, mrow in manifest.iterrows():
            fpath = Path(mrow["file"]).expanduser()
            label = str(mrow["label"])
            try:
                df = readEnrichmentFile(fpath)
            except Exception as exc:
                lgr.error("Failed to read %s: %s", fpath, exc)
                raise

            match = df[df["Term"] == term]
            if match.empty:
                lgr.warning(
                    "Pathway not found in file %s (label=%s): %s",
                    fpath,
                    label,
                    term,
                )
                if mark_missing_like_nonsignificant:
                    records.append(
                        {
                            "Term": term,
                            "display": term_to_display.get(term, term),
                            "sample": label,
                            "neg_log10": float("nan"),
                            "size_value": float("nan"),
                            "plot_status": "missing",
                            "color_quantity_label": color_label,
                            "source_file": str(fpath),
                        }
                    )
                continue
            row = match.iloc[0]
            raw_p = float(row[p_col_name])
            nl = negLog10Safe(raw_p)
            sz = sizeMetricForRow(row, size_metric)
            status = (
                "significant"
                if raw_p <= float(significance_threshold)
                else "nonsignificant"
            )
            records.append(
                {
                    "Term": term,
                    "display": term_to_display.get(term, term),
                    "sample": label,
                    "neg_log10": nl,
                    "size_value": sz,
                    "plot_status": status,
                    "color_quantity_label": color_label,
                    "source_file": str(fpath),
                }
            )

    out = pd.DataFrame.from_records(records)
    if out.empty:
        raise ValueError(
            "No data points to plot: no matching pathways in any input file."
        )

    finite_sizes = out.loc[out["plot_status"] != "missing", "size_value"].to_numpy(
        dtype=float
    )
    finite_sizes = finite_sizes[np.isfinite(finite_sizes)]
    if len(finite_sizes) > 0:
        min_sz = float(np.min(finite_sizes))
    else:
        min_sz = 1.0
    miss_mask = out["plot_status"] == "missing"
    if miss_mask.any():
        out.loc[miss_mask, "size_value"] = min_sz * 0.85

    if not np.all(np.isfinite(out["size_value"].to_numpy())):
        bad = out.loc[~np.isfinite(out["size_value"].to_numpy()), "size_value"]
        raise ValueError(f"Non-finite values in size_value after fill: {bad}")
    found_mask = out["plot_status"].isin(["significant", "nonsignificant"])
    sub_nl = out.loc[found_mask, "neg_log10"].to_numpy(dtype=float)
    if not np.all(np.isfinite(sub_nl)):
        raise ValueError("Non-finite neg_log10 for significant/nonsignificant rows.")
    return out


def resolveColormap(
    colormap_arg: str,
    significance: str,
) -> Tuple[mcolors.Colormap, str]:
    """Resolve matplotlib colormap and colorbar label.

    Args:
        colormap_arg (str): ``auto`` or a registered matplotlib colormap name.
        significance (str): adjustedPvalue vs pvalue (used when auto).

    Returns:
        Tuple of (Colormap, colorbar label string).
    """
    if colormap_arg.lower() == "auto":
        _, oranges, reds = getHeatmapStyleColormaps()
        if significance == "adjustedPvalue":
            return reds, "-log10(FDR)"  # aligned with enrichr_api FDR heatmap label
        return oranges, "-log10(p-value)"
    try:
        cmap = matplotlib.colormaps[colormap_arg]  # matplotlib >= 3.7
    except Exception:
        cmap = cm.get_cmap(colormap_arg)
    if significance == "adjustedPvalue":
        return cmap, "-log10(adjusted P-value)"
    return cmap, "-log10(P-value)"


def scatterDotplot(
    plot_df: pd.DataFrame,
    cmap: mcolors.Colormap,
    colorbar_label: str,
    vmin: float,
    vmax: float,
    size_metric_key: str,
    show_ring: bool,
    figure_title: Optional[str],
    y_label: str,
    x_label: str,
    dot_scale: float,
    figsize: Tuple[float, float],
    y_display_order: Sequence[str],
    x_sample_order: Sequence[str],
    legendLabelSpacing: float = 2.15,
    legendBorderPad: float = 0.9,
) -> Tuple[plt.Figure, plt.Axes]:
    """Draw a dot plot with optional outer ring (GSEApy-style).

    Args:
        plot_df (pd.DataFrame): Must contain display, sample, neg_log10, size_value, plot_status.
        cmap (Colormap): Colormap for -log10 values (significant points only).
        colorbar_label (str): Colorbar title.
        vmin (float): Color scale minimum.
        vmax (float): Color scale maximum.
        size_metric_key (str): Name of size metric for legend text.
        show_ring (bool): Draw visible edge around markers.
        figure_title (str, optional): If set, figure title; if None or empty, no title.
        y_label (str): Y axis label (pathways).
        x_label (str): X axis label (samples).
        dot_scale (float): Scales marker area (points^2 base multiplier).
        figsize (Tuple[float, float]): Figure size in inches.
        y_display_order (Sequence[str]): Pathway display labels top-to-bottom.
        x_sample_order (Sequence[str]): Sample columns left-to-right.
        legendLabelSpacing (float): Vertical gap between size-legend rows (matplotlib ``labelspacing``).
        legendBorderPad (float): Padding inside the size-legend frame.

    Returns:
        Tuple of (Figure, Axes).
    """
    pathways = [str(x) for x in y_display_order]
    samples = [str(x) for x in x_sample_order]
    y_index = {p: i for i, p in enumerate(pathways)}
    x_index = {s: i for i, s in enumerate(samples)}

    plot_df = plot_df.reset_index(drop=True)
    if "plot_status" not in plot_df.columns:
        plot_df = plot_df.assign(plot_status="significant")
    is_sig = (plot_df["plot_status"] == "significant").to_numpy()
    is_grey = plot_df["plot_status"].isin(["nonsignificant", "missing"]).to_numpy()

    sizes = plot_df["size_value"].to_numpy(dtype=float)
    smin = float(np.min(sizes))
    smax = float(np.max(sizes))
    if smin == smax:
        size_pts = np.full(len(plot_df), 80.0 * dot_scale)
    else:
        norm_sz = (sizes - smin) / (smax - smin)
        size_pts = (30.0 + 220.0 * norm_sz) * dot_scale

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(FIGURE_CANVAS_FACE_COLOR)
    ax.set_facecolor(RING_PANEL_FACE_COLOR)
    xs = np.array([x_index[str(s)] for s in plot_df["sample"]], dtype=float)
    ys = np.array([y_index[str(p)] for p in plot_df["display"]], dtype=float)

    # GSEApy DotPlot.scatter(outer_ring=True): three scatters, edgecolors none.
    # Ring radii use the global maximum marker *area* (smax), not per-point area:
    #   black s = smax * 1.6, white s = smax * 1.3, inner s = area per row.
    # (See gseapy plot.py / gseapy.code.example.txt.) A white middle layer is
    # invisible on a default white axes face; use an off-white panel so
    # the white ring reads as a ring, not only a black outer halo.
    if show_ring:
        smax_area = float(np.max(size_pts))
        ring_black = 1.6
        ring_white = 1.3
        ax.scatter(
            xs,
            ys,
            s=smax_area * ring_black,
            c="black",
            edgecolors="none",
            linewidths=0.0,
            zorder=1,
        )
        ax.scatter(
            xs,
            ys,
            s=smax_area * ring_white,
            c="white",
            edgecolors="none",
            linewidths=0.0,
            zorder=2,
        )

    sc = None
    if np.any(is_sig):
        sc = ax.scatter(
            xs[is_sig],
            ys[is_sig],
            s=size_pts[is_sig],
            c=plot_df.loc[is_sig, "neg_log10"].to_numpy(dtype=float),
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            edgecolors="none",
            linewidths=0.0,
            zorder=3 if show_ring else 1,
        )
    if np.any(is_grey):
        ax.scatter(
            xs[is_grey],
            ys[is_grey],
            s=size_pts[is_grey],
            c=NONSIGNIFICANT_FACE_COLOR,
            edgecolors="none",
            linewidths=0.0,
            zorder=4 if show_ring else 2,
        )

    ax.set_xticks(range(len(samples)))
    ax.set_xticklabels(samples, rotation=45, ha="right")
    ax.set_yticks(range(len(pathways)))
    ax.set_yticklabels(pathways)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if figure_title is not None and str(figure_title).strip():
        ax.set_title(str(figure_title).strip())
    if sc is not None:
        cbar = fig.colorbar(sc, ax=ax, shrink=0.6)
        cbar.set_label(colorbar_label)

    # Size legend: representative markers at min/mid/max (marker size ~ sqrt scatter s)
    legend_handles: List[Line2D] = []
    for frac, lab in ((0.0, "min"), (0.5, "mid"), (1.0, "max")):
        if smin == smax:
            val = smin
            s_pt = 80.0 * dot_scale
        else:
            val = smin + frac * (smax - smin)
            norm_sz = (val - smin) / (smax - smin)
            s_pt = (30.0 + 220.0 * norm_sz) * dot_scale
        msize = float(np.sqrt(max(s_pt, 1e-6)))
        legend_handles.append(
            Line2D(
                [0],
                [0],
                linestyle="None",
                marker="o",
                markersize=msize,
                markerfacecolor="0.45",
                markeredgecolor="0.45",
                markeredgewidth=0.0,
                label=f"{lab}: {val:.4g}",
            )
        )
    leg = ax.legend(
        handles=legend_handles,
        title=f"Dot size ({size_metric_key})",
        loc="upper left",
        bbox_to_anchor=(1.28, 1.0),
        frameon=True,
        labelspacing=float(legendLabelSpacing),
        borderpad=float(legendBorderPad),
        handletextpad=0.65,
        handlelength=1.0,
        handleheight=1.6,
        borderaxespad=0.55,
    )
    leg.get_title().set_fontsize("small")

    ax.set_xlim(-0.5, len(samples) - 0.5)
    ax.set_ylim(-0.5, len(pathways) - 0.5)
    ax.invert_yaxis()
    fig.tight_layout()
    return fig, ax


def resolveFigureSizeInches(
    n_columns: int,
    n_rows: int,
    figure_width: Optional[float],
    figure_height: Optional[float],
    figure_width_per_column: float,
    figure_width_pad: float,
    figure_height_per_row: float,
    figure_height_pad: float,
) -> Tuple[float, float]:
    """Compute figure width and height in inches.

    Width defaults to ``figure_width_pad + n_columns * figure_width_per_column``
    (minimum 4 inches). Height defaults to ``figure_height_pad + n_rows *
    figure_height_per_row`` (minimum 4 inches) unless explicit dimensions override.

    Args:
        n_columns (int): Number of x-axis categories (manifest rows).
        n_rows (int): Number of pathway rows plotted.
        figure_width (float, optional): If set, fixed width in inches.
        figure_height (float, optional): If set, fixed height in inches.
        figure_width_per_column (float): Inches per column when width is auto.
        figure_width_pad (float): Extra inches for margins, colorbar, and legend when width is auto.
        figure_height_per_row (float): Inches per pathway row when height is auto.
        figure_height_pad (float): Base height when height is auto.

    Returns:
        Tuple of (width_inches, height_inches).
    """
    n_columns = max(1, int(n_columns))
    n_rows = max(1, int(n_rows))
    if figure_width is not None:
        w = float(figure_width)
    else:
        w = float(figure_width_pad) + n_columns * float(figure_width_per_column)
        w = max(4.0, w)
    if figure_height is not None:
        h = float(figure_height)
    else:
        h = float(figure_height_pad) + n_rows * float(figure_height_per_row)
        h = max(4.0, h)
    return (w, h)


def parseArgs(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    lgr.info("Current working directory: %s", os.getcwd())
    argv_for_log = list(sys.argv[1:] if argv is None else argv)
    lgr.info(
        "Command used to run the program: %s %s",
        Path(sys.executable).name,
        " ".join(shlex.quote(str(x)) for x in argv_for_log),
    )

    parser = argparse.ArgumentParser(
        description="Dot plot for pathway enrichment across labeled samples."
    )
    parser.add_argument(
        "--inputManifest",
        required=True,
        type=str,
        help="TSV with columns file<TAB>label listing enrichment tables and sample names.",
    )
    parser.add_argument(
        "--outputPrefix",
        required=True,
        type=str,
        help="Prefix for output PDF/PNG/TSV/log files (no directory).",
    )
    parser.add_argument(
        "--outputDir",
        default=".",
        type=str,
        help="Directory for outputs (default: current directory).",
    )
    parser.add_argument(
        "--significanceColumn",
        choices=["adjustedPvalue", "pvalue"],
        default="adjustedPvalue",
        help="Which p-value column drives color (-log10). Default: adjustedPvalue (FDR).",
    )
    parser.add_argument(
        "--colormap",
        default="auto",
        type=str,
        help="Colormap: 'auto' uses enrichr_api-style greys+Reds (FDR) or greys+Oranges (P); "
        "otherwise any matplotlib registered name (e.g. viridis_r).",
    )
    parser.add_argument(
        "--colorVmin",
        default=0.0,
        type=float,
        help="Minimum for color scale (default 0, matching enrichr_api heatmaps).",
    )
    parser.add_argument(
        "--colorVmax",
        default=5.0,
        type=float,
        help="Maximum for color scale (default 5, matching enrichr_api heatmaps).",
    )
    parser.add_argument(
        "--sizeMetric",
        choices=["oddsRatio", "combinedScore", "overlap"],
        default="oddsRatio",
        help="Numeric quantity controlling dot size (overlap parses 'k/n' as k/n).",
    )
    parser.add_argument(
        "--pathwaysOfInterest",
        default=None,
        type=str,
        help="Optional TSV without header: pathway term, or term<TAB>display label.",
    )
    parser.add_argument(
        "--topN",
        default=10,
        type=int,
        help="When --pathwaysOfInterest is omitted, number of top pathways by ranking sum.",
    )
    parser.add_argument(
        "--dotScale",
        default=2.0,
        type=float,
        help="Multiplier for dot sizes (default 2.0).",
    )
    parser.add_argument(
        "--showRing",
        default="true",
        type=str,
        help="Draw outer ring on markers (true/false). Default: true.",
    )
    parser.add_argument(
        "--figureWidth",
        default=None,
        type=float,
        help="Figure width in inches. If omitted, width = figureWidthPad + nColumns * figureWidthPerColumn (min 4 in).",
    )
    parser.add_argument(
        "--figureHeight",
        default=None,
        type=float,
        help="Figure height in inches. If omitted, height = figureHeightPad + nRows * figureHeightPerRow (min 4 in).",
    )
    parser.add_argument(
        "--figureWidthPerColumn",
        default=1.15,
        type=float,
        help="When --figureWidth is omitted, inches allocated per sample column (x category). Default: 1.15.",
    )
    parser.add_argument(
        "--figureWidthPad",
        default=1.0,
        type=float,
        help="When --figureWidth is omitted, extra inches for y-axis labels, colorbar, and legend. Default: 1.0.",
    )
    parser.add_argument(
        "--figureHeightPerRow",
        default=0.35,
        type=float,
        help="When --figureHeight is omitted, inches per pathway row (y). Default: 0.35.",
    )
    parser.add_argument(
        "--figureHeightPad",
        default=2.0,
        type=float,
        help="When --figureHeight is omitted, base height in inches before row scaling. Default: 2.0.",
    )
    parser.add_argument(
        "--legendLabelSpacing",
        default=2.15,
        type=float,
        help="Vertical spacing between size-legend entries (matplotlib labelspacing). Default: 2.15.",
    )
    parser.add_argument(
        "--legendBorderPad",
        default=0.9,
        type=float,
        help="Padding inside the size-legend frame. Default: 0.9.",
    )
    parser.add_argument(
        "--figureTitle",
        default=None,
        type=str,
        help="Optional figure title. If omitted or empty, no title is drawn.",
    )
    parser.add_argument(
        "--significanceThreshold",
        default=0.05,
        type=float,
        help="Threshold on the raw p column used for color (--significanceColumn): "
        "values above are drawn in neutral grey (nonsignificant). Default: 0.05.",
    )
    parser.add_argument(
        "--markMissingLikeNonsignificant",
        default="false",
        type=str,
        help="If true, draw a grey dot for pathway×sample pairs missing from that file "
        "(same style as nonsignificant). Default: false.",
    )
    parser.add_argument(
        "--logLevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )

    args = parser.parse_args(argv)

    try:
        import importlib.metadata as imeta

        rich_v = imeta.version("rich")
    except Exception:
        try:
            import pkg_resources

            rich_v = pkg_resources.get_distribution("rich").version
        except Exception:
            rich_v = "unknown"
    lgr.info(
        "Package versions: pandas=%s numpy=%s matplotlib=%s seaborn=%s rich=%s",
        pd.__version__,
        np.__version__,
        matplotlib.__version__,
        sns.__version__,
        rich_v,
    )

    return args


def writeRunMetadata(
    out_dir: Path,
    prefix: str,
    args: argparse.Namespace,
) -> Path:
    """Write UTC run metadata JSON next to outputs."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {
        "run_id": run_id,
        "timestamp_utc": run_id,
        "script": Path(__file__).name,
        "argv": list(sys.argv),
        "args": {k: getattr(args, k) for k in vars(args)},
    }
    path = out_dir / f"{prefix}.run_metadata.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> None:
    """CLI entry: load tables, rank or filter pathways, plot, save TSVs."""
    configureLogging()
    args = parseArgs(argv)

    out_dir = Path(args.outputDir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = str(args.outputPrefix).strip()
    if not prefix:
        raise ValueError("--outputPrefix must be non-empty.")

    configureLogging(analysisPrefix=str(out_dir / prefix), logLevel=args.logLevel)
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)

    manifest_path = Path(args.inputManifest).expanduser().resolve()
    manifest = readInputManifest(manifest_path)
    lgr.info("Loaded manifest with %d rows from %s", len(manifest), manifest_path)

    merged, p_cols, fdr_cols = buildLogMatrix(manifest)
    use_fdr = args.significanceColumn == "adjustedPvalue"

    if args.pathwaysOfInterest:
        poi_path = Path(args.pathwaysOfInterest).expanduser().resolve()
        poi = parsePathwaysOfInterest(poi_path)
        terms_order = [t for t, _ in poi]
        term_to_display = {t: d for t, d in poi}
        lgr.info(
            "Using %d pathways from %s",
            len(terms_order),
            poi_path,
        )
    else:
        terms_order = selectTopTermsByRankingSum(
            merged,
            p_cols,
            fdr_cols,
            use_fdr_for_ranking=use_fdr,
            top_n=args.topN,
        )
        term_to_display = {t: t for t in terms_order}
        lgr.info(
            "Selected top %d pathways by ranking sum (%s).",
            len(terms_order),
            "FDR" if use_fdr else "P-value",
        )

    plot_df = collectPlotRecords(
        manifest,
        terms_order,
        term_to_display,
        significance=args.significanceColumn,
        size_metric=args.sizeMetric,
        lgr=lgr,
        significance_threshold=float(args.significanceThreshold),
        mark_missing_like_nonsignificant=str2bool(args.markMissingLikeNonsignificant),
    )

    cmap, cb_label = resolveColormap(args.colormap, args.significanceColumn)

    size_names = {
        "oddsRatio": "Odds ratio",
        "combinedScore": "Combined score",
        "overlap": "Overlap (k/n)",
    }

    terms_plotted = set(plot_df["Term"].unique())
    y_order = [term_to_display[t] for t in terms_order if t in terms_plotted]
    seen_display: Set[str] = set()
    y_display_order: List[str] = []
    for lab in y_order:
        if lab not in seen_display:
            seen_display.add(lab)
            y_display_order.append(lab)
    for disp in pd.unique(plot_df["display"]):
        if disp not in seen_display:
            lgr.warning(
                "Display label %r was not in ordered pathway list; appending to Y axis.",
                disp,
            )
            seen_display.add(str(disp))
            y_display_order.append(str(disp))

    sample_order = [str(x) for x in manifest["label"].tolist()]
    n_rows = max(1, len(y_display_order))
    n_cols = max(1, len(sample_order))
    fig_w, fig_h = resolveFigureSizeInches(
        n_columns=n_cols,
        n_rows=n_rows,
        figure_width=args.figureWidth,
        figure_height=args.figureHeight,
        figure_width_per_column=float(args.figureWidthPerColumn),
        figure_width_pad=float(args.figureWidthPad),
        figure_height_per_row=float(args.figureHeightPerRow),
        figure_height_pad=float(args.figureHeightPad),
    )
    lgr.info(
        "Figure size %.2f x %.2f in (columns=%d, rows=%d; width auto=%s, height auto=%s)",
        fig_w,
        fig_h,
        n_cols,
        n_rows,
        args.figureWidth is None,
        args.figureHeight is None,
    )

    ft_raw = args.figureTitle
    figure_title_opt: Optional[str] = None
    if ft_raw is not None and str(ft_raw).strip():
        figure_title_opt = str(ft_raw).strip()

    fig, ax = scatterDotplot(
        plot_df,
        cmap=cmap,
        colorbar_label=cb_label,
        vmin=float(args.colorVmin),
        vmax=float(args.colorVmax),
        size_metric_key=size_names[args.sizeMetric],
        show_ring=str2bool(args.showRing),
        figure_title=figure_title_opt,
        y_label="Pathway",
        x_label="Sample",
        dot_scale=float(args.dotScale),
        figsize=(fig_w, fig_h),
        y_display_order=y_display_order,
        x_sample_order=sample_order,
        legendLabelSpacing=float(args.legendLabelSpacing),
        legendBorderPad=float(args.legendBorderPad),
    )

    base = out_dir / prefix
    pdf_path = Path(str(base) + ".dotplot.pdf")
    png_path = Path(str(base) + ".dotplot.png")
    fig.savefig(
        pdf_path,
        bbox_inches="tight",
        dpi=300,
        facecolor=FIGURE_CANVAS_FACE_COLOR,
        edgecolor="none",
    )
    fig.savefig(
        png_path,
        bbox_inches="tight",
        dpi=300,
        facecolor=FIGURE_CANVAS_FACE_COLOR,
        edgecolor="none",
    )
    plt.close(fig)
    lgr.info("Wrote %s and %s", pdf_path, png_path)

    color_pivot = plot_df.pivot_table(
        index="display",
        columns="sample",
        values="neg_log10",
        aggfunc="first",
    )
    color_pivot = color_pivot.reindex(columns=sample_order)
    color_pivot.to_csv(
        str(base) + ".plotted_color_values.tsv",
        sep="\t",
    )
    size_pivot = plot_df.pivot_table(
        index="display",
        columns="sample",
        values="size_value",
        aggfunc="first",
    )
    size_pivot = size_pivot.reindex(columns=sample_order)
    size_pivot.to_csv(
        str(base) + ".plotted_size_values.tsv",
        sep="\t",
    )
    status_pivot = plot_df.pivot_table(
        index="display",
        columns="sample",
        values="plot_status",
        aggfunc="first",
    )
    status_pivot = status_pivot.reindex(columns=sample_order)
    status_pivot.to_csv(
        str(base) + ".plotted_plot_status.tsv",
        sep="\t",
    )
    lgr.info(
        "Wrote TSVs: %s.plotted_color_values.tsv, %s.plotted_size_values.tsv, %s.plotted_plot_status.tsv",
        base,
        base,
        base,
    )

    meta_path = writeRunMetadata(out_dir, prefix, args)
    lgr.info("Wrote run metadata: %s", meta_path)

    command_used = " ".join(shlex.quote(arg) for arg in [Path(sys.executable).name] + list(sys.argv))
    lgr.info("Command used to run script: %s", command_used)

    lgr.info("All done, thank you!")


if __name__ == "__main__":
    main()
