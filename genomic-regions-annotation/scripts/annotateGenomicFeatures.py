#!/usr/bin/env python
##########################################################################################
#
# Copyright (c) 2020-~ Wojciech Rosikiewicz && St Jude
# This source code is released for free distribution under the terms of the CreativeCommons BY-NC-SA 4.0 International License
#*Author: Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# File Name: annotateGenomicFeatures.py
#
##########################################################################################
#
# This peak annotation script was intended to be used on the output of the voom2anno.sh script (aka. *.anno file).
# Example lines of the input file:
# Region	log2FC	log2AveExpr	t.value	p.value	q.value	FPKM.sample1_KO	FPKM.sample2_KO	FPKM.sample1_WT	FPKM.sample2_WT	theAUC	UpRank	DownRank	MADScore	MADScoreGrp1	MADScoreGrp2	Averlog2FPKMGrp1	Averlog2FPKMGrp2	RegionSize	Regulation	Gene_2kb	Gencode_ids	Gene_2-50kb	Gencode_ids	Closest_Gene	Gencode_id	Distance
# chr2:85770357-85770620	-2.4479196817109	7.25996937043856	-3.97194722778353	7.24754980542008e-05	0.025499296065403	758.59	0.000	1289.71	1375.31	1	1996	14	0.037382456	0.004319527	0.088062664	10.922080662	9.832633163	263	Down2	.	.	ATOH8	ENSG00000168874.13	ATOH8	ENSG00000168874.13	9608
#
# The strategy for the annotation is described here ("Feature Assignment Versions" section): https://wiki.stjude.org/pages/viewpage.action?spaceKey=CAB&title=Peak+annotation
# Hierarchal order of the annotation:
# 1. Promoter.Up
# 2. Promoter.Down
# 3. Exon
# 4. Intron
# 5. TES(transcription end sites)
# 6. Dis5(5' distal regions)
# 7. Dis3(3' distal regions)
# 8. Intergenic
##########################################################################################

import sys
import logging
import inspect
import argparse
if not any(arg in ("-h", "--help") for arg in sys.argv[1:]):
    import os
    import glob
    from pathlib import Path
    import subprocess
    
    import matplotlib.pyplot as plt
    import seaborn as sns
    from pylab import *
    import matplotlib
    matplotlib.use('Agg')
    
    import numpy as np
    import scipy
    import pandas as pd
    
    import pybedtools
    
    from pybedtools import BedTool
    from matplotlib.backends.backend_pdf import PdfPages
    #from adjustText import adjust_text

