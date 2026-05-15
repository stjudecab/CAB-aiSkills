#!/usr/bin/env python
#########################################################################
# Copyright (c) 2016-~ Beisi Xu && St Jude
# 
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
# 
#*Author:       Beisi Xu < xubeisi [at] gmail DOT com >
# File Name: enrichr_api.py
# Description:
# example usage for single gene set test: enrichr_api.py -a gene.sym -t stjudemm -o Pathway_gene -m api,sum 
# ,where each line in gene.sym is a gene name
# example usage for multiple gene sets from within GMT file: python ~/programs/GIT/sjcab_std_report/commonbin/enrichr_api.py -a annotatedGenes.GeneNames.fixedNames.selected.gmt -o testName -m gmt,api,sum
#########################################################################

import re, os, sys
from string import *
from optparse import OptionParser
from pathlib import Path

import json
import requests
import time
import string
import subprocess
import pandas as pd

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import numpy as np

from functools import reduce

import logging
from pdb import set_trace

#export HTTP_PROXY="http://10.43.51.93:808"
#export HTTPS_PROXY="http://10.43.51.93:808"

server  = 'https://amp.pharm.mssm.edu'
server  = 'https://maayanlab.cloud'

ENRICHR_URLADD = server + '/Enrichr/addList'

ENRICHR_URL_EN = server + '/Enrichr/enrich'
ENRICHR_URL_EX = server + '/Enrichr/export'
query_string_EN = '?userListId=%s&backgroundType=%s'
query_string_EX = '?userListId=%s&filename=%s&backgroundType=%s'

scrDir = os.path.dirname(os.path.abspath(__file__))
workDir = os.getcwd()
CRTFILE = os.path.join(scrDir, 'data/curl_crt.crt')

# sjcabutils is shipped as commonbin/sjcabutils.py. When this script is run from
# sjcab_custom_pathwayEnrichment/, only that directory is on sys.path — add commonbin.
_commonbin = os.path.normpath(os.path.join(scrDir, os.pardir, "commonbin"))
if os.path.isfile(os.path.join(_commonbin, "sjcabutils.py")) and _commonbin not in sys.path:
    sys.path.insert(0, _commonbin)


