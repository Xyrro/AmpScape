#!/bin/bash
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
nvidia-smi --query-gpu=name,memory.total --format=csv
python -c 'import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.is_bf16_supported())'
for m in unet fno vit gnn; do
  echo "== smoke $m"
  python scripts/train.py --model $m --task T1 --tier S --root data/builds/mini --out runs/smoke/${m}_T1 --epochs 2 --max-train 64 --batch 8 --workers 2 --eval-splits test_id --published-root none --time-budget-min 5 2>&1 | grep -v Warning | tail -6
done
echo "== smoke T3/T4 unet"
python scripts/train.py --model unet --task T3 --tier S --root data/builds/mini --out runs/smoke/unet_T3 --epochs 1 --max-train 32 --batch 8 --workers 2 --eval-splits test_id --published-root none 2>&1 | grep -v Warning | tail -3
python scripts/train.py --model unet --task T4 --tier S --root data/builds/mini --out runs/smoke/unet_T4 --epochs 1 --max-train 32 --batch 8 --workers 2 --eval-splits test_id --published-root none 2>&1 | grep -v Warning | tail -3
echo "== done"
