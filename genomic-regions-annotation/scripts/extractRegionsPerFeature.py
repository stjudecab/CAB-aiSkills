#!/usr/bin/env python
##########################################################################################
#
# Copyright (c) 2020-~ Wojciech Rosikiewicz && St Jude
# This source code is released for free distribution under the terms of the CreativeCommons BY-NC-SA 4.0 International License
#*Author: Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: extractRegionsPerFeature.py
#
##########################################################################################
#
# Extract feature-specific BED files and a combined GMT gene-set file from annotated
# peak tables produced by voom2anno.sh and annotateGenomicFeatures.py.
#
# Example:
# python extractRegionsPerFeature.py -i sample.voom.anno -o sample.byFeature
# python extractRegionsPerFeature.py -i sample.bed.anno
#
##########################################################################################

import sys
import json
import re
import logging
import inspect
import argparse

if "-h" not in sys.argv:
    import os
    from datetime import datetime, timezone
    from pathlib import Path

    import pandas as pd

ANALYSIS_PREFIX = "extractRegionsPerFeature"
DEFAULT_FEATURE_COLUMN = "FeatureAssignment"
DEFAULT_GENE_BODY_COLUMN = "inGeneBody"
DEFAULT_LOG2FC_COLUMN = "log2FC"
DEFAULT_FDR_COLUMN = "q.value"

FEATURE_NAME_REPLACEMENTS = {
    "Dis5 (5' distal regions)": "Dis5.5prime_distal_regions",
    "Dis3 (3' distal regions)": "Dis3.3prime_distal_regions",
    "TES (transcription end sites)": "TES.transcription_end_sites",
}


def configureLogging(analysisPrefix):
    logging.basicConfig(
        level=logging.INFO,
        format="###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler("{}.log".format(analysisPrefix)),
            logging.StreamHandler(),
        ],
        datefmt="%y-%m-%d %H:%M:%S",
    )


def parseArgs():
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    parser = argparse.ArgumentParser(
        description=(
            "Extract feature-specific BED files and a combined GMT gene-set file from "
            "annotated peak tables with FeatureAssignment and inGeneBody columns."
        )
    )
    parser.add_argument(
        "-i",
        "--infileName",
        help="Input annotated table (*.anno, *.tsv, *.txt, *.bed.anno, *.narrowPeak.anno, *.xlsx).",
        required=True,
        dest="infileName",
    )
    parser.add_argument(
        "-o",
        "--outDir",
        help="Output directory. Default: <input-basename>.byFeature beside the input file.",
        default=None,
        dest="outDir",
    )
    parser.add_argument(
        "--mode",
        help="Input mode: auto, bed, or voom. Default = auto.",
        default="auto",
        choices=["auto", "bed", "voom"],
        dest="mode",
    )
    parser.add_argument(
        "--featureColumn",
        help="Column containing genomic feature assignments. Default = FeatureAssignment.",
        default=DEFAULT_FEATURE_COLUMN,
        dest="featureColumn",
    )
    parser.add_argument(
        "--geneBodyColumn",
        help="Column containing gene-body overlap annotations. Default = inGeneBody.",
        default=DEFAULT_GENE_BODY_COLUMN,
        dest="geneBodyColumn",
    )
    parser.add_argument(
        "--log2FCColumn",
        help="Column containing log2 fold change values. Default = log2FC.",
        default=DEFAULT_LOG2FC_COLUMN,
        dest="log2FCColumn",
    )
    parser.add_argument(
        "--fdrColumn",
        help="Column containing FDR/q-values. Default = q.value.",
        default=DEFAULT_FDR_COLUMN,
        dest="fdrColumn",
    )
    parser.add_argument(
        "--fdrThreshold",
        help="FDR threshold for voom mode (strictly less than). Default = 0.05.",
        type=float,
        default=0.05,
        dest="fdrThreshold",
    )
    parser.add_argument(
        "--log2FCThreshold",
        help="Absolute log2FC threshold for voom mode. Default = 0.",
        type=float,
        default=0.0,
        dest="log2FCThreshold",
    )
    parser.add_argument(
        "--sheetName",
        help="Excel sheet name for .xlsx inputs. Default: first sheet.",
        default=None,
        dest="sheetName",
    )

    args = parser.parse_args()
    configureLogging(ANALYSIS_PREFIX)
    logger1.info("command used to run extraction script: python {}".format(" ".join(str(x) for x in sys.argv)))
    logger1.info("infileName: {}".format(args.infileName))
    logger1.info("outDir: {}".format(args.outDir))
    logger1.info("mode: {}".format(args.mode))
    logger1.info("featureColumn: {}".format(args.featureColumn))
    logger1.info("geneBodyColumn: {}".format(args.geneBodyColumn))
    logger1.info("log2FCColumn: {}".format(args.log2FCColumn))
    logger1.info("fdrColumn: {}".format(args.fdrColumn))
    logger1.info("fdrThreshold: {}".format(args.fdrThreshold))
    logger1.info("log2FCThreshold: {}".format(args.log2FCThreshold))
    logger1.info("sheetName: {}".format(args.sheetName))
    return args


