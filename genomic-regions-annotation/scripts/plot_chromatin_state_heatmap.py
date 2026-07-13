#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: plot_chromatin_state_heatmap.py
# Description:
# Plot a publication heatmap from BEDinContext statsCombined.frc.tsv output.
#########################################################################

"""Plot a fraction heatmap from chromatin-state annotation TSV outputs."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_reproducibility import (
    addReproducibilityArgs,
    appendCommandLog,
    collectBaseToolVersions,
    configureRunLogging,
    runIdUtc,
    timestampIsoUtc,
    writeAgentArtifacts,
    writeRunMetadata,
)


def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the chromatin-state heatmap plotter.

    Args:
        argv (list[str] | None): Optional argv override.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Create a publication-quality heatmap from a BEDinContext "
            "statsCombined.frc.tsv (or similar) fraction matrix."
        )
    )
    parser.add_argument(
        "--inputFile",
        required=True,
        help="Tab-delimited matrix with a State index column and one column per BED file.",
    )
    parser.add_argument(
        "--outputPrefix",
        required=True,
        help="Output path prefix (no extension). Writes .pdf and .png.",
    )
    parser.add_argument(
        "--cmap",
        default="Reds",
        help="Matplotlib/seaborn colormap name. Default: Reds.",
    )
    parser.add_argument(
        "--vmin",
        type=float,
        default=0.0,
        help="Color scale minimum (fraction). Default: 0.",
    )
    parser.add_argument(
        "--vmax",
        type=float,
        default=1.0,
        help="Color scale maximum (fraction). Default: 1.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Raster DPI. Default: 300.",
    )
    addReproducibilityArgs(parser)
    return parser.parse_args(argv)


def plotHeatmap(
    inputFile: Path,
    outputPrefix: Path,
    *,
    cmap: str,
    vmin: float,
    vmax: float,
    dpi: int,
) -> list[Path]:
    """Draw and save PDF/PNG heatmaps from a fraction matrix.

    Args:
        inputFile (Path): statsCombined.frc.tsv-like matrix.
        outputPrefix (Path): Output prefix without extension.
        cmap (str): Colormap name.
        vmin (float): Color scale minimum (fraction units).
        vmax (float): Color scale maximum (fraction units).
        dpi (int): PNG resolution.

    Returns:
        list[Path]: Written figure paths.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    if not inputFile.is_file():
        raise FileNotFoundError(
            f"Expected fraction matrix at {inputFile}, but the file was not found."
        )

    df = pd.read_csv(inputFile, sep="\t", index_col="State")
    outputPrefix.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots()
    fig.set_size_inches(max(6, 0.6 * df.shape[1] + 3), max(5, 0.35 * df.shape[0] + 2))
    sns.heatmap(
        df,
        annot=True,
        vmin=vmin,
        vmax=vmax,
        cmap=cmap,
        cbar_kws={"label": "fraction of peaks overlapping with emission state"},
        linewidths=0.5,
        fmt=".2%",
        ax=ax,
    )
    ax.set_title("Chromatin-state annotation fractions")
    ax.set_xlabel("Regions input file")
    ax.set_ylabel("Chromatin state")
    plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment="right")

    pdfPath = Path(str(outputPrefix) + ".pdf")
    pngPath = Path(str(outputPrefix) + ".png")
    fig.savefig(pdfPath, bbox_inches="tight", dpi=dpi)
    fig.savefig(pngPath, bbox_inches="tight", dpi=dpi)
    plt.close(fig)
    return [pdfPath, pngPath]


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for chromatin-state fraction heatmaps.

    Args:
        argv (list[str] | None): Optional argv override.

    Returns:
        int: Process exit code.
    """
    try:
        from skill_env import bootstrap

        bootstrap()
    except Exception:
        pass

    args = parseArgs(argv)
    runId = args.runId or runIdUtc()
    outputPrefix = Path(args.outputPrefix)
    outputDir = Path(args.outputDir).resolve() if args.outputDir else outputPrefix.parent.resolve()
    outputDir.mkdir(parents=True, exist_ok=True)
    logPath = configureRunLogging(outputDir, "plot_chromatin_state_heatmap")
    commandsPath = appendCommandLog(outputDir, runId)
    writeAgentArtifacts(
        outputDir,
        agentRequest=args.agentRequest,
        agentRequestFile=Path(args.agentRequestFile) if args.agentRequestFile else None,
        agentWorkflow=args.agentWorkflow,
        agentWorkflowFile=Path(args.agentWorkflowFile) if args.agentWorkflowFile else None,
    )

    try:
        outputs = plotHeatmap(
            Path(args.inputFile),
            outputPrefix,
            cmap=args.cmap,
            vmin=args.vmin,
            vmax=args.vmax,
            dpi=args.dpi,
        )
        for path in outputs:
            logging.info("Wrote %s", path)
        writeRunMetadata(
            outputDir / "run_metadata.json",
            {
                "skill": "genomic-regions-annotation",
                "script": "plot_chromatin_state_heatmap.py",
                "run_id": runId,
                "timestamp_utc": timestampIsoUtc(),
                "command": " ".join(sys.argv if argv is None else argv),
                "working_directory": Path.cwd().as_posix(),
                "inputs": [str(Path(args.inputFile).resolve())],
                "output_directory": outputDir.as_posix(),
                "output_prefix": str(outputPrefix),
                "parameters": {
                    "cmap": args.cmap,
                    "vmin": args.vmin,
                    "vmax": args.vmax,
                    "dpi": args.dpi,
                },
                "tool_versions": collectBaseToolVersions(Path(__file__)),
                "summary": {"n_figures": len(outputs)},
                "outputs": [p.resolve().as_posix() for p in outputs],
                "logs": {
                    "plot_chromatin_state_heatmap.log": logPath.as_posix(),
                    "commands.log": commandsPath.as_posix(),
                },
                "attribution": {
                    "method": "Chromatin-state fraction heatmap from BEDinContext stats",
                    "skill_package": "genomic-regions-annotation",
                },
            },
        )
        return 0
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
