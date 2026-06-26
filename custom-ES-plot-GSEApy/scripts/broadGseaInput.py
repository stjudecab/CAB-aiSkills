#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < email [at] gmail DOT com >
# File Name: broadGseaInput.py
# Description:
# Load Broad Institute GSEA desktop output and render ES plots via GSEApy.
#########################################################################

"""Helpers for reading Broad GSEA desktop output and plotting enrichment scores."""

from __future__ import annotations

import inspect
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import gseapy
import matplotlib.pyplot as plt
import pandas as pd
from gseapy.base import GSEAbase


@dataclass(frozen=True)
class BroadGseaTermResult:
    """Enrichment statistics and hit indices for one Broad GSEA gene set.

    Attributes:
        term (str): Gene-set name.
        es (float): Enrichment score from Broad GSEA.
        nes (float): Normalized enrichment score from Broad GSEA.
        pval (float): Nominal p-value (NP attribute in results.edb).
        fdr (float): FDR q-value from Broad GSEA.
        fwer (float): Family-wise error rate p-value from Broad GSEA.
        hitIndices (list[int]): Zero-based hit indices along the ranked list.
    """

    term: str
    es: float
    nes: float
    pval: float
    fdr: float
    fwer: float
    hitIndices: list[int]


@dataclass
class BroadGseaContext:
    """Parsed Broad GSEA desktop output required for ES replotting.

    Attributes:
        gseaDir (Path): Root directory of the Broad GSEA run.
        resultsEdbPath (Path): Path to ``edb/results.edb``.
        rankPath (Path): Path to the collapsed ``.rnk`` file under ``edb/``.
        geneSetPath (Path): Path to ``edb/gene_sets.gmt``.
        geneList (list[str]): Ordered gene symbols from the ranked list.
        correlVector (list[float]): Ranking metric values aligned to ``geneList``.
        geneSetDict (dict[str, list[str]]): Gene-set name to member genes.
        termResults (dict[str, BroadGseaTermResult]): Per-term Broad statistics.
        reportStats (dict[str, pd.Series]): Optional rows from GSEA report TSV files.
        weight (float): GSEA weighted scoring exponent (default 1.0).
    """

    gseaDir: Path
    resultsEdbPath: Path
    rankPath: Path
    geneSetPath: Path
    geneList: list[str]
    correlVector: list[float]
    geneSetDict: dict[str, list[str]]
    termResults: dict[str, BroadGseaTermResult]
    reportStats: dict[str, pd.Series]
    weight: float


def locateBroadGseaFiles(gseaDir: Path) -> tuple[Path, Path, Path]:
    """Locate required Broad GSEA files under the ``edb/`` subdirectory.

    Args:
        gseaDir (Path): Broad GSEA desktop output directory.

    Returns:
        tuple[Path, Path, Path]: ``results.edb``, ranked ``.rnk``, and ``gene_sets.gmt``.

    Raises:
        FileNotFoundError: If ``edb/`` or any required file is missing.
    """
    edbDir = gseaDir / "edb"
    if not edbDir.is_dir():
        raise FileNotFoundError(
            "Broad GSEA output directory is missing edb/ subdirectory: {}".format(
                gseaDir
            )
        )

    resultsMatches = sorted(edbDir.glob("results.edb"))
    rankMatches = sorted(edbDir.glob("*.rnk"))
    gmtMatches = sorted(edbDir.glob("gene_sets.gmt"))

    if not resultsMatches:
        raise FileNotFoundError(
            "Could not locate edb/results.edb under Broad GSEA directory: {}".format(
                gseaDir
            )
        )
    if not rankMatches:
        raise FileNotFoundError(
            "Could not locate edb/*.rnk under Broad GSEA directory: {}".format(
                gseaDir
            )
        )
    if not gmtMatches:
        raise FileNotFoundError(
            "Could not locate edb/gene_sets.gmt under Broad GSEA directory: {}".format(
                gseaDir
            )
        )

    return resultsMatches[0], rankMatches[0], gmtMatches[0]