def parseArgs():
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    parser = argparse.ArgumentParser(description="This peak annotation script was intended to be used on the output of the voom2anno.sh script (aka. *.anno file). More details in the header of the script. The example command:\npython ~/programs/GIT/sjcab_std_report/sjcab_custom_atac/annotateGenomicFeatures.py -i test.vout.anno -g hg19\n\nExample usage in 'plotHeatmap' mode:\npython ~/programs/GIT/sjcab_std_report/sjcab_custom_atac/annotateGenomicFeatures.py -i GenomicFeaturesAnnotation/GenomicFeaturesAnnotation.summary.manual.tsv -m plotHeatmap")
    parser.add_argument("-i", "--infileName", help="Name of the input file (*.anno file).", action="store", type=str, required=True, dest="infileName")
    parser.add_argument("-g", "--genome", help="Required. Currently one of: hg19, hg38, mm9, mm10, sacCer3. No default is applied; callers must state the genome explicitly.", choices=["hg19", "hg38", "mm9", "mm10", "sacCer3"], action="store", type=str, required=True, dest="genome")
    parser.add_argument("-a", "--annoPath", help="The path containing 2kb.dis3.bed, 2kb.dis5.bed, 2kb.exon.bed, 2kb.intergenic.bed, 2kb.intron.bed, 2kb.promoter.bed, 2kb.promoter.down.bed, 2kb.promoter.up.bed, 2kb.tes.bed files for the genome version specified in 'genome' parameter. By default = '/research/rgs01/applications/hpcf/authorized_apps/cab/sjcab_share/sjcab_std_chip/data/anno/'.", default="/research/rgs01/applications/hpcf/authorized_apps/cab/sjcab_share/sjcab_std_chip/data/anno/", action="store", type=str, required=False, dest="annoPath")
    parser.add_argument("-c", "--columnHeader", help="Name of the column in which genomic features data will be stored. This might be useful if one wish to have multi level assignments.", default="FeatureAssignment", action="store", type=str, required=False, dest="columnHeader")
    parser.add_argument("-f", "--features", help="*.lst file (with one file name per row) located under 'annoPath' path or comma-separated list of reference BED files, which will be used to annotate genomic features to. By default = '2kb.promoter.up.bed,2kb.promoter.down.bed,2kb.exon.bed,2kb.intron.bed,2kb.tes.bed,2kb.dis5.bed,2kb.dis3.bed,2kb.intergenic.bed'", default="2kb.promoter.up.bed,2kb.promoter.down.bed,2kb.exon.bed,2kb.intron.bed,2kb.tes.bed,2kb.dis5.bed,2kb.dis3.bed,2kb.intergenic.bed", action="store", type=str, required=False, dest="features")
    parser.add_argument("-fl", "--featureLabels", help="*.labels.lst file (with one label per row) located under 'annoPath' path or comma-separated list of labels for the reference BED files. By default = 'Promoter.Up,Promoter.Down,Exon,Intron,TES (transcription end sites),Dis5 (5' distal regions),Dis3 (3' distal regions),Intergenic'", default="Promoter.Up,Promoter.Down,Exon,Intron,TES (transcription end sites),Dis5 (5' distal regions),Dis3 (3' distal regions),Intergenic", action="store", type=str, required=False, dest="featureLabels")
    parser.add_argument("-t", "--tmpDir", help="the name of the temporary directory (i.e. directory where a backup of the oryginal anno file will be stored just in case). By default = 'tmp_GenomicFeaturesAnnotation'", default="tmp_GenomicFeaturesAnnotation", action="store", type=str, required=False, dest="tmpDir")
    parser.add_argument("-m", "--mode", help="Mode of the program. Options are 'auto', which will conduct annotation of the *.anno file, automatically detecting the sub-mode of 'BED_format' or 'VOUT_format'; or the 'plotHeatmap' mode, which might be used to plot the heatmap of the data pointed to by 'infileName' (-i flag). This second mode is mainly for manual posprocessing, for example when one was analyzing multiple files in the 'BED_format' and wish to visualize their biases in a nice way. Also, the name of the differential categories (i.e. contents of the 'Category' column') will be used, as the assumption is that one manually set these names to be 'nice'. By default = 'auto'", default="auto", action="store", type=str, required=False, dest="mode", choices=['auto','plotHeatmap','VOUT_format_1on1','VOUT_format', 'VOUT_format_meth', 'VOUT_format_meth_1on1', "BED_format"])

    args = parser.parse_args()

    analysisPrefix = "GenomicFeaturesAnnotation"
    genome = args.genome
    annoPath = args.annoPath
    infileName = args.infileName
    columnHeader = args.columnHeader
    features = args.features
    featureLabels = args.featureLabels
    tmpDir = args.tmpDir
    mode = args.mode

    configureLogging(analysisPrefix)
    logger1.info("command used to run annotation script: python {}".format(' '.join(str(x) for x in sys.argv)))
    logger1.info("infileName: {}".format(infileName))
    logger1.info("analysisPrefix: {}".format(analysisPrefix))
    logger1.info("genome: {}".format(genome))
    logger1.info("annoPath: {}".format(annoPath))
    logger1.info("columnHeader: {}".format(columnHeader))
    logger1.info("features: {}".format(features))
    logger1.info("featureLabels: {}".format(featureLabels))
    logger1.info("tmpDir: {}".format(tmpDir))
    logger1.info("mode: {}".format(mode))


    if features.endswith(".lst") and featureLabels.endswith(".labels.lst"):
        featuresTMP = []
        infile = open(os.path.join(annoPath, genome, features))
        for row in infile:
            featuresTMP.append(row.strip())
        infile.close()

        labelsTMP = []
        infile = open(os.path.join(annoPath, genome, featureLabels))
        for row in infile:
            labelsTMP.append(row.strip())
        infile.close()

        if len(featuresTMP) == len(labelsTMP):
            i = 1
            for f, l in zip():
                logger1.info("Priority {} file '{}', recognized as '{}'.".format(i, f, l))
                i += 1
        else:
            logger1.error("features lst file listed the following region files (in the order of priority): {}".format(', '.join(str(x) for x in featuresTMP)))
            logger1.error("labels lst file listed the following region labels (in the order of priority): {}".format(', '.join(str(x) for x in labelsTMP)))
            logger1.error("The lengths of the above do not match, Program was aborted.")
            exit()
        return analysisPrefix, genome, annoPath, infileName, columnHeader, featuresTMP, labelsTMP, tmpDir, mode
    elif len(features.split(",")) == len(featureLabels.split(",")):
        return analysisPrefix, genome, annoPath, infileName, columnHeader, features.split(","), featureLabels.split(","), tmpDir, mode
    else:
        logger1.error("the length of features ({}) and featureLabels ({}) is not matching, or two lst files were not provided. The program has been aborted.".format(features.split(","), featureLabels.split(",")))
        exit()

