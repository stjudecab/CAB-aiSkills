#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `bioinformatics-reporting` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Shared discovery, validation, profiling, and report-model utilities."""

from __future__ import annotations

import base64
import csv
import html
import json
import logging
import mimetypes
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd
import yaml

from upstream_skills import (
    discoverUpstreamSkills,
    evaluateGenomeBuildDisplay,
    loadUpstreamRegistry,
    mergeUpstreamMethodsIntoModel,
)

SKILL_NAME = "bioinformatics-reporting"
SCHEMA_VERSION = "1.0"

CONFIDENCE_EXPLICIT = "explicit"
CONFIDENCE_HIGH = "high-confidence inference"
CONFIDENCE_TENTATIVE = "tentative inference"
CONFIDENCE_UNKNOWN = "unknown"

ARTIFACT_ROLES: Tuple[str, ...] = (
    "sample_metadata",
    "study_design",
    "qc_metrics",
    "sequencing_qc",
    "alignment_qc",
    "sample_qc",
    "count_matrix",
    "normalized_matrix",
    "primary_results",
    "differential_expression",
    "differential_accessibility",
    "differential_binding",
    "differential_methylation",
    "genomic_regions",
    "annotation_results",
    "motif_enrichment",
    "pathway_enrichment",
    "gsea_results",
    "overlap_results",
    "correlation_results",
    "pca_plot",
    "heatmap",
    "volcano_plot",
    "ma_plot",
    "coverage_plot",
    "enrichment_plot",
    "upset_plot",
    "venn_plot",
    "methods",
    "parameters",
    "provenance",
    "warnings",
    "supplementary_table",
    "supplementary_figure",
    "unknown",
)

TABLE_EXTENSIONS = {".csv", ".tsv", ".txt", ".bed", ".narrowpeak", ".broadpeak", ".xlsx"}
FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".gif", ".webp"}
TEXT_EXTENSIONS = {".md", ".log", ".yaml", ".yml", ".json", ".toml"}
IGNORE_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "conda-env",
    "logs",
    "tmp",
}
IGNORE_FILE_PATTERNS = (
    re.compile(r"^\."),
    re.compile(r"\.pyc$"),
    re.compile(r"~$"),
)

DEFAULT_REPORT_CONFIG: Dict[str, Any] = {
    "title": None,
    "subtitle": None,
    "author": None,
    "organization": None,
    "logo": "${skillLoc}/assets/CAB-aiSkills_bioinformatics-reporting.white.svg",
    "primary_color": "#17365D",
    "accent_color": "#267F8E",
    "include_toc": True,
    "self_contained_html": True,
    "render_pdf": True,
}

COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "identifier": ("gene", "genesymbol", "gene_symbol", "symbol", "geneid", "gene_id", "feature", "name", "region"),
    "log2fc": ("log2fc", "log2foldchange", "logfc", "lfc", "foldchange"),
    "significance": ("padj", "fdr", "qvalue", "q_value", "adjpval", "adj_pval", "fdr_pval"),
    "pvalue": ("pvalue", "pval", "p_value", "pval_raw"),
    "chromosome": ("chr", "chrom", "chromosome"),
    "start": ("start", "chromstart"),
    "end": ("end", "chromend", "stop"),
}

ROLE_FILENAME_RULES: Tuple[Tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"volcano", re.I), "volcano_plot", CONFIDENCE_HIGH),
    (re.compile(r"\bma[_\.-]?plot|\bma\.", re.I), "ma_plot", CONFIDENCE_HIGH),
    (re.compile(r"\bpca\b", re.I), "pca_plot", CONFIDENCE_HIGH),
    (re.compile(r"heatmap", re.I), "heatmap", CONFIDENCE_HIGH),
    (re.compile(r"upset", re.I), "upset_plot", CONFIDENCE_HIGH),
    (re.compile(r"venn", re.I), "venn_plot", CONFIDENCE_HIGH),
    (re.compile(r"coverage", re.I), "coverage_plot", CONFIDENCE_TENTATIVE),
    (re.compile(r"enrich", re.I), "enrichment_plot", CONFIDENCE_TENTATIVE),
    (re.compile(r"sample.*metadata|metadata.*sample", re.I), "sample_metadata", CONFIDENCE_HIGH),
    (re.compile(r"deseq|deg|differential.*expr", re.I), "differential_expression", CONFIDENCE_TENTATIVE),
    (re.compile(r"differential.*peak|diff.*access|atac.*diff|da_peaks", re.I), "differential_accessibility", CONFIDENCE_TENTATIVE),
    (re.compile(r"chip.*diff|diff.*bind|cut.*run|cut.*tag", re.I), "differential_binding", CONFIDENCE_TENTATIVE),
    (re.compile(r"methyl|dmr|dmc", re.I), "differential_methylation", CONFIDENCE_TENTATIVE),
    (re.compile(r"pathway|enrichr|ora", re.I), "pathway_enrichment", CONFIDENCE_TENTATIVE),
    (re.compile(r"gsea|prerank|nes", re.I), "gsea_results", CONFIDENCE_TENTATIVE),
    (re.compile(r"motif|meme|homer", re.I), "motif_enrichment", CONFIDENCE_TENTATIVE),
    (re.compile(r"overlap|intersect|intervene", re.I), "overlap_results", CONFIDENCE_TENTATIVE),
    (re.compile(r"qc|fastqc|multiqc|qualimap", re.I), "sequencing_qc", CONFIDENCE_TENTATIVE),
    (re.compile(r"count.*matrix|counts\.|featurecounts", re.I), "count_matrix", CONFIDENCE_TENTATIVE),
)