def parseBroadResultsEdb(resultsPath: Path) -> dict[str, BroadGseaTermResult]:
    """Parse Broad GSEA ``results.edb`` into per-term enrichment records.

    Args:
        resultsPath (Path): Path to ``edb/results.edb``.

    Returns:
        dict[str, BroadGseaTermResult]: Gene-set name to parsed enrichment data.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    tree = ET.parse(resultsPath)
    termResults: dict[str, BroadGseaTermResult] = {}

    for node in tree.getroot().findall("DTG"):
        genesetAttr = node.attrib.get("GENESET", "")
        if "#" not in genesetAttr:
            lgr.warning(
                "Skipping DTG node with unexpected GENESET attribute: {}".format(
                    genesetAttr
                )
            )
            continue

        term = genesetAttr.split("#", 1)[1]
        hitRaw = node.attrib.get("HIT_INDICES", "").split()
        hitIndices = [int(value) for value in hitRaw if value]

        termResults[term] = BroadGseaTermResult(
            term=term,
            es=float(node.attrib.get("ES")),
            nes=float(node.attrib.get("NES")),
            pval=float(node.attrib.get("NP")),
            fdr=float(node.attrib.get("FDR")),
            fwer=float(node.attrib.get("FWER")),
            hitIndices=hitIndices,
        )

    lgr.info(
        "Parsed {} gene set(s) from Broad GSEA results.edb.".format(
            len(termResults)
        )
    )
    return termResults


def loadBroadReportStats(gseaDir: Path) -> dict[str, pd.Series]:
    """Load optional per-term statistics from Broad GSEA HTML report TSV files.

    Args:
        gseaDir (Path): Broad GSEA desktop output directory.

    Returns:
        dict[str, pd.Series]: Gene-set name to report row (last file wins on duplicates).
    """
    reportStats: dict[str, pd.Series] = {}
    for pattern in ("gsea_report_for_na_pos_*.tsv", "gsea_report_for_na_neg_*.tsv"):
        for reportPath in sorted(gseaDir.glob(pattern)):
            reportFrame = pd.read_csv(reportPath, sep="\t")
            if "NAME" not in reportFrame.columns:
                continue
            for _, row in reportFrame.iterrows():
                reportStats[str(row["NAME"])] = row
    return reportStats


def inferBroadWeight(gseaDir: Path, defaultWeight: float = 1.0) -> float:
    """Infer GSEA weighted scoring exponent from the run ``.rpt`` file when present.

    Args:
        gseaDir (Path): Broad GSEA desktop output directory.
        defaultWeight (float): Fallback weight when the report is absent or ambiguous.

    Returns:
        float: Weighted score exponent for ``enrichment_score`` (typically ``1.0``).
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    rptMatches = sorted(gseaDir.glob("*.rpt"))
    if not rptMatches:
        lgr.info(
            "No .rpt file found; using default Broad GSEA weight={}.".format(
                defaultWeight
            )
        )
        return defaultWeight

    scoringScheme = None
    for rawLine in rptMatches[0].read_text(encoding="utf-8").splitlines():
        parts = rawLine.split("\t")
        if len(parts) >= 3 and parts[0] == "param" and parts[1] == "scoring_scheme":
            scoringScheme = parts[2].strip()
            break

    if scoringScheme == "weighted":
        lgr.info("Broad GSEA scoring_scheme=weighted; using weight=1.0.")
        return 1.0

    lgr.info(
        "Broad GSEA scoring_scheme={}; using default weight={}.".format(
            scoringScheme, defaultWeight
        )
    )
    return defaultWeight


