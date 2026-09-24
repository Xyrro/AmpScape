#!/usr/bin/env bash
#SBATCH --job-name=ampscape-solve
#SBATCH --nodes=1
#SBATCH --ntasks=1
# time / cpus / mem / partition / array / output are passed by scripts/generate.py submit
# One shard per array task. No network is needed: inputs were materialised by `generate.py prepare`
# on the login node and the Julia depot is precompiled on scratch.
set -euo pipefail
# AMPSCAPE_SCRATCH / AMPSCAPE_NODE_TMP / AMPSCAPE_MODULES are exported by scripts/generate.py submit from the cluster profile.
: "${AMPSCAPE_SCRATCH:?AMPSCAPE_SCRATCH must be set (cluster profile scratch_root)}"
source "$AMPSCAPE_SCRATCH/scripts/env.sh"
export JULIA_NUM_THREADS=1                       # one solve at a time; CHOLMOD/BLAS use the allocated cores
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export JULIA_DEPOT_PATH="$AMPSCAPE_SCRATCH/julia_depot"
export TMPDIR="${AMPSCAPE_NODE_TMP:-${TMPDIR:-/tmp}}/ampscape_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID:-0}"
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"' EXIT
SHARD="${SLURM_ARRAY_TASK_ID:-0}"
echo "host=$(hostname) build=$AMPSCAPE_BUILD shard=$SHARD cpus=${SLURM_CPUS_PER_TASK:-1} start=$(date -u +%FT%TZ)"
cd "$AMPSCAPE_SCRATCH"
EXTRA=()
# config list is '+'-separated in --export (sbatch splits --export on commas)
[ -n "${AMPSCAPE_CONFIGS:-}" ] && EXTRA+=(--configs "${AMPSCAPE_CONFIGS//+/,}")
[ "${AMPSCAPE_FORCE:-0}" = "1" ] && EXTRA+=(--force)
# 2026-09-21: Omniscape's progress bars (\r-updated) made each L task log 3-4 MB (12 GB of logs over S-L); keep only real lines
python scripts/generate.py solve --build "$AMPSCAPE_BUILD" --shard "$SHARD" \
    --solver "${AMPSCAPE_SOLVER:-cholmod}" --fallback "${AMPSCAPE_FALLBACK:-cg+amg}" --omniscape-solver "${AMPSCAPE_OSOLVER:-cholmod}" "${EXTRA[@]}" 2>&1 \
    | tr '\r' '\n' | grep --line-buffered -v '^Progress' || true
# v1.0: finalize + validate + quicklooks on the compute node right after the solve (idempotent; skips if final exists)
python scripts/generate.py finalize --build "$AMPSCAPE_BUILD" --shard "$SHARD" --quicklooks 2>&1 | grep -v Warning | tail -2
echo "end=$(date -u +%FT%TZ)"
