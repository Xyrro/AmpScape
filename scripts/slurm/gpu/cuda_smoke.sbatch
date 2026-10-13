#!/bin/bash
# One-epoch training smoke test on a cuda13 GPU node (node feature `cuda13`; owner request 2026-10-13 before the
# L-tier tuning pass): prints driver / CUDA versions seen by torch, trains U-Net T1 one epoch on the mini build and
# evaluates test_id. Usage:
#   sbatch -A coc -q coc-ice -p coc-gpu --constraint=cuda13 --gres=gpu:1 -c4 --mem=24G -t 00:30:00 \
#     -J cuda13-smoke -o logs/smoke/cuda13_smoke_%j.out scripts/slurm/gpu/cuda_smoke.sbatch
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
echo "host=$(hostname) job=$SLURM_JOB_ID start=$(date -u +%FT%TZ)"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
nvidia-smi | head -4 | tail -2
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda runtime", torch.version.cuda, "cudnn", torch.backends.cudnn.version())
print("device", torch.cuda.get_device_name(0), "capability", torch.cuda.get_device_capability(0))
x = torch.randn(1024, 1024, device="cuda")
print("matmul ok", float((x @ x).sum()))
PY
OUT=${OUT:-work/cuda13_smoke}
rm -rf "$OUT"
python scripts/train.py --model "${MODEL:-unet}" --task "${TASK:-T1}" --tier S --root data/builds/mini --out "$OUT" \
  --seed 1 --epochs 1 --batch 4 --workers 2 --eval-splits test_id 2>&1 | grep -v Warning | tail -15
echo "exit=${PIPESTATUS[0]} end=$(date -u +%FT%TZ)"
