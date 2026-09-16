#!/bin/bash
# usage: sbatch --array=0-9 finalize_range.sh <build> <shards_per_task>
# Finalizes every shard of its range as soon as the solver outputs exist; polls every 5 min until all are done
# (or the walltime ends) so it can be submitted while the solve array is still running.
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
B=$1; N=$2; LO=$((SLURM_ARRAY_TASK_ID * N)); HI=$((LO + N - 1))
while true; do
  left=0
  for s in $(seq $LO $HI); do
    f=$(printf "%s/shards/shard-%05d.h5" "$B" $s); o=$(printf "%s/outputs/shard-%05d.outputs.h5" "$B" $s); u=$(printf "%s/shards/shard-%05d.uploaded" "$B" $s)
    if [ -f "$u" ] || [ -f "$f" ]; then continue; fi
    if [ -f "$o" ] && python - "$o" <<'PY' 2>/dev/null
import sys, h5py
with h5py.File(sys.argv[1], "r") as h: ok = all("complete" in h["samples"][k].attrs for k in h["samples"])
sys.exit(0 if ok else 1)
PY
    then python scripts/generate.py finalize --build "$B" --shard $s --quicklooks 2>&1 | grep -v Warning | tail -1
    else left=$((left + 1)); fi
  done
  [ $left -eq 0 ] && { echo "range $LO-$HI finalized $(date -u +%FT%TZ)"; exit 0; }
  sleep 300
done
