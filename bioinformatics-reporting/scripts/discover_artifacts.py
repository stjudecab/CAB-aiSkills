#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Recursively discover and classify bioinformatics result artifacts."""

from __future__ import annotations

import argparse
import json
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
from report_common import collectToolVersions, discoverArtifacts, dumpJson, dumpYaml, skillRoot


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Discover and classify artifacts in a results directory (read-only)."
    )
    parser.add_argument("resultsDir", help="Root results directory to scan.")
    parser.add_argument(
        "--output",
        dest="output",
        required=True,
        help="Output inventory path (.yaml or .json).",
    )
    parser.add_argument(
        "--maxFiles",
        dest="maxFiles",
        type=int,
        default=5000,
        help="Maximum number of files to inventory.",
    )
    addReproducibilityArguments(parser)
    return parser


def main() -> None:
    """Discover artifacts and write an inventory file."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    outputPath = Path(args.output).expanduser().resolve()
    outputDir = Path(args.outputDir).expanduser().resolve() if args.outputDir else outputPath.parent
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "discover_artifacts.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    resultsDir = Path(args.resultsDir).expanduser().resolve()
    inventory = discoverArtifacts(resultsDir, maxFiles=args.maxFiles)
    suffix = outputPath.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        dumpYaml(inventory, outputPath)
    else:
        dumpJson(inventory, outputPath)

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="discover_artifacts.py",
        runId=runId,
        inputs=[{"path": resultsDir.as_posix(), "label": "resultsDir"}],
        outputDirectory=outputDir,
        outputPrefix=outputPath.as_posix(),
        parameters={"maxFiles": args.maxFiles, "output": outputPath.as_posix()},
        toolVersions=collectToolVersions(),
        summary={"artifact_count": len(inventory.get("artifacts") or [])},
        outputs=[outputPath.as_posix()],
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "discover_artifacts.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Read-only recursive artifact discovery and role classification",
            "skill_package": f"{skillRoot().name} discover_artifacts.py",
            "note": "Source inputs are never modified.",
        },
    )
    logging.getLogger(__name__).info("Wrote discovery inventory to %s", outputPath)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
