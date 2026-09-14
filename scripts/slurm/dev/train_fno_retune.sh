#!/bin/bash
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
echo "host=$(hostname) start=$(date -u +%FT%TZ)"
python scripts/train.py --model fno --task T1 --tier S --root data/dev/S --out runs/dev/fno_T1_lr3e-4 --lr 3e-4 \
    --epochs 120 --patience 12 --batch 16 --workers 4 --time-budget-min 75 \
    --eval-splits test_id,test_ood,ood_region --published-root data/builds/published --published-tiers S,XXL 2>&1 | grep -v Warning
echo "end=$(date -u +%FT%TZ)"
