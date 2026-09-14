#!/bin/bash
# Streaming sync loop for one tier build (login node only: HF pushes never run in Slurm jobs).
# usage: nohup scripts/slurm/v1/sync_loop.sh <build> <tier> [interval_s] > <build>/logs/sync_loop.out 2>&1 &
BUILD=$1; TIER=$2; INT=${3:-900}
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
while true; do
  echo "== $(date -u +%FT%TZ) finalize"
  python scripts/generate.py finalize --build "$BUILD" --quicklooks 2>&1 | grep -v Warning | tail -3
  echo "== $(date -u +%FT%TZ) sync"
  python scripts/sync_shards.py --build "$BUILD" --tier "$TIER" --live --publish-index 2>&1 | grep -v Warning | tail -5
  rc=$?
  if [ $rc -eq 2 ]; then echo "STOP RULE: a shard failed to upload twice — pausing (loop exits)"; exit 2; fi
  sleep "$INT"
done
