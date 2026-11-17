#!/bin/bash
#SBATCH -J r3-reference
# account, QoS, partition: submit with ampscape_sbatch (scripts/env.sh, site values in scripts/env.local.sh)
#SBATCH -N1 -n1 -c 16 --mem=96G -t 03:00:00
#SBATCH -o aux/review_round3/logs/reference_%j.out
# Review round 3, point 3a: official T4 L models (fp32, CPU), production targets and the radius-law baseline against the
# exact block-1 maps of the enlarged L reference (original 60 + top-up 60).
set -eu
cd "${AMPSCAPE_SCRATCH:-${SLURM_SUBMIT_DIR:-.}}"
source scripts/env.sh
export HF_HUB_DISABLE_XET=1 OMP_NUM_THREADS=16
python scripts/review/r3_t4_eval.py reference --tier L
