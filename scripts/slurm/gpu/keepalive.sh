#!/bin/bash
# Keep the Phase 10 GPU driver and the run offloader alive on the login node, detached from any session.
#   setsid nohup bash scripts/slurm/gpu/keepalive.sh > /dev/null 2>&1 < /dev/null &      (idempotent; see runbook)
# Every 5 min: start the driver if its lease pid is dead, start the offloader if no copy runs. Survives a dead
# session; after a login-node reboot run the same line again (PACE login nodes allow no user cron/systemd).
# Memory hygiene (2026-10-13): the login node's 4 GB per-user cgroup does not reclaim our clean page cache and
# OOM-kills instead (SIGKILL on staging subprocesses, tmux attaches, the SSH session) — every 10 min, and whenever
# memory.current > 2.5 GiB, run scripts/evict_cache.py (posix_fadvise DONTNEED over the scratch roots).
# Process selection: lease pid (driver) or an exact `python <script>` match (offloader) — never pkill/killall/-f
# patterns, which can match tmux, screen, sshd, bash or the Claude CLI (tests/test_no_pattern_kills.py).
cd "$(dirname "$0")/../../.." || exit 1
source scripts/env.sh
PIDFILE=logs/keepalive.pid
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null && [ "$(cat "$PIDFILE")" != "$$" ]; then
  echo "keepalive already running ($(cat "$PIDFILE"))"; exit 0
fi
echo $$ > "$PIDFILE"
log() { echo "$(date -u +%FT%TZ) $*" >> logs/keepalive.log; }
CG="/sys/fs/cgroup/user.slice/user-$(id -u).slice"
MEM_TRIGGER_BYTES=$((2684354560))   # 2.5 GiB
mem_current() { cat "$CG/memory.current" 2>/dev/null || echo 0; }
evict() { python scripts/evict_cache.py --quiet "$@" >> logs/keepalive.log 2>&1; }
log "keepalive started pid $$ (memory.current $(mem_current) B, max $(cat "$CG/memory.max" 2>/dev/null))"
evict
tick=0
while true; do
  tick=$((tick + 1))
  # memory hygiene first: a staging/upload burst must not reach the cgroup limit before the sweep runs
  if [ "$(mem_current)" -gt "$MEM_TRIGGER_BYTES" ]; then
    log "memory.current $(mem_current) B > 2.5 GiB: evicting page cache"; evict
  elif [ $((tick % 2)) -eq 0 ]; then
    evict
  fi
  if [ -f logs/GPU_ALERT.txt ]; then sleep 300; continue; fi
  dpid=$(python -c "import json;print(json.load(open('logs/lease_gpu_driver.json'))['pid'])" 2>/dev/null)
  if [ -z "$dpid" ] || ! kill -0 "$dpid" 2>/dev/null || ! ps -o args= -p "$dpid" 2>/dev/null | grep -q gpu_driver; then
    rm -f logs/lease_gpu_driver.json
    PLAN=""; [ -s logs/driver_plan.txt ] && PLAN="--plan-file $(cat logs/driver_plan.txt)"  # phase 13+: plan file
    setsid nohup python scripts/slurm/gpu/gpu_driver.py $PLAN >> logs/gpu_driver.err 2>&1 < /dev/null &
    log "driver (re)started pid $!"
  fi
  if [ ! -f logs/offloader_disabled ] && ! ps -eo args | awk '$1=="python" && $2 ~ /offload_runs\.py$/' | grep -q .; then
    setsid nohup python scripts/slurm/gpu/offload_runs.py --loop 600 >> logs/offload_runs.log 2>&1 < /dev/null &
    log "offloader (re)started pid $!"
  fi
  sleep 300
done
