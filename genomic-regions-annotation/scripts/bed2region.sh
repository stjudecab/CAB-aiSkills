#!/bin/bash
#########################################################################
# Copyright (c) 2015-~ Beisi Xu
# 
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
# 
#*Author:       Beisi Xu < xubeisi [at] gmail DOT com >
# File Name: region2bed.sh
# Description: 
#########################################################################

if [[ $@ =~ \-h ]]
then
    echo "Usage:
    cat 1.bed | bed2region.sh 2000 # add 2kb to region
    cat 1.bed | bed2region.sh -2000 # add 2kb and don't change from column 4
    cat 1.bed | bed2region.sh -2000 reg # add 2kb and still bed
    "
    exit
fi

if [ $# -gt 0 ]
then
    len=$1
else
    len=0
fi

if [ $# -gt 1 ]
then
    mode=$2
else
    mode=region
fi

iiistart=1
iic1=$iiistart
let iis1=$iiistart+1
let iie1=$iiistart+2
let iic2=$iiistart+3
let iis2=$iiistart+4
let iie2=$iiistart+5

if [[ $mode =~ bed ]]
then
    theout="region2bed.sh -0"
else
    theout="tabit.sh"
fi

if [[ $len =~ "-" ]]
then
    len=$(echo $len | sed "s/\-//")
    awk "{if(\$$iic1 ~ /chr/){ \$$iic1=\$$iic1\":\"\$$iis1-$len\"-\"\$$iie1+$len;}else{\$$iic1=\"chr\"\$$iic1\":\"\$$iis1-$len\"-\"\$$iie1+$len;} \$$iis1=\$$iie1=\"\"; print \$0}" | eval $theout
else
    awk "{if(\$$iic1 ~ /chr/){a=\$$iic1;} else {a=\"chr\"\$$iic1; } print a\":\"\$$iis1-$len\"-\"\$$iie1+$len}" | eval $theout
fi
