#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < email [at] gmail DOT com >
# File Name: plotGseapyPrerankEnrichment.py
# Description:
# Generate GSEApy prerank enrichment plots and statistics from pre_res pickles.
#########################################################################

"""Generate GSEApy prerank enrichment plots from saved pre_res pickle files."""

from __future__ import annotations

import argparse
import inspect
import logging
import os
import pickle
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from sys import argv, executable
from typing import Iterable, Sequence

import gseapy
import matplotlib.pyplot as plt
import pandas as pd
from rich.logging import RichHandler

SCRIPTStem = Path(__file__).stem
DEFAULTFigWidth = 6.0
DEFAULTFigHeight = 7.0
GENESETListSuffixes = (".lst", ".txt")
RES2DStatColumns = [
    "Term",
    "ES",
    "NES",
    "NOM p-val",
    "FDR q-val",
    "FWER p-val",
    "Tag %",
    "Gene %",
    "Lead_genes",
]


def configureLogging(
    analysisPrefix: str = SCRIPTStem,
    logLevel: str = "INFO",
    logDir: Path | None = None,
) -> None:
    """Configure Rich console logging and a plain-text audit log file.

    Args:
        analysisPrefix (str): Base name for the log file.
        logLevel (str): Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        logDir (Path | None): Directory for the log file. Defaults to cwd.
    """
    logger = logging.getLogger()
    logger.disabled = False
    logger.handlers = []
    logger.setLevel(getattr(logging, str(logLevel).upper(), logging.INFO))

    streamhdlr = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_level=True,
        show_path=True,
    )

    logPath = (logDir or Path.cwd()) / f"{analysisPrefix}.log"
    filehdlr = logging.FileHandler(logPath)

    logger.addHandler(streamhdlr)
    logger.addHandler(filehdlr)

    level = getattr(logging, str(logLevel).upper(), logging.INFO)
    streamhdlr.setLevel(level)
    filehdlr.setLevel(level)

    lgrPlainFormat = logging.Formatter(
        "###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s"
    )
    filehdlr.setFormatter(lgrPlainFormat)


