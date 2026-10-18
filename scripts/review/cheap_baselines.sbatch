#!/bin/bash
#SBATCH -J r2-cheap-baselines
#SBATCH -A coc -q coc-ice -p coc-cpu
#SBATCH -N1 -n1 -c 8 --mem=48G -t 06:00:00
#SBATCH -o aux/review_round2/cheap_baselines/slurm_%j.out
# Review round 2, point 4: truncated AMG-PCG (T3, T1 first pair) and coarsen-x4 (T1, T3) on a test_id subset per tier.
set -u
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
export HF_HUB_DISABLE_XET=1 JULIA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export TMPDIR=${TMPDIR:-/tmp}/ampscape_r2_$SLURM_JOB_ID; mkdir -p "$TMPDIR"; trap 'rm -rf "$TMPDIR"' EXIT
OUT=aux/review_round2/cheap_baselines
echo "host=$(hostname) start=$(date -u +%FT%TZ)"; lscpu | grep "Model name" | head -1
python scripts/review/fetch_subset.py --root $OUT --n S=40,M=30,L=16 || exit 1
julia --project=julia/AmpScapeSolve.jl scripts/review/pcg_truncated.jl $OUT/manifest.json $OUT/pcg.json || echo "PCG FAILED"
for T in S M L; do
  python scripts/baseline_coarsen.py --root $OUT/build_$T --splits test_id --factor 4 --out $OUT/coarsen4_$T || { echo "coarsen $T FAILED"; continue; }
  python scripts/review/score_coarsen.py --pred $OUT/coarsen4_$T/predictions.h5 --manifest $OUT/manifest.json --out $OUT/coarsen4_$T.json
done
echo "end=$(date -u +%FT%TZ)"
