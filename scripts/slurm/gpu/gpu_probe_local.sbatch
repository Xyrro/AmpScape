#!/bin/bash
# L-tier timing probe without scratch (2026-10-13): fetch one (TIER, TASK) group from the Hub straight onto the compute
# node's local NVMe, pack it once, and time one epoch of each model in MODELS (default "unet fno") on that node's GPU.
#   sbatch -A coc -q coc-ice -p ice-gpu --gres=gpu:h200:1 -c12 --mem=128G -t 01:30:00 -J probe-L-h200-local \
#     -o logs/probe/%x_%j.out --export=ALL,TASK=T1,TIER=L,BATCH=4 scripts/slurm/gpu/gpu_probe_local.sbatch
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
echo "host=$(hostname) partition=$SLURM_JOB_PARTITION job=$SLURM_JOB_ID gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1) start=$(date -u +%FT%TZ)"
L=${TMPDIR:-/tmp}/ampscape_$USER/hfcache_local_$SLURM_JOB_ID; mkdir -p "$L/stats"
cp data/hfcache/stats/norm_stats.json "$L/stats/" 2>/dev/null
T0=$(date +%s)
python scripts/slurm/gpu/stage_data.py stage --cache "$L" --tier "$TIER" --group "$TASK" --workers "${DLW:-8}" 2>&1 | tail -2
echo "fetched $TIER/$TASK to local NVMe in $(( $(date +%s) - T0 )) s ($(du -sh "$L" | cut -f1); $(df -h "$L" | tail -1 | awk '{print $4" free"}'))"
for MODEL in ${MODELS:-unet fno}; do
  OUT=work/probe/${MODEL}_${TASK}_${TIER}_${SLURM_JOB_ID}; rm -rf "$OUT"; mkdir -p "$OUT"
  T1=$(date +%s)
  python scripts/train.py --model "$MODEL" --task "$TASK" --tier "$TIER" --root "$L" --out "$OUT" --seed 1 --epochs "${EPOCHS:-1}" \
    --batch "${BATCH:-4}" --workers "${WORKERS:-8}" --patience 8 --time-budget-min 40 --eval-splits test_id \
    --packed-dir "${TMPDIR:-/tmp}/ampscape_$USER/pack" ${EXTRA:-} 2>&1 | grep -v Warning | grep -E 'pack|epoch|Error|error' | tail -6
  echo "PROBE model=$MODEL task=$TASK tier=$TIER pack=1 batch=${BATCH:-4} workers=${WORKERS:-8} gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | tr ' ' '_') epoch_s=$(tail -1 "$OUT/log.csv" 2>/dev/null | cut -d, -f5) epochs=$(tail -n +2 "$OUT/log.csv" 2>/dev/null | cut -d, -f5 | tr '\n' '/') total_s=$(( $(date +%s) - T1 )) losses=$(sed -n 2p "$OUT/log.csv" | cut -d, -f2,3)"
  rm -rf "$OUT/predictions"
done
rm -rf "$L"
echo "end=$(date -u +%FT%TZ)"