def str2bool(value: str) -> bool:
    """Parse common string representations of booleans.

    Args:
        value (str): Input value such as ``yes``, ``true``, ``0``, or ``no``.

    Returns:
        bool: Parsed boolean value.

    Raises:
        SystemExit: If the value cannot be interpreted as a boolean.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    normalized = str(value).lower()
    if normalized in ("yes", "true", "t", "y", "1"):
        return True
    if normalized in ("no", "false", "f", "n", "0"):
        return False
    lgr.critical(
        "Unrecognized parameter was set for '{}'. Program was aborted.".format(value)
    )
    raise SystemExit(1)


def utcRunId() -> str:
    """Return a UTC timestamp run ID in ``YYYYMMDDTHHMMSSZ`` format.

    Returns:
        str: Timestamp-based run identifier.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def loadPreRes(pklPath: Path):
    """Load a GSEApy ``Prerank`` ``pre_res`` object from a pickle file.

    Args:
        pklPath (Path): Path to the input ``.pkl`` file.

    Returns:
        gseapy.gsea.Prerank: Deserialized prerank result object.

    Raises:
        FileNotFoundError: If the pickle file does not exist.
        ValueError: If the deserialized object has no gene-set results.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    if not pklPath.is_file():
        raise FileNotFoundError(
            "Input pickle file not found: {} (expected a GSEApy pre_res .pkl)".format(
                pklPath
            )
        )

    with pklPath.open("rb") as handle:
        preRes = pickle.load(handle)

    lgr.info("Loaded pre_res object from {}".format(pklPath))
    lgr.info("Deserialized object type: {}".format(type(preRes).__name__))
    return preRes


def availableGeneSets(preRes) -> list[str]:
    """Return sorted gene-set names present in a ``pre_res`` object.

    Args:
        preRes: GSEApy ``Prerank`` object loaded from pickle.

    Returns:
        list[str]: Sorted unique gene-set names with prerank data.

    Raises:
        ValueError: If no gene-set names can be resolved from the object.
    """
    if getattr(preRes, "res2d", None) is not None and not preRes.res2d.empty:
        terms = preRes.res2d["Term"].astype(str).tolist()
    elif getattr(preRes, "gmt", None):
        terms = [str(term) for term in preRes.gmt.keys()]
    elif getattr(preRes, "results", None):
        terms = [str(term) for term in preRes.results.keys()]
    else:
        raise ValueError(
            "Could not resolve gene-set names from pre_res object "
            "(missing res2d, gmt, and results attributes)."
        )

    return sorted(set(terms))


def readGeneSetListFile(listPath: Path) -> list[str]:
    """Read gene-set names or patterns from a ``.lst`` or ``.txt`` file.

    Args:
        listPath (Path): Path to a list file with one gene-set spec per line.

    Returns:
        list[str]: Non-empty, non-comment lines from the file.

    Raises:
        ValueError: If the file extension is not ``.lst`` or ``.txt``.
    """
    if listPath.suffix.lower() not in GENESETListSuffixes:
        raise ValueError(
            "Gene-set list file must have a .lst or .txt extension: {}".format(
                listPath
            )
        )

    specs: list[str] = []
    for rawLine in listPath.read_text(encoding="utf-8").splitlines():
        line = rawLine.strip()
        if not line or line.startswith("#"):
            continue
        specs.append(line)
    return specs


def resolveGeneSetSpec(
    spec: str,
    available: Sequence[str],
) -> tuple[list[str], bool]:
    """Resolve one gene-set specification to concrete gene-set names.

    Resolution order:
    1. Exact name match against available gene sets.
    2. Regular-expression match against available gene sets.

    Args:
        spec (str): Gene-set name, ``allGeneSets``, or regex pattern.
        available (Sequence[str]): Gene sets present in the input pickle.

    Returns:
        tuple[list[str], bool]: Matched gene-set names and whether the spec matched.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    cleaned = spec.strip()
    if not cleaned:
        return [], False

    if cleaned == "allGeneSets":
        lgr.info(
            "Gene-set spec 'allGeneSets' selected {} available gene sets.".format(
                len(available)
            )
        )
        return list(available), True

    if cleaned in available:
        return [cleaned], True

    try:
        pattern = re.compile(cleaned)
    except re.error as exc:
        lgr.warning(
            "Gene-set spec '{}' is not an exact match and is not a valid regex: {}".format(
                cleaned, exc
            )
        )
        return [], False

    matched = sorted(term for term in available if pattern.search(term))
    if matched:
        lgr.info(
            "Gene-set regex '{}' matched {} gene set(s).".format(
                cleaned, len(matched)
            )
        )
        return matched, True

    lgr.warning(
        "Requested gene set '{}' was not found in the input pickle.".format(cleaned)
    )
    return [], False


