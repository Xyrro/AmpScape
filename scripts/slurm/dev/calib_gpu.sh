#!/bin/bash
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
for m in unet fno vit gnn; do
  echo "== calib $m"
  python scripts/train.py --model $m --task T1 --tier S --root data/builds/mini --out runs/calib/${m}_T1 --epochs 3 --batch 16 --workers 4 --eval-splits test_id --published-root none --time-budget-min 10 2>&1 | grep -v Warning | grep "epoch\|predictions"
done
