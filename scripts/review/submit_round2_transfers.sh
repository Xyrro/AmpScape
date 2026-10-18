#!/bin/bash
# Review round 2: XL and XXL scale-transfer legs for the new scale-aware seeds once their training finished
# (done.json present, results_transfer.json without the tier yet). Same template as the driver's submit_transfer.
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
GRES=${GRES:-gpu:h200:1}; PART=${PART:-ice-gpu}
for RUN in runs/full/unet_T4_L_s2_scalenorm runs/full/unet_T4_L_s3_scalenorm runs/full/fno_T4_L_s2_t2_scalenorm runs/full/fno_T4_L_s3_t2_scalenorm; do
  [ -f "$RUN/done.json" ] || { echo "$RUN: not done"; continue; }
  TIERS="XL XXL"; case "$RUN" in *fno*) TIERS="${FNO_TIERS:-XL XXL}";; esac   # FNO_TIERS=XL keeps the FNO seeds inside the GPU budget
  for TIER in $TIERS; do
    if python -c "import json,sys; d=json.load(open('$RUN/results_transfer.json')); sys.exit(0 if any(k.endswith('_${TIER}_test_id') for k in d.get('eval',{})) else 1)" 2>/dev/null; then echo "$RUN $TIER: done"; continue; fi
    if squeue -u $USER -h -o "%j" | grep -q "r2-xfer_$(basename $RUN)_$TIER"; then echo "$RUN $TIER: queued"; continue; fi
    MEM=$([ "$TIER" = XL ] && echo 96G || echo 160G)
    JID=$(sbatch --parsable -A coc -q coc-ice -p $PART -N1 -n1 -c8 --mem=$MEM --gres=$GRES -t 02:00:00 -J "r2-xfer_$(basename $RUN)_$TIER" -o "$RUN/xfer_${TIER}_%j.out" \
      --export=ALL,RUN=$RUN,TIER=$TIER,SPLITS=test_id,KEEP=none,MEM=$MEM,GRES=$GRES,WALL=02:00:00 scripts/slurm/gpu/transfer_eval.sbatch)
    echo "$RUN $TIER: job $JID"
  done
done
