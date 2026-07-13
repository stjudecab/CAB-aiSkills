"""Shared reproducibility helpers for genomic-regions-annotation skill scripts."""

from __future__ import annotations

import json
import logging
import os
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def runIdUtc() -> str:
    """Return a UTC run ID in YYYYMMDDTHHMMSSZ format.

    Returns:
        str: Timestamp-based run identifier.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def timestampIsoUtc() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        str: ISO-8601 UTC timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def configureRunLogging(
    outputDir: Path,
    scriptName: str,
    logLevel: str = "INFO",
) -> Path:
    """Configure console + file logging under ``<outputDir>/logs/<scriptName>.log``.

    Args:
        outputDir (Path): Run directory that will contain ``logs/``.
        scriptName (str): Basename used for the log file (no extension).
        logLevel (str): Logging level name.

    Returns:
        Path: Absolute path to the script log file.
    """
    logsDir = outputDir / "logs"
    logsDir.mkdir(parents=True, exist_ok=True)
    logPath = logsDir / f"{scriptName}.log"

    root = logging.getLogger()
    root.handlers.clear()
    level = getattr(logging, str(logLevel).upper(), logging.INFO)
    root.setLevel(level)

    formatter = logging.Formatter(
        "###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    streamHandler = logging.StreamHandler(sys.stderr)
    streamHandler.setFormatter(formatter)
    streamHandler.setLevel(level)
    fileHandler = logging.FileHandler(logPath, encoding="utf-8")
    fileHandler.setFormatter(formatter)
    fileHandler.setLevel(level)
    root.addHandler(streamHandler)
    root.addHandler(fileHandler)
    return logPath.resolve()


def appendCommandLog(outputDir: Path, runId: str, argv: list[str] | None = None) -> Path:
    """Append the exact CLI invocation to ``logs/commands.log``.

    Args:
        outputDir (Path): Run directory.
        runId (str): Run identifier.
        argv (list[str] | None): Argument vector; defaults to ``sys.argv``.

    Returns:
        Path: Absolute path to ``commands.log``.
    """
    logsDir = outputDir / "logs"
    logsDir.mkdir(parents=True, exist_ok=True)
    commandsPath = logsDir / "commands.log"
    cmd = " ".join(shlex.quote(a) for a in (argv if argv is not None else sys.argv))
    block = f"[{timestampIsoUtc()}] run_id={runId}\n{cmd}\n\n"
    with commandsPath.open("a", encoding="utf-8") as handle:
        handle.write(block)
    return commandsPath.resolve()


def writeAgentArtifacts(
    outputDir: Path,
    *,
    agentRequest: str | None = None,
    agentRequestFile: Path | None = None,
    agentWorkflow: str | None = None,
    agentWorkflowFile: Path | None = None,
) -> tuple[Path | None, Path | None]:
    """Write or copy agent request and workflow files into the run directory.

    Args:
        outputDir (Path): Run directory.
        agentRequest (str | None): Inline verbatim user request.
        agentRequestFile (Path | None): Path to a request text file.
        agentWorkflow (str | None): Inline workflow markdown.
        agentWorkflowFile (Path | None): Path to a workflow markdown file.

    Returns:
        tuple[Path | None, Path | None]: Paths to ``agent_request.txt`` and
        ``agent_workflow.md`` when written.
    """
    requestOut: Path | None = None
    workflowOut: Path | None = None
    outputDir.mkdir(parents=True, exist_ok=True)

    if agentRequestFile is not None:
        src = Path(agentRequestFile)
        if not src.is_file():
            raise FileNotFoundError(
                f"Expected --agentRequestFile at {src}, but the file was not found."
            )
        requestOut = outputDir / "agent_request.txt"
        requestOut.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    elif agentRequest:
        requestOut = outputDir / "agent_request.txt"
        requestOut.write_text(agentRequest, encoding="utf-8")

    if agentWorkflowFile is not None:
        src = Path(agentWorkflowFile)
        if not src.is_file():
            raise FileNotFoundError(
                f"Expected --agentWorkflowFile at {src}, but the file was not found."
            )
        workflowOut = outputDir / "agent_workflow.md"
        workflowOut.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    elif agentWorkflow:
        workflowOut = outputDir / "agent_workflow.md"
        workflowOut.write_text(agentWorkflow, encoding="utf-8")

    return (
        requestOut.resolve() if requestOut is not None else None,
        workflowOut.resolve() if workflowOut is not None else None,
    )


def writeRunMetadata(path: Path, payload: dict[str, Any]) -> None:
    """Write ``run_metadata.json`` with UTF-8 encoding.

    Args:
        path (Path): Destination JSON path.
        payload (dict[str, Any]): Metadata fields.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def collectBaseToolVersions(scriptPath: Path) -> dict[str, str]:
    """Collect base Python and script path versions for run metadata.

    Args:
        scriptPath (Path): Path to the invoking script.

    Returns:
        dict[str, str]: Tool version map.
    """
    versions = {
        "python": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "script": scriptPath.resolve().as_posix(),
    }
    for packageName in ("pandas", "numpy", "matplotlib", "seaborn", "plotly", "pybedtools"):
        try:
            mod = __import__(packageName)
            versions[packageName] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[packageName] = "not_imported"
    return versions


def addReproducibilityArgs(parser: Any) -> None:
    """Attach the standard reproducibility argparse group.

    Args:
        parser (Any): ``argparse.ArgumentParser`` instance.

    Returns:
        None.
    """
    group = parser.add_argument_group("reproducibility")
    group.add_argument(
        "--outputDir",
        default=None,
        help="Run directory for run_metadata.json, agent artifacts, and logs/.",
    )
    group.add_argument(
        "--runId",
        default=None,
        help="UTC run ID (YYYYMMDDTHHMMSSZ). Default: generate at execution.",
    )
    group.add_argument("--agentRequest", default=None, help="Inline verbatim user request.")
    group.add_argument(
        "--agentRequestFile",
        default=None,
        help="Path to a file containing the verbatim user request.",
    )
    group.add_argument("--agentWorkflow", default=None, help="Inline agent workflow markdown.")
    group.add_argument(
        "--agentWorkflowFile",
        default=None,
        help="Path to agent workflow markdown notes.",
    )


def skillRootFromScript(scriptFile: Path) -> Path:
    """Resolve the skill package root from a script under ``scripts/``.

    Args:
        scriptFile (Path): Absolute or relative path to a script.

    Returns:
        Path: Skill root directory.
    """
    return Path(scriptFile).resolve().parent.parent


def envSkipBootstrap() -> bool:
    """Return True when environment bootstrap should be skipped.

    Returns:
        bool: Whether ``GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP`` is set.
    """
    return os.environ.get("GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP", "") == "1"
