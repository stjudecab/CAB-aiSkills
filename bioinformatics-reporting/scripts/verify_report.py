#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Verify generated bioinformatics report deliverables."""

from __future__ import annotations

import argparse
import json
import logging
import re
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
from report_common import collectToolVersions, dumpJson, skillRoot
from quarto_report import rasterizePdfPages


def buildParser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Verify report deliverables and local links.")
    parser.add_argument(
        "--reportDir",
        dest="reportDir",
        required=True,
        help="Directory containing rendered report outputs.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default="",
        help="Verification summary JSON path (default: reportDir/report_verification.json).",
    )
    addReproducibilityArguments(parser)
    return parser


def verifyReport(reportDir: Path) -> dict:
    """Verify expected report files and basic HTML integrity."""
    errors: list[str] = []
    warnings: list[str] = []
    expected = [
        "bioinformatics-report.qmd",
        "report-model.json",
        "report_manifest.yaml",
    ]
    present = []
    for name in expected:
        path = reportDir / name
        if path.is_file():
            present.append(name)
        else:
            errors.append(f"Missing expected deliverable: {name}")

    htmlPath = reportDir / "bioinformatics-report.html"
    pdfPath = reportDir / "bioinformatics-report.pdf"
    if htmlPath.is_file():
        present.append("bioinformatics-report.html")
        html = htmlPath.read_text(encoding="utf-8")
        if "{{" in html and "}}" in html:
            errors.append("Unresolved template variables detected in HTML output.")
        if re.search(r"<img[^>]+src=['\"]https?://", html):
            warnings.append("HTML references external image URLs.")
        for match in re.findall(r"""<(?:img|a)[^>]+(?:src|href)=['"]([^'"]+)['"]""", html):
            if match.startswith(("http://", "https://", "#", "mailto:", "data:")):
                continue
            local_target = match.split("#", 1)[0]
            if not local_target:
                continue
            linked = (reportDir / local_target).resolve()
            if not linked.exists():
                if local_target.endswith(".pdf") and not pdfPath.is_file():
                    warnings.append(f"HTML references PDF download link but PDF was not rendered: {match}")
                else:
                    errors.append(f"Broken local link in HTML: {match}")
    else:
        warnings.append("HTML deliverable not found.")

    modelPath = reportDir / "report-model.json"
    metricsWithoutProvenance = 0
    if modelPath.is_file():
        model = json.loads(modelPath.read_text(encoding="utf-8"))
        for metric in model.get("metrics") or []:
            if not metric.get("source_artifact"):
                metricsWithoutProvenance += 1
        if not model.get("study", {}).get("genome") and (
            (model.get("study_display") or {}).get("genome_build_status") == "missing_critical"
        ):
            warnings.append("Genome build missing from report model for region-level outputs.")
        if model.get("warnings"):
            warnings.extend([f"Report model warning: {item}" for item in model["warnings"][:5]])
    else:
        errors.append("Missing report-model.json")

    pdfPages: list[str] = []
    if pdfPath.is_file():
        present.append("bioinformatics-report.pdf")
        pdfPages = rasterizePdfPages(pdfPath, reportDir / "pdf_pages")
    else:
        warnings.append("No PDF deliverable found (may be expected when Quarto/PDF dependencies are unavailable).")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "present_deliverables": present,
        "metrics_without_provenance": metricsWithoutProvenance,
        "pdf_found": pdfPath.is_file(),
        "pdf_page_count": len(pdfPages),
        "pdf_pages": pdfPages,
    }


def main() -> None:
    """Verify a rendered report directory."""
    from skill_env import bootstrap

    bootstrap()
    parser = buildParser()
    args = parser.parse_args()
    runId = args.runId or runIdUtc()
    reportDir = Path(args.reportDir).expanduser().resolve()
    outputDir = Path(args.outputDir).expanduser().resolve() if args.outputDir else reportDir
    outputDir.mkdir(parents=True, exist_ok=True)
    logFile = outputDir / "logs" / "verify_report.log"
    configureLogging(logFile)
    appendCommandLog(outputDir / "logs" / "commands.log", runId, commandLineString())
    writeAgentArtifacts(outputDir, args)

    summary = verifyReport(reportDir)
    summaryPath = Path(args.output).expanduser().resolve() if args.output else reportDir / "report_verification.json"
    dumpJson(summary, summaryPath)

    writeRunMetadata(
        outputDir / "run_metadata.json",
        skill="bioinformatics-reporting",
        script="verify_report.py",
        runId=runId,
        inputs=[{"path": reportDir.as_posix(), "label": "reportDir"}],
        outputDirectory=outputDir,
        outputPrefix=reportDir.as_posix(),
        parameters={},
        toolVersions=collectToolVersions(),
        summary={
            "valid": summary.get("valid"),
            "error_count": len(summary.get("errors") or []),
            "warning_count": len(summary.get("warnings") or []),
        },
        outputs=[summaryPath.as_posix()],
        agentRequestFile=outputDir / "agent_request.txt" if (outputDir / "agent_request.txt").exists() else None,
        agentWorkflowFile=outputDir / "agent_workflow.md" if (outputDir / "agent_workflow.md").exists() else None,
        logs={
            "verify_report.log": logFile.resolve().as_posix(),
            "commands.log": (outputDir / "logs" / "commands.log").resolve().as_posix(),
        },
        attribution={
            "method": "Quarto report bundle verification (links, placeholders, PDF pages)",
            "skill_package": f"{skillRoot().name} verify_report.py",
            "note": "report_verification.json is the authoritative verification record.",
        },
    )
    if not summary.get("valid"):
        logging.getLogger(__name__).error("Verification failed: %s", summary.get("errors"))
        sys.exit(2)
    logging.getLogger(__name__).info("Verification passed with %d warnings.", len(summary.get("warnings") or []))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).error("%s", exc)
        sys.exit(1)
