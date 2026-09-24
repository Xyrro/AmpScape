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

## Tier L rows (2026-09-20: the full 60-sample L reference; `docs/tables/t4_pareto_L.md`, `docs/figures/t4_pareto_L.png`)

Errors against the exact block-1 map; cost = median single-core solve time per landscape.

| split | method | cost s | rel-L2 | ns rel-L2 | log-MAE | top-5 % IoU | pinch recall |
|---|---|---|---|---|---|---|---|
| test_id (24) | block 1 (exact) | 12 300 | 0 | 0 | 0 | 1 | 1 |
| test_id | block 3, ca on | 1 650 | 0.028 | 0.029 | 0.008 | 0.941 | 0.935 |
| test_id | **production block 5, ca on** | 566 | **0.032** | 0.036 | 0.014 | 0.934 | 0.932 |
| test_id | block 5, ca off | 638 | 0.101 | 0.114 | 0.022 | 0.771 | 0.977 |
| test_id | block 11, ca on | 164 | 0.085 | 0.095 | 0.041 | 0.832 | 0.818 |
| test_ood (16) | block 1 (exact) | 14 000 | 0 | 0 | 0 | 1 | 1 |
| test_ood | block 3, ca on | 2 020 | 0.018 | 0.027 | 0.007 | 0.939 | 0.950 |
| test_ood | **production block 5, ca on** | 706 | **0.020** | 0.035 | 0.032 | 0.932 | 0.954 |
| test_ood | block 5, ca off | 764 | 0.100 | 0.148 | 0.041 | 0.714 | 0.980 |
| test_ood | block 11, ca on | 201 | 0.061 | 0.109 | 0.094 | 0.823 | 0.856 |
| ood_region (20) | block 1 (exact) | 13 200 | 0 | 0 | 0 | 1 | 1 |
| ood_region | block 3, ca on | 1 820 | 0.026 | 0.021 | 0.007 | 0.934 | 0.936 |
| ood_region | **production block 5, ca on** | 725 | **0.028** | 0.026 | 0.011 | 0.931 | 0.927 |
| ood_region | block 5, ca off | 729 | 0.100 | 0.101 | 0.019 | 0.752 | 0.965 |
| ood_region | block 11, ca on | 191 | 0.079 | 0.066 | 0.034 | 0.832 | 0.819 |

Same picture as M one tier up, now on real tiles as well as synthetic landscapes: the production rule (b/r 0.078)
sits at 2–3 % for a 17–22× saving over the exact map; halving the block (3) buys 0.2–0.4 points of rel-L2 for 2.5–2.9×
the cost, i.e. block 3 and block 5 are within noise of each other on every split while block 3 costs three times
more; doubling it (11) loses 4–6 points for a 3.5–3.8× saving and drops top-5 % IoU from 0.93 to 0.83; the artefact
correction is worth 3.2–5× in rel-L2 at zero cost (0.10 → 0.02–0.03) and, without it, top-5 % IoU falls to 0.71–0.77
while pinch recall rises (uncorrected seams inflate the current on the whole map). The knee of the Pareto front at L
is the production block, as at M.

## Pending
Learned-model rows (three-seed baselines after the GPU allocation).
