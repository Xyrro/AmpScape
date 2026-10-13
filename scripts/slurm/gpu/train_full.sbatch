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
# leave 15 min of the walltime for the checkpoint + (on the final leg) evaluation; the walltime is in $SLURM_JOB_END_TIME
if [ -n "${SLURM_JOB_END_TIME:-}" ]; then BUDGET=$(( ( SLURM_JOB_END_TIME - $(date +%s) ) / 60 - 15 )); else BUDGET=${BUDGET_MIN:-100}; fi
[ "$BUDGET" -lt 20 ] && BUDGET=20
# LOCALDATA=1 (2026-10-13, GNN legs): fetch the (TIER, GROUP) group from the Hub straight to the node's NVMe
# (compute nodes have outbound HTTPS; 79 GB in ≈ 19 min with 8 workers) and train from there — no scratch pinning.
# One copy per node, keyed by tier/group, lock-protected, reused by later legs on the same node, 2-day cleanup.
if [ "${LOCALDATA:-0}" = "1" ]; then
  LBASE=${TMPDIR:-/tmp}/ampscape_$USER/hfcache; mkdir -p "$LBASE"
  find "$LBASE" -mindepth 1 -maxdepth 1 -type d -mtime +2 -exec rm -rf {} + 2>/dev/null
  LROOT=$LBASE/${TIER}_${GROUP}; mkdir -p "$LROOT/stats"
  cp "$ROOT/stats/norm_stats.json" "$LROOT/stats/"
  (
    flock 9
    if [ ! -f "$LROOT/staged/${TIER}_${GROUP}.json" ]; then
      T0=$(date +%s)
      python scripts/slurm/gpu/stage_data.py stage --cache "$LROOT" --tier "$TIER" --group "$GROUP" --workers "${FETCH_WORKERS:-16}" 2>&1 | tail -1
      echo "fetched $TIER/$GROUP to $LROOT in $(( $(date +%s) - T0 )) s ($(du -sh "$LROOT" | cut -f1); $(df -h "$LROOT" | tail -1 | awk '{print $4" free"}'))"
    else
      echo "local copy of $TIER/$GROUP on $(hostname) reused"
    fi
  ) 9>"$LROOT.lock"
  if [ -f "$LROOT/staged/${TIER}_${GROUP}.json" ]; then ROOT=$LROOT; else echo "local fetch failed; falling back to $ROOT"; fi
fi
ARGS=(--model "$MODEL" --task "$TASK" --tier "$TIER" --root "$ROOT" --out "$OUT" --seed "$SEED" --epochs "$EPOCHS" --batch "$BATCH" \
      --patience "$PATIENCE" --workers "$WORKERS" --time-budget-min "$BUDGET" --resume --pause-exit \
      --eval-splits test_id,test_ood,ood_region --published-root data/builds/published --published-tiers "$TIER")
[ -n "$MAXTRAIN" ] && ARGS+=(--max-train "$MAXTRAIN")
[ -n "$EXTRA" ] && ARGS+=($EXTRA)
# PACK=1 (2026-10-13): train/val items packed once per job to the node's local NVMe (${TMPDIR:-/tmp}) and read as
# memmaps — the epoch was bound by gzip/HDF5 decoding in the loader workers (ampscape/data/packed.py; identical
# tensors; the GNN keeps the HDF5 path). Packs older than 2 days under our local dir are removed first.
if [ "${PACK:-0}" = "1" ]; then
  PACKDIR=${TMPDIR:-/tmp}/ampscape_$USER/pack; mkdir -p "$PACKDIR"
  find "$PACKDIR" -mindepth 1 -maxdepth 1 -type d -mtime +2 -exec rm -rf {} + 2>/dev/null
  ARGS+=(--packed-dir "$PACKDIR" --prefetch "${PREFETCH:-2}")
fi
python scripts/train.py "${ARGS[@]}" 2>&1 | grep -v Warning | tee -a "$OUT/train.log" | tail -40
# re-queue only when THIS job paused on its time budget (paused.json carries the job id): a job that crashed (bad GPU,
# missing file) must not re-queue itself — the driver re-submits it elsewhere. Cap: 120 re-queues per run (2-h legs).
PJ=$(python -c "import json,sys; print(json.load(open('$OUT/paused.json')).get('job',''))" 2>/dev/null || echo "")
NRQ=$(cat "$OUT/requeues.txt" 2>/dev/null || echo 0)
EXCL=""; [ -s logs/gpu_bad_nodes.txt ] && EXCL="--exclude=$(tr '\n' ',' < logs/gpu_bad_nodes.txt | sed 's/,$//')"
if [ -f "$OUT/paused.json" ] && [ ! -f "$OUT/results.json" ] && [ "$PJ" = "$SLURM_JOB_ID" ] && [ "$NRQ" -lt 120 ]; then
  echo $((NRQ + 1)) > "$OUT/requeues.txt"
  echo "paused at $(cat "$OUT/paused.json"); re-queueing with --resume (re-queue $((NRQ + 1)), $EXCL)"
  sbatch --parsable $EXCL -A coc -q "${QOS:-coc-ice}" -p "${SLURM_JOB_PARTITION}" -N1 -n1 -c "${SLURM_CPUS_PER_TASK:-6}" --mem="${MEM:-48G}" \
    --gres="${GRES:-gpu:1}" -t "${WALL:-16:00:00}" -J "$SLURM_JOB_NAME" -o "$OUT/slurm_%j.out" \
    --export=ALL,MODEL="$MODEL",TASK="$TASK",TIER="$TIER",SEED="$SEED",OUT="$OUT",ROOT="$ROOT",EPOCHS="$EPOCHS",BATCH="$BATCH",PATIENCE="$PATIENCE",WORKERS="$WORKERS",MAXTRAIN="$MAXTRAIN",EXTRA="$EXTRA",MEM="${MEM:-48G}",GRES="${GRES:-gpu:1}",WALL="${WALL:-16:00:00}",PACK="${PACK:-0}",PREFETCH="${PREFETCH:-2}",QOS="${QOS:-coc-ice}",LOCALDATA="${LOCALDATA:-0}",GROUP="${GROUP:-}" \
    scripts/slurm/gpu/train_full.sbatch
  exit 0
fi
# T4 at M / L: the official evaluation surface is the exact block-1 reference (docs/t4_fidelity.md) + block-size rows
PRED="$OUT/predictions/hfcache_${TIER}_test_id"
if [ "$TASK" = "T4" ] && [ -f "$PRED/predictions.h5" ] && { [ "$TIER" = "M" ] || [ "$TIER" = "L" ]; }; then
  REF=aux/t4_bs1_reference/${TIER}_bs1
  BLOCKS=$(ls -d aux/t4_blocksize_baselines/${TIER}_* 2>/dev/null | tr '\n' ' ')
  python scripts/evaluate.py --predictions "$PRED" --root "$ROOT" --tier "$TIER" --split test_id \
      --t4-reference "$REF" --t4-blocks $BLOCKS --out "$OUT/eval_t4_reference" 2>&1 | grep -v Warning | tail -5
fi
echo "end=$(date -u +%FT%TZ)"
