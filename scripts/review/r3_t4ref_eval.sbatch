#!/bin/bash
#SBATCH -J r3-t4ref
#SBATCH -A coc -q coc-ice -p coc-cpu
#SBATCH -N1 -n1 -c 4 --mem=48G -t 02:00:00
#SBATCH -o aux/review_round3/logs/t4ref_%A_%a.out
# Review round 3 (owner-approved republish of the 120-map L reference): re-run the official T4 reference evaluation of
# one L run (array index = line of work/r3_L_runs.txt) — the run's stored test_id predictions are fetched from the Hub
# to node-local disk; same evaluate.py command as the training legs, minimal root (scripts/review/r3_eval_root.py).
set -euo pipefail
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
RUN=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" work/r3_L_runs.txt)
L="${TMPDIR:-/tmp}/ampscape_r3t4ref_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"; mkdir -p "$L"; trap 'rm -rf "$L"' EXIT
REL=aux/results/runs_full/$RUN/predictions/hfcache_L_test_id/predictions.h5
HF_XET_CACHE="$L/xet" python -c "from huggingface_hub import hf_hub_download as d; d('Xirro/AmpScape', '$REL', repo_type='dataset', local_dir='$L')"
PRED="$L/$(dirname $REL)"
cp runs/full/$RUN/predictions/hfcache_L_test_id/meta.json "$PRED/" 2>/dev/null || true
echo "run=$RUN host=$(hostname) start=$(date -u +%FT%TZ)"
python scripts/evaluate.py --predictions "$PRED" --root work/r3_rootL --tier L --split test_id \
  --t4-reference aux/t4_bs1_reference/L_bs1 \
  --t4-blocks aux/t4_blocksize_baselines/L_b3_ca1 aux/t4_blocksize_baselines/L_b5_ca0 aux/t4_blocksize_baselines/L_b11_ca1 \
  --out runs/full/$RUN/eval_t4_reference --workers 4 2>&1 | grep -v Warning | tail -4
echo "end=$(date -u +%FT%TZ)"
