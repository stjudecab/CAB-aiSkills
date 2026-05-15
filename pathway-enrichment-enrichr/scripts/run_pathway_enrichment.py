#!/usr/bin/env python
"""Unified CLI for Enrichr pathway enrichment (single list, GMT batch, or gene-list manifest)."""

from __future__ import annotations

import argparse
import json
import logging
import string
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd

from enrichment_postprocess import (
    readGeneListLines,
    sanitizeGMTSetName,
    writeGenesListExcel,
    writeSummaryExcelsAndBarPlots,
)

SKILL_NAME = "pathway-enrichment-enrichr"
SKILL_VERSION = "1.0.0"


def utcRunId() -> str:
    """Return a UTC timestamp suitable for a run-scoped directory name.

    Returns:
        str: Timestamp in ``YYYYMMDDTHHMMSSZ`` format.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def prefixAllowed(value: str) -> bool:
    """Return True if ``value`` uses only characters accepted by enrichr_api GMT output dirs.

    Args:
        value (str): Proposed ``-o`` output prefix / folder name.

    Returns:
        bool: Whether the prefix is allowed.
    """
    allowed = set(string.ascii_lowercase + string.digits + "." + "-" + "_")
    return set(value.lower()) <= allowed


def writeRunMetadata(path: Path, payload: dict) -> None:
    """Serialize run metadata as JSON next to outputs.

    Args:
        path (Path): Destination JSON path.
        payload (dict): Serializable metadata.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def buildManifestGmt(manifest_path: Path, out_gmt: Path) -> None:
    """Build a GMT file from a TSV manifest of per-sample gene lists.

    Args:
        manifest_path (Path): TSV with columns ``file`` (or ``path``) and ``label`` (or ``sample``).
        out_gmt (Path): Destination GMT path.

    Returns:
        None.

    Raises:
        ValueError: If required columns are missing or a list file is empty.
    """
    df = pd.read_csv(manifest_path, sep="\t", dtype=str)
    colmap = {str(c).lower(): c for c in df.columns}
    file_col = colmap.get("file") or colmap.get("path") or colmap.get("gene_list")
    label_col = colmap.get("label") or colmap.get("sample") or colmap.get("name")
    if not file_col or not label_col:
        raise ValueError(
            "Manifest must include columns for file path and label "
            "(e.g. file, label). Got: {}".format(list(df.columns))
        )
    lines_out = []
    for i, r in df.iterrows():
        fp = Path(str(r[file_col]).strip()).expanduser()
        label = str(r[label_col]).strip()
        name = sanitizeGMTSetName(label, "sample{}".format(i))
        if not prefixAllowed(name):
            raise ValueError(
                "Sanitized label {!r} must contain only letters, digits, '.', '-', '_'.".format(
                    name
                )
            )
        genes = readGeneListLines(fp)
        if not genes:
            raise ValueError("No genes read from {}".format(fp))
        lines_out.append(
            "{}\t{}\t{}".format(name, name, "\t".join(genes)),
        )
    out_gmt.parent.mkdir(parents=True, exist_ok=True)
    out_gmt.write_text("\n".join(lines_out) + "\n", encoding="utf-8")


