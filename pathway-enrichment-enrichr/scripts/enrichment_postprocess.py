#!/usr/bin/env python
"""Post-processing for single-sample Enrichr outputs: Excel summaries and bar plots."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def readGeneListLines(path: Path) -> List[str]:
    """Read non-empty gene symbols from a one-per-line list file.

    Args:
        path (Path): Plain-text gene list path.

    Returns:
        List[str]: Stripped gene identifiers in file order.
    """
    genes: List[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            token = line.split()[0]
            genes.append(token)
    return genes


def sanitizeGMTSetName(raw: str, fallback: str) -> str:
    """Restrict gene-set names to characters accepted by enrichr_api GMT mode.

    Args:
        raw (str): Proposed set name (often a human label).
        fallback (str): Name used when sanitization removes all characters.

    Returns:
        str: Token containing only ``[A-Za-z0-9._-]``.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(raw)).strip("._-")
    return cleaned if cleaned else fallback


def writeGenesListExcel(genes: Iterable[str], out_path: Path, column_title: str) -> None:
    """Write a single-sheet workbook listing input genes (aligned with GMT batch style).

    Args:
        genes (Iterable[str]): Gene symbols to record.
        out_path (Path): Output ``*.GenesLists.xlsx`` path.
        column_title (str): Header label for the gene column (truncated to 31 chars for Excel).

    Returns:
        None.
    """
    lgr = logging.getLogger(__name__)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gene_list = list(genes)
    header = column_title[:31]
    df = pd.DataFrame({header: gene_list})
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="list", startrow=1, header=False)
        workbook = writer.book
        fmt = workbook.add_format(
            {
                "bold": True,
                "text_wrap": False,
                "valign": "bottom",
                "align": "left",
                "fg_color": "#D7E4BC",
                "border": 1,
            }
        )
        fmt.set_rotation(45)
        worksheet = writer.sheets["list"]
        worksheet.write(0, 0, header, fmt)
    lgr.info("Wrote gene list Excel: %s", out_path)


def writeSummaryExcelsAndBarPlots(
    run_dir: Path,
    sample_prefix: str,
    excel_stem: str,
    sheet_label: str,
) -> None:
    """Create FDR/nominal Excel summaries and top-pathway bar PDFs for one Enrichr prefix.

    Writes ``{excel_stem}.fc_q0.05.xlsx``, ``{excel_stem}.fc_p0.05.xlsx``, companion TXT listings,
    and ``{sample_prefix}.sum.q5.pdf`` / ``{sample_prefix}.sum.p5.pdf`` when corresponding
    tabular inputs exist under ``run_dir``.

    Args:
        run_dir (Path): Directory containing ``{sample_prefix}.sum.q5`` and ``.sum.p5`` when present.
        sample_prefix (str): Output prefix used with ``enrichr_api.py`` ``-o``.
        excel_stem (str): Base name for Excel outputs (no ``.xlsx`` suffix).
        sheet_label (str): Sheet name inside each workbook (truncated to 31 characters).

    Returns:
        None.
    """
    lgr = logging.getLogger(__name__)
    run_dir = run_dir.resolve()
    stem = excel_stem
    sheet = sheet_label[:31]

    def header_format_workbook(workbook):
        fmt = workbook.add_format(
            {
                "bold": True,
                "text_wrap": False,
                "valign": "bottom",
                "align": "left",
                "fg_color": "#D7E4BC",
                "border": 1,
            }
        )
        fmt.set_rotation(45)
        return fmt

    q5_path = run_dir / f"{sample_prefix}.sum.q5"
    p5_path = run_dir / f"{sample_prefix}.sum.p5"

    if q5_path.is_file() and q5_path.stat().st_size > 0:
        try:
            df = pd.read_csv(q5_path, sep="\t", float_precision="high")
        except pd.errors.EmptyDataError:
            lgr.warning("FDR table %s is empty; skipping FDR Excel/bar.", q5_path)
        else:
            q_xlsx = run_dir / f"{stem}.fc_q0.05.xlsx"
            q_txt = run_dir / f"{stem}.fc_q0.05_listOfSpreadsheets.txt"
            with pd.ExcelWriter(q_xlsx, engine="xlsxwriter") as outfile:
                header_format = header_format_workbook(outfile.book)
                df.to_excel(outfile, index=False, sheet_name=sheet, startrow=1, header=False)
                worksheet = outfile.sheets[sheet]
                worksheet.set_column("A:A", 50)
                worksheet.set_column("H:H", 20)
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
            with q_txt.open("w", encoding="utf-8") as fh:
                fh.write(f"{sample_prefix}\t{sheet_label}\n")

            df_plot = df.head(10).copy()
            df_plot["-log10(Adjusted P-value)"] = df_plot["Adjusted P-value"].apply(
                lambda val: -np.log10(val) if val > 10**-10 else -np.log10(10**-10)
            )
            df_plot = df_plot.sort_values("-log10(Adjusted P-value)", ascending=False)
            if len(df_plot) > 0:
                plt.clf()
                fig, ax = plt.subplots()
                sns.barplot(
                    x="-log10(Adjusted P-value)",
                    y="Term",
                    data=df_plot,
                    color="#BE4038",
                    ax=ax,
                )
                fig.savefig(
                    str(run_dir / f"{sample_prefix}.sum.q5.pdf"),
                    dpi=300,
                    bbox_inches="tight",
                )
                plt.close()
            else:
                lgr.warning("No rows for FDR bar plot for prefix %s", sample_prefix)
    else:
        lgr.warning("Skipping FDR Excel/bar: missing or empty %s", q5_path)

    if p5_path.is_file() and p5_path.stat().st_size > 0:
        try:
            df = pd.read_csv(p5_path, sep="\t", float_precision="high")
        except pd.errors.EmptyDataError:
            lgr.warning("Nominal-p table %s is empty; skipping nominal Excel/bar.", p5_path)
        else:
            p_xlsx = run_dir / f"{stem}.fc_p0.05.xlsx"
            p_txt = run_dir / f"{stem}.fc_p0.05_listOfSpreadsheets.txt"
            with pd.ExcelWriter(p_xlsx, engine="xlsxwriter") as outfile:
                header_format = header_format_workbook(outfile.book)
                df.to_excel(outfile, index=False, sheet_name=sheet, startrow=1, header=False)
                worksheet = outfile.sheets[sheet]
                worksheet.set_column("A:A", 50)
                worksheet.set_column("H:H", 20)
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
            with p_txt.open("w", encoding="utf-8") as fh:
                fh.write(f"{sample_prefix}\t{sheet_label}\n")

            df_plot = df.head(10).copy()
            df_plot["-log10(P-value)"] = df_plot["P-value"].apply(
                lambda val: -np.log10(val) if val > 10**-10 else -np.log10(10**-10)
            )
            df_plot = df_plot.sort_values("-log10(P-value)", ascending=False)
            if len(df_plot) > 0:
                plt.clf()
                fig, ax = plt.subplots()
                sns.barplot(
                    x="-log10(P-value)",
                    y="Term",
                    data=df_plot,
                    color="#FFA414",
                    ax=ax,
                )
                fig.savefig(
                    str(run_dir / f"{sample_prefix}.sum.p5.pdf"),
                    dpi=300,
                    bbox_inches="tight",
                )
                plt.close()
            else:
                lgr.warning("No rows for nominal-p bar plot for prefix %s", sample_prefix)
    else:
        lgr.warning("Skipping nominal-p Excel/bar: missing or empty %s", p5_path)

    lgr.info(
        "Single-sample summary artifacts completed under %s (Excel stem=%s).",
        run_dir,
        stem,
    )
