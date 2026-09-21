#!/bin/bash
# Streaming sync supervisor for one tier build. Runs detached from any session (setsid + nohup), is idempotent
# (a pid lock refuses a second copy; every step skips work already done), survives being restarted after a
# login-node reboot, and logs to $AMPSCAPE_SCRATCH/logs/sync.log. HF pushes only ever run here (login node).
#
# start / restart (one line):
#   setsid nohup /storage/ice1/1/8/yxiao413/EcoFlowBench/scripts/slurm/v1/sync_loop.sh data/v1/S S >/dev/null 2>&1 < /dev/null &
# parallel (N workers, 2026-09-21): start N copies with 4th arg k/N, e.g. for k in 0 1 2 3; do setsid nohup .../sync_loop.sh data/v1/XL XL 120 $k/4 >/dev/null 2>&1 < /dev/null & done
# stop:   kill $(cat $AMPSCAPE_SCRATCH/logs/sync_S.pid)   (worker k: sync_<tier>_w<k>.pid)
BUILD=$1; TIER=$2; INT=${3:-900}; WORKER=${4:-0/1}   # 4th arg k/N: one of N parallel uploaders (2026-09-21)
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
LOG="$AMPSCAPE_SCRATCH/logs/sync.log"
if [ "$WORKER" = "0/1" ]; then TAG="$TIER"; else TAG="${TIER}_w${WORKER%%/*}"; fi
PIDF="$AMPSCAPE_SCRATCH/logs/sync_${TAG}.pid"
mkdir -p "$AMPSCAPE_SCRATCH/logs"
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "$(date -u +%FT%TZ) sync_loop $TAG already running (pid $(cat "$PIDF")); exiting" >> "$LOG"; exit 0
fi
echo $$ > "$PIDF"
trap 'rm -f "$PIDF"' EXIT
echo "$(date -u +%FT%TZ) sync_loop $TAG started pid $$ build=$BUILD interval=${INT}s worker=$WORKER" >> "$LOG"
while true; do
  {
    # finalize runs inside the Slurm array tasks (solve_shard.sbatch) or a finalize array — never here: 500 shards of
    # QC would be hours of CPU on the shared login node. This loop only validates, uploads, verifies and deletes.
    echo "== $(date -u +%FT%TZ) $TAG sync"
    AMPSCAPE_LEASE_OWNER=$$ python scripts/sync_shards.py --build "$BUILD" --tier "$TIER" --live --publish-index --worker "$WORKER" 2>&1 | grep -v Warning | grep -v '"already"' | tail -8
    rc=${PIPESTATUS[0]}
    if [ "$rc" -eq 2 ]; then echo "$(date -u +%FT%TZ) STOP RULE: a shard failed to upload twice — loop pausing (exit 2); report to the owner"; exit 2; fi
    echo "== $(date -u +%FT%TZ) $TAG uploaded=$(ls "$BUILD"/shards/*.uploaded 2>/dev/null | wc -l) final_local=$(ls "$BUILD"/shards/*.h5 2>/dev/null | wc -l) failed=$(ls "$BUILD"/shards/*.upload_failed 2>/dev/null | wc -l)"
  } >> "$LOG" 2>&1
  sleep "$INT"
done
