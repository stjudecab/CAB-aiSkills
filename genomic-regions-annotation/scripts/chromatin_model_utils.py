"""Utilities for ChromHMM / Segway chromatin-state model preprocessing."""

from __future__ import annotations

import gzip
import logging
import re
import shutil
import subprocess
from pathlib import Path

SEGWAY_STATE_MAP = {
    "Quiescent": "1",
    "ConstitutiveHet": "2",
    "FacultativeHet": "3",
    "Transcribed": "4",
    "Promoter": "5",
    "Enhancer": "6",
    "RegPermissive": "7",
    "Bivalent": "8",
    "LowConfidence": "9",
}

ROADMAP_BASE_URL = (
    "https://egg2.wustl.edu/roadmap/data/byFileType/chromhmmSegmentations/"
    "ChmmModels/coreMarks/jointModel/final"
)


def stripRoadmapStateColumn(rawValue: str) -> str:
    """Strip Roadmap dense-BED state labels to numeric IDs.

    Roadmap files use values like ``9_Het`` or ``15_Quies``; BEDinContext requires
    a numeric 4th column (e.g. ``9``).

    Args:
        rawValue (str): Raw fourth-column value.

    Returns:
        str: Numeric state ID string.
    """
    text = str(rawValue).strip()
    if "_" in text:
        return text.split("_", 1)[0]
    return text


def rewriteRoadmapDenseBed(inputPath: Path, outputPath: Path) -> int:
    """Rewrite a Roadmap dense BED so column 4 is numeric-only.

    Args:
        inputPath (Path): Raw downloaded dense BED (may be gzipped).
        outputPath (Path): Destination dense BED path.

    Returns:
        int: Number of data rows written (excluding track header).

    Raises:
        ValueError: If no data rows are found.
    """
    openFn = gzip.open if str(inputPath).endswith(".gz") else open
    mode = "rt"
    nRows = 0
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    with openFn(inputPath, mode, encoding="utf-8", errors="replace") as handleIn, outputPath.open(
        "w", encoding="utf-8"
    ) as handleOut:
        for line in handleIn:
            if not line.strip():
                continue
            if line.startswith("track") or line.startswith("browser"):
                handleOut.write(line if line.endswith("\n") else line + "\n")
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 4:
                continue
            fields[3] = stripRoadmapStateColumn(fields[3])
            handleOut.write("\t".join(fields) + "\n")
            nRows += 1
    if nRows == 0:
        raise ValueError(
            f"No dense-BED data rows found after Roadmap rewrite of {inputPath}."
        )
    return nRows


def convertSegwayBedLine(fields: list[str]) -> list[str] | None:
    """Convert one Segway BED row to ChromHMM-compatible dense format.

    Args:
        fields (list[str]): Tab-split BED fields (at least 9 columns expected).

    Returns:
        list[str] | None: Rewritten fields, or None if the state is unknown/skipped.
    """
    if len(fields) < 9:
        return None
    segwayCol4 = fields[3]
    if "_" in segwayCol4:
        _, stateName = segwayCol4.split("_", 1)
    else:
        stateName = segwayCol4
    if stateName not in SEGWAY_STATE_MAP:
        logging.warning("Unknown Segway state name %r; skipping line.", stateName)
        return None
    mapped = SEGWAY_STATE_MAP[stateName]
    return [
        fields[0],
        fields[1],
        fields[2],
        mapped,
        "0",
        fields[5],
        fields[6],
        fields[7],
        fields[8],
    ]


