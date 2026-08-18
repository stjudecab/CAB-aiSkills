#########################################################################
# Copyright (c) 2026-~ Hasan Al Reza && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Hasan Al Reza < hasan.al.reza.bd@gmail.com >
# File Name: genometriCorr.r
# Description:
# Runs bidirectional GenometriCorr analyses on two BED files and generates
# PDF correlation reports and visualizations for the selected genome build.
#########################################################################


setwd(getwd())

args = commandArgs(trailingOnly=TRUE)

### Loading libraries:

library(GenometriCorr)
library(GenomicRanges)
library(rtracklayer)

setA = import(args[1])#import("diff_KOvsWTno1_GCB_no2_c3.0_cond2.bed")
setB = import(args[2])#import("allChromosomes_WT2.res_100000.norm_KR.wsize_10.BORDERS.bed")
setA_shortName = args[3]#"DHMR" <-- label of the first BED
setB_shortName = args[4]#"TADs_100k" <-- label of the second BED

if (args[5] == "mm10") {
library(TxDb.Mmusculus.UCSC.mm10.knownGene)
seqinfo(setA) <- seqinfo(TxDb.Mmusculus.UCSC.mm10.knownGene)[seqnames(seqinfo(setA))]
seqinfo(setB) <- seqinfo(TxDb.Mmusculus.UCSC.mm10.knownGene)[seqnames(seqinfo(setB))]
} else if (args[5] == "hg38"){
library(TxDb.Hsapiens.UCSC.hg38.knownGene)
seqinfo(setA) <- seqinfo(TxDb.Hsapiens.UCSC.hg38.knownGene)[seqnames(seqinfo(setA))]
seqinfo(setB) <- seqinfo(TxDb.Hsapiens.UCSC.hg38.knownGene)[seqnames(seqinfo(setB))]
} else if (args[5] == "hg19"){
library(TxDb.Hsapiens.UCSC.hg19.knownGene)
seqinfo(setA) <- seqinfo(TxDb.Hsapiens.UCSC.hg19.knownGene)[seqnames(seqinfo(setA))]
seqinfo(setB) <- seqinfo(TxDb.Hsapiens.UCSC.hg19.knownGene)[seqnames(seqinfo(setB))]
} else {
print("unrecognized argument for genome version for knownGenes, Script currently supports only hg38 and mm10 references")
}

setA_vs_setB = GenometriCorrelation(setA,setB,keep.distributions=TRUE)
graphical.report(setA_vs_setB, pdffile = paste(setA_shortName, "_versus_", setB_shortName, ".projection.pdf.pdf", sep=""), show.chromosomes = c("chr1"), show.all = T)
visualize(setA_vs_setB, pdffile = paste(setA_shortName, "_versus_", setB_shortName, ".vis.pdf", sep=""), show.chromosomes = c("chr1"), show.all = T)

setB_vs_setA = GenometriCorrelation(setB,setA,keep.distributions=TRUE)
graphical.report(setB_vs_setA, pdffile = paste(setB_shortName, "_versus_", setA_shortName, ".projection.pdf", sep=""), show.chromosomes = c("chr1"), show.all = T)
visualize(setB_vs_setA, pdffile = paste(setB_shortName, "_versus_", setA_shortName, ".vis.pdf", sep=""), show.chromosomes = c("chr1"), show.all = T)


