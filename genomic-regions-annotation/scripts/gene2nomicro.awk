#!/bin/awk -f

BEGIN {
    if (icol > 0){
    icol=icol;
} else { icol=1 }
IGNORECASE=1;
}
$icol !~ /^G[Mm][0-9]+/ && $icol !~ /[^ ]*R[Ii][Kk][0-9]*$/ && $icol !~ /^RP[0-9L]{1,2}-/ && $icol !~ /^A[CDLP][0-9]+\.[0-9]/ && $icol !~ /^CT[ABCD]-/ && $icol !~ /^IG[HKJL]/ && $icol !~ /^MIR[0-9]+/ && $icol !~ /^KB-/ && $icol !~ /^MT-/ && $icol !~ /^RN7S/ && $icol !~ /^RN5SP/ && $icol !~ /^RNU[0-9]+/ && $icol !~ /^SNOR[AD]/ && $icol !~ /^TR[ABCDG][VJ][0-9]/ && $icol !~ /^XXbac-/ && $icol !~ /^RNA5SP/ && $icol !~ /^LA16c-/ && $icol !~ /^ATP[0-9]/ && $icol !~ /^A[AIUVW][0-9]{6}/ &&  $icol !~ /^CAAA[0-9]{8}/ && $icol !~ /^B[CX][0-9]{6}/ && $icol !~ /^mmu-mir-/ && $icol !~ /^n-R5s/{print $0}
