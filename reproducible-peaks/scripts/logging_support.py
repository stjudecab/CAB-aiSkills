#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: logging_support.py
# Description:
# Shared Rich console and file logging helpers for reproducible-peaks CLI scripts.
#########################################################################

"""Shared Rich console + plain file logging helpers for reproducible-peaks CLI scripts."""

from __future__ import annotations

import logging
from importlib import metadata
import platform
import subprocess
import sys

from rich.logging import RichHandler


def configureLogging(
    *,
    analysisPrefix: str,
    logLevel: str = "INFO",
) -> None:
    """Configure root logging with Rich console and an audit-style file handler.

    Args:
        analysisPrefix (str): Base name for ``<prefix>.log`` (no extension); pass
            ``Path(__file__).stem`` from the invoking script.
        logLevel (str): Level name, e.g. ``INFO``, ``DEBUG``.

    Returns:
        None.
    """
    root = logging.getLogger()
    root.disabled = False
    root.handlers.clear()
    level = getattr(logging, str(logLevel).upper(), logging.INFO)
    root.setLevel(level)

    streamhdlr = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_level=True,
        show_path=True,
    )
    filehdlr = logging.FileHandler(f"{analysisPrefix}.log", encoding="utf-8")
    root.addHandler(streamhdlr)
    root.addHandler(filehdlr)
    streamhdlr.setLevel(level)
    filehdlr.setLevel(level)
    filehdlr.setFormatter(
        logging.Formatter(
            "###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s"
        )
    )


def logImportedPackageVersions(lgr: logging.Logger, names: tuple[str, ...]) -> None:
    """Log installed distribution versions for the given import/package names.

    Args:
        lgr (logging.Logger): Logger to write through.
        names (tuple[str, ...]): Distribution names to query (e.g. ``("ChIP-R",)``).

    Returns:
        None.
    """
    lgr.info("Versions of selected packages:")
    for name in names:
        try:
            ver = metadata.version(name)
        except metadata.PackageNotFoundError:
            ver = "not installed"
        lgr.info("  %s==%s", name, ver)


def logRuntimeEnvironment(lgr: logging.Logger) -> None:
    """Log Python platform and optional ``chipr`` binary discovery.

    Args:
        lgr (logging.Logger): Logger to write through.

    Returns:
        None.
    """
    lgr.info("Python: %s", sys.version.replace("\n", " "))
    lgr.info("Platform: %s", platform.platform())
    for cmd in ("chipr", "chip-r", "ChIP-R"):
        try:
            proc = subprocess.run(
                [cmd, "-h"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if proc.returncode == 0:
                lgr.info("ChIP-R entrypoint on PATH: %s (exit 0)", cmd)
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    lgr.warning(
        "No ChIP-R CLI found on PATH (tried chipr, chip-r, ChIP-R). "
        "Install with: conda install bioconda::chip-r  OR  pip install ChIP-R"
    )
