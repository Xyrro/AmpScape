#!/bin/bash
# Detached uploader for the precision pass (login node): every 5 min uploads the shards whose `run` finished
# (idempotent; one commit per shard, sha256-verified; local copies removed). Stops on a mismatch (exit ≠ 0).
#   setsid nohup scripts/slurm/v1/precision_upload_loop.sh S >/dev/null 2>&1 < /dev/null &
T=$1; cd /storage/ice1/1/8/yxiao413/EcoFlowBench; source scripts/env.sh
LOG=$AMPSCAPE_SCRATCH/logs/precision_upload_$T.log; PIDF=$AMPSCAPE_SCRATCH/logs/precision_upload_$T.pid
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "already running" >> "$LOG"; exit 0; fi
echo $$ > "$PIDF"; trap 'rm -f "$PIDF"' EXIT
while true; do
  echo "== $(date -u +%FT%TZ) $T" >> "$LOG"
  python scripts/precision_pass.py upload --tier $T --work work/precision/$T >> "$LOG" 2>&1 || { echo "UPLOAD STOPPED (error) $(date -u +%FT%TZ)" >> "$LOG"; exit 2; }
  sleep 300
done