def configureLogging(analysisPrefix):
    # https://stackoverflow.com/questions/9321741/printing-to-screen-and-writing-to-a-file-at-the-same-time
    logging.basicConfig(level = logging.INFO,
                        format = '###\t[%(asctime)s] %(filename)s:%(lineno)d: %(name)s %(levelname)s: %(message)s',
                        handlers = [logging.FileHandler('{}.log'.format(analysisPrefix)), logging.StreamHandler()],
                        datefmt='%y-%m-%d %H:%M:%S')

def annotateFeature(region, features, featuresDict, labelsDict):
    txtBed = "{}\t{}\t{}".format(region.split(":")[0], region.split(":")[1].split("-")[0], region.split(":")[1].split("-")[1])
    bed = BedTool(txtBed, from_string=True)
    for feature in features:
        ovr = bed.intersect(featuresDict[feature])
        if len(ovr) > 0:
            return labelsDict[feature]

def annotateFeatures(df, features, featuresDict, labelsDict):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    regionsRaw = list(df['Region'])
    regionsProcessed = ""
    regionsDict = {}
    regionsAnno = {}
    for region in regionsRaw:
        txtBed = "{}\t{}\t{}\n".format(region.split(":")[0], region.split(":")[1].split("-")[0], region.split(":")[1].split("-")[1])
        regionsDict[txtBed.strip()] = region
        regionsProcessed += txtBed
    regions = BedTool(regionsProcessed, from_string=True)
    for feature in features:
        intersections = regions.intersect(featuresDict[feature], wa=True, u=True)
        for region in intersections:
            regionsAnno[regionsDict[str(region).strip()]] = labelsDict[feature]
        regions = regions.subtract(featuresDict[feature], A=True)
        logger1.info("Feature {} completed.".format(feature) )
    logger1.info("Annotated {} out of {} regions.".format(len(regionsAnno), len(regionsRaw) ))
    return regionsAnno

def generateSummary(df, columnHeader, infileName, labelsDict, features, analysisPrefix, resultsDir, tmpDir, category, description):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    sumDict = dict(df[columnHeader].value_counts())
    outfileName = "{}/{}.summary.tsv".format(resultsDir, analysisPrefix)
    if os.path.isfile(outfileName):
        outfile = open(outfileName, "a")
    else:
        outfile = open(outfileName, "w")
        outfile.write("Annotated file\tCategory\tThreshold\t#Regions")
        for feature in features:
            outfile.write("\t{}".format(labelsDict[feature]))
        outfile.write("\n")

    outfile.write("{}\t{}\t{}\t{}".format(infileName, category, description[category][1], len(df)))
    for feature in features:
        if labelsDict[feature] in sumDict:
            outfile.write("\t{}".format(sumDict[labelsDict[feature]]))
        else:
            outfile.write("\t0")
