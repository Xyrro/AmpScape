# Scratch cleanup, 2026-11-14

Owner approval (2026-11-14): "OK delete the ones can be fully reproduce and safe". Scratch went from 286.0 GB to
204.6 GB of the 300 GB quota (other projects kept writing during the run). Earlier cleanup:
`docs/scratch_cleanup_2026-10-26.md`.

## Rule

Only files whose exact bytes are on the Hub were deleted, plus two download caches. Small files (json, parquet, md, csv,
logs) were kept, so every table and figure script still runs without a download.

## How it was checked

1. Read-only verification (Slurm jobs 7057660, 7057971, `scripts/maintenance/verify_against_hub.py`): every candidate
   hashed against the Hub at `main` = `aa2bc2f546bffe56f1584326ed3840e5a3fb0649`; renamed or merged builds (the L
   reference and block-size top-ups merged on 2026-10-22) matched by content (`--by-content`).
2. Restore manifest (`scripts/maintenance/build_delete_manifest.py`):
   `docs/maintenance/restore_manifest_2026-11-14.jsonl`, one line per deleted file with its local path, the Hub path
   holding identical bytes, the pinned commit, the size and the hash.
3. Deletion job 7059374 (`scripts/maintenance/delete_verified.py`): a dry run on one group, then one file per group
   downloaded from the Hub at the pinned commit and hash-checked (all 11 passed) before anything was deleted; each
   local file re-hashed and deleted only if still identical. Result: 3,836 deleted (81.22 GB), 0 changed, 0 absent.
4. Restore test after deletion: `runs/dev/gnn_T1/best.pt` restored to its original path with
   `restore_from_hub.py`, sha256 identical to the manifest (left in place).

## Deleted

| Group | Local files | GB | Hub location |
|---|---|---|---|
| `t1_pair1` | `aux/t1_pair1/**/*.h5` | 32.15 | `aux/t1_pair1/` (same paths) |
| `best_pt` | `runs/full/*/best.pt` (203) | 30.19 | `aux/results/runs_full/<run>/best.pt` |
| `blocksize` | `aux/t4_blocksize_baselines/**/*.h5` (336) | 7.06 | `aux/t4_blocksize_baselines/{M,L}/…` (merged builds; manifest maps names) |
| `scale_probe_h5`, `scale_probe_tif` | `aux/scale_probe/**/*.{h5,tif}` (525) | 3.86 | `aux/scale_probe/` |
| `bs1_reference` | `aux/t4_bs1_reference/**/*.h5` (528) | 2.41 | `aux/t4_bs1_reference/{M,L}/…` (merged; manifest maps names) |
| `runs_tune`, `runs_dev` | checkpoints and predictions (142) | 2.59 | `aux/results/runs_tune/`, `aux/results/runs_dev/` |
| `runs_full_h5` | transfer predictions (4) | 1.40 | `aux/results/runs_full/` |
| `predictions` | `data/predictions/**/*.h5` (83) | 1.19 | `aux/results/predictions/` |
| `wp7_h5` | `aux/wp7/shards/*.h5` (15) | 0.38 | `aux/wp7/shards/` |
| caches | `data/hfcache_r3` (round-3 download cache; both cached commits on the Hub), `data/hfcache/.cache` (90 abandoned partial downloads) | 6.4 | — |

## Kept (not fully reproducible)

- `runs/full/gnn_T4_L_s1/predictions/hfcache_XXL_test_id/predictions.h5` (1.3 GB): modified on scratch 16 min after
  its 2026-10-04 upload and 94 KB larger than the Hub copy; the Hub holds the earlier version.
- 120 `aux/wp7` tiles not on the Hub; `work/probe` (GPU probe checkpoints); `data/sources` (provider re-download);
  `data/v1` audits, `data/repro`; environments; `aux/review_round2/3` (until submission).

## What needs a restore first

Paper tables and figures need nothing. These need the listed group back first:

| Work | Groups |
|---|---|
| T1 pair-1 training (`ampscape/data/dataset.py`), accel pair-1 jobs | `t1_pair1` |
| Transfer evaluation, WP7 demo, any re-scoring of a trained model | `best_pt` |
| T4 exact-reference scoring of a new run (`train_full.sbatch`, `scripts/review/r3_t4_eval.py`) | `bs1_reference`, `blocksize` |
| WP5 scale probe, WP7 demo inputs | `scale_probe_*`, `wp7_h5` |

```bash
# Slurm CPU job on the cluster (compute nodes reach the Hub); --only takes a glob over the local paths
python scripts/maintenance/restore_from_hub.py --manifest docs/maintenance/restore_manifest_2026-11-14.jsonl \
    --groups best_pt bs1_reference [--only 'runs/full/unet_T4_L_*'] [--dry-run]
```
