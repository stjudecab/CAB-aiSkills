#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `genomic-set-analysis` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Shared reproducibility logging helpers for genomic-set-analysis scripts."""

from __future__ import annotations

import argparse
import logging
import os
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def runIdUtc() -> str:
    """Return a UTC run ID in ``YYYYMMDDTHHMMSSZ`` format.

    Returns:
        str: Timestamp-based run ID suitable for run-scoped metadata.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def commandLineString() -> str:
    """Return the current process command line with shell-safe quoting.

    Returns:
        str: Reconstructed ``python …`` invocation string.
    """
    return "python " + " ".join(shlex.quote(str(part)) for part in sys.argv)


def configureLogging(logFile: Optional[Path] = None) -> None:
    """Configure root logging to stderr and, optionally, a plain-text log file.

    Args:
        logFile (Optional[Path]): File path for a persistent log under ``logs/``. When
            ``None`` only a stream handler is attached.

    Returns:
        None.
    """
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if logFile is not None:
        logFile.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logFile))
    formatter = logging.Formatter(
        "###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def appendCommandLog(commandsLog: Path, runId: str, command: str) -> None:
    """Append one executed command block to ``commands.log``.

    Args:
        commandsLog (Path): Append-only command audit log path.
        runId (str): UTC run ID for this execution.
        command (str): Full command string to record.

    Returns:
        None.
    """
    commandsLog.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(commandsLog, "a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] run_id={runId}\n{command}\n\n")


def readOptionalText(
    inlineText: Optional[str],
    filePath: Optional[str],
    envVar: Optional[str] = None,
) -> Optional[str]:
    """Return trimmed text from an inline string, file, or environment variable.

    Args:
        inlineText (Optional[str]): Inline request or workflow text.
        filePath (Optional[str]): Path to a text file to read.
        envVar (Optional[str]): Environment variable name fallback.

    Returns:
        Optional[str]: Trimmed text when present, else ``None``.
    """
    if inlineText:
        return inlineText.strip()
    if filePath:
        return Path(filePath).expanduser().read_text(encoding="utf-8").strip()
    if envVar and os.environ.get(envVar):
        return os.environ[envVar].strip()
    return None


def writeOptionalText(outputDir: Path, filename: str, content: Optional[str]) -> Optional[Path]:
    """Write *content* to *outputDir/filename* when present.

    Args:
        outputDir (Path): Destination directory for the audit artifact.
        filename (str): Output filename (e.g. ``agent_request.txt``).
        content (Optional[str]): Text to write.

    Returns:
        Optional[Path]: Written path when *content* was provided, else ``None``.
    """
    if not content:
        return None
    outPath = outputDir / filename
    outPath.write_text(content.rstrip() + "\n", encoding="utf-8")
    return outPath


def copyOptionalTextFile(source: Optional[str], outputDir: Path, destName: str) -> Optional[Path]:
    """Copy a text file into the output directory when it exists.

    Args:
        source (Optional[str]): Source file path.
        outputDir (Path): Destination directory.
        destName (str): Destination filename inside *outputDir*.

    Returns:
        Optional[Path]: Copied path when the source exists, else ``None``.
    """
    if not source:
        return None
    src = Path(source).expanduser()
    if not src.is_file():
        return None
    dest = outputDir / destName
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def addReproducibilityArguments(parser: argparse.ArgumentParser) -> None:
    """Add standard reproducibility flags to an ``argparse`` parser.

    Args:
        parser (argparse.ArgumentParser): Parser receiving the reproducibility group.

    Returns:
        None.
    """
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


def writeAgentArtifacts(
    outputDir: Path,
    args: argparse.Namespace,
    *,
    requestEnvVar: str = "GENOMIC_SET_ANALYSIS_AGENT_REQUEST",
    workflowEnvVar: str = "GENOMIC_SET_ANALYSIS_AGENT_WORKFLOW",
) -> tuple[Optional[Path], Optional[Path]]:
    """Write ``agent_request.txt`` and ``agent_workflow.md`` from CLI flags.

    Args:
        outputDir (Path): Run output directory receiving audit artifacts.
        args (argparse.Namespace): Parsed arguments with reproducibility fields.
        requestEnvVar (str): Environment variable fallback for the user request.
        workflowEnvVar (str): Environment variable fallback for workflow notes.

    Returns:
        tuple[Optional[Path], Optional[Path]]: Paths to ``agent_request.txt`` and
        ``agent_workflow.md`` when written.
    """
    outputDir.mkdir(parents=True, exist_ok=True)
    agentRequest = readOptionalText(
        args.agentRequest or None,
        args.agentRequestFile or None,
        requestEnvVar,
    )
    agentRequestPath = writeOptionalText(outputDir, "agent_request.txt", agentRequest)
    agentWorkflowPath = copyOptionalTextFile(
        args.agentWorkflowFile or None,
        outputDir,
        "agent_workflow.md",
    )
    if agentWorkflowPath is None:
        agentWorkflow = readOptionalText(
            args.agentWorkflow or None,
            None,
            workflowEnvVar,
        )
        agentWorkflowPath = writeOptionalText(outputDir, "agent_workflow.md", agentWorkflow)
    return agentRequestPath, agentWorkflowPath