def resolveGeneSetNames(
    geneSetNameArg: str,
    available: Sequence[str],
) -> tuple[list[str], int]:
    """Resolve ``--geneSetName`` into concrete gene-set names to plot.

    Supported forms:
    - Exact gene-set name
    - Comma-separated names and/or regex patterns
    - Path to a ``.lst`` or ``.txt`` file with one spec per line
    - ``allGeneSets`` to plot every available gene set

    Args:
        geneSetNameArg (str): Raw ``--geneSetName`` argument value.
        available (Sequence[str]): Gene sets present in the input pickle.

    Returns:
        tuple[list[str], int]: Unique gene-set names to plot and the count of
            specifications that matched nothing.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    candidatePath = Path(geneSetNameArg)
    if candidatePath.is_file():
        lgr.info("Reading gene-set specs from list file: {}".format(candidatePath))
        specs = readGeneSetListFile(candidatePath)
    elif geneSetNameArg.strip() == "allGeneSets":
        specs = ["allGeneSets"]
    else:
        specs = [part.strip() for part in geneSetNameArg.split(",") if part.strip()]

    resolved: list[str] = []
    seen: set[str] = set()
    missingCount = 0

    for spec in specs:
        matchedTerms, found = resolveGeneSetSpec(spec, available)
        if not found:
            missingCount += 1
            continue
        for term in matchedTerms:
            if term not in seen:
                seen.add(term)
                resolved.append(term)

    if missingCount:
        lgr.warning(
            "{} gene-set specification(s) did not match any available gene set.".format(
                missingCount
            )
        )

    lgr.info(
        "Resolved {} gene set(s) for plotting from {} specification(s).".format(
            len(resolved), len(specs)
        )
    )
    return resolved, missingCount


def defaultOutputDir(pklPath: Path, runId: str) -> Path:
    """Build the default run-scoped output directory for enrichment plots.

    Args:
        pklPath (Path): Input pickle path.
        runId (str): UTC run identifier.

    Returns:
        Path: ``plots/enrichment/<pkl_stem>/<run_id>/`` under the pickle parent.
    """
    pklStem = pklPath.name
    if pklStem.startswith("GSEApy_prerank.pre_res."):
        pklStem = pklStem[len("GSEApy_prerank.pre_res.") :]
    if pklStem.endswith(".pkl"):
        pklStem = pklStem[: -len(".pkl")]
    return pklPath.parent / "plots" / "enrichment" / pklStem / runId


def res2dRowForTerm(preRes, term: str) -> pd.Series:
    """Return the ``res2d`` statistics row for one gene set.

    Args:
        preRes: GSEApy ``Prerank`` object loaded from pickle.
        term (str): Gene-set name.

    Returns:
        pd.Series: Matching statistics row.

    Raises:
        KeyError: If the gene set is absent from ``res2d``.
    """
    if getattr(preRes, "res2d", None) is None or preRes.res2d.empty:
        raise KeyError("pre_res.res2d is empty; cannot write statistics for '{}'.".format(term))

    matches = preRes.res2d.loc[preRes.res2d["Term"].astype(str) == term]
    if matches.empty:
        raise KeyError("Gene set '{}' not found in pre_res.res2d.".format(term))
    return matches.iloc[0]


def writeStatisticsText(
    outTxt: Path,
    pklPath: Path,
    term: str,
    row: pd.Series,
) -> None:
    """Write enrichment statistics for one gene set to a plain-text file.

    Args:
        outTxt (Path): Output ``.txt`` path adjacent to plot files.
        pklPath (Path): Source pickle path recorded in the header.
        term (str): Gene-set name.
        row (pd.Series): Statistics row from ``pre_res.res2d``.
    """
    lines = [
        "GSEA prerank enrichment statistics",
        "Source pickle: {}".format(pklPath.name),
        "Source pickle path: {}".format(pklPath.resolve()),
        "",
        "Gene set: {}".format(term),
    ]
    for column in RES2DStatColumns:
        if column == "Term":
            continue
        if column in row.index:
            lines.append("{}: {}".format(column, row[column]))
    outTxt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plotEnrichmentForTerm(
    preRes,
    pklPath: Path,
    term: str,
    outputDir: Path,
    figWidth: float,
    figHeight: float,
) -> tuple[Path, Path, Path]:
    """Generate enrichment plot and statistics file for one gene set.

    Args:
        preRes: GSEApy ``Prerank`` object loaded from pickle.
        pklPath (Path): Source pickle path recorded in statistics output.
        term (str): Gene-set name to plot.
        outputDir (Path): Directory for plot and statistics outputs.
        figWidth (float): Figure width in inches.
        figHeight (float): Figure height in inches.

    Returns:
        tuple[Path, Path, Path]: Paths to PNG, PDF, and TXT outputs.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    outputDir.mkdir(parents=True, exist_ok=True)

    pngPath = outputDir / f"{term}.png"
    pdfPath = outputDir / f"{term}.pdf"
    txtPath = outputDir / f"{term}.txt"

    lgr.info("Plotting enrichment for gene set: {}".format(term))
    preRes.plot(
        terms=term,
        figsize=(figWidth, figHeight),
        ofname=str(pngPath),
    )
    plt.close("all")

    preRes.plot(
        terms=term,
        figsize=(figWidth, figHeight),
        ofname=str(pdfPath),
    )
    plt.close("all")

    row = res2dRowForTerm(preRes, term)
    writeStatisticsText(txtPath, pklPath, term, row)

    lgr.info("Saved enrichment plot: {}".format(pngPath))
    lgr.info("Saved enrichment plot: {}".format(pdfPath))
    lgr.info("Saved enrichment statistics: {}".format(txtPath))
    return pngPath, pdfPath, txtPath