def sanitizeFeatureName(name):
    s = str(name).strip()
    if s in FEATURE_NAME_REPLACEMENTS:
        return FEATURE_NAME_REPLACEMENTS[s]
    s = s.replace("'", "prime")
    s = re.sub(r"\s*\([^)]*\)", "", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w.\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def inputBasename(infileName):
    name = Path(infileName).name
    for suffix in [
        ".voom.anno.Ranks.tsv",
        ".bed.anno",
        ".narrowPeak.anno",
        ".broadPeak.anno",
        ".voom.anno",
        ".anno",
        ".tsv",
        ".txt",
        ".xlsx",
    ]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return Path(infileName).stem


def defaultOutDir(infileName):
    inPath = Path(infileName).resolve()
    return str(inPath.parent / "{}.byFeature".format(inputBasename(infileName)))


def loadInputTable(infileName, sheetName=None):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    inPath = Path(infileName)
    if not inPath.is_file():
        raise SystemExit("Input file does not exist: {}".format(infileName))

    suffix = inPath.suffix.lower()
    if suffix == ".xlsx":
        xl = pd.ExcelFile(infileName)
        useSheet = sheetName if sheetName is not None else xl.sheet_names[0]
        logger1.info("Reading Excel sheet '{}' from {}".format(useSheet, infileName))
        df = pd.read_excel(infileName, sheet_name=useSheet)
        return df, useSheet
    if suffix in [".tsv", ".txt", ".anno"] or infileName.endswith(".bed.anno") or infileName.endswith(".narrowPeak.anno") or infileName.endswith(".broadPeak.anno"):
        logger1.info("Reading tab-delimited file {}".format(infileName))
        return pd.read_csv(infileName, sep="\t", index_col=False), None

    raise SystemExit("Unsupported input file format: {}".format(infileName))


def detectMode(df, requestedMode, log2FCColumn, fdrColumn):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    if requestedMode != "auto":
        logger1.info("Mode explicitly set to {}.".format(requestedMode))
        return requestedMode

    hasDiff = log2FCColumn in df.columns and fdrColumn in df.columns
    mode = "voom" if hasDiff else "bed"
    logger1.info("Auto-detected mode '{}'.".format(mode))
    return mode


def validateRequiredColumns(df, featureColumn, geneBodyColumn, mode, log2FCColumn, fdrColumn):
    missing = []
    for col in [featureColumn, geneBodyColumn]:
        if col not in df.columns:
            missing.append(col)
    if mode == "voom":
        for col in [log2FCColumn, fdrColumn]:
            if col not in df.columns:
                missing.append(col)
    if missing:
        raise SystemExit(
            "Missing required column(s): {}. Regenerate annotations with annotateGenomicFeatures.py "
            "or provide alternate column names.".format(", ".join(missing))
        )


def parseRegionString(region):
    if ":" not in region or "-" not in region.split(":", 1)[1]:
        raise ValueError("Invalid Region format: {}".format(region))
    chrom, coords = region.split(":", 1)
    start, end = coords.split("-", 1)
    return chrom, int(start), int(end)


def normalizeCoordinates(df):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    work = df.copy()
    if {"chr", "start", "end"}.issubset(work.columns):
        work["chr"] = work["chr"].astype(str)
        work["start"] = work["start"].astype(int)
        work["end"] = work["end"].astype(int)
    elif "Region" in work.columns:
        parsed = work["Region"].apply(parseRegionString)
        work["chr"] = parsed.apply(lambda x: x[0])
        work["start"] = parsed.apply(lambda x: x[1])
        work["end"] = parsed.apply(lambda x: x[2])
    else:
        raise SystemExit("Input table must contain chr/start/end columns or a Region column.")

    invalid = work[work["start"] > work["end"]]
    if len(invalid) > 0:
        raise SystemExit("Found {} rows with start > end.".format(len(invalid)))
    logger1.info("Normalized coordinates for {} rows.".format(len(work)))
    return work


def filterForMode(df, mode, log2FCColumn, fdrColumn, fdrThreshold, log2FCThreshold):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    if mode == "bed":
        logger1.info("BED mode: no differential filtering applied.")
        return df.copy()

    sig = df[df[fdrColumn] < fdrThreshold].copy()
    sig["_direction"] = "neutral"
    sig.loc[sig[log2FCColumn] > log2FCThreshold, "_direction"] = "up"
    sig.loc[sig[log2FCColumn] < -log2FCThreshold, "_direction"] = "down"
    sig = sig[sig["_direction"].isin(["up", "down"])].copy()
    logger1.info(
        "Voom mode: {} total rows, {} significant ({} < {}), {} up, {} down after log2FC threshold {}.".format(
            len(df),
            len(df[df[fdrColumn] < fdrThreshold]),
            fdrColumn,
            fdrThreshold,
            len(sig[sig["_direction"] == "up"]),
            len(sig[sig["_direction"] == "down"]),
            log2FCThreshold,
        )
    )
    return sig


def parseGeneBodyGenes(value):
    if pd.isna(value):
        return []
    text = str(value).strip()
    if text in ["", "."]:
        return []
    genes = []
    for part in text.split(","):
        gene = part.strip()
        if gene and gene != ".":
            genes.append(gene)
    return genes


def collectUniqueGenes(values):
    genes = set()
    for value in values:
        genes.update(parseGeneBodyGenes(value))
    return sorted(genes)


def writeBedFile(bedPath, subDf):
    bed = subDf[["chr", "start", "end"]].sort_values(["chr", "start", "end"])
    bed.to_csv(bedPath, sep="\t", header=False, index=False)


def buildOutputGroups(df, mode, featureColumn):
    groups = []
    featureMap = {}
    for feature, featDf in df.groupby(featureColumn, sort=True):
        featureOriginal = str(feature)
        if featureOriginal in ["False", ""] or pd.isna(feature):
            continue
        safeFeature = sanitizeFeatureName(featureOriginal)
        featureMap[featureOriginal] = safeFeature
        if mode == "bed":
            groups.append(
                {
                    "feature_original": featureOriginal,
                    "feature_sanitized": safeFeature,
                    "direction": None,
                    "set_name": safeFeature,
                    "bed_filename": "{}.bed".format(safeFeature),
                    "dataframe": featDf,
                }
            )
        else:
            for direction in ["up", "down"]:
                sub = featDf[featDf["_direction"] == direction]
                if sub.empty:
                    continue
                setName = "{}.{}".format(safeFeature, direction)
                groups.append(
                    {
                        "feature_original": featureOriginal,
                        "feature_sanitized": safeFeature,
                        "direction": direction,
                        "set_name": setName,
                        "bed_filename": "{}.bed".format(setName),
                        "dataframe": sub,
                    }
                )
    return groups, featureMap


def writeGmtFile(gmtPath, geneSets):
    with open(gmtPath, "w", encoding="utf-8") as fh:
        for entry in geneSets:
            fh.write("\t".join([entry["set_name"], entry["description"], *entry["genes"]]) + "\n")


def writeManifests(outDir, manifest):
    manifestPath = Path(outDir) / "extraction_manifest.json"
    summaryPath = Path(outDir) / "extraction_manifest.tsv"
    with manifestPath.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    with summaryPath.open("w", encoding="utf-8") as fh:
        fh.write(
            "set_name\tbed_filename\tfeature_original\tfeature_sanitized\tdirection\tn_regions\tn_unique_genes\n"
        )
        for entry in manifest["output_files"]:
            direction = entry.get("direction") if entry.get("direction") is not None else ""
            fh.write(
                "{set_name}\t{bed_filename}\t{feature_original}\t{feature_sanitized}\t{direction}\t{n_regions}\t{n_unique_genes}\n".format(
                    set_name=entry["set_name"],
                    bed_filename=entry["bed_filename"],
                    feature_original=entry["feature_original"],
                    feature_sanitized=entry["feature_sanitized"],
                    direction=direction,
                    n_regions=entry["n_regions"],
                    n_unique_genes=entry["n_unique_genes"],
                )
            )


def extractRegions(args):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    outDir = args.outDir if args.outDir is not None else defaultOutDir(args.infileName)
    Path(outDir).mkdir(parents=True, exist_ok=True)

    df, sheetName = loadInputTable(args.infileName, args.sheetName)
    mode = detectMode(df, args.mode, args.log2FCColumn, args.fdrColumn)
    validateRequiredColumns(
        df,
        args.featureColumn,
        args.geneBodyColumn,
        mode,
        args.log2FCColumn,
        args.fdrColumn,
    )
    df = normalizeCoordinates(df)
    filtered = filterForMode(
        df,
        mode,
        args.log2FCColumn,
        args.fdrColumn,
        args.fdrThreshold,
        args.log2FCThreshold,
    )

    groups, featureMap = buildOutputGroups(filtered, mode, args.featureColumn)
    if len(groups) == 0:
        logger1.warning("No output groups were generated.")

    inputStem = inputBasename(args.infileName)
    gmtPath = Path(outDir) / "{}.byFeature.genesets.gmt".format(inputStem)
    outputFiles = []
    geneSets = []

    for group in groups:
        bedPath = Path(outDir) / group["bed_filename"]
        writeBedFile(bedPath, group["dataframe"])
        genes = collectUniqueGenes(group["dataframe"][args.geneBodyColumn])
        description = (
            "Peaks from {} grouped by {} feature {}".format(
                Path(args.infileName).name,
                mode,
                group["set_name"],
            )
        )
        if mode == "voom":
            description += "; FDR < {}; log2FC threshold {}".format(
                args.fdrThreshold,
                args.log2FCThreshold,
            )
        geneSets.append(
            {
                "set_name": group["set_name"],
                "description": description,
                "genes": genes,
            }
        )
        outputFiles.append(
            {
                "set_name": group["set_name"],
                "bed_file": str(bedPath),
                "bed_filename": group["bed_filename"],
                "feature_original": group["feature_original"],
                "feature_sanitized": group["feature_sanitized"],
                "direction": group["direction"],
                "n_regions": int(len(group["dataframe"])),
                "n_unique_genes": int(len(genes)),
            }
        )
        logger1.info(
            "Wrote {} with {} regions and {} unique genes.".format(
                group["bed_filename"],
                len(group["dataframe"]),
                len(genes),
            )
        )

    writeGmtFile(gmtPath, geneSets)
    logger1.info("Wrote GMT file with {} gene sets: {}".format(len(geneSets), gmtPath))

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python {}".format(" ".join(str(x) for x in sys.argv)),
        "source_file": str(Path(args.infileName).resolve()),
        "source_sheet": sheetName,
        "output_directory": str(Path(outDir).resolve()),
        "mode": mode,
        "filters": {
            "feature_column": args.featureColumn,
            "gene_body_column": args.geneBodyColumn,
            "log2fc_column": args.log2FCColumn,
            "fdr_column": args.fdrColumn,
            "fdr_threshold": args.fdrThreshold,
            "log2fc_threshold": args.log2FCThreshold,
            "direction_rule": "log2FC > threshold => up; log2FC < -threshold => down",
        },
        "input_summary": {
            "total_rows": int(len(df)),
            "rows_after_filtering": int(len(filtered)),
            "feature_types_present": int(df[args.featureColumn].nunique(dropna=True)),
            "output_bed_files": len(outputFiles),
            "output_gene_sets": len(geneSets),
        },
        "feature_name_mapping": featureMap,
        "gmt_file": str(gmtPath),
        "output_files": sorted(outputFiles, key=lambda x: x["bed_filename"]),
    }
    writeManifests(outDir, manifest)
    logger1.info("Manifest written to {}".format(Path(outDir) / "extraction_manifest.json"))
    return manifest


def main():
    args = parseArgs()
    extractRegions(args)
    logging.info("All done, thank you.")


if __name__ == "__main__":
    main()
