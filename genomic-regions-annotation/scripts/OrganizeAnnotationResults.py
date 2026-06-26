#!/usr/bin/env python
# coding: utf-8

##########################################################################################
#
# Copyright (c) 2020-~ Wojciech Rosikiewicz && St Jude
# This source code is released for free distribution under the terms of the CreativeCommons BY-NC-SA 4.0 International License
#*Author: Wojciech Rosikiewicz < rosikiewicz [at] gmail DOT com >
# 
##########################################################################################

import os
import shutil
import glob
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import math
import logging
import inspect
import matplotlib.patheffects as path_effects
import matplotlib.patches as patches

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from adjustText import adjust_text

import matplotlib
matplotlib.use('Agg')

import random
from collections import OrderedDict 

import plotly.express as px

"""
Usage:
python OrganizeAnnotationResults.py

Note, this sciript is intended to use from within the directory where the *.voom|bed.anno
files are located. These files must have been previously created using voom2anno.sh
script, availible here: https://git.stjude.org/users/bxu2/repos/sjcab_std_report/browse/sjcab_custom_atac

Compare Regulation    Threshold       #Region #Gene_Promoter  #Gene_Enhancer
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Up      >2fold,p<0.05   152     24      81
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Up      >2fold,passed_FDR_0.05  152     24      81
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Down    >2fold,p<0.05   201     15      110
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Down    >2fold,passed_FDR_0.05  201     15      110

Compare Regulation    CodeName  Threshold       #Region #Gene_Promoter  #Gene_Enhancer
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Up      Up2     >2fold,p<0.05   152     24      81
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Up      Up2NoFDR    >2fold,passed_FDR_0.05  152     24      81
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Up      Up    <2fold,p<0.05  x     x      x
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Down    Down2   >2fold,p<0.05   201     15      110
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Down    Down2NoFDR    >2fold,passed_FDR_0.05  201     15      110
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Down    Down    <2fold,p<0.05  x     x      x
CHIP.Rub.H3K27Ac.Zymo.KOvsWT    Control    Control    Control  x     x      x

Up2NoFDR == Down2NoFDR ==category== >2fold,p<0.05
Up2 == Down2 ==category== >2fold,passed_FDR_0.05

=============

You may find the results of the differential chromatin accessibility analysis for SRM182570 data under to following directory:
/research/rgs01/project_space/greengrp/Epigenetic_Macrophages/common/cab/ATAC/GREEN-182570-ATACSEQ_DifferentialAnalysis

The following comparisons were made:
RubKO vs. WT; prefix CAB-7_SRM182570.RubKO_vs_WT
RubKO_engulf vs. WT_engulf; prefix CAB-7_SRM182570.RubKO_engulf_vs_WT_engulf
RubKO_engulf vs. RubKO; prefix CAB-7_SRM182570.RubKO_engulf_vs_RubKO
WT_engulf vs. WT; prefix CAB-7_SRM182570.WT_engulf_vs_WT

Under the abovementioned directory you will find the following types of files:
summaryTable.tsv – this file contains a summary of the number of differentially accessible regions, annotated with promoter regions and enhancers in studied contexts (e.g. RubKO vs. WT)

annotations.xlsx – this excel file contains the detailed annotation and classification of all identified regions. Each of your comparisons is inside of separate spredsheet. Each spreadsheet is also individually accessible through *.anno.gz files. Note, that each region is here classified to one of 9 categories described below for *.pdf files.

*.pdf – a boxplot showing the signal levels (measured with FPKM), among the regions classified into one of 9 categories, described in a decreasing level of stringency:
    1. Down2 and Up2 – regions with decreased or increased signal,  respectively; fold change > 2 and FDR <= 0.05
    2. Down2NoFDR and Up2NoFDR – regions with decreased or increased signal,  respectively; fold change > 2 and p-value <= 0.05
    3. Down and Up – regions with decreased or increased signal,  respectively; FDR <= 0.05
    4. DownNoFDR and UpNoFDR – regions with decreased or increased signal,  respectively; p-value <= 0.05
    5. Control – all remaining peaks
Note: *.test.pdf will display only the samples from the actual comparison (e.g. 4 samples for RubKO vs. WT), while *.all.pdf has the results for all 8 samples.

*.gmt – two files listing gene names per condition, category and threshold (e.g. all genes with significantly increased accessibility (Up2) within promoter regions etc.). There are two gmt files because one is listing gene names, while the other is listing Gencode ids. These files might become handy to directly run GSEA on them if RNA-Seq or microarrays would be available for the project, for example to see If the expression of genes with increased chromatin accessibility in promoters is biased toward upregulation in KO phenotype, etc.
"""

def configureLogging(analysisPrefix):
    # https://stackoverflow.com/questions/9321741/printing-to-screen-and-writing-to-a-file-at-the-same-time
    logging.basicConfig(level = logging.INFO,
                        format = '###\t[%(asctime)s] %(levelname)s %(name)s: %(message)s',
                        handlers = [logging.FileHandler('{}.log'.format(analysisPrefix)), logging.StreamHandler()],
                        datefmt='%y-%m-%d %H:%M:%S')
                        
def uniqueOnly(l):
    d = {}
    for elem in l:
        d[elem] = 1
    return list(d.keys())

def organizeOutputList(inDict):
    maxLen = 0
    fields = list(inDict.keys())
    fields.sort()
    for elem in fields:
        if maxLen < len(inDict[elem]):
            maxLen = len(inDict[elem])
    for elem in fields:
        tmp = [""]*maxLen
        for gene, field, idx in zip(inDict[elem], tmp, range(0,maxLen+1,1)):
            tmp[idx] = gene
        inDict[elem] = tmp
    return inDict, fields

