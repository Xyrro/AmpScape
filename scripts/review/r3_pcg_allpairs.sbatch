#!/bin/bash
#SBATCH -J r3-pcg-allpairs
#SBATCH -A coc -q coc-ice -p coc-cpu
#SBATCH -N1 -n1 -c 1 --mem=24G -t 08:00:00
#SBATCH -o aux/review_round3/logs/pcg_allpairs_%j.out
# Review round 3, point 2a: truncated AMG-PCG summed over every T1 pair, on the round-2 test_id subset (S 40, M 30, L 16).
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export JULIA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
mkdir -p aux/review_round3/pcg_allpairs
echo "host=$(hostname) start=$(date -u +%FT%TZ)"; lscpu | grep "Model name" | head -1
julia --project=julia/AmpScapeSolve.jl scripts/review/pcg_truncated_allpairs.jl aux/review_round2/cheap_baselines/manifest.json aux/review_round3/pcg_allpairs/pcg_allpairs.json
echo "end=$(date -u +%FT%TZ)"
