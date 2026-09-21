#!/bin/bash
# XL cost probe (owner 2026-09-21): shards 0-1 at 1 cpu and 2-3 at 4 cpus, same 16 GB, 10 h walltime.
# Run after data/v1/XL/manifest.parquet exists. Step 1 prepares the 4 shards (Slurm), step 2 submits the solves.
cd /storage/ice1/1/8/yxiao413/EcoFlowBench; source scripts/env.sh
B=data/v1/XL
if [ "$1" = prepare ]; then
  sbatch --parsable -A coc -q coc-ice -p coc-cpu -N1 -n1 -c1 --mem=16G -t 02:00:00 -J prep-XL-probe -o data/v1/logs/prep_XL_probe_%A_%a.out \
    --array=0-3 --wrap 'source scripts/env.sh; python scripts/generate.py prepare --build data/v1/XL --shard $SLURM_ARRAY_TASK_ID'
elif [ "$1" = submit ]; then
  python scripts/generate.py submit --build $B --shards 0-1 --cpus 1 --mem 16G --max-concurrent 2 --skip-precompile | tail -1
  python scripts/generate.py submit --build $B --shards 2-3 --cpus 4 --mem 16G --max-concurrent 2 --skip-precompile | tail -1
fi
