#!/bin/bash
cd "${AMPSCAPE_SCRATCH:-${SLURM_SUBMIT_DIR:-.}}"
source scripts/env.sh
python scripts/generate.py finalize --build "$1" --quicklooks
python scripts/generate.py status --build "$1"