def resolve_pathway_dotplot_script():
    """Find pathway_dotplot.py: next to this script, or under sjcab_custom_pathwayEnrichment/ (commonbin layout)."""
    candidates = (
        os.path.join(scrDir, "pathway_dotplot.py"),
        os.path.normpath(
            os.path.join(scrDir, os.pardir, "sjcab_custom_pathwayEnrichment", "pathway_dotplot.py")
        ),
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def pathway_dotplot_candidate_paths():
    """Paths tried by resolve_pathway_dotplot_script (for log messages)."""
    return (
        os.path.join(scrDir, "pathway_dotplot.py"),
        os.path.normpath(
            os.path.join(scrDir, os.pardir, "sjcab_custom_pathwayEnrichment", "pathway_dotplot.py")
        ),
    )


def configureLogging(analysisPrefix):
    logging.basicConfig(level = logging.INFO,
                        format = '###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s',
                        handlers = [logging.FileHandler('enrichr_api.{}.log'.format(analysisPrefix)), logging.StreamHandler()],
                        datefmt='%y-%m-%d %H:%M:%S')

def ConvertRGB2sth(r, g, b):
    tmp_r = (r/255.0)
    tmp_g = (g/255.0)
    tmp_b = (b/255.0)

    return tmp_r, tmp_g, tmp_b

def make_colormap(seq):
    """Return a LinearSegmentedColormap
    seq: a sequence of floats and RGB-tuples. The floats should be increasing
    and in the interval (0,1).
    """
    seq = [(None,) * 3, 0.0] + list(seq) + [1.0, (None,) * 3]
    cdict = {'red': [], 'green': [], 'blue': []}
    for i, item in enumerate(seq):
        if isinstance(item, float):
            r1, g1, b1 = seq[i - 1]
            r2, g2, b2 = seq[i + 1]
            cdict['red'].append([item, r1, r2])
            cdict['green'].append([item, g1, g2])
            cdict['blue'].append([item, b1, b2])
    return mcolors.LinearSegmentedColormap('CustomMap', cdict)

def getCmaps():
    # to design new color palette do e.g. this 'sns.color_palette("rocket_r", 9), and add the output after 'ConvertRGB2sth(208,206,206)', which stands for grey color. Uselful info also here: https://seaborn.pydata.org/tutorial/color_palettes.html
    cmap_grey_rocket_r = sns.color_palette([ConvertRGB2sth(208,206,206),
                                            (0.96739773, 0.77451297, 0.65057302),
                                            (0.96298491, 0.6126247, 0.45145074),
                                            (0.95165009, 0.44224144, 0.30214494),
                                            (0.90848638, 0.24568473, 0.24598324),
                                            (0.79085854, 0.10184672, 0.313391),
                                            (0.63139686, 0.10067417, 0.35664819),
                                            (0.45809049, 0.12142996, 0.34540024),
                                            (0.29977678, 0.11356089, 0.29254823),
                                            (0.14633406, 0.07973393, 0.1986151)])
    cmap_grey_Oranges = sns.color_palette([ConvertRGB2sth(208,206,206),
                                            (0.9969242599000384, 0.914648212226067, 0.8323721645520954),
                                            (0.9937254901960785, 0.8501960784313726, 0.7043137254901961),
                                            (0.9921568627450981, 0.7644444444444445, 0.5524029219530949),
                                            (0.9921568627450981, 0.6564705882352941, 0.3827450980392157),
                                            (0.9914186851211073, 0.550726643598616, 0.23277201076509035),
                                            (0.9545098039215686, 0.44, 0.10666666666666666),
                                            (0.8871510957324106, 0.3320876585928489, 0.03104959630911188),
                                            (0.7709803921568628, 0.2541176470588235, 0.007058823529411764),
                                            (0.6179930795847751, 0.19907727797001154, 0.012610534409842366)])
    cmap_grey_Reds = sns.color_palette([ConvertRGB2sth(208,206,206),
                                            (0.9969242599000384, 0.8961937716262975, 0.8489042675893886),
                                            (0.9913725490196079, 0.7913725490196079, 0.7082352941176471),
                                            (0.9882352941176471, 0.6715417147251057, 0.5605382545174933),
                                            (0.9874509803921568, 0.5411764705882353, 0.41568627450980394),
                                            (0.9835755478662053, 0.4127950788158401, 0.28835063437139563),
                                            (0.9466666666666667, 0.26823529411764707, 0.19607843137254902),
                                            (0.8503344867358708, 0.14686658977316416, 0.13633217993079583),
                                            (0.7364705882352941, 0.08, 0.10117647058823528),
                                            (0.5946174548250673, 0.04613610149942329, 0.07558631295655516)])
    return cmap_grey_rocket_r, cmap_grey_Oranges, cmap_grey_Reds

def check(test_str, allowed = set(string.ascii_lowercase + string.digits + '.' + "-" + "_" + "/")):
    '''this function will quickly check if the gene set name has only signs allowed for making them folder and filenames. Returns Bool value'''
    return set(test_str.lower()) <= allowed

def read(file):
    all = {}

    for line in open(file,"r"):
        sline = line.strip().split()
        if len(sline) > 0:
            all[sline[0]] = 1
    return all

def ftenrichrline(line,overmin,pmax,qmax,noold=1):
    sline = line.replace("\xA0","\x20").replace(";"," ").strip().split("\t")
    if not re.search("/",sline[1]):
        sys.stderr.write(line.replace("\xA0","\x20").replace(";"," "))
        return []
    if int(sline[1].split("/")[0]) > overmin:
        if float(sline[2]) <= pmax and float(sline[3]) <= qmax:
            if noold:
                return sline[:4] + sline[6:]
            else:
                return sline
        else:
            return []
    else:
        return []

def controldType(df, field):
    df[field] = df[field].apply(lambda val: float(val))
    return df[field]
#     try:


def gmt_write_dotplot_manifest(gmt_base, samples_dict_ordered, samples_dict, out_dir):
    """Write file<TAB>label manifest pointing at per-sample *.sum.all tables."""
    manifest_path = os.path.join(out_dir, "{}.dotplot_manifest.tsv".format(gmt_base))
    with open(manifest_path, "w", encoding="utf-8") as mf:
        mf.write("file\tlabel\n")
        for sample in samples_dict_ordered:
            mf.write("{}\t{}\n".format(
                "{}.sum.all".format(sample),
                samples_dict[sample],
            ))
    return manifest_path


def gmt_write_pathways_of_interest(path, terms):
    """Write one pathway Term per line for pathway_dotplot --pathwaysOfInterest."""
    with open(path, "w", encoding="utf-8") as pf:
        for t in terms:
            pf.write("{}\n".format(str(t).replace("\r", " ").replace("\n", " ")))


def gmt_run_pathway_dotplot(
    pathway_dotplot_script,
    python_exe,
    out_dir,
    manifest_path,
    gmt_base,
    pathways_tag,
    output_prefix,
    significance_column,
    terms,
):
    """Run pathway_dotplot.py; log failures without aborting enrichr_api."""
    if not terms:
        logging.warning("pathway dotplot skipped (no pathways): {}".format(output_prefix))
        return
    poi_path = os.path.join(out_dir, "{}.dotplot_pathways.{}.tsv".format(gmt_base, pathways_tag))
    try:
        gmt_write_pathways_of_interest(poi_path, terms)
    except Exception as e:
        logging.error("Failed writing pathways file {}: {}".format(poi_path, e))
        return
    cmd = [
        python_exe,
        pathway_dotplot_script,
        "--inputManifest", os.path.abspath(manifest_path),
        "--outputPrefix", output_prefix,
        "--outputDir", os.path.abspath(out_dir),
        "--significanceColumn", significance_column,
        "--colormap", "auto",
        "--pathwaysOfInterest", os.path.abspath(poi_path),
    ]
    logging.info("pathway dotplot: {}".format(" ".join(cmd)))
    try:
        proc = subprocess.run(
            cmd,
            cwd=out_dir,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            logging.error(
                "pathway_dotplot.py failed (exit %s) for %s. stderr (truncated): %s",
                proc.returncode,
                output_prefix,
                (proc.stderr or "")[:2000],
            )
        else:
            logging.info("pathway dotplot finished: {}".format(output_prefix))
    except Exception as e:
        logging.error("pathway_dotplot subprocess error for {}: {}".format(output_prefix, e))
#     try:
#         tmp = pd.to_numeric(df[field], errors="raise")
#         return tmp
#     except ValueError:
#         df[field] = df[field].apply(lambda val: float(val))
#         return df[field]
#     except:
#         print("Failed to correct dtype\n", df[field])
#         return df[field]

def main(argv):
    usage = " %prog [options] -b file -i 1 "
    parser = OptionParser(usage)
    parser.add_option("-a", "--file1", action="store", type="string",
            dest="f1", help="file1 to match", metavar="<file>")
    parser.add_option("-b", "--file2", action="store", type="string",
            dest="f2", help="file2 to match", metavar="<file>")
    parser.add_option("-t", "--table", action="store", type="string",
            dest="iftab", help="delimiter, [ %default ]", metavar="<char>",default='stjudehg')
    parser.add_option("-o", "--outprefix", action="store", type="string",
            dest="fout", help="outfile to match", metavar="<file>")
    parser.add_option("-m", "--mode", action="store", type="string",
            dest="mode", help="api: getresults; sum(:summary)|sumerge[_80](:merge terms of 80% overlap)|raw ", metavar="<file>", default="api,sum")
    parser.add_option("-e", "--engine", action="store", type=str,
            dest="engine", help="Engine, so either 'Enrichr' or 'YeastEnrichr'. By default = 'Enrichr'.", default="Enrichr")#, choices=['Enrichr', 'YeastEnrichr'])
    (opt, args) = parser.parse_args(argv)
    if len(argv) < 2:
        parser.print_help()
        sys.exit(1)
    try:
        import sjcabutils as GenomeData
    except ImportError:
        import time

        class GenomeData:
            @staticmethod
            def logcmd(argv0, thefile):
                """Fallback if commonbin/sjcabutils.py is unavailable (matches sjcabutils.logcmd)."""
                dirtime = time.strftime("%Y-%b-%d-%H-%M", time.localtime())
                argv = [rr for rr in argv0]
                for ii in range(1, len(argv)):
                    if re.search("[, *?!|;]", argv0[ii]) or len(argv0[ii]) < 1:
                        argv[ii] = '"' + argv[ii] + '"'
                argv[0] = argv[0].split("/")[-1]
                with open(thefile, "a") as flog:
                    flog.write(" ".join(argv) + " # " + dirtime + " \n")
    GenomeData.logcmd(argv, '.run.log')
    
    configureLogging(os.path.basename(opt.fout))
    
    modes0 = opt.mode.split(",")
    modes = []
    poverlap = 80
    for rr in modes0:
        if rr.split("_")[0] == "sumerge":
            if re.search("_",rr):
                poverlap = float(rr.split("_")[1])
            modes.append("sum")
            modes.append("merge")
        else:
            modes.append(rr.split("_")[0])
                
    if "gmt" in modes:
        modes.remove("gmt")
        logging.info("Using GMT mode")
        if check(opt.fout):
            Path(opt.fout).mkdir(parents=True, exist_ok=True)
            inGMT = open(opt.f1, "r")
            os.chdir(os.path.join(workDir, opt.fout))
            geneSets = {}
            for row in inGMT:
                geneSet = row.strip().split("\t")
                geneSetName = geneSet[0]
                geneSets[geneSetName] = geneSet[2:]
                if check(geneSetName):
                    outName = os.path.join(workDir, opt.fout, "{}.txt".format(geneSetName))
                    tmpFile = open(outName,'w')
                    tmpFile.write('\n'.join(str(x) for x in geneSet[2:]))
                    tmpFile.close()
                    if len(modes) > 0:
                        command = "{} {} -a {} -o {} -m {} -e {} -t {}".format(sys.executable, os.path.join(scrDir, os.path.basename(__file__)), outName, geneSetName, ','.join(str(x) for x in modes), opt.engine, opt.iftab)
                        logging.info("running command: {}".format(command))
                        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout.read()
                        logging.info("{} done".format(geneSetName))
                else:
                    logging.error("gene set names provided in GMT file needs to have only letters, numbers '.', '-' and '_', no other signs allowed. Your entry looks like:\t{}".format(geneSetName))
                    exit()
            inGMT.close()
            ## here we need to establish which part of the sample name might be chopped off without losing the information (i.e. we remove everything that is present in all sample names)
            geneSet = set(list(geneSets.keys())[0].split("."))
            for geneSetName in list(geneSets.keys())[1:]:
                geneSet = geneSet.intersection(set(geneSetName.split(".")))
            samplesDict = {}
            for geneSetName in list(geneSets.keys()):
                tmp = geneSetName.split(".")
                for rep in geneSet:
                    tmp.remove(rep)
                samplesDict[geneSetName] = '.'.join(str(x) for x in tmp)
            samplesDict_ordered = list(samplesDict.keys())
            samplesDict_ordered.sort()
            
            
            ## Prepare the output XLS files:
            
            ## No.1 excel file containing lists of genes tested:
            outfile = pd.ExcelWriter("{}.GenesLists.xlsx".format(os.path.basename(opt.f1).replace(".gmt", "")), engine='xlsxwriter')
            workbook = outfile.book
            header_format = workbook.add_format({
            'bold': True,
            'text_wrap': False,
            'valign': 'bottom',
            'align': "left",
            'fg_color': '#D7E4BC',
            'border': 1})
            header_format.set_rotation(45)
            
            dfs = []
            for col_num, value in enumerate(samplesDict_ordered):
                dfs.append(pd.DataFrame({samplesDict[value]:geneSets[value]}))
            df = pd.concat(dfs, ignore_index=True, axis=1)
            df.to_excel(outfile, index=False, sheet_name="list", startrow=1, header=False)
            
            worksheet = outfile.sheets["list"]
            for col_num, value in enumerate(samplesDict_ordered):
                worksheet.write(0, col_num, samplesDict[value], header_format)
            outfile.close()
            
            ## No.2 excel file containing q<0.05 results:
            outfile = pd.ExcelWriter("{}.fc_q0.05.xlsx".format(os.path.basename(opt.f1).replace(".gmt", "")), engine='xlsxwriter')
            outfileTXT = open("{}.fc_q0.05_listOfSpreadsheets.txt".format(os.path.basename(opt.f1).replace(".gmt", "")), 'w')
            workbook = outfile.book
            header_format = workbook.add_format({
            'bold': True,
            'text_wrap': False,
            'valign': 'bottom',
            'align': "left",
            'fg_color': '#D7E4BC',
            'border': 1})
            header_format.set_rotation(45)
            
            for sample in samplesDict_ordered:
                try:
                    df = pd.read_csv("{}.sum.q5".format(sample), sep="\t", float_precision='high')
#                     df["P-value"] = controldType(df, "P-value") #pd.to_numeric(df["P-value"], errors="coerce")
#                     df["Adjusted P-value"] = controldType(df, "Adjusted P-value") #pd.to_numeric(df["Adjusted P-value"], errors="coerce")
#                     df["Z-score"] = pd.to_numeric(df["Z-score"], errors="coerce")
#                     df["Combined Score"] = pd.to_numeric(df["Combined Score"], errors="coerce")
                    df.to_excel(outfile, index=False, sheet_name=samplesDict[sample][:31], startrow=1, header=False)
                    worksheet = outfile.sheets[samplesDict[sample][:31]]
                    worksheet.set_column("A:A", 50)
                    worksheet.set_column("H:H", 20)
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                    outfileTXT.write("{}\t{}\n".format(sample, samplesDict[sample]))
                    
                    ## Draw bar plot for top 10 pathways enriched:
                    df_plot = df.head(10).copy()
#                     df.to_csv("test.{}.tsv".format(sample),sep="\t")
#                     print(sample, df.dtypes)
#                     print(df_plot[['Term','P-value','Adjusted P-value']])
                    df_plot["-log10(Adjusted P-value)"] = df_plot['Adjusted P-value'].apply(lambda val: -np.log10(val) if val > 10**-10 else -np.log10(10**-10))
                    df_plot = df_plot.sort_values("-log10(Adjusted P-value)",ascending=False)
                    if len(df_plot) > 0:
                        plt.clf()
                        fig, ax = plt.subplots()
                        sns.barplot(x="-log10(Adjusted P-value)", y="Term", data=df_plot, color='#BE4038', ax=ax)
                        fig.savefig("{}.sum.q5.pdf".format(sample),dpi=300, bbox_inches='tight')
                        plt.close()
                    else:
                        logging.warning("df_plot length == 0 -> no significant entries found in {} file".format("{}.sum.q5".format(sample)))
                    
                except FileNotFoundError:
                    logging.warning("file '{}' not found - most likely no significant results were found.".format("{}.sum.q5".format(sample)))
                
                except pd.errors.EmptyDataError:
                    logging.warning("file '{}' is empty - would have triggered the 'pandas.errors.EmptyDataError' - most likely no significant results were found.".format("{}.sum.q5".format(sample)))
                
                except Exception as e:
                    logging.error("Unknown error while processing file '{}.sum.all' ::: => {}".format(e))
                
            outfile.close()
            outfileTXT.close()
            
            ## No.2 excel file containing p<0.05 results:
            outfile = pd.ExcelWriter("{}.fc_p0.05.xlsx".format(os.path.basename(opt.f1).replace(".gmt", "")), engine='xlsxwriter')
            outfileTXT = open("{}.fc_p0.05_listOfSpreadsheets.txt".format(os.path.basename(opt.f1).replace(".gmt", "")), 'w')
            workbook = outfile.book
            header_format = workbook.add_format({
            'bold': True,
            'text_wrap': False,
            'valign': 'bottom',
            'align': "left",
            'fg_color': '#D7E4BC',
            'border': 1})
            header_format.set_rotation(45)
            
            for sample in samplesDict_ordered:
                try:
                    df = pd.read_csv("{}.sum.p5".format(sample), sep="\t", float_precision='high')
                    df.to_excel(outfile, index=False, sheet_name=samplesDict[sample][:31], startrow=1, header=False)
                    worksheet = outfile.sheets[samplesDict[sample][:31]]
                    worksheet.set_column("A:A", 50)
                    worksheet.set_column("H:H", 20)
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                    outfileTXT.write("{}\t{}\n".format(sample, samplesDict[sample]))
                    
                    ## Draw bar plot for top 10 pathways enriched:
                    
                    df_plot = df.head(10).copy()
                    df_plot["-log10(P-value)"] = df_plot['P-value'].apply(lambda val: -np.log10(val) if val > 10**-10 else -np.log10(10**-10))
                    df_plot = df_plot.sort_values("-log10(P-value)",ascending=False)
                    if len(df_plot) > 0:
                        plt.clf()
                        fig, ax = plt.subplots()
                        sns.barplot(x="-log10(P-value)", y="Term", data=df_plot, color='#FFA414', ax=ax)
                        fig.savefig("{}.sum.p5.pdf".format(sample),dpi=300, bbox_inches='tight')
                        plt.close()
                    else:
                        logging.warning("df_plot lenght == 0 -> no significant entries found in {} file".format("{}.sum.p5".format(sample)))
                
                except FileNotFoundError:
                    logging.warning("file '{}' not found - most likely no significant results were found.".format("{}.sum.p5".format(sample)))
                
                except pd.errors.EmptyDataError:
                    logging.warning("file '{}' is empty - would have triggered the 'pandas.errors.EmptyDataError' - most likely no significant results were found.".format("{}.sum.p5".format(sample)))
                
                except Exception as e:
                    logging.error("Unknown error while processing file '{}.sum.all' ::: => {}".format(e))
                
            outfile.close()
            outfileTXT.close()
            
            ## No.3 tsv summary files containing all availible datasets combined, with either p-values or FDRs, saved as -log10 values. These might be used for further plotting 
            dfsList = []
            pValColumns = []
            pValColumnsDown = []
            pValColumnsUp = []
            FDRColumns = []
            FDRColumnsDown = []
            FDRColumnsUp = []
            log10Cols=[]
            for sample in samplesDict_ordered:
                try:
#                     df = pd.read_csv("{}.sum.all".format(sample), sep="\t", index_col="Term", float_precision='high')
                    df = pd.read_csv("{}.sum.all".format(sample), sep="\t", float_precision='high')
                    df["{} -log10(P)".format(sample)] = df['P-value'].apply(lambda val: -np.log10(val) if val > 10**-10 else -np.log10(10**-10))
                    pValColumns.append("{} -log10(P)".format(sample))
                    df["{} -log10(FDR)".format(sample)] = df['Adjusted P-value'].apply(lambda val: -np.log10(val) if val > 10**-10 else -np.log10(10**-10))
                    FDRColumns.append("{} -log10(FDR)".format(sample))
                    df.drop(columns=list(df.columns.difference(["Term", "{} -log10(P)".format(sample),"{} -log10(FDR)".format(sample)])), inplace=True)
                    log10Cols.append("{} -log10(P)".format(sample))
                    log10Cols.append("{} -log10(FDR)".format(sample))
#                     df.drop_duplicates(inplace=True)
#                     df = df.loc[df.index.drop_duplicates()]
                    dfsList.append(df.copy())
#                     print(df)
                    ### Attempting to auto-detect columns for differential peaks. This will work fine for the automated diffPeak pipeline, but might not work correctly in other, custom datasets.
                    if ".Down" in sample:
                        pValColumnsDown.append("{} -log10(P)".format(sample))
                        FDRColumnsDown.append("{} -log10(FDR)".format(sample))
                    if ".Up" in sample:
                        pValColumnsUp.append("{} -log10(P)".format(sample))
                        FDRColumnsUp.append("{} -log10(FDR)".format(sample))
                
                except FileNotFoundError:
                    logging.warning("file '{}.sum.all' not found - most likely no significant results were found for this sample".format(sample))
                
                except pd.errors.EmptyDataError:
                    logging.warning("file '{}.sum.all' is empty - would have triggered the 'pandas.errors.EmptyDataError' - most likely no significant results were found for this sample".format(sample))
                
                except Exception as e:
                    logging.error("Unknown error while processing file '{}.sum.all' ::: => {}".format(e))


#             dfsJoined = pd.concat(dfsList, axis=1, join='outer')
#             dfsJoined = pd.merge(left, right, on='Term')
            dfsJoined = reduce(lambda left,right: pd.merge(left,right,on='Term',how="outer"), dfsList)
#             dfsJoined = pd.concat(dfsList, axis=1, join_axes=[dfsList[0].index])
            dfsJoined.fillna(0, inplace=True)
            dfsJoined.set_index('Term', inplace=True)

            dfsJoined['rankingSumPval'] = dfsJoined[pValColumns].apply(lambda x: np.sum([abs(y) for y in x]), axis=1)
            dfsJoined['rankingSumFDR'] = dfsJoined[FDRColumns].apply(lambda x: np.sum([abs(y) for y in x]), axis=1)
#             dfsJoined.sort_values('rankingSum', ascending=False, inplace=True)
            if len(FDRColumnsUp) > 0 and len(pValColumnsUp) > 0:
                dfsJoined['rankingSumUpPval'] = dfsJoined[list(pValColumnsUp)].apply(lambda x: np.sum([abs(y) for y in x]), axis=1)
                dfsJoined['rankingSumUpFDR'] = dfsJoined[list(FDRColumnsUp)].apply(lambda x: np.sum([abs(y) for y in x]), axis=1)
                UpSwitch = 1
            else:
                UpSwitch = 0
            if len(FDRColumnsDown) > 0 and len(pValColumnsDown) > 0:
                dfsJoined['rankingSumDownPval'] = dfsJoined[list(pValColumnsDown)].apply(lambda x: np.sum([abs(y) for y in x]), axis=1)
                dfsJoined['rankingSumDownFDR'] = dfsJoined[list(FDRColumnsDown)].apply(lambda x: np.sum([abs(y) for y in x]), axis=1)
                DownSwitch = 1
            else:
                DownSwitch = 0
            
            dfsJoined['NAME'] = dfsJoined.index
            (dfsJoined[['NAME']+pValColumns]).to_csv("{}.summary_pvals.tsv".format(os.path.basename(opt.f1).replace(".gmt", "")), sep='\t', index=False)
            (dfsJoined[['NAME']+FDRColumns]).to_csv("{}.summary_FDRs.tsv".format(os.path.basename(opt.f1).replace(".gmt", "")), sep='\t', index=False)

            ## Plot top 10 gene signatures:
            cmap_grey_rocket_r, cmap_grey_Oranges, cmap_grey_Reds = getCmaps()
#             SeabornVersion = str(sns.__version__).split(".")
#             if int(SeabornVersion[0]) >= 0 and int(SeabornVersion[1]) >= 11:
#             df_plot_p = (dfsJoined[pValColumns]).head(10).copy()
#             df_plot_f = (dfsJoined[FDRColumns]).head(10).copy()
            
            if len(dfsJoined) > 0: #sanity check
                gmt_base = os.path.basename(opt.f1).replace(".gmt", "")
                pathway_dotplot_py = resolve_pathway_dotplot_script()
                dotplot_manifest_path = None
                terms_pval_top = dfsJoined.sort_values('rankingSumPval', ascending=False).head(10).index.tolist()
                terms_fdr_top = dfsJoined.sort_values('rankingSumFDR', ascending=False).head(10).index.tolist()
                terms_up_pval_top = []
                terms_up_fdr_top = []
                terms_dn_pval_top = []
                terms_dn_fdr_top = []
                if UpSwitch == 1:
                    terms_up_pval_top = dfsJoined.sort_values('rankingSumUpPval', ascending=False).head(10).index.tolist()
                    terms_up_fdr_top = dfsJoined.sort_values('rankingSumUpFDR', ascending=False).head(10).index.tolist()
                if DownSwitch == 1:
                    terms_dn_pval_top = dfsJoined.sort_values('rankingSumDownPval', ascending=False).head(10).index.tolist()
                    terms_dn_fdr_top = dfsJoined.sort_values('rankingSumDownFDR', ascending=False).head(10).index.tolist()
                if pathway_dotplot_py is not None:
                    dotplot_manifest_path = gmt_write_dotplot_manifest(
                        gmt_base, samplesDict_ordered, samplesDict, os.getcwd()
                    )
                    logging.info("Using pathway_dotplot.py at {}".format(pathway_dotplot_py))
                else:
                    c0, c1 = pathway_dotplot_candidate_paths()
                    logging.warning(
                        "pathway_dotplot.py not found (tried {} and {}); skipping GMT summary dotplots".format(c0, c1)
                    )

                fig, ax = plt.subplots()
                dfsJoined.sort_values('rankingSumPval', ascending=False, inplace=True)
                df_plot = (dfsJoined[pValColumns]).head(10).copy()
                ax = sns.heatmap(df_plot, vmin=0, vmax=5, cmap=cmap_grey_Oranges, cbar_kws={'label': "-log10(p-value)"}, linewidths=.5)
                plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
                plt.savefig("{}.summary_pvals.top10.pdf".format(os.path.basename(opt.f1).replace(".gmt", "")), bbox_inches='tight', dpi=300)
                plt.close()
                
                fig, ax = plt.subplots()
                dfsJoined.sort_values('rankingSumFDR', ascending=False, inplace=True)
                df_plot = (dfsJoined[FDRColumns]).head(10).copy()
                ax = sns.heatmap(df_plot, vmin=0, vmax=5, cmap=cmap_grey_Reds, cbar_kws={'label': "-log10(FDR)"}, linewidths=.5)
                plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
                plt.savefig("{}.summary_FDRs.top10.pdf".format(os.path.basename(opt.f1).replace(".gmt", "")), bbox_inches='tight', dpi=300)
                plt.close()
                
                if UpSwitch == 1:
#                     df_plot = dfsJoined.sort_values('rankingSumUp', ascending=False)
#                     df_plot_p = (df_plot[pValColumnsUp]).head(10).copy()
#                     df_plot_f = (df_plot[FDRColumnsUp]).head(10).copy()
                    
                    fig, ax = plt.subplots()
                    dfsJoined.sort_values('rankingSumUpPval', ascending=False, inplace=True)
                    df_plot = (dfsJoined[pValColumnsUp]).head(10).copy()
                    ax = sns.heatmap(df_plot, vmin=0, vmax=5, cmap=cmap_grey_Oranges, cbar_kws={'label': "-log10(p-value)"}, linewidths=.5)
                    plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
                    plt.savefig("{}.summary_pvals.top10Up.pdf".format(os.path.basename(opt.f1).replace(".gmt", "")), bbox_inches='tight', dpi=300)
                    plt.close()
                    
                    fig, ax = plt.subplots()
                    dfsJoined.sort_values('rankingSumUpFDR', ascending=False, inplace=True)
                    df_plot = (dfsJoined[FDRColumnsUp]).head(10).copy()
                    ax = sns.heatmap(df_plot, vmin=0, vmax=5, cmap=cmap_grey_Reds, cbar_kws={'label': "-log10(FDR)"}, linewidths=.5)
                    plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
                    plt.savefig("{}.summary_FDRs.top10Up.pdf".format(os.path.basename(opt.f1).replace(".gmt", "")), bbox_inches='tight', dpi=300)
                    plt.close()
                    
#                     df_plot = dfsJoined.sort_values('rankingSumDown', ascending=False)
#                     df_plot_p = (df_plot[pValColumnsDown]).head(10).copy()
#                     df_plot_f = (df_plot[FDRColumnsDown]).head(10).copy()
                
                if DownSwitch == 1:
                    fig, ax = plt.subplots()
                    dfsJoined.sort_values('rankingSumDownPval', ascending=False, inplace=True)
                    df_plot = (dfsJoined[pValColumnsDown]).head(10).copy()
                    ax = sns.heatmap(df_plot, vmin=0, vmax=5, cmap=cmap_grey_Oranges, cbar_kws={'label': "-log10(p-value)"}, linewidths=.5)
                    plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
                    plt.savefig("{}.summary_pvals.top10Down.pdf".format(os.path.basename(opt.f1).replace(".gmt", "")), bbox_inches='tight', dpi=300)
                    plt.close()
                    
                    fig, ax = plt.subplots()
                    dfsJoined.sort_values('rankingSumDownFDR', ascending=False, inplace=True)
                    df_plot = (dfsJoined[FDRColumnsDown]).head(10).copy()
                    ax = sns.heatmap(df_plot, vmin=0, vmax=5, cmap=cmap_grey_Reds, cbar_kws={'label': "-log10(FDR)"}, linewidths=.5)
                    plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
                    plt.savefig("{}.summary_FDRs.top10Down.pdf".format(os.path.basename(opt.f1).replace(".gmt", "")), bbox_inches='tight', dpi=300)
                    plt.close()

                if dotplot_manifest_path is not None:
                    py_exe = sys.executable
                    gmt_run_pathway_dotplot(
                        pathway_dotplot_py, py_exe, os.getcwd(), dotplot_manifest_path, gmt_base,
                        "summary_pvals_top10", "{}.summary_pvals.top10".format(gmt_base), "pvalue", terms_pval_top,
                    )
                    gmt_run_pathway_dotplot(
                        pathway_dotplot_py, py_exe, os.getcwd(), dotplot_manifest_path, gmt_base,
                        "summary_FDRs_top10", "{}.summary_FDRs.top10".format(gmt_base), "adjustedPvalue", terms_fdr_top,
                    )
                    if UpSwitch == 1:
                        gmt_run_pathway_dotplot(
                            pathway_dotplot_py, py_exe, os.getcwd(), dotplot_manifest_path, gmt_base,
                            "summary_pvals_top10Up", "{}.summary_pvals.top10Up".format(gmt_base), "pvalue", terms_up_pval_top,
                        )
                        gmt_run_pathway_dotplot(
                            pathway_dotplot_py, py_exe, os.getcwd(), dotplot_manifest_path, gmt_base,
                            "summary_FDRs_top10Up", "{}.summary_FDRs.top10Up".format(gmt_base), "adjustedPvalue", terms_up_fdr_top,
                        )
                    if DownSwitch == 1:
                        gmt_run_pathway_dotplot(
                            pathway_dotplot_py, py_exe, os.getcwd(), dotplot_manifest_path, gmt_base,
                            "summary_pvals_top10Down", "{}.summary_pvals.top10Down".format(gmt_base), "pvalue", terms_dn_pval_top,
                        )
                        gmt_run_pathway_dotplot(
                            pathway_dotplot_py, py_exe, os.getcwd(), dotplot_manifest_path, gmt_base,
                            "summary_FDRs_top10Down", "{}.summary_FDRs.top10Down".format(gmt_base), "adjustedPvalue", terms_dn_fdr_top,
                        )
                    
            else:
                logging.warning("No significant gene signatures were enriched, plotting top 10 not possible")
#             else:
#                 print("###\tSeaborn version is {}, but at least 0.11.0 is required. HEatmaps not plotted. (FYI. the color palette require this high version, if you really need a work around this, modify the code at 'cmap=' for cmap selection)".format(sns.__version__))
        else:
            logging.error("the output provided with '-o' flag needs to have only letters, numbers '.', '-' and '_', no other signs allowed")
            exit()
            
    else:
        if opt.fout == None:
            opt.fout = opt.f1.replace(".txt","").replace(".sym","").replace(".lst","")

        if "api" in modes:
            if opt.engine == "YeastEnrichr":
                ENRICHR_URLADD = server + '/YeastEnrichr/addList'
                ENRICHR_URL_EN = server + '/YeastEnrichr/enrich'
                ENRICHR_URL_EX = server + '/YeastEnrichr/export'
                if opt.iftab == "KEGG_2016,BioCarta_2016,WikiPathways_2016,Reactome_2016,GO_Biological_Process_2018,GO_Cellular_Component_2018,GO_Molecular_Function_2018,KEA_2015":
                    ### this means the default params were not changed from Enrichr to YeastEnrichr engine, thus these are now changed here to:
                    opt.iftab = "KEGG_2019,WikiPathways_2018,GO_Biological_Process_2018,GO_Cellular_Component_2018,GO_Molecular_Function_2018,InterPro_Domains_2019,Pfam_Domains_2019,Phenotype_AutoRIF"
            else:
                ENRICHR_URLADD = server + '/Enrichr/addList'
                ENRICHR_URL_EN = server + '/Enrichr/enrich'
                ENRICHR_URL_EX = server + '/Enrichr/export'
                if opt.iftab in [ "stjudeold" ]:
                    opt.iftab = "KEGG_2016,BioCarta_2016,WikiPathways_2016,Reactome_2016,GO_Biological_Process_2018,GO_Cellular_Component_2018,GO_Molecular_Function_2018,KEA_2015"
                if opt.iftab in [ "stjudehg" ]:
                    opt.iftab = "KEGG_2019_Human,BioCarta_2016,WikiPathways_2019_Human,Reactome_2016,GO_Biological_Process_2018,GO_Cellular_Component_2018,GO_Molecular_Function_2018,KEA_2015,ChEA_2016"
                    opt.iftab = "KEGG_2021_Human,BioCarta_2016,WikiPathway_2021_Human,Reactome_2016,GO_Biological_Process_2021,GO_Cellular_Component_2021,GO_Molecular_Function_2021,KEA_2015,ChEA_2016"
                    opt.iftab = "KEGG_2021_Human,BioCarta_2016,WikiPathway_2023_Human,Reactome_2022,GO_Biological_Process_2023,GO_Cellular_Component_2023,GO_Molecular_Function_2023,KEA_2015,ChEA_2022"
                    opt.iftab = "KEGG_2026,BioCarta_2016,WikiPathways_2024_Human,Reactome_Pathways_2024,GO_Biological_Process_2026,GO_Cellular_Component_2026,GO_Molecular_Function_2026,KEA_2015,ChEA_2022"
                if opt.iftab in [ "stjudemm" ]:
                    opt.iftab = "KEGG_2019_Mouse,BioCarta_2016,WikiPathways_2019_Mouse,Reactome_2016,GO_Biological_Process_2018,GO_Cellular_Component_2018,GO_Molecular_Function_2018,KEA_2015,ChEA_2016"
                    opt.iftab = "KEGG_2019_Mouse,BioCarta_2016,WikiPathways_2019_Mouse,Reactome_2016,GO_Biological_Process_2021,GO_Cellular_Component_2021,GO_Molecular_Function_2021,KEA_2015,ChEA_2016"
                    opt.iftab = "KEGG_2019_Mouse,BioCarta_2016,WikiPathways_2019_Mouse,Reactome_2022,GO_Biological_Process_2023,GO_Cellular_Component_2023,GO_Molecular_Function_2023,KEA_2015,ChEA_2022"
                    opt.iftab = "KEGG_2026,BioCarta_2016,WikiPathways_2024_Mouse,Reactome_Pathways_2024,GO_Biological_Process_2026,GO_Cellular_Component_2026,GO_Molecular_Function_2026,KEA_2015,ChEA_2022"
            
            logging.info("Using libraries: {}".format(opt.iftab))
            logging.info("Server set to ENRICHR_URLADD: {}".format(ENRICHR_URLADD))
            logging.info("Server set to ENRICHR_URL_EN: {}".format(ENRICHR_URL_EN))
            logging.info("Server set to ENRICHR_URL_EX: {}".format(ENRICHR_URL_EX))
            
            ttt = opt.iftab.split(',')
            todo = []

            genes1 = read(opt.f1)
            if not opt.f2 == None:
                genes2 = read(opt.f2)
                for name in genes1:
                    if name in genes2:
                        todo.append(name)
            else:
                for name in genes1:
                    todo.append(name)

            genes_str = '\n'.join(todo)
            description = ''
    #        print genes_str
            payload = {
                'list': (None, genes_str),
                'description': (None, description)
            }
            try:
                response = requests.post(ENRICHR_URLADD, files=payload)#, verify=CRTFILE)
            except:
                time.sleep(2)
                response = requests.post(ENRICHR_URLADD, files=payload)#, verify=CRTFILE)
            if not response.ok:
                raise Exception('Error analyzing gene list')
            #set_trace()
            data = json.loads(response.text)

            user_list_id = data['userListId']
            for gene_set_library in ttt:
                filename = opt.fout + '.' + gene_set_library
                if not os.path.isfile(filename + '.txt'):
                    url = ENRICHR_URL_EX + query_string_EX % (user_list_id, filename, gene_set_library)
    #                time.sleep(2)
                    response = requests.get(url, stream=False)#, verify=CRTFILE)
    #                response = requests.get(url, stream=True)
                    with open(filename + '.txt', 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024): 
                            if chunk:
                                f.write(chunk)
        if "sum" in modes:
            import glob
            allout = glob.glob(opt.fout+'.*.txt')
            dbname = []
            cccc = [ [ ".sum.p5", 0.05, 1, 4, "", 1, 6 ], [ ".sum.q5", 0.05, 0.05, 4, "", 1, 6 ], [ ".sum.all", 1, 1, 4, "", 1, 6 ] ]
            if 'raw' in modes:
                cccc.append([ ".sum.raw", 1.1, 1.1, 0, "", 1, 6 ])
            for ff in allout:
                for irp in [ "_2016","_2015","_2018", "_2021" ]:
                    ff = ff.replace(irp,"")
                dbname.append(ff.split(".")[-2])
            for cutoffs in cccc:
                suf, pmax, qmax, overmin, towr, noold, isort = cutoffs
                sline = open(allout[0]).readline().strip().split("\t")
                if noold:
                    sline = sline[:4] + sline[6:]
                towr += "\t".join(sline + ["Database"]) + "\n"
                with open(opt.fout+suf,"w") as fffout:
                    for iff in range(len(allout)):
                        ff = allout[iff]
                        db = dbname[iff]
                        for line in open(ff).readlines()[1:]:
                            sline = ftenrichrline(line,overmin,pmax,qmax,noold)
                            if len(sline) > 0:
                                towr += "\t".join(sline + [ db ]) + "\n"
                    fffout.write(towr)
                with open(opt.fout+suf,"r") as fffout:
                    allline = fffout.readlines()
                if len(allline) > 1:
                    os.system("(head -n 1 {0} ; tail -n +2 {0} | sort -t'\t' -rg -k{1} ) > {0}.tmp && mv {0}.tmp {0}".format(opt.fout+suf, isort))
#               ### Commenting the two lines below. I.e. it would delete q5 and p5 files without contents, but since now the heatmaps are generated as well, i need these files, even if empty, in order to have a column generated on a heatmap. This solution works perfectly for cases when we have many columns, and "top 10" pathways are derived from other. But It might become unstable in case if for example none of the pathways will be enriched and all will be empty for example. This will require debugging, most likely, and maybe even uncommenting these lines again?
#                 else:
#                     os.system("rm {}".format(opt.fout+suf))
            os.system("rm {}".format(" ".join(allout)))
        if "merge" in modes:
            for cutoffs in cccc:
                suf, pmax, qmax, overmin, towr, noold, isort = cutoffs
                fover = opt.fout+suf
                header = open(fover).readline().strip().split("\t")
                allori = {}
                for line in open(fover).readlines()[1:]:
                    sline = line.strip().split("\t")
                    score = float(sline[5])
                    allori[sline[0]] = [ score, sline[6].split(), sline ]
    
    

if __name__ == '__main__':
    main(sys.argv)
