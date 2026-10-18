#!/bin/bash
#SBATCH -J r2-omni-threads
#SBATCH -A coc -q coc-ice -p coc-cpu
#SBATCH -N1 -n1 -c 24 --mem=96G -t 06:00:00
#SBATCH --array=1,8,24
#SBATCH -o aux/review_round2/omniscape_threads/slurm_%A_%a.out
# Review round 2, point 1: Omniscape wall time vs Julia threads (array index = thread count); 4 M + 2 L landscapes.
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export JULIA_NUM_THREADS=$SLURM_ARRAY_TASK_ID OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export TMPDIR=${TMPDIR:-/tmp}/ampscape_r2_$SLURM_JOB_ID; mkdir -p "$TMPDIR"; trap 'rm -rf "$TMPDIR"' EXIT
echo "host=$(hostname) threads=$JULIA_NUM_THREADS cpus=$SLURM_CPUS_PER_TASK start=$(date -u +%FT%TZ)"
lscpu | grep "Model name" | head -1
julia --project=julia/AmpScapeSolve.jl scripts/review/omniscape_threads.jl aux/review_round2/omniscape_threads/threads_${SLURM_ARRAY_TASK_ID}.json 4 2
echo "end=$(date -u +%FT%TZ)"