def loadBroadGseaContext(gseaDir: Path, weight: float | None = None) -> BroadGseaContext:
    """Load Broad GSEA desktop output into a plotting context.

    Args:
        gseaDir (Path): Broad GSEA desktop output directory.
        weight (float | None): Optional weighted score exponent. When ``None``,
            infer from the run ``.rpt`` file or default to ``1.0``.

    Returns:
        BroadGseaContext: Parsed ranked list, gene sets, and enrichment statistics.

    Raises:
        FileNotFoundError: If required Broad GSEA files are missing.
        ValueError: If ranked list or gene-set tables are empty.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    resolvedDir = gseaDir.expanduser().resolve()
    if not resolvedDir.is_dir():
        raise FileNotFoundError(
            "Broad GSEA output directory not found: {}".format(resolvedDir)
        )

    resultsPath, rankPath, geneSetPath = locateBroadGseaFiles(resolvedDir)
    rankFrame = pd.read_csv(rankPath, sep="\t", header=None)
    if rankFrame.shape[1] < 2 or rankFrame.empty:
        raise ValueError(
            "Ranked list file must contain at least two columns (gene, score): {}".format(
                rankPath
            )
        )

    geneList = rankFrame.iloc[:, 0].astype(str).tolist()
    correlVector = rankFrame.iloc[:, 1].astype(float).tolist()
    if not all(pd.notna(value) for value in correlVector):
        raise ValueError(
            "Non-finite values detected in ranked metric column: {}".format(rankPath)
        )

    geneSetDict = gseapy.read_gmt(str(geneSetPath))
    termResults = parseBroadResultsEdb(resultsPath)
    reportStats = loadBroadReportStats(resolvedDir)
    resolvedWeight = weight if weight is not None else inferBroadWeight(resolvedDir)

    lgr.info("Loaded Broad GSEA context from {}".format(resolvedDir))
    lgr.info("  results.edb: {}".format(resultsPath.name))
    lgr.info("  ranked list: {}".format(rankPath.name))
    lgr.info("  gene sets: {}".format(geneSetPath.name))
    lgr.info("  weighted score exponent: {}".format(resolvedWeight))

    return BroadGseaContext(
        gseaDir=resolvedDir,
        resultsEdbPath=resultsPath,
        rankPath=rankPath,
        geneSetPath=geneSetPath,
        geneList=geneList,
        correlVector=correlVector,
        geneSetDict=geneSetDict,
        termResults=termResults,
        reportStats=reportStats,
        weight=resolvedWeight,
    )


def availableBroadGeneSets(context: BroadGseaContext) -> list[str]:
    """Return sorted gene-set names present in Broad GSEA ``results.edb``.

    Args:
        context (BroadGseaContext): Parsed Broad GSEA output.

    Returns:
        list[str]: Sorted unique gene-set names.
    """
    return sorted(context.termResults.keys())


def broadStatisticsMapping(
    context: BroadGseaContext,
    term: str,
) -> dict[str, Any]:
    """Build a statistics mapping for one Broad GSEA gene set.

    Args:
        context (BroadGseaContext): Parsed Broad GSEA output.
        term (str): Gene-set name.

    Returns:
        dict[str, Any]: Statistics fields aligned with GSEApy pickle output text files.

    Raises:
        KeyError: If the gene set is absent from ``results.edb``.
    """
    if term not in context.termResults:
        raise KeyError(
            "Gene set '{}' not found in Broad GSEA results.edb.".format(term)
        )

    termResult = context.termResults[term]
    stats: dict[str, Any] = {
        "Term": term,
        "ES": termResult.es,
        "NES": termResult.nes,
        "NOM p-val": termResult.pval,
        "FDR q-val": termResult.fdr,
        "FWER p-val": termResult.fwer,
    }

    reportRow = context.reportStats.get(term)
    if reportRow is not None:
        for column in ("Tag %", "Gene %", "LEADING EDGE"):
            if column in reportRow.index and pd.notna(reportRow[column]):
                stats[column] = reportRow[column]
        if "Lead_genes" not in stats and "LEADING EDGE" in stats:
            leadingEdge = str(stats["LEADING EDGE"])
            if "tags=" in leadingEdge:
                stats["Lead_genes"] = leadingEdge

    return stats


DEFAULTChipFactorTraceColors = {
    "EP300": "#8955A7",
    "CBP": "#C01788",
    "H3K27AC": "#00542F",
    "BRD4": "#8A2F04",
}
DEFAULTChipFactorTraceColorNames = {
    "EP300": "English Violet",
    "CBP": "Pansy purple",
    "H3K27AC": "Forest Green",
    "BRD4": "Seal Brown",
}
DEFAULTChipFactorTracePlotOrder = ("EP300", "CBP", "H3K27AC", "BRD4")
DEFAULTChipFactorTraceFallbackColor = "#949494"


def broadRunningScoresForTerm(context: BroadGseaContext, term: str) -> list[float]:
    """Compute the running enrichment score vector for one Broad GSEA gene set.

    Args:
        context (BroadGseaContext): Parsed Broad GSEA output.
        term (str): Gene-set name.

    Returns:
        list[float]: Running enrichment scores along the ranked gene list.

    Raises:
        KeyError: If the gene set is absent from Broad results or GMT.
    """
    if term not in context.termResults:
        raise KeyError(
            "Gene set '{}' not found in Broad GSEA results.edb.".format(term)
        )
    if term not in context.geneSetDict:
        raise KeyError(
            "Gene set '{}' not found in Broad GSEA gene_sets.gmt.".format(term)
        )

    enrichBase = GSEAbase()
    return enrichBase.enrichment_score(
        gene_list=context.geneList,
        correl_vector=context.correlVector,
        gene_set=context.geneSetDict[term],
        weight=context.weight,
        nperm=0,
    )[-1]


def normalizeChipFactorKey(factor: str) -> str:
    """Normalize a ChIP factor label for color-map lookup.

    Args:
        factor (str): Short factor label such as ``BRD4`` or ``H3K27ac``.

    Returns:
        str: Uppercase factor key used in ``DEFAULTChipFactorTraceColors``.
    """
    return factor.strip().upper()


def broadTraceColorForFactor(factor: str) -> str:
    """Return the trace-plot color hex code for one ChIP factor.

    Args:
        factor (str): Short factor label such as ``BRD4`` or ``H3K27AC``.

    Returns:
        str: Hex color from ``DEFAULTChipFactorTraceColors``, or the fallback gray.
    """
    return DEFAULTChipFactorTraceColors.get(
        normalizeChipFactorKey(factor),
        DEFAULTChipFactorTraceFallbackColor,
    )


def broadTraceColorForTerm(term: str) -> str:
    """Return the trace-plot color hex code for one gene-set name.

    Args:
        term (str): Full gene-set name.

    Returns:
        str: Hex color assigned to the parsed ChIP factor.
    """
    return broadTraceColorForFactor(shortChipFactorLabel(term))


def chipFactorTraceSortKey(factor: str) -> tuple[int, str]:
    """Return a sort key for combined trace plot factor ordering.

    Args:
        factor (str): Short ChIP factor label.

    Returns:
        tuple[int, str]: Primary index from ``DEFAULTChipFactorTracePlotOrder``,
            then uppercase factor name for stable tie-breaking.
    """
    normalized = normalizeChipFactorKey(factor)
    try:
        orderIndex = DEFAULTChipFactorTracePlotOrder.index(normalized)
    except ValueError:
        orderIndex = len(DEFAULTChipFactorTracePlotOrder)
    return orderIndex, normalized


def sortBroadTermsForCombinedTrace(terms: Sequence[str]) -> list[str]:
    """Sort gene sets for combined trace plots by ChIP factor display order.

    Order is ``EP300``, ``CBP``, ``H3K27AC``, ``BRD4``; unknown factors sort last.

    Args:
        terms (Sequence[str]): Gene-set names to order.

    Returns:
        list[str]: Sorted gene-set names.
    """
    return sorted(terms, key=lambda term: chipFactorTraceSortKey(shortChipFactorLabel(term)))


def writeCombinedTraceColorMap(outputDir: Path, terms: Sequence[str]) -> tuple[Path, Path]:
    """Write factor and gene-set color assignments for combined trace plots.

    Args:
        outputDir (Path): Run output directory.
        terms (Sequence[str]): Gene-set names included in combined trace plots.

    Returns:
        tuple[Path, Path]: Paths to the factor palette TSV and gene-set color TSV.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    outputDir.mkdir(parents=True, exist_ok=True)

    factorMapPath = outputDir / "combined_trace_color_map.tsv"
    factorRows = [
        {
            "plot_order": plotOrder + 1,
            "chip_factor": factor,
            "color_name": DEFAULTChipFactorTraceColorNames.get(factor, ""),
            "color_hex": DEFAULTChipFactorTraceColors[factor],
        }
        for plotOrder, factor in enumerate(DEFAULTChipFactorTracePlotOrder)
        if factor in DEFAULTChipFactorTraceColors
    ]
    pd.DataFrame(factorRows).to_csv(factorMapPath, sep="\t", index=False)

    geneSetMapPath = outputDir / "combined_trace_gene_set_colors.tsv"
    geneSetRows = [
        {
            "gene_set": term,
            "chip_factor": shortChipFactorLabel(term),
            "plot_order": chipFactorTraceSortKey(shortChipFactorLabel(term))[0] + 1,
            "color_name": DEFAULTChipFactorTraceColorNames.get(
                normalizeChipFactorKey(shortChipFactorLabel(term)),
                "",
            ),
            "color_hex": broadTraceColorForTerm(term),
        }
        for term in sortBroadTermsForCombinedTrace(set(terms))
    ]
    pd.DataFrame(geneSetRows).to_csv(geneSetMapPath, sep="\t", index=False)

    lgr.info("Wrote combined trace color map: {}".format(factorMapPath))
    lgr.info("Wrote combined trace gene-set colors: {}".format(geneSetMapPath))
    return factorMapPath, geneSetMapPath


