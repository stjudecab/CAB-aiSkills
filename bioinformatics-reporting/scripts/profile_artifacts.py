#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Profile one or many tables listed in a manifest or discovery inventory."""

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
    collectToolVersions,
    dumpJson,
    loadStructuredFile,
    profileTable,
    skillRoot,
)


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Profile tables referenced by a manifest or inventory.")
    parser.add_argument(
        "--manifest",
        dest="manifest",
        default="",
        help="Manifest YAML/JSON path.",
    )
    parser.add_argument(
        "--inventory",
        dest="inventory",
        default="",
        help="Discovery inventory YAML/JSON path.",
    )
    parser.add_argument(
        "--baseDir",
        dest="baseDir",
        required=True,
        help="Base directory for relative artifact paths.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        required=True,
        help="Output profiles JSON path.",
    )
    parser.add_argument("--maxRows", dest="maxRows", type=int, default=10000)
    parser.add_argument("--previewRows", dest="previewRows", type=int, default=20)
    addReproducibilityArguments(parser)
    return parser


def collectTablePaths(manifestPath: Path, inventoryPath: Path, baseDir: Path) -> list[str]:
    """Collect relative table paths from manifest or discovery inventory."""
    paths: list[str] = []
    if manifestPath.is_file():
        manifest = loadStructuredFile(manifestPath)
        for analysis in manifest.get("analyses") or []:
            for artifact in analysis.get("artifacts") or []:
                rel = artifact.get("path")
                if rel and (baseDir / rel).suffix.lower() in TABLE_EXTENSIONS:
                    paths.append(rel)
    elif inventoryPath.is_file():
        inventory = loadStructuredFile(inventoryPath)
        for artifact in inventory.get("artifacts") or []:
            rel = artifact.get("path")
            if rel and artifact.get("format") in {"tsv", "csv", "txt", "xlsx"}:
                paths.append(rel)
    return sorted(set(paths))


def main() -> None:
    """Profile tables and write a combined JSON document."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    baseDir = Path(args.baseDir).expanduser().resolve()
    outputPath = Path(args.output).expanduser().resolve()
    outputDir = Path(args.outputDir).expanduser().resolve() if args.outputDir else outputPath.parent
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "profile_artifacts.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    manifestPath = Path(args.manifest).expanduser().resolve() if args.manifest else Path()
    inventoryPath = Path(args.inventory).expanduser().resolve() if args.inventory else Path()
    tablePaths = collectTablePaths(manifestPath, inventoryPath, baseDir)
    if not tablePaths:
        logging.getLogger(__name__).error("No table artifacts found to profile.")
        sys.exit(2)

    profiles = {}
    for rel in tablePaths:
        resolved = (baseDir / rel).resolve()
        if resolved.is_file():
            profiles[rel] = profileTable(resolved, maxRows=args.maxRows, previewRows=args.previewRows)
    dumpJson({"profiles": profiles, "table_count": len(profiles)}, outputPath)

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="profile_artifacts.py",
        runId=runId,
        inputs=[{"path": baseDir.as_posix(), "label": "baseDir"}],
        outputDirectory=outputDir,
        outputPrefix=outputPath.as_posix(),
        parameters={"maxRows": args.maxRows, "previewRows": args.previewRows},
        toolVersions=collectToolVersions(),
        summary={"profiled_tables": len(profiles)},
        outputs=[outputPath.as_posix()],
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "profile_artifacts.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Batch deterministic table profiling for reporting",
            "skill_package": f"{skillRoot().name} profile_artifacts.py",
            "note": "No scientific interpretation is performed here.",
        },
    )
    logging.getLogger(__name__).info("Profiled %d tables.", len(profiles))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
