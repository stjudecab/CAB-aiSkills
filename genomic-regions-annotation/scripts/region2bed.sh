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

#cat 1.region | region2bed.sh 2000 # add 2kb to bed3
#cat 1.region | region2bed.sh -2000 # add 2kb and don't change from column 4
#cat 1.region | region2bed.sh -2000 reg # add 2kb and still region

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
    mode=bed
fi

if [[ $mode =~ bed ]]
then
    theout="tabit.sh"
else
    theout="bed2region.sh -0"
fi
rr=$RANDOM.$(date +%Y%m%d-%H%M%S-%N).$RANDOM
if [[ $len =~ "-" ]]
then
    len=$(echo $len | sed "s/\-//")
    awk '{print $0}' > tmp0.region2bed.$rr
    if [[ $(tail -n 1 tmp0.region2bed.$rr | awk '{printf $1}') =~ : ]]
    then
        cat tmp0.region2bed.$rr | awk '{print $1}' | sed "s/,//g;s/[:-]/ /g;s/[\*]/ /g;s/[()]/ /g;s/^/chr/;s/chrchr/chr/" | awk "{print \$1\" \"\$2 - $len\" \"\$3 + $len}" > tmp1.region2bed.$rr
        cat tmp0.region2bed.$rr | awk '{$1="";print $0}'  > tmp2.region2bed.$rr
    else
        cat tmp0.region2bed.$rr | awk '{print $1,$2,$3}' | sed "s/,//g;s/[:-]/ /g;s/[\*]/ /g;s/[()]/ /g;s/^/chr/;s/chrchr/chr/" | awk "{print \$1\" \"\$2 - $len\" \"\$3 + $len}" > tmp1.region2bed.$rr
        cat tmp0.region2bed.$rr | awk '{$1=$2=$3="";print $0}'  > tmp2.region2bed.$rr
    fi
    paste tmp1.region2bed.$rr tmp2.region2bed.$rr | eval $theout
    rm tmp{0,1,2}.region2bed.$rr
else
    sed "s/,//g;s/[:-]/ /g;s/[\*]/ /g;s/[()]/ /g;s/^/chr/;s/chrchr/chr/i" | awk "{print \$1\" \"\$2 - $len\" \"\$3 + $len}" | eval $theout
fi
