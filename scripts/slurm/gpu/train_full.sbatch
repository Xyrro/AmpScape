#!/bin/bash
# Phase 10-full baseline job on ICE (owner 2026-09-24): train one (model, task, tier, seed) with the official config,
# resumable across the 16-h walltime (train.py --resume --pause-exit + self re-queue), then evaluate through the harness
# (test_id / test_ood / ood_region, published tiles; T4 rows at M/L also against the exact block-1 reference and the
# block-size rows). Usage (the driver submits it):
#   sbatch ... --export=ALL,MODEL=unet,TASK=T1,TIER=S,SEED=1,OUT=runs/full/unet_T1_S_s1,ROOT=data/hfcache,EPOCHS=30,BATCH=16 train_full.sbatch
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-6}
ROOT=${ROOT:-data/hfcache}; EPOCHS=${EPOCHS:-30}; BATCH=${BATCH:-16}; PATIENCE=${PATIENCE:-8}; WORKERS=${WORKERS:-6}
MAXTRAIN=${MAXTRAIN:-}; EXTRA=${EXTRA:-}
mkdir -p "$OUT"
echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1) model=$MODEL task=$TASK tier=$TIER seed=$SEED start=$(date -u +%FT%TZ) job=$SLURM_JOB_ID"
# leave 45 min of the walltime for checkpointing + evaluation; the walltime is in $SLURM_JOB_END_TIME
if [ -n "${SLURM_JOB_END_TIME:-}" ]; then BUDGET=$(( ( SLURM_JOB_END_TIME - $(date +%s) ) / 60 - 45 )); else BUDGET=${BUDGET_MIN:-900}; fi
[ "$BUDGET" -lt 30 ] && BUDGET=30
ARGS=(--model "$MODEL" --task "$TASK" --tier "$TIER" --root "$ROOT" --out "$OUT" --seed "$SEED" --epochs "$EPOCHS" --batch "$BATCH" \
      --patience "$PATIENCE" --workers "$WORKERS" --time-budget-min "$BUDGET" --resume --pause-exit \
      --eval-splits test_id,test_ood,ood_region --published-root data/builds/published --published-tiers "$TIER")
[ -n "$MAXTRAIN" ] && ARGS+=(--max-train "$MAXTRAIN")
[ -n "$EXTRA" ] && ARGS+=($EXTRA)
python scripts/train.py "${ARGS[@]}" 2>&1 | grep -v Warning | tee -a "$OUT/train.log" | tail -40
# re-queue only when THIS job paused on its time budget (paused.json carries the job id): a job that crashed (bad GPU,
# missing file) must not re-queue itself — the driver re-submits it elsewhere. Cap: 40 re-queues per run.
PJ=$(python -c "import json,sys; print(json.load(open('$OUT/paused.json')).get('job',''))" 2>/dev/null || echo "")
NRQ=$(cat "$OUT/requeues.txt" 2>/dev/null || echo 0)
EXCL=""; [ -s logs/gpu_bad_nodes.txt ] && EXCL="--exclude=$(tr '\n' ',' < logs/gpu_bad_nodes.txt | sed 's/,$//')"
if [ -f "$OUT/paused.json" ] && [ ! -f "$OUT/done.json" ] && [ "$PJ" = "$SLURM_JOB_ID" ] && [ "$NRQ" -lt 40 ]; then
  echo $((NRQ + 1)) > "$OUT/requeues.txt"
  echo "paused at $(cat "$OUT/paused.json"); re-queueing with --resume (re-queue $((NRQ + 1)), $EXCL)"
  sbatch --parsable $EXCL -A coc -q coc-ice -p "${SLURM_JOB_PARTITION}" -N1 -n1 -c "${SLURM_CPUS_PER_TASK:-6}" --mem="${MEM:-48G}" \
    --gres="${GRES:-gpu:1}" -t "${WALL:-16:00:00}" -J "$SLURM_JOB_NAME" -o "$OUT/slurm_%j.out" \
    --export=ALL,MODEL="$MODEL",TASK="$TASK",TIER="$TIER",SEED="$SEED",OUT="$OUT",ROOT="$ROOT",EPOCHS="$EPOCHS",BATCH="$BATCH",PATIENCE="$PATIENCE",WORKERS="$WORKERS",MAXTRAIN="$MAXTRAIN",EXTRA="$EXTRA",MEM="${MEM:-48G}",GRES="${GRES:-gpu:1}",WALL="${WALL:-16:00:00}" \
    scripts/slurm/gpu/train_full.sbatch
  exit 0
fi
# T4 at M / L: the official evaluation surface is the exact block-1 reference (docs/t4_fidelity.md) + block-size rows
if [ "$TASK" = "T4" ] && [ -f "$OUT/predictions/T4/predictions.h5" ] && { [ "$TIER" = "M" ] || [ "$TIER" = "L" ]; }; then
  REF=aux/t4_bs1_reference/${TIER}_bs1
  BLOCKS=$(ls -d aux/t4_blocksize_baselines/${TIER}_* 2>/dev/null | tr '\n' ' ')
  python scripts/evaluate.py --predictions "$OUT/predictions/T4" --root "$ROOT" --tier "$TIER" --split test_id \
      --t4-reference "$REF" --t4-blocks $BLOCKS --out "$OUT/eval_t4_reference" 2>&1 | grep -v Warning | tail -5
fi
echo "end=$(date -u +%FT%TZ)"