def skillRoot() -> Path:
    """Return the bioinformatics-reporting skill root directory.

    Returns:
        Path: Absolute path to the skill package root.
    """
    return Path(__file__).resolve().parent.parent


def escapeHtml(text: Any) -> str:
    """Escape untrusted text for HTML embedding.

    Args:
        text (Any): Value to escape.

    Returns:
        str: HTML-safe string.
    """
    return html.escape("" if text is None else str(text), quote=True)


def loadStructuredFile(path: Path) -> Any:
    """Load YAML or JSON from *path*.

    Args:
        path (Path): Input file path.

    Returns:
        Any: Parsed structured content.

    Raises:
        ValueError: When the file extension is unsupported.
    """
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    if suffix == ".json":
        return json.loads(text)
    raise ValueError(f"Unsupported structured file extension: {path}")


def dumpYaml(data: Mapping[str, Any], path: Path) -> None:
    """Write *data* as YAML to *path*.

    Args:
        data (Mapping[str, Any]): Serializable mapping.
        path (Path): Destination path.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=True), encoding="utf-8")


def dumpJson(data: Mapping[str, Any], path: Path) -> None:
    """Write *data* as JSON to *path*.

    Args:
        data (Mapping[str, Any]): Serializable mapping.
        path (Path): Destination path.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def shouldIgnorePath(path: Path) -> bool:
    """Return True when *path* should be excluded from discovery.

    Args:
        path (Path): Candidate filesystem path.

    Returns:
        bool: True if the path should be ignored.
    """
    for part in path.parts:
        if part in IGNORE_DIR_NAMES:
            return True
    name = path.name
    for pattern in IGNORE_FILE_PATTERNS:
        if pattern.search(name):
            return True
    return False


def detectFormat(path: Path) -> str:
    """Infer a simple format label from the file extension.

    Args:
        path (Path): Input file path.

    Returns:
        str: Lowercase format label.
    """
    suffix = path.suffix.lower()
    if suffix == ".tsv":
        return "tsv"
    if suffix == ".csv":
        return "csv"
    if suffix in {".txt", ".log"}:
        return "txt"
    if suffix == ".xlsx":
        return "xlsx"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix == ".json":
        return "json"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return suffix.lstrip(".")
    if suffix == ".svg":
        return "svg"
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".html":
        return "html"
    if suffix == ".bed":
        return "bed"
    return suffix.lstrip(".") or "unknown"


def classifyArtifact(path: Path, columns: Optional[Sequence[str]] = None) -> Tuple[str, str]:
    """Infer artifact role and confidence from filename and optional columns.

    Args:
        path (Path): Artifact path.
        columns (Optional[Sequence[str]]): Optional table column names.

    Returns:
        tuple[str, str]: Role and confidence label.
    """
    joined = path.as_posix().lower()
    for pattern, role, confidence in ROLE_FILENAME_RULES:
        if pattern.search(joined):
            return role, confidence

    if columns:
        lowered = {str(col).lower() for col in columns}
        if lowered & set(COLUMN_ALIASES["log2fc"]) and lowered & set(COLUMN_ALIASES["significance"]):
            if "peak" in joined or path.suffix.lower() in {".bed", ".narrowpeak", ".broadpeak"}:
                return "differential_accessibility", CONFIDENCE_HIGH
            return "differential_expression", CONFIDENCE_HIGH
        if lowered & set(COLUMN_ALIASES["chromosome"]) and lowered & set(COLUMN_ALIASES["start"]):
            return "genomic_regions", CONFIDENCE_HIGH

    suffix = path.suffix.lower()
    if suffix in FIGURE_EXTENSIONS:
        return "supplementary_figure", CONFIDENCE_TENTATIVE
    if suffix in TABLE_EXTENSIONS:
        return "supplementary_table", CONFIDENCE_TENTATIVE
    if suffix in TEXT_EXTENSIONS:
        return "supplementary_table", CONFIDENCE_UNKNOWN
    return "unknown", CONFIDENCE_UNKNOWN


