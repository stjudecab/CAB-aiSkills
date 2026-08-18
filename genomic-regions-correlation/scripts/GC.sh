#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Hasan Al Reza && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Hasan Al Reza < hasan.al.reza.bd@gmail.com >
# File Name: GC.sh
# Description:
# Submits an R-based genomic correlation job to LSF after validating the
# script and BED inputs.
#########################################################################

set -euo pipefail

proc=16
mem=128000

usage() {
    echo "Usage:"
    echo "  $0 <R_script> <query_bed> <reference_bed> <query_label> <reference_label> <genome>"
    exit 1
}

[[ $# -eq 6 ]] || usage

R_SCRIPT="$1"
QUERY_BED="$2"
REFERENCE_BED="$3"
QUERY_LABEL="$4"
REFERENCE_LABEL="$5"
GENOME="$6"

if [[ ! -f "$R_SCRIPT" ]]; then
    echo "ERROR: Cannot find R script: $R_SCRIPT"
    exit 1
fi

if [[ ! -f "$QUERY_BED" ]]; then
    echo "ERROR: Cannot find query BED: $QUERY_BED"
    exit 1
fi

if [[ ! -f "$REFERENCE_BED" ]]; then
    echo "ERROR: Cannot find reference BED: $REFERENCE_BED"
    exit 1
fi

bsub \
    -n "$proc" \
    -R "span[hosts=1]" \
    -R "rusage[mem=$(($mem/$proc))]" \
    -P GC \
    -J GC \
    -q cab_auto \
    -cwd "$(pwd -P)" \
    "Rscript \"$R_SCRIPT\" \
        \"$QUERY_BED\" \
        \"$REFERENCE_BED\" \
        \"$QUERY_LABEL\" \
        \"$REFERENCE_LABEL\" \
        \"$GENOME\""