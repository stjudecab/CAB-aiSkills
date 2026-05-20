#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2024-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: volcano_ma_grid.py
# Description:
# Volcano and MA plot grids from differential-analysis result tables (manifest TSV).
#########################################################################

"""
volcano_grid.py
===============

Create uniform grids of Volcano and/or MA plots from multiple
differential-analysis result tables listed in a two-column TSV file.

The script will
- read a TSV that contains absolute paths in the column *inputFile*
  and friendly labels in *sampleLabel*,
- draw either or both plot families (Volcano and MA) with axis limits
  shared across every panel so the figures are directly comparable,
- highlight user-supplied feature IDs (for example gene symbols), and
- export high-resolution PNG and PDF figures.

Typical command-line sessions
-----------------------------

# 1.  Draw both grids with default column names
python volcano_grid.py inputs.tsv results/baseline

# 2.  Volcano grid only, custom fold-change column, highlight two genes
python volcano_grid.py inputs.tsv results/volcOnly \
       --plotsToPlot volcano \
       --fcCol log2FC \
       --labelPoints FXN,TP53

# 3.  MA grid only, specify average-expression column, force 4 columns
python volcano_grid.py inputs.tsv results/MA \
       --plotsToPlot ma \
       --aveExprCol log2AveExpr \
       --cols 4
"""

from __future__ import annotations
import math, os, re, inspect
import math
import os
import inspect
from pathlib import Path
from sys import stdout
from typing import Sequence, Tuple, Set

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patheffects as pe
import logging

# -----------------------------------------------------------------------------
# logging helpers
# -----------------------------------------------------------------------------
class CustomFormatter(logging.Formatter):
    """
    Colour-coded formatter for console output.
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    blue = "\x1b[34;20m"
    pink = "\x1b[35;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = (
        "###\t[%(asctime)s] %(filename)s:%(lineno)d: "
        "%(name)s %(levelname)s: %(message)s"
    )

    FORMATS = {
        logging.DEBUG: blue + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def str2bool(v):
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    if str(v).lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif str(v).lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        lgr.critical("Unrecognized parameter was set for '{}'. Program was aborted.".format(v))
        exit()

def configure_logging(log_prefix: str = os.path.basename(__file__).replace(".py", "")):
    """
    Configure root logger with colourful console output and a plain text log file.

    A file called <log_prefix>.log will be created in the working directory.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    stream_hdlr = logging.StreamHandler(stdout)
    file_hdlr = logging.FileHandler(f"{log_prefix}.log")

    stream_hdlr.setLevel(logging.INFO)
    file_hdlr.setLevel(logging.INFO)

    stream_hdlr.setFormatter(CustomFormatter())
    file_hdlr.setFormatter(
        logging.Formatter(
            "###\t[%(asctime)s] %(filename)s:%(lineno)d: "
            "%(name)s %(levelname)s: %(message)s"
        )
    )

    logger.addHandler(stream_hdlr)
    logger.addHandler(file_hdlr)


# -----------------------------------------------------------------------------
# utilities
# -----------------------------------------------------------------------------
def _format_p_value(v) -> float:
    """
    Convert a numeric value or a string like '<1e-08' to -log10(p).

    Parameters
    ----------
    v : float | str
        Raw p-value or q-value originating from the result table.

    Returns
    -------
    float
        The negative base-10 logarithm of v.
    """
    try:
        return -np.log10(float(v))
    except Exception:
        if isinstance(v, str) and "<" in v:
            return -np.log10(float(v.replace("<", "").replace(" ", "")))
        raise


def _scan_limits_volcano(
    paths: Sequence[Path],
    fc_col: str,
    sig_col: str,
    custom_abs_max_fc: float | None = None,
    custom_max_p: float | None = None,
) -> Tuple[float, float]:
    """
    Derive global axis limits for a set of Volcano plots.

    For every file the absolute maximum |fold-change| and the largest
    -log10(FDR) are collected; ten percent padding is then added.
    If custom_abs_max_fc or custom_max_p are set, they override the data-driven values.

    Returns
    -------
    absMaxX, absMaxY : float
        Values suitable for Axes.set_xlim and Axes.set_ylim.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    max_abs_fc, max_logsig = 0.0, 0.0
    for fp in paths:
        lgr.debug(f"Scanning {fp}")
        df = pd.read_csv(fp, sep="\t", usecols=[fc_col, sig_col])
        max_abs_fc = max(max_abs_fc, df[fc_col].abs().max(skipna=True))
        max_logsig = max(
            max_logsig, df[sig_col].apply(_format_p_value).max(skipna=True)
        )
    # Axis limits: always add 10% padding for clean visualization
    abs_x = (custom_abs_max_fc if custom_abs_max_fc is not None else max_abs_fc) * 1.10
    abs_y = (custom_max_p if custom_max_p is not None else max_logsig) * 1.10
    return abs_x, abs_y


def _scan_limits_ma(
    paths: Sequence[Path],
    fc_col: str,
    ave_col: str,
    custom_abs_max_fc: float | None = None,
    custom_ave_min: float | None = None,
    custom_ave_max: float | None = None,
) -> Tuple[float, Tuple[float, float]]:
    """
    Derive global axis limits for a set of MA plots.
    Custom limits override data-driven values when provided.

    Returns
    -------
    absMaxY : float
    (x_min, x_max) : tuple[float, float]
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    max_abs_fc, x_min, x_max = 0.0, 1e9, -1e9
    for fp in paths:
        lgr.debug(f"Scanning {fp}")
        df = pd.read_csv(fp, sep="\t", usecols=[fc_col, ave_col])
        max_abs_fc = max(max_abs_fc, df[fc_col].abs().max(skipna=True))
        x_min = min(x_min, df[ave_col].min(skipna=True))
        x_max = max(x_max, df[ave_col].max(skipna=True))
    # Y-axis (FC): always add 10% padding for clean visualization
    y_lim = (custom_abs_max_fc if custom_abs_max_fc is not None else max_abs_fc) * 1.10
    # Always add 10% padding for clean visualization
    if custom_ave_min is not None or custom_ave_max is not None:
        x_min_use = custom_ave_min if custom_ave_min is not None else x_min
        x_max_use = custom_ave_max if custom_ave_max is not None else x_max
        x_span = (x_max_use - x_min_use) * 0.10
        x_lim = (x_min_use - x_span, x_max_use + x_span)
    else:
        x_span = (x_max - x_min) * 0.10
        x_lim = (x_min - x_span, x_max + x_span)
    return y_lim, x_lim


