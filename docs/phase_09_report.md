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

TODO_PUBLISHED

## 4. Non-learned baseline: coarsen ×4 → CHOLMOD → upsample

TODO_BASELINE

## 5. Tests, commits

TODO_TESTS
