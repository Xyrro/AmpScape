#!/bin/bash
# prepare inputs for a dev build (login-node-free: no network needed once tiles/resistance rasters exist)
cd $AMPSCAPE_SCRATCH
source scripts/env.sh
python scripts/generate.py prepare --build "$1"
