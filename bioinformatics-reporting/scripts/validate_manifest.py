#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Validate a bioinformatics report manifest and resolve artifact paths."""

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
from report_common import (
    collectToolVersions,
    dumpJson,
    loadStructuredFile,
    skillRoot,
    validateManifest,
)


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(description="Validate a report manifest schema and paths.")
    parser.add_argument("manifest", help="Manifest YAML or JSON path.")
    parser.add_argument(
        "--baseDir",
        dest="baseDir",
        default="",
        help="Base directory for relative artifact paths (default: manifest parent).",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default="",
        help="Optional validation report JSON path.",
    )
    addReproducibilityArguments(parser)
    return parser


def main() -> None:
    """Validate a manifest and optionally write a validation report."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    manifestPath = Path(args.manifest).expanduser().resolve()
    baseDir = Path(args.baseDir).expanduser().resolve() if args.baseDir else manifestPath.parent
    outputDir = Path(args.outputDir).expanduser().resolve() if args.outputDir else manifestPath.parent
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "validate_manifest.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    manifest = loadStructuredFile(manifestPath)
    report = validateManifest(manifest, baseDir)
    if args.output:
        dumpJson(report, Path(args.output).expanduser().resolve())
    else:
        dumpJson(report, outputDir / "validation-report.json")

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="validate_manifest.py",
        runId=runId,
        inputs=[{"path": manifestPath.as_posix(), "label": "manifest"}],
        outputDirectory=outputDir,
        outputPrefix=manifestPath.as_posix(),
        parameters={"baseDir": baseDir.as_posix()},
        toolVersions=collectToolVersions(),
        summary={
            "valid": report.get("valid"),
            "error_count": len(report.get("errors") or []),
            "warning_count": len(report.get("warnings") or []),
        },
        outputs=[str(args.output or (outputDir / "validation-report.json"))],
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "validate_manifest.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Manifest schema and artifact path validation",
            "skill_package": f"{skillRoot().name} validate_manifest.py",
            "note": "Distinguishes fatal errors from warnings.",
        },
    )

    if not report.get("valid"):
        logging.getLogger(__name__).error("Manifest validation failed.")
        sys.exit(2)
    logging.getLogger(__name__).info("Manifest validation passed with %d warnings.", len(report.get("warnings") or []))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
