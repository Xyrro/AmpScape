# Addendum WP2 report — block-size Pareto baseline for T4 (tier M)

Date: 2026-09-19. Compute: ≈ 55 CPU-h (3 000 Omniscape solves on the 1 000-sample M reference subset). Nothing in v1.0 changed.

## Setup
Same 1 000 landscapes as the block-1 reference (`aux/t4_bs1_reference/M_bs1`: test_id 400, test_ood 300, ood_region 300;
real and synthetic). Radius 32 px. Rows: block 1 (exact), production block 3 with `correct_artifacts` (b/r 0.094),
block 3 without artefact correction, block 7 (b/r 0.22) with and without. `correct_artifacts` is a real config key of
Omniscape 0.6.2 (`src/config.jl`; it only acts when block > 1) and is passed through the aux inputs
(`omni_correct_artifacts` attr → `solve_omniscape(...; correct_artifacts)`). Outputs and timings under
`aux/t4_blocksize_baselines/M_b{3,7}_ca{0,1}/` (`vs_bs1.parquet`, `vs_bs1.md`); table `docs/tables/t4_pareto_M.md`;
figure `docs/figures/t4_pareto_M.png`; `scripts/t4_pareto.py` and `evaluate.py --t4-blocks` print the block rows beside a
learned model on every split (no M-trained model exists yet — the learned rows are added with the three-seed baselines).

## Result (errors against the exact block-1 map; mean over the split; cost = median single-core solve time)

| split | method | cost s | rel-L2 | ns rel-L2 | log-MAE | top-5 % IoU | pinch recall | Spearman |
|---|---|---|---|---|---|---|---|---|
| test_id | block 1 (exact) | 776 | 0 | 0 | 0 | 1 | 1 | 1 |
| test_id | **production block 3, ca on** | 111 | **0.029** | 0.037 | 0.012 | 0.936 | 0.931 | 0.998 |
| test_id | block 3, ca off | 112 | 0.111 | 0.107 | 0.026 | 0.611 | 0.766 | 0.986 |
| test_id | block 7, ca on | 25.5 | 0.098 | 0.106 | 0.053 | 0.808 | 0.808 | 0.985 |
| test_id | block 7, ca off | 25.4 | 0.292 | 0.377 | 0.068 | 0.547 | 0.966 | 0.966 |
| test_ood | production block 3, ca on | 133 | 0.032 | 0.052 | 0.011 | 0.915 | 0.925 | 0.995 |
| test_ood | block 3, ca off | 132 | 0.115 | 0.152 | 0.027 | 0.600 | 0.779 | 0.963 |
| test_ood | block 7, ca on | 30.2 | 0.103 | 0.149 | 0.089 | 0.768 | 0.822 | 0.963 |
| test_ood | block 7, ca off | 30.7 | 0.299 | 0.548 | 0.106 | 0.537 | 0.958 | 0.922 |
| ood_region | production block 3, ca on | 123 | 0.027 | 0.035 | 0.012 | 0.917 | 0.914 | 0.998 |
| ood_region | block 3, ca off | 121 | 0.109 | 0.100 | 0.027 | 0.496 | 0.728 | 0.981 |
| ood_region | block 7, ca on | 29.1 | 0.093 | 0.095 | 0.044 | 0.763 | 0.772 | 0.983 |
| ood_region | block 7, ca off | 25.3 | 0.292 | 0.331 | 0.060 | 0.443 | 0.975 | 0.960 |

## Reading
- **The artefact correction is worth 4× in relative L2 at no cost** (block 3: 0.029 with vs 0.111 without; block 7: 0.098
  vs 0.292) and it is what keeps the hot spots (top-5 % IoU 0.94 vs 0.61 at block 3). Without it the block seams dominate;
  the addendum's pilot (own re-implementation without the correction) was measuring that seam error, which the production
  pipeline does not have. Pinch-point recall *rises* without the correction (0.97 at block 7 ca off) because seam spikes
  create spurious local maxima that happen to cover the true ones — a reminder that recall alone is not a fidelity metric.
- **Block-size degradation is nearly split-independent**: production block 3 costs 0.027–0.032 rel-L2 on every split,
  block 7 (ca on) 0.093–0.103, with only the non-source rel-L2 on the contrast-10⁶ split noticeably worse (0.149). This
  is the expected "block_size degrades little OOD" behaviour; the learned-model rows will show whether models degrade
  more (Phase 10 dev evidence says they do on scale, less on biome/table hold-outs).
- **Cost–error frontier at M**: 776 s (exact) → 111 s (block 3, 2.9 % error) → 25 s (block 7, 9.8 %). A learned model has
  to land below 0.03 rel-L2 at ≈ 0.01 s/landscape to dominate the production block on this axis; the dev-scale U-Net was at
  0.09 rel-L2 on its own (exact, tier S) targets, i.e. currently comparable to block 7 in error and 2 500× cheaper.
- Spearman is ≥ 0.92 for every row including the worst — rank correlation cannot separate these baselines, which is why
  the harness reports rel-L2, non-source rel-L2 and top-q IoU as primary (WP3).

## Tier L rows (2026-09-20: the first 20 synthetic samples of the L reference; `docs/tables/t4_pareto_L.md`, `docs/figures/t4_pareto_L.png`)

| split | method | cost s | rel-L2 | ns rel-L2 | log-MAE | top-5 % IoU | pinch recall |
|---|---|---|---|---|---|---|---|
| test_id (12) | block 1 (exact) | 11 400 | 0 | 0 | 0 | 1 | 1 |
| test_id | block 3, ca on | 1 483 | 0.029 | 0.035 | 0.010 | 0.944 | 0.936 |
| test_id | **production block 5, ca on** | 545 | **0.035** | 0.045 | 0.018 | 0.937 | 0.947 |
| test_id | block 5, ca off | 561 | 0.098 | 0.108 | 0.026 | 0.800 | 0.978 |
| test_id | block 11, ca on | 137 | 0.092 | 0.122 | 0.054 | 0.840 | 0.811 |
| test_ood (8) | production block 5, ca on | 580 | 0.020 | 0.042 | 0.057 | 0.970 | 0.973 |
| test_ood | block 3 / block 11, ca on | 1 553 / 145 | 0.016 / 0.062 | 0.030 / 0.146 | 0.007 / 0.166 | 0.976 / 0.909 | 0.957 / 0.886 |
| test_ood | block 5, ca off | 602 | 0.105 | 0.175 | 0.063 | 0.899 | 0.988 |

Same picture as M one tier up: the production rule (b/r 0.078 here) sits at 3.5 % for a 21× saving over the exact map;
halving the block (3) buys 0.6 points of rel-L2 for 2.7× the cost; doubling it (11) loses 6 points for a 4× saving;
the artefact correction is again worth ≈ 2.8× in rel-L2 at zero cost. Re-scored once more when the reference reaches
45–60 samples (real tiles and ood_region are topped up as L real shards land).

## Pending
Learned-model rows (three-seed baselines after the GPU allocation); the L reference completion.
