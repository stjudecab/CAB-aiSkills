#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Render Quarto HTML/PDF bioinformatics reports from a normalized report model."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd
import yaml

from report_common import (
    detectFormat,
    detectPdfEngine,
    dumpJson,
    escapeHtml,
    loadStructuredFile,
    prepareEmbeddableFigure,
    skillRoot,
)

logger = logging.getLogger(__name__)

REPORT_BASENAME = "bioinformatics-report"


def sha256File(path: Path) -> str:
    """Return the SHA-256 hex digest of *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def findQuartoExecutable() -> Optional[str]:
    """Locate a Quarto CLI executable on PATH."""
    return shutil.which("quarto")


def copyThemeAssets(outputDir: Path) -> Path:
    """Copy the bundled SCSS theme into the report output directory."""
    source = skillRoot() / "assets" / "report.scss"
    destination = outputDir / "report.scss"
    if source.is_file():
        shutil.copy2(source, destination)
    else:
        destination.write_text(
            "/*-- scss:defaults --*/\n$primary: #17365D;\n/*-- scss:rules --*/\n",
            encoding="utf-8",
        )
    return destination


def stageModelArtifacts(
    model: Mapping[str, Any],
    baseDir: Path,
    outputDir: Path,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Copy referenced figures/tables into portable report subdirectories."""
    staged: List[Dict[str, Any]] = []
    warnings: List[str] = []
    figuresDir = outputDir / "figures"
    tablesDir = outputDir / "tables"
    figuresDir.mkdir(parents=True, exist_ok=True)
    tablesDir.mkdir(parents=True, exist_ok=True)

    for figure in model.get("figures") or []:
        rel = figure.get("path")
        if not rel:
            continue
        source = (baseDir / rel).resolve()
        if not source.is_file():
            warnings.append(f"Missing figure referenced in model: {rel}")
            continue
        embedPath, embedName, note = prepareEmbeddableFigure(source, figuresDir)
        if embedPath is None or embedName is None:
            warnings.append(note or f"Could not stage figure: {rel}")
            continue
        staged.append(
            {
                "source": source.as_posix(),
                "destination": embedPath.as_posix(),
                "report_path": f"figures/{embedName}",
                "sha256": sha256File(embedPath),
                "role": figure.get("role"),
                "note": note,
            }
        )
        figure["staged_path"] = f"figures/{embedName}"

    for table in model.get("tables") or []:
        rel = table.get("path")
        if not rel:
            continue
        source = (baseDir / rel).resolve()
        if not source.is_file():
            warnings.append(f"Missing table referenced in model: {rel}")
            continue
        safeName = Path(rel).name
        dest = tablesDir / safeName
        if not dest.exists():
            shutil.copy2(source, dest)
        staged.append(
            {
                "source": source.as_posix(),
                "destination": dest.as_posix(),
                "report_path": f"tables/{safeName}",
                "sha256": sha256File(dest),
                "role": table.get("role"),
            }
        )
        table["staged_path"] = f"tables/{safeName}"

    return staged, warnings


def loadNarrative(narrativePath: Optional[Path]) -> Dict[str, Any]:
    """Load optional agent-authored narrative YAML."""
    if narrativePath is None or not narrativePath.is_file():
        return {}
    data = loadStructuredFile(narrativePath)
    return data if isinstance(data, dict) else {}


