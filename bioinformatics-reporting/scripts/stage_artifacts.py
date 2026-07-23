#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Copy selected result artifacts into a portable report staging directory."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from quarto_report import sha256File
from run_logging import (
    addReproducibilityArguments,
    appendCommandLog,
    commandLineString,
    configureLogging,
    runIdUtc,
    writeAgentArtifacts,
    writeRunMetadata,
)
from report_common import collectToolVersions, dumpJson, dumpYaml, loadStructuredFile, skillRoot


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Stage portable report artifacts with checksums.")
    parser.add_argument(
        "--manifest",
        dest="manifest",
        default="",
        help="Manifest YAML/JSON listing artifacts to stage.",
    )
    parser.add_argument(
        "--selection",
        dest="selection",
        default="",
        help="TSV with columns source_path,destination_rel (alternative to manifest).",
    )
    parser.add_argument(
        "--baseDir",
        dest="baseDir",
        required=True,
        help="Base directory for relative source paths.",
    )
    parser.add_argument(
        "--stageDir",
        dest="stageDir",
        required=True,
        help="Destination staging directory (figures/, tables/ created as needed).",
    )
    parser.add_argument(
        "--inventory",
        dest="inventory",
        default="",
        help="Optional artifact_inventory.tsv output path.",
    )
    addReproducibilityArguments(parser)
    return parser


def loadSelection(manifestPath: Path, selectionPath: Path, baseDir: Path) -> List[Dict[str, str]]:
    """Load staging pairs from manifest artifacts or a TSV selection file."""
    pairs: List[Dict[str, str]] = []
    if selectionPath.is_file():
        with selectionPath.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                source = row.get("source_path") or row.get("source")
                dest = row.get("destination_rel") or row.get("destination")
                if source and dest:
                    pairs.append({"source": source, "destination": dest})
        return pairs

    manifest = loadStructuredFile(manifestPath)
    for analysis in manifest.get("analyses") or []:
        for artifact in analysis.get("artifacts") or []:
            rel = artifact.get("path")
            if not rel:
                continue
            role = artifact.get("role", "other")
            if role.endswith("_plot") or role in {"pca_plot", "heatmap", "coverage_plot", "enrichment_plot", "upset_plot", "venn_plot", "supplementary_figure"}:
                dest = f"figures/{Path(rel).name}"
            else:
                dest = f"tables/{Path(rel).name}"
            pairs.append({"source": rel, "destination": dest})
    return pairs


def stageArtifacts(pairs: List[Dict[str, str]], baseDir: Path, stageDir: Path) -> Dict[str, Any]:
    """Copy artifacts and record SHA-256 checksums."""
    staged: List[Dict[str, Any]] = []
    errors: List[str] = []
    for pair in pairs:
        source = (baseDir / pair["source"]).resolve()
        dest = (stageDir / pair["destination"]).resolve()
        if not source.is_file():
            errors.append(f"Missing source artifact: {source}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(source.read_bytes())
        staged.append(
            {
                "source": source.as_posix(),
                "destination": dest.as_posix(),
                "destination_rel": pair["destination"],
                "sha256": sha256File(dest),
            }
        )
    return {"staged": staged, "errors": errors}


def main() -> None:
    """Stage selected artifacts for report rendering."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    baseDir = Path(args.baseDir).expanduser().resolve()
    stageDir = Path(args.stageDir).expanduser().resolve()
    outputDir = Path(args.outputDir).expanduser().resolve() if args.outputDir else stageDir
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "stage_artifacts.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    manifestPath = Path(args.manifest).expanduser().resolve() if args.manifest else Path()
    selectionPath = Path(args.selection).expanduser().resolve() if args.selection else Path()
    if not manifestPath.is_file() and not selectionPath.is_file():
        logging.getLogger(__name__).error("Provide --manifest or --selection.")
        sys.exit(2)

    pairs = loadSelection(manifestPath, selectionPath, baseDir)
    result = stageArtifacts(pairs, baseDir, stageDir)
    if result["errors"]:
        logging.getLogger(__name__).error("Staging errors: %s", result["errors"])
        sys.exit(2)

    inventoryPath = Path(args.inventory).expanduser().resolve() if args.inventory else stageDir / "artifact_inventory.tsv"
    inventoryPath.parent.mkdir(parents=True, exist_ok=True)
    with inventoryPath.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "destination", "destination_rel", "sha256"],
            delimiter="\t",
        )
        writer.writeheader()
        for row in result["staged"]:
            writer.writerow(row)

    summaryPath = stageDir / "staging_summary.json"
    dumpJson({"staged_count": len(result["staged"]), "artifacts": result["staged"]}, summaryPath)

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="stage_artifacts.py",
        runId=runId,
        inputs=[
            {"path": manifestPath.as_posix() if manifestPath.is_file() else selectionPath.as_posix(), "label": "selection"},
            {"path": baseDir.as_posix(), "label": "baseDir"},
        ],
        outputDirectory=outputDir,
        outputPrefix=stageDir.as_posix(),
        parameters={"inventory": inventoryPath.as_posix()},
        toolVersions=collectToolVersions(),
        summary={"staged_count": len(result["staged"])},
        outputs=[inventoryPath.as_posix(), summaryPath.as_posix()],
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "stage_artifacts.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Read-only artifact staging with SHA-256 checksums",
            "skill_package": f"{skillRoot().name} stage_artifacts.py",
            "note": "Source result files are never modified.",
        },
    )
    logging.getLogger(__name__).info("Staged %d artifacts under %s", len(result["staged"]), stageDir)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
