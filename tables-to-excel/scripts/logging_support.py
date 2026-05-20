#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: logging_support.py
# Description:
# Shared Rich console and file logging helpers for tables-to-excel CLI scripts.
#########################################################################

"""Shared Rich console + plain file logging helpers for ExcelBuilder CLI scripts."""

from __future__ import annotations

import logging
from importlib import metadata

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


def str2bool(value: object) -> bool:
    """Parse a loose boolean string flag.

    Args:
        value (object): User or config value (typically str).

    Returns:
        bool: Parsed boolean.

    Raises:
        SystemExit: If ``value`` is not a recognized boolean literal (exit code 1).
    """
    lgr = logging.getLogger("str2bool")
    text = str(value).lower()
    if text in ("yes", "true", "t", "y", "1"):
        return True
    if text in ("no", "false", "f", "n", "0"):
        return False
    lgr.critical(
        "Unrecognized parameter was set for %r. Program was aborted.",
        value,
    )
    raise SystemExit(1)


def logImportedPackageVersions(lgr: logging.Logger, names: tuple[str, ...]) -> None:
    """Log installed distribution versions for the given import/package names.

    Args:
        lgr (logging.Logger): Logger to write through.
        names (tuple[str, ...]): Distribution names to query (e.g. ``("pandas",)``).

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
