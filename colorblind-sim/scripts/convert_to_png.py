#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `colorblind-sim` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Convert figure files to PNG for CBviz (PDF/SVG/EPS and optional raster normalize)."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Optional

from run_logging import (
    addReproducibilityArguments,
    appendCommandLog,
    commandLineString,
    configureLogging,
    runIdUtc,
    writeAgentArtifacts,
    writeRunMetadata,
)

LOGGER = logging.getLogger("convert_to_png")

NATIVE_RASTER = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}
NEEDS_CONVERT = {".pdf", ".svg", ".eps"}


def collectToolVersions() -> dict[str, str]:
    """Collect resolved package versions for the reproducibility record.

    Returns:
        dict[str, str]: Mapping of tool name to version string.
    """
    versions: dict[str, str] = {
        "python": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "script": Path(__file__).resolve().as_posix(),
    }
    for name in ("Pillow", "pymupdf", "matplotlib", "numpy"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def detectFormat(path: Path, formatOverride: str) -> str:
    """Return a lowercase format label for *path*.

    Args:
        path (Path): Input file path.
        formatOverride (str): Explicit format when provided (e.g. ``pdf``).

    Returns:
        str: Format label such as ``png``, ``pdf``, or ``svg``.
    """
    if formatOverride:
        return formatOverride.lower().lstrip(".")
    return path.suffix.lower().lstrip(".")


def convertPdfToPng(inputPath: Path, outputPath: Path, page: int, dpi: int) -> None:
    """Rasterize one PDF page to PNG with PyMuPDF.

    Args:
        inputPath (Path): Source PDF path.
        outputPath (Path): Destination PNG path.
        page (int): 1-based page index to render.
        dpi (int): Rasterization DPI.

    Returns:
        None.

    Raises:
        ValueError: When the page index is out of range.
        RuntimeError: When PyMuPDF is unavailable or rendering fails.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF (pymupdf) is required for PDF→PNG. Run bash scripts/ensure_env.sh."
        ) from exc

    document = fitz.open(inputPath)
    try:
        if page < 1 or page > document.page_count:
            raise ValueError(
                f"PDF page {page} out of range (document has {document.page_count} page(s))."
            )
        pdfPage = document.load_page(page - 1)
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = pdfPage.get_pixmap(matrix=matrix, alpha=False)
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(outputPath.as_posix())
    finally:
        document.close()


def findSvgConverter() -> Optional[tuple[str, list[str]]]:
    """Locate a host SVG/EPS→PNG converter.

    Returns:
        Optional[tuple[str, list[str]]]: ``(tool_name, base_command)`` or ``None``.
    """
    rsvg = shutil.which("rsvg-convert")
    if rsvg:
        return ("rsvg-convert", [rsvg])
    inkscape = shutil.which("inkscape")
    if inkscape:
        return ("inkscape", [inkscape])
    return None


def convertSvgOrEpsToPng(inputPath: Path, outputPath: Path, dpi: int) -> str:
    """Rasterize SVG or EPS via ``rsvg-convert`` or ``inkscape``.

    Args:
        inputPath (Path): Source SVG or EPS path.
        outputPath (Path): Destination PNG path.
        dpi (int): Target DPI for Inkscape export.

    Returns:
        str: Name of the host tool used.

    Raises:
        RuntimeError: When neither host converter is available or conversion fails.
    """
    found = findSvgConverter()
    if found is None:
        raise RuntimeError(
            "SVG/EPS→PNG requires a host tool. Install librsvg (`rsvg-convert`) or "
            "Inkscape and ensure it is on PATH, then retry."
        )
    toolName, baseCmd = found
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    if toolName == "rsvg-convert":
        cmd = baseCmd + ["-f", "png", "-o", str(outputPath), str(inputPath)]
    else:
        # Inkscape 1.x export API
        cmd = baseCmd + [
            str(inputPath),
            f"--export-filename={outputPath}",
            f"--export-dpi={dpi}",
        ]
    LOGGER.info("Running: %s", " ".join(cmd))
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not outputPath.is_file():
        raise RuntimeError(
            f"{toolName} failed converting {inputPath} → {outputPath}: "
            f"{completed.stderr.strip() or completed.stdout.strip() or 'no output'}"
        )
    return toolName


def convertRasterToPng(inputPath: Path, outputPath: Path) -> None:
    """Normalize a raster image to RGB PNG with Pillow.

    Args:
        inputPath (Path): Source raster path.
        outputPath (Path): Destination PNG path.

    Returns:
        None.

    Raises:
        RuntimeError: When Pillow cannot open or save the image.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for raster→PNG. Run bash scripts/ensure_env.sh."
        ) from exc

    outputPath.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(inputPath) as image:
        rgb = image.convert("RGB")
        rgb.save(outputPath, format="PNG")


