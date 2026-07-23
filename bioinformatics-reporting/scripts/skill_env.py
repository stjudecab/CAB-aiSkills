#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `bioinformatics-reporting` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Bootstrap the persistent skill venv before running CLI scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ENV_ACTIVE_VAR = "BIOINFORMATICS_REPORTING_ENV_ACTIVE"
SKIP_VAR = "BIOINFORMATICS_REPORTING_SKIP_ENV_BOOTSTRAP"


def ensureEnvScript() -> Path:
    """Return the path to ``ensure_env.sh``.

    Returns:
        Path: Absolute path to the shell helper.
    """
    return Path(__file__).resolve().parent / "ensure_env.sh"


def runEnsureEnv(*args: str) -> str:
    """Run ``ensure_env.sh`` and return trimmed stdout.

    Args:
        *args: Arguments forwarded to ``ensure_env.sh``.

    Returns:
        str: Trimmed stdout from the helper.

    Raises:
        RuntimeError: When the helper script is missing.
        subprocess.CalledProcessError: When the helper exits non-zero.
    """
    script = ensureEnvScript()
    if not script.is_file():
        raise RuntimeError(f"Missing environment helper: {script}")
    completed = subprocess.run(
        ["bash", str(script), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def prependEnvBinToPath(prefix: str) -> None:
    """Prepend ``<prefix>/bin`` to ``PATH`` when not already first.

    Args:
        prefix (str): Venv environment prefix.
    """
    binDir = str(Path(prefix) / "bin")
    path = os.environ.get("PATH", "")
    pathEntries = path.split(os.pathsep) if path else []
    if not pathEntries or pathEntries[0] != binDir:
        os.environ["PATH"] = os.pathsep.join([binDir, path]) if path else binDir


def bootstrap() -> None:
    """Ensure the persistent skill env and re-exec with its Python if needed."""
    if os.environ.get(ENV_ACTIVE_VAR) == "1":
        return
    if os.environ.get(SKIP_VAR) == "1":
        return

    pythonPath = runEnsureEnv("--print-python")
    prefix = runEnsureEnv("--print-prefix")
    current = Path(sys.executable).resolve()
    target = Path(pythonPath).resolve()

    if current == target:
        os.environ[ENV_ACTIVE_VAR] = "1"
        prependEnvBinToPath(prefix)
        return

    env = os.environ.copy()
    env[ENV_ACTIVE_VAR] = "1"
    prependEnvBinToPath(prefix)
    env["PATH"] = os.environ["PATH"]
    os.execve(str(target), [str(target), *sys.argv], env)
