#!/bin/bash
#SBATCH -J r3-build
#SBATCH -A coc -q coc-ice -p coc-cpu
#SBATCH -N1 -n1 -c 2 --mem=16G -t 02:00:00
#SBATCH -o aux/review_round3/logs/build_%j.out
# Review round 3: solver inputs from the production Hub files — L block-1 reference top-up (60 samples) and the
# T4 source-rule sets (S: 4 rules incl. the production rule as a pipeline check; M: 3 new rules).
set -eu
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export HF_HUB_DISABLE_XET=1
B=scripts/review/r3_build_from_hub.py
python $B build --tier L --out aux/t4_bs1_reference/L_bs1_topup --block 1 --shard-size 1
for R in default uniform random_field habitat_core; do
  python $B build --tier S --out aux/review_round3/source_ood/S_$R --sel aux/review_round3/source_ood/S_sel/selection.parquet --rule $R --shard-size 50
done
for R in uniform random_field habitat_core; do
  python $B build --tier M --out aux/review_round3/source_ood/M_$R --sel aux/review_round3/source_ood/M_sel/selection.parquet --rule $R --shard-size 10
done
echo done
