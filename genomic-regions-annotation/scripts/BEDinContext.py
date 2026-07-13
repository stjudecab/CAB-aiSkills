#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Wojciech Rosikiewicz && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: BEDinContext.py
# Description:
# Annotate peak/region BED files to ChromHMM or Segway chromatin states.
#########################################################################

"""Annotate genomic regions to ChromHMM / Segway chromatin states.

``-s/--statesFile`` must be a resolved dense or segments BED path. For
precalculated Roadmap/ENCODE models, first run ``prepare_chromatin_model.py``
to download and cache the dense BED, then pass that cached path here.

Example usage::

    python scripts/BEDinContext.py \\
      -r example_input/chromatin/exampleInput.lst \\
      -s cache/E123_hg38_dense.bed \\
      -o BEDinContext \\
      --state2name references/chromatin-states/state2name.tsv \\
      --outputDir agentResults/genomic-regions-annotation-<runId> \\
      --runId <runId>
"""

from __future__ import annotations

import argparse
import inspect
import logging
import os
import sys
from collections import OrderedDict
from pathlib import Path

# Allow ``python scripts/BEDinContext.py`` imports of sibling helpers.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_reproducibility import (
    addReproducibilityArgs,
    appendCommandLog,
    collectBaseToolVersions,
    configureRunLogging,
    runIdUtc,
    timestampIsoUtc,
    writeAgentArtifacts,
    writeRunMetadata,
)
from chromatin_model_utils import aggregationOutputDirectory

if "-h" not in sys.argv and "--help" not in sys.argv:
    from pybedtools import BedTool

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import seaborn as sns
    from natsort import natsort_keygen, natsorted

    def setPlotlyConfigs():
        """Adjust plotly HTML write defaults for SVG download and CDN JS."""
        defPar = list(px._core.pio.write_html.__defaults__)
        defPar[0] = {
            "toImageButtonOptions": {
                "format": "svg",
                "filename": "SJCAB_EPI",
            }
        }
        defPar[2] = "cdn"
        return tuple(defPar)

    px._core.pio.write_html.__defaults__ = setPlotlyConfigs()


def str2bool(v):
    """Parse a boolean-like CLI string.

    Args:
        v (Any): Value to interpret.

    Returns:
        bool: Parsed boolean.
    """
    if str(v).lower() in ("yes", "true", "t", "y", "1"):
        return True
    if str(v).lower() in ("no", "false", "f", "n", "0"):
        return False
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    logger1.error("Unrecognized parameter was set for '%s'. Program was aborted.", v)
    raise SystemExit(1)


