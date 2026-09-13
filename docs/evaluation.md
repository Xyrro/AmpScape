# Evaluation harness and predictions format

`python scripts/evaluate.py --predictions <dir> --split <name[,name]> [--root data/builds/mini --tier S --subset mini --out <dir> --acceleration]`

## Predictions directory

```
<dir>/predictions.h5      /<sample_id>/<config>/...   (one group per sample, one per configuration)
<dir>/meta.json           {"model": ..., "task": ..., "tier": ..., "split": ..., "notes": ..., "seed": ...}
```

| dataset (per configuration group) | dtype, shape | used for |
|---|---|---|
| `cum_current` | float32 (H, W) | T1 / T1W / T1R / T4 pixel + domain + physics metrics |
| `voltage` | float32 (H, W) or (P, H, W) — first pair used | Kirchhoff residual (T1, T3) and the solver-acceleration metric (`--acceleration`) |
| `reff` | float64 (K, K) | T2 metrics |
| `current`, `voltage` | float32 (H, W) | T3 |
| `flow_potential`, `normalized` | float32 (H, W) | T4 (optional) |
| attr `inference_time_s` | float | speed-up vs the recorded solver time |

Targets are read from a build (`index.parquet` + `shards/*.h5`) or an HF-layout root; only rows with
`qc_pass` in the requested split(s) are evaluated. Samples present in the index but absent from the
predictions file are skipped (the row count is reported), so any subset can be evaluated.

## Metrics (per task; mean, median, n in `results.json` / `results.md`)

- **Pixel** (masked: NoData; for T1W also the strip pixels): `mae_log10eps` = MAE of log10(C + ε·max C_target),
  ε = 1e-6; `rel_l2`; `mse`; secondary `ssim`, `psnr_db` (on the log maps scaled to [0, 1]).
- **Domain**: `top1/5/10_iou` (top-q % sets over masked-in pixels with non-zero flow), `corridor_dice_q10`,
  `pinch_recall` (target local maxima, 7×7, in the top 5 %; hit if a predicted local maximum lies
  within 3 px), `spearman`. **Thresholds are conventions, not validated ecological criteria.**
- **Reff (T2)**: `reff_rel_error`, `reff_mae_log10`, `reff_spearman`, `reff_nn_agreement`, `reff_symmetry`.
- **Physics**: `phys_kirchhoff_residual` (when a voltage is predicted; exact graph, collapsed rows for
  regions; a float32-stored exact voltage already gives ≈ 1e-5–1e-4, which is the floor for float32
  predictions), `phys_focal_current_err` (per-pair maps only: current at a unit source/ground pixel vs 1 A;
  for T1W the cumulative map is the pair map),
  `phys_neg_fraction` / `phys_neg_min_over_max` (non-negativity), `phys_throughput_err` (proxy).
- **Efficiency**: `speedup` = solver wall time / inference time per configuration; median and geometric mean.
- **Solver acceleration** (`--acceleration`, needs `voltage`): AMG-PCG iterations and wall time to
  rtol 1e-6 from the predicted voltage vs from zero, computed in Julia with the same preconditioner and
  matrix as the stored baselines; reported as median iteration and time reductions.

Determinism: samples are processed in sorted order; no randomness. Sanity anchors: an *oracle*
(prediction = target) scores 0 error / 1.0 on every similarity metric; an all-zero predictor scores
`rel_l2 = 1`, `top-q IoU = 0`.