def convertSegwayBed(
    inputPath: Path,
    outputPath: Path,
    *,
    trackName: str,
    trackDescription: str,
) -> int:
    """Convert a gzipped or plain Segway BED to integer-state dense BED.

    Args:
        inputPath (Path): Input Segway BED (``.bed`` or ``.bed.gz``).
        outputPath (Path): Output dense BED path.
        trackName (str): Browser track name.
        trackDescription (str): Browser track description.

    Returns:
        int: Number of data rows written.
    """
    openFn = gzip.open if str(inputPath).endswith(".gz") else open
    nRows = 0
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    trackLine = (
        f'track name="{trackName}" description="{trackDescription}" '
        'visibility=1 itemRgb="On"\n'
    )
    with openFn(inputPath, "rt", encoding="utf-8", errors="replace") as handleIn, outputPath.open(
        "w", encoding="utf-8"
    ) as handleOut:
        handleOut.write(trackLine)
        for line in handleIn:
            text = line.strip()
            if not text or text.startswith("track") or text.startswith("browser"):
                continue
            converted = convertSegwayBedLine(text.split("\t"))
            if converted is None:
                continue
            handleOut.write("\t".join(converted) + "\n")
            nRows += 1
    if nRows == 0:
        raise ValueError(f"No Segway rows converted from {inputPath}.")
    return nRows


def mergeAdjacentSameState(sortedLines: list[str]) -> list[str]:
    """Merge back-to-back intervals that share chromosome, state, and color.

    Adjacent intervals where ``start == previous_end`` and the state/color match
    are collapsed. ThickStart/ThickEnd are reset to the merged start/end.

    Args:
        sortedLines (list[str]): Sorted BED data lines (no track header).

    Returns:
        list[str]: Merged BED lines.
    """
    merged: list[list[str]] = []
    prevFields: list[str] | None = None

    for line in sortedLines:
        fields = line.strip().split("\t")
        if len(fields) < 4:
            continue
        chrom = fields[0]
        start = int(fields[1])
        end = int(fields[2])
        state = fields[3]
        color = fields[8] if len(fields) > 8 else None

        if prevFields is None:
            prevFields = fields
            continue

        prevChrom = prevFields[0]
        prevEnd = int(prevFields[2])
        prevState = prevFields[3]
        prevColor = prevFields[8] if len(prevFields) > 8 else None

        if (
            chrom == prevChrom
            and state == prevState
            and color == prevColor
            and start == prevEnd
        ):
            prevFields[2] = str(end)
        else:
            if len(prevFields) > 7:
                prevFields[6] = prevFields[1]
                prevFields[7] = prevFields[2]
            merged.append(prevFields)
            prevFields = fields

    if prevFields is not None:
        if len(prevFields) > 7:
            prevFields[6] = prevFields[1]
            prevFields[7] = prevFields[2]
        merged.append(prevFields)

    return ["\t".join(fields) for fields in merged]


def mergeDenseBedFile(inputPath: Path, outputPath: Path) -> int:
    """Sort and merge adjacent same-state intervals in a dense BED file.

    Args:
        inputPath (Path): Dense BED with optional track header.
        outputPath (Path): Merged dense BED path.

    Returns:
        int: Number of merged data rows.
    """
    with inputPath.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    if not lines:
        raise ValueError(f"Empty dense BED: {inputPath}")

    header = ""
    dataLines = lines
    if lines[0].startswith("track") or lines[0].startswith("browser"):
        header = lines[0].rstrip("\n")
        dataLines = lines[1:]

    # Lexicographic sort by chrom,start,end is sufficient for merge adjacency.
    def sortKey(line: str) -> tuple:
        fields = line.strip().split("\t")
        return (fields[0], int(fields[1]), int(fields[2]))

    sortedLines = sorted((ln for ln in dataLines if ln.strip()), key=sortKey)
    mergedLines = mergeAdjacentSameState(sortedLines)

    outputPath.parent.mkdir(parents=True, exist_ok=True)
    with outputPath.open("w", encoding="utf-8") as handleOut:
        if header:
            handleOut.write(header + "\n")
        for line in mergedLines:
            handleOut.write(line + "\n")
    return len(mergedLines)


