#!/bin/bash
# usage: sbatch ... tune_one.sh <model> <variant> <extra|none> <task> [budget_min]
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
M=$1; V=$2; X=$3; T=$4; B=${5:-60}
[ "$X" = "none" ] && XA="" || XA="--extra $X"
NAME=${M}-${V}$([ "$X" = "none" ] || echo "+$X")_${T}
echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader) run=$NAME start=$(date -u +%FT%TZ)"
python scripts/train.py --model $M --variant $V $XA --task $T --tier S --root data/dev/S --out runs/tune/$NAME \
    --epochs 120 --patience 12 --batch 16 --workers 4 --time-budget-min $B \
    --eval-splits test_id,test_ood,ood_region --published-root data/builds/published --published-tiers S 2>&1 | grep -v Warning
echo "end=$(date -u +%FT%TZ)"
