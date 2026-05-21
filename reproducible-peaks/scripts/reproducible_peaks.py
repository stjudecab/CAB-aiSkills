#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: reproducible_peaks.py
# Description:
# Run ChIP-R on narrowPeak/broadPeak replicates with logged, reproducible parameters.
#########################################################################

"""Run ChIP-R on replicate peak files with format validation and audit logging."""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from sys import argv, executable
from typing import Literal, Sequence

from logging_support import (
    configureLogging,
    logImportedPackageVersions,
    logRuntimeEnvironment,
)
from sicer_to_broadpeak import convertSicerToBroadpeak

logger = logging.getLogger(__name__)

PeakFormat = Literal["narrowPeak", "broadPeak", "sicerBed", "unknown"]
CallingStrategy = Literal[
    "withControl",
    "noControl",
    "broadPeak",
    "sicer",
    "auto",
]

REPLICATE_PATTERNS = (
    re.compile(r"(?:^|[._-])rep(?:licate)?[_-]?(\d+)", re.IGNORECASE),
    re.compile(r"(?:^|[._-])r(\d+)(?:[._-]|$)", re.IGNORECASE),
)


@dataclass
class PeakFileInfo:
    """Metadata for one peak input file.

    Attributes:
        path (Path): Absolute path to the peak file.
        peakFormat (PeakFormat): Detected ENCODE/SICER format.
        callingStrategy (CallingStrategy): Inferred MACS2/SICER calling mode.
    """

    path: Path
    peakFormat: PeakFormat
    callingStrategy: CallingStrategy


