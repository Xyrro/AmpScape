# T4 (Omniscape) target fidelity — settings, what was measured, what remains to be measured

Owner correction on the review addendum (2026-09-17): the production block rule was chosen by relative L2 and maximum
difference against the exact block-1 Omniscape, not by correlation alone. This page states exactly what was measured.

## Production settings (identical for every sample of a tier; recorded per sample in `solver_stats.solver_params`)

| tier | pixel | raster | radius (px / km) | block_size (b/r) | `correct_artifacts` | Omniscape solver | s per T4 solve (measured / scaled) |
|---|---|---|---|---|---|---|---|
| S | 100 m | 128² | 16 / 1.6 | **1 (exact)** | true (no effect at block 1) | CHOLMOD | 52 (measured: v1.0 median 50.5) |
| M | 100 m | 256² | 32 / 3.2 | 3 (0.094) | true | CHOLMOD | 134 (measured: v1.0 median 103) |
| L | 200 m | 512² | 64 / 12.8 | 5 (0.078) | true | CHOLMOD | 577 (scaled) |
| XL | 500 m | 1024² | 128 / 64 | 11 (0.086) | true | CHOLMOD | 1 896 (scaled) |
| XXL | 1 km | 2048² | 256 / 256 | 25 (0.098) | true | CHOLMOD | 9 613 (scaled; published XXL tile measured 10 435) |

Rule: `block = largest odd integer ≤ radius / 10` (`configs/datasets/v1_0.yaml`, `omniscape_choice: fidelity`; radii from
`configs/solver/omniscape_reference.yaml`). `correct_artifacts = true` (Omniscape 0.6.2 default; it only acts when
block_size > 1, i.e. it is inert at S). Sources: `inverse_resistance` suitability above the 0.5 quantile, rescaled to max 1;
`source_threshold = 0`; outputs `cum_current`, `flow_potential`, `normalized`.

## What the Phase-5/6 fidelity study measured (docs/dataset_plan.md §7; 3 samples per cell, CHOLMOD, cum_current on valid pixels)

Metrics: **relative L2**, **max |Δ| / max(cum_current)**, Pearson r, and relative L2 of `normalized`.

| comparison | b/r | rel-L2 mean / max | max-diff/max (range) | Pearson (min) | cost ratio |
|---|---|---|---|---|---|
| S: block 3 vs **block 1** | 0.19 vs 0.06 | 4.49 % / 7.60 % | 0.05–0.30 | 0.9951 | block 1 is 6.4× more |
| M: block 5 vs **block 1** | 0.16 vs 0.03 | 2.00 % / 2.45 % | 0.09–0.16 | 0.9874 | block 1 is 22.6× more |
| XL: block 17 vs block 33 | 0.13 vs 0.26 | 2.47 % / 2.93 % | 0.14–0.17 | 0.9788 | block 33 is 3.6× cheaper |
| XXL: block 33 vs block 65 | 0.13 vs 0.25 | 9.46 % / 11.85 % | 0.14–0.24 | 0.9559 | block 65 is 3.8× cheaper |

**Precisely what this does and does not establish.** The two anchors against the exact block-1 solution were run at
*coarser* blocks than production (S block 3 → 4.5 %; M block 5 → 2.0 %); the error grew monotonically with b/r
(0.19 → 4.5 %, 0.16 → 2.0 %, and doubling b/r from 0.13 to 0.26 added 2.5–9.5 %). The production rule b/r ≤ 0.10
(M 3, L 5, XL 11, XXL 25) was chosen by **extrapolating** those anchors to ≈ 1 % relative L2 against block 1. So:
S targets are exact; for M–XXL the "≈ 1 %" fidelity of the production block is an extrapolation from measured
anchors, **not itself a measurement**, and the max-difference metric already showed that the pixel-wise worst case
(5–30 % of the map maximum at the anchors) is much larger than the relative L2. The addendum's WP1 turns the
extrapolation into a measurement on a reference subset with block 1 (M, L) and adds top-q IoU, pinch-point recall,
log-MAE and the non-source rel-L2 (WP3); WP2 adds the block-size Pareto rows. Results: `docs/addendum_WP1_report.md`.

## How `block_size` enters the target
Omniscape solves one window per block centre (a block of block_size² source pixels is treated as one source), so
targets at block > 1 are the *block-centred* Omniscape map, with `correct_artifacts` smoothing block seams. Cost per
map ∝ (source pixels) / block². This approximation is part of the method definition recorded per sample; it is not a
data defect, but it bounds the fidelity a learned model can meaningfully be measured against — hence WP1 item 4.
