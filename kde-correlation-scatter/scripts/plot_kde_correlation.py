import pandas as pd
# import sys
import glob, os
from sys import argv
import numpy as np
from scipy import stats

import argparse

import logging
import inspect

from functools import reduce

import seaborn as sns
import matplotlib.pyplot as plt
from pylab import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import matplotlib.patheffects as path_effects

from pybedtools import BedTool

def configureLogging(analysisPrefix):
    logging.basicConfig(level = logging.INFO,
                        format = '###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s',
                        handlers = [logging.FileHandler('{}.log'.format(analysisPrefix)), logging.StreamHandler()],
                        datefmt='%y-%m-%d %H:%M:%S')

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def label_point(x, y, val, ax):
    a = pd.concat({'x': x, 'y': y, 'val': val}, axis=1)
    for i, point in a.iterrows():
        text = ax.text(point['x']+.1, point['y'], str(point['val']), fontsize=20, color='red')
#         text = fig.text(0.5, 0.5, 'This text stands out because of\n'
#                           'its black border.', color='white',
#                           ha='center', va='center', size=30)
        text.set_path_effects([path_effects.Stroke(linewidth=2, foreground='white'),
                                  path_effects.Normal()])

def paramsParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-ix", "--infileName_X", help="Name of the input matrix for plotting, which will be plotted on X axis. Usuially this will be the output file from Differential Analysis, e.g. *.vout.anno file type, but any tab-separated file would be OK as long as it has some metric to plot", action="store", type=str, required=True, dest="infileName_X")
    parser.add_argument("-mx", "--metricColumn_X", help="Name of the column containing X axis metric, e.g. log2FC.", default="log2FC", action="store", type=str, required=False, dest="metricColumn_X")
    parser.add_argument("-sx", "--significanceColumn_X", help="Name of the column containing statistical, e.g. q.value, FDR, P.Value etc. This will only be used if 'dirTransform' (-dt flag) will be set to True.", default="FDR", action="store", type=str, required=False, dest="significanceColumn_X")
    parser.add_argument("-gx", "--geneColumn_X", help="Name of the column containing X axis gene or region names, e.g. geneSymbol (for STD RNA-seq) or Gene_2kb (for comma separated peak annotation in STD ChIP-seq).", default="geneSymbol", action="store", type=str, required=False, dest="geneColumn_X")
    parser.add_argument("-lx", "--label_X", help="The X axis label to be displayed on the final plot. By default = 'auto', which will infer the x-axis from metricColumn_X and infileName_X.", default="auto", action="store", type=str, required=False, dest="label_X")
    parser.add_argument("-rx", "--reverse_X", help="Should the direction of the change (metric) be reversed? i.e. multipled by -1. By default = 'False'.", default=False, action="store", type=str2bool, required=False, dest="reverse_X")
    parser.add_argument("-mtx", "--many2oneTransformation_X", help="In case of the peak annotation, something like 'Gene_2kb' might be specified as an input for gene names (-gx flag); in such case, gene names are comma-separated in that field, and needs to be stripped out in order to match them with the second file by gene name for example. Set this to 'True' in order to do this. Please note, that this script currently supports only values from X axis to be of this type, for when ChIP/ATAC-seq is contrasted with RNA-seq. In case if both datasets are RNA-seq, set this value to 'False', and point the geneName_X to gene name column. In case of two ChIP-seq datasets, point the geneName_X variable to 'Region'/'Peak' column, but remember that currently in such case the script looks for string match, NOT BED-regions overlap., By default = 'False'.", default=False, action="store", type=str2bool, required=False, dest="many2oneTransformation_X")

    parser.add_argument("-iy", "--infileName_Y", help="Name of the input matrix for plotting, which will be plotted on Y axis. Usually this will be the output file from Differential Analysis, e.g. *.vout.anno file type, but any tab-separated file would be OK as long as it has some metric to plot", action="store", type=str, required=True, dest="infileName_Y")
    parser.add_argument("-my", "--metricColumn_Y", help="Name of the column containing Y axis metric, e.g. log2FC.", default="log2FC", action="store", type=str, required=False, dest="metricColumn_Y")
    parser.add_argument("-sy", "--significanceColumn_Y", help="Name of the column containing statistical, e.g. q.value, FDR, P.Value etc. This will only be used if 'dirTransform' (-dt flag) will be set to True.", default="FDR", action="store", type=str, required=False, dest="significanceColumn_Y")
    parser.add_argument("-gy", "--geneColumn_Y", help="Name of the column containing Y axis gene or region names, e.g. geneSymbol (for STD RNA-seq).", default="geneSymbol", action="store", type=str, required=False, dest="geneColumn_Y")
    parser.add_argument("-ly", "--label_Y", help="The Y axis label to be displayed on the final plot. By default = 'auto', which will infer the y-axis from metricColumn_Y and infileName_Y.", default="auto", action="store", type=str, required=False, dest="label_Y")
    parser.add_argument("-ry", "--reverse_Y", help="Should the direction of the change (metric) be reversed? i.e. multipled by -1. By default = 'False'.", default=False, action="store", type=str2bool, required=False, dest="reverse_Y")

    parser.add_argument("-dt", "--dirTransform", help="Should the values from significance and metric be transformed into 'Direction * -log10(significance)' values?. If 'False', the script will not require -sx and -sy values to be set. By default = 'False'.", default=False, action="store", type=str2bool, required=False, dest="dirTransform")
    parser.add_argument("-res", "--BGres", help="KDE resolution. By default = '300j'.", default=300j, action="store", type=complex, required=False, dest="BGres")
    parser.add_argument("-t", "--FCcut", help="Fold-change threshold. Note that this will be subjected to linear or log transformation dependently on the setting of 'scaleType'. By default = '2'.", default=2, action="store", type=float, required=False, dest="FCcut")
    parser.add_argument("-scale", "--scaleType", help="Type of the scale on X and Y axes. By default = 'log2'.", default='log2', action="store", type=str, required=False, dest="scaleType", choices=['linear', 'log2', 'log10'])
    parser.add_argument("-size", "--figSize", help="Comma separated figure size: 'width,height'. By default = '10,10'.", default='10,10', action="store", type=str, required=False, dest="figSize")
    parser.add_argument("-corr", "--corrType", help="Type of correlation. By default = 'PS' which will calclate both Pearson's and Spearman's correlation.", default='PS', action="store", type=str, required=False, dest="corrType", choices=['PS', 'pearsonr', 'spearmanr'])
    parser.add_argument("-p", "--analysisPrefix", help="Prefix of the output file. Specify the prefix for the analysis. By default = 'plot_KDE_correlation'.", default="plot_KDE_correlation", action="store", type=str, required=False, dest="analysisPrefix")

    parser.add_argument("-qd", "--quadrantDescription", help="Description of the points in the Quadrant section. By default = 'genes', so as a result e.g. N1=1234 genes will be displayed. If you used ATAC/ChIP-seq data, change this value for example to 'peaks'.", default="genes", action="store", type=str, required=False, dest="quadrantDescription")
    parser.add_argument("--plotPlain", help="Use this flag to plot also plain version of the figure, in which there is no KDE background, and scatter points are larger and black (which is good for publication ready figures)", action="store_true", default=False, required=False, dest="plotPlain")
    parser.add_argument("--plotNoKDE", help="Very similar to --plotPlain, with the difference being that simply the KDE background is NOT plotted if this flag is used, but the scatter dot size and other settings basically stay the same. This is better option when there are many datapoints displayed (e.g. more than few hundeds).", action="store_true", default=False, required=False, dest="plotNoKDE")
    parser.add_argument("--plotBgKDE", help="When this is set to False, the dots will be plotted in color instead of the background being colored. This mimics the very popular type of plot used in molecular biology to show the composition of markers presence across cells. This is also good for publications and printing. If this is set to True, the datapoints and labels are white, while the background color is colored via the Kernel density. This option is good for presentations. By default=False.", default=False, action="store", type=str2bool, required=False, dest="plotBgKDE")

    parser.add_argument(
        "--comparisonMode",
        help=(
            "How datapoints are matched between X and Y.\n"
            "  - 'anno2anno' (default): string-based join on gene/annotation names "
            "given by --geneColumn_X/--geneColumn_Y.\n"
            "  - 'region2region': treat --geneColumn_X/--geneColumn_Y as genomic "
            "coordinates in '<chrom>:<start>-<end>' and use pybedtools intersection to pair overlapping regions.\n"
            "  - 'rank2rank': read both inputs as RNK (two-column) files where the first column is an "
            "identifier (gene ID or region '<chrom>:<start>-<end>') and the second column is a numeric score. "
            "In this mode, flags such as -sx, -mx, -sy, -my, -dt, -scale, -gx, -gy are ignored. "
            "If both RNK identifiers are genomic regions, they will be paired by pybedtools intersection "
            "(many-to-many supported). Otherwise, identifiers are paired by exact string match."
        ),
        default="anno2anno",
        choices=["anno2anno", "region2region", "rank2rank"],
        action="store",
        type=str,
        required=False,
        dest="comparisonMode"
    )

    parser.add_argument(
        "--markGenes",
        help=("List of items to mark on the plain scatter. In 'anno2anno' mode, "
              "this should be a text file with one identifier per line matching "
              "the X-side identifiers (e.g., gene symbols). In 'region2region' "
              "mode, this should be a BED-like file (at least 3 columns: chrom, "
              "start, end). The regions will be intersected with BOTH X and Y "
              "inputs and a point is marked if it overlaps with at least one side. "
              "Note, the matching items will be marked irrespectively if they meet "
              "the thresholds or not. Default: '' (disabled)."),
        default="",
        action="store",
        type=str,
        required=False,
        dest="markGenes"
    )

