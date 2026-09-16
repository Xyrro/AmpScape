#!/bin/bash
# usage: sbatch --array=0-9 prepare_range.sh <build> <shards_per_task>
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
B=$1; N=$2; LO=$((SLURM_ARRAY_TASK_ID * N)); HI=$((LO + N - 1))
for s in $(seq $LO $HI); do python scripts/generate.py prepare --build "$B" --shard $s 2>&1 | grep -v Warning | tail -1; done