def parseArgs():
    """Parse CLI arguments and validate inputs for chromatin-state annotation.

    Returns:
        tuple: regions, statesFile, outputDirectory, mode, state2name,
        state2nameFile, aggregation, args.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Annotate BED regions to chromatin states using a resolved dense/segments "
            "BED file. Prepare Roadmap/ENCODE models with prepare_chromatin_model.py first."
        )
    )
    parser.add_argument(
        "-r",
        "--regions",
        help="[REQUIRED] Comma-separated BED paths or a *.lst file listing BED paths.",
        required=True,
        dest="regions",
    )
    parser.add_argument(
        "-s",
        "--statesFile",
        help=(
            "[REQUIRED] Path to a dense or segments chromatin-state BED file. "
            "Collection codes (E123 / ENCFF*) are no longer resolved here; run "
            "prepare_chromatin_model.py and pass the cached dense BED path."
        ),
        required=True,
        dest="statesFile",
    )
    parser.add_argument(
        "-o",
        "--outputDirectory",
        help="Annotation result subdirectory name or path. Default: BEDinContext.",
        default="BEDinContext",
        dest="outputDirectory",
    )
    parser.add_argument(
        "-c",
        "--colorsList",
        help="Optional *.lst of custom colors (not yet implemented).",
        required=False,
        dest="colorsList",
    )
    parser.add_argument(
        "-m",
        "--mode",
        help="Chromatin BED format: 'segments' or 'dense'. Default: dense.",
        default="dense",
        choices=["segments", "dense"],
        dest="mode",
    )
    parser.add_argument(
        "-a",
        "--aggregation",
        help=(
            "Summary metric: 'regions' (default; primary peak counts at the top of "
            "-o), 'bp' (base-pair sums under <out>/aggregationByBp/), or 'both'."
        ),
        default="regions",
        choices=["regions", "bp", "both"],
        dest="aggregation",
    )
    parser.add_argument(
        "--state2name",
        help=(
            "Tab-separated map of E* state IDs to friendly names. "
            "Use 'auto' to keep numeric E* labels only. Default: auto."
        ),
        default="auto",
        dest="state2name",
    )
    addReproducibilityArgs(parser)
    args = parser.parse_args()

    runId = args.runId or runIdUtc()
    if args.outputDir:
        runDir = Path(args.outputDir).resolve()
    else:
        runDir = Path(args.outputDirectory).resolve().parent
        if str(runDir) in (".", ""):
            runDir = Path.cwd()
    runDir.mkdir(parents=True, exist_ok=True)
    configureRunLogging(runDir, "BEDinContext")
    appendCommandLog(runDir, runId)
    writeAgentArtifacts(
        runDir,
        agentRequest=args.agentRequest,
        agentRequestFile=Path(args.agentRequestFile) if args.agentRequestFile else None,
        agentWorkflow=args.agentWorkflow,
        agentWorkflowFile=Path(args.agentWorkflowFile) if args.agentWorkflowFile else None,
    )
    args.runIdResolved = runId
    args.runDirResolved = runDir

    logging.info("Current working directory: %s", os.getcwd())
    logging.info("Command used to run the program: python %s", " ".join(sys.argv))
    logging.info("Run ID: %s", runId)
    logging.info("Run directory: %s", runDir)

    if args.regions.endswith(".lst"):
        logging.info("Loading in %s file...", args.regions)
        regions = list(pd.read_csv(args.regions, header=None)[0])
    else:
        regions = args.regions.split(",")
    errors = False
    for region in regions:
        if not os.path.isfile(region):
            logging.error(
                "%s file is not accessible. Expected an existing BED path from -r.",
                region,
            )
            errors = True
    if errors:
        msg = (
            "At least one regions BED file (provided by -r) was not accessible. "
            "Program execution was aborted."
        )
        logging.error(msg)
        raise FileNotFoundError(msg)
    logging.info("Regions (-r flag): %s", regions)

    if not os.path.isfile(args.statesFile):
        msg = (
            f"statesFile {args.statesFile!r} was not found. Pass a resolved dense/segments "
            "BED path. For Roadmap/ENCODE collections, run prepare_chromatin_model.py first "
            "and supply the resulting cache/<collection>_<genome>_dense.bed path."
        )
        logging.error(msg)
        raise FileNotFoundError(msg)
    statesFile = args.statesFile
    logging.info("statesFile (-s flag): %s", statesFile)

    resultsDir = Path(args.outputDirectory)
    if not resultsDir.is_absolute():
        resultsDir = runDir / resultsDir
    args.outputDirectory = str(resultsDir)
    logging.info("outputDirectory (-o flag): %s", args.outputDirectory)
    logging.info(
        "colorsList (-c flag): %s >>> not implemented yet.",
        args.colorsList,
    )
    logging.info("Mode (-m flag): %s", args.mode)
    logging.info("Aggregation metric (-a/--aggregation): %s", args.aggregation)

    if args.state2name != "auto":
        if not os.path.isfile(args.state2name):
            msg = (
                f"state2name file was provided via --state2name, but {args.state2name} "
                "is not accessible. Program execution was aborted."
            )
            logging.error(msg)
            raise FileNotFoundError(msg)
        state2nameFile = args.state2name
    else:
        state2nameFile = "auto"
    logging.info("state2name file (--state2name): %s", state2nameFile)

    if state2nameFile != "auto":
        tmp = pd.read_csv(state2nameFile, sep="\t", header=None)
        state2name = pd.Series(tmp[1].values, index=tmp[0]).to_dict()
    else:
        state2name = {}

    return (
        regions,
        statesFile,
        args.outputDirectory,
        args.mode,
        state2name,
        state2nameFile,
        args.aggregation,
        args,
    )
    
def rgb2hex(r,g,b): #https://stackoverflow.com/questions/3380726/converting-a-rgb-color-tuple-to-a-six-digit-code
    return "#{:02x}{:02x}{:02x}".format(r,g,b)

def hex2rgb(hexcode):
    return tuple(map(ord,hexcode[1:].decode('hex')))

def stackedBar(finalStatFile, outfilePrefix, statesPrefix, state2nameFile, state2name, resultsDir="BEDinContext", colors="auto", mode='dense', totalStates=0, infileName_segments="none", valueLabel="Number of regions"):
    """
    Example finalStatFile:
           PHF6_ReproPeaks.bed  H3K14Ac_down.bed
    State                                       
    E1                    5616            6037.0
    E2                    1867            3227.0
    E3                     524               5.0
    E4                     734               0.0
    E5                     656             406.0
    E6                     448               0.0
    E7                    2266             165.0
    E8                    1019               0.0
    E9                    1850               0.0
    E10                    638               0.0
    E11                    870               7.0
    E12                   1672               1.0
    """
    
    statsCombined = pd.read_csv(finalStatFile, sep="\t")#, index="State")
    outName = os.path.join(resultsDir, f"statsCombined.list.tsv")
    
    ### Reformat the data:
    list_stack = []
    percentageLabel = f"Percentage of {valueLabel.replace('Number of ', '')}"
    labels = ['Regions file', 'State', valueLabel, 'Percentage', percentageLabel]
    samples = list(statsCombined)
    samples.remove("State")
    for idx, row in statsCombined.iterrows():
        for bed in samples:
            frc = (row[bed]/np.sum(statsCombined[bed]))*100
            list_stack.append((bed, row["State"], row[bed], "{0} ({1:.2f}%)".format(row[bed], frc), round(frc, 2)))
    df_stack = pd.DataFrame.from_records(list_stack, columns=labels)
    df_stack.to_csv(outName, sep = "\t", index=False)
    
    ### Generate plot:
    if mode == 'dense':
        colors = 'custom'
        colorPatterns = getColorPatterns(infileName_segments, statesPrefix, state2nameFile, state2name)
    
    if colors == "auto":
        cmap = plt.get_cmap('Spectral')
        colors = [matplotlib.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, len(statsCombined))]
    elif colors == 'custom' and mode == 'dense':
        colors = []
        fallback = (0.8, 0.8, 0.8, 1.0)
        for state in range(1, totalStates+1):
            if state2nameFile == "auto":
                stateName = f"{statesPrefix}{state}"
            else:
                stateName = "{}: {}".format(f"{statesPrefix}{state}", state2name[f"{statesPrefix}{state}"])
            # States absent from the dense BED have no observed RGB; use grey.
            rgba = colorPatterns.get(stateName, fallback)
            colors.append(matplotlib.colors.rgb2hex(rgba))
        #colors = [colorPatterns[state] for state in colorPatterns]
    color_discrete_map = dict(zip(statsCombined["State"], colors))
    
    fig=px.bar(df_stack,
                x='Regions file',
                y=percentageLabel,
                color='State',
                barmode = 'relative',
                text=df_stack['Percentage'],
                color_discrete_map=color_discrete_map)

    fig.update_layout(title = f"Distribution of ChromHMM states from file {os.path.basename(infileName_segments)}",
                       template = 'simple_white',
                       xaxis_title = 'Regions input file name',
                       yaxis_title = 'Percentage',
                       height = 600)
    fig.update_yaxes(range=[0,100])
    fig.write_image(f"{resultsDir}/{outfilePrefix}.stackedBar.png", scale=4)
    fig.write_image(f"{resultsDir}/{outfilePrefix}.stackedBar.pdf") #https://plotly.com/python/static-image-export/#vector-formats-svg-and-pdf
    fig.write_html(f"{resultsDir}/{outfilePrefix}.stackedBar.html")
    
    logging.info(f"Saved {outfilePrefix}.stackedBar.[png|pdf|html] files")
    
def pieBarPlot(statDf, outfilePrefix, statesPrefix, state2nameFile, state2name, plotType, resultsDir="BEDinContext", colors="auto", mode='dense', colorPatterns='dense', totalStates=0, valueLabel="Number of regions"):
    """
    Example statDf input:
       state  Number of regions
    0     E1     5616
    1     E2     1867
    2     E3      524
    3     E4      734
    4     E5      656
    5     E6      448
    6     E7     2266
    7     E8     1019
    8     E9     1850
    9    E10      638
    10   E11      870
    11   E12     1672
    """
    
    if mode == 'dense':
        colors = 'custom'
    
    if plotType == "bar" or plotType == "pie":
    
        if colors == "auto":
            cmap = plt.get_cmap('Spectral')
            colors = [cmap(i) for i in np.linspace(0, 1, len(statDf))]
            #print(colors)
        elif colors == 'custom' and mode == 'dense':
            colors = []
            fallback = (0.8, 0.8, 0.8, 1.0)
            for state in range(1, totalStates+1):
                if state2nameFile == "auto":
                    stateName = f"{statesPrefix}{state}"
                else:
                    stateName = "{}: {}".format(f"{statesPrefix}{state}", state2name[f"{statesPrefix}{state}"])
                if stateName in colorPatterns:
                    colors.append(colorPatterns[stateName])
                else:
                    colors.append(fallback)
                # colors.append(colorPatterns[stateName])
            #colors = [colorPatterns[state] for state in colorPatterns]
            
        plt.clf()
        fig, ax = plt.subplots(figsize=(7, 4))
        if plotType == "pie":
            ax = plt.pie(statDf[valueLabel], labels=statDf['State'], autopct='%1.1f%%', shadow=False, colors=colors)
            suffix = "piePlot"
        else:
            ax = sns.barplot(x=statDf[valueLabel], y=statDf['State'], palette=colors)
            suffix = "barPlot"
        plt.title(f"Distribution of ChromHMM states by {valueLabel} for {np.sum(statDf[valueLabel])} total\nRegions ID: {outfilePrefix}")
        plt.savefig(os.path.join(resultsDir, f"{outfilePrefix}.{suffix}.pdf"), bbox_inches='tight', dpi=300)
        plt.savefig(os.path.join(resultsDir, f"{outfilePrefix}.{suffix}.png"), bbox_inches='tight', dpi=300)
        plt.close()
        logging.info(f"{plotType} plot drawn for {outfilePrefix}")
    else:
        logging.error(f"Unsupoported type of plot requested for 'pieBarPlot' dunction for '{outfilePrefix}' data. The requested type was plotType='{plotType}', but should only be 'pie' or 'bar'. No plots generated.")

def hextriplet(colortuple):
    # Solution by MestreLion: https://stackoverflow.com/questions/3380726/converting-an-rgb-color-tuple-to-a-hexidecimal-string
    return '#' + ''.join(f'{i:02X}' for i in colortuple)

def fractriplet(colortuple):
    return (colortuple[0]/255, colortuple[1]/255, colortuple[2]/255, 1)

def getColorPatterns(infileName, statesPrefix, state2nameFile, state2name):
    segments = pd.read_csv(infileName, sep="\t", header=None, skiprows=1)
    segments.columns = ["chrm", "start", "end", "stateTMP", "score", "strand", "start2", "end2", "color"]
    segments["state"] = segments["stateTMP"].apply(lambda x: f"{statesPrefix}{x}" if state2nameFile == "auto" else "{}: {}".format(f"{statesPrefix}{x}", state2name[f"{statesPrefix}{x}"]))
    
    colorPatternsTMP = {}
    for idx, row in segments.iterrows():
        tmp = row["color"].split(",")
        colorPatternsTMP[row['state']] = (int(tmp[0]), int(tmp[1]), int(tmp[2]))
    states = colorPatternsTMP.keys()
    states = natsorted(states)
    colorPatterns = OrderedDict()
    for state in states:
        #colorPatterns[state].append(hextriplet(colortuple[colorPatterns[state][0]]))
        colorPatterns[state] = fractriplet(colorPatternsTMP[state])
    return colorPatterns

def getNumberOfStates(infileName):
    """Return the highest numeric state ID present in a dense/segments BED.

    Dense ChromHMM models label states 1..N. Using ``max`` (not unique count)
    preserves contiguous E1..EN labeling when intermediate states are absent
    from a toy or partial segmentation file.

    Args:
        infileName (str): Path to dense/segments BED (track header skipped).

    Returns:
        int: Maximum numeric state ID.
    """
    segments = pd.read_csv(
        infileName, sep="\t", header=None, skiprows=1, usecols=[0, 1, 2, 3]
    )
    values = []
    for raw in segments[3]:
        text = str(raw).strip()
        if "_" in text:
            text = text.split("_", 1)[0]
        if text.upper().startswith("E") and text[1:].isdigit():
            values.append(int(text[1:]))
        else:
            values.append(int(text))
    if not values:
        raise ValueError(f"No state IDs found in {infileName}")
    return max(values)

def makeStatDf(segDf, totalStates, statesPrefix, state2nameFile, state2name, aggregation="regions"):
    if aggregation == "regions":
        statDf = segDf["state"].value_counts().to_frame().reset_index()
        statDf.sort_values(by=["state"], inplace=True, ascending=True, key=natsort_keygen())
        statDf.reset_index(drop=True, inplace=True)
        statDf.columns = ["State", "Number of regions"]
        valueLabel = "Number of regions"
    elif aggregation == "bp":
        statDf = segDf.groupby("state", as_index=False)["overlap"].sum()
        statDf.sort_values(by=["state"], inplace=True, ascending=True, key=natsort_keygen())
        statDf.reset_index(drop=True, inplace=True)
        statDf.columns = ["State", "Number of bp"]
        valueLabel = "Number of bp"
    else:
        msg = f"Unsupported aggregation='{aggregation}'. Expected 'regions' or 'bp'."
        logging.error(msg)
        raise Exception(msg)

    if len(statDf) < totalStates:
        # means that some states are missing and their values should be set to 0
        if state2nameFile == "auto":
            refStates = [f"{statesPrefix}{x}" for x in range(1, totalStates+1)]
        else:
            refStates = ["{}: {}".format(f"{statesPrefix}{x}", state2name[f"{statesPrefix}{x}"]) for x in range(1, totalStates+1)]

        missingStates = set(refStates).difference(set(statDf["State"]))
        for state in missingStates:
            statDf.loc[len(statDf.index)] = [state, 0]
        statDf.sort_values(by=["State"], inplace=True, ascending=True, key=natsort_keygen())
        statDf.reset_index(drop=True, inplace=True)

    return statDf, valueLabel


def bed2context(
    infileName_bedOfInterest,
    infileName_segments,
    segments,
    mode,
    totalStates,
    statesPrefix,
    state2nameFile,
    state2name,
    resultsDir="BEDinContext",
    aggregation="regions",
    bed2statesDir=None,
):
    """Annotate one peak BED to chromatin states and write summary plots.

    Args:
        infileName_bedOfInterest: Path to input peak/region BED.
        infileName_segments: Path to dense/segments chromatin BED.
        segments: pybedtools BedTool of states.
        mode: ``dense`` or ``segments``.
        totalStates: Maximum numeric state ID.
        statesPrefix: State ID prefix (``E`` for dense).
        state2nameFile: Path or ``auto``.
        state2name: Mapping of E* IDs to friendly names.
        resultsDir: Directory for this aggregation's tables/plots.
        aggregation: ``regions`` or ``bp``.
        bed2statesDir: If set, write the per-peak best-state BED here (typically
            the top-level results directory). Omit for the secondary bp pass when
            ``regions`` already wrote it.

    Returns:
        pandas.DataFrame: Per-state counts indexed for combining across files.
    """
    bedOfInterest = pd.read_csv(infileName_bedOfInterest, sep="\t", header=None, usecols = [0, 1, 2]) # effectively remove columns other than chromosome, start, end
    bedOfInterest = BedTool.from_dataframe(bedOfInterest)

    colorPatterns = mode
    if mode == "dense":
        colorPatterns = getColorPatterns(infileName_segments, statesPrefix, state2nameFile, state2name)

    segmentation = bedOfInterest.intersect(segments, wo=True)

    segDf = pd.read_table(segmentation.fn, header=None)
    ### Example output of the segmentation at this stage:
    #           0         1         2     3         4         5    6    7
    # 0      chr1    762473    763317  chr1    762200    763400   E1  844
    # 1      chr1    804998    805822  chr1    804600    805000   E6    2
    # 2      chr1    804998    805822  chr1    805000    805800   E7  800
    # 3      chr1    804998    805822  chr1    805800    809600   E4   22
    # 4      chr1    839213    841107  chr1    839000    840000   E2  787

    segDf = segDf[[0, 1, 2] + list(segDf)[-2:]]
    segDf.columns = ["chrm", "start", "end", "state", "overlap"]

    # BED annotation file remains one line per input interval, assigned to the state
    # with the largest bp overlap. The bp summary below uses the full unsquashed
    # segDf and sums all state-specific overlaps.
    segDfBest = segDf.sort_values(by=["overlap"], ascending=False).copy()
    segDfBest.drop_duplicates(subset = ["chrm", "start", "end"], keep = 'first', inplace=True)
    segDfBest.sort_values(by=["chrm", "start", "end"], ascending=True, inplace=True, key=natsort_keygen())
    segDfBest.drop(columns=["overlap"], inplace=True)
    if bed2statesDir is not None:
        Path(bed2statesDir).mkdir(parents=True, exist_ok=True)
        segDfBest.to_csv(
            os.path.join(
                bed2statesDir,
                f"{(os.path.basename(infileName_bedOfInterest)).replace('.bed','').replace('.narrowPeak','').replace('.narrowpeak','')}.bed2states.bed",
            ),
            sep="\t",
            header=False,
            index=False,
        )

    Path(resultsDir).mkdir(parents=True, exist_ok=True)
    statSourceDf = segDfBest if aggregation == "regions" else segDf
    statDf, valueLabel = makeStatDf(statSourceDf, totalStates, statesPrefix, state2nameFile, state2name, aggregation=aggregation)
    outfilePrefix = (os.path.basename(infileName_bedOfInterest)).replace('.bed','').replace('.narrowPeak','').replace('.narrowpeak','')

    # generate plots:
    pieBarPlot(statDf, outfilePrefix, statesPrefix, state2nameFile, state2name, plotType="pie", resultsDir=resultsDir, mode=mode, colorPatterns=colorPatterns, totalStates=totalStates, valueLabel=valueLabel)
    pieBarPlot(statDf, outfilePrefix, statesPrefix, state2nameFile, state2name, plotType="bar", resultsDir=resultsDir, mode=mode, colorPatterns=colorPatterns, totalStates=totalStates, valueLabel=valueLabel)

    statDf.columns = ["State", os.path.basename(infileName_bedOfInterest)]
    statDf.set_index("State", inplace=True)
    logging.info(f"processed {infileName_bedOfInterest} using aggregation={aggregation} -> {resultsDir}")
    return statDf


def main() -> int:
    """Run chromatin-state annotation and persist run metadata.

    Returns:
        int: Process exit code.
    """
    try:
        from skill_env import bootstrap

        bootstrap()
    except Exception:
        pass

    (
        bedsOfInterest,
        infileName_segments,
        resultsDir,
        mode,
        state2name,
        state2nameFile,
        aggregation,
        args,
    ) = parseArgs()

    if mode == "segments":
        statesPrefix = ""
    elif mode == "dense":
        statesPrefix = "E"
    else:
        raise ValueError(f"Unsupported mode={mode!r}")

    totalStates = getNumberOfStates(infileName_segments)
    # Skip the track header row present in dense ChromHMM browser files.
    segments = pd.read_csv(
        infileName_segments,
        sep="\t",
        header=None,
        usecols=[0, 1, 2, 3],
        skiprows=1,
    )
    segments["state"] = segments[3].apply(
        lambda x: f"{statesPrefix}{x}"
        if state2name == {}
        else "{}: {}".format(f"{statesPrefix}{x}", state2name[f"{statesPrefix}{x}"])
    )
    segments.drop(columns=[3], inplace=True)
    segments = BedTool.from_dataframe(segments)

    logging.info("Found a total of %s reference chromatin states.", totalStates)

    Path(resultsDir).mkdir(parents=True, exist_ok=True)
    outputFiles: list[str] = []

    aggregationsToRun = ["regions", "bp"] if aggregation == "both" else [aggregation]
    for aggregationMetric in aggregationsToRun:
        metricOutDir = aggregationOutputDirectory(resultsDir, aggregationMetric)
        Path(metricOutDir).mkdir(parents=True, exist_ok=True)
        # Per-peak assignment BED is a primary artifact at the top level.
        writeBed2States = aggregationMetric == "regions" or aggregation == "bp"
        bed2statesDir = resultsDir if writeBed2States else None

        stats = []
        for infileName_bedOfInterest in bedsOfInterest:
            stats.append(
                bed2context(
                    infileName_bedOfInterest,
                    infileName_segments,
                    segments,
                    mode,
                    totalStates,
                    statesPrefix,
                    state2nameFile,
                    state2name,
                    metricOutDir,
                    aggregation=aggregationMetric,
                    bed2statesDir=bed2statesDir,
                )
            )

        valueLabel = "Number of regions" if aggregationMetric == "regions" else "Number of bp"
        statsCombinedFileNum = os.path.join(metricOutDir, "statsCombined.num.tsv")
        if len(stats) > 1:
            statsCombined = stats[0].join(stats[1:])
            statsCombined.fillna(0, inplace=True)
        else:
            statsCombined = stats[0]
        statsCombined.to_csv(statsCombinedFileNum, sep="\t")
        logging.info("generated final stats file %s", statsCombinedFileNum)
        outputFiles.append(statsCombinedFileNum)

        statsCombinedFileFrc = os.path.join(metricOutDir, "statsCombined.frc.tsv")
        statsCombinedFrc = statsCombined.copy()
        for column in list(statsCombinedFrc):
            s = np.sum(statsCombinedFrc[column])
            statsCombinedFrc[column] = statsCombinedFrc[column].apply(
                lambda x: x / s if s != 0 else 0
            )
        statsCombinedFrc.to_csv(statsCombinedFileFrc, sep="\t")
        logging.info("generated final stats file %s", statsCombinedFileFrc)
        outputFiles.append(statsCombinedFileFrc)

        stackedBar(
            statsCombinedFileNum,
            "statsCombined",
            statesPrefix,
            state2nameFile,
            state2name,
            resultsDir=metricOutDir,
            totalStates=totalStates,
            mode=mode,
            infileName_segments=infileName_segments,
            valueLabel=valueLabel,
        )
        for ext in (".stackedBar.png", ".stackedBar.pdf", ".stackedBar.html", ".list.tsv"):
            # stackedBar writes statsCombined.list.tsv and stackedBar figures
            if ext == ".list.tsv":
                candidate = os.path.join(metricOutDir, "statsCombined.list.tsv")
            else:
                candidate = os.path.join(metricOutDir, f"statsCombined{ext}")
            if os.path.isfile(candidate):
                outputFiles.append(candidate)

    runDir = args.runDirResolved
    writeRunMetadata(
        runDir / "run_metadata.json",
        {
            "skill": "genomic-regions-annotation",
            "script": "BEDinContext.py",
            "run_id": args.runIdResolved,
            "timestamp_utc": timestampIsoUtc(),
            "command": " ".join(sys.argv),
            "working_directory": Path.cwd().as_posix(),
            "inputs": {
                "regions": [str(Path(p).resolve()) for p in bedsOfInterest],
                "statesFile": str(Path(infileName_segments).resolve()),
                "state2name": state2nameFile,
            },
            "output_directory": runDir.as_posix(),
            "parameters": {
                "mode": mode,
                "aggregation": aggregation,
                "outputDirectory": resultsDir,
            },
            "tool_versions": collectBaseToolVersions(Path(__file__)),
            "summary": {
                "n_region_files": len(bedsOfInterest),
                "n_states": totalStates,
            },
            "outputs": [str(Path(p).resolve()) for p in outputFiles if Path(p).is_file()],
            "logs": {
                "BEDinContext.log": (runDir / "logs" / "BEDinContext.log").as_posix(),
                "commands.log": (runDir / "logs" / "commands.log").as_posix(),
            },
            "attribution": {
                "method": "Chromatin-state overlap annotation (largest bp overlap)",
                "skill_package": "genomic-regions-annotation",
                "note": (
                    "Do not run OrganizeAnnotationResults.py after chromatin-state "
                    "annotation; this branch is independent of gene/feature annotation."
                ),
            },
        },
    )
    logging.info("Wrote run metadata: %s", runDir / "run_metadata.json")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logging.error("%s", exc)
        raise SystemExit(1)