def readTableHeader(path: Path) -> List[str]:
    """Read only the header row from a supported table file.

    Args:
        path (Path): Table path.

    Returns:
        list[str]: Column names when readable, else empty list.
    """
    suffix = path.suffix.lower()
    try:
        if suffix == ".xlsx":
            frame = pd.read_excel(path, nrows=0)
            return [str(col) for col in frame.columns]
        delimiter = "\t" if suffix in {".tsv", ".txt", ".bed", ".narrowpeak", ".broadpeak"} else ","
        with open(path, encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            row = next(reader, [])
            return [str(col) for col in row]
    except Exception as exc:
        logging.getLogger(__name__).warning("Could not read header for %s: %s", path, exc)
        return []


def discoverArtifacts(
    resultsDir: Path,
    *,
    maxFiles: int = 5000,
) -> Dict[str, Any]:
    """Recursively inventory candidate artifacts under *resultsDir*.

    Args:
        resultsDir (Path): Root directory to scan.
        maxFiles (int): Maximum number of files to inventory.

    Returns:
        dict[str, Any]: Discovery payload with artifact inventory entries.
    """
    if not resultsDir.is_dir():
        raise FileNotFoundError(f"Results directory not found: {resultsDir}")

    artifacts: List[Dict[str, Any]] = []
    count = 0
    for path in sorted(resultsDir.rglob("*")):
        if not path.is_file() or shouldIgnorePath(path.relative_to(resultsDir)):
            continue
        count += 1
        if count > maxFiles:
            logging.getLogger(__name__).warning(
                "Discovery stopped at maxFiles=%d under %s", maxFiles, resultsDir
            )
            break
        relPath = path.relative_to(resultsDir).as_posix()
        columns: List[str] = []
        if path.suffix.lower() in TABLE_EXTENSIONS:
            columns = readTableHeader(path)
        role, confidence = classifyArtifact(path, columns)
        artifacts.append(
            {
                "path": relPath,
                "role": role,
                "format": detectFormat(path),
                "confidence": confidence,
                "description": None,
                "columns": columns[:20],
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "results_dir": resultsDir.resolve().as_posix(),
        "artifacts": artifacts,
    }


def normalizeManifest(manifest: Mapping[str, Any], baseDir: Path) -> Dict[str, Any]:
    """Normalize a study manifest, resolving relative artifact paths.

    Args:
        manifest (Mapping[str, Any]): Raw manifest content.
        baseDir (Path): Base directory for relative paths.

    Returns:
        dict[str, Any]: Normalized manifest copy.
    """
    normalized = json.loads(json.dumps(manifest))
    analyses = normalized.get("analyses") or []
    for analysis in analyses:
        for artifact in analysis.get("artifacts") or []:
            rel = artifact.get("path")
            if rel:
                resolved = (baseDir / rel).resolve()
                artifact["resolved_path"] = resolved.as_posix()
                artifact["exists"] = resolved.is_file()
    if normalized.get("samples", {}).get("metadata"):
        metaRel = normalized["samples"]["metadata"]
        metaPath = (baseDir / metaRel).resolve()
        normalized["samples"]["metadata_resolved"] = metaPath.as_posix()
        normalized["samples"]["metadata_exists"] = metaPath.is_file()
    return normalized


def validateManifest(
    manifest: Mapping[str, Any],
    baseDir: Path,
) -> Dict[str, Any]:
    """Validate manifest schema, paths, and recommended fields.

    Args:
        manifest (Mapping[str, Any]): Manifest content.
        baseDir (Path): Base directory for relative artifact paths.

    Returns:
        dict[str, Any]: Validation report with errors and warnings lists.
    """
    errors: List[str] = []
    warnings: List[str] = []
    normalized = normalizeManifest(manifest, baseDir)

    if manifest.get("schema_version") not in {SCHEMA_VERSION, None}:
        warnings.append(
            f"schema_version {manifest.get('schema_version')!r} differs from supported {SCHEMA_VERSION}"
        )

    analyses = normalized.get("analyses") or []
    if not analyses:
        warnings.append("No analyses[] entries supplied.")

    readableCount = 0
    seenPaths: Dict[str, str] = {}
    for analysis in analyses:
        analysisId = analysis.get("id") or "<unnamed>"
        analysisType = analysis.get("type")
        if not analysisType:
            warnings.append(f"Analysis {analysisId}: missing type.")
        comparison = analysis.get("comparison") or {}
        if comparison and not comparison.get("numerator") and not comparison.get("denominator"):
            warnings.append(f"Analysis {analysisId}: comparison direction incomplete.")
        params = analysis.get("parameters") or {}
        if not params.get("fdr_threshold") and not params.get("padj_threshold"):
            warnings.append(f"Analysis {analysisId}: no FDR/padj threshold recorded.")
        for artifact in analysis.get("artifacts") or []:
            rel = artifact.get("path")
            role = artifact.get("role", "unknown")
            if role not in ARTIFACT_ROLES:
                warnings.append(f"Analysis {analysisId}: custom role {role!r}.")
            if not rel:
                errors.append(f"Analysis {analysisId}: artifact missing path.")
                continue
            if rel in seenPaths:
                warnings.append(f"Duplicate artifact path {rel!r} in analyses {seenPaths[rel]} and {analysisId}.")
            else:
                seenPaths[rel] = analysisId
            if not artifact.get("exists"):
                errors.append(f"Analysis {analysisId}: missing file {rel}")
            else:
                readableCount += 1

    upstream = discoverUpstreamSkills(baseDir, manifest, skillRoot())
    registry = loadUpstreamRegistry(skillRoot())
    genomeLabel, genomeStatus, genomeWarnings = evaluateGenomeBuildDisplay(manifest, upstream, registry)
    normalized["upstream_skills"] = upstream
    normalized["study_display"] = {
        "genome_build": genomeLabel,
        "genome_build_status": genomeStatus,
    }
    warnings.extend(genomeWarnings)
    if not normalized.get("provenance"):
        warnings.append("Provenance block missing.")

    if readableCount == 0 and analyses:
        errors.append("All referenced primary files are missing.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "normalized_manifest": normalized,
        "readable_artifact_count": readableCount,
    }


def canonicalColumnName(name: str) -> Optional[str]:
    """Map a column name to a canonical semantic role when recognized.

    Args:
        name (str): Original column name.

    Returns:
        Optional[str]: Canonical role label or None.
    """
    lowered = name.strip().lower().replace("-", "_").replace(" ", "_")
    for canonical, aliases in COLUMN_ALIASES.items():
        if lowered in aliases or lowered == canonical:
            return canonical
    return None


def profileTable(
    path: Path,
    *,
    maxRows: int = 10000,
    previewRows: int = 20,
    sampleRows: int = 5000,
) -> Dict[str, Any]:
    """Safely profile a supported table without full scientific interpretation.

    Args:
        path (Path): Table file path.
        maxRows (int): Maximum rows to read for profiling.
        previewRows (int): Rows to retain in the preview subset.
        sampleRows (int): Rows to scan when the file exceeds *maxRows*.

    Returns:
        dict[str, Any]: Deterministic profile JSON.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Table not found: {path}")

    suffix = path.suffix.lower()
    profile: Dict[str, Any] = {
        "path": path.as_posix(),
        "format": detectFormat(path),
        "readable": False,
        "row_count": None,
        "column_count": None,
        "columns": [],
        "semantic_columns": {},
        "missing_values": {},
        "value_ranges": {},
        "preview": {"rows": [], "selection": f"first {previewRows} rows after header"},
        "warnings": [],
    }

    try:
        if suffix == ".xlsx":
            frame = pd.read_excel(path, nrows=maxRows)
        elif suffix in {".tsv", ".txt", ".bed", ".narrowpeak", ".broadpeak"}:
            frame = pd.read_csv(path, sep="\t", nrows=maxRows, dtype=str, low_memory=False)
        elif suffix == ".csv":
            frame = pd.read_csv(path, nrows=maxRows, dtype=str, low_memory=False)
        else:
            profile["warnings"].append(f"Unsupported table extension: {suffix}")
            return profile
    except Exception as exc:
        profile["warnings"].append(f"Failed to read table: {exc}")
        return profile

    profile["readable"] = True
    profile["row_count"] = int(frame.shape[0])
    profile["column_count"] = int(frame.shape[1])
    profile["columns"] = [str(col) for col in frame.columns]

    semantic: Dict[str, str] = {}
    for col in profile["columns"]:
        canonical = canonicalColumnName(col)
        if canonical and canonical not in semantic:
            semantic[canonical] = col
    profile["semantic_columns"] = semantic

    for col in frame.columns:
        colName = str(col)
        series = frame[col]
        missing = int(series.isna().sum() + (series.astype(str).str.strip() == "").sum())
        profile["missing_values"][colName] = missing
        if canonicalColumnName(colName) in {"log2fc", "significance", "pvalue"}:
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                profile["value_ranges"][colName] = {
                    "min": float(numeric.min()),
                    "max": float(numeric.max()),
                }

    previewFrame = frame.head(previewRows).copy()
    for col in previewFrame.columns:
        if canonicalColumnName(str(col)) == "chromosome":
            previewFrame[col] = previewFrame[col].astype(str)
    profile["preview"]["rows"] = previewFrame.fillna("").astype(str).to_dict(orient="records")

    if profile["row_count"] >= maxRows:
        profile["warnings"].append(
            f"Table exceeds profiling row cap ({maxRows}); counts and preview are partial."
        )
        profile["preview"]["selection"] = f"first {previewRows} rows from sampled {maxRows} rows"

    return profile


def provenanceMetric(
    value: Any,
    description: str,
    sourceArtifact: str,
    calculation: str,
    columns: Sequence[str],
) -> Dict[str, Any]:
    """Build a provenance-backed metric dictionary.

    Args:
        value (Any): Metric value.
        description (str): Human-readable metric description.
        sourceArtifact (str): Source artifact path.
        calculation (str): Deterministic calculation description.
        columns (Sequence[str]): Column names involved.

    Returns:
        dict[str, Any]: Provenance metric record.
    """
    return {
        "value": value,
        "description": description,
        "source_artifact": sourceArtifact,
        "calculation": calculation,
        "columns": list(columns),
    }


def countSignificantFeatures(
    path: Path,
    profile: Mapping[str, Any],
    parameters: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    """Count significant up/down features when threshold columns are available.

    Args:
        path (Path): Source table path.
        profile (Mapping[str, Any]): Table profile with semantic columns.
        parameters (Mapping[str, Any]): Analysis parameters including thresholds.

    Returns:
        Optional[dict[str, Any]]: Significance summary with provenance or None.
    """
    semantic = profile.get("semantic_columns") or {}
    sigCol = semantic.get("significance")
    fcCol = semantic.get("log2fc")
    if not sigCol:
        return None

    fdrThreshold = parameters.get("fdr_threshold", parameters.get("padj_threshold"))
    fcThreshold = parameters.get("absolute_log2_fold_change_threshold", parameters.get("fc_threshold"))

    try:
        suffix = path.suffix.lower()
        if suffix == ".xlsx":
            frame = pd.read_excel(path)
        elif suffix in {".tsv", ".txt", ".bed", ".narrowpeak", ".broadpeak"}:
            frame = pd.read_csv(path, sep="\t", low_memory=False)
        else:
            frame = pd.read_csv(path, low_memory=False)
    except Exception:
        return None

    sigSeries = pd.to_numeric(frame[sigCol], errors="coerce")
    tested = int(sigSeries.notna().sum())
    significantMask = pd.Series(True, index=frame.index)
    calcParts = []
    columns = [sigCol]

    if fdrThreshold is not None:
        significantMask &= sigSeries < float(fdrThreshold)
        calcParts.append(f"{sigCol} < {fdrThreshold}")
    if fcCol and fcThreshold is not None:
        fcSeries = pd.to_numeric(frame[fcCol], errors="coerce")
        significantMask &= fcSeries.abs() >= float(fcThreshold)
        calcParts.append(f"abs({fcCol}) >= {fcThreshold}")
        columns.append(fcCol)

    significant = int(significantMask.sum())
    up = down = 0
    if fcCol:
        fcSeries = pd.to_numeric(frame[fcCol], errors="coerce")
        up = int((significantMask & (fcSeries > 0)).sum())
        down = int((significantMask & (fcSeries < 0)).sum())

    return {
        "tested_features": provenanceMetric(
            tested,
            "Number of features with a testable significance value",
            path.name,
            f"non-null {sigCol}",
            [sigCol],
        ),
        "significant_features": provenanceMetric(
            significant,
            "Number of features passing supplied thresholds",
            path.name,
            " and ".join(calcParts) if calcParts else f"non-null {sigCol}",
            columns,
        ),
        "upregulated_features": provenanceMetric(up, "Upregulated significant features", path.name, f"{fcCol} > 0 with thresholds", columns) if fcCol else None,
        "downregulated_features": provenanceMetric(down, "Downregulated significant features", path.name, f"{fcCol} < 0 with thresholds", columns) if fcCol else None,
    }


def mergeReportConfig(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    """Merge manifest report config with defaults.

    Args:
        manifest (Mapping[str, Any]): Study manifest.

    Returns:
        dict[str, Any]: Resolved report configuration.
    """
    config = dict(DEFAULT_REPORT_CONFIG)
    userConfig = manifest.get("report") or {}
    config.update({key: userConfig.get(key, value) for key, value in config.items()})
    study = manifest.get("study") or {}
    if not config.get("title") and study.get("title"):
        config["title"] = study.get("title")
    logo = config.get("logo")
    if logo and "${skillLoc}" in str(logo):
        config["logo"] = str(logo).replace("${skillLoc}", skillRoot().as_posix())
    elif not logo:
        config["logo"] = (skillRoot() / "assets" / "CAB-aiSkills_bioinformatics-reporting.white.svg").as_posix()
    return config


FIGURE_ROLES = {
    "volcano_plot",
    "ma_plot",
    "pca_plot",
    "heatmap",
    "coverage_plot",
    "enrichment_plot",
    "upset_plot",
    "venn_plot",
    "supplementary_figure",
}

TABLE_ROLES = {
    "primary_results",
    "differential_expression",
    "differential_accessibility",
    "differential_binding",
    "differential_methylation",
    "pathway_enrichment",
    "gsea_results",
    "motif_enrichment",
    "overlap_results",
    "supplementary_table",
}

# Tables summarized visually by a companion figure are linked in-line instead of duplicated.
FIGURE_LINKED_TABLE_ROLES: Dict[str, Tuple[str, ...]] = {
    "venn_plot": ("overlap_results",),
    "upset_plot": ("overlap_results",),
    "enrichment_plot": ("pathway_enrichment", "gsea_results"),
}


def linkRedundantArtifacts(
    figures: List[Dict[str, Any]],
    tables: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Attach companion tables to figures and omit redundant standalone table blocks."""
    figures_out = [dict(item) for item in figures]
    tables_out = [dict(item) for item in tables]
    omitted: List[Dict[str, Any]] = []
    drop_paths: set[str] = set()

    for figure in figures_out:
        linked_roles = FIGURE_LINKED_TABLE_ROLES.get(str(figure.get("role") or ""))
        if not linked_roles:
            continue
        analysis_id = figure.get("analysis_id")
        for table in tables_out:
            if table.get("path") in drop_paths:
                continue
            if table.get("analysis_id") != analysis_id:
                continue
            if table.get("role") not in linked_roles:
                continue
            figure["linked_table"] = table
            drop_paths.add(str(table.get("path")))
            omitted.append(
                {
                    "path": table.get("path"),
                    "role": table.get("role"),
                    "reason": f"Linked next to {figure.get('role')} figure instead of a separate section",
                    "linked_figure_role": figure.get("role"),
                }
            )

    tables_filtered = [table for table in tables_out if table.get("path") not in drop_paths]
    return figures_out, tables_filtered, omitted


def convertPdfFigureToPng(source: Path, dest_png: Path) -> bool:
    """Convert the first page of a PDF figure to PNG for Sphinx/LaTeX embedding."""
    dest_png.parent.mkdir(parents=True, exist_ok=True)
    stem = dest_png.with_suffix("")
    if shutil.which("pdftoppm"):
        completed = subprocess.run(
            ["pdftoppm", "-png", "-singlefile", "-f", "1", "-l", "1", str(source), str(stem)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and dest_png.is_file():
            return True
    if shutil.which("convert"):
        completed = subprocess.run(
            ["convert", "-density", "150", f"{source}[0]", str(dest_png)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and dest_png.is_file():
            return True
    try:
        from PIL import Image

        with Image.open(source) as image:
            image.save(dest_png, format="PNG")
        return dest_png.is_file()
    except Exception:
        return False


def prepareEmbeddableFigure(source: Path, dest_dir: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """Stage a figure for HTML/PDF embedding, converting PDF inputs to PNG when needed."""
    if not source.is_file():
        return None, None, "Source figure not found"
    suffix = source.suffix.lower()
    if suffix == ".pdf":
        embed_name = source.with_suffix(".png").name
        dest_png = dest_dir / embed_name
        if convertPdfFigureToPng(source, dest_png):
            return dest_png, embed_name, "converted_from_pdf"
        return None, None, "PDF figure could not be converted to PNG"
    embed_name = source.name
    dest = dest_dir / embed_name
    if not dest.exists():
        shutil.copy2(source, dest)
    return dest, embed_name, None


def collectVersionRecords(baseDir: Path, model: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Collect software versions from the manifest, upstream runs, and JSON manifests under baseDir."""
    from upstream_skills import findRunMetadataFiles

    records: List[Dict[str, str]] = []
    seen: set[Tuple[str, str, str]] = set()

    def add(name: Any, version: Any, source: str) -> None:
        if name is None or version is None:
            return
        name_text = str(name).strip()
        version_text = str(version).strip()
        source_text = str(source).strip()
        if not name_text or not version_text:
            return
        key = (name_text.lower(), version_text, source_text)
        if key in seen:
            return
        seen.add(key)
        records.append({"name": name_text, "version": version_text, "source": source_text})

    for item in model.get("software") or []:
        add(item.get("name"), item.get("version"), "report manifest")

    provenance = model.get("provenance") or {}
    pipeline_name = provenance.get("pipeline")
    pipeline_version = provenance.get("pipeline_version")
    if pipeline_name and pipeline_version:
        add(pipeline_name, pipeline_version, "report manifest")
    for item in provenance.get("software") or []:
        add(item.get("name"), item.get("version"), "report manifest")

    for skill in (model.get("upstream_skills") or {}).get("detected_skills") or []:
        skill_name = skill.get("skill") or "upstream"
        for name, version in (skill.get("tool_versions") or {}).items():
            rel = skill.get("run_metadata_path") or f"{skill_name}/run_metadata.json"
            add(name, version, rel)

    for meta_path in findRunMetadataFiles(baseDir):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        try:
            rel = meta_path.resolve().relative_to(baseDir.resolve()).as_posix()
        except ValueError:
            rel = meta_path.name
        skill = meta.get("skill") or "unknown"
        for name, version in (meta.get("tool_versions") or {}).items():
            add(name, version, rel)
        for item in (meta.get("software") or []) if isinstance(meta.get("software"), list) else []:
            if isinstance(item, dict):
                add(item.get("name"), item.get("version"), rel)

    skip_names = {"report-model.json", "verification-summary.json", "run_metadata.json"}
    for json_path in sorted(baseDir.rglob("*.json")):
        if json_path.name in skip_names:
            continue
        if "report-model" in json_path.name or "verification-summary" in json_path.name:
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        try:
            rel = json_path.resolve().relative_to(baseDir.resolve()).as_posix()
        except ValueError:
            rel = json_path.name
        tool_versions = data.get("tool_versions")
        if isinstance(tool_versions, dict):
            for name, version in tool_versions.items():
                add(name, version, rel)
        software = data.get("software")
        if isinstance(software, list):
            for item in software:
                if isinstance(item, dict):
                    add(item.get("name"), item.get("version"), rel)

    records.sort(key=lambda item: (item["name"].lower(), item["source"].lower()))
    return records


def buildReportModel(
    manifest: Mapping[str, Any],
    baseDir: Path,
    profiles: Mapping[str, Mapping[str, Any]],
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build the normalized report model consumed by rendering.

    Args:
        manifest (Mapping[str, Any]): Validated manifest content.
        baseDir (Path): Base directory for artifact paths.
        profiles (Mapping[str, Mapping[str, Any]]): Table profiles keyed by artifact path.
        validation (Mapping[str, Any]): Validation report.

    Returns:
        dict[str, Any]: Normalized report model JSON.
    """
    reportConfig = mergeReportConfig(manifest)
    study = dict(manifest.get("study") or {})
    warnings = list(validation.get("warnings") or [])
    warnings.extend(manifest.get("warnings") or [])
    normalized = (validation.get("normalized_manifest") or {})
    upstream = normalized.get("upstream_skills") or discoverUpstreamSkills(baseDir, manifest, skillRoot())
    studyDisplay = normalized.get("study_display") or {}
    if not studyDisplay:
        registry = loadUpstreamRegistry(skillRoot())
        genomeLabel, genomeStatus, genomeWarnings = evaluateGenomeBuildDisplay(manifest, upstream, registry)
        studyDisplay = {"genome_build": genomeLabel, "genome_build_status": genomeStatus}
        for warning in genomeWarnings:
            if warning not in warnings:
                warnings.append(warning)
    analysesOut: List[Dict[str, Any]] = []
    figures: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    metrics: List[Dict[str, Any]] = []

    for analysis in manifest.get("analyses") or []:
        analysisEntry: Dict[str, Any] = {
            "id": analysis.get("id"),
            "type": analysis.get("type"),
            "title": analysis.get("title") or analysis.get("id"),
            "comparison": analysis.get("comparison") or {},
            "parameters": analysis.get("parameters") or {},
            "warnings": analysis.get("warnings") or [],
            "artifacts": [],
            "summaries": {},
        }
        for artifact in analysis.get("artifacts") or []:
            rel = artifact.get("path")
            if not rel:
                continue
            role = artifact.get("role", "unknown")
            resolved = (baseDir / rel).resolve()
            entry = {
                "path": rel,
                "resolved_path": resolved.as_posix(),
                "role": role,
                "format": artifact.get("format") or detectFormat(resolved),
                "description": artifact.get("description"),
                "confidence": artifact.get("confidence", CONFIDENCE_EXPLICIT),
                "exists": resolved.is_file(),
            }
            analysisEntry["artifacts"].append(entry)

            if role in FIGURE_ROLES and resolved.is_file():
                figures.append(
                    {
                        "analysis_id": analysis.get("id"),
                        "role": role,
                        "path": rel,
                        "caption": artifact.get("description") or f"{role.replace('_', ' ')} from {rel}",
                        "source_artifact": rel,
                    }
                )
            elif role in TABLE_ROLES and resolved.is_file():
                profile = profiles.get(rel, {})
                tables.append(
                    {
                        "analysis_id": analysis.get("id"),
                        "role": role,
                        "path": rel,
                        "description": artifact.get("description") or role.replace("_", " "),
                        "profile": profile,
                        "download_path": rel,
                    }
                )
                summary = countSignificantFeatures(resolved, profile, analysis.get("parameters") or {})
                if summary:
                    analysisEntry["summaries"]["significance"] = summary
                    for key, metric in summary.items():
                        if metric:
                            metrics.append(metric)

        analysesOut.append(analysisEntry)

    figures, tables, omitted = linkRedundantArtifacts(figures, tables)
    model_without_versions = {
        "software": (manifest.get("provenance") or {}).get("software") or [],
        "provenance": manifest.get("provenance") or {},
        "upstream_skills": upstream,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "study": study,
        "study_display": studyDisplay,
        "samples": manifest.get("samples") or {},
        "report_config": reportConfig,
        "upstream_skills": upstream,
        "analyses": analysesOut,
        "figures": figures,
        "tables": tables,
        "metrics": metrics,
        "methods": mergeUpstreamMethodsIntoModel(manifest, upstream),
        "parameters": {
            analysis.get("id"): analysis.get("parameters") or {}
            for analysis in manifest.get("analyses") or []
            if analysis.get("id")
        },
        "warnings": warnings,
        "limitations": manifest.get("limitations") or [],
        "provenance": manifest.get("provenance") or {},
        "software": (manifest.get("provenance") or {}).get("software") or [],
        "versions": collectVersionRecords(baseDir, model_without_versions),
        "validation": {
            "valid": validation.get("valid"),
            "errors": validation.get("errors") or [],
            "warnings": validation.get("warnings") or [],
        },
        "omitted_artifacts": omitted,
    }


def collectToolVersions() -> Dict[str, str]:
    """Collect resolved Python dependency versions for run metadata.

    Returns:
        dict[str, str]: Tool and library versions.
    """
    versions = {
        "python": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "pandas": pd.__version__,
        "pyyaml": yaml.__version__ if hasattr(yaml, "__version__") else "unknown",
        "script_dir": skillRoot().as_posix(),
    }
    quarto = shutil.which("quarto")
    versions["quarto"] = (
        subprocess.check_output(["quarto", "--version"], text=True).strip() if quarto else "not installed"
    )
    pdf_engine = detectPdfEngine()
    versions["pdf_engine"] = pdf_engine or "not installed"
    return versions


def detectPdfEngine() -> Optional[str]:
    """Detect an available PDF rendering engine on the host.

    Returns:
        Optional[str]: Engine label when found.
    """
    if shutil.which("pdflatex"):
        return "pdflatex"
    if shutil.which("xelatex"):
        return "xelatex"
    if shutil.which("typst"):
        return "typst"
    return None


def encodeFigureDataUri(path: Path) -> Optional[str]:
    """Return a base64 data URI for raster figures when self-contained HTML is requested.

    Args:
        path (Path): Figure path.

    Returns:
        Optional[str]: Data URI or None when unsupported.
    """
    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return None
    mime = mimetypes.types_map.get(suffix, "application/octet-stream")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def looksLikeIdentifier(value: str) -> bool:
    """Heuristically detect sample identifiers that may contain personal data.

    Args:
        value (str): Sample identifier candidate.

    Returns:
        bool: True when the value looks sensitive.
    """
    lowered = value.lower()
    patterns = ("patient", "subject", "mrn", "dob", "ssn", "name")
    return any(token in lowered for token in patterns)


def redactSampleIds(sampleIds: Iterable[str]) -> Tuple[List[str], Optional[str]]:
    """Redact sample IDs that appear to contain personal identifiers.

    Args:
        sampleIds (Iterable[str]): Sample identifiers.

    Returns:
        tuple[list[str], Optional[str]]: Redacted IDs and optional warning message.
    """
    ids = list(sampleIds)
    if not ids:
        return ids, None
    if any(looksLikeIdentifier(item) for item in ids):
        redacted = [f"sample_{index + 1}" for index in range(len(ids))]
        return redacted, "Sample identifiers were redacted because they may contain personal data."
    return ids, None
