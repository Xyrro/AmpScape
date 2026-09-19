# Addendum WP2 report — block-size Pareto baseline for T4 (tier M)

Date: 2026-09-19. Compute: ≈ 55 CPU-h (3 000 Omniscape solves on the 1 000-sample M reference subset). Artefacts:
`aux/t4_blocksize_baselines/M_b{3,7}_ca{0,1}/` (inputs, outputs with solve times, `vs_bs1.parquet` / `.md` scored
against the block-1 reference), `docs/tables/t4_pareto_M.md`, `docs/figures/t4_pareto_M.png`. Nothing in v1.0 changed.

## Design
Blocks ≈ {0.05, 0.1, 0.2}·r at r = 32 px → odd blocks {1, 3, 7}; `correct_artifacts` on and off (the installed
Omniscape 0.6.2 exposes the key `correct_artifacts`, verified in its source; it is inert at block 1). Block 1 is the
reference (WP1), block 3 with correction is the production target. All rows score against the exact block-1 map on the
same 1 000 samples (test_id 400, test_ood 300, ood_region 300; real and synthetic), so they are directly comparable with
learned models evaluated with `scripts/evaluate.py --t4-reference` (`scripts/t4_pareto.py --runs …` adds the learned rows
with their batch-amortised inference cost once M-trained models exist — none yet: Phase 10 trained at S only).

## Results (mean over samples; cost = median single-core Omniscape solve per 256² landscape)

| split | method | cost s | rel-L2 | ns rel-L2 | log-MAE | top-5 % IoU | pinch recall | Spearman |
|---|---|---|---|---|---|---|---|---|
| test_id | block 1 (exact) | 776 | 0 | 0 | 0 | 1 | 1 | 1 |
| test_id | **block 3, corrected (production)** | 111 | **0.029** | 0.037 | 0.012 | 0.936 | 0.931 | 0.998 |
| test_id | block 3, uncorrected | 112 | 0.111 | 0.107 | 0.026 | 0.611 | 0.766 | 0.986 |
| test_id | block 7, corrected | 25.5 | 0.098 | 0.106 | 0.053 | 0.808 | 0.808 | 0.985 |
| test_id | block 7, uncorrected | 25.4 | 0.292 | 0.377 | 0.068 | 0.547 | 0.966* | 0.966 |
| test_ood | block 3, corrected (production) | 133 | 0.032 | 0.052 | 0.011 | 0.915 | 0.925 | 0.995 |
| test_ood | block 3, uncorrected | 132 | 0.115 | 0.152 | 0.027 | 0.600 | 0.779 | 0.963 |
| test_ood | block 7, corrected | 30.2 | 0.103 | 0.149 | 0.089 | 0.768 | 0.822 | 0.963 |
| test_ood | block 7, uncorrected | 30.7 | 0.299 | 0.548 | 0.106 | 0.537 | 0.958* | 0.922 |
| ood_region | block 3, corrected (production) | 123 | 0.027 | 0.035 | 0.012 | 0.917 | 0.914 | 0.998 |
| ood_region | block 3, uncorrected | 121 | 0.109 | 0.100 | 0.027 | 0.496 | 0.728 | 0.981 |
| ood_region | block 7, corrected | 29.1 | 0.093 | 0.095 | 0.044 | 0.763 | 0.772 | 0.983 |
| ood_region | block 7, uncorrected | 25.3 | 0.292 | 0.331 | 0.060 | 0.443 | 0.975* | 0.960 |

\* pinch-point recall is inflated for the uncorrected maps: the block-seam spikes create spurious local maxima that hit
every true pinch point by chance — the top-q IoU columns show the real loss (0.44–0.55).

## Reading
- **Artefact correction is the dominant factor**, not the block size: block 3 uncorrected is 4× worse than the production
  block 3 corrected (0.11 vs 0.03 rel-L2) and no better than block 7 corrected at 4.4× the cost. The Omniscape default
  (`correct_artifacts = true`) is the right production choice and is what the benchmark's targets use.
- The block-size ladder at fixed correction gives the expected cost–error trade-off: 1 → 3 → 7 costs 776 → 111 → 26 s per
  landscape for 0 → 0.03 → 0.10 rel-L2 (top-5 % IoU 1 → 0.94 → 0.81). These are the non-learned rows every learned T4
  model must beat at its inference cost.
- **OOD behaviour**: the block-size rows degrade little from test_id to test_ood / ood_region (e.g. production 0.029 → 0.032
  → 0.027; block 7 corrected 0.098 → 0.103 → 0.093), as the addendum expected; the learned-model comparison on the same
  axis needs M-trained models (Phase 12 full baselines), after which `t4_pareto.py` prints both families side by side per
  split with cost columns.
- Spearman stays ≥ 0.92 for every row, including block 7 uncorrected with rel-L2 0.29 — rank correlation hides pixel-level
  and hot-spot error, as the pilot suggested; the paper should not report Spearman alone for T4.

## Not done / pending
L (block 5 production; blocks {3, 7, 13}) after the L block-1 sanity reference exists (WP1, on approval of the ≈ 210
CPU-h). Learned rows: after the M-trained baselines. Stopping here for the owner's confirmation (addendum §6).
