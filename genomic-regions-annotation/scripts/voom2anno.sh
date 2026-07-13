#!/bin/bash
#########################################################################
# Copyright (c) 2016-~ Beisi Xu && St Jude
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#*Author:       Beisi Xu < xubeisi [at] gmail DOT com >
# File Name: voom2anno.sh
#########################################################################
# Load bedtools module (ignore error if already loaded)
module load bedtools/2.30.0 2>/dev/null || true

modein=$1
fout=$2
fanno0=$3

if [ $# -lt 4 ]
then
    echo "Usage: voom2anno.sh pktest[ih]1|bed[3-6]h0 f.vout gencode.tss|refFlat.tss [ 2000[2kb|1M] ] [ 10000 ] "
    echo "bed3i1(ignore 1st line from bed)"
    echo "bed6h1(keep 1st line from bed)"
    echo "bed6o(keep bed format)"
    echo "bedpe:chr1 s1 e1 chr2 s2 e2"
    exit
fi

if [ ! -s $fanno0 ] # hg38|hg19|mm10|sacCer3
then
    fspeclst=$(dirname $0)/voom2anno.sh.lst
    if grep $fanno0 $fspeclst 2> /dev/null > /dev/null
    then
        fanno0=$(grep $fanno0 $fspeclst | head -n 1)
        fanno0=$(dirname $0 | sed "s/sjcab_custom_atac/sjcab_std_anno_report/")/$fanno0
    fi
    if [ ! -s $fanno0 ]
    then
        exit
    fi
fi

if [[ ! ${fanno0} =~ .clean$ ]]
then
    if [ ! -f ${fanno0}.clean ] || [ $(head -n 10 ${fanno0}.clean | wcn.sh) -lt 9 ]
    then
        #    cat ${fanno0} | awk '$4 !~ /^Gm[0-9]*/ && $4 !~ /[^ ]+Rik$/ && $4 !~ /^A[CL][0-9]+\.[0-9]/ && $4 !~ /^RP[0-9]+\-[0-9]/{print $0}' | tabit.sh > ${fanno0}.clean
        cat ${fanno0} | awk -v icol=4 --re-interval -f `which gene2nomicro.awk` > ${fanno0}.clean
    fi
    fanno=${fanno0}.clean
fi

echo $0 $@ >> .run.log

diso=$4
diso2=$5

disstr=$(echo $diso | sed "s/\(.*\)000000/\1Mb/;s/\(.*\)000/\1kb/")
disstr2=$(echo $diso2 | sed "s/\(.*\)000000/\1Mb/;s/\(.*\)000/\1kb/")

dis=$(echo $diso | sed "s/[Mm]b/000000/;s/[Kk]b/000/;s/[Mm]/000000/;s/[Kk]/000/")
dis2=$(echo $diso2 | sed "s/[Mm]b/000000/;s/[Kk]b/000/;s/[Mm]/000000/;s/[Kk]/000/")

suff="Gene_2kb        Gencode_ids  Gene_2-10kb     Gencode_ids  Closest_Gene_out10kb    Gencode_id   Distance"
suff=$(echo "Gene_XXX1XXX        Gencode_ids  Gene_XXX2XXX     Gencode_ids  Closest_Gene_outXXX3XXX    Gencode_id   Distance" | sed "s/XXX1XXX/$disstr/;s/XXX2XXX/$disstr-$disstr2/;s/[Mk]b-/-/;s/XXX3XXX/$disstr2/")
suff=$(echo "Gene_XXX1XXX        Gencode_ids  Gene_XXX2XXX     Gencode_ids  Closest_Gene    Gencode_id   Distance" | sed "s/XXX1XXX/$disstr/;s/XXX2XXX/$disstr-$disstr2/;s/[Mk]b-/-/;")


fwrout=${fout}.anno

> $fwrout


if [[ $modein =~ pktest ]]
then
    nheader=$(echo $modein | sed "s/pktest[ih]//")
    nheaderx=$(echo $modein | sed "s/pktest//")
    if [[ $nheaderx =~ i ]] || [[ $nheaderx =~ h ]]
    then
        if [ ${#nheader} -lt 1 ]
        then
            nheader=2
        else
            nheader=$(echo $nheader | awk '{print $1+1}')
        fi
        if [ $nheader -lt 1 ]
        then
            nheader=1
        fi
    else
        nheader=1
    fi
    tail -n +$nheader $fout | region2bed.sh -0 | sortBed -i - > ${fout}.bed
elif [[ $modein =~ bed ]]
then
    nheaderx=$(echo $modein | sed "s/bed//")
    if [[ $nheaderx =~ i ]] || [[ $nheaderx =~ h ]]
    then
        nheader=$(echo $nheaderx | sed "s/.*[iho]//")
        if [ ${#nheader} -lt 1 ]
        then
            nheader=2
        else
            nheader=$(echo $nheader | awk '{print $1+1}')
        fi
        if [ $nheader -lt 1 ]
        then
            nheader=1
        fi
    else
        nheader=1
    fi
    nbed=$(echo $nheaderx | sed "s/[iho].*//")
    if [ ${#nbed} -gt 0 ]
    then
        nbed=$nbed
    else
        nbed=$(head -n 1 $fout | awk '{printf NF}')
    fi
    echo "chr start end pk_name pk_score pk_strand " | tabnNA.sh $nbed | tr "\n" "\t" > $fwrout
    echo $suff >> $fwrout
    tabit.sh $fwrout
    tail -n +$nheader $fout | tabnNA.sh $nbed | sortBed -i - > ${fout}.bed
fi

fbed=${fout}.bed


(cat $fanno | winandgroup.sh ${fbed} 4,7 distinct,distinct $dis ; cat ${fbed} | windowBed -a - -b $fanno -w $dis -v | awk '{print $0," . . "}' ) | tabit.sh | sortBed -i - > ${fout}.tmp1
windowBed -a ${fout}.tmp1 -b $fanno -w $dis -v | tabit.sh > ${fout}.tmp2
windowBed -a ${fout}.tmp2 -b $fanno -w $dis2 -v | awk '{print $0," . . "}' > ${fout}.tmp4
(cat $fanno | winandgroup.sh ${fout}.tmp2 4,7 distinct,distinct $dis2 ; windowBed -a ${fout}.tmp1 -b $fanno -w $dis -u | awk '{print $0," . . "}')  > ${fout}.tmp44
cat ${fout}.tmp4 ${fout}.tmp44 | tabit.sh | sortBed -i > ${fout}.tmp3
cat $fanno | closestBed -a ${fout}.tmp3 -b - -d -t first | awk '{$(NF-1)=$(NF-4)=$(NF-3)=$(NF-7)=$(NF-6)=$(NF-8)=""; print $0}' | tabit.sh | sortBed -i >> $fwrout # closest

if [[ $modein =~ bed ]] && [[ $modein =~ h ]]
then
    nnheader=$(echo $nheader | awk '{print $1-1}')
    (head -n $nnheader $fout | sed "s/$/ $suff/" | sed "s/name1.*name2.*name3/chr:start-end/;s/chr:0-0/Region/" | tabit.sh ; cat $fwrout | tail -n +$nheader | tabit.sh | bed2region.sh -0 | sed "s/chr:0-0/Region/") > ${fwrout}.tmp
    mv ${fwrout}{.tmp,}
elif [[ $modein =~ bed ]] && [[ $modein =~ i ]]
then
    (head -n 1 $fwrout | tabit.sh | sed "s/chr.*start.*end/Region/" ; cat $fwrout | tail -n +2 | tabit.sh | bed2region.sh -0) > ${fwrout}.tmp
    mv ${fwrout}{.tmp,}
elif [[ $modein =~ bed ]] && [[ $modein =~ o ]]
then
    echo no
elif [[ $modein =~ pktest ]] && [[ $modein =~ h ]]
then
    nnheader=$(echo $nheader | awk '{print $1-1}')
    head -n $nnheader $fout | sed "s/$/ $suff/" | tabit.sh > ${fwrout}.tmp
    cat $fwrout | bed2region.sh -0 | sort -gk 2 >> ${fwrout}.tmp
    mv ${fwrout}.tmp $fwrout
fi
# Clean up temp files (use -f to suppress errors for non-existent files)
rm -f ${fout}.{tmp,tmp0,tmp1,tmp2,tmp3,tmp4,tmp44,bed} 2>/dev/null || true
