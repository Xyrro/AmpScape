#!/bin/bash
#SBATCH -J r3-build-blocks
# account, QoS, partition: submit with ampscape_sbatch (scripts/env.sh, site values in scripts/env.local.sh)
#SBATCH -N1 -n1 -c 2 --mem=16G -t 01:00:00
#SBATCH -o aux/review_round3/logs/build_blocks_%j.out
# Review round 3 (owner-approved L reference republish): block-size rows for the 60 new L reference landscapes.
set -eu
cd "${AMPSCAPE_SCRATCH:-${SLURM_SUBMIT_DIR:-.}}"
source scripts/env.sh
export HF_HUB_DISABLE_XET=1
S=aux/t4_bs1_reference/L_bs1_topup/selection.parquet
for spec in "3 1" "5 0" "11 1"; do set -- $spec
  python scripts/review/r3_build_from_hub.py build --tier L --out aux/t4_blocksize_baselines/L_b$1_ca$2_topup --sel $S --block $1 --correct-artifacts $2 --shard-size 5
done
