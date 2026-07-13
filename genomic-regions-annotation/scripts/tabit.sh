#!/bin/bash
#########################################################################
# Copyright (c) 2011-~ Beisi Xu
# 

if [ $# -gt 0 ]
then
    ff=$1
    if [ -f $ff ]
    then
        awk '{i=1;while(i<NF){printf("%s\t",$i);i++;}printf("%s\n",$i)}' $ff > ${ff}.tabtmp
        mv ${ff}.tabtmp $ff
    else
        awk '{i=1;while(i<NF){printf("%s\t",$i);i++;}printf("%s\n",$i)}'
    fi
else
    awk '{i=1;while(i<NF){printf("%s\t",$i);i++;}printf("%s\n",$i)}'
fi