#     parser.add_argument("-c", "--cmap", help="Pythons CMap. Availible options at https://matplotlib.org/3.3.2/tutorials/colors/colormaps.html. By default = 'RdBu_r'.", default="RdBu_r", action="store", type=str, required=False, dest="cmap")

    args = parser.parse_args()
    
    configureLogging(args.analysisPrefix)
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    logger1.info("Command used to run the program: python {}".format(' '.join(str(x) for x in argv)))
    logger1.info("Current working directory: {}".format(os.getcwd()))
    logger1.info("Name of the X-axis input matrix (-ix flag): {}".format(args.infileName_X))
    logger1.info("Name of the X-axis metric column (-mx flag): {}".format(args.metricColumn_X))
    logger1.info("Name of the X-axis gene name column (-gx flag): {}".format(args.geneColumn_X))
    if args.label_X == "auto":
        label_X = "{} ({})".format(os.path.basename(args.infileName_X), args.metricColumn_X)
    else:
        label_X = args.label_X
    logger1.info("Name of the X-axis label (-lx flag): {}".format(label_X))
    logger1.info("Should the X-axis be reversed (-rx flag): {}".format(args.reverse_X))
    logger1.info("Many-2-one transformation of X-axis gene names (-mtx flag): {}".format(args.many2oneTransformation_X))
    
    logger1.info("Name of the Y-axis input matrix (-iy flag): {}".format(args.infileName_Y))
    logger1.info("Name of the Y-axis metric column (-my flag): {}".format(args.metricColumn_Y))
    logger1.info("Name of the Y-axis gene name column (-gy flag): {}".format(args.geneColumn_Y))
    if args.label_Y == "auto":
        label_Y = "{} ({})".format(os.path.basename(args.infileName_Y), args.metricColumn_Y)
    else:
        label_Y = args.label_Y
    logger1.info("Name of the Y-axis label (-ly flag): {}".format(label_Y))
    logger1.info("Should the y-axis be reversed (-ry flag): {}".format(args.reverse_Y))
    
    logger1.info("KDE resolution (-res flag): {}".format(args.BGres))
    scaleType = args.scaleType
    logger1.info("Type of the scale on X and Y axes (-scale flag): {}".format(args.scaleType))
    if args.dirTransform == True:
        logger1.info("Directional transformation mode (-dt flag): {}; significanceColumn_X and significanceColumn_Y values will be used.".format(args.dirTransform))
        logger1.info("significanceColumn_X (-sx flag): {}".format(args.significanceColumn_X))
        logger1.info("significanceColumn_Y (-sy flag): {}".format(args.significanceColumn_Y))
        logger1.info("Overwriting ScaleType (-scale scale flag value) to log10")
        scaleType = "log10"
    if args.FCcut == 0:
        FCcut = 0
    else:
        if scaleType == "linear":
            FCcut = args.FCcut
        elif scaleType == "log2":
            FCcut = abs(np.log2(args.FCcut))
        else:
            FCcut = abs(np.log10(args.FCcut))
    logger1.info("Fold-change threshold (-t flag): {}; converted to {}".format(args.FCcut, FCcut))
    figSize = [int(args.figSize.split(",")[0]), int(args.figSize.split(",")[1])]
    logger1.info("Figure size (-size flag): {}".format(figSize))
    logger1.info("Correlation type (-corr flag): {}".format(args.corrType))
    logger1.info("Analysis prefix (-p flag): {}".format(args.analysisPrefix))
    
    
    logger1.info("Quadrant description (-qd flag): {}".format(args.quadrantDescription))
    logger1.info("Plot Plain scatter (--plotPlain flag): {}".format(args.plotPlain))
    logger1.info("No KDE background plotting (--plotNoKDE flag): {}".format(args.plotNoKDE))
    logger1.info("Plot background KDE (--plotBgKDE flag): {}".format(args.plotBgKDE))
    logger1.info("Comparison mode (--comparisonMode): {}".format(args.comparisonMode))
    
    if args.markGenes != "":
        if args.comparisonMode == "anno2anno":
            markGenes = list(set(pd.read_csv(args.markGenes, header=None)[0]))
            logger1.info("Mark items (anno2anno mode; inferred based on --markGenes flag file): {} ==> {}".format(args.markGenes, markGenes))
        else:
            # region2region: store path; parsing occurs later (needs coordinates)
            markGenes = {"bedPath": args.markGenes}
            logger1.info("Mark regions (region2region mode): using BED from {}".format(args.markGenes))
    else:
        markGenes = []
        logger1.info("Mark items (inferred based on --markGenes flag): None")

        # rank2rank mode adjustments
    if args.comparisonMode == "rank2rank":
        # Validate .rnk suffix
        if not str(args.infileName_X).lower().endswith(".rnk") or not str(args.infileName_Y).lower().endswith(".rnk"):
            raise ValueError("In rank2rank mode both -ix and -iy must point to files with the '.rnk' suffix.")

        # Informative logging about ignored flags
        logger1.info("rank2rank mode active: ignoring flags -sx, -mx, -sy, -my, -dt, -scale, -gx, -gy, -mtx.")
        logger1.info("Only aesthetics (labels, reverse flags), thresholds (-t), sizes, and marking will be used.")

        # Override scale handling and directional transform for thresholding
        scaleType = "linear"
        logger1.info("Overriding scaleType to 'linear' for rank2rank; thresholds (-t) treated in linear metric space.")
        # dirTransform is meaningless here
        if args.dirTransform:
            logger1.info("Overriding --dirTransform to False in rank2rank mode.")
        args.dirTransform = False

        # Auto labels for rank2rank if 'auto'
        if args.label_X == "auto":
            label_X = "{} (score)".format(os.path.basename(args.infileName_X))
        if args.label_Y == "auto":
            label_Y = "{} (score)".format(os.path.basename(args.infileName_Y))

        # Recompute FCcut with linear semantics
        if args.FCcut == 0:
            FCcut = 0
        else:
            FCcut = args.FCcut
        logger1.info("Fold-change threshold (-t flag) in rank2rank: {}; used as {}".format(args.FCcut, FCcut))


    if args.geneColumn_X == "Region" and args.geneColumn_Y == "Region" and args.comparisonMode == "anno2anno":
        logger1.warn(" >>>>>>>>> PLEASE READ <<<<<<<<< Most likely you wanted to compare two ChIP-seq / Cut-and-Run / ATAC-seq experiments, but you forgot to set the --comparisonMode flag to 'region2region', which would have used bedtools to intersect the regions for their pairing. Instead now it will treat the regions 'literally' as string-to-string comparison. If that is what you intended, great, good luck and have a nice rest of the day; BUT! in most applications it might not work as expected and its recommended to compare string regions in format `<chrom>:<start>-<end>` by using the `region2region` mode.")

    return args.infileName_X, args.metricColumn_X, args.geneColumn_X, label_X, args.reverse_X, args.many2oneTransformation_X, args.infileName_Y, args.metricColumn_Y, args.geneColumn_Y, label_Y, args.reverse_Y, args.BGres, FCcut, scaleType, figSize, args.corrType, args.analysisPrefix, args.dirTransform, args.significanceColumn_X, args.significanceColumn_Y, args.plotPlain, args.plotNoKDE, args.plotBgKDE, args.quadrantDescription, args.comparisonMode, markGenes

