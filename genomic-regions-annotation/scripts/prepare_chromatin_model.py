#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: prepare_chromatin_model.py
# Description:
# Download and preprocess ChromHMM Roadmap or Segway/ENCODE models into the
# skill-local cache as ChromHMM-compatible dense BED files.
#########################################################################

"""Prepare cached ChromHMM/Segway dense BED models for BEDinContext annotation."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

from chromatin_model_utils import (
    ROADMAP_BASE_URL,
    cacheDenseBedName,
    convertSegwayBed,
    isChromHmmCollection,
    isSegwayCollection,
    joinHeaderAndData,
    mergeDenseBedFile,
    rewriteRoadmapDenseBed,
    runLiftOver,
    splitTrackAndData,
)
from skill_reproducibility import (
    addReproducibilityArgs,
    appendCommandLog,
    collectBaseToolVersions,
    configureRunLogging,
    runIdUtc,
    skillRootFromScript,
    timestampIsoUtc,
    writeAgentArtifacts,
    writeRunMetadata,
)


def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for chromatin model preparation.

    Args:
        argv (list[str] | None): Optional argv override.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Download and preprocess a ChromHMM Roadmap or Segway/ENCODE chromatin "
            "state model into the skill-local cache as a dense BED accepted by BEDinContext.py."
        )
    )
    parser.add_argument(
        "--collection",
        required=True,
        help="Roadmap ChromHMM code (e.g. E123) or Segway ENCODE accession (e.g. ENCFF089AXD).",
    )
    parser.add_argument(
        "--genome",
        required=True,
        choices=["hg19", "hg38"],
        help="Target genome build for the cached dense BED.",
    )
    parser.add_argument(
        "--cacheDir",
        default=None,
        help="Model cache directory. Default: <skillRoot>/cache/",
    )
    parser.add_argument(
        "--skillRoot",
        default=None,
        help="Skill package root. Default: parent of scripts/.",
    )
    parser.add_argument(
        "--forceRefresh",
        action="store_true",
        help="Redownload and reprocess even if a cached dense BED already exists.",
    )
    parser.add_argument(
        "--copyToRunDir",
        default=None,
        help="Optional directory that receives a copy of the prepared model and metadata.",
    )
    addReproducibilityArgs(parser)
    return parser.parse_args(argv)


def loadRoadmapMetadata(path: Path) -> dict[str, dict[str, str]]:
    """Load Roadmap collection metadata keyed by Collection ID.

    Args:
        path (Path): Path to RoadmapCollectionsMetadata.tsv.

    Returns:
        dict[str, dict[str, str]]: Metadata rows by collection.

    Raises:
        FileNotFoundError: If the metadata file is missing.
        ValueError: If required columns are missing.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Expected Roadmap metadata at {path}, but the file was not found."
        )
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"Collection", "StatesFileLoc.hg38", "StatesFileLoc.hg19", "Name"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Roadmap metadata at {path} is missing required columns {sorted(required)}; "
                f"found {reader.fieldnames}."
            )
        rows = {row["Collection"].strip(): row for row in reader}
    return rows


def loadSegwayMetadata(path: Path) -> dict[str, dict[str, str]]:
    """Load Segway/ENCODE metadata keyed by File accession.

    Args:
        path (Path): Path to Segway_annotations_ENCODE_metadata.tsv.

    Returns:
        dict[str, dict[str, str]]: Metadata rows by accession.

    Raises:
        FileNotFoundError: If the metadata file is missing.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Expected Segway metadata at {path}, but the file was not found."
        )
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = {row["File accession"].strip(): row for row in reader}
    return rows


def downloadUrl(url: str, destination: Path) -> None:
    """Download a remote file to a local path.

    Args:
        url (str): Source URL.
        destination (Path): Local destination path.

    Returns:
        None.

    Raises:
        RuntimeError: If the download fails.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Downloading %s -> %s", url, destination)
    try:
        with urllib.request.urlopen(url, timeout=300) as response, destination.open("wb") as out:
            shutil.copyfileobj(response, out)
    except Exception as exc:
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc


