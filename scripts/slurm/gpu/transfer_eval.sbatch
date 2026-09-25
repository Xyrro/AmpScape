#!/bin/bash
# Scale-transfer evaluation leg (docs/phase10_full_schedule.md §5): an S/M/L-trained run evaluated at XL or XXL.
# Submitted by gpu_driver.py with --export RUN,TIER,SPLITS,MEM,GRES,WALL; resumable per split (transfer_eval.py).
# SPLITS is '+'-separated: a comma inside an --export value is split by Slurm (08:30Z: only test_id ran).
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
source scripts/env.sh
echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1) run=$RUN tier=$TIER start=$(date -u +%FT%TZ) job=$SLURM_JOB_ID"
python scripts/transfer_eval.py --run "$RUN" --tier "$TIER" --splits "$(echo "${SPLITS:-test_id+test_ood+ood_region}" | tr "+" ",")" --root data/hfcache --workers "${SLURM_CPUS_PER_TASK:-8}"
echo "end=$(date -u +%FT%TZ) rc=$?"
