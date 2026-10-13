#!/bin/bash
# GPU-type timing probe (owner 2026-10-13): one epoch of the official config for (MODEL, TASK, TIER) on the staged
# cache, evaluation on test_id only, output under work/probe/. Prints the GPU, driver and torch build, the queue
# wait (submit → start) and the epoch time from log.csv. Usage (the owner/driver submits it):
#   sbatch -A coc -q coc-ice -p ice-gpu --gres=gpu:h200:1 -c6 --mem=48G -t 00:40:00 -J probe-unet-M-h200 \
#     -o logs/probe/%x_%j.out --export=ALL,MODEL=unet,TASK=T4,TIER=M,BATCH=16 scripts/slurm/gpu/gpu_probe.sbatch
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-6}
SUBMIT=$(scontrol show job "$SLURM_JOB_ID" | grep -oE 'SubmitTime=[^ ]+' | cut -d= -f2)
START=$(scontrol show job "$SLURM_JOB_ID" | grep -oE 'StartTime=[^ ]+' | cut -d= -f2)
WAIT_S=$(( $(date -d "$START" +%s) - $(date -d "$SUBMIT" +%s) ))
echo "host=$(hostname) partition=$SLURM_JOB_PARTITION job=$SLURM_JOB_ID submit=$SUBMIT start=$START wait_s=$WAIT_S"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda runtime", torch.version.cuda, "device", torch.cuda.get_device_name(0), "capability", torch.cuda.get_device_capability(0))
PY
OUT=work/probe/${MODEL}_${TASK}_${TIER}_${SLURM_JOB_ID}
rm -rf "$OUT"; mkdir -p "$OUT"
ROOT=${ROOT:-data/hfcache}; LOCALBASE=${TMPDIR:-/tmp}/ampscape_$USER
OPTS=""
if [ "${LOCAL:-0}" = "1" ]; then   # option (a): the tier's task-group files on the node's local disk
  T0=$(date +%s); L=$LOCALBASE/hfcache_$SLURM_JOB_ID; mkdir -p "$L/data/$TIER"
  cp -r "$ROOT/index" "$ROOT/splits" "$ROOT/stats" "$L/" && cp -r "$ROOT/data/$TIER/$TASK" "$L/data/$TIER/"
  echo "local copy of $TIER/$TASK: $(du -sh "$L" | cut -f1) in $(( $(date +%s) - T0 )) s to $L ($(df -h "$L" | tail -1 | awk '{print $4" free"}'))"
  ROOT=$L
fi
if [ "${PACK:-0}" = "1" ]; then OPTS="$OPTS --packed-dir $LOCALBASE/pack"; fi   # option (c)
[ -n "${PREFETCH:-}" ] && OPTS="$OPTS --prefetch $PREFETCH"                      # option (b)
T0=$(date +%s)
python scripts/train.py --model "$MODEL" --task "$TASK" --tier "$TIER" --root "$ROOT" --out "$OUT" \
  --seed 1 --epochs "${EPOCHS:-1}" --batch "${BATCH:-16}" --workers "${WORKERS:-6}" --patience 8 --time-budget-min 30 \
  --eval-splits test_id $OPTS ${EXTRA:-} 2>&1 | grep -v Warning | grep -E 'pack|epoch|rel_l2|Error|error' | tail -8
echo "exit=${PIPESTATUS[0]} total_s=$(( $(date +%s) - T0 ))"
[ "${LOCAL:-0}" = "1" ] && rm -rf "$L"
echo "log.csv: $(tail -1 "$OUT/log.csv" 2>/dev/null)"
echo "PROBE model=$MODEL task=$TASK tier=$TIER local=${LOCAL:-0} pack=${PACK:-0} prefetch=${PREFETCH:-2} batch=${BATCH:-16} workers=${WORKERS:-6} gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | tr ' ' '_') wait_s=$WAIT_S epoch_s=$(tail -1 "$OUT/log.csv" 2>/dev/null | cut -d, -f5) epochs=$(tail -n +2 "$OUT/log.csv" 2>/dev/null | cut -d, -f5 | tr "\n" "/") total_s=$(( $(date +%s) - T0 ))"
rm -rf "$OUT/predictions"
