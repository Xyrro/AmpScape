#!/bin/bash
#SBATCH -J phase10-wp7-demo
#SBATCH -A coc
#SBATCH -q coc-ice
#SBATCH -p coc-gpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 6
#SBATCH --mem=96G
#SBATCH --gres=gpu:l40s:1
#SBATCH -t 04:00:00
#SBATCH -o logs/wp7_demo_%j.out
# WP7 many-query demonstration with the best T4 model at L (docs/phase10_full_schedule.md):
#   RUN=runs/full/unet_T4_L_s1 sbatch scripts/slurm/gpu/wp7_demo.sbatch
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
source scripts/env.sh
echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1) run=$RUN start=$(date -u +%FT%TZ)"
python scripts/wp7_demo.py run --run "$RUN"
echo "end=$(date -u +%FT%TZ)"
