#!/bin/bash
# prepare inputs for a dev build (login-node-free: no network needed once tiles/resistance rasters exist)
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
python scripts/generate.py prepare --build "$1"