def convertToPng(
    inputPath: Path,
    outputPath: Path,
    *,
    formatName: str,
    page: int,
    dpi: int,
    force: bool,
) -> dict[str, str]:
    """Convert *inputPath* to PNG at *outputPath* when needed.

    Args:
        inputPath (Path): Source figure path.
        outputPath (Path): Destination PNG path.
        formatName (str): Detected or overridden format label.
        page (int): 1-based PDF page index.
        dpi (int): Rasterization DPI for PDF/SVG.
        force (bool): When True, re-encode native rasters to PNG as well.

    Returns:
        dict[str, str]: Summary with keys ``method``, ``format``, ``output``.

    Raises:
        ValueError: When the format is unsupported.
        RuntimeError: When conversion fails.
    """
    suffix = f".{formatName}" if formatName else inputPath.suffix.lower()
    if suffix == ".png" and not force:
        if inputPath.resolve() != outputPath.resolve():
            outputPath.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inputPath, outputPath)
        return {"method": "copy", "format": "png", "output": outputPath.as_posix()}

    if suffix == ".pdf" or formatName == "pdf":
        convertPdfToPng(inputPath, outputPath, page=page, dpi=dpi)
        return {"method": "pymupdf", "format": "pdf", "output": outputPath.as_posix()}

    if suffix in {".svg", ".eps"} or formatName in {"svg", "eps"}:
        tool = convertSvgOrEpsToPng(inputPath, outputPath, dpi=dpi)
        return {"method": tool, "format": formatName or suffix.lstrip("."), "output": outputPath.as_posix()}

    if suffix in NATIVE_RASTER or force:
        convertRasterToPng(inputPath, outputPath)
        return {"method": "pillow", "format": formatName or suffix.lstrip("."), "output": outputPath.as_posix()}

    raise ValueError(
        f"Unsupported figure format {suffix!r} for {inputPath}. "
        f"Native for CBviz (with Pillow): {sorted(NATIVE_RASTER)}. "
        f"Convert first: {sorted(NEEDS_CONVERT)}."
    )


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Convert PDF/SVG/EPS (or normalize rasters) to PNG for CBviz."
    )
    parser.add_argument("--input", required=True, help="Input figure path.")
    parser.add_argument(
        "--output",
        default="",
        help="Output PNG path. Default: <outputDir>/prepared/<stem>.png",
    )
    parser.add_argument(
        "--format",
        dest="formatName",
        default="",
        help="Override format detection (png, pdf, svg, eps, jpg, tiff, …).",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="1-based PDF page to rasterize (default: 1).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Rasterization DPI for PDF/SVG (default: 300).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-encode even when input is already PNG or a native raster.",
    )
    addReproducibilityArguments(parser)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the converter CLI.

    Args:
        argv (Optional[list[str]]): Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        int: Process exit code (0 on success).
    """
    from skill_env import bootstrap

    bootstrap()

    parser = buildParser()
    args = parser.parse_args(argv)

    inputPath = Path(args.input).expanduser().resolve()
    if not inputPath.is_file():
        LOGGER.error("Input file not found: %s", inputPath)
        return 1

    runId = args.runId or runIdUtc()
    if args.outputDir:
        outputDir = Path(args.outputDir).expanduser().resolve()
    elif args.output:
        outputDir = Path(args.output).expanduser().resolve().parent
    else:
        outputDir = Path.cwd() / f"colorblind-sim-{runId}"

    outputDir.mkdir(parents=True, exist_ok=True)
    logsDir = outputDir / "logs"
    logsDir.mkdir(parents=True, exist_ok=True)
    logFile = logsDir / "convert_to_png.log"
    configureLogging(logFile)
    appendCommandLog(logsDir / "commands.log", runId, commandLineString())

    LOGGER.info("Run ID: %s", runId)
    LOGGER.info("Command: %s", commandLineString())
    LOGGER.info("Working directory: %s", Path.cwd())
    LOGGER.info("Output directory: %s", outputDir)

    if args.output:
        outputPath = Path(args.output).expanduser().resolve()
    else:
        prepared = outputDir / "prepared"
        prepared.mkdir(parents=True, exist_ok=True)
        outputPath = prepared / f"{inputPath.stem}.png"

    formatName = detectFormat(inputPath, args.formatName)
    agentRequestPath, agentWorkflowPath = writeAgentArtifacts(outputDir, args)

    try:
        summary = convertToPng(
            inputPath,
            outputPath,
            formatName=formatName,
            page=args.page,
            dpi=args.dpi,
            force=args.force,
        )
    except (ValueError, RuntimeError) as exc:
        LOGGER.error("%s", exc)
        return 1

    LOGGER.info("Wrote %s via %s", outputPath, summary["method"])
    outputs = [outputPath.resolve().as_posix()] if outputPath.is_file() else []
    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="colorblind-sim",
        script="convert_to_png.py",
        runId=runId,
        inputs=[{"path": inputPath.as_posix(), "format": formatName, "role": "source_figure"}],
        outputDirectory=outputDir,
        outputPrefix=None,
        parameters={
            "page": args.page,
            "dpi": args.dpi,
            "force": args.force,
            "format": formatName,
        },
        toolVersions=collectToolVersions(),
        summary=summary,
        outputs=outputs,
        agentRequestFile=agentRequestPath,
        agentWorkflowFile=agentWorkflowPath,
        logs={
            "convert_to_png.log": logFile.resolve().as_posix(),
            "commands.log": (logsDir / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Format conversion to PNG for CBviz input",
            "skill_package": "CAB-aiSkills colorblind-sim",
            "note": "Agent prepares inputs; this script performs conversion only.",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
