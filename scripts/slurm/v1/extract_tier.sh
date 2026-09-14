#!/bin/bash
# usage: sbatch ... extract_tier.sh <tier|XXL_strict> <first_accepted> [workers]
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
T=$1; N=$2; W=${3:-4}
echo "host=$(hostname) tier=$T n=$N start=$(date -u +%FT%TZ)"
python scripts/extract_tiles.py --specs data/tiles/v1.0/specs/$T --out data/tiles/v1.0 --workers $W --first-accepted $N --per-specs-manifest 2>&1 | grep -v Warning | grep "prefix mode\|rejected\|Error\|Traceback" | tail -40
echo "end=$(date -u +%FT%TZ)"