#             logger1.info("{} feature not present in sumDict for {} category".format(labelsDict[feature], category ))
    outfile.write("\n")
    outfile.close()

    outfileName = "{}/{}.{}.summary.tsv".format(tmpDir, infileName, category)
    outfile = open(outfileName, "w")
    outfile.write("Genomic feature\tNumber of regions\n")
    for feature in features:
        if labelsDict[feature] in sumDict:
            outfile.write("{}\t{}\n".format(labelsDict[feature], sumDict[labelsDict[feature]]))
        else:
            outfile.write("{}\t0\n".format(labelsDict[feature]))

    outfile.close()
    logger1.info("Summary files generated")
    return sumDict, len(df)

def barPlot(infileName, resultsDir, sumDict, featureLabels, category, description, noFeatures, tmpDir):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    summarydf = pd.read_csv("{}/{}.{}.summary.tsv".format(tmpDir, infileName, category), sep = "\t", index_col=False)
    if np.sum(summarydf["Number of regions"]) > 0:
        plt.clf()
        cmap = plt.get_cmap('Spectral')
        colors = [cmap(i) for i in np.linspace(0, 1, 8)]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax = sns.barplot(x="Number of regions", y="Genomic feature", data=summarydf, palette=colors)#color="#D44D4D")
        plt.title("{} regions, {} ({})".format(noFeatures, category, description[category][1]))
        plt.savefig("{}/{}.{}.barPlot.pdf".format(resultsDir, infileName, category), bbox_inches='tight', dpi=300)
        plt.savefig("{}/{}.{}.barPlot.png".format(resultsDir, infileName, category), bbox_inches='tight', dpi=300)
        plt.close()
        logger1.info("Bar plot drawn for {}; {} category".format(infileName, category))
    else:
        logger1.warning("Bar plot was NOT drawn for {}; {} category; {} features were included into this category.".format(infileName, category, noFeatures))

def piePlot(infileName, resultsDir, sumDict, featureLabels, category, description, noFeatures, tmpDir):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    df = pd.read_csv("{}/{}.{}.summary.tsv".format(tmpDir, infileName, category), sep = "\t", index_col=False)
    if np.sum(df["Number of regions"]) > 0:
        plt.clf()
        cmap = plt.get_cmap('Spectral')
        colors = [cmap(i) for i in np.linspace(0, 1, 8)]
        fig, ax = plt.subplots(figsize=(7, 4))
        source_pie = plt.pie(df['Number of regions'], labels=df['Genomic feature'], autopct='%1.1f%%', shadow=False, colors=colors)
    #     source_pie = df.iplot(kind='pie', labels='Genomic feature', values='Number of regions', title='Sources of Pie')
        plt.title("{} regions, {} ({})".format(noFeatures, category, description[category][1]))
        plt.savefig("{}/{}.{}.piePlot.pdf".format(resultsDir, infileName, category), bbox_inches='tight', dpi=300)
        plt.savefig("{}/{}.{}.piePlot.png".format(resultsDir, infileName, category), bbox_inches='tight', dpi=300)
        plt.close()
        logger1.info("Pie plot drawn for {}; {} category".format(infileName, category))
    else:
        logger1.warning("Pie plot was NOT drawn for {}; {} category; {} features were included into this category.".format(infileName, category, noFeatures))

