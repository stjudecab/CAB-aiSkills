#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `genomic-set-analysis` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Expression summaries (boxplots and heatmaps) for genes linked to each set/sector.

This is the portable, HPC-independent expression module of the CAB-aiSkills
``genomic-set-analysis`` skill. It intentionally decouples expression plotting from any
specific annotation schema: it consumes a GMT file that maps each set/sector name to a
gene list (produced either by ``intervene_peaks_combine.py`` in gene-set mode, or by the
``genomic-regions-annotation`` skill for BED-derived sectors), plus an expression matrix
and a per-sample condition assignment.

Gating (required by design):
    Expression plots are only generated when BOTH an expression matrix and a clearly
    defined per-sample condition mapping are supplied. The script fails fast otherwise.

Interpretation notes:
    Region-level sectors are mutually exclusive, but nearby-gene annotation happens after
    the region split, so one gene can legitimately belong to several sectors. Rows are
    therefore duplicated across sectors and renamed ``<gene>.<set>`` so every membership is
    preserved. ``exprMatrix`` values are raw (in the units named by ``--exprYaxis``, e.g.
    TPM/FPKM, linear space); ``exprMatrixLog10`` is ``log10(x + 1)``; ``exprMatrixZ`` is a
    per-gene z-score of the log10 values (each gene standardized independently).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from run_logging import (
    addReproducibilityArguments,
    appendCommandLog,
    commandLineString,
    configureLogging,
    runIdUtc,
    writeAgentArtifacts,
)

LOGGER = logging.getLogger("expression_summary")


