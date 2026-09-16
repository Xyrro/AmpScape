#!/bin/bash
# Streaming sync supervisor for one tier build. Runs detached from any session (setsid + nohup), is idempotent
# (a pid lock refuses a second copy; every step skips work already done), survives being restarted after a
# login-node reboot, and logs to $AMPSCAPE_SCRATCH/logs/sync.log. HF pushes only ever run here (login node).
#
# start / restart (one line):
#   setsid nohup /storage/ice1/1/8/yxiao413/EcoFlowBench/scripts/slurm/v1/sync_loop.sh data/v1/S S >/dev/null 2>&1 < /dev/null &
# stop:   kill $(cat $AMPSCAPE_SCRATCH/logs/sync_S.pid)
BUILD=$1; TIER=$2; INT=${3:-900}
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
LOG="$AMPSCAPE_SCRATCH/logs/sync.log"; PIDF="$AMPSCAPE_SCRATCH/logs/sync_${TIER}.pid"
mkdir -p "$AMPSCAPE_SCRATCH/logs"
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "$(date -u +%FT%TZ) sync_loop $TIER already running (pid $(cat "$PIDF")); exiting" >> "$LOG"; exit 0
fi
echo $$ > "$PIDF"
trap 'rm -f "$PIDF"' EXIT
echo "$(date -u +%FT%TZ) sync_loop $TIER started pid $$ build=$BUILD interval=${INT}s" >> "$LOG"
while true; do
  {
    echo "== $(date -u +%FT%TZ) $TIER finalize"
    python scripts/generate.py finalize --build "$BUILD" --quicklooks 2>&1 | grep -v Warning | grep -v "^shard .*inputs already\|^ *[0-9]* *[0-9]* *True" | tail -4
    echo "== $(date -u +%FT%TZ) $TIER sync"
    python scripts/sync_shards.py --build "$BUILD" --tier "$TIER" --live --publish-index 2>&1 | grep -v Warning | grep -v '"already"' | tail -8
    rc=${PIPESTATUS[0]}
    if [ "$rc" -eq 2 ]; then echo "$(date -u +%FT%TZ) STOP RULE: a shard failed to upload twice — loop pausing (exit 2); report to the owner"; exit 2; fi
    echo "== $(date -u +%FT%TZ) $TIER uploaded=$(ls "$BUILD"/shards/*.uploaded 2>/dev/null | wc -l) final_local=$(ls "$BUILD"/shards/*.h5 2>/dev/null | wc -l) failed=$(ls "$BUILD"/shards/*.upload_failed 2>/dev/null | wc -l)"
  } >> "$LOG" 2>&1
  sleep "$INT"
done