def generateHeatmap(infilePrefix, resultsDir, mode):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)

    if mode == 'plotHeatmap':
        pdfName = "{}.Heatmap.pdf".format(infilePrefix)
    else:
        pdfName = "{}/{}.Heatmap.pdf".format(resultsDir, infilePrefix.replace(".anno",""))
    with PdfPages(pdfName) as pdf_pages:
        if mode == 'plotHeatmap':
            df = pd.read_csv(infilePrefix, sep="\t", index_col=False)
        else:
            df = pd.read_csv("{}/GenomicFeaturesAnnotation.summary.tsv".format(resultsDir), sep="\t", index_col=False)
            df = df[df["Annotated file"] == infilePrefix]
        columns = list(df)
        columns.remove("Annotated file")
        columns.remove("Threshold")
        columns.remove("#Regions")

        ### Generate heatmap with raw numbers:
        dfPlot = df[columns].copy()
        dfPlot = dfPlot.set_index("Category")
        plt.clf()
        fig, ax = plt.subplots(figsize=(10, 4))
        ax = sns.heatmap(dfPlot, cmap="Reds", annot = True, fmt="d")#, robust=True)
        plt.xticks(rotation=45, horizontalalignment='right')
        if mode == 'plotHeatmap':
            plt.title("Genomic features annotation, raw numbers\n{}".format(infilePrefix))
        else:
            plt.title("Genomic features annotation, raw numbers; cumulative diff. categories\n{}".format(infilePrefix))
        pdf_pages.savefig(fig, bbox_inches='tight', dpi=300)

        ### Generate heatmap with percentage per row numbers:
        normalizedDf_values = []
        normalizedDf_labels = columns
        for index, row in df.iterrows():
            allRegions = int(row['#Regions'])
            category = row['Category']

            tmpList = []
            for col in columns:
                if col == 'Category':
                    tmpList.append(category)
                else:
                    if allRegions > 0:
                        tmpList.append((int(row[col])/allRegions)*100)
                    else:
                        tmpList.append(0)
            normalizedDf_values.append(tuple(tmpList))
        dfPlot = pd.DataFrame.from_records(normalizedDf_values, columns=normalizedDf_labels)
        dfPlot = dfPlot.set_index("Category")

        plt.clf()
        fig, ax = plt.subplots(figsize=(10, 4))
        ax = sns.heatmap(dfPlot, cmap="Greens", annot = True, fmt=".1f")#, robust=True)
        for t in ax.texts: t.set_text(t.get_text() + "%")
        plt.xticks(rotation=45, horizontalalignment='right')
        plt.title("Genomic features annotation, row-normalized percentage values\n{}".format(infilePrefix))
        pdf_pages.savefig(fig, bbox_inches='tight', dpi=300)

        ### Generate heatmap with percentage per row numbers:
        normalizedDf_values = []
        normalizedDf_labels = columns
        for index, row in df.iterrows():
            allRegions = int(row['#Regions'])
            category = row['Category']

            tmpList = []
            tmpValues = []
            for col in columns:
                if col == 'Category':
                    tmpList.append(category)
                else:
                    if allRegions > 0:
                        tmpValues.append(int(row[col]))
                    else:
                        tmpList.append(0)
            if allRegions > 0:
                maxVal = np.max(tmpValues)
                minVal = np.min(tmpValues)
                for val in tmpValues:
                    tmpList.append( (val-minVal)/(maxVal-minVal) )
            normalizedDf_values.append(tuple(tmpList))
        dfPlot = pd.DataFrame.from_records(normalizedDf_values, columns=normalizedDf_labels)
        dfPlot = dfPlot.set_index("Category")

        plt.clf()
        fig, ax = plt.subplots(figsize=(10, 4))
        ax = sns.heatmap(dfPlot, cmap="Blues", annot = True, fmt=".3f")#, robust=True)
        plt.xticks(rotation=45, horizontalalignment='right')
        plt.title("Genomic features annotation, row-normalized min-max values\n{}".format(infilePrefix))
        pdf_pages.savefig(fig, bbox_inches='tight', dpi=300)
    logger1.info("Heatmaps drawn for {}.".format(infilePrefix))

