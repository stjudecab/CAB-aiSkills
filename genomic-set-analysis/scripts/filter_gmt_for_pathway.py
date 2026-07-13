#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `genomic-set-analysis` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Filter a GMT file before pathway enrichment by gene-count thresholds.

Default policy (unless the user overrides in the agent workflow):
    - keep only gene sets with at least ``--minGenes`` genes (default 5),
    - for intersection batches, keep at most ``--topN`` sets ranked by gene count
      (default 10); pass ``--topN 0`` for no cap (typical for original input sets).
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import OrderedDict
from pathlib import Path
from typing import List, Tuple

import pandas as pd

LOGGER = logging.getLogger("filter_gmt_for_pathway")


def configureLogging() -> None:
    """Configure stderr logging for the filter script.

    Returns:
        None.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="### [%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


def parseArguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.

    Raises:
        SystemExit: On argparse failure.
        ValueError: When numeric thresholds are invalid.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Filter a GMT file for pathway enrichment: keep sets with at least "
            "--minGenes genes and, optionally, only the top --topN sets by gene count."
        )
    )
    parser.add_argument("--gmt", required=True, help="Input GMT file path.")
    parser.add_argument("--output", required=True, help="Filtered GMT output path.")
    parser.add_argument(
        "--manifest",
        default="",
        help="Optional TSV manifest recording inclusion/exclusion per set.",
    )
    parser.add_argument(
        "--minGenes",
        type=int,
        default=5,
        help="Minimum gene count required to include a set (default 5).",
    )
    parser.add_argument(
        "--topN",
        type=int,
        default=10,
        help=(
            "Maximum number of sets to keep after minGenes filtering, ranked by gene count "
            "descending (default 10). Use 0 for no cap (typical for original input sets)."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
    args = parser.parse_args()
    if args.minGenes < 1:
        raise ValueError("--minGenes must be >= 1.")
    if args.topN < 0:
        raise ValueError("--topN must be >= 0.")
    return args


def readGmt(gmtPath: Path) -> "OrderedDict[str, List[str]]":
    """Read a GMT file into an ordered set-name to gene-list mapping.

    Args:
        gmtPath (Path): Path to the GMT file.

    Returns:
        OrderedDict[str, List[str]]: Set names mapped to deduplicated gene lists.

    Raises:
        ValueError: When the GMT contains no non-empty gene sets.
    """
    geneSets: "OrderedDict[str, List[str]]" = OrderedDict()
    with open(gmtPath, "r", encoding="utf-8") as handle:
        for row in handle:
            fields = row.rstrip("\n").split("\t")
            if len(fields) < 3:
                continue
            genes = [gene for gene in fields[2:] if gene.strip() != ""]
            if genes:
                geneSets[fields[0]] = genes
    if not geneSets:
        raise ValueError(f"No non-empty gene sets found in GMT: {gmtPath}")
    return geneSets


def selectSetsForPathway(
    geneSets: "OrderedDict[str, List[str]]",
    minGenes: int,
    topN: int,
) -> Tuple["OrderedDict[str, List[str]]", List[dict]]:
    """Select gene sets that meet the default pathway-enrichment policy.

    Args:
        geneSets (OrderedDict[str, List[str]]): Input gene sets.
        minGenes (int): Minimum genes required for inclusion.
        topN (int): Maximum sets to keep after ranking by size; ``0`` means no cap.

    Returns:
        Tuple[OrderedDict[str, List[str]], List[dict]]: Filtered gene sets and per-set
        decision rows for the manifest.
    """
    ranked = sorted(geneSets.items(), key=lambda item: len(item[1]), reverse=True)
    manifestRows: List[dict] = []
    eligible: List[Tuple[str, List[str]]] = []
    for setName, genes in ranked:
        geneCount = len(genes)
        if geneCount < minGenes:
            manifestRows.append(
                {
                    "set_name": setName,
                    "gene_count": geneCount,
                    "included": "false",
                    "reason": f"below_minGenes_{minGenes}",
                }
            )
            continue
        eligible.append((setName, genes))

    if topN > 0:
        selected = eligible[:topN]
        for setName, genes in eligible[topN:]:
            manifestRows.append(
                {
                    "set_name": setName,
                    "gene_count": len(genes),
                    "included": "false",
                    "reason": f"outside_top_{topN}",
                }
            )
    else:
        selected = eligible

    filtered: "OrderedDict[str, List[str]]" = OrderedDict()
    for setName, genes in selected:
        filtered[setName] = genes
        manifestRows.append(
            {
                "set_name": setName,
                "gene_count": len(genes),
                "included": "true",
                "reason": "selected",
            }
        )
    manifestRows.sort(key=lambda row: (-int(row["gene_count"]), row["set_name"]))
    return filtered, manifestRows


def writeGmt(geneSets: "OrderedDict[str, List[str]]", outPath: Path) -> None:
    """Write gene sets to a GMT file.

    Args:
        geneSets (OrderedDict[str, List[str]]): Gene sets to write.
        outPath (Path): Destination GMT path.

    Returns:
        None.

    Raises:
        ValueError: When no gene sets remain after filtering.
    """
    if not geneSets:
        raise ValueError("No gene sets remain after filtering; adjust --minGenes or --topN.")
    with open(outPath, "w", encoding="utf-8") as handle:
        for setName, genes in geneSets.items():
            handle.write("\t".join([setName, "genomic-set-analysis"] + genes) + "\n")


def main() -> None:
    """Entry point: filter a GMT file for pathway enrichment.

    Returns:
        None.

    Raises:
        FileExistsError: When outputs exist and ``--overwrite`` was not given.
        ValueError: When filtering removes every set.
    """
    configureLogging()
    args = parseArguments()
    gmtPath = Path(args.gmt)
    outPath = Path(args.output)
    if not gmtPath.is_file():
        raise FileNotFoundError(f"GMT file not found: {gmtPath}")
    if outPath.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists: {outPath}. Use --overwrite to replace it.")

    geneSets = readGmt(gmtPath)
    filtered, manifestRows = selectSetsForPathway(geneSets, args.minGenes, args.topN)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    writeGmt(filtered, outPath)
    LOGGER.info(
        "Wrote filtered GMT with %d/%d sets: %s",
        len(filtered),
        len(geneSets),
        outPath,
    )

    if args.manifest:
        manifestPath = Path(args.manifest)
        if manifestPath.exists() and not args.overwrite:
            raise FileExistsError(f"Manifest exists: {manifestPath}. Use --overwrite.")
        frame = pd.DataFrame(manifestRows)
        frame.to_csv(manifestPath, sep="\t", index=False)
        LOGGER.info("Wrote pathway filter manifest: %s", manifestPath)

    if not filtered:
        raise ValueError(
            "No gene sets passed the filter. Lower --minGenes, raise --topN, or ask the user "
            "whether to run enrichment on smaller sets."
        )


if __name__ == "__main__":
    from skill_env import bootstrap

    bootstrap()
    main()
