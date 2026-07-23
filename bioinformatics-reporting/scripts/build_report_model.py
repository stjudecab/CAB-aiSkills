#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Build the normalized report model from a validated manifest."""

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
    TABLE_EXTENSIONS,
    buildReportModel,
    collectToolVersions,
    dumpJson,
    loadStructuredFile,
    profileTable,
    skillRoot,
    validateManifest,
)


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(description="Build normalized report-model JSON.")
    parser.add_argument("--manifest", dest="manifest", required=True, help="Manifest YAML/JSON path.")
    parser.add_argument(
        "--output",
        dest="output",
        required=True,
        help="Output report-model JSON path.",
    )
    parser.add_argument(
        "--baseDir",
        dest="baseDir",
        default="",
        help="Base directory for relative artifact paths (default: manifest parent).",
    )
    addReproducibilityArguments(parser)
    return parser


def main() -> None:
    """Validate manifest, profile tables, and write report model JSON."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    manifestPath = Path(args.manifest).expanduser().resolve()
    outputPath = Path(args.output).expanduser().resolve()
    baseDir = Path(args.baseDir).expanduser().resolve() if args.baseDir else manifestPath.parent
    outputDir = Path(args.outputDir).expanduser().resolve() if args.outputDir else outputPath.parent
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "build_report_model.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    manifest = loadStructuredFile(manifestPath)
    validation = validateManifest(manifest, baseDir)
    if not validation.get("valid"):
        logging.getLogger(__name__).error("Manifest invalid: %s", validation.get("errors"))
        sys.exit(2)

    profiles = {}
    for analysis in manifest.get("analyses") or []:
        for artifact in analysis.get("artifacts") or []:
            rel = artifact.get("path")
            role = artifact.get("role", "")
            if not rel or rel in profiles:
                continue
            resolved = (baseDir / rel).resolve()
            if resolved.suffix.lower() in TABLE_EXTENSIONS and resolved.is_file():
                profiles[rel] = profileTable(resolved)

    model = buildReportModel(manifest, baseDir, profiles, validation)
    dumpJson(model, outputPath)

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="build_report_model.py",
        runId=runId,
        inputs=[{"path": manifestPath.as_posix(), "label": "manifest"}],
        outputDirectory=outputDir,
        outputPrefix=outputPath.as_posix(),
        parameters={"baseDir": baseDir.as_posix()},
        toolVersions=collectToolVersions(),
        summary={
            "analysis_count": len(model.get("analyses") or []),
            "figure_count": len(model.get("figures") or []),
            "table_count": len(model.get("tables") or []),
            "metric_count": len(model.get("metrics") or []),
        },
        outputs=[outputPath.as_posix()],
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "build_report_model.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Normalized report model assembly with provenance-backed metrics",
            "skill_package": f"{skillRoot().name} build_report_model.py",
            "note": "Metrics are computed only from supplied thresholds and readable tables.",
        },
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
