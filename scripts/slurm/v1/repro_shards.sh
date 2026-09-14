#!/bin/bash
# prepare + solve + finalize the reproducibility shards of one tier, then compare with the dev shards
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
T=$1
export JULIA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python scripts/generate.py prepare --build data/repro/$T 2>&1 | grep -v Warning | tail -2
for s in $(python -c "import pandas as pd; print(' '.join(str(x) for x in sorted(pd.read_parquet('data/repro/$T/manifest.parquet').shard.unique())))"); do
  python scripts/generate.py solve --build data/repro/$T --shard $s 2>&1 | grep -v "Warning\|Progress" | tail -2
done
python scripts/generate.py finalize --build data/repro/$T 2>&1 | grep -v Warning | tail -2
python scripts/compare_shards.py --a data/dev/$T/shards --b data/repro/$T/shards --out data/repro/${T}_compare.json
