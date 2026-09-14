# Dev subset (`$AMPSCAPE_SCRATCH/data/dev`) — a true prefix of v1.0

Built 2026-09-14 on ICE. 3 000 S and 500 M landscapes drawn from the v1.0 sampling design with the v1.0 seeds,
all tasks, splits by the v1.0 spatial rule. Because every stream is deterministic and tier-disjoint, the dev
subset is the first 3 000 / 500 landscapes of v1.0 and stays valid as long as the pipeline is frozen
(`ampscape/solve/plan_v1.py`, `scripts/plan_v1.py`, `scripts/build_v1_tiles.py`).

## Streams (per tier)

| family | stream | dev prefix |
|---|---|---|
| synthetic (60 %) | seed = `TIER_SEED_BASE[tier] + i` (S 100 000 000 + i, M 200 000 000 + i, …), landscape = `sample_landscape_v1(seed)` — v1.0 generator mix with the 20 % hard-case stratum (`high_contrast_1e5/1e6`, `rmax_saturated`, `narrow_corridor`, `large_nodata`; `docs/figures/v1_hard_cases.png`), contrast ∈ {10…10⁴} otherwise; split by seed family; `regions` (T1R) on patch-mosaic landscapes (C5) | S 1 800, M 300 |
| real (40 %) | tiles of the v1.0 tile stream (`data/tiles/v1`: stratified round-robin over biome × realm × gHM tercile, seeds 20260906·10 + tier index, full v1.0 lists S 8 000 / M 4 000 / XXL 32 sampled once; S–XL centres must fit one 20° macro-cell — straddlers snapped to the cell's interior box), **prefix-extracted** in list order (`extract_tiles.py --first-accepted`; rejected tiles skipped, never replaced), × 5 tables (generic_hm, large_mammal, amphibian, forest_bird, one seeded `random_lm` per tile); source seed = sha1(tile \| table) | S 240 tiles → 1 200, M 40 tiles → 200 |

Sample ids are UUID5 of (`ampscape-v1.0`, family, key) and therefore identical in v1.0. Extraction: S 242 tiles
visited for 240 accepted (2 rejected), M 42 for 40; 1 400 resistance rasters. Shards: S 30 × 100, M 13 × 40.

## Splits (v1.0 rule, `configs/datasets/v1_0.yaml`, seed 20260906)

| tier | landscapes | configs (QC pass) | train | val | test_id | test_ood (forest_bird, contrast 10⁶) | ood_region | of which real tiles train / val / test_id / test_ood / ood_region |
|---|---|---|---|---|---|---|---|---|
| S | 3 000 | 15 880 (100 %) | 1 839 | 326 | 351 | 184 | 300 | 110 / 37 / 33 / 147 landscapes from 240 tiles (forest_bird demotes every tile's 5th table) |
| M | 500 | 2 685 (99.9 %; 2 `residual_high` at contrast 10⁶) | 359 | 31 | 33 | 37 | 40 | 30 / 1 / 1 / — / 8 tiles |

Configurations per landscape: points (T1/T2), wall-to-wall NS + EW (T1W; undefined on 13 + 17 S and 2 + 3 M
large-NoData landscapes and therefore skipped), advanced (T3), omniscape (T4), regions (T1R on 910 S / 190 M
landscapes: real tiles with ≥ 2 habitat patches and synthetic patch mosaics). CG baselines on every test/OOD
sample. Hard cases (S): narrow_corridor 123, large_nodata 95, high_contrast_1e5 71, rmax_saturated 49,
high_contrast_1e6 39 (= 20.4 % of synthetic). Quicklooks in `data/dev/<tier>/quicklooks`.

### Two findings that need an owner decision (both only change split *labels*, which are recomputed at finalize)

1. **Cell-level biome hold-out over-reaches.** With "held-out biomes are whole cells", mangrove / montane tiles
   touch 23 of the 56 cells holding dev tiles, so 52 % of the real S tiles became `ood_region` and no real tile
   was left for `test_id`. The hold-out is now tile-level by default (`test_ood_region.unit: tile`; `cell` keeps
   the old behaviour): a tile is OOD when its own biome/realm is held out (24 % of dev tiles).
2. **XXL parent regions merge into continents.** With the real v1.0 XXL centres, the 32 footprints (2 048 km,
   ≈ 90 % of land) merge into 13 components covering 72 % of the S tiles; five held-out parents propagate OOD to
   12 of 13 components (1 real S `test_id` tile left). `spatial_block.parent_regions: false` for dev: S–XL tiles
   are assigned by their macro-cell only; XXL stays test-only; the S-inside-XXL overlap is ≤ 0.004 % of an XXL
   tile. Options for v1.0: keep this, place XXL centres only in test/OOD cells, or cap XXL footprint merging.

### Post-freeze note (2026-09-14)

The macro-cell assignment is now frozen for the whole grid (`configs/splits/cell_assignment_v1.json`), which moves
25 S and 73 M dev split labels (labels only; recomputed at finalize), and the tile reader now applies the C2
majority rule to S land cover, so the dev subset's **real** half is not bitwise reproducible from the frozen
pipeline and is regenerated as part of v1.0; the synthetic half is (see the freeze checklist in
`docs/status/latest.md`).

## Cost and storage

| item | S (3 000) | M (500) |
|---|---|---|
| solve arrays | 30 shards × 100, 1 CPU / 6 GB, 20 concurrent | 13 shards × 40 |
| median solve s: points / W2W / advanced / omniscape (b = 1 at S, 3 at M) | 0.19 / 0.09 / 0.08 / 50.5 | 0.82 / 0.40 / 0.38 / 103 |
| mean per landscape | 54.5 s | 112 s |
| peak RSS | 2.7 GB | 2.6 GB |
| shards on disk | 3.05 GB | 1.82 GB |

Total **66 CPU-hours** (solve arrays + prepare + finalize, `sacct`), wall-clock ≈ 4 h for both tiers with
20 concurrent jobs; below the 150 core-hour threshold, so the run was launched without a prior gate report.
Tiles (`data/tiles/v1`): 238 MB. Predictions of the coarsen-×4 baseline: `data/predictions/dev_coarsen4`.
