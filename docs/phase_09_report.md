# Phase 9 report — metrics, evaluation harness, published-resistance OOD set, non-learned baseline

Date: 2026-09-13. Status: **complete, awaiting owner confirmation** before Phase 10 (learned baselines).

## 1. Metrics (`ampscape/metrics`)

| module | metrics | notes |
|---|---|---|
| `pixel` | `mse`, `mae_log10eps`, `rel_l2`; secondary `ssim`, `psnr_db` | log10(C + ε·max C_target), ε = 1e-6 (owner decision, replaces log1p); SSIM/PSNR on the log maps scaled to [0, 1] |
| `domain` | `top1/5/10_iou`, `corridor_dice_q10`, `pinch_recall`, `spearman` | top-q sets exclude zero-flow pixels; pinch points = 7×7 local maxima inside the top 5 % (hit radius 3 px); Spearman is NaN for constant inputs; **thresholds are conventions, not validated ecological criteria** |
| `reff` (T2) | `reff_rel_error`, `reff_mae_log10`, `reff_spearman`, `reff_nn_agreement`, `reff_symmetry` | over the upper triangle of the K×K matrix |
| `physics` | `phys_kirchhoff_residual` (exact graph, collapsed rows for regions, re-exported from `ampscape.solve.qc`), `phys_focal_current_err` (per-pair maps; 1 A at a unit source/ground), `phys_neg_fraction` / `phys_neg_min_over_max`, `phys_throughput_err` | a float32-stored *exact* voltage already gives ≈ 1e-5–1e-4 residual, the floor for float32 predictions |
| `efficiency` | `speedup` per configuration (solver wall time / inference time), median and geometric mean | solver time = the recorded reference wall time of the same configuration |
| `acceleration` | AMG-PCG iterations / wall time to rtol 1e-6 from the predicted voltage vs from zero (`scripts/warm_start_eval.jl`, same preconditioner and matrix as the stored `cg_baseline`) | needs `voltage` and a stored zero-start baseline (test/OOD samples) |

Masking: NoData pixels always; for T1W also the strip pixels (they carry the injected current by
convention). Every metric has a hand-computed unit test (`tests/test_metrics.py`,
`tests/test_metrics_transforms.py`): the oracle scores 0 error / 1.0 similarity, an all-zero predictor
scores rel-L2 1 and IoU 0, and the specific constructed cases (shifted peak, half-correct top-q set,
asymmetric Reff, negative pixels, 2× speed-up) give the expected numbers.

## 2. `scripts/evaluate.py` and the predictions format

`python scripts/evaluate.py --predictions <dir> --split test_id[,test_ood,…] [--root … --tier … --subset … --out … --acceleration]`

The format (`docs/evaluation.md`): one `predictions.h5` with `/<sample_id>/<config>/{cum_current, voltage,
pairwise_current, reff, current, flow_potential, normalized}` plus the attribute `inference_time_s`, and a
`meta.json` (model, task, tier, split, notes, seed). Targets come from a build root or an HF-layout root;
only `qc_pass` rows of the requested splits are evaluated; samples missing from the file are skipped and
counted, so any subset works. Output: `results.json` (per-task mean/median/n, per-sample rows, run
metadata) and `results.md`. Deterministic: sorted sample order, no randomness.

## 3. `test_ood_published`

Built from the three CC BY 4.0 / CC0 rasters registered in Phase 7–8 (`docs/survey_resistance_surfaces.md`,
`docs/licenses.md`), resistance used **as given**, no re-mapping:

| source | native | tier (rule: nearest tier with pixel ≥ native, geometric mean of R = area mean of log R) | tiles | R range | NoData |
|---|---|---|---|---|---|
| Eurac Alps landscape permeability (CC BY 4.0) | 20 m, EPSG:32631 | S (100 m) | 30 | 1–1000 | 0.2 % |
| Hawaiian gallinule resistance (CC0) | 10 m, EPSG:32604 (CRS not embedded in the archive; UTM 4N assumed and recorded) | S (100 m) | 15 | 1–100 | 0 % |
| Raccoon Europe (CC BY 4.0) | 1 km | XXL (1 km, native) | 1 (centre 55.0° N, 24.7° E) | 1.19–100 | 13.8 % |

