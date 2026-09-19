# Addendum WP1 report — T4 ground-truth fidelity audit and block-1 reference subset (part 1: tier M)

Date: 2026-09-18. Compute used: ≈ 40 CPU-h (200 block-1 Omniscape solves at M, 17 Slurm tasks). Nothing in v1.0 changed.

## 1. Settings and what the original study measured
`docs/t4_fidelity.md`: block/radius/`correct_artifacts` per tier; the Phase-5/6 study used relative L2, max |Δ|/max and
Pearson against block 1 at S block 3 (4.5 %) and M block 5 (2.0 %) and **extrapolated** the production rule
(b/r ≤ 0.10) to ≈ 1 %; S targets are exact (block 1); `correct_artifacts = true` everywhere (inert at S).

## 2. Extension of the metrics and the block-1 reference subset
`aux/t4_bs1_reference/M_bs1/` (selection.parquet, manifest, inputs with `omni_block_size = 1`, outputs with solve times,
`index.parquet` keyed by `sample_id`, `summary.md/json`): the first 100 test_id and 100 test_ood M landscapes whose
production shards were on the Hub at selection time. **They are all synthetic** (the M real shards are generated last;
test_ood at M is currently the contrast-10⁶ hold-out, 102 of the 200 samples). Production (block 3, `correct_artifacts`)
vs block 1, per-sample metrics incl. the WP3 non-source columns:

| split | rel-L2 mean / median / max | ns rel-L2 | log-MAE | top-1/5/10 % IoU | pinch recall | max Δ/max | Spearman | cost ratio |
|---|---|---|---|---|---|---|---|---|
| test_id (100) | 0.031 / 0.028 / 0.254 | 0.040 / 0.034 / 0.155 | 0.012 | 0.911 / 0.945 / 0.956 | 0.953 | 0.090 (max 0.40) | 0.998 | 6.7× |
| test_ood (100) | 0.031 / 0.024 / 0.247 | 0.054 / 0.041 / 0.366 | 0.012 | 0.933 / 0.959 / 0.969 | 0.958 | 0.073 (max 0.52) | 0.998 | 6.5× |

By contrast: mean rel-L2 0.029–0.037 at every level; the tail (9 % of landscapes > 5 %, 2 % > 10 %, worst 25 %) sits on
`random_cluster` landscapes at contrast ≥ 10⁴ (block seams across fragmented high-contrast texture); the OOD split is not
worse than test_id in the mean, only in the non-source tail. **The ≈ 1 % extrapolation was optimistic by ≈ 3× in relative
L2**; rank-level and hot-spot quantities are stable (Spearman 0.998, top-5 % IoU 0.95, pinch recall 0.95).

## 3. Flag check (item 4): production-target-vs-block-1 error vs best-baseline-vs-production-target error
No M-trained model exists yet, so the comparison uses the dev (tier S, exact targets) U-Net as the best available
baseline: test_id rel-L2 **0.093**, top-5 % IoU 0.74, pinch recall 0.83 — versus the M label approximation
**0.031** (ns 0.040), top-5 % IoU 0.95, pinch recall 0.95. The mean label approximation is ≈ 3× smaller than the best
model error and its domain-level effect (IoU, pinch points) is 3–4× smaller, so the condition "not clearly smaller" is
**not met on the mean**; it *is* met in the tail (the worst 2 % of landscapes have label deviations of 10–25 %, comparable
to model error). Recommended reading for the paper: T4 at M–XXL is a benchmark against the *block-centred* Omniscape with a
quantified 3 % (M) approximation; per-sample deviations are published in the aux index so users can exclude the tail.
**Stopping here for the owner's decision** (per the addendum) before WP2; the pending parts below continue on approval.

## 4. Pending parts of WP1 (cost)
- M real tiles and `ood_region` (100 samples ≈ 23 CPU-h): after the M real shards (300–499) are generated (driver, ≈ 1–2 days).
- L block-1 reference (45 samples: 15 per split, ≈ 4 h each ≈ 180 CPU-h): after L production exists; L is planned
  (`data/v1/L`, 1 000 shards) so the subset can be prepared now and the solves started as soon as the owner approves the cost.
- XL/XXL: block 1 is infeasible (11² and 25² times the production cost); the M and L measurements plus the study's
  monotonic b/r trend are the fidelity statement for those tiers.

## 5. Part 2 (2026-09-19): the 1 000-sample M reference (official T4 evaluation surface at M)

Owner decision 2026-09-18 implemented: `aux/t4_bs1_reference/M_bs1/` grown to 1 000 samples by stratified quotas
(test_id: 200 synthetic + 200 real; test_ood: 150 contrast-10⁶ + 150 forest_bird; ood_region: 300 real), block 1 solved
for all of them (≈ 205 CPU-h incl. three re-runs of shards that exceeded the 4-h walltime on real tiles and one re-chunked shard; all 1 000 scored). Production (block 3) vs block 1:

| split | family | n | rel-L2 mean / median / max | ns rel-L2 | top-5 % IoU | pinch recall | max Δ/max |
|---|---|---|---|---|---|---|---|
| test_id | real | 200 | 0.027 / 0.028 / 0.046 | 0.035 | 0.930 | 0.912 | 0.101 |
| test_id | synthetic | 200 | 0.032 / 0.028 / 0.254 | 0.040 | 0.941 | 0.952 | 0.092 |
| test_ood | real (forest_bird) | 150 | 0.026 / 0.024 / 0.052 | 0.038 | 0.880 | 0.893 | 0.101 |
| test_ood | synthetic (contrast 10⁶) | 150 | 0.038 / 0.025 / 0.482 | 0.065 | 0.951 | 0.958 | 0.085 |
| ood_region | real | 300 | 0.027 / 0.027 / 0.076 | 0.035 | 0.917 | 0.914 | 0.102 |

Overall: mean rel-L2 0.029, median 0.027; **47 of 1 000 samples (4.7 %) in the > 5 % tail — 11 % of the synthetic
samples but only 1.4 % of the real tiles** (the tail is the fragmented high-contrast synthetic texture); real tiles have
no deviation above 8 %. Block 1 costs 7.2× the production solve. The per-sample index (`index.parquet`, keyed by
`sample_id`, with `tail_gt5pct`) and `summary.md` are the published artefacts; the harness uses the reference with
`--t4-reference aux/t4_bs1_reference/M_bs1`.

## 6. Tier L reference (interim, 2026-09-19): first 13 of 20 synthetic samples

Production block 5 (radius 64 px, b/r 0.078, `correct_artifacts`) vs block 1: test_id (n = 9) rel-L2 **0.036** / median
0.032 / max 0.058, non-source 0.048, top-5 % IoU 0.95, pinch recall 0.94, max Δ/max 0.105; test_ood contrast-10⁶ (n = 4)
rel-L2 0.023, non-source 0.047, top-5 % IoU 0.97. Block 1 at L costs **21× the production solve** (median 12 080 s vs
564 s, i.e. ≈ 3.4 CPU-h per landscape), which is why the L reference is a 45–60-sample sanity set. The remaining 7
samples of the first batch are re-solved with a 16-h walltime (the solver resumes completed samples); the real-tile
and ood_region parts are topped up hourly as L real shards reach the Hub. Interim reading: the M-level approximation
(≈ 3 %) holds at L with the same b/r rule.