def _parse_region_string(s):
    """
    Parse '<chrom>:<start>-<end>' into (chrom, start, end) with ints for start/end.
    Return None if parsing fails.
    """
    if not isinstance(s, str) or ":" not in s or "-" not in s:
        return None
    try:
        chrom = s.split(":")[0]
        se = s.split(":")[1]
        start = int(se.split("-")[0])
        end = int(se.split("-")[1])
        # enforce start <= end
        if start > end:
            start, end = end, start
        return (chrom, start, end)
    except Exception:
        return None


def _df_to_bedtool_from_idcol(df, id_col, name_col="name"):
    """
    Given df with an identifier column containing '<chrom>:<start>-<end>',
    return (BedTool, parsed_df) where parsed_df has columns:
    ['chrom','start','end', name_col]
    Rows that fail to parse are dropped.
    """
    rows = []
    for _, r in df.iterrows():
        rid = r[id_col]
        parsed = _parse_region_string(rid)
        if parsed is not None:
            chrom, start, end = parsed
            rows.append((chrom, start, end, rid))
    if not rows:
        return None, pd.DataFrame(columns=["chrom", "start", "end", name_col])
    parsed_df = pd.DataFrame(rows, columns=["chrom", "start", "end", name_col])
    bt = BedTool.from_dataframe(parsed_df.rename(columns={name_col: "name"}))
    return bt, parsed_df


def _intersect_region_tables(data_X, data_Y, geneColumn_X, geneColumn_Y, metricColumn_X, metricColumn_Y):
    """
    Build df_final via region intersection (many-to-many OK).
    Output columns:
      - geneColumn_X (X id string)
      - metricColumn_X
      - metricColumn_Y
      - UniqueEntryIdentifier_Y  (Y id string for optional marking)
    """
    # Build BedTools
    btX, dfXreg = _df_to_bedtool_from_idcol(data_X, geneColumn_X, name_col="nameX")
    btY, dfYreg = _df_to_bedtool_from_idcol(data_Y, geneColumn_Y, name_col="nameY")
    if btX is None or btY is None:
        return pd.DataFrame(columns=[geneColumn_X, metricColumn_X, metricColumn_Y, "UniqueEntryIdentifier_Y"])

    # Map id -> metric
    x_metric_map = dict(zip(data_X[geneColumn_X], data_X[metricColumn_X]))
    y_metric_map = dict(zip(data_Y[geneColumn_Y], data_Y[metricColumn_Y]))

    # Intersect X vs Y; keep both sides (-wa -wb)
    inter = btX.intersect(btY, wa=True, wb=True)

    # pybedtools returns columns: X.chrom, X.start, X.end, X.name, Y.chrom, Y.start, Y.end, Y.name
    x_ids = []
    y_ids = []
    for f in inter:
        x_ids.append(f.name)      # X name
        y_ids.append(f.fields[7]) # Y name (8th column)

    if not x_ids:
        return pd.DataFrame(columns=[geneColumn_X, metricColumn_X, metricColumn_Y, "UniqueEntryIdentifier_Y"])

    df_pairs = pd.DataFrame({"X_id": x_ids, "Y_id": y_ids})
    # Attach metrics; drop missing
    df_pairs[metricColumn_X] = df_pairs["X_id"].map(x_metric_map)
    df_pairs[metricColumn_Y] = df_pairs["Y_id"].map(y_metric_map)
    df_pairs = df_pairs.dropna(subset=[metricColumn_X, metricColumn_Y])

    # Rename to expected columns
    df_final = pd.DataFrame({
        geneColumn_X: df_pairs["X_id"].values,
        metricColumn_X: df_pairs[metricColumn_X].values,
        metricColumn_Y: df_pairs[metricColumn_Y].values,
        "UniqueEntryIdentifier_Y": df_pairs["Y_id"].values
    })

    return df_final

def _read_rnk_file(path):
    """
    Load a RNK file (two columns: id, score). Accepts tab or whitespace.
    Handles optional header. Returns a DataFrame with columns ['id','score'].
    """
    # Try without header
    try:
        df = pd.read_csv(path, sep=r"\s+|\t", engine="python", header=None)
    except Exception as e:
        raise ValueError(f"Failed to read RNK file {path}: {e}")

    if df.shape[1] < 2:
        raise ValueError(f"RNK file {path} must have at least two columns")

    # Heuristics: if first row, second column is not numeric, assume header present
    def _is_number(x):
        try:
            float(x)
            return True
        except Exception:
            return False

    if not _is_number(df.iloc[0, 1]):
        # Re-read with header
        df = pd.read_csv(path, sep=r"\s+|\t", engine="python", header=0)
        if df.shape[1] < 2:
            raise ValueError(f"RNK file {path} must have at least two columns")
        # Take first two columns
        df = df.iloc[:, :2]

    else:
        df = df.iloc[:, :2]

    df = df.rename(columns={df.columns[0]: "id", df.columns[1]: "score"})
    # Coerce score to float
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df = df.dropna(subset=["id", "score"]).reset_index(drop=True)
    return df


