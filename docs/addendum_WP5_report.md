# Addendum WP5 report — resolution-versus-size confound (analysis and probe design; no generation yet)

Date: 2026-09-17. Cost of this package: analysis only. Probe-set cost estimate below (not launched).

## 1. Pixel size × raster size × Omniscape radius per tier

| tier | pixel size | raster | extent | Omniscape radius (px / km) | block |
|---|---|---|---|---|---|
| S | 100 m | 128² | 12.8 km | 16 / 1.6 km | 1 |
| M | 100 m | 256² | 25.6 km | 32 / 3.2 km | 3 |
| L | 200 m | 512² | 102 km | 64 / 12.8 km | 5 |
| XL | 500 m | 1024² | 512 km | 128 / 64 km | 11 |
| XXL | 1 km | 2048² | 2 048 km | 256 / 256 km | 25 |

**Finding.** Three quantities co-vary across tiers: raster size (pixels), pixel size (metres), and — for T4 — the window
radius, which is fixed in *pixels* (radius = raster/8) and therefore grows in kilometres with the tier. Only S → M
changes one factor at a time (same 100 m pixel, 2× the raster and 2× the radius in pixels). From M to L and beyond,
`test_ood_scale` mixes (i) extrapolation in pixel count, (ii) coarser pixels (different texture statistics of the real
covariates and of the synthetic priors, whose length scales are in pixels), and (iii) a larger physical window for T4.
The dev-subset result that models collapse on the XXL published tile therefore cannot be attributed to any one of these.
Consequence for the paper: state the confound and interpret `test_ood_scale` as "scale" in the combined sense, with the
probe set below separating the axes where it matters.

## 2. Geographic independence of XXL real tiles across splits (owner question, written confirmation)

XXL is test-only. XXL tiles are *not* their own assignment regions (owner decision 2026-09-14): S–XL tiles are assigned
by the frozen macro-cell rule, so an XXL footprint (2 048 km) does overlap finer-tier training cells — this is
disclosed in the task specification and the card (`test_ood_scale` at XXL isolates resolution, not spatial novelty).
The strict subset `test_ood_scale_strict` (6 XXL tiles sampled inside test_id cells only, with a geometric check at
finalize that no train/val tile of any tier intersects their boxes) is the geographically independent XXL set. XL tiles
are cell-assigned and overlap-free by construction (the sampler snaps XL centres into a cell's interior box).

## 3. Controlled probe set (design; owner confirmation required before generation)

Two-by-two design from **existing v1.0 L tile centres** (real) and matching synthetic seeds, one resistance table
(large_mammal) for real tiles, all configurations solved with the production settings of the *matching tier* where one
exists, and the same Omniscape radius **in kilometres** (12.8 km) in every cell so that T4 compares like with like:

| | raster 256² | raster 512² |
|---|---|---|
| **pixel 100 m** | 25.6 km window: **M-native** (radius 128 px = 12.8 km, block 11) | 51.2 km: **new extraction at 100 m** of the L centre (radius 128 px, block 11) |
| **pixel 200 m** | 51.2 km: **central crop of the L tile** (radius 64 px, block 5) | 102 km: **L-native** (radius 64 px, block 5) |

Rows compare raster size at fixed pixel size; columns compare pixel size at fixed raster size; the diagonal (M-native vs
L-native) is what `test_ood_scale` currently measures. A second, cheaper block (T1/T3 only, no T4) keeps the radius
irrelevant. Size: 60 real L test tiles (test_id 30, ood_region 30) + 60 synthetic (same seeds regenerated at 256² and
512²; pixel size is nominal for synthetic, so only the raster-size axis is meaningful there).

**Cost estimate.** Per landscape: 256² all tasks ≈ 112 s (measured M) + T4 at radius 128 px on 256² ≈ 4× the M cost
≈ 8 min; 512² ≈ 590 s + T4 at radius 64 px = L-native (already in the estimate). Real: 60 × (M-native 8 min + crop
8 min + 100 m/512² ≈ 12 min + L-native 10 min) ≈ 38 CPU-h; synthetic: 60 × (2 sizes × ≈ 9 min) ≈ 18 CPU-h;
extraction of 60 new 512²/100 m tiles ≈ 10 min. **≈ 60 CPU-h**, 4 GB. Stored as `aux/scale_probe/` with its own index
(`sample_id`, `probe_cell`, `source_tile`, `pixel_m`, `raster`), never mixed into v1.0. Evaluation: models trained on
S+M (100 m) evaluated on each cell separately; the drop from cell (100 m, 256²) to (200 m, 256²) is the resolution
effect, to (100 m, 512²) the size effect.

## 4. Recommendation
Do (b) now — the confound is stated in `docs/task_specification.md` / `docs/dataset_card.md` by this report — and build
the probe (a) after WP1/WP2 on your confirmation of the ≈ 60 CPU-h.

## 5. Probe set built (2026-09-19; owner approval of the ≈ 60 CPU-h estimate)

`aux/scale_probe/`: 60 real L tiles (30 `test_id`, 30 `ood_region`, table large_mammal) × 4 cells + 60 synthetic seeds
(900 000 000 + i, disjoint from every v1.0 stream) × 2 sizes = **360 landscapes, all five configurations (T1R where
patches exist), CHOLMOD, 100 % QC pass, 47 CPU-h** (45 shards of 8, one array). Cells: A = 256² @ 100 m (central crop of
C), B = 256² @ 200 m (central crop of the L tile), C = 512² @ 100 m (new extraction around the L centre, same reader as
v1.0), D = 512² @ 200 m (L-native); T4 window fixed at 12.8 km (radius 128 px / block 11 at 100 m, 64 px / block 5 at
200 m). `probe_index.parquet` (sample_id → probe_cell, source_tile, family, intended split, size, pixel_m) is the key;
the build's own `index.parquet` carries the finalize-time split labels, which for the synthetic seeds follow the seed
hash and are irrelevant here — use `probe_index.parquet`.

Median T4 solve time per landscape by cell: A 133 s, B 181 s, C 714 s, D 768 s (synthetic 256² 164 s, 512² 709 s):
at fixed physical window the 100 m cells are as expensive as the 200 m cells of the same raster size (the window has
4× the pixels but block 11 vs 5 compensates), so the probe's cost axis is raster size.

Evaluation recipe (after the three-seed baselines): a model trained on S + M (100 m) is evaluated with
`scripts/evaluate.py --root aux/scale_probe/probe_L --tier L --split test_id,ood_region` and the per-sample rows grouped
by `probe_cell`; A → C isolates raster-size extrapolation at fixed pixel size, A → B isolates resolution at fixed
raster size, B → D the size axis at 200 m, and D vs (`test_ood_scale` at L) shows how much of the production scale gap
each axis explains. The finalized shards (≈ 2 GB) stay on scratch until the evaluation is done; publishing them under
`aux/scale_probe/` on the Hub is a public push and is left for the owner's call.