def getCategories(mode):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    if mode == "VOUT_format":
        description = {"Up2" : ["Up", ">2fold,FDR<0.05"],
                       "Up2NoFDR" : ["Up", ">2fold,p<0.05"],
                       "Up" : ["Up", "FDR<0.05"],
                       "UpNoFDR" : ["Up", "p<0.05"],
                       "Control" : ["Control", "Control"],
                       "DownNoFDR" : ["Down", "p<0.05"],
                       "Down" : ["Down", "FDR<0.05"],
                       "Down2NoFDR" : ["Down", ">2fold,p<0.05"],
                       "Down2" : ["Down", ">2fold,FDR<0.05"],
                       "AllRegions" : ["AllRegions", "All regions from the analysis"]}

        cumulativeCategories = {"Up2" : ["Up2"],
                                "Up2NoFDR" : ["Up2", "Up2NoFDR"],
                                "Up" : ["Up", "Up2"],
                                "UpNoFDR" : ["Up", "Up2", "Up2NoFDR", "UpNoFDR"],
                                "Down2" : ["Down2"],
                                "Down2NoFDR" : ["Down2", "Down2NoFDR"],
                                "Down" : ["Down", "Down2"],
                                "DownNoFDR" : ["Down", "Down2", "Down2NoFDR", "DownNoFDR"],
                                "Control" : ["Control"],
                                "AllRegions" : ["Down", "Down2", "Down2NoFDR", "DownNoFDR", "Control", "Up", "Up2", "Up2NoFDR", "UpNoFDR", "Other"]}
        categoriesOrder = ["Up2", "Up2NoFDR", "Up", "UpNoFDR", "Control", "DownNoFDR", "Down", "Down2NoFDR", "Down2", "AllRegions"]
        logger1.info("Mode set to {}.".format(mode))
        return description, cumulativeCategories, categoriesOrder
    elif mode == "VOUT_format_1on1":
        description = {"Up2FC" : ["Up", ">2fold"],
                       "Control" : ["Control", "Control"],
                       "Down2FC" : ["Down", ">2fold"],
                       "AllRegions" : ["AllRegions", "All regions from the analysis"]}

        cumulativeCategories = {"Up2FC" : ["Up2FC"],
                                "Down2FC" : ["Down2FC"],
                                "Control" : ["Control"],
                                "AllRegions" : ["Down2FC", "Control", "Up2FC", "Other"]}
        categoriesOrder = ["Up2FC", "Control", "Down2FC", "AllRegions"]
        logger1.info("Mode set to {}.".format(mode))
        return description, cumulativeCategories, categoriesOrder
    elif mode == "VOUT_format_meth":
        description = {"hyperDMq25" : ["Hypermethylated", "diffMeth>25,FDR<0.05"],
                       "hyperDMp25" : ["Hypermethylated", "diffMeth>25,p<0.05"],
                       "hyperDM25" : ["Hypermethylated", "diffMeth>25"],
                       "Control" : ["Control", "Control"],
                       "hypoDM25" : ["Hypomethylated", "diffMeth<-25"],
                       "hypoDMp25" : ["Hypomethylated", "diffMeth<-25,p<0.05"],
                       "hypoDMq25" : ["Hypomethylated", "diffMeth<-25,FDR<0.05"],
                       "AllRegions" : ["AllRegions", "All regions from the analysis"]}

        cumulativeCategories = {"hyperDMq25" : ["hyperDMq25"],
                                "hyperDMp25" : ["hyperDMq25", "hyperDMp25"],
                                "hyperDM25" : ["hyperDM25", "hyperDMq25", "hyperDMp25"],
                                "hypoDMq25" : ["hypoDMq25"],
                                "hypoDMp25" : ["hypoDMq25", "hypoDMp25"],
                                "hypoDM25" : ["hypoDM25", "hypoDMq25", "hypoDMp25"],
                                "Control" : ["Control"],
                                "AllRegions" : ["hyperDMq25", "hyperDMp25", "hyperDM25", "Control", "hypoDM25", "hypoDMp25", "hypoDMq25", "Other"]}
        categoriesOrder = ["hyperDMq25", "hyperDMp25", "hyperDM25", "Control", "hypoDM25", "hypoDMp25", "hypoDMq25", "AllRegions"]
        logger1.info("Mode set to {}.".format(mode))
        return description, cumulativeCategories, categoriesOrder
    elif mode == "VOUT_format_meth_1on1":
        description = {"hyperDM25" : ["Hypermethylated", "diffMeth>25"],
                       "Control" : ["Control", "Control"],
                       "hypoDM25" : ["Hypomethylated", "diffMeth<-25"],
                       "AllRegions" : ["AllRegions", "All regions from the analysis"]}

        cumulativeCategories = {"hyperDM25" : ["hyperDM25"],
                                "hypoDM25" : ["hypoDM25"],
                                "Control" : ["Control"],
                                "AllRegions" : ["hyperDM25", "Control", "hypoDM25", "Other"]}
        categoriesOrder = ["hyperDM25", "Control", "hypoDM25", "AllRegions"]
        logger1.info("Mode set to {}.".format(mode))
        return description, cumulativeCategories, categoriesOrder
    elif mode == "BED_format":
        description = {"BED_format" : ["BED_format", "all regions from BED file"]}
        cumulativeCategories = {"BED_format" : ["BED_format"]}
        categoriesOrder = ["BED_format"]
        logger1.info("Mode set to {}.".format(mode))
        return description, cumulativeCategories, categoriesOrder
    else:
        logger1.error("Unknown mode = {}. program was aborted.".format(mode))
        exit()

