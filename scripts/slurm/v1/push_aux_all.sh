#!/bin/bash
# Push every scratch-only evaluation asset to the Hub under aux/ (owner 2026-09-21). Login node only; idempotent.
cd /storage/ice1/1/8/yxiao413/EcoFlowBench; source scripts/env.sh
LOG=$AMPSCAPE_SCRATCH/logs/push_aux.log
P="python scripts/push_aux.py"
BUILD_INC="shards/*.h5 index/*.parquet index.parquet manifest*.parquet build.json splits/* stats/*"
AUX_INC="outputs/*.h5 inputs/*.h5 manifest.parquet selection.parquet build.json summary.json summary.md index.parquet vs_bs1.parquet vs_bs1.md"
{
echo "== start $(date -u +%FT%TZ)"
$P --src data/dev/S --dest aux/dev/S --include $BUILD_INC
$P --src data/dev/M --dest aux/dev/M --include $BUILD_INC
$P --src data/builds/mini --dest aux/mini --include $BUILD_INC
$P --src aux/scale_probe/probe_L --dest aux/scale_probe/probe_L --include $BUILD_INC
$P --src aux/scale_probe --dest aux/scale_probe --include '*.parquet' tiles resistance
$P --src aux/t4_bs1_reference/M_bs1 --dest aux/t4_bs1_reference/M --include $AUX_INC
$P --src aux/t4_bs1_reference/L_bs1 --dest aux/t4_bs1_reference/L --include $AUX_INC
for b in M_b3_ca0 M_b7_ca1 M_b7_ca0; do $P --src aux/t4_blocksize_baselines/$b --dest aux/t4_blocksize_baselines/M/$b --include $AUX_INC; done
for b in L_b3_ca1 L_b11_ca1 L_b5_ca0; do $P --src aux/t4_blocksize_baselines/$b --dest aux/t4_blocksize_baselines/L/$b --include $AUX_INC; done
$P --src data/predictions --dest aux/results/predictions --include coarsen4 coarsen4_published dev_coarsen4 oracle zeros
$P --src runs/dev --dest aux/results/runs_dev --include '*'
$P --src runs/tune --dest aux/results/runs_tune --include '*'
[ -d data/builds/published/shards ] && [ "$(ls data/builds/published/outputs/*.done 2>/dev/null | wc -l)" = 4 ] && $P --src data/builds/published --dest aux/test_ood_published --include $BUILD_INC
echo "== end $(date -u +%FT%TZ)"
} >> $LOG 2>&1
