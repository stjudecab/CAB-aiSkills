#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: sicer_to_broadpeak.py
# Description:
# Convert SICER-style BED (10 columns) to ENCODE broadPeak (9 columns) for ChIP-R.
#########################################################################

"""Convert SICER broad-peak BED files to ENCODE broadPeak format for ChIP-R input."""

from __future__ import annotations

import argparse
import logging
import math
import os
import shlex
import sys
from pathlib import Path
from sys import argv, executable

from logging_support import configureLogging, logImportedPackageVersions, logRuntimeEnvironment

logger = logging.getLogger(__name__)


def parseSicerLine(fields: list[str], lineNumber: int, sourcePath: Path) -> list[str]:
    """Map one SICER BED row to nine broadPeak columns.

    SICER rows commonly have: chrom, start, end, name, score, strand, then three
    numeric fields and a block-length column. broadPeak requires signalValue,
    pValue, and qValue in columns 7–9 (1-based).

    Args:
        fields (list[str]): Whitespace-split line fields.
        lineNumber (int): 1-based line number for error messages.
        sourcePath (Path): Source file path for errors.

    Returns:
        list[str]: Nine broadPeak fields.

    Raises:
        ValueError: If the row has fewer than nine columns or non-finite numerics.
    """
    if len(fields) < 9:
        msg = (
            f"{sourcePath}:{lineNumber}: expected at least 9 columns for SICER BED, "
            f"found {len(fields)}"
        )
        raise ValueError(msg)

    chrom = fields[0]
    start = fields[1]
    end = fields[2]
    name = fields[3]
    score = fields[4]
    strand = fields[5] if fields[5] in (".", "+", "-") else "."

    signalRaw = fields[7] if len(fields) > 7 else fields[6]
    signalValue = float(signalRaw)
    if not math.isfinite(signalValue):
        msg = (
            f"{sourcePath}:{lineNumber}: non-finite signalValue in column 8 "
            f"({signalRaw!r})"
        )
        raise ValueError(msg)

    pValue = "0"
    qValue = "0"
    return [
        chrom,
        start,
        end,
        name,
        score,
        strand,
        signalRaw,
        pValue,
        qValue,
    ]


def convertSicerToBroadpeak(inputPath: Path, outputPath: Path) -> int:
    """Write broadPeak rows from a SICER BED file.

    Args:
        inputPath (Path): SICER BED path.
        outputPath (Path): Output broadPeak path.

    Returns:
        int: Number of data rows written.

    Raises:
        ValueError: On malformed rows or non-finite values.
        FileNotFoundError: If ``inputPath`` does not exist.
    """
    if not inputPath.is_file():
        raise FileNotFoundError(f"Input file not found: {inputPath}")

    outputPath.parent.mkdir(parents=True, exist_ok=True)
    rowCount = 0
    with inputPath.open(encoding="utf-8") as infile, outputPath.open(
        "w", encoding="utf-8"
    ) as outfile:
        for lineNumber, line in enumerate(infile, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("track") or stripped.startswith("browser"):
                continue
            fields = stripped.split()
            broad = parseSicerLine(fields, lineNumber, inputPath)
            outfile.write("\t".join(broad) + "\n")
            rowCount += 1
    return rowCount


def parseArgs(argv_override: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for SICER→broadPeak conversion.

    Args:
        argv_override (list[str] | None): Optional argv for tests.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    lgr = logging.getLogger("parseArgs")
    lgr.info("Current working directory: %s", os.getcwd())
    lgr.info("Command used to run the program: python %s", " ".join(str(x) for x in argv))

    parser = argparse.ArgumentParser(
        description="Convert SICER BED (10 columns) to ENCODE broadPeak (9 columns).",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="SICER-style BED input path.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="broadPeak output path.",
    )
    parser.add_argument(
        "--logLevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default INFO).",
    )
    if argv_override is not None:
        return parser.parse_args(argv_override)
    return parser.parse_args()


def main(argv_override: list[str] | None = None) -> int:
    """CLI entrypoint for SICER→broadPeak conversion.

    Args:
        argv_override (list[str] | None): Optional argv for tests.

    Returns:
        int: Process exit code (0 success, non-zero on failure).
    """
    args = parseArgs(argv_override)
    configureLogging(analysisPrefix=Path(__file__).stem, logLevel=args.logLevel)
    lgr = logging.getLogger("main")
    logImportedPackageVersions(lgr, ("rich",))
    logRuntimeEnvironment(lgr)
    command_used = " ".join(shlex.quote(arg) for arg in [executable] + list(argv))
    lgr.info("Command used to run script: %s", command_used)
    lgr.info("input: %s", args.input.resolve())
    lgr.info("output: %s", args.output.resolve())

    try:
        rows = convertSicerToBroadpeak(args.input.resolve(), args.output.resolve())
    except (ValueError, FileNotFoundError) as exc:
        lgr.critical("%s", exc)
        return 1

    lgr.info("Wrote %d broadPeak rows to %s", rows, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