Tiles are `pub_<source>_<tier>_<hash>` (`data/tiles/published/published_tiles.parquet`, 2-band GeoTIFFs with a
provenance JSON tag: source DOI, licence, native pixel size, resampling rule, CRS assumption). The planner
family `published` gives them split `test_ood_published`, all applicable tasks (points K per tier, wall-to-wall
NS/EW, advanced, Omniscape with the tier's radius/block) and `cg_baseline = true`. Build `data/builds/published`
(Slurm array 5774245: three S shards 16–21 min each, the XXL shard 3 h 0 min of which Omniscape 2 h 54 min,
peak RSS 9.6 GB — consistent with the XXL_test profile entry). Reference solver CHOLMOD throughout, no fallback;
residuals ≤ 5.5e-10 (S) and ≤ 3.5e-9 (XXL), no refinement triggered.

Finalised (`generate.py finalize --quicklooks`, job 5776137): 46 samples / 230 configuration rows, **100 % QC
pass**, index split `test_ood_published` = 46, quicklooks for every sample (the raccoon XXL tile spans the
south-eastern Baltic; 13.8 % NoData = sea). The published rasters are included in the manifest and
`docs/licenses.md` (Phase 8); the build is not on HF yet (mini-only repo; publication route per DECISIONS).

Coarsen-×4 baseline on `test_ood_published` (`data/predictions/coarsen4_published/eval_test_ood_published/`, jobs
5776137 + 5776269; the XXL coarse solve exposed an ungrounded coarse island → `refine_voltage!` now catches a
non-positive-definite reduced system and the coarsener drops sources on ungrounded islands):

| task | source (tier) | n | mae_log10eps | rel_l2 | top5_iou | pinch_recall | corridor_dice_q10 | spearman | reff_rel_error | speed-up (mean) |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | Eurac Alps (S) | 30 | 0.155 | 0.483 | 0.474 | 0.275 | 0.714 | 0.898 | 0.176 | 5.4 |
| T1 | gallinule (S) | 15 | 0.058 | 0.469 | 0.565 | 0.298 | 0.795 | 0.969 | 0.142 | 6.0 |
| T1 | raccoon (XXL) | 1 | 0.041 | 0.485 | 0.778 | 0.145 | 0.885 | 0.980 | 0.086 | 15.5 |
| T1W | Eurac Alps (S) | 60 | 0.149 | 0.390 | 0.361 | 0.231 | 0.621 | 0.822 | 0.052 | 2.5 |
| T1W | gallinule (S) | 30 | 0.044 | 0.236 | 0.296 | 0.309 | 0.525 | 0.666 | 0.018 | 2.7 |
| T1W | raccoon (XXL) | 2 | 0.048 | 0.154 | 0.637 | 0.186 | 0.814 | 0.970 | 0.025 | 5.5 |
| T3 | Eurac Alps (S) | 30 | 0.157 | 0.407 | 0.501 | 0.263 | 0.728 | 0.898 | – | 3.0 |
| T3 | gallinule (S) | 15 | 0.055 | 0.322 | 0.593 | 0.288 | 0.803 | 0.965 | – | 3.3 |
| T3 | raccoon (XXL) | 1 | 0.048 | 0.138 | 0.781 | 0.224 | 0.898 | 0.987 | – | 11.5 |
| T4 | Eurac Alps (S) | 30 | 0.456 | 0.748 | 0.490 | 0.326 | 0.724 | 0.928 | – | 59 |
| T4 | gallinule (S) | 15 | 0.475 | 0.759 | 0.425 | 0.310 | 0.637 | 0.907 | – | 81 |
| T4 | raccoon (XXL) | 1 | 0.525 | 0.753 | 0.657 | 0.227 | 0.823 | 0.979 | – | 28 |

Overall (230 rows): T1 mae 0.121 / rel-L2 0.479 / top-5 IoU 0.510; T1W 0.113 / 0.335 / 0.346; T3 0.122 / 0.373 /
0.538; T4 0.463 / 0.752 / 0.472 — the same order as on the mini test splits, with the Eurac Alps tiles (20 m
native, contrast 10³, strongly textured) the hardest S set. Acceleration on the 68 systems with a stored
baseline: no gain (iterations 14 → 14 median; XXL T3 35 → 38, the interpolated voltage has a relative residual
of 3.4e4 on the 3.6 M-node fine graph), i.e. an upsampled coarse solution is not a useful PCG warm start.



## 4. Non-learned baseline: coarsen ×4 → CHOLMOD → upsample

Method (`ampscape/models/coarsen.py`, `scripts/baseline_coarsen.py`, brief §12.1): resistance → geometric
mean over 4×4 blocks; NoData → majority; focal labels → any pixel of the block; T3 sources → block sum
(Σ S = 1), T4 sources → block mean; ground → any; Omniscape radius and block ÷ 4. Reference CHOLMOD solve on
the 32×32 grid (Slurm job 5774662, 4 CPUs, 9.9 min for 44 landscapes incl. Julia start-up), bilinear
upsampling, Reff taken from the coarse solve. Three scale rules were needed to make the baseline
physically comparable and are documented in `DECISIONS.md`:

1. pairwise/advanced current maps are divided by f (a coarse node collects the flow crossing f fine
   pixels); Omniscape maps are not (their sources were mean-pooled); the true focal pixels are reset to
   the exact 1 A per pair, and coarse focal pixels are in-filled from the nearest non-focal coarse pixel
   before upsampling (the naive version stamped 4-pixel-wide bands with the injected current: T1W rel-L2
   1.91 → 0.24);
2. for T3, a coarse block holding both a source and a ground pixel becomes ground only, the remaining
   sources are renormalised — Circuitscape leaves a node that is both source and ground ungrounded (27 of
   the 32 coarse ground nodes of one mini sample sat at up to 4.7 V; T3 rel-L2 0.90 → 0.26);
3. for T3, the block-summed injection is removed before the 1/f scaling and the fine injection added
   back (node current = through-flow + injection).

Inference time = coarsening + coarse solve + upsampling, measured per landscape.

### Results (mini, tier S, `evaluate.py`, mean over configurations; `data/predictions/coarsen4/eval_*/`)

| task | split | n | mae_log10eps | rel_l2 | top5_iou | pinch_recall | corridor_dice_q10 | spearman | reff_rel_error | reff_spearman | ssim | speed-up (median) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | test_id | 15 | 0.075 | 0.381 | 0.617 | 0.390 | 0.835 | 0.970 | 0.167 | 0.934 | 0.863 | 2.59 |
| T1W | test_id | 30 | 0.064 | 0.181 | 0.457 | 0.453 | 0.717 | 0.888 | 0.037 | – | 0.733 | 2.32 |
| T3 | test_id | 15 | 0.077 | 0.195 | 0.692 | 0.387 | 0.860 | 0.963 | – | – | 0.867 | 2.85 |
| T4 | test_id | 15 | 0.446 | 0.712 | 0.668 | 0.638 | 0.822 | 0.951 | – | – | 0.837 | 62.0 |
| T1 | test_ood | 8 | 0.120 | 0.531 | 0.448 | 0.164 | 0.695 | 0.908 | 0.116 | 0.953 | 0.663 | 4.47 |
| T1R | test_ood | 6 | 0.184 | 0.185 | 0.652 | 0.476 | 0.733 | 0.910 | 0.104 | 0.986 | 0.689 | 3.88 |
| T1W | test_ood | 16 | 0.115 | 0.363 | 0.249 | 0.127 | 0.490 | 0.698 | 0.123 | – | 0.446 | 2.39 |
| T3 | test_ood | 8 | 0.118 | 0.355 | 0.450 | 0.150 | 0.685 | 0.912 | – | – | 0.691 | 2.95 |
| T4 | test_ood | 8 | 0.477 | 0.749 | 0.425 | 0.228 | 0.623 | 0.879 | – | – | 0.513 | 81.1 |
| T1 | ood_region | 21 | 0.095 | 0.432 | 0.618 | 0.394 | 0.809 | 0.945 | 0.144 | 0.950 | 0.789 | 2.40 |
| T1R | ood_region | 8 | 0.147 | 0.257 | 0.576 | 0.419 | 0.730 | 0.905 | 0.096 | 0.987 | 0.745 | 4.71 |
| T1W | ood_region | 42 | 0.079 | 0.234 | 0.340 | 0.165 | 0.561 | 0.759 | 0.087 | – | 0.596 | 2.40 |
| T3 | ood_region | 21 | 0.087 | 0.262 | 0.572 | 0.318 | 0.765 | 0.931 | – | – | 0.779 | 2.94 |
| T4 | ood_region | 21 | 0.476 | 0.726 | 0.553 | 0.489 | 0.759 | 0.919 | – | – | 0.703 | 58.0 |
| **T1** | all three | 44 | 0.093 | 0.433 | 0.587 | 0.351 | 0.797 | 0.947 | 0.147 | 0.945 | 0.791 | 2.44 |
| **T1R** | all three | 14 | 0.163 | 0.227 | 0.608 | 0.444 | 0.731 | 0.907 | 0.100 | 0.986 | 0.721 | 4.30 |
| **T1W** | all three | 88 | 0.080 | 0.239 | 0.363 | 0.256 | 0.601 | 0.792 | 0.076 | – | 0.616 | 2.39 |
| **T3** | all three | 44 | 0.089 | 0.256 | 0.591 | 0.311 | 0.783 | 0.938 | – | – | 0.793 | 2.94 |
| **T4** | all three | 44 | 0.466 | 0.725 | 0.569 | 0.493 | 0.756 | 0.922 | – | – | 0.714 | 61.0 |

Physics and acceleration (all three splits): `phys_neg_fraction` = 0 everywhere; `phys_focal_current_err`
= 0 (focal pixels reset by construction); `phys_throughput_err` 0.03 (T1), 0.19 (T1R), 0.015 (T1W),
0.017 (T3); Kirchhoff residual of the upsampled voltage (median) 1.2 (T1), 0.77 (T1R), 0.33 (T1W), 10.5
(T3) — an interpolated field is not a solution of the fine graph, as expected. Solver acceleration on the
70 systems with a stored zero-start baseline (T3 and K ≤ 4 T1): AMG-PCG iterations 11 → 10 (median
reduction 6.9 %), time 28 ms → 22 ms (7.5 %); warm-start residual median 2.7 (zero start = 1). At tier S
the PCG converges in ≈ 11 iterations, so the acceleration track has little headroom there; it is meant
for XL/XXL where the baseline needs hundreds of iterations.

Reading: the baseline recovers the global pattern (Spearman 0.79–0.95, corridor Dice 0.6–0.8) but loses
the fine structure (top-5 % IoU 0.36–0.61, pinch-point recall 0.26–0.49) and is worst on Omniscape (T4
mae 0.47), whose radius/block ÷ 4 changes the moving-window integration itself. T1W and T4 degrade most
on `test_ood` (contrast 10⁶, saturated tables). Speed-up is 2.4–4.7× for the Circuitscape tasks and
≈ 60× for Omniscape (16× fewer windows, each 16× smaller). These numbers are the reference row for the
Phase 10 learned baselines.


## 5. Tests, commits

- Tests: 122 passing (`pytest --ignore=tests/test_real_network.py`, 3 min); new `tests/test_coarsen.py` (6),
  `tests/test_metrics.py` (5), `tests/test_metrics_transforms.py`.
- Compute this phase (ICE, all within the gates): published build 3 × ~18 min + 3 h 0 min (4 CPUs each),
  baseline/finalize/eval jobs 10–12 min each, warm-start evaluations on the login node (≈ 6 min, Julia
  start-up dominated); cumulative ICE usage stays far below 500 CPU-h. No downloads, no HF pushes.
- Harness fixes found while running the baseline (all in `DECISIONS.md`): per-pair focal-current check
  (the cumulative map carries pass-through current), zero-flow pixels excluded from top-q sets and pinch
  points (plateaus of zeros were counted as maxima), published tiles' root resolution in `prepare`,
  the three baseline scale rules, robust refinement.
- Open: the acceleration track only becomes informative at XL/XXL with a *learned* voltage; a coarse-solve
  warm start does not help. The metric thresholds (top-q, 7×7 maxima, 3 px) remain conventions
  (brief §17). GRIP4 licence still awaiting PBL's reply (owner).

## Next step (Phase 10, on confirmation)

Learned baselines on the mini (brief §12): U-Net / FNO-style surrogates for T1/T1W/T3/T4 in log10-ε space,
a Reff head for T2, training on `train` with the train-only normalisation stats, evaluation through
`evaluate.py` on `test_id`, `test_ood`, `ood_region` and `test_ood_published`, GPU runs ≤ 20 GPU-h.

