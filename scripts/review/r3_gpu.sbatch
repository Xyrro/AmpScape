#!/bin/bash
#SBATCH -A coc -q coc-ice -p ice-gpu
#SBATCH -N1 -n1 -c 6 --mem=48G --gres=gpu:h100:1 -t 02:00:00
# Review round 3 GPU step: CMD is one of
#   decision          python scripts/review/r3_decision.py predict
#   source_ood_<tier> python scripts/review/r3_t4_eval.py models --tier <tier>
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export HF_HUB_DISABLE_XET=1 OMP_NUM_THREADS=6
echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1) step=$STEP start=$(date -u +%FT%TZ)"
case "$STEP" in
  decision) python scripts/review/r3_decision.py predict; python scripts/review/r3_decision.py predict --fp32 ;;
  source_ood_*) python scripts/review/r3_t4_eval.py models --tier "${STEP#source_ood_}" ;;
esac
echo "end=$(date -u +%FT%TZ)"
