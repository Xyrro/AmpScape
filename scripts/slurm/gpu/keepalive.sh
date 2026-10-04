#!/bin/bash
# Keep the Phase 10 GPU driver and the run offloader alive on the login node, detached from any session.
#   setsid nohup bash scripts/slurm/gpu/keepalive.sh > /dev/null 2>&1 < /dev/null &      (idempotent; see runbook)
# Every 5 min: start the driver if its lease pid is dead, start the offloader if no copy runs. Survives a dead
# session; after a login-node reboot run the same line again (or let the cron entry from the runbook do it).
cd "$(dirname "$0")/../../.." || exit 1
source scripts/env.sh
PIDFILE=logs/keepalive.pid
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null && [ "$(cat "$PIDFILE")" != "$$" ]; then
  echo "keepalive already running ($(cat "$PIDFILE"))"; exit 0
fi
echo $$ > "$PIDFILE"
log() { echo "$(date -u +%FT%TZ) $*" >> logs/keepalive.log; }
log "keepalive started pid $$"
while true; do
  if [ -f logs/GPU_ALERT.txt ]; then sleep 300; continue; fi
  dpid=$(python -c "import json;print(json.load(open('logs/lease_gpu_driver.json'))['pid'])" 2>/dev/null)
  if [ -z "$dpid" ] || ! kill -0 "$dpid" 2>/dev/null || ! ps -o args= -p "$dpid" 2>/dev/null | grep -q gpu_driver; then
    rm -f logs/lease_gpu_driver.json
    PLAN=""; [ -s logs/driver_plan.txt ] && PLAN="--plan-file $(cat logs/driver_plan.txt)"  # phase 13+: plan file
    setsid nohup python scripts/slurm/gpu/gpu_driver.py $PLAN >> logs/gpu_driver.err 2>&1 < /dev/null &
    log "driver (re)started pid $!"
  fi
  if ! ps -eo args | awk '$1=="python" && $2 ~ /offload_runs\.py$/' | grep -q .; then
    setsid nohup python scripts/slurm/gpu/offload_runs.py --loop 600 >> logs/offload_runs.log 2>&1 < /dev/null &
    log "offloader (re)started pid $!"
  fi
  sleep 300
done
