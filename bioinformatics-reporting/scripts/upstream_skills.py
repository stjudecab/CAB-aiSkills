#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
"""Discover upstream CAB-aiSkills runs and pull methods plus critical-input context."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml

logger = logging.getLogger(__name__)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKDOWN_HEADING_RE = re.compile(r"^#+\s*")


def loadUpstreamRegistry(skillRoot: Path) -> Dict[str, Any]:
    registryPath = skillRoot / "references" / "upstream-skills-registry.yaml"
    if not registryPath.is_file():
        return {"skills": {}, "region_interpretation_roles": []}
    return yaml.safe_load(registryPath.read_text(encoding="utf-8")) or {}


def skillSearchPaths(baseDir: Path, skillRoot: Path) -> List[Path]:
    candidates: List[Path] = []
    envPaths = os.environ.get("BIOINFORMATICS_REPORTING_SKILL_PATHS", "")
    for item in envPaths.split(os.pathsep):
        if item.strip():
            candidates.append(Path(item.strip()).expanduser())
    candidates.append(skillRoot.parent)
    for parent in [baseDir, *list(baseDir.parents)[:8]]:
        cursorSkills = parent / ".cursor" / "skills"
        if cursorSkills.is_dir():
            candidates.append(cursorSkills)
    seen: set[str] = set()
    unique: List[Path] = []
    for path in candidates:
        resolved = path.resolve().as_posix()
        if resolved not in seen and path.is_dir():
            seen.add(resolved)
            unique.append(path)
    return unique


def resolveSkillPackage(skillName: str, searchPaths: Sequence[Path]) -> Optional[Path]:
    for root in searchPaths:
        candidate = root / skillName
        if (candidate / "SKILL.md").is_file():
            return candidate.resolve()
    return None


def findRunMetadataFiles(baseDir: Path, *, maxFiles: int = 25) -> List[Path]:
    """Find run_metadata.json files under the report target directory only."""
    found: List[Path] = []
    seen: set[str] = set()
    baseResolved = baseDir.resolve()

    def isUnderBase(path: Path) -> bool:
        try:
            path.resolve().relative_to(baseResolved)
            return True
        except ValueError:
            return path.resolve() == baseResolved

    def add(path: Path) -> None:
        resolved = path.resolve()
        if not isUnderBase(resolved):
            return
        key = resolved.as_posix()
        if key in seen or not resolved.is_file():
            return
        seen.add(key)
        found.append(resolved)

    add(baseDir / "run_metadata.json")
    for meta in sorted(baseDir.rglob("run_metadata.json")):
        add(meta)
        if len(found) >= maxFiles:
            return found
    return found[:maxFiles]


def markdownToManuscriptMethods(text: str, *, maxChars: int = 2500) -> str:
    """Convert markdown methods text into manuscript-ready prose with paragraph breaks."""
    paragraphs: List[str] = []
    current: List[str] = []
    for rawLine in text.splitlines():
        line = rawLine.strip()
        if not line or line.startswith("```"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.startswith("|") or line.startswith("- ---"):
            continue
        if line.lower().startswith("## contents"):
            continue
        if MARKDOWN_HEADING_RE.match(line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            line = MARKDOWN_HEADING_RE.sub("", line).strip()
        line = MARKDOWN_LINK_RE.sub(r"\1", line)
        line = line.strip("*`_ ")
        if line:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    summary = "\n\n".join(paragraph for paragraph in paragraphs if paragraph).strip()
    if len(summary) > maxChars:
        summary = summary[: maxChars - 3].rstrip() + "..."
    return summary


def markdownToPlainSummary(text: str, *, maxChars: int = 1200) -> str:
    lines: List[str] = []
    for rawLine in text.splitlines():
        line = rawLine.strip()
        if not line or line.startswith("```"):
            continue
        if line.startswith("|") or line.startswith("- ---"):
            continue
        if line.lower().startswith("## contents"):
            continue
        if MARKDOWN_HEADING_RE.match(line):
            if lines:
                lines.append("")
            line = MARKDOWN_HEADING_RE.sub("", line).strip()
        line = MARKDOWN_LINK_RE.sub(r"\1", line)
        line = line.strip("*`_ ")
        if line:
            lines.append(line)
    summary = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if len(summary) > maxChars:
        summary = summary[: maxChars - 3].rstrip() + "..."
    return summary


def extractSkillPurpose(skillPackage: Path) -> str:
    skillMd = skillPackage / "SKILL.md"
    if not skillMd.is_file():
        return ""
    text = skillMd.read_text(encoding="utf-8")
    match = re.search(r"## Purpose\s*\n(.*?)(?:\n## |\Z)", text, re.S)
    if match:
        return markdownToPlainSummary(match.group(1), maxChars=800)
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    return markdownToPlainSummary(body, maxChars=500)


def extractReadmeIntroParagraph(text: str) -> str:
    """Return the first human-readable intro paragraph from a skill README."""
    paragraph_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if paragraph_lines:
                break
            continue
        if stripped.startswith(("<", "![", "#", "|", "- ", "```")):
            if paragraph_lines:
                break
            continue
        paragraph_lines.append(stripped)
    if not paragraph_lines:
        return ""
    paragraph = " ".join(paragraph_lines)
    paragraph = MARKDOWN_LINK_RE.sub(r"\1", paragraph)
    return paragraph.strip()


def extractReadmeMethodsSentence(text: str) -> str:
    """Extract the manuscript-style methods sentence from README when present."""
    patterns = [
        r"(?:\*\*Methods \(one sentence\):\*\*|Methods \(one sentence\):)\s*\n+\s*>\s*(.+?)(?:\n\n|\n## |\Z)",
        r"(?:\*\*Methods \(one sentence\):\*\*|Methods \(one sentence\):)\s*\n+\s*(.+?)(?:\n\n|\n## |\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.S | re.I)
        if not match:
            continue
        sentence = match.group(1).strip()
        sentence = re.sub(r"^>\s*", "", sentence, flags=re.M)
        sentence = re.sub(r"\s+", " ", sentence).strip()
        if sentence:
            return sentence
    return ""


def extractReadmeMethodsOverview(skillPackage: Path) -> str:
    """Prefer README intro + methods sentence for manuscript-ready methods text."""
    readme = skillPackage / "README.md"
    if not readme.is_file():
        return ""
    text = readme.read_text(encoding="utf-8")
    chunks: List[str] = []
    intro = extractReadmeIntroParagraph(text)
    methods = extractReadmeMethodsSentence(text)
    if intro:
        chunks.append(intro)
    if methods:
        chunks.append(methods)
    return "\n\n".join(chunks).strip()


def extractSkillMdMethodsSection(skillPackage: Path) -> str:
    """Extract an explicit Methods section from SKILL.md when present."""
    skillMd = skillPackage / "SKILL.md"
    if not skillMd.is_file():
        return ""
    text = skillMd.read_text(encoding="utf-8")
    match = re.search(r"## Methods\s*\n(.*?)(?:\n## |\Z)", text, re.S | re.I)
    if match:
        return markdownToManuscriptMethods(match.group(1), maxChars=2000)
    return ""


def extractManuscriptMethodsFromReference(text: str) -> str:
    """Extract methods prose from a reference doc, skipping TOC-only reference files."""
    match = re.search(r"## Methods\s*\n(.*?)(?:\n## |\Z)", text, re.S | re.I)
    if match:
        return markdownToManuscriptMethods(match.group(1), maxChars=1800)
    if re.search(r"^## Contents\s*$", text, re.M):
        return ""
    if re.search(r"\breference\s*$", text.splitlines()[0].lower() if text.splitlines() else "", re.I):
        return ""
    return ""


def markdownInlineToRst(text: str) -> str:
    """Convert common markdown inline markup to reStructuredText for methods rendering."""
    converted = text
    converted = re.sub(r"`([^`]+)`", r"``\1``", converted)
    converted = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", converted)
    converted = MARKDOWN_LINK_RE.sub(r"\1", converted)
    return converted


def loadMethodsOverview(skillPackage: Path, registryEntry: Mapping[str, Any]) -> str:
    """Load manuscript-ready methods text, preferring README over agent reference docs."""
    readme_methods = extractReadmeMethodsOverview(skillPackage)
    if readme_methods:
        return markdownInlineToRst(readme_methods)

    skill_methods = extractSkillMdMethodsSection(skillPackage)
    if skill_methods:
        return markdownInlineToRst(skill_methods)

    for relPath in registryEntry.get("methods_files") or []:
        refPath = skillPackage / str(relPath)
        if refPath.is_file():
            extracted = extractManuscriptMethodsFromReference(refPath.read_text(encoding="utf-8"))
            if extracted:
                return markdownInlineToRst(extracted)

    purpose = extractSkillPurpose(skillPackage)
    return markdownInlineToRst(purpose) if purpose else ""


def registryCriticalInputs(skillName: str, registry: Mapping[str, Any]) -> Dict[str, Any]:
    entry = (registry.get("skills") or {}).get(skillName) or {}
    return dict(entry.get("critical_inputs") or {})


def inferCriticalInputsFromSkillMd(skillPackage: Path) -> Dict[str, Any]:
    text = (skillPackage / "SKILL.md").read_text(encoding="utf-8").lower()
    if "genome build" not in text:
        return {"genome_build": {"requirement": "optional", "report_label": "Not recorded in report manifest", "note": "No explicit genome-build policy found in upstream SKILL.md."}}
    if "does not need a genome" in text:
        return {"genome_build": {"requirement": "not_applicable", "report_label": "Not required for core outputs of this upstream skill", "note": "Derived from upstream SKILL.md."}}
    if "mandatory" in text or "never assumed" in text:
        return {"genome_build": {"requirement": "required", "report_label": "Required by upstream skill (missing from manifest)", "note": "Derived from upstream SKILL.md."}}
    return {"genome_build": {"requirement": "conditional", "report_label": "Required only for some upstream substeps", "note": "Derived from upstream SKILL.md."}}


def manifestReferencesSkill(manifest: Mapping[str, Any], skillName: str) -> bool:
    provenance = manifest.get("provenance") or {}
    pipeline = str(provenance.get("pipeline") or "").lower()
    if skillName.replace("-", " ") in pipeline or skillName in pipeline:
        return True
    for analysis in manifest.get("analyses") or []:
        for artifact in analysis.get("artifacts") or []:
            if skillName in str(artifact.get("path") or ""):
                return True
    return False


def buildDetectedSkillRecord(skillName: str, runMetadata: Mapping[str, Any], runMetadataPath: Path, skillPackage: Optional[Path], registry: Mapping[str, Any]) -> Dict[str, Any]:
    registryEntry = (registry.get("skills") or {}).get(skillName) or {}
    methodsOverview = loadMethodsOverview(skillPackage, registryEntry) if skillPackage else ""
    if not methodsOverview:
        methodsOverview = str((runMetadata.get("attribution") or {}).get("method") or "").strip()
    criticalInputs = registryCriticalInputs(skillName, registry)
    if not criticalInputs and skillPackage is not None:
        criticalInputs = inferCriticalInputsFromSkillMd(skillPackage)
    return {
        "skill": skillName,
        "display_name": registryEntry.get("display_name") or skillName,
        "skill_package_found": skillPackage is not None,
        "skill_package_path": skillPackage.as_posix() if skillPackage else None,
        "run_metadata_path": runMetadataPath.as_posix(),
        "run_id": runMetadata.get("run_id"),
        "timestamp_utc": runMetadata.get("timestamp_utc"),
        "methods_overview": methodsOverview,
        "attribution": runMetadata.get("attribution") or {},
        "parameters": runMetadata.get("parameters") or {},
        "tool_versions": runMetadata.get("tool_versions") or {},
        "outputs": runMetadata.get("outputs") or [],
        "critical_inputs": criticalInputs,
    }


def discoverUpstreamSkills(baseDir: Path, manifest: Mapping[str, Any], skillRoot: Path) -> Dict[str, Any]:
    registry = loadUpstreamRegistry(skillRoot)
    searchPaths = skillSearchPaths(baseDir, skillRoot)
    detectedBySkill: Dict[str, Dict[str, Any]] = {}
    for metaPath in findRunMetadataFiles(baseDir):
        try:
            runMetadata = json.loads(metaPath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("Skipping invalid run metadata %s: %s", metaPath, exc)
            continue
        skillName = str(runMetadata.get("skill") or "").strip()
        if not skillName or skillName == "bioinformatics-reporting":
            continue
        package = resolveSkillPackage(skillName, searchPaths)
        if package is None and not manifestReferencesSkill(manifest, skillName):
            continue
        detectedBySkill[skillName] = buildDetectedSkillRecord(skillName, runMetadata, metaPath, package, registry)
    provenanceSkill = str((manifest.get("provenance") or {}).get("skill") or "").strip()
    if provenanceSkill and provenanceSkill not in detectedBySkill:
        package = resolveSkillPackage(provenanceSkill, searchPaths)
        if package is not None and manifestReferencesSkill(manifest, provenanceSkill):
            registryEntry = (registry.get("skills") or {}).get(provenanceSkill) or {}
            detectedBySkill[provenanceSkill] = {
                "skill": provenanceSkill,
                "display_name": registryEntry.get("display_name") or provenanceSkill,
                "skill_package_found": True,
                "skill_package_path": package.as_posix(),
                "run_metadata_path": None,
                "methods_overview": loadMethodsOverview(package, registryEntry),
                "critical_inputs": registryCriticalInputs(provenanceSkill, registry) or inferCriticalInputsFromSkillMd(package),
                "tool_versions": {},
                "parameters": {},
                "outputs": [],
                "attribution": {},
            }
    return {"search_paths": [path.as_posix() for path in searchPaths], "detected_skills": list(detectedBySkill.values())}


def reportUsesRegionInterpretation(manifest: Mapping[str, Any], registry: Mapping[str, Any]) -> bool:
    regionRoles = set(registry.get("region_interpretation_roles") or [])
    for analysis in manifest.get("analyses") or []:
        if str(analysis.get("type") or "") in regionRoles:
            return True
        for artifact in analysis.get("artifacts") or []:
            if str(artifact.get("role") or "") in regionRoles:
                return True
    return False


def evaluateGenomeBuildDisplay(manifest: Mapping[str, Any], upstream: Mapping[str, Any], registry: Mapping[str, Any]) -> Tuple[str, str, List[str]]:
    study = manifest.get("study") or {}
    genome = study.get("genome")
    if genome:
        return str(genome), "specified", []
    detected = upstream.get("detected_skills") or []
    regionScope = reportUsesRegionInterpretation(manifest, registry)
    requirements: List[str] = []
    labels: List[str] = []
    for item in detected:
        genomeMeta = (item.get("critical_inputs") or {}).get("genome_build") or {}
        requirements.append(str(genomeMeta.get("requirement") or "optional"))
        label = genomeMeta.get("report_label")
        if label:
            labels.append(str(label))
    if detected and not regionScope and all(req == "not_applicable" for req in requirements):
        return labels[0], "not_required", []
    if detected and not regionScope and all(req in {"not_applicable", "conditional", "optional"} for req in requirements):
        return labels[0] if labels else "Not required for the summarized upstream outputs", "not_required_for_report", []
    if any(req == "required" for req in requirements) or regionScope:
        return "Not specified", "missing_critical", ["Study genome build is not specified but is required for region-level results or an upstream skill that mandates an explicit build."]
    if not detected:
        return "Not specified", "unknown", ["Study genome build not specified."]
    return "Not specified", "unknown", []


def mergeUpstreamMethodsIntoModel(manifest: Mapping[str, Any], upstream: Mapping[str, Any]) -> List[Dict[str, Any]]:
    methods: List[Dict[str, Any]] = list(manifest.get("methods") or [])
    for item in upstream.get("detected_skills") or []:
        overview = item.get("methods_overview")
        if not overview:
            continue
        methods.append(
            {
                "source_skill": item.get("skill"),
                "title": item.get("display_name") or item.get("skill"),
                "overview": overview,
                "run_id": item.get("run_id"),
                "run_metadata_path": item.get("run_metadata_path"),
                "tool_versions": item.get("tool_versions") or {},
            }
        )
    return methods
