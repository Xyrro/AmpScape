#!/bin/bash
#SBATCH -J r3-prep-Lref
#SBATCH -A coc -q coc-ice -p coc-cpu
#SBATCH -N1 -n1 -c 2 --mem=16G -t 01:00:00
#SBATCH -o aux/review_round3/logs/prep_Lref_%j.out
# Review round 3, point 3a: inputs for the 60 added L block-1 reference samples (shards 60-119; 0-59 are kept).
set -eu
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
python scripts/aux_t4_blocks.py prepare --out aux/t4_bs1_reference/L_bs1 --build data/v1/L --block 1 --shard-size 1
