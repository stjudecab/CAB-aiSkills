#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `colorblind-sim` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Run CBviz colorblindness simulation with optional format conversion."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Optional

from convert_to_png import NEEDS_CONVERT, NATIVE_RASTER, convertToPng, detectFormat
from run_logging import (
    addReproducibilityArguments,
    appendCommandLog,
    commandLineString,
    configureLogging,
    runIdUtc,
    writeAgentArtifacts,
    writeRunMetadata,
)

LOGGER = logging.getLogger("run_colorblind_sim")


def collectToolVersions() -> dict[str, str]:
    """Collect resolved package and CBviz versions for the reproducibility record.

    Returns:
        dict[str, str]: Mapping of tool name to version string.
    """
    versions: dict[str, str] = {
        "python": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "script": Path(__file__).resolve().as_posix(),
        "cbviz_cli": shutil.which("cbviz") or "not found",
        "cbviz_fast_cli": shutil.which("cbviz-fast") or "not found",
    }
    for name in ("cbviz", "colorspacious", "matplotlib", "numpy", "Pillow", "pymupdf"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def resolveSimulationInput(
    inputPath: Path,
    outputDir: Path,
    *,
    forceConvert: bool,
    page: int,
    dpi: int,
) -> tuple[Path, Optional[dict[str, str]]]:
    """Return a CBviz-ready PNG path, converting when the format requires it.

    Args:
        inputPath (Path): User-provided figure path.
        outputDir (Path): Run directory (prepared/ lives here).
        forceConvert (bool): Force raster re-encode to PNG.
        page (int): 1-based PDF page.
        dpi (int): Conversion DPI.

    Returns:
        tuple[Path, Optional[dict[str, str]]]: Ready image path and optional
        conversion summary.

    Raises:
        ValueError: When the format is unsupported.
        RuntimeError: When conversion fails.
    """
    formatName = detectFormat(inputPath, "")
    suffix = f".{formatName}" if formatName else inputPath.suffix.lower()

    needsConversion = suffix in NEEDS_CONVERT or forceConvert
    if suffix == ".png" and not forceConvert:
        return inputPath, None
    if suffix in NATIVE_RASTER and not forceConvert:
        # Pillow-backed formats are accepted by matplotlib.imread / CBviz.
        return inputPath, None
    if not needsConversion and suffix not in NEEDS_CONVERT:
        raise ValueError(
            f"Unsupported figure format {suffix!r}. "
            f"Pass PNG/JPEG/TIFF/BMP/GIF directly, or PDF/SVG/EPS for conversion."
        )

    preparedDir = outputDir / "prepared"
    preparedDir.mkdir(parents=True, exist_ok=True)
    pngPath = preparedDir / f"{inputPath.stem}.png"
    summary = convertToPng(
        inputPath,
        pngPath,
        formatName=formatName,
        page=page,
        dpi=dpi,
        force=forceConvert or suffix in NATIVE_RASTER,
    )
    return pngPath, summary


def buildCbvizCommand(
    *,
    mode: str,
    infile: Path,
    outfile: Path,
    severity: int,
    types: str,
    runAll: bool,
    individualPlots: bool,
    noOriginal: bool,
) -> list[str]:
    """Build the ``cbviz`` / ``cbviz-fast`` argv list.

    Args:
        mode (str): ``fast`` or ``simulate``.
        infile (Path): Input image path for CBviz.
        outfile (Path): Output image path prefix/file.
        severity (int): CVD severity 0–100.
        types (str): Comma-separated CVD type prefixes for simulate mode.
        runAll (bool): Use ``--all`` in simulate mode.
        individualPlots (bool): Write one file per CVD type.
        noOriginal (bool): Omit the original panel.

    Returns:
        list[str]: Command argv.

    Raises:
        ValueError: When mode/type flags are inconsistent.
        FileNotFoundError: When the CBviz executable is missing.
    """
    if mode == "fast":
        exe = shutil.which("cbviz-fast")
        if not exe:
            raise FileNotFoundError(
                "cbviz-fast not found on PATH. Run bash scripts/ensure_env.sh."
            )
        return [exe, "-s", str(severity), str(infile), str(outfile)]

    if mode != "simulate":
        raise ValueError(f"Unknown mode {mode!r}; use fast or simulate.")

    exe = shutil.which("cbviz")
    if not exe:
        raise FileNotFoundError(
            "cbviz not found on PATH. Run bash scripts/ensure_env.sh."
        )
    cmd = [exe, "simulate", "-s", str(severity)]
    if runAll:
        cmd.append("-a")
    elif types:
        cmd.extend(["-t", types])
    else:
        raise ValueError("simulate mode requires --all or --types.")
    if individualPlots:
        cmd.append("--individual-plots")
    if noOriginal:
        cmd.append("--no-original")
    cmd.extend([str(infile), str(outfile)])
    return cmd


def collectOutputs(outfile: Path, individualPlots: bool) -> list[str]:
    """Return existing deliverable paths produced by CBviz.

    Args:
        outfile (Path): Requested outfile path.
        individualPlots (bool): Whether per-type files were requested.

    Returns:
        list[str]: Absolute paths that exist after the run.
    """
    found: list[str] = []
    if outfile.is_file():
        found.append(outfile.resolve().as_posix())
    if individualPlots:
        parent = outfile.parent
        stem = outfile.stem
        for path in sorted(parent.glob(f"{stem}.*.png")):
            found.append(path.resolve().as_posix())
        # CBviz may also use other extensions from outfile
        for path in sorted(parent.glob(f"{stem}.*")):
            if path.is_file() and path.resolve().as_posix() not in found:
                if path.suffix.lower() in {".png", ".pdf", ".jpg", ".jpeg"}:
                    found.append(path.resolve().as_posix())
    return found


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Simulate color vision deficiency on a figure using CBviz."
    )
    parser.add_argument("--input", required=True, help="Input figure path.")
    parser.add_argument(
        "--outputPrefix",
        required=True,
        help="Output path prefix or file (CBviz outfile). Prefer under the run directory.",
    )
    parser.add_argument(
        "--mode",
        choices=("fast", "simulate"),
        default="fast",
        help="fast=cbviz-fast 2x2 grid (default); simulate=full cbviz simulate CLI.",
    )
    parser.add_argument(
        "--types",
        default="protan,deuteran,tritan",
        help="Comma-separated CVD types for simulate mode (default: protan,deuteran,tritan).",
    )
    parser.add_argument(
        "--severity",
        type=int,
        default=100,
        help="CVD severity 0–100 (default: 100).",
    )
    parser.add_argument(
        "--all",
        dest="runAll",
        action="store_true",
        help="simulate mode: include *opic and anomalous panels (cbviz -a).",
    )
    parser.add_argument(
        "--individualPlots",
        action="store_true",
        help="simulate mode: write one image per CVD type.",
    )
    parser.add_argument(
        "--noOriginal",
        action="store_true",
        help="simulate mode: omit the original panel.",
    )
    parser.add_argument(
        "--forceConvert",
        action="store_true",
        help="Force conversion/normalization to PNG before CBviz.",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="1-based PDF page when converting PDF (default: 1).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for PDF/SVG conversion (default: 300).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into an existing run directory / overwriting outfile.",
    )
    addReproducibilityArguments(parser)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the colorblind simulation CLI.

    Args:
        argv (Optional[list[str]]): Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        int: Process exit code (0 on success).
    """
    from skill_env import bootstrap

    bootstrap()

    parser = buildParser()
    args = parser.parse_args(argv)

    if args.severity < 0 or args.severity > 100:
        LOGGER.error("--severity must be in [0, 100]; got %s", args.severity)
        return 1

    inputPath = Path(args.input).expanduser().resolve()
    if not inputPath.is_file():
        LOGGER.error("Input file not found: %s", inputPath)
        return 1

    runId = args.runId or runIdUtc()
    outputPrefix = Path(args.outputPrefix).expanduser()
    if args.outputDir:
        outputDir = Path(args.outputDir).expanduser().resolve()
    else:
        outputDir = outputPrefix.resolve().parent

    if outputDir.exists() and any(outputDir.iterdir()) and not args.overwrite:
        # Allow non-empty dirs only with --overwrite to avoid clobbering prior runs.
        # First-time creation of empty prepared/logs is fine after mkdir.
        existingMeta = outputDir / "run_metadata.json"
        if existingMeta.is_file():
            LOGGER.error(
                "Run directory already has run_metadata.json: %s. "
                "Pass --overwrite or choose a new --outputDir / --runId.",
                outputDir,
            )
            return 1

    outputDir.mkdir(parents=True, exist_ok=True)
    outfile = outputPrefix if outputPrefix.is_absolute() else (outputDir / outputPrefix.name)
    # CBviz/matplotlib infer format from the outfile suffix. Prefixes like
    # ``figure.cb`` must become ``figure.cb.png`` (matching upstream examples).
    knownOutSuffixes = {".png", ".pdf", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".svgz"}
    if outfile.suffix.lower() not in knownOutSuffixes:
        outfile = Path(str(outfile) + ".png")
    outfile.parent.mkdir(parents=True, exist_ok=True)

    if outfile.is_file() and not args.overwrite:
        LOGGER.error("Output exists: %s (pass --overwrite to replace).", outfile)
        return 1

    logsDir = outputDir / "logs"
    logsDir.mkdir(parents=True, exist_ok=True)
    logFile = logsDir / "run_colorblind_sim.log"
    configureLogging(logFile)
    appendCommandLog(logsDir / "commands.log", runId, commandLineString())

    LOGGER.info("Run ID: %s", runId)
    LOGGER.info("Command: %s", commandLineString())
    LOGGER.info("Working directory: %s", Path.cwd())
    LOGGER.info("Output directory: %s", outputDir)
    toolVersions = collectToolVersions()
    for key, value in toolVersions.items():
        LOGGER.info("Version %s=%s", key, value)

    agentRequestPath, agentWorkflowPath = writeAgentArtifacts(outputDir, args)

    try:
        simInput, conversionSummary = resolveSimulationInput(
            inputPath,
            outputDir,
            forceConvert=args.forceConvert,
            page=args.page,
            dpi=args.dpi,
        )
        cmd = buildCbvizCommand(
            mode=args.mode,
            infile=simInput,
            outfile=outfile,
            severity=args.severity,
            types=args.types,
            runAll=args.runAll,
            individualPlots=args.individualPlots,
            noOriginal=args.noOriginal,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        LOGGER.error("%s", exc)
        return 1

    if conversionSummary:
        LOGGER.info("Converted input via %s → %s", conversionSummary["method"], simInput)
    LOGGER.info("Running: %s", " ".join(cmd))
    appendCommandLog(logsDir / "commands.log", runId, " ".join(cmd))

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.stdout.strip():
        LOGGER.info("cbviz stdout:\n%s", completed.stdout.strip())
    if completed.stderr.strip():
        LOGGER.info("cbviz stderr:\n%s", completed.stderr.strip())
    if completed.returncode != 0:
        LOGGER.error("CBviz exited with code %s", completed.returncode)
        return completed.returncode

    outputs = collectOutputs(outfile, individualPlots=args.individualPlots)
    if not outputs:
        LOGGER.error("CBviz finished but no output files were found near %s", outfile)
        return 1

    LOGGER.info("Wrote %d deliverable(s)", len(outputs))
    for path in outputs:
        LOGGER.info("  %s", path)

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="colorblind-sim",
        script="run_colorblind_sim.py",
        runId=runId,
        inputs=[
            {
                "path": inputPath.as_posix(),
                "format": detectFormat(inputPath, ""),
                "role": "source_figure",
            },
            {
                "path": simInput.as_posix(),
                "format": "png" if simInput.suffix.lower() == ".png" else detectFormat(simInput, ""),
                "role": "cbviz_infile",
            },
        ],
        outputDirectory=outputDir,
        outputPrefix=outfile.as_posix(),
        parameters={
            "mode": args.mode,
            "types": args.types,
            "severity": args.severity,
            "all": args.runAll,
            "individualPlots": args.individualPlots,
            "noOriginal": args.noOriginal,
            "forceConvert": args.forceConvert,
            "page": args.page,
            "dpi": args.dpi,
            "conversion": conversionSummary,
        },
        toolVersions=toolVersions,
        summary={
            "n_outputs": len(outputs),
            "cbviz_returncode": completed.returncode,
        },
        outputs=outputs,
        agentRequestFile=agentRequestPath,
        agentWorkflowFile=agentWorkflowPath,
        logs={
            "run_colorblind_sim.log": logFile.resolve().as_posix(),
            "commands.log": (logsDir / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "CBviz color vision deficiency simulation (colorspacious)",
            "skill_package": "CAB-aiSkills colorblind-sim",
            "note": (
                "Agent prepares run directory and flags; this script converts formats "
                "when needed and invokes upstream cbviz / cbviz-fast."
            ),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
