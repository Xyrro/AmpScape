# Addendum WP3 report — non-source-pixel metrics

Date: 2026-09-17. Cost: code only (no compute beyond the unit tests and one harness run).

## What was added
`ampscape/metrics/nonsource.py`: `nonsource_mask(kind, base_mask, focal, source_strength, ground, halo=2)` and
`all_nonsource(pred, target, ns_mask, total_mask)` → `ns_rel_l2`, `ns_mae_log10eps`, `ns_top1_iou`, `ns_top5_iou`,
`ns_top10_iou`, `ns_fraction`. Masks: T4 = pixels with zero source strength (no halo — Omniscape sources are diffuse);
T1 / T1W / T1R = outside every focal pixel plus a 2-px Chebyshev halo; T3 = outside source and ground pixels plus the halo.
All masks are recoverable from the stored inputs for every task, so nothing is guessed. The harness reports them on every
split (`ns_rel_l2`, `ns_mae_log10eps`, `ns_top5_iou` primary; the rest secondary); `docs/evaluation.md` documents them.

## Tests
`tests/test_metrics_nonsource.py`: halo exclusion geometry, advanced/omniscape masks, and a hand-computed rel-L2 in which
two 0.5 errors on matrix pixels give ns_rel_l2 = √0.5/√15 while the plain rel-L2 is swamped by the 100-valued source pixel.

## First numbers (coarsen-×4 baseline, mini test_id, for illustration)
T1: rel-L2 0.381 overall vs **ns_rel_l2 0.218** (top-5 % IoU 0.617 vs ns 0.627); T1W 0.181 vs 0.180. For T1 the plain
rel-L2 is dominated by the focal pixels (reset to 1 A by construction in this baseline); the matrix error is smaller. The
learned-baseline tables (Phase 10) will be re-scored with these columns when the three-seed runs are made.

## Not done / notes
No change to stored data or splits. The halo radius (2 px) is a convention like the other domain thresholds and is
documented as such.
