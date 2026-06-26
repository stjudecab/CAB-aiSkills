#!/bin/bash
#########################################################################
# Copyright (c) 2011-~ Beisi Xu
# 
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
# 
#*Author:       Beisi Xu < xubeisi [at] gmail DOT com >
# File Name: tabit.sh
# Description: 
#########################################################################

#awk '{i=1;while(i<=NF){printf("%.3lf\t",$i);i++;}printf "\n"}'
if [ $# -lt 1 ]
then
echo "Need NF"
exit
else
nf=$1
fi

awk -v nnf=$nf '{i=1;while(i<=nnf){if(i<=NF){printf("%s\t",$i)}else{printf("NA\t")};i++;}printf("\n",$i)}'