# -----------------------------------------------------------------------------
# single-panel drawers
# -----------------------------------------------------------------------------
def _draw_common_frame(ax: plt.Axes):
    """Ensure all four spines are visible and set short tick marks."""
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(True)
    ax.tick_params(length=2)


def _add_labels(
    ax: plt.Axes,
    rows: pd.DataFrame,
    x: str,
    y: str,
    name_col: str,
    addText: bool = True,
    identifyRegionByGeneName: bool = False,
    region2gene: dict | None = None
):
    """
    Scatter a larger black point and write a white-outlined label
    for each row supplied.
    """
    sns.scatterplot(
        rows,
        x=x,
        y=y,
        s=17,
        color="black",
        edgecolor="white",
        ax=ax,
        zorder=4,
    )
    if addText:
        for _, r in rows.iterrows():
            ax.text(
                r[x] + 0.25,
                r[y] + 0.1,
                str(r[name_col]) if not identifyRegionByGeneName else str(region2gene[r[name_col]]),
                fontsize=8,
                color="black",
                fontweight="bold",
                path_effects=[
                    pe.Stroke(linewidth=1, foreground="white"),
                    pe.Normal(),
                ],
                zorder=5,
            )


def _plot_single_volcano(
    df: pd.DataFrame,
    ax: plt.Axes,
    *,
    fc_col: str,
    sig_col: str,
    name_col: str,
    fc_cut: float,
    fdr_cut: float,
    abs_max_x: float,
    abs_max_y: float,
    label_points: Sequence[str] | None,
    plotGeneNames: bool = True,
    plotDiffGeneMark: bool = True,
    identifyRegionByGeneName: bool = False,
    region2gene: dict | None = None,
    fc_clip_limit: float | None = None,
) -> Tuple[Set[str], Set[str]]:
    """
    Draw one Volcano plot inside *ax*.
    If fc_clip_limit is set, FC values are clipped to [-fc_clip_limit, fc_clip_limit] for display.
    """
    grey, red, blue = "#B7B7B7", "#d9534f", "#428bca"
    df[f"-log10({sig_col})"] = df[sig_col].apply(_format_p_value)
    fc_thr = np.log2(fc_cut) if "log2" in fc_col.lower() else fc_cut
    up = df[(df[fc_col] > fc_thr) & (df[sig_col] < fdr_cut)]
    dn = df[(df[fc_col] < -fc_thr) & (df[sig_col] < fdr_cut)]

    if fc_clip_limit is not None:
        df_plot = df.copy()
        df_plot[fc_col] = np.clip(df_plot[fc_col], -fc_clip_limit, fc_clip_limit)
        up_plot = up.copy()
        up_plot[fc_col] = np.clip(up_plot[fc_col], -fc_clip_limit, fc_clip_limit)
        dn_plot = dn.copy()
        dn_plot[fc_col] = np.clip(dn_plot[fc_col], -fc_clip_limit, fc_clip_limit)
    else:
        df_plot, up_plot, dn_plot = df, up, dn

    sns.scatterplot(
        df_plot,
        x=fc_col,
        y=f"-log10({sig_col})",
        s=3,
        color=grey,
        ax=ax,
        edgecolor="none",
    )
    sns.scatterplot(
        up_plot,
        x=fc_col,
        y=f"-log10({sig_col})",
        s=3,
        color=red,
        ax=ax,
        edgecolor="none",
    )
    sns.scatterplot(
        dn_plot,
        x=fc_col,
        y=f"-log10({sig_col})",
        s=3,
        color=blue,
        ax=ax,
        edgecolor="none",
    )

    ax.axhline(-np.log10(fdr_cut), ls="--", lw=0.3, color="black")
    ax.axvline(fc_thr, ls="--", lw=0.3, color="black")
    ax.axvline(-fc_thr, ls="--", lw=0.3, color="black")

    if label_points is not None:
        presentPoints = len(df[df[name_col].isin(label_points)])
        if presentPoints == 0:
            lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
            lgr.warning(f"None of the label points were found in the data frame, so no labels will be plotted.")
            greenMeansGo = False
        else:
            lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
            lgr.info(f"{presentPoints} out of {len(label_points)} label points were found in the data frame.")
            greenMeansGo = True

        if greenMeansGo:
            if plotGeneNames:
                if plotDiffGeneMark:
                
                    interest = df[df[name_col].isin(label_points)].copy()

                    if not interest.empty:
                        def _suffix(row):
                            if row[sig_col] < fdr_cut and row[fc_col] >  fc_thr:
                                return " (↑)"
                            if row[sig_col] < fdr_cut and row[fc_col] < -fc_thr:
                                return " (↓)"
                            return " (≈)"

                        interest["label_text"] = interest[name_col] + interest.apply(_suffix, axis=1)
                        interest_display = interest.copy()
                        if fc_clip_limit is not None:
                            interest_display[fc_col] = np.clip(interest_display[fc_col], -fc_clip_limit, fc_clip_limit)
                        # plot big black dots + text
                        _add_labels(
                            ax,
                            interest_display,         # DataFrame with label_text column (clipped for position if fc_clip_limit set)
                            fc_col,
                            f"-log10({sig_col})",
                            "label_text",             # column to display
                            addText=True,
                            identifyRegionByGeneName=identifyRegionByGeneName,
                            region2gene=region2gene if identifyRegionByGeneName else None
                        )
                
                else:
                    label_df = df[df[name_col].isin(label_points)]
                    if fc_clip_limit is not None:
                        label_df = label_df.copy()
                        label_df[fc_col] = np.clip(label_df[fc_col], -fc_clip_limit, fc_clip_limit)
                    _add_labels(
                        ax,
                        label_df,
                        fc_col,
                        f"-log10({sig_col})",
                        name_col,
                        addText=True,
                        identifyRegionByGeneName=identifyRegionByGeneName,
                        region2gene=region2gene if identifyRegionByGeneName else None
                    )
            else:
                label_df = df[df[name_col].isin(label_points)]
                if fc_clip_limit is not None:
                    label_df = label_df.copy()
                    label_df[fc_col] = np.clip(label_df[fc_col], -fc_clip_limit, fc_clip_limit)
                _add_labels(
                        ax,
                        label_df,
                        fc_col,
                        f"-log10({sig_col})",
                        "none",
                        addText=False,
                        identifyRegionByGeneName=identifyRegionByGeneName,
                        region2gene=region2gene if identifyRegionByGeneName else None
                    )

    ax.set_xlim(-abs_max_x, abs_max_x)
    ax.set_ylim(0, abs_max_y)
    ax.text(
        0.01,
        0.99,
        f"↓{len(dn):,}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=blue,
        fontsize=10,
    )
    ax.text(
        0.99,
        0.99,
        f"↑{len(up):,}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        color=red,
        fontsize=10,
    )

    _draw_common_frame(ax)

    def _id_to_gene(val):
        return region2gene[val] if (identifyRegionByGeneName and
                                    region2gene is not None and
                                    val in region2gene) else val

    return { _id_to_gene(x) for x in up[name_col].dropna() }, \
           { _id_to_gene(x) for x in dn[name_col].dropna() }


