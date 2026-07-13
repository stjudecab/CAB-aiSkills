#!/usr/bin/env python3
# Copyright (c) 2026 Wojciech Rosikiewicz && St Jude Children's Research Hospital.
# Part of the CAB-aiSkills `genomic-set-analysis` skill.
# Licensed under CC BY-NC-SA 4.0 (see repository LICENSE.txt).
"""Order-independent overlap of genomic region sets (or gene sets) via Intervene.

This is the portable core of the CAB-aiSkills ``genomic-set-analysis`` skill and a
reworked, HPC-independent successor to the in-house ``IntervenePeaksCombine.py``
wrapper for the Intervene tool (https://github.com/asntech/intervene).

Scientific intent:
    Given two or more peak/region sets (BED / narrowPeak) or gene sets (GMT), build a
    single union of elements, mark membership per input, and split that union into
    mutually exclusive combinatorial sectors (A-only, A and B, A and B and C, ...).
    Overlap structure is plotted with Intervene (Venn / UpSet / pairwise). Operating on
    the union makes the result independent of input order, at the documented cost that
    the union can contain fewer regions than any single "A overlaps B" pairwise count.

What this script deliberately does NOT do (handled by the agent per SKILL.md):
    - Peak annotation (delegated to the ``genomic-regions-annotation`` skill).
    - Pathway enrichment (delegated to the ``pathway-enrichment-enrichr`` skill).
    - Motif enrichment and deeptools heatmaps (not yet available; planned).
    - Any LSF/``bsub`` scheduling (removed; everything runs locally).

Reproducibility:
    A ``run_metadata.json`` records a UTC run ID, the exact command, resolved inputs and
    parameters, every Intervene command executed, and the versions of Python, Intervene,
    BEDTools, pybedtools, pandas, and numpy. A human-readable ``logs/commands.log`` mirrors
    the executed shell commands.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from run_logging import (
    addReproducibilityArguments,
    appendCommandLog,
    commandLineString,
    configureLogging,
    runIdUtc,
    writeAgentArtifacts,
)

LOGGER = logging.getLogger("intervene_peaks_combine")

GENOMIC_SUFFIXES = (".bed", ".narrowpeak", ".narrowPeak", ".broadPeak", ".broadpeak")
DEFAULT_MAX_LABEL_LENGTH = 15


def autoLabelFromPath(path: str) -> str:
    """Derive a default label from a BED-like file path.

    Args:
        path (str): Path to a region file.

    Returns:
        str: Basename with a common genomic suffix removed.
    """
    return re.sub(
        r"\.(bed|narrowPeak|narrowpeak|broadPeak|broadpeak)$",
        "",
        os.path.basename(path),
    )


def labelsAreShortEnough(labels: List[str], maxLen: int = DEFAULT_MAX_LABEL_LENGTH) -> bool:
    """Return whether every label is already short and unique.

    Args:
        labels (List[str]): Candidate analysis labels.
        maxLen (int): Maximum allowed length per label. Defaults to 15.

    Returns:
        bool: ``True`` when all labels are non-empty, at most ``maxLen`` characters, and unique.
    """
    if not labels:
        return False
    if len(labels) != len(set(labels)):
        return False
    return all(0 < len(label) <= maxLen for label in labels)


def writeSetLabelsManifest(
    interveneDir: Path,
    mode: str,
    inputSource: str,
    inputList: List[str],
    originalLabels: List[str],
    analysisLabels: List[str],
) -> Path:
    """Write a TSV mapping original set names to the analysis labels used in outputs.

    Args:
        interveneDir (Path): The ``<prefix>.intervene/`` output directory.
        mode (str): Either ``genomic`` or ``geneSet``.
        inputSource (str): Raw ``-i`` value (comma-separated BEDs, GMT path, or manifest path).
        inputList (List[str]): Resolved input paths (BED mode) or analysis labels (GMT mode).
        originalLabels (List[str]): Labels before any agent shortening.
        analysisLabels (List[str]): Labels used for filenames, matrices, and Intervene plots.

    Returns:
        Path: Path to ``setLabelsManifest.tsv``.
    """
    manifestPath = interveneDir / "setLabelsManifest.tsv"
    rows = []
    for idx, (inp, original, analysis) in enumerate(
        zip(inputList, originalLabels, analysisLabels), start=1
    ):
        if mode == "geneSet":
            inputIdentifier = inputSource
            originalSetName = original
        else:
            inputIdentifier = inp
            originalSetName = original
        rows.append(
            {
                "input_index": idx,
                "input_identifier": inputIdentifier,
                "original_label": originalSetName,
                "analysis_label": analysis,
                "labels_unchanged": "true" if original == analysis else "false",
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(manifestPath, sep="\t", index=False)
    LOGGER.info("Wrote set label manifest: %s", manifestPath)
    return manifestPath


def commandOutput(command: List[str]) -> str:
    """Run a command and return its combined stdout/stderr text, never raising.

    Args:
        command (List[str]): Command and arguments to execute.

    Returns:
        str: Captured output stripped of trailing whitespace, or an error marker when the
        executable is missing or fails.
    """
    try:
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        return proc.stdout.decode("utf-8", errors="replace").strip()
    except FileNotFoundError:
        return f"NOT_FOUND ({command[0]})"
    except Exception as exc:  # pragma: no cover - defensive
        return f"ERROR ({exc})"


def collectToolVersions() -> Dict[str, str]:
    """Collect versions of the tools used, for the reproducibility record.

    Returns:
        Dict[str, str]: Mapping of tool name to a version string. Values are best-effort;
        missing tools are recorded as ``NOT_FOUND`` rather than raising.
    """
    try:
        import pybedtools

        pybedtoolsVersion = getattr(pybedtools, "__version__", "unknown")
    except Exception:  # pragma: no cover - defensive
        pybedtoolsVersion = "unknown"
    intervene = commandOutput(["intervene", "--version"])
    if intervene.startswith("NOT_FOUND") or intervene.startswith("ERROR"):
        intervene = commandOutput(["intervene", "-v"])
    return {
        "python": sys.version.split()[0],
        "intervene": intervene or "unknown",
        "bedtools": commandOutput(["bedtools", "--version"]) or "unknown",
        "pybedtools": pybedtoolsVersion,
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }


def parseArguments() -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments with resolved ``inputList`` and ``names``.

    Raises:
        SystemExit: On argparse failure.
        FileNotFoundError: When an input file does not exist.
        ValueError: When inputs, labels, or figure size are inconsistent.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Order-independent overlap of genomic region sets (or gene sets) using "
            "Intervene. Produces Venn/UpSet/pairwise plots, a membership matrix, per-sector "
            "BED/gene-list files, and a reproducibility record. Annotation, pathway "
            "enrichment, motif enrichment, deeptools, and expression plots are handled by "
            "the agent per SKILL.md, not by this script."
        )
    )
    parser.add_argument(
        "-i",
        "--inputPeaks",
        dest="inputPeaks",
        required=True,
        help=(
            "Comma-separated list of BED/narrowPeak files (>=2). Alternatively a single "
            "'*.gmt' file (gene-set mode) or a single '*.tsv' manifest with two columns "
            "(BED path, label; no header; '#' comments ignored)."
        ),
    )
    parser.add_argument(
        "-n",
        "--names",
        dest="names",
        default="auto",
        help=(
            "Comma-separated analysis labels matching -i order. These short names are used in "
            "output filenames, matrices, and Intervene plots. Default 'auto' strips the file "
            "suffix from BED basenames. For a GMT file, use this to supply shortened labels "
            "while preserving the original GMT set names in setLabelsManifest.tsv. Ignored for "
            "TSV-manifest input (labels come from the manifest)."
        ),
    )
    parser.add_argument(
        "-o",
        "--outputPrefix",
        dest="outputPrefix",
        default="genomicSetAnalysis",
        help="Analysis prefix used for the '<prefix>.intervene/' output directory and files.",
    )
    parser.add_argument(
        "--outputDir",
        dest="outputDir",
        default=".",
        help=(
            "Parent directory that will contain '<outputPrefix>.intervene/'. Point this at "
            "'agentResults/' for skill runs. Default: current directory."
        ),
    )
    parser.add_argument(
        "--figSize",
        dest="figSize",
        default="10,6",
        help="Figure size as 'width,height' integers. Default '10,6'.",
    )
    parser.add_argument(
        "--toPlot",
        dest="toPlot",
        default="venn,upset",
        help=(
            "Comma-separated plot types: any of 'venn', 'upset', 'pairwise', or 'ignore' to "
            "skip plotting (matrix and sets are still written). Default 'venn,upset'."
        ),
    )
    parser.add_argument(
        "--mbColor",
        dest="mbColor",
        default="#BF1010",
        help="[UpSet] Main bar plot color. Default '#BF1010'.",
    )
    parser.add_argument(
        "--sbColor",
        dest="sbColor",
        default="#727272",
        help="[UpSet] Set-size bar plot color. Default '#727272'.",
    )
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="Overwrite an existing '<outputPrefix>.intervene/' directory instead of failing.",
    )
    parser.add_argument(
        "--dryRun",
        dest="dryRun",
        action="store_true",
        help="Validate inputs and print the planned Intervene commands without executing.",
    )
    addReproducibilityArguments(parser)
    args = parser.parse_args()

    args.inputList, args.gmtMode, args.gmtContent, args.names, args.originalLabels = resolveInputs(
        args.inputPeaks, args.names
    )
    if not labelsAreShortEnough(args.names):
        LOGGER.info(
            "Analysis labels exceed %d characters or are not all unique: %s. "
            "Consider shorter -n values; see SKILL.md.",
            DEFAULT_MAX_LABEL_LENGTH,
            args.names,
        )

    figParts = [p.strip() for p in str(args.figSize).split(",")]
    if len(figParts) != 2 or not all(p.lstrip("-").isdigit() for p in figParts):
        raise ValueError(
            f"Invalid --figSize '{args.figSize}'. Expected 'width,height' with two integers."
        )
    args.figSizeParsed = (int(figParts[0]), int(figParts[1]))

    args.plotVenn = "venn" in args.toPlot and "ignore" not in args.toPlot
    args.plotUpset = "upset" in args.toPlot and "ignore" not in args.toPlot
    args.plotPairwise = "pairwise" in args.toPlot and "ignore" not in args.toPlot
    if args.plotVenn and len(args.inputList) > 6:
        LOGGER.warning("More than 6 inputs: Venn diagram disabled (UpSet still available).")
        args.plotVenn = False
    if args.gmtMode:
        args.plotPairwise = False
    return args


def resolveInputs(
    inputPeaks: str, names: str
) -> Tuple[List[str], bool, "OrderedDict[str, List[str]]", List[str], List[str]]:
    """Resolve raw ``-i``/``-n`` values into input files/sets, mode, and labels.

    Args:
        inputPeaks (str): Raw comma-separated ``-i`` value (multiple BEDs, or a single
            ``*.gmt`` or ``*.tsv`` file).
        names (str): Raw ``-n`` value or ``'auto'``.

    Returns:
        Tuple[List[str], bool, OrderedDict[str, List[str]], List[str], List[str]]: A 5-tuple of
        ``(inputList, gmtMode, gmtContent, analysisLabels, originalLabels)``. In gene-set mode
        ``inputList`` holds analysis labels and ``gmtContent`` maps analysis label to gene list;
        otherwise ``gmtContent`` is empty and ``inputList`` holds BED file paths.

    Raises:
        FileNotFoundError: When an input file does not exist.
        ValueError: When the input configuration is unsupported or labels mismatch.
    """
    inputList = [x for x in inputPeaks.split(",") if x != ""]
    gmtMode = False
    gmtContent: "OrderedDict[str, List[str]]" = OrderedDict()
    labels: List[str]

    if len(inputList) == 1:
        single = inputList[0]
        if not os.path.isfile(single):
            raise FileNotFoundError(f"Input file does not exist: {single}")
        if single.endswith(GENOMIC_SUFFIXES):
            raise ValueError(
                "Only one BED/narrowPeak file was given. Provide >=2 region files, or a "
                "single '*.gmt' (gene sets) or '*.tsv' (manifest) file."
            )
        if single.endswith(".gmt"):
            gmtMode = True
            labels = []
            originalLabels: List[str] = []
            with open(single, "r", encoding="utf-8") as handle:
                for row in handle:
                    fields = row.rstrip("\n").split("\t")
                    setName = re.sub(r"[ :/\\(),\[\]]", "_", fields[0])
                    genes = [g for g in fields[2:] if g != ""]
                    if genes:
                        gmtContent[setName] = genes
                        labels.append(setName)
                        originalLabels.append(setName)
            if len(gmtContent) < 2:
                raise ValueError(
                    "Fewer than two non-empty gene sets parsed from the GMT file; nothing to overlap."
                )
            if names != "auto":
                analysisLabels = [label.strip() for label in names.split(",") if label.strip() != ""]
                if len(analysisLabels) != len(originalLabels):
                    raise ValueError(
                        f"Number of --names labels ({len(analysisLabels)}) does not match the number "
                        f"of gene sets in the GMT file ({len(originalLabels)})."
                    )
                remapped: "OrderedDict[str, List[str]]" = OrderedDict()
                for original, analysis in zip(originalLabels, analysisLabels):
                    remapped[analysis] = gmtContent[original]
                gmtContent = remapped
                labels = analysisLabels
            inputList = labels
            return inputList, gmtMode, gmtContent, labels, originalLabels
        if single.endswith(".tsv"):
            frame = pd.read_csv(
                single, sep="\t", header=None, usecols=[0, 1], names=["path", "label"], comment="#"
            )
            frame.dropna(how="all", inplace=True)
            frame["path"] = frame["path"].astype(str).str.strip()
            frame["label"] = frame["label"].astype(str).str.strip()
            frame = frame[frame["path"] != ""]
            if len(frame) < 2:
                raise ValueError(
                    f"The manifest '{single}' must list at least two BED entries; found {len(frame)}."
                )
            inputList = [os.path.abspath(p) for p in frame["path"].tolist()]
            for bed in inputList:
                if not os.path.isfile(bed):
                    raise FileNotFoundError(f"BED listed in manifest does not exist: {bed}")
            labels = frame["label"].tolist()
            if names != "auto":
                LOGGER.warning("--names ignored; labels are taken from the TSV manifest.")
            return inputList, gmtMode, gmtContent, labels, labels
        raise ValueError(
            f"Unsupported single input '{single}'. Expected multiple BEDs, or one '*.gmt'/'*.tsv'."
        )

    for bed in inputList:
        if not os.path.isfile(bed):
            raise FileNotFoundError(f"Input file does not exist: {bed}")
    originalLabels = [autoLabelFromPath(bed) for bed in inputList]
    if names == "auto":
        labels = originalLabels
    else:
        labels = [label.strip() for label in names.split(",") if label.strip() != ""]
    if len(labels) != len(inputList):
        raise ValueError(
            f"Number of labels ({len(labels)}) does not match number of inputs ({len(inputList)})."
        )
    return inputList, gmtMode, gmtContent, labels, originalLabels


def runShell(command: str, commandsLog: Path, dryRun: bool, allowFailure: bool = False) -> bool:
    """Run a shell command, logging it, and fail fast on a non-zero exit code.

    Args:
        command (str): Full shell command to execute.
        commandsLog (Path): File to append the command to for auditing.
        dryRun (bool): When ``True`` the command is logged but not executed.
        allowFailure (bool): When ``True`` a non-zero exit is logged as a prominent
            warning and reported (not raised); use only for genuinely optional steps
            (e.g. cosmetic pairwise plots that can hit upstream tool/library
            incompatibilities). Defaults to ``False`` (fail fast).

    Returns:
        bool: ``True`` when the command succeeded (or was skipped via ``dryRun``),
        ``False`` when it failed but ``allowFailure`` was set.

    Raises:
        RuntimeError: When the command exits with a non-zero status and
            ``allowFailure`` is ``False``.
    """
    LOGGER.info("CMD: %s", command)
    with open(commandsLog, "a", encoding="utf-8") as handle:
        handle.write(command + "\n")
    if dryRun:
        return True
    proc = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = proc.stdout.decode("utf-8", errors="replace")
    if output.strip():
        LOGGER.info("OUTPUT: %s", output.strip())
    if proc.returncode != 0:
        if allowFailure:
            LOGGER.warning(
                "Optional step failed with exit code %d and was skipped: %s\n%s",
                proc.returncode,
                command,
                output,
            )
            return False
        raise RuntimeError(
            f"Command failed with exit code {proc.returncode}: {command}\n{output}"
        )
    return True


def stageOriginalInputs(inputList: List[str], labels: List[str], destDir: Path) -> List[str]:
    """Copy original BED inputs into ``destDir`` under label-based names for annotation.

    Copying (not modifying) preserves canonical raw inputs while giving the annotation and
    pathway-enrichment addons a self-contained directory keyed by human-readable labels.

    Args:
        inputList (List[str]): Absolute or relative BED input paths.
        labels (List[str]): Labels aligned with ``inputList``.
        destDir (Path): Destination directory (created if missing).

    Returns:
        List[str]: Paths of the staged BED files.
    """
    destDir.mkdir(parents=True, exist_ok=True)
    staged: List[str] = []
    for bed, label in zip(inputList, labels):
        safeLabel = re.sub(r"[^0-9A-Za-z._-]+", "_", label)
        target = destDir / f"{safeLabel}.bed"
        shutil.copyfile(bed, target)
        staged.append(str(target))
    return staged


def buildSetsCounted(setsDir: Path, countedDir: Path) -> int:
    """Copy files from ``setsDir`` into ``countedDir`` prefixed with a zero-padded count.

    The count prefix (number of regions/genes) makes downstream selection of the largest
    sectors deterministic and lexicographically sortable.

    Args:
        setsDir (Path): Directory of per-sector files produced by Intervene.
        countedDir (Path): Destination directory (created if missing).

    Returns:
        int: Number of files written.
    """
    countedDir.mkdir(parents=True, exist_ok=True)
    created = 0
    for path in sorted(glob.glob(os.path.join(str(setsDir), "*"))):
        if os.path.isdir(path):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            count = sum(1 for line in handle if line.strip())
        shutil.copy2(path, countedDir / f"{count:09d}__{os.path.basename(path)}")
        created += 1
    return created


def writeGmt(setToGenes: "OrderedDict[str, List[str]]", outPath: Path) -> None:
    """Write a GMT file from an ordered mapping of set name to gene list.

    Args:
        setToGenes (OrderedDict[str, List[str]]): Ordered set-name to gene-list mapping.
        outPath (Path): Destination ``.gmt`` path.

    Returns:
        None.
    """
    with open(outPath, "w", encoding="utf-8") as handle:
        for setName, genes in setToGenes.items():
            if not genes:
                continue
            handle.write("\t".join([setName, "genomic-set-analysis"] + list(genes)) + "\n")


def runGeneSetMode(args: argparse.Namespace, interveneDir: Path, commandsLog: Path) -> None:
    """Run the workflow for gene-set (GMT) input.

    Args:
        args (argparse.Namespace): Parsed arguments (``gmtContent``, ``names``, plotting flags).
        interveneDir (Path): The ``<prefix>.intervene/`` output directory.
        commandsLog (Path): Auditing log for executed commands.

    Returns:
        None.
    """
    prefix = args.outputPrefix
    elemFiles: List[str] = []
    unionElements: set = set()
    matrixPath = interveneDir / f"{prefix}.matrix.tsv"
    with open(matrixPath, "w", encoding="utf-8") as matrix:
        matrix.write("ElementID\t" + "\t".join(args.names) + "\n")
        for setName in args.gmtContent:
            unionElements.update(args.gmtContent[setName])
            elemPath = interveneDir / f"{prefix}.{setName}.geneSet.txt"
            with open(elemPath, "w", encoding="utf-8") as handle:
                handle.write("\n".join(args.gmtContent[setName]) + "\n")
            elemFiles.append(str(elemPath))
        for element in sorted(unionElements):
            flags = ["1" if element in args.gmtContent[s] else "0" for s in args.gmtContent]
            matrix.write(element + "\t" + "\t".join(flags) + "\n")
    LOGGER.info("Wrote membership matrix: %s", matrixPath)

    figSize = f"{args.figSizeParsed[0]} {args.figSizeParsed[1]}"
    namesArg = ",".join(args.names)
    inputsArg = " ".join(elemFiles)
    saveOverlaps = "--save-overlaps"
    if args.plotVenn:
        runShell(
            f"intervene venn -i {inputsArg} --names {namesArg} -o {interveneDir} "
            f"--project {prefix} --figsize {figSize} --type list {saveOverlaps}",
            commandsLog,
            args.dryRun,
        )
        saveOverlaps = ""
    if args.plotUpset:
        runShell(
            f'intervene upset -i {inputsArg} --names {namesArg} -o {interveneDir} '
            f'--project {prefix} --figsize {figSize} --mbcolor "{args.mbColor}" '
            f'--sbcolor "{args.sbColor}" --type list {saveOverlaps}',
            commandsLog,
            args.dryRun,
        )

    setsDir = interveneDir / "sets"
    if setsDir.is_dir():
        buildSetsCounted(setsDir, interveneDir / "setsCounted")
        intersectionGmt: "OrderedDict[str, List[str]]" = OrderedDict()
        for txt in sorted(glob.glob(os.path.join(str(setsDir), "*.txt"))):
            with open(txt, "r", encoding="utf-8") as handle:
                genes = [g.strip() for g in handle if g.strip()]
            intersectionGmt[os.path.basename(txt).replace(".txt", "")] = genes
        writeGmt(intersectionGmt, interveneDir / "intersections.gmt")
        LOGGER.info("Wrote intersections.gmt for pathway enrichment of combinatorial sectors.")
    writeGmt(args.gmtContent, interveneDir / "originalSets.gmt")
    LOGGER.info("Wrote originalSets.gmt for pathway enrichment of the original gene sets.")


def runGenomicMode(args: argparse.Namespace, interveneDir: Path, commandsLog: Path) -> Dict[str, object]:
    """Run the workflow for genomic-region (BED) input.

    Merges inputs into a union, marks membership, splits into sectors with Intervene, and
    stages original inputs for downstream annotation/pathway enrichment.

    Args:
        args (argparse.Namespace): Parsed arguments (``inputList``, ``names``, plotting flags).
        interveneDir (Path): The ``<prefix>.intervene/`` output directory.
        commandsLog (Path): Auditing log for executed commands.

    Returns:
        Dict[str, object]: Summary with the number of merged regions and staged input paths.

    Raises:
        ImportError: When ``pybedtools`` is not installed.
    """
    from pybedtools import BedTool

    prefix = args.outputPrefix
    merged = BedTool(args.inputList[0])
    for bed in args.inputList[1:]:
        merged = merged.cat(BedTool(bed), postmerge=True)
    mergedPath = interveneDir / f"{prefix}.mergedPeaks_all.bed"
    merged.saveas(str(mergedPath))
    LOGGER.info("Merged %d regions from %d inputs into %s", len(merged), len(args.inputList), mergedPath)

    matrix: "OrderedDict[Tuple[str, str, str], List[int]]" = OrderedDict()
    for region in merged:
        matrix[(region[0], region[1], region[2])] = [0] * len(args.inputList)
    fromMergedFiles: List[str] = []
    for idx, (bed, label) in enumerate(zip(args.inputList, args.names)):
        hits = merged.intersect(BedTool(bed), wa=True, u=True)
        safeLabel = re.sub(r"[^0-9A-Za-z._-]+", "_", label)
        outPath = interveneDir / f"{prefix}.{safeLabel}.fromMerged.bed"
        hits.saveas(str(outPath))
        fromMergedFiles.append(str(outPath))
        for region in hits:
            matrix[(region[0], region[1], region[2])][idx] = 1
        LOGGER.info("Marked %d regions for '%s' -> %s", len(hits), label, outPath)

    matrixPath = interveneDir / f"{prefix}.mergedPeaks_matrix.tsv"
    with open(matrixPath, "w", encoding="utf-8") as handle:
        handle.write("chrm\tstart\tend\t" + "\t".join(args.names) + "\n")
        for key, flags in matrix.items():
            handle.write("\t".join(list(key) + [str(v) for v in flags]) + "\n")
    LOGGER.info("Wrote membership matrix: %s", matrixPath)

    figSize = f"{args.figSizeParsed[0]} {args.figSizeParsed[1]}"
    namesArg = ",".join(args.names)
    inputsArg = " ".join(fromMergedFiles)
    saveOverlaps = "--save-overlaps"
    if args.plotVenn:
        runShell(
            f"intervene venn -i {inputsArg} --names {namesArg} -o {interveneDir} "
            f"--project {prefix} --figsize {figSize} --type genomic {saveOverlaps}",
            commandsLog,
            args.dryRun,
        )
        saveOverlaps = ""
    if args.plotUpset:
        runShell(
            f'intervene upset -i {inputsArg} --names {namesArg} -o {interveneDir} '
            f'--project {prefix} --figsize {figSize} --mbcolor "{args.mbColor}" '
            f'--sbcolor "{args.sbColor}" --type genomic {saveOverlaps}',
            commandsLog,
            args.dryRun,
        )
    if args.plotPairwise:
        pairwiseSkipped: List[str] = []
        for htype in ("tribar", "color", "pie"):
            base = f"{interveneDir}/{prefix}"
            # Pairwise heatmaps are an optional visualization. Some Intervene releases call
            # the pandas ``DataFrame.ix`` accessor (removed in pandas >=1.0) inside the
            # heatmap layout, which aborts only the pairwise plot; the matrix, sectors, and
            # Venn/UpSet outputs are already written. Treat pairwise as best-effort so an
            # upstream-tool incompatibility does not discard the primary deliverables.
            ok = runShell(
                f"intervene pairwise -i {inputsArg} --names {namesArg} -o {interveneDir} "
                f"--project {prefix} --compute frac --htype {htype} --figsize {figSize} --type genomic "
                f"&& mv {base}_pairwise_frac.pdf {base}_pairwise_frac.{htype}.pdf "
                f"&& mv {base}_pairwise_frac.R {base}_pairwise_frac.{htype}.R",
                commandsLog,
                args.dryRun,
                allowFailure=True,
            )
            if not ok:
                pairwiseSkipped.append(htype)
        if pairwiseSkipped:
            LOGGER.warning(
                "Pairwise plot(s) %s were skipped due to an Intervene/pandas incompatibility "
                "(DataFrame.ix); the frac matrix is still written to %s_pairwise_frac_matrix.txt.",
                ",".join(pairwiseSkipped),
                f"{interveneDir}/{prefix}",
            )

    setsDir = interveneDir / "sets"
    if setsDir.is_dir():
        created = buildSetsCounted(setsDir, interveneDir / "setsCounted")
        LOGGER.info("Wrote %d counted sector files to setsCounted/", created)
    else:
        LOGGER.warning("No 'sets/' directory produced by Intervene (plotting may be disabled).")

    staged = stageOriginalInputs(args.inputList, args.names, interveneDir / "originalInputs")
    LOGGER.info("Staged %d original inputs under originalInputs/ for annotation/pathway steps.", len(staged))
    return {"mergedRegions": len(merged), "stagedOriginalInputs": staged}


def collectExistingOutputs(interveneDir: Path, prefix: str, gmtMode: bool) -> List[str]:
    """Return output artifact paths that exist after a successful run.

    Args:
        interveneDir (Path): The ``<prefix>.intervene/`` output directory.
        prefix (str): Analysis output prefix.
        gmtMode (bool): Whether the run used gene-set (GMT) input.

    Returns:
        List[str]: Absolute POSIX paths to files that were written.
    """
    candidates: List[Path] = [
        interveneDir / "run_metadata.json",
        interveneDir / "setLabelsManifest.tsv",
        interveneDir / "agent_request.txt",
        interveneDir / "agent_workflow.md",
        interveneDir / "logs" / "intervene_peaks_combine.log",
        interveneDir / "logs" / "commands.log",
    ]
    if gmtMode:
        candidates.extend(
            [
                interveneDir / f"{prefix}.matrix.tsv",
                interveneDir / "intersections.gmt",
                interveneDir / "originalSets.gmt",
            ]
        )
    else:
        candidates.extend(
            [
                interveneDir / f"{prefix}.mergedPeaks_all.bed",
                interveneDir / f"{prefix}.mergedPeaks_matrix.tsv",
            ]
        )
    for pattern in ("*.pdf", f"{prefix}.intervene_*.pdf"):
        candidates.extend(Path(p) for p in glob.glob(str(interveneDir / pattern)))
    return sorted({path.resolve().as_posix() for path in candidates if path.is_file()})


def writeRunMetadata(
    args: argparse.Namespace,
    interveneDir: Path,
    runId: str,
    versions: Dict[str, str],
    summary: Dict[str, object],
    agentRequestPath: Optional[Path],
    agentWorkflowPath: Optional[Path],
    logs: Dict[str, str],
) -> None:
    """Write ``run_metadata.json`` capturing inputs, parameters, and tool versions.

    Args:
        args (argparse.Namespace): Parsed arguments.
        interveneDir (Path): Output directory receiving the metadata file.
        runId (str): UTC run ID for this execution.
        versions (Dict[str, str]): Tool version strings.
        summary (Dict[str, object]): Mode-specific summary values.
        agentRequestPath (Optional[Path]): Path to saved user request text.
        agentWorkflowPath (Optional[Path]): Path to saved agent workflow notes.
        logs (Dict[str, str]): Paths to script and command logs.

    Returns:
        None.
    """
    metadata = {
        "skill": "genomic-set-analysis",
        "script": "intervene_peaks_combine.py",
        "run_id": runId,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command": commandLineString(),
        "working_directory": os.getcwd(),
        "mode": "geneSet" if args.gmtMode else "genomic",
        "inputs": args.inputList,
        "labels": args.names,
        "original_labels": args.originalLabels,
        "set_labels_manifest": str(interveneDir / "setLabelsManifest.tsv"),
        "output_directory": str(interveneDir.resolve()),
        "output_prefix": args.outputPrefix,
        "parameters": {
            "outputPrefix": args.outputPrefix,
            "outputDir": args.outputDir,
            "figSize": args.figSizeParsed,
            "toPlot": args.toPlot,
            "mbColor": args.mbColor,
            "sbColor": args.sbColor,
            "dryRun": args.dryRun,
        },
        "tool_versions": versions,
        "summary": summary,
        "outputs": collectExistingOutputs(interveneDir, args.outputPrefix, args.gmtMode),
        "agent_request_file": agentRequestPath.resolve().as_posix() if agentRequestPath else None,
        "agent_workflow_file": agentWorkflowPath.resolve().as_posix() if agentWorkflowPath else None,
        "logs": logs,
        "citation_keys": ["intervene", "bedtools", "pybedtools"],
        "attribution": {
            "method": "Intervene (Khan & Mathelier, BMC Bioinformatics 2017); BEDTools (Quinlan & Hall 2010).",
            "skill_package": "CAB-aiSkills genomic-set-analysis (orchestration only).",
            "note": (
                "Annotation, pathway enrichment, motif, deeptools, and expression are run by the "
                "agent via sibling skills; pass --agentRequest/--agentWorkflow to record agent steps."
            ),
        },
    }
    with open(interveneDir / "run_metadata.json", "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    LOGGER.info("Wrote reproducibility record: %s", interveneDir / "run_metadata.json")


def main() -> None:
    """Entry point: parse arguments, run the requested mode, and record metadata.

    Returns:
        None.

    Raises:
        FileExistsError: When the output directory exists and ``--overwrite`` was not given.
    """
    args = parseArguments()
    runId = args.runId or runIdUtc()

    interveneDir = Path(args.outputDir) / f"{args.outputPrefix}.intervene"
    if interveneDir.exists() and not args.overwrite and not args.dryRun:
        raise FileExistsError(
            f"Output directory already exists: {interveneDir}. Use --overwrite to reuse it."
        )
    interveneDir.mkdir(parents=True, exist_ok=True)
    logsDir = interveneDir / "logs"
    logsDir.mkdir(parents=True, exist_ok=True)
    scriptLog = logsDir / "intervene_peaks_combine.log"
    commandsLog = logsDir / "commands.log"
    configureLogging(scriptLog)

    command = commandLineString()
    appendCommandLog(commandsLog, runId, command)
    LOGGER.info("Run ID: %s", runId)
    LOGGER.info("Command: %s", command)
    LOGGER.info("Working directory: %s", os.getcwd())
    LOGGER.info("Output directory: %s", interveneDir.resolve())

    agentRequestPath, agentWorkflowPath = writeAgentArtifacts(interveneDir, args)
    if agentRequestPath:
        LOGGER.info("Wrote user request: %s", agentRequestPath)
    if agentWorkflowPath:
        LOGGER.info("Wrote agent workflow: %s", agentWorkflowPath)

    versions = collectToolVersions()
    LOGGER.info("Tool versions: %s", json.dumps(versions))
    LOGGER.info(
        "Mode: %s | inputs: %d | labels: %s",
        "geneSet" if args.gmtMode else "genomic",
        len(args.inputList),
        args.names,
    )

    if args.gmtMode:
        runGeneSetMode(args, interveneDir, commandsLog)
        summary: Dict[str, object] = {"geneSets": len(args.gmtContent)}
    else:
        summary = runGenomicMode(args, interveneDir, commandsLog)

    manifestPath = writeSetLabelsManifest(
        interveneDir=interveneDir,
        mode="geneSet" if args.gmtMode else "genomic",
        inputSource=args.inputPeaks,
        inputList=args.inputList,
        originalLabels=args.originalLabels,
        analysisLabels=args.names,
    )
    summary["setLabelsManifest"] = str(manifestPath)

    writeRunMetadata(
        args,
        interveneDir,
        runId,
        versions,
        summary,
        agentRequestPath,
        agentWorkflowPath,
        {
            "intervene_peaks_combine.log": scriptLog.resolve().as_posix(),
            "commands.log": commandsLog.resolve().as_posix(),
        },
    )
    LOGGER.info("Done. Results under: %s", interveneDir)


if __name__ == "__main__":
    from skill_env import bootstrap

    bootstrap()
    main()