def parseArgs(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for pathway enrichment runs.

    Args:
        argv (list[str] | None): Arguments after the program name, or None for ``sys.argv``.

    Returns:
        argparse.Namespace: Parsed options.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run Enrichr pathway enrichment: Excel summaries and PDF bar plots for one gene list; "
            "GMT or manifest batch adds combined tables, heatmaps, and dot plots."
        )
    )
    parser.add_argument(
        "--mode",
        choices=["single", "gmt", "manifest"],
        required=True,
        help="single: one gene list; gmt: GMT file; manifest: TSV of per-sample gene list paths.",
    )
    parser.add_argument(
        "--outputDir",
        required=True,
        type=Path,
        help="Root directory for outputs (a run subfolder is created unless --runId names an existing path).",
    )
    parser.add_argument(
        "--runId",
        default=None,
        type=str,
        help="Run folder name under outputDir (default: UTC YYYYMMDDTHHMMSSZ).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow reusing an existing run directory (writes into it).",
    )
    parser.add_argument(
        "--libraryPreset",
        default="stjudehg",
        type=str,
        help="Enrichr preset keyword or comma-separated library names (enrichr_api -t).",
    )
    parser.add_argument(
        "--engine",
        choices=["Enrichr", "YeastEnrichr"],
        default="Enrichr",
        help="Enrichr backend.",
    )
    parser.add_argument("--genes", type=Path, help="Plain gene list file (single mode).")
    parser.add_argument(
        "--outPrefix",
        type=str,
        help="Output basename for single mode, or batch directory name for gmt/manifest (letters, digits, ., -, _).",
    )
    parser.add_argument(
        "--sampleLabel",
        type=str,
        default=None,
        help="Label for Excel sheets in single mode (default: outPrefix).",
    )
    parser.add_argument(
        "--excelStem",
        type=str,
        default=None,
        help="Excel output basename without suffix in single mode (default: outPrefix).",
    )
    parser.add_argument("--gmt", type=Path, help="GMT gene-set file (gmt mode).")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="TSV manifest with columns file<TAB>label (manifest mode).",
    )
    parser.add_argument(
        "--manifestStem",
        type=str,
        default="gene_lists",
        help="Intermediate GMT basename for manifest mode (default gene_lists).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: orchestrate enrichr_api and optional single-sample Excel/bar post-processing.

    Args:
        argv (list[str] | None): CLI arguments (excluding argv[0]).

    Returns:
        int: Process exit code (0 on success).
    """
    args = parseArgs(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    lgr = logging.getLogger("run_pathway_enrichment")

    run_id = args.runId or utcRunId()
    run_root = args.outputDir.expanduser().resolve() / run_id
    if run_root.exists() and not args.overwrite:
        lgr.error(
            "Run directory exists: %s (pass --overwrite to reuse).",
            run_root,
        )
        return 1
    run_root.mkdir(parents=True, exist_ok=True)

    enrichr_py = SCRIPTS_DIR / "enrichr_api.py"

    meta = {
        "skill": SKILL_NAME,
        "skill_version": SKILL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "library_preset": args.libraryPreset,
        "engine": args.engine,
        "run_root": str(run_root),
    }

    if args.outPrefix and not prefixAllowed(args.outPrefix):
        lgr.error(
            "outPrefix must contain only letters, digits, '.', '-', '_' (Enrichr batch constraint): %s",
            args.outPrefix,
        )
        return 1

    if args.mode == "single":
        if not args.genes or not args.outPrefix:
            lgr.error("single mode requires --genes and --outPrefix.")
            return 1
        genes_path = args.genes.expanduser().resolve()
        if not genes_path.is_file():
            lgr.error("Gene list not found: %s", genes_path)
            return 1
        out_prefix = args.outPrefix
        label = args.sampleLabel or out_prefix
        excel_stem = args.excelStem or out_prefix

        cmd = [
            sys.executable,
            str(enrichr_py),
            "-a",
            str(genes_path),
            "-o",
            out_prefix,
            "-m",
            "api,sum",
            "-t",
            args.libraryPreset,
            "-e",
            args.engine,
        ]
        lgr.info("Running: %s", " ".join(cmd))
        subprocess.run(cmd, cwd=str(run_root), check=True)

        genes = readGeneListLines(genes_path)
        writeGenesListExcel(
            genes,
            run_root / "{}.GenesLists.xlsx".format(excel_stem),
            column_title=label,
        )
        writeSummaryExcelsAndBarPlots(
            run_root,
            sample_prefix=out_prefix,
            excel_stem=excel_stem,
            sheet_label=label,
        )
        meta.update(
            {
                "genes": str(genes_path),
                "out_prefix": out_prefix,
                "excel_stem": excel_stem,
            }
        )

    elif args.mode == "gmt":
        if not args.gmt or not args.outPrefix:
            lgr.error("gmt mode requires --gmt and --outPrefix.")
            return 1
        gmt_path = args.gmt.expanduser().resolve()
        if not gmt_path.is_file():
            lgr.error("GMT not found: %s", gmt_path)
            return 1
        cmd = [
            sys.executable,
            str(enrichr_py),
            "-a",
            str(gmt_path),
            "-o",
            args.outPrefix,
            "-m",
            "gmt,api,sum",
            "-t",
            args.libraryPreset,
            "-e",
            args.engine,
        ]
        lgr.info("Running: %s", " ".join(cmd))
        subprocess.run(cmd, cwd=str(run_root), check=True)
        meta.update({"gmt": str(gmt_path), "gmt_output_dir": args.outPrefix})

    elif args.mode == "manifest":
        if not args.manifest or not args.outPrefix:
            lgr.error("manifest mode requires --manifest and --outPrefix.")
            return 1
        manifest_path = args.manifest.expanduser().resolve()
        if not manifest_path.is_file():
            lgr.error("Manifest not found: %s", manifest_path)
            return 1
        tmp_gmt = run_root / "{}.gmt".format(args.manifestStem)
        buildManifestGmt(manifest_path, tmp_gmt)
        cmd = [
            sys.executable,
            str(enrichr_py),
            "-a",
            str(tmp_gmt),
            "-o",
            args.outPrefix,
            "-m",
            "gmt,api,sum",
            "-t",
            args.libraryPreset,
            "-e",
            args.engine,
        ]
        lgr.info("Running: %s", " ".join(cmd))
        subprocess.run(cmd, cwd=str(run_root), check=True)
        meta.update({"manifest": str(manifest_path), "built_gmt": str(tmp_gmt)})

    writeRunMetadata(run_root / "run_metadata.json", meta)
    lgr.info("Finished. Primary outputs under %s", run_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