def _plot_single_ma(
    df: pd.DataFrame,
    ax: plt.Axes,
    *,
    fc_col: str,
    ave_col: str,
    name_col: str,
    fc_cut: float,
    abs_max_y: float,
    x_min: float,
    x_max: float,
    label_points: Sequence[str] | None,
    plotGeneNames: bool = True,
    plotDiffGeneMark: bool = True,
    identifyRegionByGeneName: bool = False,
    region2gene: dict | None = None,
    fc_clip_limit: float | None = None,
) -> Tuple[Set[str], Set[str]]:
    """
    Draw one MA plot inside *ax*.
    If fc_clip_limit is set, FC values are clipped to [-fc_clip_limit, fc_clip_limit] for display.
    """
    grey, red, blue = "#B7B7B7", "#d9534f", "#428bca"
    fc_thr = np.log2(fc_cut) if "log2" in fc_col.lower() else fc_cut
    up = df[df[fc_col] > fc_thr]
    dn = df[df[fc_col] < -fc_thr]

    if fc_clip_limit is not None:
        df_plot = df.copy()
        df_plot[fc_col] = np.clip(df_plot[fc_col], -fc_clip_limit, fc_clip_limit)
        up_plot = up.copy()
        up_plot[fc_col] = np.clip(up_plot[fc_col], -fc_clip_limit, fc_clip_limit)
        dn_plot = dn.copy()
        dn_plot[fc_col] = np.clip(dn_plot[fc_col], -fc_clip_limit, fc_clip_limit)
    else:
        df_plot, up_plot, dn_plot = df, up, dn

    sns.scatterplot(
        df_plot,
        x=ave_col,
        y=fc_col,
        s=3,
        color=grey,
        ax=ax,
        edgecolor="none",
    )
    sns.scatterplot(
        up_plot,
        x=ave_col,
        y=fc_col,
        s=3,
        color=red,
        ax=ax,
        edgecolor="none",
    )
    sns.scatterplot(
        dn_plot,
        x=ave_col,
        y=fc_col,
        s=3,
        color=blue,
        ax=ax,
        edgecolor="none",
    )

    ax.axhline(fc_thr, ls="--", lw=0.3, color="black")
    ax.axhline(-fc_thr, ls="--", lw=0.3, color="black")
    ax.axhline(0, ls="-", lw=0.3, color="black")

    if label_points is not None:
        presentPoints = len(df[df[name_col].isin(label_points)])
        if presentPoints == 0:
            lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
            lgr.warning(f"None of the label points were found in the data frame, so no labels will be plotted.")
            greenMeansGo = False
        else:
            lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
            lgr.info(f"{presentPoints} out of {len(label_points)} label points were found in the data frame.")
            greenMeansGo = True

        if greenMeansGo:
            if plotGeneNames:
                if plotDiffGeneMark:

                    interest = df[df[name_col].isin(label_points)].copy()

                    if not interest.empty:
                        def _suffix(row):
                            if row[fc_col] > fc_thr:
                                return " (↑)"
                            if row[fc_col] < -fc_thr:
                                return " (↓)"
                            return " (≈)"

                        interest["label_text"] = interest[name_col] + interest.apply(_suffix, axis=1)

                        interest_display = interest.copy()
                        if fc_clip_limit is not None:
                            interest_display[fc_col] = np.clip(interest_display[fc_col], -fc_clip_limit, fc_clip_limit)
                        # plot big black dots + text
                        _add_labels(
                            ax,
                            interest_display,         # DataFrame with label_text column (clipped for position if fc_clip_limit set)
                            ave_col,
                            fc_col,
                            "label_text",             # column to display
                            addText=True,
                            identifyRegionByGeneName=identifyRegionByGeneName,
                            region2gene=region2gene if identifyRegionByGeneName else None
                        )
                else:
                    label_df = df[df[name_col].isin(label_points)]
                    if fc_clip_limit is not None:
                        label_df = label_df.copy()
                        label_df[fc_col] = np.clip(label_df[fc_col], -fc_clip_limit, fc_clip_limit)
                    _add_labels(ax,
                                label_df,
                                ave_col,
                                fc_col,
                                name_col,
                                addText=True,
                                identifyRegionByGeneName=identifyRegionByGeneName,
                                region2gene=region2gene if identifyRegionByGeneName else None
                                )
            else:
                label_df = df[df[name_col].isin(label_points)]
                if fc_clip_limit is not None:
                    label_df = label_df.copy()
                    label_df[fc_col] = np.clip(label_df[fc_col], -fc_clip_limit, fc_clip_limit)
                _add_labels(
                        ax,
                        label_df,
                        ave_col,
                        fc_col,
                        "none",
                        addText=False,
                        identifyRegionByGeneName=identifyRegionByGeneName,
                        region2gene=region2gene if identifyRegionByGeneName else None
                    )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-abs_max_y, abs_max_y)
    ax.text(
        0.99,
        0.07,
        f"↓{len(dn):,}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        color=blue,
        fontsize=10,
    )
    ax.text(
        0.99,
        0.99,
        f"↑{len(up):,}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        color=red,
        fontsize=10,
    )

    _draw_common_frame(ax)

    def _id_to_gene(val):
        return region2gene[val] if (identifyRegionByGeneName and
                                    region2gene is not None and
                                    val in region2gene) else val

    return { _id_to_gene(x) for x in up[name_col].dropna() }, \
           { _id_to_gene(x) for x in dn[name_col].dropna() }