def formatMarkdownTable(rows: Sequence[Sequence[Any]], headers: Sequence[str]) -> str:
    """Format a simple markdown table without external dependencies."""
    header = "| " + " | ".join(str(item) for item in headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def dataframePreviewMarkdown(path: Path, maxRows: int = 12) -> str:
    """Render a compact markdown preview of a tabular file."""
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        frame = pd.read_excel(path, nrows=maxRows)
    elif suffix in {".tsv", ".txt", ".bed", ".narrowpeak", ".broadpeak"}:
        frame = pd.read_csv(path, sep="\t", nrows=maxRows)
    elif suffix == ".csv":
        frame = pd.read_csv(path, nrows=maxRows)
    else:
        return "_Preview unavailable for this format._"
    frame = frame.head(maxRows)
    headers = [str(col) for col in frame.columns]
    rows = [list(row) for row in frame.fillna("").astype(str).itertuples(index=False, name=None)]
    return formatMarkdownTable(rows, headers)


def buildSummaryCards(model: Mapping[str, Any]) -> List[Tuple[str, str]]:
    """Build summary-card label/value pairs for the report banner."""
    cards: List[Tuple[str, str]] = []
    study = model.get("study") or {}
    cards.append(("Analyses", str(len(model.get("analyses") or []))))
    cards.append(("Figures", str(len(model.get("figures") or []))))
    cards.append(("Tables", str(len(model.get("tables") or []))))
    genome = (model.get("study_display") or {}).get("genome_build") or study.get("genome") or "Not specified"
    cards.append(("Genome build", str(genome)))
    return cards


def buildExecutiveSummary(model: Mapping[str, Any], narrative: Mapping[str, Any]) -> str:
    """Compose the executive summary section."""
    if narrative.get("executive_summary"):
        return str(narrative["executive_summary"]).strip()
    study = model.get("study") or {}
    title = study.get("title") or "Bioinformatics analysis"
    parts = [
        f"This report summarizes **existing** outputs for **{title}**. "
        "No primary differential, enrichment, or overlap statistics were recomputed for this document.",
        "",
        "**Key observations (from result files):**",
    ]
    for metric in model.get("metrics") or []:
        value = metric.get("value")
        description = metric.get("description") or metric.get("source_artifact") or "metric"
        if value is not None:
            parts.append(f"- **{description}:** {value}")
    if len(parts) <= 4:
        parts.append("- Review the staged tables and figures below for detailed results.")
    return "\n".join(parts)


def buildMethodsSection(model: Mapping[str, Any]) -> str:
    """Render methods text from manifest and detected upstream runs."""
    blocks: List[str] = []
    provenance = model.get("provenance") or {}
    if provenance.get("pipeline"):
        blocks.append(
            f"**Pipeline:** {provenance.get('pipeline')} "
            f"(version {provenance.get('pipeline_version', 'unspecified')})."
        )
    for method in model.get("methods") or []:
        title = method.get("title") or method.get("source_skill") or "Method"
        overview = method.get("overview") or ""
        if overview:
            blocks.append(f"**{title}:** {overview}")
    versions = model.get("versions") or []
    if versions:
        versionRows = [(item.get("name"), item.get("version"), item.get("source")) for item in versions[:15]]
        blocks.append("\n**Software versions (resolved from result directory):**\n")
        blocks.append(formatMarkdownTable(versionRows, ["Tool", "Version", "Source"]))
    if not blocks:
        blocks.append(
            "_Methods were not fully documented in the supplied manifest or run metadata. "
            "Inspect `run_metadata.json` files in the source results directory._"
        )
    return "\n\n".join(blocks)


def buildValidationTable(model: Mapping[str, Any]) -> str:
    """Build the result validation table."""
    validation = model.get("validation") or {}
    rows = [
        ("Manifest validation", "Pass" if validation.get("valid") else "Fail", "; ".join(validation.get("errors") or []) or "No fatal errors"),
        ("Warnings recorded", str(len(model.get("warnings") or [])), "See limitations section"),
        ("Metrics with provenance", str(len(model.get("metrics") or [])), "Computed from supplied tables only"),
    ]
    genomeStatus = (model.get("study_display") or {}).get("genome_build_status")
    if genomeStatus == "missing_critical":
        rows.append(("Genome build documented", "Missing", "Required for region-level interpretation"))
    return formatMarkdownTable(rows, ["Check", "Status", "Notes"])


def buildFigureBlocks(model: Mapping[str, Any]) -> str:
    """Render markdown figure blocks for staged artifacts."""
    blocks: List[str] = []
    for index, figure in enumerate(model.get("figures") or [], start=1):
        staged = figure.get("staged_path") or figure.get("path")
        if not staged:
            continue
        caption = figure.get("caption") or figure.get("role") or f"Figure {index}"
        suffix = Path(staged).suffix.lower()
        width = "85%" if suffix == ".pdf" else "90%"
        blocks.append(f"![{caption}]({staged}){{#fig-{index} width={width}}}\n")
        linked = figure.get("linked_table")
        if linked and linked.get("staged_path"):
            blocks.append(f"\nCompanion table: [`{linked.get('staged_path')}`]({linked['staged_path']})\n")
    if not blocks:
        blocks.append("_No figures were staged for this report._")
    return "\n".join(blocks)


def buildTableBlocks(model: Mapping[str, Any], outputDir: Path) -> str:
    """Render markdown sections for staged tables with compact previews."""
    blocks: List[str] = []
    for table in model.get("tables") or []:
        staged = table.get("staged_path") or table.get("path")
        if not staged:
            continue
        title = table.get("description") or table.get("role") or staged
        blocks.append(f"### {title}\n")
        tablePath = outputDir / staged
        if tablePath.is_file():
            blocks.append(dataframePreviewMarkdown(tablePath))
            blocks.append(f"\n[Download full table]({staged})\n")
        else:
            blocks.append(f"[Download table]({staged})\n")
    if not blocks:
        blocks.append("_No tables were staged for this report._")
    return "\n".join(blocks)


def buildAnalysisOverview(model: Mapping[str, Any]) -> str:
    """Render analysis overview rows."""
    rows = []
    for analysis in model.get("analyses") or []:
        comparison = analysis.get("comparison") or {}
        direction = ""
        if comparison.get("numerator") or comparison.get("denominator"):
            direction = f"{comparison.get('numerator', '?')} vs {comparison.get('denominator', '?')}"
        params = analysis.get("parameters") or {}
        threshold = params.get("fdr_threshold", params.get("padj_threshold", ""))
        rows.append(
            (
                analysis.get("id") or "",
                analysis.get("type") or "",
                analysis.get("title") or "",
                direction,
                threshold,
            )
        )
    if not rows:
        return "_No analyses were recorded in the report model._"
    return formatMarkdownTable(rows, ["ID", "Type", "Title", "Comparison", "FDR threshold"])


def generateQmd(
    model: Mapping[str, Any],
    outputDir: Path,
    narrative: Mapping[str, Any],
) -> Path:
    """Generate the Quarto markdown source file."""
    config = model.get("report_config") or {}
    study = model.get("study") or {}
    title = config.get("title") or study.get("title") or "Bioinformatics Report"
    subtitle = config.get("subtitle") or study.get("description") or ""
    author = config.get("author") or "Automated bioinformatics report"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cards = buildSummaryCards(model)
    cardHtml = []
    for label, value in cards:
        cardHtml.append(
            f'<div class="summary-card"><div class="label">{escapeHtml(label)}</div>'
            f'<div class="value">{escapeHtml(value)}</div></div>'
        )
    limitations = list(model.get("limitations") or [])
    limitations.extend(model.get("warnings") or [])
    limitationText = "\n".join(f"- {item}" for item in limitations) or "- None recorded."

    themes = narrative.get("biological_themes")
    if isinstance(themes, list):
        themesText = "\n".join(f"- {item}" for item in themes)
    elif isinstance(themes, str):
        themesText = themes.strip()
    else:
        themesText = "_No agent-authored biological themes were supplied. Interpret tables and figures cautiously._"

    titleEscaped = str(title).replace('"', '\\"')
    subtitleEscaped = str(subtitle).replace('"', '\\"')
    authorEscaped = str(author).replace('"', '\\"')

    qmd = f"""---
title: "{titleEscaped}"
subtitle: "{subtitleEscaped}"
author: "{authorEscaped}"
date: "{date}"
format:
  html:
    toc: true
    toc-depth: 3
    number-sections: true
    theme: report.scss
    embed-resources: true
    df-print: paged
  pdf:
    documentclass: article
    papersize: letter
    geometry:
      - margin=0.85in
    toc: true
    number-sections: true
    include-in-header:
      text: |
        \\usepackage{{float}}
        \\usepackage{{booktabs}}
        \\usepackage{{longtable}}
execute:
  echo: false
  warning: false
  message: false
---

```{{=html}}
<div class="report-banner">
  <div class="summary-grid">
    {''.join(cardHtml)}
  </div>
</div>
```

## Executive summary

{buildExecutiveSummary(model, narrative)}

::: {{.callout-warning title="Interpretation boundaries"}}
Statistical enrichment and overlap results indicate co-occurrence with annotated collections. They do **not** demonstrate pathway activation, causal regulation, or direction of effect unless supported by separate differential evidence with explicit comparison direction.
:::

## Analysis overview

{buildAnalysisOverview(model)}

## Methods

{buildMethodsSection(model)}

## Result validation and quality checks

{buildValidationTable(model)}

## Principal results — figures

{buildFigureBlocks(model)}

## Principal results — tables

{buildTableBlocks(model, outputDir)}

## Biological themes

{themesText}

## Limitations and warnings

{limitationText}

## Provenance appendix

| Artifact | Role | Format |
| -------- | ---- | ------ |
"""
    for analysis in model.get("analyses") or []:
        for artifact in analysis.get("artifacts") or []:
            qmd += (
                f"| `{artifact.get('path')}` | {artifact.get('role')} | "
                f"{artifact.get('format') or detectFormat(Path(str(artifact.get('path'))))} |\n"
            )

    qmdPath = outputDir / f"{REPORT_BASENAME}.qmd"
    qmdPath.write_text(qmd, encoding="utf-8")
    return qmdPath


def runQuartoRender(qmdPath: Path, outputDir: Path, formats: Sequence[str], logsDir: Path) -> Dict[str, Any]:
    """Invoke Quarto to render HTML and optional PDF."""
    logsDir.mkdir(parents=True, exist_ok=True)
    quarto = findQuartoExecutable()
    status: Dict[str, Any] = {
        "outputs": [],
        "warnings": [],
        "builds": [],
        "pdf_engine": detectPdfEngine(),
        "quarto": quarto or "not installed",
    }
    if quarto is None:
        status["warnings"].append("Quarto CLI not found; QMD source was written but not rendered.")
        return status

    for fmt in formats:
        logPath = logsDir / f"quarto_render_{fmt}.log"
        command = [quarto, "render", qmdPath.name, "--to", fmt, "--output-dir", outputDir.as_posix()]
        completed = subprocess.run(
            command,
            cwd=outputDir,
            capture_output=True,
            text=True,
            check=False,
        )
        logPath.write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
        status["builds"].append({"format": fmt, "returncode": completed.returncode, "log": logPath.as_posix()})
        if completed.returncode != 0:
            status["warnings"].append(f"Quarto render failed for format={fmt}; see {logPath.name}")
            continue
        if fmt == "html":
            htmlPath = outputDir / f"{REPORT_BASENAME}.html"
            if htmlPath.is_file():
                status["outputs"].append(htmlPath.as_posix())
        if fmt == "pdf":
            pdfPath = outputDir / f"{REPORT_BASENAME}.pdf"
            if pdfPath.is_file():
                status["outputs"].append(pdfPath.as_posix())
            elif status["pdf_engine"] is None:
                status["warnings"].append("PDF render requested but no PDF engine (pdflatex/xelatex) was detected.")
    return status


def rasterizePdfPages(pdfPath: Path, pagesDir: Path) -> List[str]:
    """Rasterize PDF pages for agent inspection when pdftoppm is available."""
    pagesDir.mkdir(parents=True, exist_ok=True)
    if not pdfPath.is_file() or shutil.which("pdftoppm") is None:
        return []
    prefix = pagesDir / "page"
    completed = subprocess.run(
        ["pdftoppm", "-png", "-r", "150", str(pdfPath), str(prefix)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return sorted(path.as_posix() for path in pagesDir.glob("page-*.png"))


def writeVerificationSummary(
    outputDir: Path,
    model: Mapping[str, Any],
    renderStatus: Mapping[str, Any],
    staged: Sequence[Mapping[str, Any]],
    formats: Sequence[str],
) -> Path:
    """Write authoritative verification JSON for the rendered bundle."""
    htmlPath = outputDir / f"{REPORT_BASENAME}.html"
    pdfPath = outputDir / f"{REPORT_BASENAME}.pdf"
    qmdPath = outputDir / f"{REPORT_BASENAME}.qmd"
    errors: List[str] = []
    warnings = list(renderStatus.get("warnings") or [])
    if not qmdPath.is_file():
        errors.append("Missing QMD source.")
    if "html" in {item.get("format") for item in renderStatus.get("builds") or []} and not htmlPath.is_file():
        errors.append("HTML render requested but bioinformatics-report.html is missing.")
    if htmlPath.is_file():
        html = htmlPath.read_text(encoding="utf-8")
        if "{{" in html and "}}" in html:
            errors.append("Unresolved template placeholders detected in HTML.")
        for match in re.findall(r"""<(?:img|a)[^>]+(?:src|href)=['"]([^'"]+)['"]""", html):
            if match.startswith(("http://", "https://", "#", "mailto:", "data:")):
                continue
            local = (outputDir / match.split("#", 1)[0]).resolve()
            if not local.exists():
                if match.endswith(".pdf") and "pdf" not in formats:
                    warnings.append(f"HTML references PDF download link but PDF was not requested: {match}")
                elif match.endswith(".pdf") and not pdfPath.is_file():
                    warnings.append(f"HTML references PDF download link but PDF was not rendered: {match}")
                else:
                    errors.append(f"Broken local link in HTML: {match}")
    pdfPages: List[str] = []
    if pdfPath.is_file():
        pdfPages = rasterizePdfPages(pdfPath, outputDir / "pdf_pages")
    summary = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "deliverables": {
            "qmd": qmdPath.as_posix() if qmdPath.is_file() else None,
            "html": htmlPath.as_posix() if htmlPath.is_file() else None,
            "pdf": pdfPath.as_posix() if pdfPath.is_file() else None,
            "pdf_page_count": len(pdfPages),
            "pdf_pages": pdfPages,
        },
        "staged_artifact_count": len(staged),
        "metrics_without_provenance": sum(
            1 for metric in model.get("metrics") or [] if not metric.get("source_artifact")
        ),
        "render": renderStatus,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    path = outputDir / "report_verification.json"
    dumpJson(summary, path)
    return path


def renderQuartoReport(
    model: Mapping[str, Any],
    baseDir: Path,
    outputDir: Path,
    formats: Sequence[str],
    logsDir: Path,
    narrativePath: Optional[Path] = None,
) -> Dict[str, Any]:
    """Stage artifacts, generate QMD, render HTML/PDF, and verify outputs."""
    outputDir.mkdir(parents=True, exist_ok=True)
    copyThemeAssets(outputDir)
    staged, stageWarnings = stageModelArtifacts(model, baseDir, outputDir)
    narrative = loadNarrative(narrativePath)
    if narrativePath and narrativePath.is_file():
        dumpJson(narrative, outputDir / "report_narrative.yaml")
    qmdPath = generateQmd(model, outputDir, narrative)
    renderStatus = runQuartoRender(qmdPath, outputDir, formats, logsDir)
    renderStatus["warnings"] = list(stageWarnings) + list(renderStatus.get("warnings") or [])
    renderStatus["qmd"] = qmdPath.as_posix()
    renderStatus["staged"] = list(staged)
    verificationPath = writeVerificationSummary(outputDir, model, renderStatus, staged, formats)
    renderStatus["verification"] = verificationPath.as_posix()
    renderStatus["outputs"] = list(renderStatus.get("outputs") or [])
    for candidate in (qmdPath, outputDir / f"{REPORT_BASENAME}.html", outputDir / f"{REPORT_BASENAME}.pdf"):
        if candidate.is_file() and candidate.as_posix() not in renderStatus["outputs"]:
            renderStatus["outputs"].append(candidate.as_posix())
    renderStatus["outputs"].append(verificationPath.as_posix())
    return renderStatus