def listGeneSets(
    resolvedTerms: Sequence[str],
    outputDir: Path | None = None,
) -> Path | None:
    """Log and optionally write resolved gene-set names without plotting.

    Args:
        resolvedTerms (Sequence[str]): Gene-set names resolved from ``--geneSetName``.
        outputDir (Path | None): Optional directory for ``gene_sets.list.txt``.

    Returns:
        Path | None: Path to the written list file, or ``None`` if not written.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    lgr.info("List-only mode enabled; no enrichment plots will be generated.")
    lgr.info("Resolved gene set count: {}".format(len(resolvedTerms)))
    for term in resolvedTerms:
        lgr.info("Gene set: {}".format(term))

    listPath: Path | None = None
    if outputDir is not None:
        outputDir.mkdir(parents=True, exist_ok=True)
        listPath = outputDir / "gene_sets.list.txt"
        listPath.write_text("\n".join(resolvedTerms) + "\n", encoding="utf-8")
        lgr.info("Wrote gene set list: {}".format(listPath))

    lgr.info("Listed {} gene set(s).".format(len(resolvedTerms)))
    return listPath


def writeRunMetadata(
    metadataPath: Path,
    runId: str,
    pklPath: Path,
    geneSetSpecs: str,
    plottedTerms: Iterable[str],
    missingSpecCount: int,
    listOnly: bool = False,
) -> None:
    """Persist run metadata for reproducibility.

    Args:
        metadataPath (Path): Output JSON metadata path.
        runId (str): UTC run identifier.
        pklPath (Path): Input pickle path.
        geneSetSpecs (str): Raw ``--geneSetName`` argument.
        plottedTerms (Iterable[str]): Gene sets plotted or listed.
        missingSpecCount (int): Number of unresolved gene-set specifications.
        listOnly (bool): Whether the run was list-only (no plots generated).
    """
    metadata = {
        "run_id": runId,
        "timestamp_utc": runId,
        "input_pkl": str(pklPath.resolve()),
        "gene_set_name_arg": geneSetSpecs,
        "list_only": listOnly,
        "gene_sets": list(plottedTerms),
        "missing_spec_count": missingSpecCount,
        "gseapy_version": gseapy.__version__,
    }
    if listOnly:
        metadata["listed_gene_sets"] = list(plottedTerms)
    else:
        metadata["plotted_gene_sets"] = list(plottedTerms)
    metadataPath.write_text(
        pd.Series(metadata).to_json(indent=2) + "\n",
        encoding="utf-8",
    )


def parseArgs() -> argparse.Namespace:
    """Parse command-line arguments for enrichment plotting.

    Returns:
        argparse.Namespace: Parsed CLI arguments.
    """
    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    lgr.info("Current working directory: {}".format(os.getcwd()))
    lgr.info(
        "Command used to run the program: python {}".format(
            " ".join(str(x) for x in argv)
        )
    )

    parser = argparse.ArgumentParser(
        description=(
            "Generate GSEApy prerank enrichment plots and statistics from "
            "saved pre_res pickle files."
        )
    )

    requiredParams = parser.add_argument_group("REQUIRED parameters")
    requiredParams.add_argument(
        "--inPKL",
        help="Path to a GSEApy prerank pre_res pickle file (.pkl).",
        action="store",
        type=str,
        required=True,
        dest="inPKL",
    )
    requiredParams.add_argument(
        "--geneSetName",
        help=(
            "Gene set(s) to plot. Accepts an exact name, comma-separated names "
            "and/or regex patterns, a .lst/.txt file (one spec per line), "
            "'allGeneSets', or a regex such as 'SOS_peaks.*'."
        ),
        action="store",
        type=str,
        required=True,
        dest="geneSetName",
    )

    optionalParams = parser.add_argument_group("OPTIONAL parameters")
    optionalParams.add_argument(
        "--listOnly",
        help=(
            "List resolved gene sets without generating plots. Use to preview regex "
            "matches, confirm a gene set exists in the pickle, or inspect the full "
            "selection. Default=False."
        ),
        default=False,
        action="store_true",
        required=False,
        dest="listOnly",
    )
    optionalParams.add_argument(
        "--outputDir",
        help=(
            "Output directory for plots and statistics. Default: "
            "plots/enrichment/<pkl_stem>/<run_id>/ next to the input pickle."
        ),
        action="store",
        type=str,
        required=False,
        default=None,
        dest="outputDir",
    )
    optionalParams.add_argument(
        "--figWidth",
        help="Enrichment plot width in inches. Default=6.0.",
        default=DEFAULTFigWidth,
        action="store",
        type=float,
        required=False,
        dest="figWidth",
    )
    optionalParams.add_argument(
        "--figHeight",
        help="Enrichment plot height in inches. Default=7.0.",
        default=DEFAULTFigHeight,
        action="store",
        type=float,
        required=False,
        dest="figHeight",
    )
    optionalParams.add_argument(
        "--logLevel",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default=INFO.",
        default="INFO",
        action="store",
        type=str,
        required=False,
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )

    args = parser.parse_args()

    lgr.info("List the versions of imported packages:")
    lgr.info("  gseapy: {}".format(gseapy.__version__))
    lgr.info("  pandas: {}".format(pd.__version__))
    import matplotlib

    lgr.info("  matplotlib: {}".format(matplotlib.__version__))

    commandUsed = " ".join(shlex.quote(arg) for arg in [os.path.basename(executable)] + argv)
    lgr.info("Command used to run script: {}".format(commandUsed))
    lgr.info("Input pickle (--inPKL): {}".format(args.inPKL))
    lgr.info("Gene set selection (--geneSetName): {}".format(args.geneSetName))
    lgr.info("List only (--listOnly): {}".format(args.listOnly))
    lgr.info("Output directory (--outputDir): {}".format(args.outputDir))
    lgr.info("Figure width (--figWidth): {}".format(args.figWidth))
    lgr.info("Figure height (--figHeight): {}".format(args.figHeight))
    lgr.info("Logging level (--logLevel): {}".format(args.logLevel))

    return args


def main() -> None:
    """Run enrichment plotting from a GSEApy prerank pickle file."""
    configureLogging()
    args = parseArgs()
    configureLogging(logLevel=args.logLevel)

    lgr = logging.getLogger(inspect.currentframe().f_code.co_name)
    runId = utcRunId()
    pklPath = Path(args.inPKL).expanduser().resolve()

    preRes = loadPreRes(pklPath)
    available = availableGeneSets(preRes)
    lgr.info("Found {} gene set(s) in the input pickle.".format(len(available)))

    resolvedTerms, missingSpecCount = resolveGeneSetNames(args.geneSetName, available)
    if not resolvedTerms:
        lgr.error(
            "No gene sets were resolved. Check --geneSetName and the log "
            "for missing or invalid specifications."
        )
        raise SystemExit(1)

    if args.outputDir:
        outputDir = Path(args.outputDir).expanduser().resolve()
    else:
        outputDir = defaultOutputDir(pklPath, runId) if not args.listOnly else None

    if args.listOnly:
        listGeneSets(resolvedTerms, outputDir=outputDir)
        if outputDir is not None:
            metadataPath = outputDir / "run_metadata.json"
            writeRunMetadata(
                metadataPath=metadataPath,
                runId=runId,
                pklPath=pklPath,
                geneSetSpecs=args.geneSetName,
                plottedTerms=resolvedTerms,
                missingSpecCount=missingSpecCount,
                listOnly=True,
            )
            lgr.info("Saved run metadata: {}".format(metadataPath))
        lgr.info("All done, thank you!")
        return

    outputDir.mkdir(parents=True, exist_ok=True)
    lgr.info("Writing outputs to {}".format(outputDir))

    plottedTerms: list[str] = []
    for term in resolvedTerms:
        plotEnrichmentForTerm(
            preRes=preRes,
            pklPath=pklPath,
            term=term,
            outputDir=outputDir,
            figWidth=args.figWidth,
            figHeight=args.figHeight,
        )
        plottedTerms.append(term)

    metadataPath = outputDir / "run_metadata.json"
    writeRunMetadata(
        metadataPath=metadataPath,
        runId=runId,
        pklPath=pklPath,
        geneSetSpecs=args.geneSetName,
        plottedTerms=plottedTerms,
        missingSpecCount=missingSpecCount,
        listOnly=False,
    )
    lgr.info("Saved run metadata: {}".format(metadataPath))
    lgr.info("Plotted {} gene set(s).".format(len(plottedTerms)))
    lgr.info("All done, thank you!")


if __name__ == "__main__":
    main()
