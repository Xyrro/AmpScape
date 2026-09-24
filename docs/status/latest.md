# Status — 2026-09-24 09:20Z: Phase 10-full running; headline S and M/T1 results in

## Progress
- 19 of 132 runs finished (all S seed-1 and most S seed-2 runs; U-Net and FNO T1 at M seed 1); 18 legs queued or
  running; WP4 data-scaling at S started (unet n1000/n5000). Running table: `docs/tables/baselines_full.md`.
- Headline rel-L2 on test_id (seed 1): T1 S — U-Net 0.111, FNO 0.198, ViT 0.238; T1 M — U-Net 0.238, FNO 0.266
  (error roughly doubles from S to M for both); T4 S — U-Net 0.040, FNO 0.070, ViT 0.071 (T4 S below 0.05 as flagged
  earlier). M evaluation takes ≈ 45 min (FNO) in its own leg.
- Training is 3–7× under the budget estimates; the calendar estimate is bounded by staging and the 32-GPU-hour
  running cap, not by GPU time.

## Changes to the schedule and operation (all committed)
- Three M legs (fno T1 s1/s2, vit T1 s1) hit the 2-h walltime during evaluation before the evaluation-deferral patch;
  they resumed from `done.json` in fresh evaluation legs (no training lost). No timeout since the patch.
- Staging is now strict-priority with eviction by furthest next use and **draining**: groups pinned by running jobs
  that block a higher-priority group stop receiving new jobs until they can be evicted (evaluation-only legs exempt).
  Priorities are tier-major (S → M → L → XL inside P1/P2/P3), so the headline M/T4 runs stage before L.
- Scratch floor without the training cache is ≈ 143 GB (data/tiles 37, data/sources 20, data/dev 12, aux 18, runs,
  caches). Under the 265 GB guard the cache can hold ≈ 120 GB, so the L groups (T1 84 GB, T4 82 GB) cannot be
  staged together: L runs will proceed group by group (L/T1 U-Net and FNO, then L/T4), adding roughly one day to
  the L milestone. XL groups (61 + 61 GB) fit together.
- Offloader restarted correctly (`scripts/slurm/gpu/offload_loop.sh`); finished runs are on the Hub under
  `aux/results/runs_full/<run>/` and their predictions removed locally.

## For the owner (no action taken)
- Deleting `data/sources` (20 GB) and `data/tiles/v1.0` (37 GB) from scratch would let both L groups stay staged
  and remove the group-by-group serialisation. Both are re-downloadable/regenerable (sources from the manifest
  URLs; tiles from sources), and WP7 keeps its own copies of the 20 tiles under `aux/wp7/tiles`. I will not delete
  them without approval.
- The published real-tile set exists at S only, so M/L/XL runs report test_id / test_ood / ood_region (T4 M/L also
  the exact block-1 reference rows).

Next: headline M/T4 (U-Net, FNO), then L; weekly report or on schedule changes.