def shortChipFactorLabel(term: str) -> str:
    """Extract a short ChIP factor label from a Broad gene-set name.

    Args:
        term (str): Full gene-set name such as ``CHIP.BRD4_GM15850_...``.

    Returns:
        str: Short label such as ``BRD4`` when parseable, else the full term.
    """
    parts = term.split(".")
    if len(parts) >= 2 and parts[0] == "CHIP":
        return parts[1].split("_")[0]
    return term


def formatBroadTraceLegendLabel(context: BroadGseaContext, term: str) -> str:
    """Build a compact legend label with NES for combined trace plots.

    Args:
        context (BroadGseaContext): Parsed Broad GSEA output.
        term (str): Gene-set name.

    Returns:
        str: Legend label such as ``BRD4 (NES=2.29)`` or ``BRD4 (NES=nan)``.
    """
    termResult = context.termResults[term]
    nesValue = termResult.nes
    if pd.isna(nesValue):
        nesText = "nan"
    else:
        nesText = "{:.3f}".format(float(nesValue))
    return "{} (NES={})".format(shortChipFactorLabel(term), nesText)


def groupBroadTermsByDirectionSuffix(
    terms: Sequence[str],
) -> dict[str, list[str]]:
    """Group gene sets by trailing direction suffix such as ``TOP500_UP``.

    Args:
        terms (Sequence[str]): Resolved gene-set names.

    Returns:
        dict[str, list[str]]: Mapping from suffix to sorted gene-set names.
    """
    grouped: dict[str, list[str]] = {}
    for term in terms:
        if "." not in term:
            suffix = term
        else:
            suffix = term.rsplit(".", 1)[-1]
        grouped.setdefault(suffix, []).append(term)
    return {
        suffix: sortBroadTermsForCombinedTrace(grouped[suffix])
        for suffix in sorted(grouped.keys())
    }


