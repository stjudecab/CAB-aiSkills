#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `genomic-set-analysis` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Pairwise Fisher exact overlap significance for genomic-set-analysis.

Mirrors the optional module in the in-house ``IntervenePeaksCombine.py`` wrapper:
for each unordered pair of sets, build a 2x2 contingency table against a discrete
universe of size N, compute two-sided Fisher exact p-value and odds ratio, Jaccard
index, fold enrichment (observed/expected), enrichment direction, Benjamini–Hochberg
FDR, and write TSV matrices plus one seaborn clustermap per statistic.

Universe size N defaults to the analysis union (``auto`` / ``-1``): BED = merged-peak
count; GMT = unique genes across sets. A positive integer overrides N when the user
knows a true background size.

BED mode counts overlaps with ``pybedtools`` on ``*.fromMerged.bed`` files. GMT mode
uses Python set intersections.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

LOGGER = logging.getLogger(__name__)


def bhFdr(pvalues: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg FDR for a 1-d array of p-values (NaNs ignored).

    Args:
        pvalues (np.ndarray): Raw p-values; non-finite entries stay NaN in the output.

    Returns:
        np.ndarray: FDR-adjusted values aligned to ``pvalues``.
    """
    pvalues = np.asarray(pvalues, dtype=float)
    out = np.full(pvalues.shape, np.nan, dtype=float)
    valid = np.isfinite(pvalues)
    if not np.any(valid):
        return out
    p = pvalues[valid]
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / np.arange(1, n + 1, dtype=float)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0.0, 1.0)
    restored = np.empty(n, dtype=float)
    restored[order] = adj
    out[valid] = restored
    return out


def parseUniverseSpec(raw: object) -> Union[str, int]:
    """Parse ``--pairwiseSignificanceUniverse`` into ``'auto'`` or a positive int.

    Args:
        raw (object): CLI value (``auto``, ``-1``, or a positive integer string).

    Returns:
        Union[str, int]: ``'auto'`` or a positive integer.

    Raises:
        ValueError: When the value is not recognized.
    """
    text = str(raw).strip()
    if text.lower() in ("auto", "-1"):
        return "auto"
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError(
            f"Invalid pairwiseSignificanceUniverse '{raw}'. Use 'auto', '-1', or a positive integer."
        ) from exc
    if value < 1:
        raise ValueError(
            f"pairwiseSignificanceUniverse must be 'auto', '-1', or a positive integer; got {value}."
        )
    return value


def resolveUniverseN(
    universeSpec: Union[str, int, None],
    unionSize: int,
    logger: Optional[logging.Logger] = None,
) -> Tuple[int, str]:
    """Resolve Fisher/fold-enrichment population size N.

    Args:
        universeSpec: ``'auto'`` / ``-1`` / ``None`` → use ``unionSize``; else positive int.
        unionSize (int): Size of the analysis union (merged peaks or unique genes).
        logger (Optional[logging.Logger]): Optional logger for warnings.

    Returns:
        Tuple[int, str]: ``(N, source_label)`` where source is ``auto_union`` or ``manual``.
    """
    unionSize = int(unionSize)
    if universeSpec in (None, "auto", -1, "-1"):
        return unionSize, "auto_union"
    N = int(universeSpec)
    if N < 1:
        raise ValueError(f"Manual pairwise universe must be a positive integer, got {N}.")
    if N < unionSize and logger is not None:
        logger.warning(
            "Manual universe N=%d is smaller than the analysis union size=%d. "
            "Some contingency cells may be negative and Fisher/fold enrichment will be skipped "
            "for those pairs.",
            N,
            unionSize,
        )
    return N, "manual"


def pairFoldEnrichment(a: int, sizeA: int, sizeB: int, N: int) -> Tuple[float, float, str]:
    """Expected overlap and fold enrichment under independence: E = |A|*|B|/N; FE = a/E.

    Args:
        a (int): Observed intersection size.
        sizeA (int): Size of set A.
        sizeB (int): Size of set B.
        N (int): Universe size.

    Returns:
        Tuple[float, float, str]: ``(expected, fold_enrichment, direction)`` where direction is
        ``overrepresented``, ``underrepresented``, ``equal``, or ``undefined``.
    """
    if sizeA <= 0 or sizeB <= 0 or N <= 0:
        return np.nan, np.nan, "undefined"
    expected = (float(sizeA) * float(sizeB)) / float(N)
    if expected == 0:
        fe = np.inf if a > 0 else np.nan
    else:
        fe = float(a) / expected
    if not np.isfinite(fe):
        direction = "overrepresented" if a > 0 else "undefined"
    elif fe > 1.0:
        direction = "overrepresented"
    elif fe < 1.0:
        direction = "underrepresented"
    else:
        direction = "equal"
    return expected, fe, direction


def scorePairwiseOverlap(
    a: int,
    sizeA: int,
    sizeB: int,
    N: int,
    logger: Optional[logging.Logger] = None,
    labelI: Optional[str] = None,
    labelJ: Optional[str] = None,
) -> Dict[str, object]:
    """Fisher, Jaccard, and fold enrichment for one unordered pair."""
    b = sizeA - a
    c = sizeB - a
    d = N - sizeA - sizeB + a
    if min(a, b, c, d) < 0:
        if logger is not None:
            logger.warning(
                "Negative contingency cell for %s vs %s (a=%s, b=%s, c=%s, d=%s); "
                "skipping Fisher for this pair.",
                labelI,
                labelJ,
                a,
                b,
                c,
                d,
            )
        orIj, pIj = np.nan, np.nan
    else:
        orIj, pIj = fisher_exact([[a, b], [c, d]], alternative="two-sided")
    unionAb = sizeA + sizeB - a
    jac = (float(a) / unionAb) if unionAb > 0 else np.nan
    expected, foldEnr, direction = pairFoldEnrichment(a, sizeA, sizeB, N)
    return {
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "jaccard": jac,
        "odds_ratio": orIj,
        "fisher_pvalue": pIj,
        "expected_overlap": expected,
        "fold_enrichment": foldEnr,
        "enrichment_direction": direction,
    }


def _prepareJaccardForPlot(jacMat: np.ndarray) -> np.ndarray:
    """Blank the diagonal (self-Jaccard is always 1) so it does not dominate the color scale."""
    mat = np.asarray(jacMat, dtype=float).copy()
    np.fill_diagonal(mat, np.nan)
    return mat


def _prepareLog2Or(orMat: np.ndarray) -> np.ndarray:
    """log2(odds ratio) for plotting; OR clipped away from 0/inf; diagonal = 0."""
    mat = np.asarray(orMat, dtype=float).copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        finite = np.isfinite(mat) & (mat > 0)
        mat[finite] = np.clip(mat[finite], 1e-6, 1e6)
        out = np.full(mat.shape, np.nan, dtype=float)
        out[finite] = np.log2(mat[finite])
        zeroMask = np.isfinite(mat) & (mat == 0)
        out[zeroMask] = np.log2(1e-6)
        infMask = np.isposinf(mat)
        out[infMask] = np.log2(1e6)
    np.fill_diagonal(out, 0.0)
    return out


def _prepareNegLog10(pMat: np.ndarray) -> np.ndarray:
    """-log10(p or FDR) for plotting; diagonal forced to 0."""
    mat = -np.log10(np.clip(np.asarray(pMat, dtype=float), 1e-300, 1.0))
    np.fill_diagonal(mat, 0.0)
    return mat


def _writeClustermap(
    plotMat: np.ndarray,
    names: Sequence[str],
    outDir: Path,
    stem: str,
    title: str,
    cbarLabel: str,
    figsize: tuple,
    cmap: str = "viridis",
    center: Optional[float] = None,
    maskDiagonal: bool = False,
) -> None:
    """Write PDF/PNG clustermap (or heatmap fallback) for one pairwise statistic."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    n = len(names)
    plotDf = pd.DataFrame(plotMat, index=list(names), columns=list(names))
    mask = np.eye(n, dtype=bool) if maskDiagonal else None
    clusterDf = plotDf.copy()
    if maskDiagonal:
        off = plotDf.values[~np.eye(n, dtype=bool)]
        off = off[np.isfinite(off)]
        fillDiag = float(np.nanmedian(off)) if off.size else 0.0
        for i in range(n):
            clusterDf.iloc[i, i] = fillDiag
    filled = clusterDf.fillna(0.0)
    if n >= 2 and float(np.nanstd(filled.values)) > 0:
        g = sns.clustermap(
            filled,
            cmap=cmap,
            figsize=figsize,
            linewidths=0.3,
            tree_kws={"linewidths": 0.5},
            center=center,
            mask=mask,
        )
        g.ax_heatmap.set_title(title)
        if getattr(g, "ax_cbar", None) is not None:
            g.ax_cbar.set_ylabel(cbarLabel)
        elif getattr(g, "cax", None) is not None:
            g.cax.set_ylabel(cbarLabel)
        fig = g.fig
    else:
        fig, ax = plt.subplots(figsize=figsize)
        sns.heatmap(filled, cmap=cmap, ax=ax, linewidths=0.3, center=center, mask=mask)
        ax.set_title(title)
    pdfPath = outDir / f"{stem}.clustermap.pdf"
    pngPath = outDir / f"{stem}.clustermap.png"
    fig.savefig(pdfPath, bbox_inches="tight")
    fig.savefig(pngPath, dpi=150, bbox_inches="tight")
    plt.close("all")
    LOGGER.info("Pairwise clustermap written to %s and %s", pdfPath, pngPath)


def runPairwiseSignificance(
    names: Sequence[str],
    outDir: Union[str, Path],
    mode: str,
    figsize: tuple = (10, 8),
    bedFiles: Optional[Sequence[str]] = None,
    universeSize: Optional[int] = None,
    universeSpec: Union[str, int, None] = "auto",
    geneSets: Optional[Mapping[str, Sequence[str]]] = None,
) -> Optional[Path]:
    """Compute pairwise Fisher overlap significance and write TSVs + clustermaps.

    For each unordered pair of sets A and B against discrete universe of size N:

        a = |A ∩ B|,  b = |A \\ B|,  c = |B \\ A|,  d = N - |A ∪ B|

    then ``scipy.stats.fisher_exact(..., alternative='two-sided')``, Jaccard,
    fold enrichment ``a / (|A|*|B|/N)``, enrichment direction, and BH-FDR.

    Args:
        names (Sequence[str]): Set labels (matrix row/column order).
        outDir (str | Path): Destination directory (created if missing).
        mode (str): ``'bed'`` or ``'gmt'``.
        figsize (tuple): Clustermap ``(width, height)``.
        bedFiles (Optional[Sequence[str]]): ``*.fromMerged.bed`` paths (BED mode).
        universeSize (Optional[int]): Analysis-union size (merged peaks or unique genes).
        universeSpec (Union[str, int, None]): ``'auto'``/``-1`` → use ``universeSize``;
            positive int → manual background N.
        geneSets (Optional[Mapping[str, Sequence[str]]]): Label → gene list (GMT mode).

    Returns:
        Optional[Path]: ``outDir`` on success, or ``None`` if fewer than 2 sets.

    Raises:
        ValueError: On invalid mode or missing required inputs.
        ImportError: When BED mode cannot import ``pybedtools``.
    """
    namesList = list(names)
    n = len(namesList)
    if n < 2:
        LOGGER.warning("Fewer than 2 sets; skipping pairwise significance.")
        return None

    outPath = Path(outDir)
    outPath.mkdir(parents=True, exist_ok=True)

    overlap = np.zeros((n, n), dtype=float)
    jaccard = np.full((n, n), np.nan, dtype=float)
    oddsRatio = np.full((n, n), np.nan, dtype=float)
    pvalue = np.full((n, n), np.nan, dtype=float)
    foldEnrichment = np.full((n, n), np.nan, dtype=float)
    expectedOverlap = np.full((n, n), np.nan, dtype=float)
    enrichmentDirection = np.full((n, n), "", dtype=object)
    longRows: List[Dict[str, object]] = []

    if mode == "bed":
        if not bedFiles or universeSize is None:
            raise ValueError("BED pairwise significance requires bedFiles and universeSize (union).")
        if len(bedFiles) != n:
            raise ValueError("bedFiles length must match names length.")
        from pybedtools import BedTool

        bedtools = [BedTool(path) for path in bedFiles]
        sizes = np.array([len(bt) for bt in bedtools], dtype=int)
        N, NSource = resolveUniverseN(universeSpec, universeSize, LOGGER)
        LOGGER.info(
            "BED pairwise significance: %d sets, universe N=%d (%s; union size=%d).",
            n,
            N,
            NSource,
            int(universeSize),
        )
        for i in range(n):
            overlap[i, i] = sizes[i]
            jaccard[i, i] = 1.0
            enrichmentDirection[i, i] = "self"
            for j in range(i + 1, n):
                a = len(bedtools[i].intersect(bedtools[j], wa=True, u=True))
                sizeA = int(sizes[i])
                sizeB = int(sizes[j])
                scored = scorePairwiseOverlap(
                    a, sizeA, sizeB, N, logger=LOGGER, labelI=namesList[i], labelJ=namesList[j]
                )
                overlap[i, j] = overlap[j, i] = scored["a"]
                jaccard[i, j] = jaccard[j, i] = scored["jaccard"]
                oddsRatio[i, j] = oddsRatio[j, i] = scored["odds_ratio"]
                pvalue[i, j] = pvalue[j, i] = scored["fisher_pvalue"]
                foldEnrichment[i, j] = foldEnrichment[j, i] = scored["fold_enrichment"]
                expectedOverlap[i, j] = expectedOverlap[j, i] = scored["expected_overlap"]
                enrichmentDirection[i, j] = enrichmentDirection[j, i] = scored["enrichment_direction"]
                longRows.append(
                    {
                        "set_i": namesList[i],
                        "set_j": namesList[j],
                        "size_i": sizeA,
                        "size_j": sizeB,
                        "universe_N": N,
                        "universe_source": NSource,
                        "union_size": int(universeSize),
                        "a_intersection": scored["a"],
                        "b_A_only": scored["b"],
                        "c_B_only": scored["c"],
                        "d_neither": scored["d"],
                        "expected_overlap": scored["expected_overlap"],
                        "fold_enrichment": scored["fold_enrichment"],
                        "enrichment_direction": scored["enrichment_direction"],
                        "jaccard": scored["jaccard"],
                        "odds_ratio": scored["odds_ratio"],
                        "fisher_pvalue": scored["fisher_pvalue"],
                    }
                )
    elif mode == "gmt":
        if geneSets is None:
            raise ValueError("GMT pairwise significance requires geneSets.")
        setList = []
        for name in namesList:
            if name not in geneSets:
                raise ValueError(f"Gene set label '{name}' missing from geneSets.")
            setList.append(set(geneSets[name]))
        sizes = np.array([len(s) for s in setList], dtype=int)
        if universeSize is not None:
            unionSize = int(universeSize)
        else:
            universe: set = set()
            for s in setList:
                universe |= s
            unionSize = len(universe)
        N, NSource = resolveUniverseN(universeSpec, unionSize, LOGGER)
        LOGGER.info(
            "GMT pairwise significance: %d sets, universe N=%d (%s; union size=%d).",
            n,
            N,
            NSource,
            unionSize,
        )
        for i in range(n):
            overlap[i, i] = sizes[i]
            jaccard[i, i] = 1.0
            enrichmentDirection[i, i] = "self"
            for j in range(i + 1, n):
                a = len(setList[i] & setList[j])
                sizeA = int(sizes[i])
                sizeB = int(sizes[j])
                scored = scorePairwiseOverlap(
                    a, sizeA, sizeB, N, logger=LOGGER, labelI=namesList[i], labelJ=namesList[j]
                )
                overlap[i, j] = overlap[j, i] = scored["a"]
                jaccard[i, j] = jaccard[j, i] = scored["jaccard"]
                oddsRatio[i, j] = oddsRatio[j, i] = scored["odds_ratio"]
                pvalue[i, j] = pvalue[j, i] = scored["fisher_pvalue"]
                foldEnrichment[i, j] = foldEnrichment[j, i] = scored["fold_enrichment"]
                expectedOverlap[i, j] = expectedOverlap[j, i] = scored["expected_overlap"]
                enrichmentDirection[i, j] = enrichmentDirection[j, i] = scored["enrichment_direction"]
                longRows.append(
                    {
                        "set_i": namesList[i],
                        "set_j": namesList[j],
                        "size_i": sizeA,
                        "size_j": sizeB,
                        "universe_N": N,
                        "universe_source": NSource,
                        "union_size": unionSize,
                        "a_intersection": scored["a"],
                        "b_A_only": scored["b"],
                        "c_B_only": scored["c"],
                        "d_neither": scored["d"],
                        "expected_overlap": scored["expected_overlap"],
                        "fold_enrichment": scored["fold_enrichment"],
                        "enrichment_direction": scored["enrichment_direction"],
                        "jaccard": scored["jaccard"],
                        "odds_ratio": scored["odds_ratio"],
                        "fisher_pvalue": scored["fisher_pvalue"],
                    }
                )
    else:
        raise ValueError(f"mode must be 'bed' or 'gmt', got {mode!r}")

    pairPvals = np.array([row["fisher_pvalue"] for row in longRows], dtype=float)
    pairFdr = bhFdr(pairPvals)
    fdr = np.full((n, n), np.nan, dtype=float)
    for idx, row in enumerate(longRows):
        i = namesList.index(str(row["set_i"]))
        j = namesList.index(str(row["set_j"]))
        fdrIj = pairFdr[idx]
        row["fisher_fdr"] = fdrIj
        fdr[i, j] = fdr[j, i] = fdrIj

    def writeMatrix(arr: np.ndarray, path: Path, floatFormat: Optional[str] = None) -> None:
        df = pd.DataFrame(arr, index=namesList, columns=namesList)
        df.index.name = "set"
        df.to_csv(path, sep="\t", float_format=floatFormat)

    writeMatrix(overlap, outPath / "pairwise.overlap_count.tsv", floatFormat="%.0f")
    writeMatrix(expectedOverlap, outPath / "pairwise.expected_overlap.tsv")
    writeMatrix(foldEnrichment, outPath / "pairwise.fold_enrichment.tsv")
    writeMatrix(enrichmentDirection, outPath / "pairwise.enrichment_direction.tsv")
    writeMatrix(jaccard, outPath / "pairwise.jaccard.tsv")
    writeMatrix(oddsRatio, outPath / "pairwise.odds_ratio.tsv")
    writeMatrix(pvalue, outPath / "pairwise.fisher_pvalue.tsv")
    writeMatrix(fdr, outPath / "pairwise.fisher_fdr.tsv")
    longDf = pd.DataFrame(longRows)
    longPath = outPath / "pairwise.summary.long.tsv"
    longDf.to_csv(longPath, sep="\t", index=False)
    LOGGER.info("Pairwise significance long summary written to %s", longPath)

    try:
        specs = [
            (
                np.asarray(overlap, dtype=float),
                "pairwise.overlap_count",
                "Pairwise overlap count",
                "Overlap count",
                "viridis",
                None,
                False,
            ),
            (
                _prepareJaccardForPlot(jaccard),
                "pairwise.jaccard",
                "Pairwise Jaccard index (diagonal masked)",
                "Jaccard",
                "viridis",
                None,
                True,
            ),
            (
                _prepareLog2Or(oddsRatio),
                "pairwise.log2_odds_ratio",
                r"Pairwise $\log_2$ odds ratio",
                r"$\log_2$(odds ratio)",
                "RdBu_r",
                0.0,
                False,
            ),
            (
                np.asarray(foldEnrichment, dtype=float),
                "pairwise.fold_enrichment",
                "Pairwise fold enrichment (obs/exp; diagonal masked)",
                "Fold enrichment",
                "viridis",
                None,
                True,
            ),
            (
                _prepareNegLog10(pvalue),
                "pairwise.fisher_pvalue",
                r"Pairwise Fisher $p$-value ($-\log_{10}$)",
                r"$-\log_{10}$(Fisher $p$)",
                "viridis",
                None,
                False,
            ),
            (
                _prepareNegLog10(fdr),
                "pairwise.fisher_fdr",
                r"Pairwise Fisher FDR ($-\log_{10}$)",
                r"$-\log_{10}$(Fisher FDR)",
                "viridis",
                None,
                False,
            ),
        ]
        for plotMat, stem, title, cbarLabel, cmap, center, maskDiag in specs:
            _writeClustermap(
                plotMat,
                namesList,
                outPath,
                stem,
                title,
                cbarLabel,
                figsize=figsize,
                cmap=cmap,
                center=center,
                maskDiagonal=maskDiag,
            )
    except Exception as exc:
        LOGGER.warning("Could not generate pairwise significance clustermaps: %s", exc)
        LOGGER.debug(traceback.format_exc())

    LOGGER.info("Pairwise significance outputs written under %s", outPath)
    return outPath
