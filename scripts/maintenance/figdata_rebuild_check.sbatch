#!/bin/bash
#SBATCH -J figdata-rebuild-check
# account, QoS, partition: submit with ampscape_sbatch (scripts/env.sh, site values in scripts/env.local.sh)
#SBATCH -N1 -n1 -c 4 --mem=16G -t 01:00:00
#SBATCH -o work/delete_check/figdata_%j.out
# Owner 2026-10-26: rebuild paper/figdata from the Hub into a separate directory and compare it with the current copy.
set -u
cd "${AMPSCAPE_SCRATCH:-${SLURM_SUBMIT_DIR:-.}}"
source scripts/env.sh
export TMPDIR=${TMPDIR:-/tmp}/ampscape_fd_$SLURM_JOB_ID; mkdir -p "$TMPDIR"; trap 'rm -rf "$TMPDIR"' EXIT
OUT=work/delete_check/figdata_rebuild; rm -rf $OUT
python scripts/paper_figdata.py --out $OUT --tmp $TMPDIR/fd || { echo "rebuild FAILED"; exit 1; }
python scripts/maintenance/compare_figdata.py paper/figdata $OUT; echo "compare_rc=$?"
