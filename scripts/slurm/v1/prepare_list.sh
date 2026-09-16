#!/bin/bash
# usage: sbatch --array=0-(K-1) prepare_list.sh <build> <listfile> <per_task>
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
B=$1; L=$2; N=$3; arr=($(cat "$L")); LO=$((SLURM_ARRAY_TASK_ID * N)); HI=$((LO + N - 1))
for i in $(seq $LO $HI); do [ $i -lt ${#arr[@]} ] || break; python scripts/generate.py prepare --build "$B" --shard ${arr[$i]} 2>&1 | grep -v Warning | tail -1; done