def prepareChromHmm(
    collection: str,
    genome: str,
    roadmapMeta: dict[str, dict[str, str]],
    scratchDir: Path,
    cachePath: Path,
) -> dict:
    """Download and preprocess a Roadmap ChromHMM dense BED.

    Args:
        collection (str): Roadmap collection code (e.g. ``E123``).
        genome (str): ``hg19`` or ``hg38``.
        roadmapMeta (dict[str, dict[str, str]]): Metadata table.
        scratchDir (Path): Temporary working directory.
        cachePath (Path): Final cached dense BED path.

    Returns:
        dict: Model metadata payload.

    Raises:
        KeyError: If the collection is unknown.
    """
    key = collection.upper() if collection.upper() in roadmapMeta else collection
    if key not in roadmapMeta and collection not in roadmapMeta:
        # Normalize E001 vs e001
        matches = [k for k in roadmapMeta if k.upper() == collection.upper()]
        if not matches:
            raise KeyError(
                f"Collection {collection!r} was not found in RoadmapCollectionsMetadata.tsv. "
                f"Expected an ID such as E123."
            )
        key = matches[0]
    row = roadmapMeta[key]
    urlCol = "StatesFileLoc.hg38" if genome == "hg38" else "StatesFileLoc.hg19"
    url = row[urlCol].strip()
    if not url:
        url = (
            f"{ROADMAP_BASE_URL}/{key}_15_coreMarks_hg38lift_dense.bed.gz"
            if genome == "hg38"
            else f"{ROADMAP_BASE_URL}/{key}_15_coreMarks_dense.bed.gz"
        )

    rawPath = scratchDir / f"{key}_{genome}_raw.bed.gz"
    rewrittenPath = scratchDir / f"{key}_{genome}_rewritten.bed"
    downloadUrl(url, rawPath)
    nRows = rewriteRoadmapDenseBed(rawPath, rewrittenPath)
    shutil.copy2(rewrittenPath, cachePath)
    return {
        "source": "RoadmapEpigenomics",
        "collection": key,
        "name": row.get("Name", ""),
        "sample_type": row.get("Sample Type", ""),
        "genome": genome,
        "download_url": url,
        "preprocess_steps": [
            "download_gzip_dense_bed",
            "strip_state_name_suffix_from_column4",
        ],
        "n_data_rows": nRows,
        "dense_bed": cachePath.as_posix(),
    }


