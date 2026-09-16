#!/bin/bash
# merge the per-tier tile manifests and build the five resistance rasters per accepted tile (v1.0 tile set)
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
python scripts/build_v1_tiles.py merge --out data/tiles/v1.0 2>&1 | grep -v Warning | tail -2
python scripts/build_v1_tiles.py resist --out data/tiles/v1.0 2>&1 | grep -v Warning | tail -2
python scripts/build_v1_tiles.py parents --out data/tiles/v1.0 2>&1 | tail -1