def _all_region_ids(series_like):
    """
    Return True if all non-null ids in series_like are region strings '<chrom>:<start>-<end>'
    and parse cleanly; otherwise False.
    """
    if series_like is None:
        return False
    any_rows = False
    for s in series_like:
        if pd.isna(s):
            continue
        any_rows = True
        if _parse_region_string(s) is None:
            return False
    return any_rows


def _prepare_rank_df(path, side_label):
    """
    Read RNK and convert to the internal form expected by the rest of the pipeline:
      columns -> ['UniqueEntryIdentifier', f'{side_label}_metric']
    """
    df = _read_rnk_file(path)
    df = df.rename(columns={"id": "UniqueEntryIdentifier", "score": f"{side_label}_metric"})
    df = df[["UniqueEntryIdentifier", f"{side_label}_metric"]]
    return df


def convertSignificance(pVal, log2FC, minSignificance = 1e-10):
    if pVal <= minSignificance:
        pVal = minSignificance
    if log2FC < 0:
        direction = -1
    else:
        direction = 1
    return direction * -np.log10(pVal)

def plot_KDE_correlation(infileName_X, metricColumn_X, geneColumn_X, label_X, reverse_X, many2oneTransformation_X, infileName_Y, metricColumn_Y, geneColumn_Y, label_Y, reverse_Y, BGres, FCcut, scaleType, figSize, corrType, analysisPrefix, dirTransform, significanceColumn_X, significanceColumn_Y, quadrantDescription, plotNoKDE, plotBgKDE, comparisonMode):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    
    if comparisonMode == "rank2rank":
        logger1.info("Loading RNK inputs for X and Y (rank2rank mode).")
        data_X = _prepare_rank_df(infileName_X, side_label=f"{scaleType}_metric_X".replace("linear_", ""))  # name consistency
        data_Y = _prepare_rank_df(infileName_Y, side_label=f"{scaleType}_metric_Y".replace("linear_", ""))

        # Ensure column names exactly match downstream expectations
        # Rename to ['UniqueEntryIdentifier', f'{scaleType}_metric_X'] etc.
        if f"{scaleType}_metric_X" not in data_X.columns:
            data_X = data_X.rename(columns={data_X.columns[1]: f"{scaleType}_metric_X"})
        if f"{scaleType}_metric_Y" not in data_Y.columns:
            data_Y = data_Y.rename(columns={data_Y.columns[1]: f"{scaleType}_metric_Y"})

        geneColumn_X = "UniqueEntryIdentifier"
        geneColumn_Y = "UniqueEntryIdentifier"
        metricColumn_X = f"{scaleType}_metric_X"
        metricColumn_Y = f"{scaleType}_metric_Y"

        if reverse_X:
            data_X[metricColumn_X] = -data_X[metricColumn_X]
            logger1.info("Reversed metric direction for X-axis data (rank2rank).")
        if reverse_Y:
            data_Y[metricColumn_Y] = -data_Y[metricColumn_Y]
            logger1.info("Reversed metric direction for Y-axis data (rank2rank).")
    else:
        ### Import X axis data:
        if dirTransform == True:
            logger1.info("Directional transformation mode application for X axis")
        if many2oneTransformation_X == False:
            data_X = pd.read_csv(infileName_X, sep="\t")
            if dirTransform == True:
                data_X["{}_metric_X".format(scaleType)] = data_X[[significanceColumn_X,metricColumn_X]].apply(lambda x: convertSignificance(x.iloc[0], x.iloc[1]), axis=1)
                data_X = data_X.rename(columns={geneColumn_X:"UniqueEntryIdentifier"})
            else:
                data_X = data_X.rename(columns={geneColumn_X:"UniqueEntryIdentifier", metricColumn_X:"{}_metric_X".format(scaleType)})
            geneColumn_X = "UniqueEntryIdentifier"
            metricColumn_X = "{}_metric_X".format(scaleType)
            #data_X.drop(data_X.columns.difference([geneColumn_X,metricColumn_X]), 1, inplace=True)
            data_X = data_X[[geneColumn_X,metricColumn_X]]
            logger1.info("Imported X-axis data in standard mode")
        else:
            tmpDF = pd.read_csv(infileName_X, sep="\t")
            records = []
            for index, row in tmpDF.iterrows():
                if row[geneColumn_X] != ".":
                    genes = row[geneColumn_X].split(",")
                    for gene in genes:
                        if dirTransform == True:
                            records.append( (gene, convertSignificance(row[significanceColumn_X], row[metricColumn_X])) )
                        else:
                            records.append( (gene, row[metricColumn_X]) )
            geneColumn_X = "UniqueEntryIdentifier"
            metricColumn_X = "{}_metric_X".format(scaleType)
            labels = [geneColumn_X,metricColumn_X]
            data_X = pd.DataFrame.from_records(records, columns=labels)
            logger1.info("Imported X-axis data in many2one transformation mode")
        
        if reverse_X == True:
            data_X[metricColumn_X] = data_X[metricColumn_X].apply(lambda val: -val)
            logger1.info("Reversed metric direction for X-axis data")
        
        ### Import Y axis data:
        data_Y = pd.read_csv(infileName_Y, sep="\t")
        if dirTransform == True:
            logger1.info("Directional transformation mode application for Y axis")
            data_Y["{}_metric_Y".format(scaleType)] = data_Y[[significanceColumn_Y,metricColumn_Y]].apply(lambda x: convertSignificance(x.iloc[0], x.iloc[1]), axis=1)
            data_Y = data_Y.rename(columns={geneColumn_Y:"UniqueEntryIdentifier"})
        else:
            data_Y = data_Y.rename(columns={geneColumn_Y:"UniqueEntryIdentifier", metricColumn_Y:"{}_metric_Y".format(scaleType)})
        geneColumn_Y = "UniqueEntryIdentifier"
        metricColumn_Y = "{}_metric_Y".format(scaleType)
        #data_Y.drop(data_Y.columns.difference([geneColumn_Y,metricColumn_Y]), 1, inplace=True)
        data_Y = data_Y[[geneColumn_Y,metricColumn_Y]]
        logger1.info("Imported Y-axis data in standard mode")
        if reverse_Y == True:
            data_Y[metricColumn_Y] = data_Y[metricColumn_Y].apply(lambda val: -val)
            logger1.info("Reversed metric direction for Y-axis data")
        
    ### left merge on X-AXIS DATA as the base:
    if comparisonMode == "anno2anno":
        dfs = [data_X, data_Y]
        df_final = reduce(lambda left,right: pd.merge(left,right,on=geneColumn_X), dfs)
        logger1.info("Combined X and Y axes data ending up with {} data points".format(len(df_final)))
    elif comparisonMode == "rank2rank":
        # Identify if we deal with region vs string pairing
        x_regions = _all_region_ids(data_X[geneColumn_X])
        y_regions = _all_region_ids(data_Y[geneColumn_Y])
        if x_regions and y_regions:
            logger1.info("rank2rank: both RNK identifiers look like genomic regions; intersecting regions (many-to-many supported).")
            df_final = _intersect_region_tables(
                data_X, data_Y,
                geneColumn_X=geneColumn_X, geneColumn_Y=geneColumn_Y,
                metricColumn_X=metricColumn_X, metricColumn_Y=metricColumn_Y
            )
            logger1.info("rank2rank intersection resulted in {} overlapping pairs".format(len(df_final)))
        else:
            logger1.info("rank2rank: using exact string match on identifiers.")
            df_final = pd.merge(data_X, data_Y, on=geneColumn_X)
            logger1.info("rank2rank string-based pairing resulted in {} matched items".format(len(df_final)))
    else:
        df_final = _intersect_region_tables(
            data_X, data_Y,
            geneColumn_X=geneColumn_X, geneColumn_Y=geneColumn_Y,
            metricColumn_X=metricColumn_X, metricColumn_Y=metricColumn_Y
        )
        logger1.info("Combined X and Y (region2region) via intersection; {} overlapping pairs".format(len(df_final)))

    ### Identify the "significant" in both:
    df_final.to_csv("{}.PreprocessedData_all.tsv".format(analysisPrefix), sep='\t', index=False)
    df_significant = df_final[((df_final[metricColumn_X] >= FCcut) | (df_final[metricColumn_X] <= -FCcut)) & 
                              ((df_final[metricColumn_Y] >= FCcut) | (df_final[metricColumn_Y] <= -FCcut))].copy()
    logger1.info("Applied thresholds (FCcut={}) filtering data down to {} data points".format(FCcut, len(df_significant)))
    
    ### Compute correlation:
    if corrType == "PS":
        corrP = stats.pearsonr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        corrS = stats.spearmanr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        title_text = "{0} vs. {1}\nPearson's correlation = {2:.5f}, pvalue = {3:.5f}\nSpearman's correlation = {4:.5f}, pvalue = {5:.5f}".format(label_X, label_Y, corrP[0], corrP[1], corrS[0], corrS[1])
    elif corrType == "pearsonr":
        corrP = stats.pearsonr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        corrS = ["N/A", "N/A"]
        title_text = "{} vs. {}\nPearson's correlation = {:.5f}, pvalue = {:.5f}".format(label_X, label_Y, corrP[0], corrP[1])
    else:
        corrS = stats.spearmanr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        corrP = ["N/A", "N/A"]
        title_text = "{} vs. {}\nSpearman's correlation = {:.5f}, pvalue = {:.5f}".format(label_X, label_Y, corrS[0], corrS[1])
    logger1.info("Computed Pearson's Correlation coefficient: {} (p-value={})".format(corrP[0], corrP[1]))
    logger1.info("Computed Spearman's Correlation coefficient: {} (p-value={})".format(corrS[0], corrS[1]))
    
    ### Process data and plot:
    m1_sign = np.array(list(df_significant[metricColumn_X]))
    m2_sign = np.array(list(df_significant[metricColumn_Y]))
    xmin = m1_sign.min()
    xmax = m1_sign.max()
    ymin = m2_sign.min()
    ymax = m2_sign.max()

    absMax = np.array([abs(xmax), abs(ymax), abs(xmin), abs(ymin)]).max()
    absMax = absMax + absMax*0.1

    xmin = ymin = -absMax
    xmax = ymax = absMax

    plt.clf()
    fig, ax = plt.subplots(figsize=(figSize[0],figSize[1]))
    
