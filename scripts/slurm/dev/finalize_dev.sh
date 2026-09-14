#!/bin/bash
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
source scripts/env.sh
python scripts/generate.py finalize --build "$1" --quicklooks
python scripts/generate.py status --build "$1"