def utcRunId() -> str:
    """Return a UTC timestamp run ID.

    Returns:
        str: Run ID in ``YYYYMMDDTHHMMSSZ`` format.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def defaultMinEntries(replicateCount: int) -> int:
    """Compute default ChIP-R ``-m`` (minentries) from replicate count.

    For two or more replicates, use ``n - 1`` unless the user overrides. For a
    single file, ChIP-R still accepts ``-m 1`` (tool default).

    Args:
        replicateCount (int): Number of replicate peak files in this run.

    Returns:
        int: Minimum entries for ChIP-R ``-m``.
    """
    if replicateCount >= 2:
        return replicateCount - 1
    return 1


def detectPeakFormat(path: Path, sampleLines: int = 5) -> PeakFormat:
    """Detect narrowPeak, broadPeak, or SICER-style BED from file content and name.

    Args:
        path (Path): Peak file path.
        sampleLines (int): Number of non-header lines to inspect.

    Returns:
        PeakFormat: Detected format label.
    """
    nameLower = path.name.lower()
    if ".sicer." in nameLower or nameLower.endswith(".sicer.bed"):
        return "sicerBed"

    dataRows: list[list[str]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("track") or stripped.startswith("browser"):
                continue
            dataRows.append(stripped.split())
            if len(dataRows) >= sampleLines:
                break

    if not dataRows:
        return "unknown"

    columnCounts = {len(row) for row in dataRows}
    if columnCounts == {10}:
        if ".narrowpeak" in nameLower or ".narrowpeak.gz" in nameLower:
            return "narrowPeak"
        if ".broadpeak" in nameLower:
            return "broadPeak"
        if any("dom_" in row[3] for row in dataRows if len(row) > 3):
            return "sicerBed"
        return "narrowPeak"
    if columnCounts == {9}:
        return "broadPeak"
    return "unknown"


def inferCallingStrategy(paths: Sequence[Path], peakFormat: PeakFormat) -> CallingStrategy:
    """Infer MACS2/SICER calling strategy from filenames and format.

    Args:
        paths (Sequence[Path]): Input peak paths for one reproducibility set.
        peakFormat (PeakFormat): Format detected on the first file.

    Returns:
        CallingStrategy: Strategy label for rank-method and documentation.
    """
    if peakFormat == "sicerBed":
        return "sicer"
    if peakFormat == "broadPeak":
        return "broadPeak"
    if any("noc_" in p.name.lower() for p in paths):
        return "noControl"
    return "withControl"


def replicateIdsFromNames(paths: Sequence[Path]) -> list[str]:
    """Extract replicate id tokens from file names for sanity checks.

    Args:
        paths (Sequence[Path]): Input paths.

    Returns:
        list[str]: Replicate id strings (empty string when not matched).
    """
    ids: list[str] = []
    for path in paths:
        matched = ""
        for pattern in REPLICATE_PATTERNS:
            hit = pattern.search(path.stem)
            if hit:
                matched = hit.group(1)
                break
        ids.append(matched)
    return ids


def warnReplicateCollisions(paths: Sequence[Path], lgr: logging.Logger) -> None:
    """Log warnings when replicate ids repeat (possible mixed conditions).

    Args:
        paths (Sequence[Path]): Input paths.
        lgr (logging.Logger): Logger instance.

    Returns:
        None.
    """
    repIds = replicateIdsFromNames(paths)
    if not any(repIds):
        lgr.info(
            "No replicate tokens (rep/replicate/Rn) detected in file names; "
            "verify all inputs belong to one condition."
        )
        return

    seen: dict[str, list[str]] = {}
    for path, rep in zip(paths, repIds):
        if not rep:
            continue
        seen.setdefault(rep, []).append(path.name)

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        lgr.warning(
            "Duplicate replicate ids in file names (possible mixed conditions): %s",
            duplicates,
        )
        lgr.warning(
            "Confirm with the user that all listed files are one target/condition "
            "before merging replicates."
        )


def validateNumericFields(path: Path, peakFormat: PeakFormat) -> None:
    """Fail on non-finite signal/p/q columns where applicable.

    Args:
        path (Path): Peak file path.
        peakFormat (PeakFormat): Detected format.

    Raises:
        ValueError: If a required numeric field is non-finite.
    """
    if peakFormat not in ("narrowPeak", "broadPeak"):
        return

    with path.open(encoding="utf-8") as handle:
        for lineNumber, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("track"):
                continue
            fields = stripped.split()
            ncol = len(fields)
            if peakFormat == "narrowPeak" and ncol < 10:
                msg = f"{path}:{lineNumber}: narrowPeak requires 10 columns, found {ncol}"
                raise ValueError(msg)
            if peakFormat == "broadPeak" and ncol < 9:
                msg = f"{path}:{lineNumber}: broadPeak requires 9 columns, found {ncol}"
                raise ValueError(msg)
            for idx in (6, 7, 8):
                if idx >= ncol:
                    continue
                try:
                    value = float(fields[idx])
                except ValueError:
                    continue
                if not math.isfinite(value):
                    msg = (
                        f"{path}:{lineNumber}: non-finite value in column {idx + 1} "
                        f"({fields[idx]!r})"
                    )
                    raise ValueError(msg)


def resolveChiprExecutable() -> str:
    """Return the first ChIP-R CLI found on PATH.

    Returns:
        str: Executable name.

    Raises:
        FileNotFoundError: If no entrypoint is available.
    """
    for cmd in ("chipr", "chip-r", "ChIP-R"):
        if shutil.which(cmd):
            return cmd
    msg = (
        "ChIP-R not found on PATH. Install with "
        "'conda install bioconda::chip-r' or 'pip install ChIP-R'."
    )
    raise FileNotFoundError(msg)


def rankMethodForStrategy(strategy: CallingStrategy, override: str | None) -> str:
    """Choose ChIP-R ``--rankmethod`` from calling strategy.

    Args:
        strategy (CallingStrategy): Inferred or user strategy.
        override (str | None): User override when set.

    Returns:
        str: Rank method passed to ChIP-R.
    """
    if override:
        return override
    if strategy == "noControl":
        return "signalvalue"
    return "pvalue"


def buildChiprCommand(
    *,
    chiprExe: str,
    preparedInputs: Sequence[Path],
    outputPrefix: Path,
    minEntries: int,
    rankMethod: str,
    alpha: float,
    size: int,
    seed: float,
    dupHandling: str,
) -> list[str]:
    """Assemble a ChIP-R command line.

    Args:
        chiprExe (str): ChIP-R executable name.
        preparedInputs (Sequence[Path]): Input peak paths after any conversion.
        outputPrefix (Path): Output prefix (no extension) for ChIP-R ``-o``.
        minEntries (int): ``-m`` value.
        rankMethod (str): ``--rankmethod`` value.
        alpha (float): ``-a`` alpha cutoff.
        size (int): ``-s`` minimum peak size.
        seed (float): Random seed for dup handling.
        dupHandling (str): ``--duphandling`` value.

    Returns:
        list[str]: argv list for ``subprocess``.
    """
    cmd = [
        chiprExe,
        "-i",
        *[str(p) for p in preparedInputs],
        "-o",
        str(outputPrefix),
        "-m",
        str(minEntries),
        "--rankmethod",
        rankMethod,
        "--duphandling",
        dupHandling,
        "--seed",
        str(seed),
        "-a",
        str(alpha),
        "-s",
        str(size),
    ]
    return cmd


def parseArgs(argv_override: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv_override (Sequence[str] | None): Optional argv for tests.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run ChIP-R on replicate narrowPeak/broadPeak files with "
            "logged parameters and optional SICER conversion."
        ),
    )
    parser.add_argument(
        "--inputFiles",
        required=True,
        help=(
            "Comma-separated list of replicate peak files (narrowPeak, broadPeak, "
            "or SICER BED to convert)."
        ),
    )
    parser.add_argument(
        "--outputDir",
        required=True,
        type=Path,
        help="Run directory for ChIP-R outputs, logs, and metadata.",
    )
    parser.add_argument(
        "--outputPrefix",
        default="reproducible_peaks",
        help="Prefix for ChIP-R output BED files (default: reproducible_peaks).",
    )
    parser.add_argument(
        "--runId",
        default=None,
        help="UTC run id (default: generated YYYYMMDDTHHMMSSZ).",
    )
    parser.add_argument(
        "--minEntries",
        type=int,
        default=None,
        help="ChIP-R -m / minentries (default: n-1 for n>=2 replicates, else 1).",
    )
    parser.add_argument(
        "--rankMethod",
        default=None,
        choices=["pvalue", "qvalue", "signalvalue"],
        help="Override ChIP-R --rankmethod (default: inferred from peak calling).",
    )
    parser.add_argument(
        "--callingStrategy",
        default="auto",
        choices=["auto", "withControl", "noControl", "broadPeak", "sicer"],
        help="Peak-calling strategy; auto infers from names and format.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="ChIP-R -a / alpha (default 0.05).",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=20,
        help="ChIP-R -s / minimum peak size (default 20).",
    )
    parser.add_argument(
        "--seed",
        type=float,
        default=0.5,
        help="ChIP-R --seed (default 0.5).",
    )
    parser.add_argument(
        "--dupHandling",
        default="average",
        choices=["average", "random"],
        help="ChIP-R --duphandling (default average).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into an existing run directory.",
    )
    parser.add_argument(
        "--dryRun",
        action="store_true",
        help="Validate inputs and log the ChIP-R command without executing.",
    )
    parser.add_argument(
        "--logLevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default INFO).",
    )
    if argv_override is not None:
        return parser.parse_args(list(argv_override))
    return parser.parse_args()


def resolveInputPaths(spec: str) -> list[Path]:
    """Parse comma-separated peak file paths.

    Args:
        spec (str): Comma-separated paths.

    Returns:
        list[Path]: Resolved absolute paths.

    Raises:
        FileNotFoundError: If any path is missing.
    """
    paths = [Path(part.strip()).expanduser() for part in spec.split(",") if part.strip()]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        msg = "Missing input peak file(s): " + ", ".join(str(p) for p in missing)
        raise FileNotFoundError(msg)
    return [p.resolve() for p in paths]


def prepareInputs(
    infos: Sequence[PeakFileInfo],
    stagingDir: Path,
    lgr: logging.Logger,
) -> list[Path]:
    """Stage inputs, converting SICER BED to broadPeak when needed.

    Args:
        infos (Sequence[PeakFileInfo]): Per-file metadata.
        stagingDir (Path): Directory for prepared copies.
        lgr (logging.Logger): Logger instance.

    Returns:
        list[Path]: Paths passed to ChIP-R.
    """
    stagingDir.mkdir(parents=True, exist_ok=True)
    prepared: list[Path] = []
    for info in infos:
        if info.peakFormat == "sicerBed":
            outPath = stagingDir / f"{info.path.stem}.broadPeak"
            rows = convertSicerToBroadpeak(info.path, outPath)
            lgr.info(
                "Converted SICER BED %s -> %s (%d rows)",
                info.path,
                outPath,
                rows,
            )
            prepared.append(outPath)
        else:
            dest = stagingDir / info.path.name
            if dest.resolve() != info.path.resolve():
                shutil.copy2(info.path, dest)
            prepared.append(dest)
    return prepared


def writeRunMetadata(
    path: Path,
    *,
    runId: str,
    timestampUtc: str,
    command: list[str],
    cwd: str,
    decisions: dict[str, object],
    inputFiles: list[str],
) -> None:
    """Persist machine-readable run metadata.

    Args:
        path (Path): JSON output path.
        runId (str): Run identifier.
        timestampUtc (str): ISO-8601 UTC timestamp.
        command (list[str]): ChIP-R argv executed or planned.
        cwd (str): Working directory at run time.
        decisions (dict[str, object]): Strategy and parameter decisions.
        inputFiles (list[str]): Absolute input paths.

    Returns:
        None.
    """
    payload = {
        "skill": "reproducible-peaks",
        "run_id": runId,
        "timestamp_utc": timestampUtc,
        "cwd": cwd,
        "command": command,
        "input_files": inputFiles,
        "decisions": decisions,
        "attribution": {
            "skill_packager": (
                "CAB-aiSkills reproducible-peaks skill author(s); see AUTHORS.md and SKILL.md metadata"
            ),
            "method": "ChIP-R (Newell et al., bioRxiv 2020, doi:10.1101/2020.11.24.396960)",
            "citations_doc": "references/citations.md",
        },
        "citation_keys": [
            "chipr_newell_2020_biorxiv",
            "cab_aiskills_reproducible_peaks",
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv_override: Sequence[str] | None = None) -> int:
    """CLI entrypoint for ChIP-R reproducible peaks.

    Args:
        argv_override (Sequence[str] | None): Optional argv for tests.

    Returns:
        int: Exit code (0 success).
    """
    args = parseArgs(argv_override)
    runId = args.runId or utcRunId()
    runDir = args.outputDir.resolve()
    if runDir.exists() and not args.overwrite:
        print(f"Run directory exists (use --overwrite): {runDir}", file=sys.stderr)
        return 1
    runDir.mkdir(parents=True, exist_ok=True)

    logStem = str((runDir / "reproducible_peaks").with_suffix(""))
    configureLogging(analysisPrefix=logStem, logLevel=args.logLevel)
    lgr = logging.getLogger("main")
    lgr.info("Current working directory: %s", os.getcwd())
    lgr.info("Command used to run the program: python %s", " ".join(str(x) for x in argv))
    logImportedPackageVersions(lgr, ("ChIP-R", "rich"))
    logRuntimeEnvironment(lgr)

    command_used = " ".join(shlex.quote(arg) for arg in [executable] + list(argv))
    lgr.info("Command used to run script: %s", command_used)
    lgr.info("run_id: %s", runId)
    lgr.info("outputDir: %s", runDir)

    try:
        inputPaths = resolveInputPaths(args.inputFiles)
    except FileNotFoundError as exc:
        lgr.critical("%s", exc)
        return 1

    lgr.info("Input peak files (%d):", len(inputPaths))
    for path in inputPaths:
        lgr.info("  %s", path)

    warnReplicateCollisions(inputPaths, lgr)

    infos: list[PeakFileInfo] = []
    for path in inputPaths:
        peakFormat = detectPeakFormat(path)
        if peakFormat == "unknown":
            lgr.critical(
                "Unrecognized peak format for %s (expected narrowPeak, broadPeak, "
                "or SICER BED).",
                path,
            )
            return 1
        try:
            validateNumericFields(path, peakFormat)
        except ValueError as exc:
            lgr.critical("%s", exc)
            return 1

        if args.callingStrategy == "auto":
            strategy = inferCallingStrategy([path], peakFormat)
        else:
            strategy = args.callingStrategy  # type: ignore[assignment]

        infos.append(
            PeakFileInfo(path=path, peakFormat=peakFormat, callingStrategy=strategy)
        )
        lgr.info(
            "File %s: format=%s strategy=%s",
            path.name,
            peakFormat,
            strategy,
        )

    strategies = {info.callingStrategy for info in infos}
    if len(strategies) > 1:
        lgr.critical(
            "Mixed calling strategies across inputs %s; use one condition/mode per run.",
            strategies,
        )
        return 1
    strategy = strategies.pop()
    peakFormats = {info.peakFormat for info in infos}
    if len(peakFormats) > 1 and "sicerBed" in peakFormats:
        lgr.critical("Mixed SICER and non-SICER inputs in one run.")
        return 1

    minEntries = (
        args.minEntries
        if args.minEntries is not None
        else defaultMinEntries(len(inputPaths))
    )
    rankMethod = rankMethodForStrategy(strategy, args.rankMethod)
    lgr.info("Decisions: strategy=%s minEntries=%s rankMethod=%s", strategy, minEntries, rankMethod)

    stagingDir = runDir / "prepared_inputs"
    try:
        prepared = prepareInputs(infos, stagingDir, lgr)
    except (ValueError, FileNotFoundError) as exc:
        lgr.critical("%s", exc)
        return 1

    chiprExe = "chipr"
    if not args.dryRun:
        try:
            chiprExe = resolveChiprExecutable()
        except FileNotFoundError as exc:
            lgr.critical("%s", exc)
            return 1

    outputPrefix = runDir / args.outputPrefix
    chiprCmd = buildChiprCommand(
        chiprExe=chiprExe,
        preparedInputs=prepared,
        outputPrefix=outputPrefix,
        minEntries=minEntries,
        rankMethod=rankMethod,
        alpha=args.alpha,
        size=args.size,
        seed=args.seed,
        dupHandling=args.dupHandling,
    )
    lgr.info("ChIP-R command: %s", " ".join(shlex.quote(c) for c in chiprCmd))

    timestampUtc = datetime.now(timezone.utc).isoformat()
    peakRecords = [
        {
            "path": str(info.path),
            "peakFormat": info.peakFormat,
            "callingStrategy": info.callingStrategy,
        }
        for info in infos
    ]
    decisions = {
        "calling_strategy": strategy,
        "peak_formats": peakRecords,
        "min_entries": minEntries,
        "rank_method": rankMethod,
        "alpha": args.alpha,
        "size": args.size,
        "seed": args.seed,
        "dup_handling": args.dupHandling,
        "dry_run": args.dryRun,
    }
    writeRunMetadata(
        runDir / "run_metadata.json",
        runId=runId,
        timestampUtc=timestampUtc,
        command=chiprCmd,
        cwd=os.getcwd(),
        decisions=decisions,
        inputFiles=[str(p) for p in inputPaths],
    )

    if args.dryRun:
        lgr.info("dryRun=True; skipping ChIP-R execution.")
        return 0

    proc = subprocess.run(chiprCmd, capture_output=True, text=True, check=False)
    if proc.stdout:
        lgr.info("ChIP-R stdout:\n%s", proc.stdout.strip())
    if proc.stderr:
        lgr.info("ChIP-R stderr:\n%s", proc.stderr.strip())
    if proc.returncode != 0:
        lgr.critical("ChIP-R failed with exit code %s", proc.returncode)
        return proc.returncode

    lgr.info("ChIP-R finished successfully. Outputs under prefix: %s", outputPrefix)
    for suffix in ("_all.bed", "_optimal.bed", "_log.txt"):
        candidate = Path(f"{outputPrefix}{suffix}")
        if candidate.is_file():
            lgr.info("  %s", candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
