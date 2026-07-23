#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Safely profile supported tables for reporting summaries."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from run_logging import (
    addReproducibilityArguments,
    appendCommandLog,
    commandLineString,
    configureLogging,
    runIdUtc,
    writeAgentArtifacts,
    writeRunMetadata,
)
from report_common import collectToolVersions, dumpJson, profileTable, skillRoot


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(description="Profile a supported table without interpretation.")
    parser.add_argument("table", help="Table file path.")
    parser.add_argument(
        "--output",
        dest="output",
        required=True,
        help="Output profile JSON path.",
    )
    parser.add_argument("--maxRows", dest="maxRows", type=int, default=10000)
    parser.add_argument("--previewRows", dest="previewRows", type=int, default=20)
    addReproducibilityArguments(parser)
    return parser


def main() -> None:
    """Profile a table and write JSON output."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    tablePath = Path(args.table).expanduser().resolve()
    outputPath = Path(args.output).expanduser().resolve()
    outputDir = Path(args.outputDir).expanduser().resolve() if args.outputDir else outputPath.parent
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "profile_table.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    profile = profileTable(
        tablePath,
        maxRows=args.maxRows,
        previewRows=args.previewRows,
    )
    dumpJson(profile, outputPath)

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="profile_table.py",
        runId=runId,
        inputs=[{"path": tablePath.as_posix(), "label": "table"}],
        outputDirectory=outputDir,
        outputPrefix=outputPath.as_posix(),
        parameters={"maxRows": args.maxRows, "previewRows": args.previewRows},
        toolVersions=collectToolVersions(),
        summary={
            "readable": profile.get("readable"),
            "row_count": profile.get("row_count"),
            "column_count": profile.get("column_count"),
        },
        outputs=[outputPath.as_posix()],
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "profile_table.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Deterministic table profiling for reporting",
            "skill_package": f"{skillRoot().name} profile_table.py",
            "note": "No scientific interpretation is performed here.",
        },
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
