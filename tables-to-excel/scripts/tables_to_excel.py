#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: tables_to_excel.py
# Description:
# Merge CSV/TSV/TXT tables into one multi-sheet Excel workbook with NameDictionary sheet.
#########################################################################

"""Merge tabular files into one multi-sheet Excel workbook with a path map sheet.

This module provides a CLI that reads CSV, TSV, or TXT tables and writes them to
a single ``.xlsx`` file using pandas and openpyxl. The first sheet is always
``NameDictionary``, mapping final sheet names to absolute source paths.

Excel worksheet names are limited to 31 characters (ECMA-376 / ISO 29500); this
script truncates basenames and deduplicates with ``(N)`` suffixes while respecting
that limit.
"""

from __future__ import annotations

import argparse
import logging
import os
import shlex
import sys
from pathlib import Path
from sys import argv, executable
from typing import List, Sequence, Tuple

import pandas as pd

from logging_support import configureLogging, logImportedPackageVersions

MAX_SHEET_NAME_LENGTH: int = 31  # Maximum sheet name length supported by Excel (ECMA-376 / ISO 29500)

logger = logging.getLogger(__name__)


def parseArgs(argv_override: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the tables-to-Excel workflow.

    Args:
        argv_override (Sequence[str] | None): If set, passed to ``parse_args``;
            otherwise ``sys.argv`` is used.

    Returns:
        argparse.Namespace: Parsed arguments including ``input``, ``output``,
            ``maxSheetNameLen``, ``overwrite``, and ``logLevel``.
    """
    lgr = logging.getLogger("parseArgs")
    lgr.info("Current working directory: %s", os.getcwd())
    lgr.info("Command used to run the program: python %s", " ".join(str(x) for x in argv))

    parser = argparse.ArgumentParser(
        description="Convert tabular data files to a multi-sheet Excel workbook.",
    )
    parser.add_argument(
        "-i",
        dest="input",
        required=True,
        help=(
            "Comma-separated list of CSV/TSV/TXT file paths, or a single .lst "
            "file containing one file path per line."
        ),
    )
    parser.add_argument(
        "-o",
        dest="output",
        required=True,
        help="Output file path prefix. The workbook is written to <OUTPUT>.xlsx.",
    )
    parser.add_argument(
        "--maxSheetNameLen",
        type=int,
        default=MAX_SHEET_NAME_LENGTH,
        metavar="N",
        help=(
            f"Maximum Excel sheet name length (default: {MAX_SHEET_NAME_LENGTH}, "
            f"hard cap: {MAX_SHEET_NAME_LENGTH})."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    parser.add_argument(
        "--logLevel",
        default="INFO",
        action="store",
        type=str,
        required=False,
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default=INFO.",
    )
    if argv_override is not None:
        args = parser.parse_args(list(argv_override))
    else:
        args = parser.parse_args()

    logImportedPackageVersions(
        lgr,
        ("pandas", "openpyxl", "rich", "packaging"),
    )
    lgr.info("Current working directory: %s", os.getcwd())
    command_used = " ".join(
        shlex.quote(arg) for arg in [os.path.basename(executable)] + argv
    )
    lgr.info("Command used to run script: %s", command_used)
    lgr.info("Input (-i): %s", args.input)
    lgr.info("Output (-o): %s", args.output)
    lgr.info("maxSheetNameLen: %s", args.maxSheetNameLen)
    lgr.info("overwrite: %s", args.overwrite)
    lgr.info("logLevel: %s", args.logLevel)
    return args


def clampMaxSheetNameLen(requested: int) -> int:
    """Clamp user-provided max sheet name length to Excel's hard limit.

    Args:
        requested (int): Requested maximum length from the user.

    Returns:
        int: Effective maximum length, at most ``MAX_SHEET_NAME_LENGTH``.
    """
    if requested > MAX_SHEET_NAME_LENGTH:
        logger.warning(
            "--maxSheetNameLen %s exceeds Excel limit %s; clamping to %s.",
            requested,
            MAX_SHEET_NAME_LENGTH,
            MAX_SHEET_NAME_LENGTH,
        )
        return MAX_SHEET_NAME_LENGTH
    return requested


def resolve_input_files(input_spec: str, base_dir: Path | None = None) -> List[Path]:
    """Resolve the ``-i`` value into a list of existing tabular file paths.

    Args:
        input_spec (str): Raw ``-i`` value: comma-separated paths or one ``.lst`` file.
        base_dir (Path | None): Directory for resolving relative paths in ``.lst`` files;
            defaults to current working directory.

    Returns:
        List[Path]: Ordered, resolved absolute paths to input tables.

    Raises:
        FileNotFoundError: If the list file or any listed table path does not exist.
        ValueError: If an unsupported file extension is encountered.
    """
    base = base_dir if base_dir is not None else Path.cwd()
    trimmed = input_spec.strip()
    raw_parts = [p.strip() for p in trimmed.split(",") if p.strip()]
    if (
        len(raw_parts) == 1
        and Path(raw_parts[0]).expanduser().suffix.lower() == ".lst"
    ):
        spec_path = Path(raw_parts[0]).expanduser()
        list_file = spec_path if spec_path.is_absolute() else (base / spec_path)
        list_file = list_file.resolve()
        logger.debug("Reading input list file: %s", list_file)
        if not list_file.is_file():
            raise FileNotFoundError(
                f"Input list file not found at path '{list_file}'. "
                f"Expected an existing .lst file listing one data path per line."
            )
        lines: List[str] = []
        text = list_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
        paths: List[Path] = []
        list_parent = list_file.parent
        for raw in lines:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = (list_parent / p).resolve()
            else:
                p = p.resolve()
            paths.append(p)
    else:
        paths = []
        for raw in raw_parts:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = (base / p).resolve()
            else:
                p = p.resolve()
            paths.append(p)

    for p in paths:
        validateTableExtension(p)
        if not p.is_file():
            raise FileNotFoundError(
                f"Input table file not found at path '{p}'. "
                f"Expected an existing file with extension .csv, .tsv, or .txt."
            )
    return paths


def validateTableExtension(path: Path) -> None:
    """Ensure ``path`` uses a supported tabular extension.

    Args:
        path (Path): Candidate input file path.

    Raises:
        ValueError: If the suffix is not ``.csv``, ``.tsv``, or ``.txt``.
    """
    suffix = path.suffix.lower()
    if suffix not in (".csv", ".tsv", ".txt"):
        raise ValueError(
            f"Unsupported table extension '{path.suffix}' for file '{path}'. "
            f"Expected one of: .csv, .tsv, .txt."
        )


def detect_separator(path: Path) -> str:
    """Return the field separator for ``path`` based on its extension.

    Args:
        path (Path): Input table file path.

    Returns:
        str: ``','`` for CSV or ``'\\t'`` for TSV/TXT.

    Raises:
        ValueError: If the extension is not supported.
    """
    suffix = path.suffix.lower()
    logger.debug("Detecting separator for %s (suffix=%s)", path, suffix)
    if suffix == ".csv":
        return ","
    if suffix in (".tsv", ".txt"):
        return "\t"
    raise ValueError(
        f"Cannot detect separator for '{path}': unsupported extension '{path.suffix}'. "
        f"Expected .csv, .tsv, or .txt."
    )


def ensure_string_column_headers(table: pd.DataFrame, source_path: Path) -> None:
    """Ensure column labels are strings; warn if coercion was needed.

    Args:
        table (pd.DataFrame): Loaded table (modified in place if needed).
        source_path (Path): Source path for log messages.

    Returns:
        None.
    """
    original = list(table.columns)
    if all(isinstance(c, str) for c in original):
        return
    logger.warning(
        "Coercing non-string column headers to str for file '%s'.",
        source_path,
    )
    table.columns = [str(c) for c in original]


def load_table(path: Path) -> pd.DataFrame:
    """Load a delimited table into a DataFrame without mutating column semantics.

    Args:
        path (Path): Path to a ``.csv``, ``.tsv``, or ``.txt`` file.

    Returns:
        pd.DataFrame: Loaded table preserving columns as read by pandas.

    Raises:
        ValueError: If the file extension is unsupported.
    """
    sep = detect_separator(path)
    logger.info("Loading table: %s", path)
    table = pd.read_csv(path, sep=sep, encoding="utf-8")
    ensure_string_column_headers(table, path)
    return table


def truncate_sheet_name(name: str, max_length: int) -> str:
    """Truncate a worksheet name to the active maximum length.

    Args:
        name (str): Proposed sheet name (typically a file stem).
        max_length (int): Maximum allowed length (positive).

    Returns:
        str: ``name`` unchanged if shorter than or equal to ``max_length``;
            otherwise truncated to ``max_length`` characters.
    """
    if len(name) <= max_length:
        return name
    logger.warning(
        "Truncating sheet name from length %s to %s: %r",
        len(name),
        max_length,
        name[:50] + ("..." if len(name) > 50 else ""),
    )
    return name[:max_length]


def make_unique_sheet_name(base: str, max_len: int, suffix_num: int) -> str:
    """Build a sheet name ``base`` + ``(suffix_num)`` fitting within ``max_len``.

    Args:
        base (str): Truncated base name prior to deduplication suffix.
        max_len (int): Maximum total sheet name length.
        suffix_num (int): Positive integer for the ``(N)`` suffix.

    Returns:
        str: Sheet name of length at most ``max_len``.
    """
    suffix = f"({suffix_num})"
    max_base = max_len - len(suffix)
    if max_base < 1:
        raise ValueError(
            f"max_len {max_len} is too small to fit suffix {suffix!r}."
        )
    truncated = base[:max_base] if len(base) > max_base else base
    return truncated + suffix


def deduplicate_sheet_names(names: List[str], max_len: int) -> List[str]:
    """Assign unique sheet names by appending ``(1)``, ``(2)``, … when needed.

    The first occurrence of a truncated name is kept unchanged. Later collisions
    receive ``(N)`` suffixes; the suffix counts toward ``max_len``, so the base
    is truncated further to fit.

    Args:
        names (List[str]): Ordered truncated candidate sheet names.
        max_len (int): Maximum length of each final sheet name.

    Returns:
        List[str]: Deduplicated names in the same order as ``names``.

    Raises:
        ValueError: If ``max_len`` cannot accommodate a suffix (internal error path).
    """
    used: set[str] = set()
    result: List[str] = []
    for idx, raw in enumerate(names):
        if raw not in used:
            final = raw
            logger.debug(
                "Dedup: index %s keeping first occurrence %r",
                idx,
                final,
            )
        else:
            k = 1
            while True:
                candidate = make_unique_sheet_name(raw, max_len, k)
                logger.debug(
                    "Dedup: index %s collision on %r trying %r (k=%s)",
                    idx,
                    raw,
                    candidate,
                    k,
                )
                if candidate not in used:
                    final = candidate
                    break
                k += 1
                if k > len(names) + 10:
                    raise ValueError(
                        f"Could not find unique sheet name for collision on {raw!r}."
                    )
        used.add(final)
        result.append(final)

    dup_check = [n for n in result if result.count(n) > 1]
    if dup_check:
        raise RuntimeError(
            f"Internal error: duplicate sheet names remain after deduplication: {set(dup_check)}"
        )
    return result


def sheet_names_from_paths(paths: Sequence[Path], max_len: int) -> List[str]:
    """Compute final worksheet names from input paths.

    Args:
        paths (Sequence[Path]): Input table paths in order.
        max_len (int): Maximum sheet name length.

    Returns:
        List[str]: Deduplicated sheet names.
    """
    stems = [truncate_sheet_name(p.stem, max_len) for p in paths]
    return deduplicate_sheet_names(list(stems), max_len)


def build_name_dictionary(
    sheet_names: Sequence[str],
    resolved_paths: Sequence[Path],
) -> pd.DataFrame:
    """Build the ``NameDictionary`` DataFrame.

    Args:
        sheet_names (Sequence[str]): Final short name per sheet.
        resolved_paths (Sequence[Path]): Absolute paths matching each row.

    Returns:
        pd.DataFrame: Two columns ``short name`` and ``path to original file``.

    Raises:
        ValueError: If length mismatch between arguments.
    """
    if len(sheet_names) != len(resolved_paths):
        raise ValueError(
            f"sheet_names length {len(sheet_names)} != paths length {len(resolved_paths)}."
        )
    abs_str = [str(p.resolve()) for p in resolved_paths]
    return pd.DataFrame(
        {"short name": list(sheet_names), "path to original file": abs_str}
    )


def excel_output_path(output_prefix: str | Path) -> Path:
    """Resolve CLI ``-o`` value to the ``.xlsx`` path to write.

    Args:
        output_prefix (str | Path): User-supplied output prefix or path.

    Returns:
        Path: Target workbook path ending in ``.xlsx``.
    """
    out = Path(output_prefix).expanduser()
    if out.suffix.lower() == ".xlsx":
        return out
    return out.with_suffix(".xlsx")


def write_excel(
    excel_path: Path,
    name_dictionary: pd.DataFrame,
    sheets: Sequence[Tuple[str, pd.DataFrame]],
    overwrite: bool,
) -> None:
    """Write NameDictionary first, then each data sheet, using openpyxl.

    Args:
        excel_path (Path): Destination ``.xlsx`` file.
        name_dictionary (pd.DataFrame): First-sheet content.
        sheets (Sequence[Tuple[str, pd.DataFrame]]): (sheet_name, data) pairs.
        overwrite (bool): If False, refuse to write if ``excel_path`` exists.

    Raises:
        FileExistsError: If ``excel_path`` exists and ``overwrite`` is False.

    Returns:
        None.
    """
    if excel_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: '{excel_path}'. "
            f"Pass --overwrite to replace it."
        )
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Writing workbook: %s", excel_path.resolve())
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        name_dictionary.to_excel(
            writer, sheet_name="NameDictionary", index=False
        )
        logger.info("Wrote sheet: NameDictionary")
        for sheet_name, table in sheets:
            logger.info("Writing sheet: %s", sheet_name)
            table.to_excel(writer, sheet_name=sheet_name, index=False)
    logger.info("Successfully wrote workbook: %s", excel_path.resolve())


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI: parse args, load tables, and write the workbook.

    Args:
        argv (Sequence[str] | None): Optional argument list (without script name).

    Returns:
        int: Exit code ``0`` on success, ``1`` on error.
    """
    lgr_main = logging.getLogger("main")
    configureLogging(analysisPrefix=Path(__file__).stem, logLevel="INFO")
    try:
        args = parseArgs(argv)
        configureLogging(analysisPrefix=Path(__file__).stem, logLevel=args.logLevel)
        max_len = clampMaxSheetNameLen(args.maxSheetNameLen)
        input_paths = resolve_input_files(args.input)
        final_names = sheet_names_from_paths(input_paths, max_len)
        name_df = build_name_dictionary(final_names, input_paths)
        loaded: List[Tuple[str, pd.DataFrame]] = []
        for p, sname in zip(input_paths, final_names):
            loaded.append((sname, load_table(p)))
        out_xlsx = excel_output_path(args.output)
        write_excel(out_xlsx, name_df, loaded, args.overwrite)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    lgr_main.info("All done, thank you!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