def buildBroadCombinedTraceInputs(
    context: BroadGseaContext,
    terms: Sequence[str],
) -> tuple[list[str], list[str], list[list[int]], list[list[float]], list[str]]:
    """Build ordered legend labels and gseaplot2 inputs for combined trace plots.

    GSEApy stacks hit tracks bottom-to-top in list order, which is the reverse of
    the desired legend order. Inputs passed to ``gseaplot2`` are therefore reversed
    while ``orderedLegendLabels`` preserves the display order for legend repair.

    Args:
        context (BroadGseaContext): Parsed Broad GSEA output.
        terms (Sequence[str]): Gene-set names to combine.

    Returns:
        tuple[list[str], list[str], list[list[int]], list[list[float]], list[str]]:
            ``orderedLegendLabels``, ``traceLegendLabels``, ``traceHits``,
            ``traceRunningScores``, and ``traceColors``.
    """
    orderedTerms = sortBroadTermsForCombinedTrace(terms)
    orderedLegendLabels = [
        formatBroadTraceLegendLabel(context, term) for term in orderedTerms
    ]
    traceTerms = list(reversed(orderedTerms))
    traceLegendLabels = [
        formatBroadTraceLegendLabel(context, term) for term in traceTerms
    ]
    traceHits = [context.termResults[term].hitIndices for term in traceTerms]
    traceRunningScores = [broadRunningScoresForTerm(context, term) for term in traceTerms]
    traceColors = [broadTraceColorForTerm(term) for term in traceTerms]
    return (
        orderedLegendLabels,
        traceLegendLabels,
        traceHits,
        traceRunningScores,
        traceColors,
    )


def reorderCombinedTraceLegend(
    fig: plt.Figure,
    orderedLegendLabels: Sequence[str],
    legendKws: dict[str, Any],
) -> None:
    """Reorder the combined trace legend to match the display factor order.

    Args:
        fig (plt.Figure): Figure returned by ``gseapy.gseaplot2``.
        orderedLegendLabels (Sequence[str]): Desired top-to-bottom legend labels.
        legendKws (dict[str, Any]): Keyword arguments forwarded to ``ax.legend``.

    Returns:
        None.
    """
    esAxis = None
    for axis in fig.axes:
        if axis.get_legend() is not None:
            esAxis = axis
            break
    if esAxis is None:
        return

    handles, labels = esAxis.get_legend_handles_labels()
    labelToHandle = dict(zip(labels, handles))
    reorderedHandles = [
        labelToHandle[label]
        for label in orderedLegendLabels
        if label in labelToHandle
    ]
    reorderedLabels = [
        label for label in orderedLegendLabels if label in labelToHandle
    ]
    esAxis.legend(reorderedHandles, reorderedLabels, **legendKws)


