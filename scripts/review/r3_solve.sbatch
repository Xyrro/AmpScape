#!/bin/bash
#SBATCH -A coc -q coc-ice -p coc-cpu
#SBATCH -N1 -n1 -c 1
# Review round 3: Omniscape solve of one aux shard per array task (no finalize; outputs read directly).
#   sbatch -J r3-solve-<name> --array=0-N --mem=.. -t .. -o <build>/logs/%A_%a.out --export=ALL,BUILD=<build> scripts/review/r3_solve.sbatch
set -euo pipefail
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export JULIA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export JULIA_DEPOT_PATH=$PWD/julia_depot
export TMPDIR=${TMPDIR:-/tmp}/ampscape_r3_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID:-0}; mkdir -p "$TMPDIR"; trap 'rm -rf "$TMPDIR"' EXIT
echo "host=$(hostname) build=$BUILD shard=$SLURM_ARRAY_TASK_ID start=$(date -u +%FT%TZ)"
python scripts/generate.py solve --build "$BUILD" --shard "$SLURM_ARRAY_TASK_ID" --configs omniscape 2>&1 | tr '\r' '\n' | grep --line-buffered -v '^Progress' || true
echo "end=$(date -u +%FT%TZ)"
