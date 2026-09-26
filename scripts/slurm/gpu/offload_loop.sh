#!/bin/bash
# Start the run offloader loop once (login node). Detects a running copy by process args, not by shell text.
cd "$(dirname "$0")/../../.." || exit 1
source scripts/env.sh
if ps -eo args | awk '$1=="python" && $2 ~ /offload_runs\.py$/' | grep -q .; then echo "offload loop already running"; exit 0; fi
setsid nohup python scripts/slurm/gpu/offload_runs.py --loop "${1:-600}" >> logs/offload_runs.log 2>&1 < /dev/null &
echo "offload loop started pid $!"