def saveBroadCombinedTraceFigure(
    traceLegendLabels: Sequence[str],
    traceHits: Sequence[Sequence[int]],
    traceRunningScores: Sequence[Sequence[float]],
    traceColors: Sequence[str],
    orderedLegendLabels: Sequence[str],
    rankMetric: Sequence[float],
    figsize: tuple[float, float],
    legendKws: dict[str, Any],
    outputPath: Path,
) -> None:
    """Render, legend-correct, and save one combined trace figure.

    Args:
        traceLegendLabels (Sequence[str]): Labels in gseaplot2 stack order.
        traceHits (Sequence[Sequence[int]]): Hit indices in stack order.
        traceRunningScores (Sequence[Sequence[float]]): RES curves in stack order.
        traceColors (Sequence[str]): Colors in stack order.
        orderedLegendLabels (Sequence[str]): Desired legend order.
        rankMetric (Sequence[float]): Ranked metric vector for the background.
        figsize (tuple[float, float]): Figure size in inches.
        legendKws (dict[str, Any]): Keyword arguments forwarded to ``ax.legend``.
        outputPath (Path): Output PNG or PDF path.

    Returns:
        None.
    """
    axes = gseapy.gseaplot2(
        terms=list(traceLegendLabels),
        hits=list(traceHits),
        RESs=list(traceRunningScores),
        rank_metric=rankMetric,
        colors=list(traceColors),
        figsize=figsize,
        legend_kws=legendKws,
        ofname=None,
    )
    if not axes:
        raise RuntimeError("gseapy.gseaplot2 did not return any axes.")
    figure = axes[0].figure
    reorderCombinedTraceLegend(figure, orderedLegendLabels, legendKws)
    figure.savefig(str(outputPath), bbox_inches="tight", dpi=300)
    plt.close(figure)


