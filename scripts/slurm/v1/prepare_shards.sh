#!/bin/bash
# usage: sbatch ... prepare_shards.sh <build> <a> <b>   (prepare shards a..b inclusive, sequentially)
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
B=$1; A=$2; Z=$3
for s in $(seq $A $Z); do python scripts/generate.py prepare --build "$B" --shard $s 2>&1 | grep -v Warning | tail -1; done
echo "prepared $A-$Z $(date -u +%FT%TZ)"