def main():
    analysisPrefix, genome, annoPath, infileName, columnHeader, features, featureLabels, tmpDir, mode = parseArgs()

    if mode in [ 'auto', 'VOUT_format_1on1', 'VOUT_format_meth_1on1', 'VOUT_format_meth', "BED_format", "VOUT_format" ]:
        ### create the directory to back up the *anno files:
        Path(tmpDir).mkdir(parents=True, exist_ok=True)

        ### create the directory to back up the *anno files:
        resultsDir = tmpDir.replace("tmp_","")
        Path(resultsDir).mkdir(parents=True, exist_ok=True)

        ### import input file as data frame:
        df = pd.read_csv(infileName, sep='\t', index_col=False)
        ori_df_columns = [ rr for rr in df.columns ]
        if mode == 'auto':
            if infileName.endswith(".bed.anno") or infileName.endswith(".narrowPeak.anno") or infileName.endswith(".broadPeak.anno"):
                mode = "BED_format"
            else:
                mode = "VOUT_format"
        if not "Region" in df.columns:
            df["Region"] = df[['chr','start','end']].apply(lambda x: "{}:{}-{}".format(x[0], x[1], x[2]), axis=1)
        #from pdb import set_trace; set_trace()
        if not 'Regulation' in df.columns:
            df['Regulation'] = df['Region'].apply(lambda x: "BED_format")
        description, cumulativeCategories, categoriesOrder = getCategories(mode)

        ### read in the genomic features:
        featuresDict = {}
        labelsDict = {}
        for feature, label in zip(features, featureLabels):
            labelsDict[feature] = label
            file = os.path.join(annoPath, genome, feature)
            if os.path.isfile(file):
                featuresDict[feature] = BedTool(file)
                logging.info("{} annotation file loaded successfully.".format(file))
            else:
                logging.error("{} annotation file does not exist.".format(file))

        ### check if the file was not already annotated, if yes, abort:
        columns = set(list(df))
        if columnHeader in columns:
            logging.warning("{} file was already annotated, as emphasized by the presence of '{}' column. Skipping the annotation part.".format(infileName, columnHeader))
        else:
            ### annotate features:
            regionsAnno = annotateFeatures(df, features, featuresDict, labelsDict)

            df[columnHeader] = df['Region'].apply(lambda region: regionsAnno[region] if region in regionsAnno else False) ### adding exception handling here, because sometimes when for example the regions are in some alternative chromosome (e.g. chr10_GL383545v1_alt), which is not in the reference annotations, then its impossible to align them to genomic contexts, and its also not correct to assign them to "intergenic" either. Those cases will have "False" status.

            ### move original *anno file to tmpDir:
            command = "mv {0} {1}/{0}.raw_bcp".format(os.path.basename(infileName), tmpDir)
            subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout.read()

            ### save the annotated file:
            df.to_csv("{}".format(os.path.basename(infileName)), sep='\t', index=False)

        ### Finalize summary tables and plots:
        for category in categoriesOrder:
            ### Generate summary file:
            sumDict, noFeatures = generateSummary(df[df['Regulation'].isin(cumulativeCategories[category])].copy(), columnHeader, os.path.basename(infileName), labelsDict, features, analysisPrefix, resultsDir, tmpDir, category, description)

            ### Draw plots:
            barPlot(os.path.basename(infileName), resultsDir, sumDict, featureLabels, category, description, noFeatures, tmpDir)
            piePlot(os.path.basename(infileName), resultsDir, sumDict, featureLabels, category, description, noFeatures, tmpDir)

        ### Generate heatmap:
        if 'Regulation' in ori_df_columns:
            generateHeatmap(os.path.basename(infileName), resultsDir, mode)
        else:
            logging.info("Heatmap not drawn for {} in {} mode.".format(os.path.basename(infileName), mode))
    elif mode == 'plotHeatmap':
        generateHeatmap(os.path.basename(infileName), None, mode)
    else:
        logging.error("An unknown mode setting = {}.".format(mode))

    logging.info("All done, thank you.")

main()