def MAplot(infileName):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    size = 10

    plt.clf()
    fig, ax = plt.subplots()
    fig.set_size_inches(size, size)

    df = pd.read_csv(infileName, sep = "\t")

    significant_FDR0 = df[(df["q.value"] <= 10**0)]
    significant_Diff2 = df[(df["Regulation"] == "Up2") | (df["Regulation"] == "Down2")]
    significant_Diff2NoFDR = df[(df["Regulation"] == "Up2NoFDR") | (df["Regulation"] == "Down2NoFDR")]
    significant_Diff = df[(df["Regulation"] == "Up") | (df["Regulation"] == "Down")]
    significant_DiffNoFDR = df[(df["Regulation"] == "UpNoFDR") | (df["Regulation"] == "DownNoFDR")]

    #https://www.color-hex.com/color-palette/20901
    color1 = "#B7B7B7"
    color2 = "#e7d87d"
    color3 = "#dd9f40"
    color4 = "#df761e"
    color5 = "#b01111"

    ax = sns.scatterplot(x="log2AveExpr", y="log2FC", data=df, s=3, color=color1, alpha=0.5, edgecolor="none")
    ax = sns.scatterplot(x="log2AveExpr", y="log2FC", data=significant_DiffNoFDR, color=color2, alpha=0.7, s=7, edgecolor="none")
    ax = sns.scatterplot(x="log2AveExpr", y="log2FC", data=significant_Diff, color=color3, alpha=0.7, s=8, edgecolor="none")
    ax = sns.scatterplot(x="log2AveExpr", y="log2FC", data=significant_Diff2NoFDR, color=color4, alpha=0.7, s=9, edgecolor="none")
    ax = sns.scatterplot(x="log2AveExpr", y="log2FC", data=significant_Diff2, color=color5, alpha=1, s=10, edgecolor="none")

    plt.plot(np.linspace(-20,120,1000), [0]*1000, '--', color='black', linewidth=1)
    plt.plot(np.linspace(-20,120,1000), [np.log2(2)]*1000, ':', color='black', linewidth=1)
    plt.plot(np.linspace(-20,120,1000), [-np.log2(2)]*1000, ':', color='black', linewidth=1)
    ymax = abs(max(df["log2FC"].min(), df["log2FC"].max(), key=abs))
    
    ax.set(xlim=(math.floor(np.min(df["log2AveExpr"])), math.ceil(np.max(df["log2AveExpr"]))) , ylim=(-ymax,ymax))

    ## Construct a legend:
    left, width = .25, .5
    bottom, height = .25, .5
    right = left + width
    top = bottom + height
    
    # Rectangles drawn on the figure absolute coords, not axes (based on https://stackoverflow.com/questions/21535294/matplotlib-add-rectangle-to-figure-not-to-axes)
    rctH = 0.013 # rectangle height
    rctS = 0.25 # first (top) rectangle position
    rctG = 0.0195 # gap between rectangles
    fig.patches.extend([plt.Rectangle((0.685,rctS-rctG*0),rctH,rctH, fill=True, color=color2, alpha=1, zorder=1000, transform=fig.transFigure, figure=fig)])
    fig.patches.extend([plt.Rectangle((0.685,rctS-rctG*1),rctH,rctH, fill=True, color=color3, alpha=1, zorder=1000, transform=fig.transFigure, figure=fig)])
    fig.patches.extend([plt.Rectangle((0.685,rctS-rctG*2),rctH,rctH, fill=True, color=color4, alpha=1, zorder=1000, transform=fig.transFigure, figure=fig)])
    fig.patches.extend([plt.Rectangle((0.685,rctS-rctG*3),rctH,rctH, fill=True, color=color5, alpha=1, zorder=1000, transform=fig.transFigure, figure=fig)])
    
    # classical patches based on the figure coordinates:
    # ax.add_patch(patches.Rectangle((7.3, -5.2), 0.5, 0.5, fill=True, color="#ffce00") )
    # ax.add_patch(patches.Rectangle((7.3, -5.9), 0.5, 0.5, fill=True, color="#ff8d00") )
    # ax.add_patch(patches.Rectangle((7.3, -6.6), 0.5, 0.5, fill=True, color="#ff3300") )
    # ax.add_patch(patches.Rectangle((7.3, -7.3), 0.5, 0.5, fill=True, color="#000000") )

    ax.text(0.75, 0.20 * (bottom + top), 'p-value<0.05\nFDR<0.05\nFC>2; p-value<0.05\nFC>2; FDR<0.05',
            horizontalalignment='left',
            verticalalignment='top',
            transform=ax.transAxes,
            fontsize=13)

    plt.savefig("{}.MAplot.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
    plt.savefig("{}.MAplot.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
    plt.close()
    logging.info("MA plot drawn for {}".format(infileName))

def barPlot(infileName, description, mode):
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    df = pd.read_csv(infileName, sep = "\t")
    color1 = "#B7B7B7"
    color2 = "#e7d87d"
    color3 = "#dd9f40"
    color4 = "#df761e"
    color5 = "#b01111"
    colors = [color5, color4, color3, color2, color1, color2, color3, color4, color5] # Up2, ---to--- Down2
    
    if mode == 'VOUT_format':
        summarylist = []
        for cat in list(description.keys()):
            summarylist.append([cat, len(df[df.Regulation == cat])])
        summarydf = pd.DataFrame(summarylist, columns=['Regulation', 'Number of regions'])
        plt.clf()
        fig, ax = plt.subplots(figsize=(7, 4))
        ax = sns.barplot(x="Number of regions", y="Regulation", data=summarydf, palette = colors)#, color="#D44D4D")
        plt.savefig("{}.bar.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.savefig("{}.bar.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.close()
        logging.info("Bar plot drawn for {}".format(infileName))
    elif mode == 'BED_format':
        logging.info("'BED_format' not yet supported. Bar plot NOT drawn for {}".format(infileName))

def reformatDF(df):
    replaced_na = df.replace([np.inf, -np.inf], np.nan)
    mask_na = 0
    replaced_na = replaced_na.fillna(mask_na)
    mask = df.isnull()
    return mask, mask_na, replaced_na

def drawHeatmap(infileName, description, mode, expressionsPrefix = ["FPKM.","RPKM.","CPM.","RAW."], colorMap = "bwr"):
    """
    row normalization - z-score - is used: https://seaborn.pydata.org/generated/seaborn.clustermap.html
    """
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    df = pd.read_csv(infileName, sep = "\t")
    df = df.sort_values('log2FC',ascending=False)
    
    ## Get list of columns with enrichment values:
    for prefix in expressionsPrefix:
        columns = [i for i in list(df) if i.startswith(prefix)]
        if len(columns) > 0:
            break
#     columns = [i for i in list(df) if i.startswith(expressionsPrefix[0])]# + ["Regulation"]
#     if len(columns) == 0:
#         columns = [i for i in list(df) if i.startswith(expressionsPrefix[1])]
#         if len(columns) == 0:
#             columns = [i for i in list(df) if i.startswith(expressionsPrefix[2])]
    
    if mode == 'VOUT_format' and len(columns) > 0:
        ### Plot top 100 Up and top 100 down regions (sorted by log2FC):
        pltDF = df.iloc[np.r_[0:100, -100:0]]
        mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
        plt.clf()
        ax = sns.clustermap(replaced_na, cmap=colorMap, yticklabels=0, col_cluster=1, mask=mask != mask_na, figsize=(10,10), z_score=0, method="ward").fig.suptitle('Top 100 and bottom 100 regions (ordered by Log2FC); Cumulative number\nData source:{}'.format(infileName)) 
        plt.savefig("{}.Heatmap.Top100.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.savefig("{}.Heatmap.Top100.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.close()
        
        ### Plot differentials from various categories:
        #1. Up2 and Down2
        pltDF = df[( ( (df.log2FC >= np.log2(2)) | (df.log2FC <= -np.log2(2)) ) & (df["q.value"] <= 0.05))]
        if len(pltDF) >= 2:
            upNo = len(df[((df.log2FC >= np.log2(2)) & (df["q.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(2)) & (df["q.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            ax = sns.clustermap(replaced_na, cmap=colorMap, yticklabels=0, col_cluster=1, mask=mask != mask_na, figsize=(10,10), z_score=0, method="ward").fig.suptitle('{} Up- and {} Down-regulated regions (>2fold,FDR<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName)) 
            plt.savefig("{}.Heatmap.Up2_Down2.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.Heatmap.Up2_Down2.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 2 regions were present for 'Up2_Down2' category (file: {}), heatmap is not plotted.".format(infileName))
            
        #2. Up2NoFDR and Down2NoFDR
        pltDF = df[( ( (df.log2FC >= np.log2(2)) | (df.log2FC <= -np.log2(2)) ) & (df["p.value"] <= 0.05))]
        if len(pltDF) >= 2:
            upNo = len(df[((df.log2FC >= np.log2(2)) & (df["p.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(2)) & (df["p.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            plt.clf()
            ax = sns.clustermap(replaced_na, cmap=colorMap, yticklabels=0, col_cluster=1, mask=mask != mask_na, figsize=(10,10), z_score=0, method="ward").fig.suptitle('{} Up- and {} Down-regulated regions (>2fold,p-value<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName)) 
            plt.savefig("{}.Heatmap.Up2NoFDR_Down2NoFDR.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.Heatmap.Up2NoFDR_Down2NoFDR.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 2 regions were present for 'Up2NoFDR_Down2NoFDR' category (file: {}), heatmap is not plotted.".format(infileName))
            
        #3. Up and Down
        pltDF = df[( (df["q.value"] <= 0.05))]
        if len(pltDF) >= 2:
            upNo = len(df[((df.log2FC >= np.log2(1)) & (df["q.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(1)) & (df["q.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            plt.clf()
            ax = sns.clustermap(replaced_na, cmap=colorMap, yticklabels=0, col_cluster=1, mask=mask != mask_na, figsize=(10,10), z_score=0, method="ward").fig.suptitle('{} Up- and {} Down-regulated regions (FDR<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName)) 
            plt.savefig("{}.Heatmap.Up_Down.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.Heatmap.Up_Down.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 2 regions were present for 'Up_Down' category (file: {}), heatmap is not plotted.".format(infileName))
            
        #4. UpNoFDR and DownNoFDR
        pltDF = df[( (df["p.value"] <= 0.05))]
        if len(pltDF) >= 2:
            upNo = len(df[((df.log2FC >= np.log2(1)) & (df["p.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(1)) & (df["p.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            plt.clf()
            ax = sns.clustermap(replaced_na, cmap=colorMap, yticklabels=0, col_cluster=1, mask=mask != mask_na, figsize=(10,10), z_score=0, method="ward").fig.suptitle('{} Up- and {} Down-regulated regions (p-value<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName)) 
            plt.savefig("{}.Heatmap.UpNoFDR_DownNoFDR.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.Heatmap.UpNoFDR_DownNoFDR.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 2 regions were present for 'UpNoFDR_DownNoFDR' category (file: {}), heatmap is not plotted.".format(infileName))
        
        logging.info("Heatmaps drawn for {}".format(infileName))
        
    elif mode == 'BED_format':
        logging.info("'BED_format' not yet supported. Heatmaps NOT drawn for {}".format(infileName))
    elif len(columns) == 0:
        logging.warning("No Expression level columns identified (file: {}), heatmap is not plotted.".format(infileName))

def label_point(x, y, val, ax):
    a = pd.concat({'x': x, 'y': y, 'val': val}, axis=1)
    texts = []
    for i, point in a.iterrows():
        texts.append(plt.text(point['x'], point['y'], str(point['val']), size=8))
    adjust_text(texts, arrowprops=dict(arrowstyle="-", color='k', lw=0.5))

def plotPCA(infileName, description, mode, expressionsPrefix = ["FPKM.","RPKM.","CPM.","RAW."], colorMap = "bwr"):
    """
    important read for PCA from scikit-learn: https://towardsdatascience.com/pca-using-python-scikit-learn-e653f8989e60
    """
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)
    df = pd.read_csv(infileName, sep = "\t")
    df = df.sort_values('log2FC',ascending=False)
    
    ## Get list of columns with enrichment values:
    for prefix in expressionsPrefix:
        columns = [i for i in list(df) if i.startswith(prefix)]# + ["Regulation"]
        columns_clean = [i.replace(prefix,"") for i in list(df) if i.startswith(prefix)]
        if len(columns) > 0:
            break
#     columns = [i for i in list(df) if i.startswith(expressionsPrefix[0])]# + ["Regulation"]
#     columns_clean = [i.replace(expressionsPrefix[0],"") for i in list(df) if i.startswith(expressionsPrefix[0])]
#     if len(columns) == 0:
#         columns = [i for i in list(df) if i.startswith(expressionsPrefix[1])]
#         columns_clean = [i.replace(expressionsPrefix[1],"") for i in list(df) if i.startswith(expressionsPrefix[1])]
#         if len(columns) == 0:
#             columns = [i for i in list(df) if i.startswith(expressionsPrefix[2])]
#             columns_clean = [i.replace(expressionsPrefix[2],"") for i in list(df) if i.startswith(expressionsPrefix[2])]
    
    if mode == 'VOUT_format':
        ### Plot top 100 Up and top 100 down regions (sorted by log2FC):
        pltDF = df.iloc[np.r_[0:100, -100:0]]
        print(columns)
        mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
        x = StandardScaler().fit_transform(replaced_na)
        y = np.rot90(x)
        
        plt.clf()
        fig = plt.figure(figsize = (6, 6))
        ax = fig.add_subplot(1,1,1) 
        pca = PCA(n_components=2)
        principalComponents = pca.fit_transform(y)
        explained_variance = pca.explained_variance_ratio_
        principalDf = pd.DataFrame(data = principalComponents, columns = ['principal component 1', 'principal component 2'])
        pcaf = ax.scatter(principalDf['principal component 1'], principalDf['principal component 2'], s = 20)
        label_point(principalDf['principal component 1'], principalDf['principal component 2'], pd.Series(columns_clean), plt.gca())
        plt.xlabel('PC 1 ({0:2.1f}% variance)'.format(explained_variance[0]*100))
        plt.ylabel('PC 2 ({0:2.1f}% variance)'.format(explained_variance[1]*100))
        plt.title('PCA based on Top 100 and bottom 100 regions (ordered by Log2FC); Cumulative number\nData source:{}'.format(infileName))
        plt.savefig("{}.PCA.Top100.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.savefig("{}.PCA.Top100.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.close()
        
        ### Plot differentials from various categories:
        #1. Up2 and Down2
        pltDF = df[( ( (df.log2FC >= np.log2(2)) | (df.log2FC <= -np.log2(2)) ) & (df["q.value"] <= 0.05))]
        if len(pltDF) >= 3:
            upNo = len(df[((df.log2FC >= np.log2(2)) & (df["q.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(2)) & (df["q.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            x = StandardScaler().fit_transform(replaced_na)
            y = np.rot90(x)
        
            plt.clf()
            fig = plt.figure(figsize = (6, 6))
            ax = fig.add_subplot(1,1,1) 
            pca = PCA(n_components=2)
            principalComponents = pca.fit_transform(y)
            explained_variance = pca.explained_variance_ratio_
            principalDf = pd.DataFrame(data = principalComponents, columns = ['principal component 1', 'principal component 2'])
            pcaf = ax.scatter(principalDf['principal component 1'], principalDf['principal component 2'], s = 20)
            label_point(principalDf['principal component 1'], principalDf['principal component 2'], pd.Series(columns_clean), plt.gca())
            plt.xlabel('PC 1 ({0:2.1f}% variance)'.format(explained_variance[0]*100))
            plt.ylabel('PC 2 ({0:2.1f}% variance)'.format(explained_variance[1]*100))
            plt.title('PCA based on {} Up- and {} Down-regulated regions (>2fold,FDR<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName))
            plt.savefig("{}.PCA.Up2_Down2.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.PCA.Up2_Down2.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 3 regions were present for 'Up2_Down2' category (file: {}), PCA is not plotted.".format(infileName))
        
        #2. Up2NoFDR and Down2NoFDR
        pltDF = df[( ( (df.log2FC >= np.log2(2)) | (df.log2FC <= -np.log2(2)) ) & (df["p.value"] <= 0.05))]
        if len(pltDF) >= 3:
            upNo = len(df[((df.log2FC >= np.log2(2)) & (df["p.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(2)) & (df["p.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            x = StandardScaler().fit_transform(replaced_na)
            y = np.rot90(x)
        
            fig = plt.figure(figsize = (6, 6))
            ax = fig.add_subplot(1,1,1) 
            pca = PCA(n_components=2)
            principalComponents = pca.fit_transform(y)
            explained_variance = pca.explained_variance_ratio_
            principalDf = pd.DataFrame(data = principalComponents, columns = ['principal component 1', 'principal component 2'])
            pcaf = ax.scatter(principalDf['principal component 1'], principalDf['principal component 2'], s = 20)
            label_point(principalDf['principal component 1'], principalDf['principal component 2'], pd.Series(columns_clean), plt.gca())
            plt.xlabel('PC 1 ({0:2.1f}% variance)'.format(explained_variance[0]*100))
            plt.ylabel('PC 2 ({0:2.1f}% variance)'.format(explained_variance[1]*100))
            plt.title('PCA based on {} Up- and {} Down-regulated regions (>2fold,p-value<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName))
            plt.savefig("{}.PCA.Up2NoFDR_Down2NoFDR.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.PCA.Up2NoFDR_Down2NoFDR.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 3 regions were present for 'Up2NoFDR_Down2NoFDR' category (file: {}), PCA is not plotted.".format(infileName))
            
        #3. Up and Down
        pltDF = df[( (df["q.value"] <= 0.05))]
        if len(pltDF) >= 3:
            upNo = len(df[((df.log2FC >= np.log2(1)) & (df["q.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(1)) & (df["q.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            x = StandardScaler().fit_transform(replaced_na)
            y = np.rot90(x)
        
            plt.clf()
            fig = plt.figure(figsize = (6, 6))
            ax = fig.add_subplot(1,1,1) 
            pca = PCA(n_components=2)
            principalComponents = pca.fit_transform(y)
            explained_variance = pca.explained_variance_ratio_
            principalDf = pd.DataFrame(data = principalComponents, columns = ['principal component 1', 'principal component 2'])
            pcaf = ax.scatter(principalDf['principal component 1'], principalDf['principal component 2'], s = 20)
            label_point(principalDf['principal component 1'], principalDf['principal component 2'], pd.Series(columns_clean), plt.gca())
            plt.xlabel('PC 1 ({0:2.1f}% variance)'.format(explained_variance[0]*100))
            plt.ylabel('PC 2 ({0:2.1f}% variance)'.format(explained_variance[1]*100))
            plt.title('PCA based on {} Up- and {} Down-regulated regions (FDR<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName))
            plt.savefig("{}.PCA.Up_Down.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.PCA.Up_Down.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 3 regions were present for 'Up_Down' category (file: {}), PCA is not plotted.".format(infileName))
            
        #4. UpNoFDR and DownNoFDR
        pltDF = df[( (df["p.value"] <= 0.05))]
        if len(pltDF) >= 3:
            upNo = len(df[((df.log2FC >= np.log2(1)) & (df["p.value"] <= 0.05))])
            downNo = len(df[((df.log2FC <= -np.log2(1)) & (df["p.value"] <= 0.05))])
            mask, mask_na, replaced_na = reformatDF(pltDF[columns].copy())
            x = StandardScaler().fit_transform(replaced_na)
            y = np.rot90(x)
            
            plt.clf()
            fig = plt.figure(figsize = (6, 6))
            ax = fig.add_subplot(1,1,1) 
            pca = PCA(n_components=2)
            principalComponents = pca.fit_transform(y)
            explained_variance = pca.explained_variance_ratio_
            principalDf = pd.DataFrame(data = principalComponents, columns = ['principal component 1', 'principal component 2'])
            pcaf = ax.scatter(principalDf['principal component 1'], principalDf['principal component 2'], s = 20)
            label_point(principalDf['principal component 1'], principalDf['principal component 2'], pd.Series(columns_clean), plt.gca())
            plt.xlabel('PC 1 ({0:2.1f}% variance)'.format(explained_variance[0]*100))
            plt.ylabel('PC 2 ({0:2.1f}% variance)'.format(explained_variance[1]*100))
            plt.title('PCA based on {} Up- and {} Down-regulated regions (p-value<0.05); Cumulative number\nData source:{}'.format(upNo, downNo, infileName))
            plt.savefig("{}.PCA.UpNoFDR_DownNoFDR.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.savefig("{}.PCA.UpNoFDR_DownNoFDR.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
            plt.close()
        else:
            logging.warning("Less than 3 regions were present for 'UpNoFDR_DownNoFDR' category (file: {}), PCA is not plotted.".format(infileName))

        logging.info("PCA plots drawn for {}".format(infileName))
        
    elif mode == 'BED_format':
        logging.info("'BED_format' not yet supported. Heatmaps NOT drawn for {}".format(infileName))
    elif len(columns) == 0:
        logging.warning("No Expression level columns identified (file: {}), heatmap is not plotted.".format(infileName))

#def plotVolcano(fig, ax, figPos, infileName, genesOfInterest, title_text, markGenes = False, log10Cutt_line = -np.log10(0.05), log2Cutt_line = np.log2(2), absMaxY = 17, absMaxX = 10, size = 10): 
def plotVolcano(infileName, description, mode):
#     markedGenesSuffix = ""
#     genes_cat1 = importTXTGenes(genesOfInterest)
    
    grey = "#B7B7B7" # grey
#     color2 = "#e7d87d"
#     color3 = "#dd9f40"
#     color4 = "#df761e"
#     color5 = "#b01111"
    black = "#000000" # black
    blue = "#107baf"
    log10Cutt_line = -np.log10(0.05)
    log2Cutt_line = np.log2(2)
    
    if mode == 'VOUT_format':
        df = pd.read_csv(infileName, sep = "\t")
        df['-log10(FDR)'] = df['q.value'].apply(lambda val: -np.log10(float(val)) if -np.log10(float(val)) < 100 else 100)
        df['-log10(p-value)'] = df['p.value'].apply(lambda val: -np.log10(float(val)) if -np.log10(float(val)) < 100 else 100)
        dfPlot = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['-log10(p-value)'], how="all")
        absMaxX = abs(max(df["log2FC"].min(), df["log2FC"].max(), key=abs))
        absMaxX = math.ceil(absMaxX + absMaxX*0.1)
        absMaxY = dfPlot["-log10(p-value)"].max()
        
        absMaxY = math.ceil(absMaxY + absMaxY*0.1)
        
        #significant_FDR0 = df[(df["q.value"] <= 10**0)]
        significant_Diff2 = df[(df["Regulation"] == "Up2") | (df["Regulation"] == "Down2")]
        significant_Diff2NoFDR = df[(df["Regulation"] == "Up2NoFDR") | (df["Regulation"] == "Down2NoFDR") | (df["Regulation"] == "Up2") | (df["Regulation"] == "Down2")]
        significant_Diff = df[(df["Regulation"] == "Up2") | (df["Regulation"] == "Down2") | (df["Regulation"] == "Up") | (df["Regulation"] == "Down")]
        significant_DiffNoFDR = df[(df["Regulation"] == "UpNoFDR") | (df["Regulation"] == "DownNoFDR") | (df["Regulation"] == "Up2NoFDR") | (df["Regulation"] == "Down2NoFDR") | (df["Regulation"] == "Up") | (df["Regulation"] == "Down") | (df["Regulation"] == "Up2") | (df["Regulation"] == "Down2")]

    
        fig, ax = plt.subplots()
        fig.set_size_inches(20, 5)
    
        
        ### Plot category Down2 and Up2:
        plt.subplot(141)
        ax = sns.scatterplot(x="log2FC", y="-log10(FDR)", data=df, s=3, color=grey, alpha=0.7, edgecolor="none")
        ax = sns.scatterplot(x="log2FC", y="-log10(FDR)", data=significant_Diff2, s=5, color=black, alpha=1, edgecolor="none")
        
        plt.plot(np.linspace(-1000,1000,1000), [log10Cutt_line]*1000, '--', color='black', linewidth=1)
        plt.plot([-log2Cutt_line]*1000, np.linspace(-1000,1000,1000), '--', color='black', linewidth=1)
        plt.plot([log2Cutt_line]*1000, np.linspace(-1000,1000,1000), '--', color='black', linewidth=1)

        ax.set_xlim([-absMaxX, absMaxX])
        ax.set_ylim([-0.1, absMaxY])

        ### Add text over the plot:
        left, width = .25, .5
        bottom, height = .25, .5
        right = left + width
        top = bottom + height

        N = len(df[df["Regulation"] == "Down2"])
        ax.text(0.01, 0.99 * (bottom + top), 'Down: {}'.format(N), horizontalalignment='left', verticalalignment='top', transform=ax.transAxes, fontsize=13)

        N = len(df[df["Regulation"] == "Up2"])
        ax.text(0.99, 0.99 * (bottom + top), 'Up: {}'.format(N), horizontalalignment='right', verticalalignment='top', transform=ax.transAxes, fontsize=13)
        
        plt.title("Up2 and Down2\n>2fold,FDR<0.05", fontsize=13)
        
        ### Plot category Down2NoFDR and Up2NoFDR:
        plt.subplot(142)
        ax = sns.scatterplot(x="log2FC", y="-log10(p-value)", data=df, s=3, color=grey, alpha=0.7, edgecolor="none")
        ax = sns.scatterplot(x="log2FC", y="-log10(p-value)", data=significant_Diff2NoFDR, s=5, color=black, alpha=1, edgecolor="none")
        
        plt.plot(np.linspace(-1000,1000,1000), [log10Cutt_line]*1000, '--', color='black', linewidth=1)
        plt.plot([-log2Cutt_line]*1000, np.linspace(-1000,1000,1000), '--', color='black', linewidth=1)
        plt.plot([log2Cutt_line]*1000, np.linspace(-1000,1000,1000), '--', color='black', linewidth=1)

        ax.set_xlim([-absMaxX, absMaxX])
        ax.set_ylim([-0.1, absMaxY])

        ### Add text over the plot:
        left, width = .25, .5
        bottom, height = .25, .5
        right = left + width
        top = bottom + height

        N = len(df[(df["Regulation"] == "Down2NoFDR") | (df["Regulation"] == "Down2")])
        ax.text(0.01, 0.99 * (bottom + top), 'Down: {}'.format(N), horizontalalignment='left', verticalalignment='top', transform=ax.transAxes, fontsize=13)

        N = len(df[(df["Regulation"] == "Up2NoFDR") | (df["Regulation"] == "Up2")])
        ax.text(0.99, 0.99 * (bottom + top), 'Up: {}'.format(N), horizontalalignment='right', verticalalignment='top', transform=ax.transAxes, fontsize=13)
        
        plt.title("Up2NoFDR and Down2NoFDR\n>2fold,p-value<0.05; Cumulative numbers", fontsize=13)
        
        
        ### Plot category Down and Up:
        plt.subplot(143)
        ax = sns.scatterplot(x="log2FC", y="-log10(FDR)", data=df, s=3, color=grey, alpha=0.7, edgecolor="none")
        ax = sns.scatterplot(x="log2FC", y="-log10(FDR)", data=significant_Diff, s=5, color=black, alpha=1, edgecolor="none")
        
        plt.plot(np.linspace(-1000,1000,1000), [log10Cutt_line]*1000, '--', color='black', linewidth=1)
        plt.plot([0]*1000, np.linspace(-1000,1000,1000), '--', color='black', linewidth=1)
#         plt.plot([log2Cutt_line]*1000, np.linspace(-1000,120,1000), '--', color='black', linewidth=1)

        ax.set_xlim([-absMaxX, absMaxX])
        ax.set_ylim([-0.1, absMaxY])

        ### Add text over the plot:
        left, width = .25, .5
        bottom, height = .25, .5
        right = left + width
        top = bottom + height

        N = len(df[(df["Regulation"] == "Down2") | (df["Regulation"] == "Down")])
        ax.text(0.01, 0.99 * (bottom + top), 'Down: {}'.format(N), horizontalalignment='left', verticalalignment='top', transform=ax.transAxes, fontsize=13)

        N = len(df[(df["Regulation"] == "Up2") | (df["Regulation"] == "Up")])
        ax.text(0.99, 0.99 * (bottom + top), 'Up: {}'.format(N), horizontalalignment='right', verticalalignment='top', transform=ax.transAxes, fontsize=13)
        
        plt.title("Up and Down\nFDR<0.05; Cumulative numbers", fontsize=13)
        
        
        ### Plot category DownNoFDR and UpNoFDR:
        plt.subplot(144)
        ax = sns.scatterplot(x="log2FC", y="-log10(p-value)", data=df, s=3, color=grey, alpha=0.7, edgecolor="none")
        ax = sns.scatterplot(x="log2FC", y="-log10(p-value)", data=significant_DiffNoFDR, s=5, color=black, alpha=1, edgecolor="none")
        
        plt.plot(np.linspace(-1000,1000,1000), [log10Cutt_line]*1000, '--', color='black', linewidth=1)
        plt.plot([0]*1000, np.linspace(-1000,1000,1000), '--', color='black', linewidth=1)
#         plt.plot([log2Cutt_line]*1000, np.linspace(-1000,120,1000), '--', color='black', linewidth=1)

        ax.set_xlim([-absMaxX, absMaxX])
        ax.set_ylim([-0.1, absMaxY])

        ### Add text over the plot:
        left, width = .25, .5
        bottom, height = .25, .5
        right = left + width
        top = bottom + height

        N = len(df[(df["Regulation"] == "Down2") | (df["Regulation"] == "Down") | (df["Regulation"] == "Down2NoFDR") | (df["Regulation"] == "DownNoFDR")])
        ax.text(0.01, 0.99 * (bottom + top), 'Down: {}'.format(N), horizontalalignment='left', verticalalignment='top', transform=ax.transAxes, fontsize=13)

        N = len(df[(df["Regulation"] == "Up2") | (df["Regulation"] == "Up") | (df["Regulation"] == "Up2NoFDR") | (df["Regulation"] == "UpNoFDR")])
        ax.text(0.99, 0.99 * (bottom + top), 'Up: {}'.format(N), horizontalalignment='right', verticalalignment='top', transform=ax.transAxes, fontsize=13)
        
        plt.title("UpNoFDR and DownNoFDR\np-value<0.05; Cumulative numbers", fontsize=13)
        
        ### Save figure:
        plt.savefig("{}.Volcano.pdf".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.savefig("{}.Volcano.png".format(infileName.replace(".anno","")), bbox_inches='tight', dpi=300)
        plt.close()

def plot_stackedBar_across_files(combined_tsv, subdirectory):
    """
    combined_tsv: the AllFiles.combinedAnno.tsv produced by _collect_all_anno_for_stacked()
                  Must contain columns: __source__, FeatureAssignment
    Saves PNG/PDF/HTML + TSV into subdirectory.
    """
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)

    if not os.path.isfile(combined_tsv):
        logger1.warning(f"Combined annotations not found: {combined_tsv}")
        return

    df = pd.read_csv(combined_tsv, sep="\t")
    required = {"__source__", "FeatureAssignment"}
    missing = required.difference(df.columns)
    if missing:
        logger1.warning(f"Skip global stacked plot; missing columns in {combined_tsv}: {sorted(missing)}")
        return

    # Standardize names used downstream
    df = df.rename(columns={"__source__": "Source", "FeatureAssignment": "Genomic context"}).copy()

    # Priority order for contexts (same as your per-file plots)
    genomicContextPriority = [
        "Promoter.Up", "Promoter.Down", "Exon", "Intron",
        "TES (transcription end sites)",
        "Dis5 (5' distal regions)", "Dis3 (3' distal regions)",
        "Intergenic"
    ]

    # Summarize counts per Source x Genomic context
    grp = df.groupby(["Source", "Genomic context"]).size().reset_index(name="Number of regions")

    # Add zero rows for missing contexts per source to keep ordering consistent
    all_sources = sorted(grp["Source"].unique().tolist())
    filled = []
    for src in all_sources:
        present = set(grp[grp["Source"] == src]["Genomic context"])
        for ctx in genomicContextPriority:
            if ctx not in present:
                filled.append({"Source": src, "Genomic context": ctx, "Number of regions": 0})
    if filled:
        grp = pd.concat([grp, pd.DataFrame(filled)], ignore_index=True)

    # Reorder contexts
    grp["Genomic context"] = pd.Categorical(grp["Genomic context"],
                                            categories=[c for c in genomicContextPriority],
                                            ordered=True)

    # Compute percentages per Source
    totals = grp.groupby("Source")["Number of regions"].sum().rename("total")
    grp = grp.merge(totals, on="Source", how="left")
    grp["Percentage of regions"] = grp.apply(
        lambda r: (r["Number of regions"] / r["total"] * 100.0) if r["total"] > 0 else 0.0, axis=1
    )
    grp["Percentage"] = grp["Percentage of regions"].map(lambda x: f"{x:.2f}%")

    # Export stats TSV (so seaborn helper can reuse it)
    outbase = os.path.join(subdirectory, "AllFilesAcrossSources")
    os.makedirs(subdirectory, exist_ok=True)
    tsv_path = f"{outbase}.GenomicFeaturesAnnotation.tsv"
    grp.loc[:, ["Source", "Genomic context", "Number of regions", "Percentage", "Percentage of regions"]]\
       .to_csv(tsv_path, sep="\t", index=False)

    # Plotly stacked bar
    cmap = plt.get_cmap('Spectral')
    colors = [matplotlib.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, len(genomicContextPriority))]
    color_discrete_map = dict(zip(genomicContextPriority, colors))

    fig = px.bar(
        grp,
        x="Source",
        y="Percentage of regions",
        color="Genomic context",
        barmode="relative",
        text="Percentage",
        category_orders={"Genomic context": genomicContextPriority},
        color_discrete_map=color_discrete_map
    )
    fig.update_layout(
        title="Percentage of regions per genomic context (stacked by BED/anno file)",
        template="simple_white",
        xaxis_title="Annotated file",
        yaxis_title="Percentage",
        # height=450
    )
    fig.update_yaxes(range=[0, 100])

    fig.write_html(f"{outbase}.GenomicFeaturesAnnotation.html")

    try:
        fig.write_image(f"{outbase}.GenomicFeaturesAnnotation.png", scale=4)
        fig.write_image(f"{outbase}.GenomicFeaturesAnnotation.pdf")
    except Exception as e:
        logger1.warning(f"Skipped Plotly image exports for {outbase}.GenomicFeaturesAnnotation: {e}")

    logger1.info(f"Saved {outbase}.GenomicFeaturesAnnotation HTML/TSV and any available Plotly images")

def plot_stackedBar_across_files_seaborn(stats_tsv):
    """
    stats_tsv: the *.GenomicFeaturesAnnotation.tsv produced by plot_stackedBar_across_files()
               Columns: Source, Genomic context, Percentage of regions
    """
    logger1 = logging.getLogger(inspect.currentframe().f_code.co_name)

    if not os.path.isfile(stats_tsv):
        logger1.warning(f"Stats file not found for seaborn plot: {stats_tsv}")
        return

    df = pd.read_csv(stats_tsv, sep="\t")
    need = {"Source", "Genomic context", "Percentage of regions"}
    if need.difference(df.columns):
        logger1.warning(f"Required columns missing in {stats_tsv}; skip seaborn stacked plot.")
        return

    # Pivot to wide for stacking
    wide = df.pivot_table(index="Source",
                          columns="Genomic context",
                          values="Percentage of regions",
                          aggfunc="first").fillna(0.0)

    # Keep consistent ordering for contexts
    genomicContextPriority = [
        "Promoter.Up", "Promoter.Down", "Exon", "Intron",
        "TES (transcription end sites)",
        "Dis5 (5' distal regions)", "Dis3 (3' distal regions)",
        "Intergenic"
    ]
    cols = [c for c in genomicContextPriority if c in wide.columns]
    wide = wide[cols]

    # seaborn aesthetics
    sns.set_style("whitegrid")
    palette = sns.color_palette("Spectral", n_colors=len(cols))

    fig, ax = plt.subplots(figsize=(max(10, len(wide) * 0.6), 5))
    bottoms = np.zeros(len(wide), dtype=float)
    x = np.arange(len(wide.index))

    for i, col in enumerate(cols):
        heights = wide[col].values
        ax.bar(x, heights, bottom=bottoms, label=col, color=palette[i])
        bottoms += heights

    ax.set_xticks(x)
    ax.set_xticklabels(wide.index, rotation=30, ha='right')
    ax.set_ylim(0, 100)
    ax.set_ylabel("Percentage")
    ax.set_xlabel("Annotated file")
    ax.set_title("Percentage of regions per genomic context (stacked by BED/anno file)")

    # Legend outside
    ax.legend(title="Genomic context", bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False)

    plt.tight_layout()

    outbase = stats_tsv.replace(".GenomicFeaturesAnnotation.tsv", ".GenomicFeaturesAnnotation.seaborn")
    plt.savefig(outbase + ".pdf", bbox_inches='tight', dpi=300)
    plt.savefig(outbase + ".png", bbox_inches='tight', dpi=300)
    plt.close()
    logger1.info(f"Saved {outbase}.[png|pdf] (seaborn-styled stacked bar)")

def _collect_all_anno_for_stacked(root="."):
    """
    Returns a list of dataframes concatenable for the global stacked bar.
    Accepts any *.anno files that have FeatureAssignment.
    """
    required = {'FeatureAssignment'} 
    dfs = []
    for path in glob.glob(os.path.join(root, "*.anno")):
        try:
            df = pd.read_csv(path, sep="\t")
            if required.issubset(df.columns):
                df["__source__"] = os.path.basename(path)
                dfs.append(df)
            else:
                logging.info(f"Skipping {path} for global stacked plot; missing columns: {sorted(required - set(df.columns))}")
        except Exception as e:
            logging.warning(f"Could not read {path}: {e}")
    return dfs

def RNKWeight(fc, p):
    ### Detect direction:
    if fc < 0:
        s = -1
    else:
        s = 1
    return s * -1 * np.log(p)/np.log(10)

def RNKWeight2(log2fc, p, minP = 2.22e-16):
    """
    Source: http://crazyhottommy.blogspot.com/2016/08/gene-set-enrichment-analysis-gsea.html
    solution: signed fold change * -log10pvalue
    which i am changing to: log2(FC) * -log10(p-value), which should not give me crazy high numbers
    """
    if p < minP:
        p = 2.22e-16
    return log2fc * -np.log10(p)

def RNKWeightFC(log2fc, p, minP = 2.22e-16):
    """Plain old log2FC"""
    return log2fc

########

configureLogging("OrganizeAnnotationResults")

root = "./"
description = {"Up2" : ["Up", ">2fold,FDR<0.05"],
               "Up2NoFDR" : ["Up", ">2fold,p<0.05"],
               "Up" : ["Up", "FDR<0.05"],
               "UpNoFDR" : ["Up", "p<0.05"],
               "Control" : ["Control", "Control"],
               "DownNoFDR" : ["Down", "p<0.05"],
               "Down" : ["Down", "FDR<0.05"],
               "Down2NoFDR" : ["Down", ">2fold,p<0.05"],
               "Down2" : ["Down", ">2fold,FDR<0.05"]}

cumulativeCategories = {"Up2" : ["Up2"],
                        "Up2NoFDR" : ["Up2", "Up2NoFDR"],
                        "Up" : ["Up", "Up2"],
                        "UpNoFDR" : ["Up", "Up2", "Up2NoFDR", "UpNoFDR"],
                        "Down2" : ["Down2"],
                        "Down2NoFDR" : ["Down2", "Down2NoFDR"],
                        "Down" : ["Down", "Down2"],
                        "DownNoFDR" : ["Down", "Down2", "Down2NoFDR", "DownNoFDR"],
                        "Control" : ["Control"]}
categoriesOrder = ["Up2", "Up2NoFDR", "Up", "UpNoFDR", "Control", "DownNoFDR", "Down", "Down2NoFDR", "Down2"]

## prepare final outputs dir:
command = "mkdir -p finalReports bedFileAnnotations allOtherFiles"
subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout.read()

output = open("finalReports/summaryTable.tsv", "w")
output.write("Comparison\tRegulation\tCodeName\tThreshold\t#Region\t#Gene_Promoter\t#Gene_Enhancer\t#Region_Cumulative\t#Gene_Promoter_Cumulative\t#Gene_Enhancer_Cumulative\n")
xlsxFile = pd.ExcelWriter("finalReports/annotations.xlsx", engine='xlsxwriter')
gmt_gn = open("finalReports/annotatedGenes.GeneNames.gmt", "w")
gmt_gn_upper = open("finalReports/annotatedGenes.GeneNames.CUMULATIVE.gmt", "w")
gmt_en = open("finalReports/annotatedGenes.Gencode.gmt", "w")
outputDict_promoter = {}
outputDict_enhancer = {}
outputDict_closest = {}
outputDict_promoter_cumulative = {}
outputDict_enhancer_cumulative = {}
outputDict_closest_cumulative = {}

for file in os.listdir(root):
    if file.endswith(".vout.anno"):
        mode = 'VOUT_format'
        logging.info("processing {} file as {} in 'VOUT_format' mode".format(file, file.replace(".vout.anno","").split(".")[0]))
        anno = pd.read_csv(file, sep = "\t")
        
        ## adding annotation to excel:
        try:
            anno.to_excel(xlsxFile, index=False, sheet_name=file    .split(".")[-1])
        except ValueError:
            logging.info("ValueError was raised due to too large size for the Excel format")
        
        ## copying gzipped annotation file to final destination:
        anno.to_csv("finalReports/{}".format(file), sep="\t", index=False)
        
        ## adding a summary to the summary table and GMT files (for GSEA):
        for cat in categoriesOrder:
            df = anno[anno.Regulation == cat]
            Gene_Promoter = 0
            Gene_Enhancer = 0
            # Standard categories here:
            gmt_gn_closest = []
            gmt_gn_promoter = []
            gmt_gn_enhancer = []
            gmt_en_closest = []
            gmt_en_promoter = []
            gmt_en_enhancer = []
            
            bed = open("bedFileAnnotations/{}.{}.bed".format(file, cat), 'w')
            GeneColNames = []
            for colName in list(df):
                if "Gene_" in colName:
                    GeneColNames.append(colName)
            if len(GeneColNames) != 2:
                logging.error("Found the following headers with 'Gene_' term: '{}', but was expecting to find two elements only, e.g. ['Gene_2kb','Gene_2-50kb'] for standard human analysis. Please investigate that. In a meantime, the execution of this program was aborted.".format(GeneColNames))
                logging.debug("Headers are: {}".format(list(df)))
            
            for index, row in df.iterrows():
                if row[GeneColNames[0]] != ".":
                    Gene_Promoter += len(row[GeneColNames[0]].split(","))
                    gmt_gn_promoter += row[GeneColNames[0]].split(",")
                    gmt_en_promoter += row["Gencode_ids"].split(",")
                if row[GeneColNames[1]] != ".":
                    Gene_Enhancer += len(row[GeneColNames[1]].split(","))
                    gmt_gn_enhancer += row[GeneColNames[1]].split(",")
                    gmt_en_enhancer += row["Gencode_ids.1"].split(",")
                if row["Closest_Gene"] != ".":
                    gmt_gn_closest.append(row["Closest_Gene"])
                    gmt_en_closest.append(row["Gencode_id"])
                bed.write("{}\n".format(row["Region"].replace(":","\t").replace("-","\t")))
            bed.close()
            
            # Cumulative categories here:
            regionsNumCumulative = 0
            gmt_gn_closest_cumulative = []
            gmt_gn_promoter_cumulative = []
            gmt_gn_enhancer_cumulative = []
            gmt_en_closest_cumulative = []
            gmt_en_promoter_cumulative = []
            gmt_en_enhancer_cumulative = []
            bed = open("bedFileAnnotations/{}.{}.cumulative.bed".format(file, cat), 'w')
            for subCat in cumulativeCategories[cat]:
                dfCum = anno[anno.Regulation == subCat]
                regionsNumCumulative += len(dfCum)
                for index, row in dfCum.iterrows():
                    if row[GeneColNames[0]] != ".":
                        gmt_gn_promoter_cumulative += row[GeneColNames[0]].split(",")
                        gmt_en_promoter_cumulative += row["Gencode_ids"].split(",")
                    if row[GeneColNames[1]] != ".":
                        gmt_gn_enhancer_cumulative += row[GeneColNames[1]].split(",")
                        gmt_en_enhancer_cumulative += row["Gencode_ids.1"].split(",")
                    if row["Closest_Gene"] != ".":
                        gmt_gn_closest_cumulative.append(row["Closest_Gene"])
                        gmt_en_closest_cumulative.append(row["Gencode_id"])
                    bed.write("{}\n".format(row["Region"].replace(":","\t").replace("-","\t")))
            bed.close()
            
            output.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(file.replace(".vout.anno",""), description[cat][0], cat, description[cat][1], len(df), len(uniqueOnly(gmt_gn_promoter)), len(uniqueOnly(gmt_gn_enhancer)), regionsNumCumulative, len(uniqueOnly(gmt_gn_promoter_cumulative)), len(uniqueOnly(gmt_gn_enhancer_cumulative))))
            
            # Add gene sets for standard categories here:
            if len(gmt_gn_promoter) > 0:
                gmt_gn.write("{0}.{1}.promoter\t{0}.{1}.promoter\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_promoter))))
                geneSetExport = open("allOtherFiles/{0}.{1}.promoter.txt".format(file.replace(".vout.anno",""), cat), 'w')
                geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_promoter))))
                geneSetExport.close()
                outputDict_promoter["{0}.{1}".format(file.replace(".vout.anno",""), cat)] = uniqueOnly(gmt_gn_promoter)
            if len(gmt_gn_enhancer) > 0:
                gmt_gn.write("{0}.{1}.enhancer\t{0}.{1}.enhancer\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_enhancer))))
                geneSetExport = open("allOtherFiles/{0}.{1}.enhancer.txt".format(file.replace(".vout.anno",""), cat), 'w')
                geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_enhancer))))
                geneSetExport.close()
                outputDict_enhancer["{0}.{1}".format(file.replace(".vout.anno",""), cat)] = uniqueOnly(gmt_gn_enhancer)
            if len(gmt_gn_closest) > 0:
                gmt_gn.write("{0}.{1}.closest\t{0}.{1}.closest\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_closest))))
                geneSetExport = open("allOtherFiles/{0}.{1}.closest.txt".format(file.replace(".vout.anno",""), cat), 'w')
                geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_closest))))
                geneSetExport.close()
                outputDict_closest["{0}.{1}".format(file.replace(".vout.anno",""), cat)] = uniqueOnly(gmt_gn_closest)
            
            if len(gmt_en_promoter) > 0:
                gmt_en.write("{0}.{1}.promoter\t{0}.{1}.promoter\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_promoter))))
            if len(gmt_en_enhancer) > 0:
                gmt_en.write("{0}.{1}.enhancer\t{0}.{1}.enhancer\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_enhancer))))
            if len(gmt_en_closest) > 0:
                gmt_en.write("{0}.{1}.closest\t{0}.{1}.closest\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_closest))))
        
            # Add gene sets for cumulative categories here:
            if len(gmt_gn_promoter_cumulative) > 0:
                gmt_gn.write("{0}.{1}.promoter.CUMULATIVE\t{0}.{1}.promoter.CUMULATIVE\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_promoter_cumulative))))
                if cat != "Control":
                    gmt_gn_upper.write("{0}.{1}\t{0}.{1}\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_promoter_cumulative))))
                geneSetExport = open("allOtherFiles/{0}.{1}.promoter.CUMULATIVE.txt".format(file.replace(".vout.anno",""), cat), 'w')
                geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_promoter_cumulative))))
                geneSetExport.close()
                outputDict_promoter_cumulative["{0}.{1}".format(file.replace(".vout.anno",""), cat)] = uniqueOnly(gmt_gn_promoter_cumulative)
            if len(gmt_gn_enhancer_cumulative) > 0:
                gmt_gn.write("{0}.{1}.enhancer.CUMULATIVE\t{0}.{1}.enhancer.CUMULATIVE\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_enhancer_cumulative))))
                geneSetExport = open("allOtherFiles/{0}.{1}.enhancer.CUMULATIVE.txt".format(file.replace(".vout.anno",""), cat), 'w')
                geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_enhancer_cumulative))))
                geneSetExport.close()
                outputDict_enhancer_cumulative["{0}.{1}".format(file.replace(".vout.anno",""), cat)] = uniqueOnly(gmt_gn_enhancer_cumulative)
            if len(gmt_gn_closest_cumulative) > 0:
                gmt_gn.write("{0}.{1}.closest.CUMULATIVE\t{0}.{1}.closest.CUMULATIVE\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_closest_cumulative))))
                geneSetExport = open("allOtherFiles/{0}.{1}.closest.CUMULATIVE.txt".format(file.replace(".vout.anno",""), cat), 'w')
                geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_closest_cumulative))))
                geneSetExport.close()
                outputDict_closest_cumulative["{0}.{1}".format(file.replace(".vout.anno",""), cat)] = uniqueOnly(gmt_gn_closest_cumulative)
            
            if len(gmt_en_promoter_cumulative) > 0:
                gmt_en.write("{0}.{1}.promoter.CUMULATIVE\t{0}.{1}.promoter.CUMULATIVE\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_promoter_cumulative))))
            if len(gmt_en_enhancer_cumulative) > 0:
                gmt_en.write("{0}.{1}.enhancer.CUMULATIVE\t{0}.{1}.enhancer.CUMULATIVE\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_enhancer_cumulative))))
            if len(gmt_en_closest_cumulative) > 0:
                gmt_en.write("{0}.{1}.closest.CUMULATIVE\t{0}.{1}.closest.CUMULATIVE\t{2}\n".format(file.replace(".vout.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_closest_cumulative))))
        
        ### Generating rank and chip files for GSEA:
        preRankDF = anno[anno[GeneColNames[0]] != "."].copy()
        preRankDF["PRank"] = preRankDF[['log2FC','p.value']].apply(lambda x: RNKWeight(x[0], x[1]), axis=1)
        preRankDF["FCPRank"] = preRankDF[['log2FC','p.value']].apply(lambda x: RNKWeight2(x[0], x[1]), axis=1)
        preRankDF["FCRank"] = preRankDF[['log2FC','p.value']].apply(lambda x: RNKWeightFC(x[0], x[1]), axis=1)
        RankDict = {} # {gene : [list of tuples with all regions assigned to a gene, fields are (PRank, FCPrank, FDR)]}
        for index, row in preRankDF.iterrows():
            genesList = row[GeneColNames[0]].split(",")
            for gene in genesList:
                if gene not in RankDict:
                    RankDict[gene] = []
                RankDict[gene].append((row["PRank"], row["FCPRank"], row["q.value"], row["FCRank"]))
        genesList = []
        genesListUpper = []
        PRankList = []
        PRankListMean = []
        FCPRankList = []
        FCPRankListMean = []
        FCRankList = []
        FCRankListMean = []
        for gene in RankDict:
            genesList.append(gene)
#             genesListUpper.append(gene)#.upper())
            if len(RankDict[gene]) == 1:
                PRankList.append(RankDict[gene][0][0])
                PRankListMean.append(RankDict[gene][0][0])
                FCPRankList.append(RankDict[gene][0][1])
                FCPRankListMean.append(RankDict[gene][0][1])
                FCRankList.append(RankDict[gene][0][3])
                FCRankListMean.append(RankDict[gene][0][3])
            else:
                PRank = RankDict[gene][0][0]
                PRankTmp = [PRank]
                FCPRank = RankDict[gene][0][1]
                FCPRankTmp = [FCPRank]
                FCRank = RankDict[gene][0][3]
                FCRankTmp = [FCRank]
                FDR = RankDict[gene][0][2]
                for region in RankDict[gene][1:]:
                    PRankTmp.append(region[0])
                    FCPRankTmp.append(region[1])
                    FCRankTmp.append(region[3])
                    if region[2] < FDR:
                        if region[0] < FCPRank or region[1] < PRank:
                            PRank = region[0]
                            FCPRank = region[1]
                            FCRank = region[3]
                            FDR = region[2]
                rndNum = random.uniform(-1,1)*random.uniform(1e-20,1e-10) # adding a super-tiny randomization to avoid GSEA running into Tie-solving situation
                PRankList.append(PRank+rndNum)
                PRankListMean.append(np.mean(PRankTmp)+rndNum)
                FCPRankList.append(FCPRank+rndNum)
                FCPRankListMean.append(np.mean(FCPRankTmp)+rndNum)
                FCRankList.append(FCRank+rndNum)
                FCRankListMean.append(np.mean(FCRankTmp)+rndNum)

        RankDF = pd.DataFrame.from_dict( {"genes": genesList, "rank": PRankList} )
        RankDF = RankDF.sort_values("rank", ascending=False)
        RankDF.to_csv("allOtherFiles/{0}.promoter.PRank.rnk".format(file.replace(".vout.anno","")), sep='\t', index=False, header=False)
        
        RankDF = pd.DataFrame.from_dict( {"genes": genesList, "rank": PRankListMean} )
        RankDF = RankDF.sort_values("rank", ascending=False)
        RankDF.to_csv("allOtherFiles/{0}.promoter.PRankMean.rnk".format(file.replace(".vout.anno","")), sep='\t', index=False, header=False)
        
        RankDF = pd.DataFrame.from_dict( {"genes": genesList, "rank": FCPRankList} )
        RankDF = RankDF.sort_values("rank", ascending=False)
        RankDF.to_csv("allOtherFiles/{0}.promoter.FCPRank.rnk".format(file.replace(".vout.anno","")), sep='\t', index=False, header=False)
        
        RankDF = pd.DataFrame.from_dict( {"genes": genesList, "rank": FCPRankListMean} )
        RankDF = RankDF.sort_values("rank", ascending=False)
        RankDF.to_csv("allOtherFiles/{0}.promoter.FCPRankMean.rnk".format(file.replace(".vout.anno","")), sep='\t', index=False, header=False)
        
        RankDF = pd.DataFrame.from_dict( {"genes": genesList, "rank": FCRankList} )
        RankDF = RankDF.sort_values("rank", ascending=False)
        RankDF.to_csv("allOtherFiles/{0}.promoter.FCRank.rnk".format(file.replace(".vout.anno","")), sep='\t', index=False, header=False)
        
        RankDF = pd.DataFrame.from_dict( {"genes": genesList, "rank": FCRankListMean} )
        RankDF = RankDF.sort_values("rank", ascending=False)
        RankDF.to_csv("allOtherFiles/{0}.promoter.FCRankMean.rnk".format(file.replace(".vout.anno","")), sep='\t', index=False, header=False)
        
        chipDF = pd.DataFrame.from_dict( {"Probe Set ID": genesList, "Gene Symbol": genesList, "Gene Title": genesList} )
        chipDF.to_csv("allOtherFiles/{0}.promoter.chip".format(file.replace(".vout.anno","")), sep='\t', index=False)
        
        ### Data visualizations:
        MAplot(file)
        barPlot(file, description, mode)
        drawHeatmap(file, description, mode)
        plotPCA(file, description, mode)
        plotVolcano(file, description, mode)
        logging.info("processed {} file.".format(file))
    
    if file.endswith(".bed.anno"):
        df = pd.read_csv(file, sep = "\t")
        cat = "BED_format"
        logging.info("processing {} file as {} in 'BED_format' mode".format(file, file.replace(".bed.anno","").split(".")[0]))
        
        ## adding annotation to excel:
        try:
            sheetName = file.replace(".bed.anno","").split(".")[0][:30]
            df.to_excel(xlsxFile, index=False, sheet_name=sheetName)
        except ValueError:
            logging.warning("ValueError was raised due to too large size for the Excel format")
        
        ## copying gzipped annotation file to final destination:
#         anno.to_csv("finalReports/{}.gz".format(file), compression="gzip")
        
        Gene_Promoter = 0
        Gene_Enhancer = 0
        gmt_gn_closest = []
        gmt_gn_promoter = []
        gmt_gn_enhancer = []
        gmt_en_closest = []
        gmt_en_promoter = []
        gmt_en_enhancer = []
        
        bed = open("bedFileAnnotations/{}.bed".format(file.replace(".bed.anno","")), 'w')
        
        fileColumns = set(list(df))
        if "Region" in fileColumns and ("chr" not in fileColumns or "start" not in fileColumns or "end" not in fileColumns):
            df['chr'] = df['Region'].apply(lambda val: val.split(":")[0])
            df['start'] = df['Region'].apply(lambda val: int(val.split(":")[1].split("-")[0]))
            df['end'] = df['Region'].apply(lambda val: int(val.split(":")[1].split("-")[1]))
        
        GeneColNames = []
        for colName in list(df):
            if "Gene_" in colName:
                GeneColNames.append(colName)
        if len(GeneColNames) != 2:
            logging.error("Found the following headers with 'Gene_' term: '{}', but was expecting to find two elements only, e.g. ['Gene_2kb','Gene_2-50kb'] for standard human analysis. Please investigate that. In a meantime, the execution of this program was aborted.".format(GeneColNames))
            logging.debug("Headers are: {}".format(list(df)))

        for index, row in df.iterrows():
            if row[GeneColNames[0]] != ".":
                Gene_Promoter += len(row[GeneColNames[0]].split(","))
                gmt_gn_promoter += row[GeneColNames[0]].split(",")
                gmt_en_promoter += row["Gencode_ids"].split(",")
            if row[GeneColNames[1]] != ".":
                Gene_Enhancer += len(row[GeneColNames[1]].split(","))
                gmt_gn_enhancer += row[GeneColNames[1]].split(",")
                gmt_en_enhancer += row["Gencode_ids.1"].split(",")
            if row["Closest_Gene"] != ".":
                gmt_gn_closest.append(row["Closest_Gene"])
                gmt_en_closest.append(row["Gencode_id"])
            bed.write("{}\t{}\t{}\n".format(row["chr"], row["start"], row["end"]))
        bed.close()
        
        output.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\tN/A\tN/A\tN/A\n".format(file.replace(".bed.anno",""), cat, "N/A", "N/A", len(df), len(uniqueOnly(gmt_gn_promoter)), len(uniqueOnly(gmt_gn_enhancer))))
        
        if len(gmt_gn_promoter) > 0:
            gmt_gn.write("{0}.{1}.promoter\t{0}.{1}.promoter\t{2}\n".format(file.replace(".bed.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_promoter))))
            geneSetExport = open("allOtherFiles/{0}.{1}.promoter.txt".format(file.replace(".bed.anno",""), cat), 'w')
            geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_promoter))))
            geneSetExport.close()
            outputDict_promoter["{0}.{1}".format(file.replace(".bed.anno",""), cat)] = uniqueOnly(gmt_gn_promoter)
            outputDict_promoter_cumulative["{0}.{1}".format(file.replace(".bed.anno",""), cat)] = uniqueOnly(gmt_gn_promoter)
        if len(gmt_gn_enhancer) > 0:
            gmt_gn.write("{0}.{1}.enhancer\t{0}.{1}.enhancer\t{2}\n".format(file.replace(".bed.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_enhancer))))
            geneSetExport = open("allOtherFiles/{0}.{1}.enhancer.txt".format(file.replace(".bed.anno",""), cat), 'w')
            geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_enhancer))))
            geneSetExport.close()
            outputDict_enhancer["{0}.{1}".format(file.replace(".bed.anno",""), cat)] = uniqueOnly(gmt_gn_enhancer)
            outputDict_enhancer_cumulative["{0}.{1}".format(file.replace(".bed.anno",""), cat)] = uniqueOnly(gmt_gn_enhancer)
        if len(gmt_gn_closest) > 0:
            gmt_gn.write("{0}.{1}.closest\t{0}.{1}.closest\t{2}\n".format(file.replace(".bed.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_gn_closest))))
            geneSetExport = open("allOtherFiles/{0}.{1}.closest.txt".format(file.replace(".bed.anno",""), cat), 'w')
            geneSetExport.write("{}".format('\n'.join(str(x) for x in uniqueOnly(gmt_gn_closest))))
            geneSetExport.close()
            outputDict_closest["{0}.{1}".format(file.replace(".bed.anno",""), cat)] = uniqueOnly(gmt_gn_closest)
            outputDict_closest_cumulative["{0}.{1}".format(file.replace(".bed.anno",""), cat)] = uniqueOnly(gmt_gn_closest)
        
        if len(gmt_en_promoter) > 0:
            gmt_en.write("{0}.{1}.promoter\t{0}.{1}.promoter\t{2}\n".format(file.replace(".bed.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_promoter))))
        if len(gmt_en_enhancer) > 0:
            gmt_en.write("{0}.{1}.enhancer\t{0}.{1}.enhancer\t{2}\n".format(file.replace(".bed.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_enhancer))))
        if len(gmt_en_closest) > 0:
            gmt_en.write("{0}.{1}.closest\t{0}.{1}.closest\t{2}\n".format(file.replace(".bed.anno",""), cat, '\t'.join(str(x) for x in uniqueOnly(gmt_en_closest))))
        
#         MAplot(file)
        logging.info("processed {} file.".format(file))

for file in os.listdir(root):   
    if file.endswith(".pdf"):
        command = "cp {0} finalReports/{0}".format(file)
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout.read()
        logging.info("{} file copied to finalReports".format(file))
    if file.endswith(".anno"):
        command = "cp {0} allOtherFiles/{0}".format(file)
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout.read()
        logging.info("{} file copied to allOtherFiles".format(file))
     
xlsxFile.close()
output.close()
gmt_gn.close()
gmt_gn_upper.close()
gmt_en.close()


dct, fields = organizeOutputList(outputDict_promoter)
df = pd.DataFrame(data=dct)
df = df[fields]
df.to_csv("finalReports/annotatedGenes_combined.GeneNames.promoter.tsv", sep='\t', index=False)

dct, fields = organizeOutputList(outputDict_enhancer)
df = pd.DataFrame(data=dct)
df = df[fields]
df.to_csv("finalReports/annotatedGenes_combined.GeneNames.enhancer.tsv", sep='\t', index=False)

dct, fields = organizeOutputList(outputDict_closest)
df = pd.DataFrame(data=dct)
df = df[fields]
df.to_csv("finalReports/annotatedGenes_combined.GeneNames.closest.tsv", sep='\t', index=False)

dct, fields = organizeOutputList(outputDict_promoter_cumulative)
df = pd.DataFrame(data=dct)
df = df[fields]
df.to_csv("finalReports/annotatedGenes_combined.GeneNames.promoter.CUMULATIVE.tsv", sep='\t', index=False)

dct, fields = organizeOutputList(outputDict_enhancer_cumulative)
df = pd.DataFrame(data=dct)
df = df[fields]
df.to_csv("finalReports/annotatedGenes_combined.GeneNames.enhancer.CUMULATIVE.tsv", sep='\t', index=False)

dct, fields = organizeOutputList(outputDict_closest_cumulative)
df = pd.DataFrame(data=dct)
df = df[fields]
df.to_csv("finalReports/annotatedGenes_combined.GeneNames.closest.CUMULATIVE.tsv", sep='\t', index=False)

try:
    os.makedirs("GenomicFeaturesAnnotation", exist_ok=True)
    _all = _collect_all_anno_for_stacked(root=".")
    if len(_all) > 0:
        all_df = pd.concat(_all, ignore_index=True)

        # Write the combined table that includes __source__
        _tmp_all = "AllFiles.combinedAnno.tsv"
        all_df.to_csv(_tmp_all, sep="\t", index=False)

        # Build Plotly + TSV in GenomicFeaturesAnnotation/
        plot_stackedBar_across_files(_tmp_all, subdirectory="GenomicFeaturesAnnotation")

        # Build seaborn version from the TSV we just wrote
        _tsv_path = os.path.join("GenomicFeaturesAnnotation", "AllFilesAcrossSources.GenomicFeaturesAnnotation.tsv")
        plot_stackedBar_across_files_seaborn(_tsv_path)

        logging.info("Global stacked bar for all annotations saved in GenomicFeaturesAnnotation/")
    else:
        logging.info("No matching BED / Voom annotation files found for global stacked bar; nothing saved.")
except Exception as e:
    logging.warning(f"Failed to create global stacked bar: {e}")

logging.info("All done, thank you.")
