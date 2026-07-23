#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Render HTML/PDF reports from a normalized report model via Quarto."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

from quarto_report import renderQuartoReport
from run_logging import (
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
    detectPdfEngine,
    dumpJson,
    dumpYaml,
    loadStructuredFile,
    profileTable,
    skillRoot,
    validateManifest,
)


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Render Quarto HTML/PDF bioinformatics reports.")
    parser.add_argument(
        "--reportModel",
        dest="reportModel",
        default="",
        help="Normalized report-model JSON path.",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest",
        default="",
        help="Optional manifest path (used when report model must be built first).",
    )
    parser.add_argument(
        "--outputDir",
        dest="outputDir",
        required=True,
        help="Report output directory.",
    )
    parser.add_argument(
        "--formats",
        dest="formats",
        default="html,pdf",
        help="Comma-separated formats: html,pdf",
    )
    parser.add_argument(
        "--baseDir",
        dest="baseDir",
        default="",
        help="Base directory for artifact paths during rendering.",
    )
    parser.add_argument(
        "--narrative",
        dest="narrative",
        default="",
        help="Optional report_narrative.yaml with agent-authored prose sections.",
    )
    repro = parser.add_argument_group("reproducibility")
    repro.add_argument(
        "--runId",
        dest="runId",
        default="",
        help="UTC run ID (YYYYMMDDTHHMMSSZ). Default: generated at execution time.",
    )
    repro.add_argument(
        "--agentRequest",
        dest="agentRequest",
        default="",
        help="Verbatim user request for this run (written as agent_request.txt).",
    )
    repro.add_argument(
        "--agentRequestFile",
        dest="agentRequestFile",
        default="",
        help="Path to a text file containing the user request.",
    )
    repro.add_argument(
        "--agentWorkflow",
        dest="agentWorkflow",
        default="",
        help="Free-form markdown describing agent workflow steps.",
    )
    repro.add_argument(
        "--agentWorkflowFile",
        dest="agentWorkflowFile",
        default="",
        help="Path to an existing agent_workflow.md to copy into the output directory.",
    )
    return parser


def writeReportManifest(
    model: Mapping[str, Any],
    outputDir: Path,
    outputs: List[str],
    verificationPath: str,
) -> Path:
    """Write the report manifest describing deliverables and provenance."""
    verification = {}
    verificationFile = Path(verificationPath)
    if verificationFile.is_file():
        verification = json.loads(verificationFile.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "1.0",
        "generated_at": model.get("generated_at"),
        "study": model.get("study"),
        "deliverables": outputs,
        "artifacts": [],
        "warnings": model.get("warnings") or [],
        "software": model.get("software") or [],
        "provenance": model.get("provenance") or {},
        "validation": model.get("validation") or {},
        "report_model": "report-model.json",
        "report_narrative": "report_narrative.yaml",
        "quarto_source": "bioinformatics-report.qmd",
        "verification": verificationPath,
        "render_status": {
            "valid": verification.get("valid"),
            "errors": verification.get("errors") or [],
            "warnings": verification.get("warnings") or [],
        },
    }
    for analysis in model.get("analyses") or []:
        for artifact in analysis.get("artifacts") or []:
            manifest["artifacts"].append(artifact)
    manifestPath = outputDir / "report_manifest.yaml"
    dumpYaml(manifest, manifestPath)
    return manifestPath


def main() -> None:
    """Render report deliverables from a report model."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    outputDir = Path(args.outputDir).expanduser().resolve()
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "render_report.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    if args.reportModel:
        modelPath = Path(args.reportModel).expanduser().resolve()
        model = json.loads(modelPath.read_text(encoding="utf-8"))
        baseDir = Path(args.baseDir).expanduser().resolve() if args.baseDir else modelPath.parent
    elif args.manifest:
        modelPath = outputDir / "report-model.json"
        manifestPath = Path(args.manifest).expanduser().resolve()
        baseDir = Path(args.baseDir).expanduser().resolve() if args.baseDir else manifestPath.parent
        manifest = loadStructuredFile(manifestPath)
        validation = validateManifest(manifest, baseDir)
        if not validation.get("valid"):
            logging.getLogger(__name__).error("Manifest invalid: %s", validation.get("errors"))
            sys.exit(2)
        profiles = {}
        for analysis in manifest.get("analyses") or []:
            for artifact in analysis.get("artifacts") or []:
                rel = artifact.get("path")
                if not rel or rel in profiles:
                    continue
                resolved = (baseDir / rel).resolve()
                if resolved.suffix.lower() in TABLE_EXTENSIONS and resolved.is_file():
                    profiles[rel] = profileTable(resolved)
        model = buildReportModel(manifest, baseDir, profiles, validation)
        dumpJson(model, modelPath)
    else:
        logging.getLogger(__name__).error("Provide --reportModel or --manifest.")
        sys.exit(2)

    formats = [item.strip().lower() for item in args.formats.split(",") if item.strip()]
    dumpJson(model, outputDir / "report-model.json")
    narrativePath = Path(args.narrative).expanduser().resolve() if args.narrative else None

    renderStatus = renderQuartoReport(
        model,
        baseDir,
        outputDir,
        formats,
        outputDir / "logs",
        narrativePath=narrativePath,
    )
    outputs: List[str] = list(renderStatus.get("outputs") or [])
    verificationPath = renderStatus.get("verification", "")
    manifestPath = writeReportManifest(model, outputDir, outputs, verificationPath)
    outputs.append(manifestPath.as_posix())

    verification = {}
    if verificationPath and Path(verificationPath).is_file():
        verification = json.loads(Path(verificationPath).read_text(encoding="utf-8"))

    pdfEngine = detectPdfEngine()
    htmlPath = outputDir / "bioinformatics-report.html"
    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="render_report.py",
        runId=runId,
        inputs=[{"path": str(args.reportModel or args.manifest), "label": "report input"}],
        outputDirectory=outputDir,
        outputPrefix=outputDir.as_posix(),
        parameters={"formats": formats, "baseDir": baseDir.as_posix(), "narrative": args.narrative or None},
        toolVersions=collectToolVersions(),
        summary={
            "html": htmlPath.as_posix() if htmlPath.is_file() else None,
            "pdf": (outputDir / "bioinformatics-report.pdf").as_posix()
            if (outputDir / "bioinformatics-report.pdf").is_file()
            else None,
            "qmd": renderStatus.get("qmd"),
            "verification_valid": verification.get("valid"),
            "pdf_engine": pdfEngine,
            "staged_artifact_count": len(renderStatus.get("staged") or []),
        },
        outputs=outputs,
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "render_report.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Quarto QMD source + HTML/PDF rendering with portable staged artifacts",
            "skill_package": f"{skillRoot().name} render_report.py",
            "note": "Scientific narrative must remain traceable to report-model.json metrics.",
        },
    )
    for warning in renderStatus.get("warnings") or []:
        logging.getLogger(__name__).warning(warning)
    if verification and not verification.get("valid"):
        logging.getLogger(__name__).error("Report verification failed: %s", verification.get("errors"))
        sys.exit(3)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