def prepareSegway(
    collection: str,
    genome: str,
    segwayMeta: dict[str, dict[str, str]],
    chainFile: Path,
    scratchDir: Path,
    cachePath: Path,
) -> dict:
    """Download and preprocess a Segway/ENCODE annotation to dense BED.

    Segway annotations are published in hg19. For ``genome=hg38``, UCSC liftOver
    is applied before adjacent-state merging.

    Args:
        collection (str): ENCODE file accession (e.g. ``ENCFF089AXD``).
        genome (str): ``hg19`` or ``hg38``.
        segwayMeta (dict[str, dict[str, str]]): Segway metadata.
        chainFile (Path): hg19→hg38 chain file.
        scratchDir (Path): Temporary working directory.
        cachePath (Path): Final cached dense BED path.

    Returns:
        dict: Model metadata payload.

    Raises:
        KeyError: If the accession is unknown.
        ValueError: If genome is unsupported.
    """
    key = collection.strip()
    if key not in segwayMeta:
        matches = [k for k in segwayMeta if k.upper() == key.upper()]
        if not matches:
            raise KeyError(
                f"Collection {collection!r} was not found in Segway_annotations_ENCODE_metadata.tsv."
            )
        key = matches[0]
    row = segwayMeta[key]
    url = (
        row.get("File download URL")
        or row.get("S3 URL")
        or row.get("Azure URL")
        or ""
    ).strip()
    if not url:
        raise ValueError(f"No download URL found for Segway accession {key}.")

    rawGz = scratchDir / f"{key}.bed.gz"
    convertedHg19 = scratchDir / f"{key}_hg19_converted.bed"
    downloadUrl(url, rawGz)
    nConverted = convertSegwayBed(
        rawGz,
        convertedHg19,
        trackName=f"{key}-{row.get('Dataset accession', '')} {row.get('Biosample term name', '')}",
        trackDescription=(
            f"Segway annotation of: {row.get('Biosample term name', '')} "
            f"{row.get('Biosample type', '')}"
        ),
    )

    steps = [
        "download_encode_bed_gz",
        "map_segway_state_names_to_integer_ids",
    ]
    workingBed = convertedHg19
    if genome == "hg38":
        headerPath = scratchDir / "header.txt"
        dataHg19 = scratchDir / "data_hg19.bed"
        dataHg38 = scratchDir / "data_hg38.bed"
        unmapped = scratchDir / "unmapped.bed"
        lifted = scratchDir / f"{key}_hg38_lifted.bed"
        splitTrackAndData(convertedHg19, headerPath, dataHg19)
        runLiftOver(dataHg19, chainFile, dataHg38, unmapped)
        joinHeaderAndData(headerPath, dataHg38, lifted)
        workingBed = lifted
        steps.append("liftover_hg19_to_hg38")
    elif genome != "hg19":
        raise ValueError(f"Unsupported genome for Segway prepare: {genome}")

    mergedPath = scratchDir / f"{key}_{genome}_merged.bed"
    nMerged = mergeDenseBedFile(workingBed, mergedPath)
    shutil.copy2(mergedPath, cachePath)
    steps.append("merge_adjacent_same_state_intervals")
    return {
        "source": "ENCODE_Segway",
        "collection": key,
        "name": row.get("Biosample term name", ""),
        "biosample_type": row.get("Biosample type", ""),
        "genome": genome,
        "native_assembly": "hg19",
        "download_url": url,
        "preprocess_steps": steps,
        "n_converted_rows": nConverted,
        "n_data_rows": nMerged,
        "dense_bed": cachePath.as_posix(),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for chromatin model preparation.

    Args:
        argv (list[str] | None): Optional argv override.

    Returns:
        int: Process exit code.
    """
    try:
        from skill_env import bootstrap

        bootstrap()
    except Exception:
        pass

    args = parseArgs(argv)
    skillRoot = Path(args.skillRoot).resolve() if args.skillRoot else skillRootFromScript(Path(__file__))
    cacheDir = Path(args.cacheDir).resolve() if args.cacheDir else (skillRoot / "cache")
    cacheDir.mkdir(parents=True, exist_ok=True)

    collection = args.collection.strip()
    genome = args.genome.strip()
    cachePath = cacheDir / cacheDenseBedName(collection.upper() if isChromHmmCollection(collection) else collection, genome)
    # Normalize ChromHMM collection casing in filename
    if isChromHmmCollection(collection):
        collectionNorm = collection.upper()
        cachePath = cacheDir / cacheDenseBedName(collectionNorm, genome)
    else:
        collectionNorm = collection

    runId = args.runId or runIdUtc()
    outputDir = Path(args.outputDir).resolve() if args.outputDir else None
    logPath = None
    commandsPath = None
    if outputDir is not None:
        outputDir.mkdir(parents=True, exist_ok=True)
        logPath = configureRunLogging(outputDir, "prepare_chromatin_model")
        commandsPath = appendCommandLog(outputDir, runId)
        writeAgentArtifacts(
            outputDir,
            agentRequest=args.agentRequest,
            agentRequestFile=Path(args.agentRequestFile) if args.agentRequestFile else None,
            agentWorkflow=args.agentWorkflow,
            agentWorkflowFile=Path(args.agentWorkflowFile) if args.agentWorkflowFile else None,
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    logging.info("Run ID: %s", runId)
    logging.info("Skill root: %s", skillRoot)
    logging.info("Cache directory: %s", cacheDir)
    logging.info("Requested collection=%s genome=%s", collectionNorm, genome)

    metaSidecar = cachePath.with_suffix(".model_meta.json")
    reusedCache = cachePath.is_file() and not args.forceRefresh
    modelMeta: dict

    refs = skillRoot / "references" / "chromatin-states"
    try:
        if reusedCache:
            logging.info("Reusing cached model: %s", cachePath)
            if metaSidecar.is_file():
                modelMeta = json.loads(metaSidecar.read_text(encoding="utf-8"))
            else:
                modelMeta = {
                    "collection": collectionNorm,
                    "genome": genome,
                    "dense_bed": cachePath.as_posix(),
                    "reused_cache": True,
                }
        else:
            with tempfile.TemporaryDirectory(prefix="chromatin_model_", dir=str(cacheDir)) as tmp:
                scratch = Path(tmp)
                if isChromHmmCollection(collectionNorm):
                    roadmapMeta = loadRoadmapMetadata(refs / "RoadmapCollectionsMetadata.tsv")
                    modelMeta = prepareChromHmm(
                        collectionNorm, genome, roadmapMeta, scratch, cachePath
                    )
                elif isSegwayCollection(collectionNorm):
                    segwayMeta = loadSegwayMetadata(
                        refs / "Segway_annotations_ENCODE_metadata.tsv"
                    )
                    chainFile = refs / "hg19ToHg38.over.chain"
                    modelMeta = prepareSegway(
                        collectionNorm,
                        genome,
                        segwayMeta,
                        chainFile,
                        scratch,
                        cachePath,
                    )
                else:
                    raise ValueError(
                        f"Unrecognized collection {collection!r}. Expected ChromHMM "
                        f"code like E123 or Segway accession like ENCFF089AXD."
                    )
            modelMeta["prepared_at_utc"] = timestampIsoUtc()
            metaSidecar.write_text(json.dumps(modelMeta, indent=2) + "\n", encoding="utf-8")
            logging.info("Wrote cached dense BED: %s", cachePath)
            logging.info("Wrote model metadata: %s", metaSidecar)

        modelMeta["reused_cache"] = reusedCache
        modelMeta["cache_path"] = cachePath.resolve().as_posix()
        modelMeta["model_meta_path"] = metaSidecar.resolve().as_posix()

        if args.copyToRunDir:
            destDir = Path(args.copyToRunDir).resolve()
            destDir.mkdir(parents=True, exist_ok=True)
            destBed = destDir / cachePath.name
            destMeta = destDir / metaSidecar.name
            shutil.copy2(cachePath, destBed)
            if metaSidecar.is_file():
                shutil.copy2(metaSidecar, destMeta)
            modelMeta["run_copy_dense_bed"] = destBed.as_posix()
            modelMeta["run_copy_model_meta"] = destMeta.as_posix()
            logging.info("Copied model into run directory: %s", destDir)

        # Always print the cache path on stdout for agent capture.
        print(cachePath.resolve().as_posix())

        if outputDir is not None:
            writeRunMetadata(
                outputDir / "run_metadata.json",
                {
                    "skill": "genomic-regions-annotation",
                    "script": "prepare_chromatin_model.py",
                    "run_id": runId,
                    "timestamp_utc": timestampIsoUtc(),
                    "command": " ".join(sys.argv),
                    "working_directory": Path.cwd().as_posix(),
                    "inputs": [
                        {
                            "collection": collectionNorm,
                            "genome": genome,
                        }
                    ],
                    "output_directory": outputDir.as_posix(),
                    "parameters": {
                        "collection": collectionNorm,
                        "genome": genome,
                        "forceRefresh": bool(args.forceRefresh),
                        "cacheDir": cacheDir.as_posix(),
                    },
                    "tool_versions": collectBaseToolVersions(Path(__file__)),
                    "summary": modelMeta,
                    "outputs": [
                        cachePath.resolve().as_posix(),
                        metaSidecar.resolve().as_posix(),
                    ],
                    "logs": {
                        "prepare_chromatin_model.log": logPath.as_posix() if logPath else None,
                        "commands.log": commandsPath.as_posix() if commandsPath else None,
                    },
                    "attribution": {
                        "method": "Prepare ChromHMM/Segway dense BED chromatin models",
                        "skill_package": "genomic-regions-annotation",
                    },
                },
            )
        return 0
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
