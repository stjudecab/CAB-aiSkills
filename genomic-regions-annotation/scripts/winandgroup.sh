#!/bin/bash
#########################################################################
# Copyright (c) 2016-~ Beisi Xu && St Jude
# 
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
# 
#*Author:       Beisi Xu < xubeisi [at] gmail DOT com >
# File Name: winandgroup.sh
# Description: 
#########################################################################

fa=$1
colsb=$2
colso=$3
if [ $# -lt 3 ]
then
    echo "Usage: cat bedb | winandgroup.sh beda cols_in_b(1-based) first,distinct,collapse,sum,mean [ windowsize(2000) ] [ intersect options ]"
    echo "if sum,mean,max,min; then only use -wo"
    exit
fi

nnfa=$(head -n 1 $fa | awk '{printf NF}')

ccadj=$(echo $colsb | tr "," "\n" | awk "{printf \$1+$nnfa\",\"}" | sed "s/,$//")
cca=$(seq $nnfa | tr "\n" "," | sed "s/,$//")

if [[ $colso =~ min|max|sum|mean ]]
then
    intpara="-wo"
else
    intpara="-wao"
fi

if [ $# -gt 3 ]
then
    dis=$4
else
    dis=0
fi

if [ $# -gt 4 ]
then
    cmdop=$5
else
    cmdop=" "
fi

if [[ $dis =~ _ ]]
then
    outmode=${dis##*_}
    dis=${dis%%_*}
else
    outmode=bed
fi

if [[ $dis =~ c ]]
then
    com="closestBed -d "
else
    if [ $dis -eq 0 ]
    then
        com="intersectBed $intpara "
    else
        com="windowBed -w $dis "
    fi
fi

$com $cmdop -a $fa -b - | groupBy -g $cca -c $ccadj -o $colso
