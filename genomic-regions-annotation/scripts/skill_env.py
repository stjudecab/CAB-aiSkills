"""Bootstrap the persistent genomic-regions-annotation Conda environment."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ENV_ACTIVE_VAR = "GENOMIC_REGIONS_ANNOTATION_ENV_ACTIVE"
SKIP_VAR = "GENOMIC_REGIONS_ANNOTATION_SKIP_ENV_BOOTSTRAP"


def bootstrap() -> None:
    """Re-exec with the cached skill interpreter when needed.

    Returns:
        None.
    """
    if os.environ.get(SKIP_VAR) == "1":
        return
    if os.environ.get(ENV_ACTIVE_VAR) == "1":
        return

    scriptDir = Path(__file__).resolve().parent
    ensureEnv = scriptDir / "ensure_env.sh"
    if not ensureEnv.is_file():
        return

    try:
        pythonPath = subprocess.check_output(
            ["bash", str(ensureEnv), "--print-python"],
            text=True,
        ).strip()
        prefix = subprocess.check_output(
            ["bash", str(ensureEnv), "--print-prefix"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return

    if not pythonPath or not Path(pythonPath).exists():
        return

    current = Path(sys.executable).resolve()
    target = Path(pythonPath).resolve()
    env = os.environ.copy()
    env["PATH"] = f"{prefix}/bin:" + env.get("PATH", "")
    env[ENV_ACTIVE_VAR] = "1"

    if current != target:
        os.execve(str(target), [str(target), *sys.argv], env)

    os.environ["PATH"] = f"{prefix}/bin:" + os.environ.get("PATH", "")
    os.environ[ENV_ACTIVE_VAR] = "1"
