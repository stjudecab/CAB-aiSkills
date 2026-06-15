#!/bin/bash
wc -l | awk '{printf $1"\t"}'
