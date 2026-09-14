#!/bin/bash
# usage: sbatch ... train_one.sh <model> <task> [published_tiers]
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
M=$1; T=$2; PT=${3:-S}
echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader) model=$M task=$T start=$(date -u +%FT%TZ)"
python scripts/train.py --model $M --task $T --tier S --root data/dev/S --out runs/dev/${M}_${T} \
    --epochs 120 --patience 12 --batch 16 --workers 4 --time-budget-min 75 \
    --eval-splits test_id,test_ood,ood_region --published-root data/builds/published --published-tiers $PT 2>&1 | grep -v Warning
echo "end=$(date -u +%FT%TZ)"