#     ax.imshow(np.rot90(Z), cmap=plt.cm.gist_earth_r, extent=[xmin, xmax, ymin, ymax], aspect="auto") # UNCOMMENT to get old-style look
#     ax.plot(m1_sign, m2_sign, 'k.', markersize=1, alpha=1) # UNCOMMENT to get old-style look
    if plotNoKDE == False:
        if plotBgKDE == True:
            X, Y = np.mgrid[xmin:xmax:BGres, ymin:ymax:BGres]
            positions = np.vstack([X.ravel(), Y.ravel()])
            values = np.vstack([m1_sign, m2_sign])
            kernel = stats.gaussian_kde(values)
            Z = np.reshape(kernel(positions).T, X.shape)

            ax.imshow(np.rot90(Z), cmap=plt.cm.viridis, extent=[xmin, xmax, ymin, ymax], aspect="auto") # COMMENT to get old-style 
            ax.plot(m1_sign, m2_sign, 'w.', markersize=1, alpha=1) # COMMENT to get old-style
            textColor = "white" # "black"
            #     textColor = "black"  # UNCOMMENT to get old-style look
        else:
            sns.set_style("white")
            # Calculate the point density
            xy = np.vstack([m1_sign, m2_sign])
            Z = stats.gaussian_kde(xy)(xy)
            sns.scatterplot(x=m1_sign, y=m2_sign, hue=Z, s=1, edgecolor=None, palette="Spectral_r", alpha=1, legend=None, ax=ax)
            textColor = "black"
    else:
        ax.plot(m1_sign, m2_sign, 'k.', markersize=1, alpha=1) # COMMENT to get old-style
        textColor = "black"

    ### Add dashed lines to plot:
    lineStyle = "--" # ":"
    if FCcut == 0:
        plt.plot(np.linspace(-20,120,1000), [0]*1000, '--', color=textColor, linewidth=1)
        plt.plot([0]*1000, np.linspace(-20,120,1000), '--', color=textColor, linewidth=1)
    else:
        plt.plot(np.linspace(-1000,-FCcut,1000), [FCcut]*1000, lineStyle, color=textColor, linewidth=1)
        plt.plot(np.linspace(FCcut,1000,1000), [FCcut]*1000, lineStyle, color=textColor, linewidth=1)
        plt.plot(np.linspace(-1000,-FCcut,1000), [-FCcut]*1000, lineStyle, color=textColor, linewidth=1)
        plt.plot(np.linspace(FCcut,1000,1000), [-FCcut]*1000, lineStyle, color=textColor, linewidth=1)

        plt.plot([FCcut]*1000, np.linspace(-1000,-FCcut,1000), lineStyle, color=textColor, linewidth=1)
        plt.plot([FCcut]*1000, np.linspace(FCcut,1000,1000), lineStyle, color=textColor, linewidth=1)
        plt.plot([-FCcut]*1000, np.linspace(-1000,-FCcut,1000), lineStyle, color=textColor, linewidth=1)
        plt.plot([-FCcut]*1000, np.linspace(FCcut,1000,1000), lineStyle, color=textColor, linewidth=1)

    plt.xlabel(label_X, fontsize=12)
    plt.ylabel(label_Y, fontsize=12)
    plt.title(title_text, fontsize=13)

    ax.set_xlim([xmin, xmax])
    ax.set_ylim([ymin, ymax])

    ### Add text over the plot:
    left, width = .25, .5
    bottom, height = .25, .5
    right = left + width
    top = bottom + height

    df_N1 = df_final[((df_final[metricColumn_X] <= -FCcut) & (df_final[metricColumn_Y] >= FCcut))].copy()
    N = len(df_N1)
    ax.text(0.01, 0.99 * (bottom + top), f'N1={N} {quadrantDescription}',
            horizontalalignment='left',
            verticalalignment='top',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    df_N2 = df_final[((df_final[metricColumn_X] >= FCcut) & (df_final[metricColumn_Y] >= FCcut))].copy()
    N = len(df_N2)
    ax.text(0.99, 0.99 * (bottom + top), f'N2={N} {quadrantDescription}',
            horizontalalignment='right',
            verticalalignment='top',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    df_N3 = df_final[((df_final[metricColumn_X] <= -FCcut) & (df_final[metricColumn_Y] <= -FCcut))].copy()
    N = len(df_N3)
    ax.text(0.01, 0.01 * (bottom + top), f'N3={N} {quadrantDescription}',
            horizontalalignment='left',
            verticalalignment='bottom',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    df_N4 = df_final[((df_final[metricColumn_X] >= FCcut) & (df_final[metricColumn_Y] <= -FCcut))].copy()
    N = len(df_N4)
    ax.text(0.99, 0.01 * (bottom + top), f'N4={N} {quadrantDescription}',
            horizontalalignment='right',
            verticalalignment='bottom',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    plt.savefig("{}.KDE.pdf".format(analysisPrefix), bbox_inches='tight', dpi=300)
    logger1.info("Saved the plot to: {}.KDE.pdf".format(analysisPrefix))
    
    df_significant.to_csv("{}.PlottedData.tsv".format(analysisPrefix), sep='\t', index=False)
    
    ### Identify if we deal with the gene names (or other plain string based identifiers), or with the genomic regions in format <chromosome>:<start>-<end>, which can be identified by the presence of both ":" and "-" and the lenght == 3 when separated by those in proper order, and all those in every single identifier. If this is true, then we wish to save the result as BED format, otherwise we just want to save as TXT files.
    formatBED = True
    geneColumn_Y = "UniqueEntryIdentifier"
    metricColumn_Y = "{}_metric_Y".format(scaleType)
    for dataPoint in df_final[geneColumn_X]:
        if ":" in dataPoint and "-" in dataPoint:
            try:
                chromosome, start, end = dataPoint.split(":")[0], dataPoint.split(":")[1].split("-")[0], dataPoint.split(":")[1].split("-")[1]
                int(start)
                int(end)
            except:
                formatBED = False
                break
        else:
            formatBED = False
            break
    
    if formatBED == True:
        logger1.info("Datapoint naming identifiers recognized as pseudo-BED format (<chromosome>:<start>-<end>) -- WILL SAVE AS BED FILES")
        if len(df_N1) > 0:
            df_N1["chrom"] = df_N1[geneColumn_X].apply(lambda x: x.split(":")[0])
            df_N1["start"] = df_N1[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[0])
            df_N1["end"] = df_N1[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[1])
            df_N1 = df_N1[["chrom","start","end",metricColumn_X,metricColumn_Y]]
            df_N1.to_csv("{}.PlottedData_N1.bed".format(analysisPrefix), sep='\t', index=False, header=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N1.bed".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N1 quadrant, BED file saving skipped.")

        if len(df_N2) > 0:
            df_N2["chrom"] = df_N2[geneColumn_X].apply(lambda x: x.split(":")[0])
            df_N2["start"] = df_N2[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[0])
            df_N2["end"] = df_N2[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[1])
            df_N2 = df_N2[["chrom","start","end",metricColumn_X,metricColumn_Y]]
            df_N2.to_csv("{}.PlottedData_N2.bed".format(analysisPrefix), sep='\t', index=False, header=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N2.bed".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N2 quadrant, BED file saving skipped.")
        
        if len(df_N3) > 0:
            df_N3["chrom"] = df_N3[geneColumn_X].apply(lambda x: x.split(":")[0])
            df_N3["start"] = df_N3[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[0])
            df_N3["end"] = df_N3[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[1])
            df_N3 = df_N3[["chrom","start","end",metricColumn_X,metricColumn_Y]]
            df_N3.to_csv("{}.PlottedData_N3.bed".format(analysisPrefix), sep='\t', index=False, header=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N3.bed".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N3 quadrant, BED file saving skipped.")
        
        if len(df_N4) > 0:
            df_N4["chrom"] = df_N4[geneColumn_X].apply(lambda x: x.split(":")[0])
            df_N4["start"] = df_N4[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[0])
            df_N4["end"] = df_N4[geneColumn_X].apply(lambda x: x.split(":")[1].split("-")[1])
            df_N4 = df_N4[["chrom","start","end",metricColumn_X,metricColumn_Y]]
            df_N4.to_csv("{}.PlottedData_N4.bed".format(analysisPrefix), sep='\t', index=False, header=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N4.bed".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N4 quadrant, BED file saving skipped.")
    else:
        logger1.info("Datapoint naming identifiers NOT recognized as pseudo-BED format (<chromosome>:<start>-<end>)")
        if len(df_N1) > 0:
            df_N1[geneColumn_X].to_csv("{}.PlottedData_N1.tsv".format(analysisPrefix), sep='\t', index=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N1.txt".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N1 quadrant, TXT file saving skipped.")

        if len(df_N2) > 0:
            df_N2[geneColumn_X].to_csv("{}.PlottedData_N2.tsv".format(analysisPrefix), sep='\t', index=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N2.txt".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N2 quadrant, TXT file saving skipped.")
        
        if len(df_N3) > 0:
            df_N3[geneColumn_X].to_csv("{}.PlottedData_N3.tsv".format(analysisPrefix), sep='\t', index=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N3.txt".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N3 quadrant, TXT file saving skipped.")
        
        if len(df_N4) > 0:
            df_N4[geneColumn_X].to_csv("{}.PlottedData_N4.tsv".format(analysisPrefix), sep='\t', index=False)
            logger1.info("Saved the plotted data to: {}.PlottedData_N4.txt".format(analysisPrefix))
        else:
            logger1.info("No datapoints in N4 quadrant, TXT file saving skipped.")

    logger1.info("Saved the plotted data to: {}.PlottedData.tsv".format(analysisPrefix))

def plot_plainPlot_correlation(infileName_X, metricColumn_X, geneColumn_X, label_X, reverse_X, many2oneTransformation_X, infileName_Y, metricColumn_Y, geneColumn_Y, label_Y, reverse_Y, BGres, FCcut, scaleType, figSize, corrType, analysisPrefix, dirTransform, significanceColumn_X, significanceColumn_Y, quadrantDescription, markGenes, comparisonMode):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    
    if comparisonMode == "rank2rank":
        logger1.info("Loading RNK inputs for X and Y (rank2rank mode).")
        data_X = _prepare_rank_df(infileName_X, side_label=f"{scaleType}_metric_X".replace("linear_", ""))
        data_Y = _prepare_rank_df(infileName_Y, side_label=f"{scaleType}_metric_Y".replace("linear_", ""))

        if f"{scaleType}_metric_X" not in data_X.columns:
            data_X = data_X.rename(columns={data_X.columns[1]: f"{scaleType}_metric_X"})
        if f"{scaleType}_metric_Y" not in data_Y.columns:
            data_Y = data_Y.rename(columns={data_Y.columns[1]: f"{scaleType}_metric_Y"})

        geneColumn_X = "UniqueEntryIdentifier"
        geneColumn_Y = "UniqueEntryIdentifier"
        metricColumn_X = f"{scaleType}_metric_X"
        metricColumn_Y = f"{scaleType}_metric_Y"

        if reverse_X:
            data_X[metricColumn_X] = -data_X[metricColumn_X]
            logger1.info("Reversed metric direction for X-axis data (rank2rank).")
        if reverse_Y:
            data_Y[metricColumn_Y] = -data_Y[metricColumn_Y]
            logger1.info("Reversed metric direction for Y-axis data (rank2rank).")
    else:
        ### Import X axis data:
        if dirTransform == True:
            logger1.info("Directional transformation mode application for X axis")
        if many2oneTransformation_X == False:
            data_X = pd.read_csv(infileName_X, sep="\t")
            if dirTransform == True:
                data_X["{}_metric_X".format(scaleType)] = data_X[[significanceColumn_X,metricColumn_X]].apply(lambda x: convertSignificance(x.iloc[0], x.iloc[1]), axis=1)
                data_X = data_X.rename(columns={geneColumn_X:"UniqueEntryIdentifier"})
            else:
                data_X = data_X.rename(columns={geneColumn_X:"UniqueEntryIdentifier", metricColumn_X:"{}_metric_X".format(scaleType)})
            geneColumn_X = "UniqueEntryIdentifier"
            metricColumn_X = "{}_metric_X".format(scaleType)
            #data_X.drop(data_X.columns.difference([geneColumn_X,metricColumn_X]), 1, inplace=True)
            data_X = data_X[[geneColumn_X,metricColumn_X]]
            logger1.info("Imported X-axis data in standard mode")
        else:
            tmpDF = pd.read_csv(infileName_X, sep="\t")
            records = []
            for index, row in tmpDF.iterrows():
                if row[geneColumn_X] != ".":
                    genes = row[geneColumn_X].split(",")
                    for gene in genes:
                        if dirTransform == True:
                            records.append( (gene, convertSignificance(row[significanceColumn_X], row[metricColumn_X])) )
                        else:
                            records.append( (gene, row[metricColumn_X]) )
            geneColumn_X = "UniqueEntryIdentifier"
            metricColumn_X = "{}_metric_X".format(scaleType)
            labels = [geneColumn_X,metricColumn_X]
            data_X = pd.DataFrame.from_records(records, columns=labels)
            logger1.info("Imported X-axis data in many2one transformation mode")
            
        if reverse_X == True:
            data_X[metricColumn_X] = data_X[metricColumn_X].apply(lambda val: -val)
            logger1.info("Reversed metric direction for X-axis data")
        
        ### Import Y axis data:
        data_Y = pd.read_csv(infileName_Y, sep="\t")
        if dirTransform == True:
            logger1.info("Directional transformation mode application for Y axis")
            data_Y["{}_metric_Y".format(scaleType)] = data_Y[[significanceColumn_Y,metricColumn_Y]].apply(lambda x: convertSignificance(x.iloc[0], x.iloc[1]), axis=1)
            data_Y = data_Y.rename(columns={geneColumn_Y:"UniqueEntryIdentifier"})
        else:
            data_Y = data_Y.rename(columns={geneColumn_Y:"UniqueEntryIdentifier", metricColumn_Y:"{}_metric_Y".format(scaleType)})
        geneColumn_Y = "UniqueEntryIdentifier"
        metricColumn_Y = "{}_metric_Y".format(scaleType)
        #data_Y.drop(data_Y.columns.difference([geneColumn_Y,metricColumn_Y]), 1, inplace=True)
        data_Y = data_Y[[geneColumn_Y,metricColumn_Y]]
        logger1.info("Imported Y-axis data in standard mode")
        if reverse_Y == True:
            data_Y[metricColumn_Y] = data_Y[metricColumn_Y].apply(lambda val: -val)
            logger1.info("Reversed metric direction for Y-axis data")
    
        
    ### left merge on X-AXIS DATA as the base:
    if comparisonMode == "anno2anno":
        dfs = [data_X, data_Y]
        df_final = reduce(lambda left,right: pd.merge(left,right,on=geneColumn_X), dfs)
        logger1.info("Combined X and Y axes data ending up with {} data points".format(len(df_final)))
    elif comparisonMode == "rank2rank":
        x_regions = _all_region_ids(data_X[geneColumn_X])
        y_regions = _all_region_ids(data_Y[geneColumn_Y])
        if x_regions and y_regions:
            logger1.info("rank2rank: both RNK identifiers look like genomic regions; intersecting regions (many-to-many supported).")
            df_final = _intersect_region_tables(
                data_X, data_Y,
                geneColumn_X=geneColumn_X, geneColumn_Y=geneColumn_Y,
                metricColumn_X=metricColumn_X, metricColumn_Y=metricColumn_Y
            )
            logger1.info("rank2rank intersection resulted in {} overlapping pairs".format(len(df_final)))
        else:
            logger1.info("rank2rank: using exact string match on identifiers.")
            df_final = pd.merge(data_X, data_Y, on=geneColumn_X)
            logger1.info("rank2rank string-based pairing resulted in {} matched items".format(len(df_final)))
    else:
        df_final = _intersect_region_tables(
            data_X, data_Y,
            geneColumn_X=geneColumn_X, geneColumn_Y=geneColumn_Y,
            metricColumn_X=metricColumn_X, metricColumn_Y=metricColumn_Y
        )
        logger1.info("Combined X and Y (region2region) via intersection; {} overlapping pairs".format(len(df_final)))

    ### Identify the genes to marked "manually" as specified via --markGenes flag:
    df_markGenes = None
    if markGenes != []:
        if comparisonMode == "anno2anno":
            df_markGenes = df_final[df_final[geneColumn_X].isin(markGenes)].copy()
            logger1.info("Identified {} genes to be marked on the plain scatter plot".format(len(df_markGenes)))
        else:
            # region2region: markGenes is a BED file path
            if isinstance(markGenes, dict) and "bedPath" in markGenes:
                try:
                    mg = pd.read_csv(markGenes["bedPath"], sep="\t", header=None, usecols=[0,1,2])
                    mg = mg.dropna().reset_index(drop=True)
                    mg.columns = ["chrom","start","end"]
                    btM = BedTool.from_dataframe(mg.assign(name="m"))
                    # Build BedTools for X and Y identifiers
                    btX, dfXreg = _df_to_bedtool_from_idcol(df_final.rename(columns={geneColumn_X: "X_id"}), "X_id", name_col="nameX")  # based on df_final's ids
                    # For Y, use the auxiliary column if present; otherwise reconstruct
                    if "UniqueEntryIdentifier_Y" in df_final.columns:
                        btY, dfYreg = _df_to_bedtool_from_idcol(df_final.rename(columns={"UniqueEntryIdentifier_Y": "Y_id"}), "Y_id", name_col="nameY")
                    else:
                        btY, dfYreg = None, pd.DataFrame()

                    markX = set()
                    markY = set()
                    if btX is not None:
                        interXM = btX.intersect(btM, wa=True, u=True)
                        for f in interXM:
                            markX.add(f.name)
                    if btY is not None:
                        interYM = btY.intersect(btM, wa=True, u=True)
                        for f in interYM:
                            markY.add(f.name)

                    mask = df_final[geneColumn_X].isin(markX)
                    if "UniqueEntryIdentifier_Y" in df_final.columns:
                        mask = mask | df_final["UniqueEntryIdentifier_Y"].isin(markY)
                    df_markGenes = df_final[mask].copy()
                    logger1.info("Identified {} items to be marked (region2region)".format(len(df_markGenes)))
                except Exception as e:
                    logger1.warning("Failed to parse/mark --markGenes BED: {}".format(e))
                    df_markGenes = None
            else:
                logger1.warning("Ignoring --markGenes in region2region: expected a BED path")
                df_markGenes = None
    
    ### Identify the "significant" in both:
    df_significant = df_final[((df_final[metricColumn_X] >= FCcut) | (df_final[metricColumn_X] <= -FCcut)) & 
                              ((df_final[metricColumn_Y] >= FCcut) | (df_final[metricColumn_Y] <= -FCcut))].copy()
    logger1.info("Applied thresholds filtering data down to {} data points".format(len(df_significant)))
    
    ### Compute correlation:
    if corrType == "PS":
        corrP = stats.pearsonr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        corrS = stats.spearmanr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        title_text = "{0} vs. {1}\nPearson's correlation = {2:.5f}, pvalue = {3:.5f}\nSpearman's correlation = {4:.5f}, pvalue = {5:.5f}".format(label_X, label_Y, corrP[0], corrP[1], corrS[0], corrS[1])
        corr = f"Pearson={corrP[0]} (p={corrP[1]}), Spearman={corrS[0]} (p={corrS[1]})"
    elif corrType == "pearsonr":
        corrP = stats.pearsonr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        title_text = "{} vs. {}\nPearson's correlation = {}, pvalue = {}".format(label_X, label_Y, corrP[0], corrP[1])
        corr = corrS[0]
    else:
        corrS = stats.spearmanr(df_significant[metricColumn_X], df_significant[metricColumn_Y])
        title_text = "{} vs. {}\nSpearman's correlation = {}, pvalue = {}".format(label_X, label_Y, corrS[0], corrS[1])
        corr = corrS[0]
    logger1.info("Computed Correlation coefficient: {}".format(corr))
    
    ### Process data and plot:
    m1_sign = np.array(list(df_significant[metricColumn_X]))
    m2_sign = np.array(list(df_significant[metricColumn_Y]))
    xmin = m1_sign.min()
    xmax = m1_sign.max()
    ymin = m2_sign.min()
    ymax = m2_sign.max()

    absMax = np.array([abs(xmax), abs(ymax), abs(xmin), abs(ymin)]).max()
    absMax = absMax + absMax*0.1

    xmin = ymin = -absMax
    xmax = ymax = absMax


    plt.clf()
    fig, ax = plt.subplots(figsize=(figSize[0],figSize[1]))
    if markGenes != []:
        ax.plot(m1_sign, m2_sign, 
            color="#a7adba", 
            markersize=10, 
            marker=".",
            linewidth=0,
            alpha=1)
    else:
        ax.plot(m1_sign, m2_sign, 
            color="#343d46", 
            markersize=8, 
            marker=".",
            linewidth=0,
            alpha=1)
    
    ### Add dashed lines to plot:
    textColor = "black"
    lineStyle = "--" # ":"
    lineColor = "#a7adba"
    if FCcut == 0:
        plt.plot(np.linspace(-20,120,1000), [0]*1000, '--', color=lineColor, linewidth=1)
        plt.plot([0]*1000, np.linspace(-20,120,1000), '--', color=lineColor, linewidth=1)
    else:
        plt.plot(np.linspace(-1000,-FCcut,1000), [FCcut]*1000, lineStyle, color=lineColor, linewidth=1)
        plt.plot(np.linspace(FCcut,1000,1000), [FCcut]*1000, lineStyle, color=lineColor, linewidth=1)
        plt.plot(np.linspace(-1000,-FCcut,1000), [-FCcut]*1000, lineStyle, color=lineColor, linewidth=1)
        plt.plot(np.linspace(FCcut,1000,1000), [-FCcut]*1000, lineStyle, color=lineColor, linewidth=1)

        plt.plot([FCcut]*1000, np.linspace(-1000,-FCcut,1000), lineStyle, color=lineColor, linewidth=1)
        plt.plot([FCcut]*1000, np.linspace(FCcut,1000,1000), lineStyle, color=lineColor, linewidth=1)
        plt.plot([-FCcut]*1000, np.linspace(-1000,-FCcut,1000), lineStyle, color=lineColor, linewidth=1)
        plt.plot([-FCcut]*1000, np.linspace(FCcut,1000,1000), lineStyle, color=lineColor, linewidth=1)

    ### Optionally mark the selected genes:
    if markGenes != []:
        ax.plot(
            np.array(list(df_markGenes[metricColumn_X])),
            np.array(list(df_markGenes[metricColumn_Y])),
            color="red",
            markersize=12, 
            marker=".",
            linewidth=0,
            alpha=1)
        label_point(df_markGenes[metricColumn_X], df_markGenes[metricColumn_Y], df_markGenes[geneColumn_X], plt.gca())
    
    ### Finalize plot labeling etc.:
    plt.xlabel(label_X, fontsize=12)
    plt.ylabel(label_Y, fontsize=12)
    plt.title(title_text, fontsize=13)

    ax.set_xlim([xmin, xmax])
    ax.set_ylim([ymin, ymax])

    ### Add text over the plot:
    left, width = .25, .5
    bottom, height = .25, .5
    right = left + width
    top = bottom + height


    N = len(df_final[((df_final[metricColumn_X] <= -FCcut) & (df_final[metricColumn_Y] >= FCcut))])
    ax.text(0.01, 0.99 * (bottom + top), f'N1={N} {quadrantDescription}',
            horizontalalignment='left',
            verticalalignment='top',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    N = len(df_final[((df_final[metricColumn_X] >= FCcut) & (df_final[metricColumn_Y] >= FCcut))])
    ax.text(0.99, 0.99 * (bottom + top), f'N2={N} {quadrantDescription}',
            horizontalalignment='right',
            verticalalignment='top',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    N = len(df_final[((df_final[metricColumn_X] <= -FCcut) & (df_final[metricColumn_Y] <= -FCcut))])
    ax.text(0.01, 0.01 * (bottom + top), f'N3={N} {quadrantDescription}',
            horizontalalignment='left',
            verticalalignment='bottom',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    N = len(df_final[((df_final[metricColumn_X] >= FCcut) & (df_final[metricColumn_Y] <= -FCcut))])
    ax.text(0.99, 0.01 * (bottom + top), f'N4={N} {quadrantDescription}',
            horizontalalignment='right',
            verticalalignment='bottom',
            transform=ax.transAxes,
            color=textColor,
            fontsize=13)

    plt.savefig("{}.plain.pdf".format(analysisPrefix), bbox_inches='tight', dpi=300)
    plt.savefig("{}.plain.svg".format(analysisPrefix), bbox_inches='tight', dpi=300)
    logger1.info("Saved the plot to: {}.plain.[pdf, svg]".format(analysisPrefix))
    

def main():
    infileName_X, metricColumn_X, geneColumn_X, label_X, reverse_X, many2oneTransformation_X, infileName_Y, metricColumn_Y, geneColumn_Y, label_Y, reverse_Y, BGres, FCcut, scaleType, figSize, corrType, analysisPrefix, dirTransform, significanceColumn_X, significanceColumn_Y, plotPlain, plotNoKDE, plotBgKDE, quadrantDescription, comparisonMode, markGenes = paramsParser()
    
    plot_KDE_correlation(infileName_X, metricColumn_X, geneColumn_X, label_X, reverse_X, many2oneTransformation_X, infileName_Y, metricColumn_Y, geneColumn_Y, label_Y, reverse_Y, BGres, FCcut, scaleType, figSize, corrType, analysisPrefix, dirTransform, significanceColumn_X, significanceColumn_Y, quadrantDescription, plotNoKDE, plotBgKDE, comparisonMode)
    
    if plotPlain == True:
        plot_plainPlot_correlation(infileName_X, metricColumn_X, geneColumn_X, label_X, reverse_X, many2oneTransformation_X, infileName_Y, metricColumn_Y, geneColumn_Y, label_Y, reverse_Y, BGres, FCcut, scaleType, figSize, corrType, analysisPrefix, dirTransform, significanceColumn_X, significanceColumn_Y, quadrantDescription, markGenes, comparisonMode)
    
    logging.info("All done, thank you!")
main()