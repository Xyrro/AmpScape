#!/bin/bash
# Review round 2 (owner, 2026-10-17; budget 16 GPU-h): MgNO seeds 2-3 at S/M on T1/T4, scale-aware seeds 2-3 of the two
# best T4 L models (U-Net, FNO w48), one U-Net T4 run trained at XL (880 landscapes). H200 on ice-gpu under coc-ice
# (the owner's other projects run on coe-gpu). Each job is one train_full.sbatch leg (self re-queue if it pauses).
# Usage: bash scripts/review/submit_round2_gpu.sh [--dry]
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
DRY=${1:-}
GRES=${GRES:-gpu:h200:1}; PART=${PART:-ice-gpu}; QOS=coc-ice; WALL=03:00:00
submit() {  # model task tier seed out extra group localdata batch cpus mem
  local MODEL=$1 TASK=$2 TIER=$3 SEED=$4 OUT=$5 EXTRA=$6 GROUP=$7 LOCAL=$8 BATCH=$9 CPUS=${10} MEM=${11}
  if [ -f "$OUT/results.json" ]; then echo "skip $OUT (results exist)"; return; fi
  if squeue -u $USER -h -o "%j" | grep -qx "r2-$(basename "$OUT")"; then echo "skip $OUT (queued or running)"; return; fi
  mkdir -p "$OUT"
  local EXCL=""; [ -s logs/gpu_bad_nodes.txt ] && EXCL="--exclude=$(tr "\n" "," < logs/gpu_bad_nodes.txt | sed "s/,$//")"
  local CMD=(sbatch --parsable $EXCL -A coc -q $QOS -p $PART -N1 -n1 -c "$CPUS" --mem="$MEM" --gres="$GRES" -t $WALL
    -J "r2-$(basename "$OUT")" -o "$OUT/slurm_%j.out"
    --export=ALL,MODEL="$MODEL",TASK="$TASK",TIER="$TIER",SEED="$SEED",OUT="$OUT",ROOT=data/hfcache,EPOCHS=30,BATCH="$BATCH",PATIENCE=8,WORKERS="$CPUS",MAXTRAIN=,EXTRA="$EXTRA",MEM="$MEM",GRES="$GRES",WALL=$WALL,PACK=1,PREFETCH=2,QOS=$QOS,LOCALDATA="$LOCAL",GROUP="$GROUP"
    scripts/slurm/gpu/train_full.sbatch)
  if [ "$DRY" = "--dry" ]; then echo "${CMD[*]}"; else echo "$(basename "$OUT"): job $("${CMD[@]}")"; fi
}
# MgNO seeds 2-3 (point 2/8): official config 'base', data fetched to node NVMe
for SEED in 2 3; do
  for TASK in T1 T4; do
    submit mgno $TASK S $SEED runs/full/mgno_${TASK}_S_s$SEED "" $TASK 1 16 6 64G
    submit mgno $TASK M $SEED runs/full/mgno_${TASK}_M_s$SEED "" $TASK 1 8 6 96G
  done
done
# scale-aware target, seeds 2-3 of the two best T4 L models (point 8)
for SEED in 2 3; do
  submit unet T4 L $SEED runs/full/unet_T4_L_s${SEED}_scalenorm "--target-norm scale" T4 1 4 8 128G
  submit fno T4 L $SEED runs/full/fno_T4_L_s${SEED}_t2_scalenorm "--variant w48 --target-norm scale" T4 1 4 8 128G
done
# trained at XL (point 7): U-Net T4 on the 880 XL training landscapes; XL/T4 is staged on scratch
submit unet T4 XL 1 runs/full/unet_T4_XL_s1 "" T4 0 2 8 160G