def runLiftOver(
    inputBed: Path,
    chainFile: Path,
    outputBed: Path,
    unmappedBed: Path,
) -> None:
    """Run UCSC liftOver on a header-free BED.

    Args:
        inputBed (Path): Header-free BED in source coordinates.
        chainFile (Path): Chain file (e.g. hg19ToHg38.over.chain).
        outputBed (Path): Lifted BED path.
        unmappedBed (Path): Unmapped regions path.

    Returns:
        None.

    Raises:
        FileNotFoundError: If ``liftOver`` is not on PATH or inputs are missing.
        RuntimeError: If liftOver exits non-zero.
    """
    if shutil.which("liftOver") is None:
        raise FileNotFoundError(
            "UCSC liftOver was not found on PATH. Install with: "
            "conda install bioconda::ucsc-liftover (via scripts/ensure_env.sh)."
        )
    if not chainFile.is_file():
        raise FileNotFoundError(f"Expected chain file at {chainFile}, but it was not found.")
    if not inputBed.is_file():
        raise FileNotFoundError(f"Expected liftOver input BED at {inputBed}, but it was not found.")

    outputBed.parent.mkdir(parents=True, exist_ok=True)
    unmappedBed.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "liftOver",
        str(inputBed),
        str(chainFile),
        str(outputBed),
        str(unmappedBed),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"liftOver failed (exit {proc.returncode}). stderr:\n{proc.stderr}"
        )


def splitTrackAndData(inputPath: Path, headerOut: Path, dataOut: Path) -> None:
    """Split a BED into track header and data lines.

    Args:
        inputPath (Path): Dense BED possibly with track/browser header.
        headerOut (Path): Path for header lines.
        dataOut (Path): Path for data lines.

    Returns:
        None.
    """
    headerLines: list[str] = []
    dataLines: list[str] = []
    with inputPath.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("track") or line.startswith("browser"):
                headerLines.append(line)
            elif line.strip():
                dataLines.append(line)
    headerOut.write_text("".join(headerLines), encoding="utf-8")
    dataOut.write_text("".join(dataLines), encoding="utf-8")


def joinHeaderAndData(headerPath: Path, dataPath: Path, outputPath: Path) -> None:
    """Concatenate track header and data into one dense BED.

    Args:
        headerPath (Path): Header file (may be empty).
        dataPath (Path): Data BED file.
        outputPath (Path): Final dense BED.

    Returns:
        None.
    """
    header = headerPath.read_text(encoding="utf-8") if headerPath.is_file() else ""
    data = dataPath.read_text(encoding="utf-8") if dataPath.is_file() else ""
    outputPath.write_text(header + data, encoding="utf-8")


def isChromHmmCollection(collection: str) -> bool:
    """Return True if the collection ID looks like a Roadmap ChromHMM code.

    Args:
        collection (str): Collection identifier.

    Returns:
        bool: True for IDs matching ``E`` + digits (e.g. ``E123``).
    """
    return bool(re.fullmatch(r"E\d+", collection.strip(), flags=re.IGNORECASE))


def isSegwayCollection(collection: str) -> bool:
    """Return True if the collection ID looks like an ENCODE Segway accession.

    Args:
        collection (str): Collection identifier.

    Returns:
        bool: True for IDs matching ``ENCFF*``.
    """
    return collection.strip().upper().startswith("ENCFF")


def cacheDenseBedName(collection: str, genome: str) -> str:
    """Build the canonical cache filename for a prepared dense BED.

    Args:
        collection (str): Collection ID (e.g. ``E123`` or ``ENCFF089AXD``).
        genome (str): Genome build (``hg19`` or ``hg38``).

    Returns:
        str: Filename such as ``E123_hg38_dense.bed``.
    """
    return f"{collection.strip()}_{genome.strip()}_dense.bed"


def aggregationOutputDirectory(resultsDir: str | Path, aggregationMetric: str) -> str:
    """Return the output directory for a regions or bp aggregation pass.

    Region-level (primary) results stay in ``resultsDir``. Base-pair summaries
    are isolated under ``resultsDir/aggregationByBp/``.

    Args:
        resultsDir (str | Path): Top-level BEDinContext output directory.
        aggregationMetric (str): ``regions`` or ``bp``.

    Returns:
        str: Directory path for that aggregation's tables and plots.

    Raises:
        ValueError: If ``aggregationMetric`` is not supported.
    """
    root = str(resultsDir)
    if aggregationMetric == "regions":
        return root
    if aggregationMetric == "bp":
        return str(Path(root) / "aggregationByBp")
    raise ValueError(f"Unsupported aggregationMetric={aggregationMetric!r}")