# -----------------------------------------------------------------------------
# grid creator
# -----------------------------------------------------------------------------
def _make_grid(
    fig_xy: Tuple[int, int],
    n_rows: int,
    n_cols: int,
    n_used: int,
):
    """
    Pre-allocate a subplot grid and hide any unused panels.

    Returns
    -------
    fig : matplotlib.figure.Figure
    axs : numpy.ndarray
        2-D array of Axes objects indexed as [row][col].
    """
    fig, axs = plt.subplots(n_rows, n_cols, figsize=fig_xy, squeeze=False)
    for j in range(n_used, n_cols * n_rows):
        r, c = divmod(j, n_cols)
        axs[r][c].axis("off")
    return fig, axs

def detectGeneName(geneName: str, labelPoints: Sequence[str] | None):
    """
    Detect if the gene name is in the list of label points.
    """
    if geneName != ".":
        namesPresent = geneName.split(",")
        for name in namesPresent:
            if name in labelPoints:
                return name
    return "discard"

# -----------------------------------------------------------------------------
# orchestrator
# -----------------------------------------------------------------------------
def generate_grids(
    inputFilesTSV: str | Path,
    outPrefix: str,
    *,
    plotsToPlot: Sequence[str],
    fcColumnName: str = "log2FC",
    significanceColumnName: str = "q.value",
    aveExprColumnName: str = "log2AveExpr",
    dataNameColumn: str = "Region",
    fcCut: float = 2.0,
    fdrCut: float = 0.05,
    numFigCol: int | None = None,
    numFigRow: int | None = None,
    figXsize: float | str = "auto",
    figYsize: float | str = "auto",
    labelPoints: Sequence[str] | None = None,
    plotGeneNames: bool = True,
    plotDiffGeneMark: bool = False,
    identifyRegionByGeneName: bool = False,
    customAbsMaxFC: float | None = None,
    customMaxP: float | None = None,
    customAbsMinAveExpr: float | None = None,
    customAbsMaxAveExpr: float | None = None,
):
    """
    Build one or two figure grids depending on plotsToPlot.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    lgr.info("Reading file list: %s", inputFilesTSV)

    io_df = pd.read_csv(inputFilesTSV, sep="\t")
    required = {"inputFile", "sampleLabel"}
    if not required.issubset(io_df.columns):
        lgr.critical("TSV must contain inputFile and sampleLabel columns.")
        raise ValueError("Incorrect TSV structure.")

    paths = [Path(p) for p in io_df["inputFile"]]
    labels = io_df["sampleLabel"].tolist()
    n_pan = len(paths)

    # geometry
    if numFigCol is None and numFigRow is None:
        numFigCol = math.ceil(math.sqrt(n_pan))
        numFigRow = math.ceil(n_pan / numFigCol)
    elif numFigCol is None:
        numFigCol = math.ceil(n_pan / numFigRow)
    elif numFigRow is None:
        numFigRow = math.ceil(n_pan / numFigCol)

    if figXsize == "auto":
        figXsize = numFigCol * 3
    if figYsize == "auto":
        figYsize = numFigRow * 3
    fig_xy = (figXsize, figYsize)

    volc_gmt_lines, ma_gmt_lines = [], []
    def _clean(label: str) -> str:
        """Convert any label to a GMT-safe identifier."""
        return re.sub(r'[^A-Za-z0-9]', '_', label)

    # Volcano grid
    if "volcano" in plotsToPlot:
        lgr.info("Generating Volcano grid")
        abs_x_v, abs_y_v = _scan_limits_volcano(
            paths, fcColumnName, significanceColumnName,
            custom_abs_max_fc=customAbsMaxFC,
            custom_max_p=customMaxP,
        )
        fig, axs = _make_grid(fig_xy, numFigRow, numFigCol, n_pan)
        for i, (fp, lbl) in enumerate(zip(paths, labels)):
            r, c = divmod(i, numFigCol)
            if identifyRegionByGeneName:
                geneAnnoColName = "Gene_2kb"
                if geneAnnoColName not in pd.read_csv(fp, sep="\t", nrows=1).columns:
                    lgr.critical(f"Column '{geneAnnoColName}' not found in {fp}. - Please check the input file or refrain from using the '--identifyRegionByGeneName' flag.")
                    raise ValueError(f"Column '{geneAnnoColName}' not found in {fp}.")
                df = pd.read_csv(
                    fp,
                    sep="\t",
                    usecols=[dataNameColumn, fcColumnName, significanceColumnName, geneAnnoColName],
                )
                df['interest'] = df[geneAnnoColName].apply(lambda x: detectGeneName(x, labelPoints))
                dfSub = df[df['interest'] != "discard"].copy()
                passedLabelPoints = set(dfSub[dataNameColumn].tolist())
                passedLabelGenes = set(dfSub['interest'].tolist()) ### Note that here we simplufy this a bit, because there is a possibility that the same point was labelled with two different genes of interest, but we only keep the first one basically.
                dfSub.to_csv(f"{outPrefix}.volcanoGrid.{lbl}.labelPoints.tsv", sep="\t", index=False)
                lgr.info(f"Identified {len(passedLabelPoints)} regions annotated with {len(passedLabelGenes)} out of {len(labelPoints)} genes of interest in the data frame. The label points were saved to {outPrefix}.volcanoGrid.{lbl}.labelPoints.tsv")
                region2gene = pd.Series(dfSub['interest'].values, index=dfSub[dataNameColumn]).to_dict()
                df.drop(columns=['interest'], inplace=True)
                
            else:
                df = pd.read_csv(
                    fp,
                    sep="\t",
                    usecols=[dataNameColumn, fcColumnName, significanceColumnName],
                )
                passedLabelPoints = labelPoints

            up_set, dn_set = _plot_single_volcano(
                df,
                axs[r][c],
                fc_col=fcColumnName,
                sig_col=significanceColumnName,
                name_col=dataNameColumn,
                fc_cut=fcCut,
                fdr_cut=fdrCut,
                abs_max_x=abs_x_v,
                abs_max_y=abs_y_v,
                label_points=passedLabelPoints,
                plotGeneNames=plotGeneNames,
                plotDiffGeneMark=plotDiffGeneMark,
                identifyRegionByGeneName=identifyRegionByGeneName,
                region2gene=region2gene if identifyRegionByGeneName else None,
                fc_clip_limit=customAbsMaxFC,
            )

            clean_lbl = _clean(lbl)
            if up_set:
                volc_gmt_lines.append(
                    f"{clean_lbl}.up.volcano\t{clean_lbl}.up.volcano\t" +
                    "\t".join(sorted(up_set))
                )
            else:
                lgr.info(f"[{lbl}] no up-regulated genes - skipped.")
            if dn_set:
                volc_gmt_lines.append(
                    f"{clean_lbl}.down.volcano\t{clean_lbl}.down.volcano\t" +
                    "\t".join(sorted(dn_set))
                )
            else:
                lgr.info(f"[{lbl}] no down-regulated genes - skipped.")

            axs[r][c].set_title(lbl, fontsize=8)
        plt.tight_layout()
        fig.savefig(f"{outPrefix}.volcanoGrid.png", dpi=300, bbox_inches="tight")
        fig.savefig(f"{outPrefix}.volcanoGrid.pdf", dpi=300, bbox_inches="tight")
        plt.close(fig)
        lgr.info("Volcano grid saved.")

        if volc_gmt_lines:
            gmt_path = f"{outPrefix}.volcanoGrid.gmt"
            with open(gmt_path, "w") as fh:
                fh.write("\n".join(volc_gmt_lines) + "\n")

            # save the GMT also as text file (this is to avoid stupid Apple bug with reading in the files such as GMT, created "online" and being unsafe)
            gmt_txt_path = f"{outPrefix}.volcanoGrid.gmt.txt"
            with open(gmt_txt_path, "w") as fh:
                fh.write("\n".join(volc_gmt_lines) + "\n")
            lgr.info("Volcano GMT[.txt] written -> %s", gmt_path)

    # MA grid
    if "ma" in plotsToPlot:
        lgr.info("Generating MA grid")
        abs_y_m, (x_min, x_max) = _scan_limits_ma(
            paths, fcColumnName, aveExprColumnName,
            custom_abs_max_fc=customAbsMaxFC,
            custom_ave_min=customAbsMinAveExpr,
            custom_ave_max=customAbsMaxAveExpr,
        )
        fig, axs = _make_grid(fig_xy, numFigRow, numFigCol, n_pan)
        for i, (fp, lbl) in enumerate(zip(paths, labels)):
            r, c = divmod(i, numFigCol)
            if identifyRegionByGeneName:
                geneAnnoColName = "Gene_2kb"
                if geneAnnoColName not in pd.read_csv(fp, sep="\t", nrows=1).columns:
                    lgr.critical(f"Column '{geneAnnoColName}' not found in {fp}. - Please check the input file or refrain from using the '--identifyRegionByGeneName' flag.")
                    raise ValueError(f"Column '{geneAnnoColName}' not found in {fp}.")
                df = pd.read_csv(
                    fp,
                    sep="\t",
                    usecols=[dataNameColumn, fcColumnName, aveExprColumnName, geneAnnoColName],
                )
                df['interest'] = df[geneAnnoColName].apply(lambda x: detectGeneName(x, labelPoints))
                dfSub = df[df['interest'] != "discard"].copy()
                passedLabelPoints = set(dfSub[dataNameColumn].tolist())
                passedLabelGenes = set(dfSub['interest'].tolist()) ### Note that here we simplufy this a bit, because there is a possibility that the same point was labelled with two different genes of interest, but we only keep the first one basically.
                dfSub.to_csv(f"{outPrefix}.maGrid.{lbl}.labelPoints.tsv", sep="\t", index=False)
                lgr.info(f"Identified {len(passedLabelPoints)} regions annotated with {len(passedLabelGenes)} out of {len(labelPoints)} genes of interest in the data frame. The label points were saved to {outPrefix}.maGrid.{lbl}.labelPoints.tsv")
                region2gene = pd.Series(dfSub['interest'].values, index=dfSub[dataNameColumn]).to_dict()
                df.drop(columns=['interest'], inplace=True)
                
            else:
                df = pd.read_csv(
                    fp,
                    sep="\t",
                    usecols=[dataNameColumn, fcColumnName, aveExprColumnName],
                )
                passedLabelPoints = labelPoints
            
            up_set, dn_set = _plot_single_ma(
                df,
                axs[r][c],
                fc_col=fcColumnName,
                ave_col=aveExprColumnName,
                name_col=dataNameColumn,
                fc_cut=fcCut,
                abs_max_y=abs_y_m,
                x_min=x_min,
                x_max=x_max,
                label_points=passedLabelPoints,
                plotGeneNames=plotGeneNames,
                plotDiffGeneMark=plotDiffGeneMark,
                identifyRegionByGeneName=identifyRegionByGeneName,
                region2gene=region2gene if identifyRegionByGeneName else None,
                fc_clip_limit=customAbsMaxFC,
            )

            clean_lbl = _clean(lbl)
            if up_set:
                ma_gmt_lines.append(
                    f"{clean_lbl}.up.ma\t{clean_lbl}.up.ma\t" +
                    "\t".join(sorted(up_set))
                )
            else:
                lgr.info(f"[{lbl}] no up-regulated genes - skipped.")
            if dn_set:
                ma_gmt_lines.append(
                    f"{clean_lbl}.down.ma\t{clean_lbl}.down.ma\t" +
                    "\t".join(sorted(dn_set))
                )
            else:
                lgr.info(f"[{lbl}] no down-regulated genes - skipped.")
            
            axs[r][c].set_title(lbl, fontsize=11)
        plt.tight_layout()
        fig.savefig(f"{outPrefix}.MAgrid.png", dpi=300, bbox_inches="tight")
        fig.savefig(f"{outPrefix}.MAgrid.pdf", dpi=300, bbox_inches="tight")
        plt.close(fig)
        lgr.info("MA grid saved.")

        if ma_gmt_lines:
            gmt_path = f"{outPrefix}.MAgrid.gmt"
            with open(gmt_path, "w") as fh:
                fh.write("\n".join(ma_gmt_lines) + "\n")
            
            # save the GMT also as text file (this is to avoid stupid Apple bug with reading in the files such as GMT, created "online" and being unsafe)
            gmt_txt_path = f"{outPrefix}.MAgrid.gmt.txt"
            with open(gmt_txt_path, "w") as fh:
                fh.write("\n".join(ma_gmt_lines) + "\n")
            
            lgr.info("MA GMT[.txt] written -> %s", gmt_path)
    else:
        lgr.info("MA grid was not requested, skipping.")

    lgr.info("Finished.")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main():
    import argparse
    import textwrap

    def _fc_cut_arg_type(value: str) -> float:
        """
        Parse --fcCut and reject values < 1 before any heavy imports or I/O.
        For log2-named fold-change columns the code uses log2(fcCut); fcCut < 1
        would make that threshold negative, which is invalid for a magnitude cutoff.
        """
        try:
            x = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"fcCut must be a number, got {value!r}."
            ) from exc
        if x < 1:
            raise argparse.ArgumentTypeError(
                "fcCut must be >= 1. Values below 1 become negative after "
                "log2(fcCut) when the fold-change column name contains 'log2' "
                "(e.g. log2FC), which is invalid for a magnitude threshold and "
                "breaks fold-change filtering."
            )
        return x

    configure_logging()

    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    lgr.info("Command: python %s", " ".join(str(a) for a in os.sys.argv))
    lgr.info("Working directory: %s", os.getcwd())

    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Draw Volcano and/or MA grids from many differential result tables.",
        epilog=textwrap.dedent(
            """
            Example
            -------
            python volcano_grid.py inputs.tsv outPrefix \\
                --plotsToPlot volcano,ma \\
                --labelPoints FXN,MYC
            """
        ),
    )
    ap.add_argument(
        "tsv",
        help="Two-column TSV with inputFile and sampleLabel (required).",
    )
    ap.add_argument(
        "prefix",
        help="Output file prefix, no extension (required).",
    )
    ap.add_argument(
        "--cols",
        type=int,
        metavar="N",
        help=(
            "Number of subplot columns. Default: unset (chosen with --rows from the "
            "number of panels; roughly sqrt(n) columns if both omitted)."
        ),
    )
    ap.add_argument(
        "--rows",
        type=int,
        metavar="N",
        help=(
            "Number of subplot rows. Default: unset (chosen with --cols from the "
            "number of panels; roughly sqrt(n) rows if both omitted)."
        ),
    )

    # columns and thresholds
    ap.add_argument(
        "--fcCol",
        default="log2FC",
        help="Fold-change column name. Default: %(default)s.",
    )
    ap.add_argument(
        "--sigCol",
        default="q.value",
        help="P/Q/FDR column for Volcano plots. Default: %(default)s.",
    )
    ap.add_argument(
        "--aveExprCol",
        default="log2AveExpr",
        help=(
            "Average-expression column for MA plots. Set to 'ignore' to skip MA even "
            "if listed in --plotsToPlot. Default: %(default)s."
        ),
    )
    ap.add_argument(
        "--nameCol",
        default="Region",
        help="Feature / region ID column. Default: %(default)s.",
    )
    ap.add_argument(
        "--fcCut",
        type=_fc_cut_arg_type,
        default=2.0,
        help=(
            "Fold-change cutoff in linear multiplicative space (2 = twofold); "
            "must be >= 1 (values below 1 are rejected; for log2 columns they would "
            "yield a negative log2(fcCut) threshold). "
            "If --fcCol's name contains 'log2' (case-insensitive, e.g. log2FC), values "
            "in the table are compared to log2(fcCut) and vertical guide lines are drawn "
            "at ±log2(fcCut) on that axis (e.g. fcCut=2 → ±1 on log2FC; fcCut=1 → 0). "
            "If the column name does not contain 'log2', fcCut is used unchanged on the "
            "column's native scale. Default: %(default)s."
        ),
    )
    ap.add_argument(
        "--fdrCut",
        type=float,
        default=0.05,
        help=(
            "Significance cutoff on the same scale as --sigCol in the input tables "
            "(raw q-value / FDR / p-value, e.g. 0.05—not log-transformed). "
            "Volcano only: a point is coloured as significant if sigCol < fdrCut and "
            "its fold change exceeds the fcCut rule; the dashed horizontal line is at "
            "-log10(fdrCut) because the y-axis shows -log10(sigCol). Unused for MA plots. "
            "Default: %(default)s."
        ),
    )

    # what to plot
    ap.add_argument(
        "--plotsToPlot",
        default="volcano,ma",
        help=(
            "Comma-separated list: volcano, ma, or both. Default: %(default)s "
            "(both plot types)."
        ),
    )

    # labels
    ap.add_argument(
        "--labelPoints",
        help=(
            "Comma-separated list of feature IDs (--nameCol) to highlight. "
            "Default: unset (no highlighted points)."
        ),
    )

    # label names
    ap.add_argument(
        "--plotGeneNames",
        help=(
            "Label highlighted points with gene/region text (Yes) or only draw larger "
            "points (No). Switch to No when highlighting more than ~5 features. "
            "Default: %(default)s."
        ),
        action="store",
        type=str2bool,
        default="Yes",
    )

    ap.add_argument(
        "--plotDiffGeneMark",
        help=(
            "When Yes and --plotGeneNames is Yes, append (↑)/(↓)/(≈) to each label "
            "from differential status. Works best for a single region; many labels "
            "overlap. WARNING: not intended for dense label sets. Default: %(default)s."
        ),
        action="store",
        type=str2bool,
        default="No",
    )

    ap.add_argument(
        "--identifyRegionByGeneName",
        help=(
            "For voom2anno-style peak tables: if Yes, treat --labelPoints as gene "
            "symbols matched via the Gene_2kb (promoter) column instead of --nameCol "
            "region IDs. Default: %(default)s."
        ),
        action="store",
        type=str2bool,
        default="No",
    )

    # custom axis limits (default "auto" = data-driven); values are as displayed on the axes
    ap.add_argument(
        "--customAbsMaxFC",
        default="auto",
        help=(
            "Absolute max on the log2(FC) axis (volcano x, MA y). Use 'auto' for "
            "data-driven limits. If a number (e.g. 2), used as displayed (2 = |log2FC|≤2); "
            "points beyond are clipped. Default: %(default)s."
        ),
    )
    ap.add_argument(
        "--customMaxP",
        default="auto",
        help=(
            "Upper y limit on the volcano plot (-log10 scale of --sigCol). Use 'auto' "
            "for data-driven, or a number (e.g. 10) as shown on the axis. Default: %(default)s."
        ),
    )
    ap.add_argument(
        "--customAbsMinAveExpr",
        type=float,
        default=None,
        metavar="FLOAT",
        help=(
            "Min MA plot x-axis (average expression); overrides data-driven minimum. "
            "Default: %(default)s (data-driven when omitted)."
        ),
    )
    ap.add_argument(
        "--customAbsMaxAveExpr",
        type=float,
        default=None,
        metavar="FLOAT",
        help=(
            "Max MA plot x-axis (average expression); overrides data-driven maximum. "
            "Default: %(default)s (data-driven when omitted)."
        ),
    )

    args = ap.parse_args()
    plots_requested = [
        s.lower().strip() for s in args.plotsToPlot.split(",") if s.strip()
    ]

    label_list = (
        [s.strip() for s in args.labelPoints.split(",")]
        if args.labelPoints
        else None
    )

    ### if the aveExprCol is set to "ignore" then we will not plot the MA grid even its specified in the plotsToPlot.
    if args.aveExprCol.lower() == "ignore":
        if "ma" in plots_requested:
            lgr.warning("MA grid was requested but aveExprCol is set to 'ignore'. Removing 'ma' from plotsToPlot.")
            plots_requested.remove("ma")
        args.aveExprCol = None

    # Parse custom axis limits (values are as displayed on the axes: log2(FC) and -log10(p))
    custom_abs_max_fc = None
    if args.customAbsMaxFC.lower() != "auto":
        try:
            custom_abs_max_fc = float(args.customAbsMaxFC)
            if custom_abs_max_fc <= 0:
                lgr.critical("--customAbsMaxFC must be a positive number (axis value, e.g. 2 for log2(FC)=2).")
                raise ValueError("customAbsMaxFC must be positive")
        except ValueError as e:
            if "customAbsMaxFC" in str(e):
                raise
            lgr.critical("--customAbsMaxFC must be 'auto' or a number (axis value, e.g. 2).")
            raise

    custom_max_p = None
    if args.customMaxP.lower() != "auto":
        try:
            custom_max_p = float(args.customMaxP)
            if custom_max_p <= 0:
                lgr.critical("--customMaxP must be a positive number.")
                raise ValueError("customMaxP must be positive")
        except ValueError as e:
            if "customMaxP" in str(e):
                raise
            lgr.critical("--customMaxP must be 'auto' or a number (e.g. 10).")
            raise

    generate_grids(
        args.tsv,
        args.prefix,
        plotsToPlot=plots_requested,
        fcColumnName=args.fcCol,
        significanceColumnName=args.sigCol,
        aveExprColumnName=args.aveExprCol,
        dataNameColumn=args.nameCol,
        fcCut=args.fcCut,
        fdrCut=args.fdrCut,
        numFigCol=args.cols,
        numFigRow=args.rows,
        labelPoints=label_list,
        plotGeneNames=args.plotGeneNames,
        plotDiffGeneMark=args.plotDiffGeneMark,
        identifyRegionByGeneName=args.identifyRegionByGeneName,
        customAbsMaxFC=custom_abs_max_fc,
        customMaxP=custom_max_p,
        customAbsMinAveExpr=args.customAbsMinAveExpr,
        customAbsMaxAveExpr=args.customAbsMaxAveExpr,
    )


if __name__ == "__main__":
    main()