#!/bin/bash
#SBATCH -J verify-before-delete
# account, QoS, partition: submit with ampscape_sbatch (scripts/env.sh, site values in scripts/env.local.sh)
#SBATCH -N1 -n1 -c 4 --mem=8G -t 03:00:00
#SBATCH -o work/delete_check/slurm_%j.out
# Owner 2026-10-26: hash every scratch copy slated for deletion against the Hub (staged groups at the pinned v1.0.2,
# the verification mirror at main).
set -u
cd "${AMPSCAPE_SCRATCH:-${SLURM_SUBMIT_DIR:-.}}"
source scripts/env.sh
V=scripts/maintenance/verify_against_hub.py; O=work/delete_check; rc=0
for g in XL/T4 XXL/T1 XXL/T4; do
  python $V --local data/hfcache/data/$g --prefix data/$g --revision v1.0.2 --out $O/${g/\//_}.json || rc=1
done
python $V --local work/verify/hub_mirror/aux --prefix aux --revision main --out $O/hub_mirror.json || rc=1
echo "rc=$rc end=$(date -u +%FT%TZ)"