def plotBroadCombinedTraceForTerms(
    context: BroadGseaContext,
    terms: Sequence[str],
    outputStem: str,
    outputDir: Path,
    figWidth: float,
    figHeight: float,
) -> tuple[Path, Path]:
    """Generate one combined multi-pathway trace plot for several gene sets.

    Uses ``gseapy.gseaplot2`` to overlay running enrichment score curves, hit
    tracks, and the ranked metric background in a single figure. Hit tracks are
    stacked bottom-to-top in factor order (BRD4 bottom, EP300 top) while the
    legend remains top-to-bottom as EP300, CBP, H3K27AC, BRD4.

    Args:
        context (BroadGseaContext): Parsed Broad GSEA output.
        terms (Sequence[str]): Gene-set names to combine (minimum one).
        outputStem (str): Output file stem without extension.
        outputDir (Path): Directory for PNG and PDF outputs.
        figWidth (float): Figure width in inches.
        figHeight (float): Figure height in inches.

    Returns:
        tuple[Path, Path]: Paths to PNG and PDF outputs.

    Raises:
        ValueError: If ``terms`` is empty.
        KeyError: If a gene set is absent from Broad results or GMT.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    if not terms:
        raise ValueError("At least one gene set is required for a combined trace plot.")

    outputDir.mkdir(parents=True, exist_ok=True)
    pngPath = outputDir / "{}.png".format(outputStem)
    pdfPath = outputDir / "{}.pdf".format(outputStem)

    (
        orderedLegendLabels,
        traceLegendLabels,
        traceHits,
        traceRunningScores,
        traceColors,
    ) = buildBroadCombinedTraceInputs(context, terms)

    traceHeight = max(figHeight, 2.5 + 0.6 * len(orderedLegendLabels))
    legendKws = {"loc": "upper center", "bbox_to_anchor": (0.5, 1.18), "ncol": 2}
    figsize = (figWidth, traceHeight)

    lgr.info(
        "Plotting combined Broad GSEA trace for {} gene set(s): {}".format(
            len(terms),
            outputStem,
        )
    )
    saveBroadCombinedTraceFigure(
        traceLegendLabels=traceLegendLabels,
        traceHits=traceHits,
        traceRunningScores=traceRunningScores,
        traceColors=traceColors,
        orderedLegendLabels=orderedLegendLabels,
        rankMetric=context.correlVector,
        figsize=figsize,
        legendKws=legendKws,
        outputPath=pngPath,
    )
    saveBroadCombinedTraceFigure(
        traceLegendLabels=traceLegendLabels,
        traceHits=traceHits,
        traceRunningScores=traceRunningScores,
        traceColors=traceColors,
        orderedLegendLabels=orderedLegendLabels,
        rankMetric=context.correlVector,
        figsize=figsize,
        legendKws=legendKws,
        outputPath=pdfPath,
    )

    lgr.info("Saved combined trace plot: {}".format(pngPath))
    lgr.info("Saved combined trace plot: {}".format(pdfPath))
    return pngPath, pdfPath


def writeBroadStatisticsText(
    outTxt: Path,
    context: BroadGseaContext,
    term: str,
) -> None:
    """Write enrichment statistics for one Broad GSEA gene set.

    Args:
        outTxt (Path): Output ``.txt`` path adjacent to plot files.
        context (BroadGseaContext): Parsed Broad GSEA output.
        term (str): Gene-set name.

    Returns:
        None.
    """
    stats = broadStatisticsMapping(context, term)
    lines = [
        "GSEA prerank enrichment statistics (Broad GSEA desktop source)",
        "Source GSEA directory: {}".format(context.gseaDir.name),
        "Source GSEA directory path: {}".format(context.gseaDir),
        "Source results.edb: {}".format(context.resultsEdbPath.name),
        "",
        "Gene set: {}".format(term),
    ]
    for column, value in stats.items():
        if column == "Term":
            continue
        lines.append("{}: {}".format(column, value))
    outTxt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plotBroadEnrichmentForTerm(
    context: BroadGseaContext,
    term: str,
    outputDir: Path,
    figWidth: float,
    figHeight: float,
) -> tuple[Path, Path, Path]:
    """Generate enrichment plot and statistics for one Broad GSEA gene set.

    Args:
        context (BroadGseaContext): Parsed Broad GSEA output.
        term (str): Gene-set name to plot.
        outputDir (Path): Directory for plot and statistics outputs.
        figWidth (float): Figure width in inches.
        figHeight (float): Figure height in inches.

    Returns:
        tuple[Path, Path, Path]: Paths to PNG, PDF, and TXT outputs.

    Raises:
        KeyError: If the gene set is absent from Broad results or GMT.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    if term not in context.termResults:
        raise KeyError(
            "Gene set '{}' not found in Broad GSEA results.edb.".format(term)
        )
    if term not in context.geneSetDict:
        raise KeyError(
            "Gene set '{}' not found in Broad GSEA gene_sets.gmt.".format(term)
        )

    outputDir.mkdir(parents=True, exist_ok=True)
    pngPath = outputDir / "{}.png".format(term)
    pdfPath = outputDir / "{}.pdf".format(term)
    txtPath = outputDir / "{}.txt".format(term)

    termResult = context.termResults[term]
    runningScores = broadRunningScoresForTerm(context, term)

    lgr.info("Plotting Broad GSEA enrichment for gene set: {}".format(term))
    gseapy.gseaplot(
        rank_metric=context.correlVector,
        term=term,
        hits=termResult.hitIndices,
        nes=termResult.nes,
        pval=termResult.pval,
        fdr=termResult.fdr,
        RES=runningScores,
        figsize=(figWidth, figHeight),
        ofname=str(pngPath),
    )
    gseapy.gseaplot(
        rank_metric=context.correlVector,
        term=term,
        hits=termResult.hitIndices,
        nes=termResult.nes,
        pval=termResult.pval,
        fdr=termResult.fdr,
        RES=runningScores,
        figsize=(figWidth, figHeight),
        ofname=str(pdfPath),
    )
    plt.close("all")

    writeBroadStatisticsText(txtPath, context, term)
    lgr.info("Saved enrichment plot: {}".format(pngPath))
    lgr.info("Saved enrichment plot: {}".format(pdfPath))
    lgr.info("Saved enrichment statistics: {}".format(txtPath))
    return pngPath, pdfPath, txtPath