def parseArguments() -> argparse.Namespace:
    """Parse and validate command-line arguments for the expression module.

    Returns:
        argparse.Namespace: Parsed arguments including ``figSizeParsed``.

    Raises:
        SystemExit: On argparse failure.
        ValueError: When neither ``--exprSampleCondition`` nor ``--metadataFile`` is given,
            or when the figure size is malformed.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Generate expression boxplots and heatmaps for genes linked to each set/sector. "
            "Requires an expression matrix AND a per-sample condition mapping."
        )
    )
    parser.add_argument("--geneSetsGmt", dest="geneSetsGmt", required=True,
                        help="GMT file mapping each set/sector name to its gene list.")
    parser.add_argument("--exprMatrixFile", dest="exprMatrixFile", required=True,
                        help="Tab-separated expression matrix (genes x samples).")
    parser.add_argument("--outputDir", dest="outputDir", required=True,
                        help="Output directory for expression tables and figures.")
    parser.add_argument("--exprGeneNameCol", dest="exprGeneNameCol", default="geneSymbol",
                        help="Column holding gene identifiers used to match GMT genes. Default 'geneSymbol'.")
    parser.add_argument("--exprColumnsToDrop", dest="exprColumnsToDrop", default="ignore",
                        help="Comma-separated non-sample columns to drop, or 'ignore'. Default 'ignore'.")
    parser.add_argument("--exprSampleCondition", dest="exprSampleCondition", default="ignore",
                        help=("Comma-separated condition per remaining sample column (order matters). "
                              "Provide this or --metadataFile."))
    parser.add_argument("--metadataFile", dest="metadataFile", default="ignore",
                        help=("TSV with columns 'sample' and 'condition' mapping samples to conditions. "
                              "Alternative to --exprSampleCondition."))
    parser.add_argument("--exprMinMeanExpression", dest="exprMinMeanExpression", type=float, default=1.0,
                        help="Drop genes whose mean expression across samples is <= this value. Default 1.0.")
    parser.add_argument("--exprYaxis", dest="exprYaxis", default="FPKM",
                        help="Y-axis label / units for boxplots (e.g. TPM, FPKM). Default 'FPKM'.")
    parser.add_argument("--exprPalette", dest="exprPalette", default="Set1",
                        help="Matplotlib/seaborn palette name for conditions. Default 'Set1'.")
    parser.add_argument("--exprFigSize", dest="exprFigSize", default="10,6",
                        help="Figure size 'width,height' integers. Default '10,6'.")
    parser.add_argument("--overwrite", dest="overwrite", action="store_true",
                        help="Reuse an existing output directory.")
    addReproducibilityArguments(parser)
    args = parser.parse_args()

    if args.exprSampleCondition == "ignore" and args.metadataFile == "ignore":
        raise ValueError(
            "Expression summaries require sample conditions: pass --exprSampleCondition or --metadataFile."
        )
    figParts = [p.strip() for p in str(args.exprFigSize).split(",")]
    if len(figParts) != 2 or not all(p.isdigit() for p in figParts):
        raise ValueError(f"Invalid --exprFigSize '{args.exprFigSize}'. Expected 'width,height' integers.")
    args.figSizeParsed = (int(figParts[0]), int(figParts[1]))
    return args


def readGmt(gmtPath: Path) -> "OrderedDict[str, List[str]]":
    """Read a GMT file into an ordered mapping of set name to gene list.

    Args:
        gmtPath (Path): Path to the GMT file.

    Returns:
        OrderedDict[str, List[str]]: Set name to gene list, in file order.

    Raises:
        FileNotFoundError: When the GMT file does not exist.
    """
    if not gmtPath.is_file():
        raise FileNotFoundError(f"Gene-set GMT file not found: {gmtPath}")
    mapping: "OrderedDict[str, List[str]]" = OrderedDict()
    with open(gmtPath, "r", encoding="utf-8") as handle:
        for row in handle:
            fields = row.rstrip("\n").split("\t")
            if len(fields) < 3:
                continue
            mapping[fields[0]] = [g for g in fields[2:] if g != ""]
    if len(mapping) < 1:
        raise ValueError(f"No gene sets parsed from {gmtPath}.")
    return mapping


def resolveConditions(
    args: argparse.Namespace, sampleColumns: List[str]
) -> "OrderedDict[str, str]":
    """Resolve a sample-to-condition mapping from CLI list or a metadata TSV.

    Args:
        args (argparse.Namespace): Parsed arguments.
        sampleColumns (List[str]): Sample column names in matrix order.

    Returns:
        OrderedDict[str, str]: Sample name to condition, aligned to ``sampleColumns``.

    Raises:
        ValueError: When the number of conditions does not match samples, or a sample is
            missing from the metadata file.
    """
    mapping: "OrderedDict[str, str]" = OrderedDict()
    if args.exprSampleCondition != "ignore":
        conditions = args.exprSampleCondition.split(",")
        if len(conditions) != len(sampleColumns):
            raise ValueError(
                f"--exprSampleCondition has {len(conditions)} entries but the matrix has "
                f"{len(sampleColumns)} sample columns after dropping non-sample columns."
            )
        for sample, condition in zip(sampleColumns, conditions):
            mapping[sample] = condition.strip()
        return mapping
    meta = pd.read_csv(args.metadataFile, sep="\t")
    lowered = {c.lower(): c for c in meta.columns}
    if "sample" not in lowered or "condition" not in lowered:
        raise ValueError("--metadataFile must contain 'sample' and 'condition' columns.")
    metaMap = dict(zip(meta[lowered["sample"]].astype(str), meta[lowered["condition"]].astype(str)))
    for sample in sampleColumns:
        if sample not in metaMap:
            raise ValueError(f"Sample '{sample}' from the matrix is absent from {args.metadataFile}.")
        mapping[sample] = metaMap[sample]
    return mapping


def assertFinite(frame: pd.DataFrame, label: str) -> None:
    """Fail fast if a data frame contains NaN or Inf values.

    Args:
        frame (pd.DataFrame): Numeric frame to validate.
        label (str): Human-readable name of the frame for error messages.

    Returns:
        None.

    Raises:
        ValueError: When any non-finite value is present.
    """
    values = frame.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        nRows = int((~np.isfinite(values)).any(axis=1).sum())
        raise ValueError(
            f"Non-finite (NaN/Inf) values detected in '{label}' across {nRows} row(s). "
            "Inspect the expression matrix; this pipeline does not silently coerce them."
        )


def expandByGeneSet(
    matrix: pd.DataFrame, geneSets: "OrderedDict[str, List[str]]"
) -> Tuple[pd.DataFrame, "OrderedDict[str, int]"]:
    """Expand an expression matrix to one row per gene/set membership.

    Args:
        matrix (pd.DataFrame): Expression matrix indexed by gene, columns are samples.
        geneSets (OrderedDict[str, List[str]]): Set name to gene list.

    Returns:
        Tuple[pd.DataFrame, OrderedDict[str, int]]: Expanded frame with an ``intersection``
        and ``sourceGene`` column and ``<gene>.<set>`` index, plus per-set membership counts.
    """
    tables: List[pd.DataFrame] = []
    counts: "OrderedDict[str, int]" = OrderedDict()
    present = set(matrix.index)
    for setName, genes in geneSets.items():
        matching = sorted(present.intersection(genes))
        counts[setName] = len(matching)
        if not matching:
            continue
        sub = matrix.loc[matching].copy()
        sub["sourceGene"] = sub.index
        sub["intersection"] = setName
        sub.index = [f"{gene}.{setName}" for gene in matching]
        tables.append(sub)
    if not tables:
        empty = matrix.iloc[0:0].copy()
        empty["sourceGene"] = []
        empty["intersection"] = []
        return empty, counts
    return pd.concat(tables, axis=0), counts


def plotBoxplots(
    expanded: pd.DataFrame,
    exprColumns: List[str],
    sampleToCondition: "OrderedDict[str, str]",
    prefix: str,
    outDir: Path,
    yLabel: str,
    palette: str,
    figSize: Tuple[int, int],
) -> None:
    """Write hue and no-hue boxplots of expression per set/sector.

    Args:
        expanded (pd.DataFrame): Expanded matrix with an ``intersection`` column.
        exprColumns (List[str]): Sample columns to melt.
        sampleToCondition (OrderedDict[str, str]): Sample to condition mapping.
        prefix (str): Output filename prefix (matrix flavor).
        outDir (Path): Output directory.
        yLabel (str): Y-axis label with units.
        palette (str): Seaborn palette name.
        figSize (Tuple[int, int]): Base figure size.

    Returns:
        None.
    """
    melted = expanded.melt(id_vars=["intersection"], value_vars=exprColumns,
                           var_name="Sample", value_name="Expression")
    conditions = sorted(set(sampleToCondition.values()))
    colors = sns.color_palette(palette, n_colors=len(conditions))
    conditionPalette = dict(zip(conditions, colors))
    samplePalette = {s: conditionPalette[c] for s, c in sampleToCondition.items()}

    plt.figure(figsize=figSize)
    sns.boxplot(x="intersection", y="Expression", hue="Sample", data=melted,
                showfliers=False, palette=samplePalette)
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Set / sector")
    plt.ylabel(yLabel)
    plt.title(f"Expression per set ({prefix})")
    handles = [mpatches.Patch(color=color, label=cond) for cond, color in conditionPalette.items()]
    plt.legend(handles=handles, title="Condition", bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    for ext in ("pdf", "png"):
        plt.savefig(outDir / f"{prefix}.expressionSummary.{ext}", bbox_inches="tight", dpi=300)
    plt.close()

    plt.figure(figsize=figSize)
    sns.boxplot(x="intersection", y="Expression", data=melted, showfliers=False, palette=palette)
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Set / sector")
    plt.ylabel(yLabel)
    plt.title(f"Expression per set, merged samples ({prefix})")
    plt.legend([], [], frameon=False)
    for ext in ("pdf", "png"):
        plt.savefig(outDir / f"{prefix}.expressionSummary.noHue.{ext}", bbox_inches="tight", dpi=300)
    plt.close()


def plotHeatmap(
    expanded: pd.DataFrame,
    exprColumns: List[str],
    sampleToCondition: "OrderedDict[str, str]",
    prefix: str,
    outDir: Path,
    palette: str,
) -> None:
    """Write a clustered heatmap with row colors by set and column colors by condition.

    Rows with zero variance are dropped before clustering (they carry no dendrogram signal).

    Args:
        expanded (pd.DataFrame): Expanded matrix with an ``intersection`` column.
        exprColumns (List[str]): Sample columns to plot.
        sampleToCondition (OrderedDict[str, str]): Sample to condition mapping.
        prefix (str): Output filename prefix (matrix flavor).
        outDir (Path): Output directory.
        palette (str): Seaborn palette name for conditions.

    Returns:
        None.
    """
    plotDf = expanded[exprColumns].copy()
    rowStd = plotDf.std(axis=1)
    plotDf = plotDf.loc[rowStd > 0]
    if plotDf.shape[0] < 2 or plotDf.shape[1] < 2:
        LOGGER.warning("Not enough variable rows/columns for heatmap '%s'; skipping.", prefix)
        return
    intersections = expanded.loc[plotDf.index, "intersection"]
    uniqueSectors = sorted(intersections.unique())
    sectorColors = dict(zip(uniqueSectors, sns.color_palette("Spectral", n_colors=len(uniqueSectors))))
    rowColors = intersections.map(sectorColors)

    conditions = sorted(set(sampleToCondition.values()))
    conditionColors = dict(zip(conditions, sns.color_palette(palette, n_colors=len(conditions))))
    colColors = pd.Series({s: conditionColors[sampleToCondition[s]] for s in plotDf.columns})

    grid = sns.clustermap(
        plotDf, row_cluster=True, col_cluster=False, cmap="vlag",
        row_colors=rowColors.values, col_colors=colColors.values,
        yticklabels=False, xticklabels=True, figsize=(max(plotDf.shape[1] * 0.6 + 4, 8), 10),
    )
    grid.ax_heatmap.set_xlabel("Samples")
    grid.ax_heatmap.set_ylabel("Genes (per set/sector)")
    grid.fig.suptitle(f"Expression heatmap ({prefix})", y=1.02)
    for ext in ("pdf", "png"):
        grid.savefig(outDir / f"{prefix}.expressionSummary.heatmap.{ext}", bbox_inches="tight", dpi=300)
    plt.close(grid.fig)


def main() -> None:
    """Entry point: build expression tables and plots for each gene set/sector.

    Returns:
        None.

    Raises:
        FileExistsError: When the output directory exists and ``--overwrite`` was not given.
    """
    args = parseArguments()
    runId = args.runId or runIdUtc()
    from scipy.stats import zscore

    outDir = Path(args.outputDir)
    if outDir.exists() and not args.overwrite and any(outDir.iterdir()):
        raise FileExistsError(f"Output directory not empty: {outDir}. Use --overwrite to reuse it.")
    outDir.mkdir(parents=True, exist_ok=True)
    logsDir = outDir / "logs"
    logsDir.mkdir(parents=True, exist_ok=True)
    scriptLog = logsDir / "expression_summary.log"
    commandsLog = logsDir / "commands.log"
    configureLogging(scriptLog)

    command = commandLineString()
    appendCommandLog(commandsLog, runId, command)
    LOGGER.info("Run ID: %s", runId)
    LOGGER.info("Command: %s", command)
    LOGGER.info("Working directory: %s", os.getcwd())
    LOGGER.info("Output directory: %s", outDir.resolve())

    agentRequestPath, agentWorkflowPath = writeAgentArtifacts(
        outDir,
        args,
        requestEnvVar="GENOMIC_SET_ANALYSIS_EXPRESSION_AGENT_REQUEST",
        workflowEnvVar="GENOMIC_SET_ANALYSIS_EXPRESSION_AGENT_WORKFLOW",
    )
    if agentRequestPath:
        LOGGER.info("Wrote user request: %s", agentRequestPath)
    if agentWorkflowPath:
        LOGGER.info("Wrote agent workflow: %s", agentWorkflowPath)

    geneSets = readGmt(Path(args.geneSetsGmt))
    LOGGER.info("Loaded %d gene sets from %s", len(geneSets), args.geneSetsGmt)

    matrix = pd.read_csv(args.exprMatrixFile, sep="\t", index_col=args.exprGeneNameCol)
    if args.exprColumnsToDrop != "ignore":
        toDrop = [c for c in args.exprColumnsToDrop.split(",")]
        missing = [c for c in toDrop if c not in matrix.columns]
        if missing:
            raise ValueError(f"--exprColumnsToDrop lists columns absent from the matrix: {missing}")
        matrix = matrix.drop(columns=toDrop)

    matrix = matrix.loc[~matrix.index.duplicated(keep="first")].sort_index()
    matrix = matrix.apply(pd.to_numeric, errors="coerce")
    assertFinite(matrix, "expression matrix (post-parse)")
    matrix = matrix[matrix.mean(axis=1) > args.exprMinMeanExpression].copy()
    LOGGER.info("Retained %d genes after mean-expression filter (> %s).", matrix.shape[0], args.exprMinMeanExpression)

    sampleColumns = list(matrix.columns)
    sampleToCondition = resolveConditions(args, sampleColumns)
    LOGGER.info("Resolved conditions for %d samples: %s", len(sampleToCondition), sorted(set(sampleToCondition.values())))

    matrixLog10 = np.log10(matrix + 1)
    matrixZ = pd.DataFrame(
        zscore(matrixLog10, axis=1, nan_policy="omit"),
        index=matrixLog10.index, columns=matrixLog10.columns,
    ).fillna(0.0)

    flavors: "OrderedDict[str, pd.DataFrame]" = OrderedDict(
        [("exprMatrix", matrix), ("exprMatrixLog10", matrixLog10), ("exprMatrixZ", matrixZ)]
    )
    membershipWritten = False
    for prefix, frame in flavors.items():
        expanded, counts = expandByGeneSet(frame, geneSets)
        if not membershipWritten:
            pd.DataFrame(
                {"set": list(counts.keys()),
                 "genesInMatrix": list(counts.values()),
                 "genesInSet": [len(geneSets[k]) for k in counts.keys()]}
            ).to_csv(outDir / "geneSetMembershipCounts.tsv", sep="\t", index=False)
            membershipWritten = True
        if expanded.shape[0] == 0:
            LOGGER.warning("No matrix genes overlap any gene set for '%s'; skipping plots.", prefix)
            expanded.to_csv(outDir / f"{prefix}.expressionSummary.tsv", sep="\t", index=True)
            continue
        expanded.to_csv(outDir / f"{prefix}.expressionSummary.tsv", sep="\t", index=True)
        exprColumns = [c for c in expanded.columns if c not in ("intersection", "sourceGene")]
        plotBoxplots(expanded, exprColumns, sampleToCondition, prefix, outDir,
                     args.exprYaxis, args.exprPalette, args.figSizeParsed)
        if prefix in ("exprMatrix", "exprMatrixZ"):
            plotHeatmap(expanded, exprColumns, sampleToCondition, prefix, outDir, args.exprPalette)

    metadata = {
        "skill": "genomic-set-analysis",
        "script": "expression_summary.py",
        "run_id": runId,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "working_directory": os.getcwd(),
        "geneSetsGmt": args.geneSetsGmt,
        "exprMatrixFile": args.exprMatrixFile,
        "output_directory": outDir.resolve().as_posix(),
        "parameters": {
            "exprGeneNameCol": args.exprGeneNameCol,
            "exprColumnsToDrop": args.exprColumnsToDrop,
            "exprMinMeanExpression": args.exprMinMeanExpression,
            "exprYaxis": args.exprYaxis,
            "exprPalette": args.exprPalette,
            "figSize": args.figSizeParsed,
            "conditions": list(OrderedDict.fromkeys(sampleToCondition.values())),
        },
        "tool_versions": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "seaborn": sns.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "agent_request_file": agentRequestPath.resolve().as_posix() if agentRequestPath else None,
        "agent_workflow_file": agentWorkflowPath.resolve().as_posix() if agentWorkflowPath else None,
        "logs": {
            "expression_summary.log": scriptLog.resolve().as_posix(),
            "commands.log": commandsLog.resolve().as_posix(),
        },
    }
    with open(outDir / "run_metadata.json", "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    LOGGER.info("Done. Expression summaries under: %s", outDir)


if __name__ == "__main__":
    from skill_env import bootstrap

    bootstrap()
    main()
