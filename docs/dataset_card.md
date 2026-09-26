---
license: cc-by-4.0
pretty_name: AmpScape
task_categories: [image-to-image, other]
tags: [landscape-connectivity, circuitscape, omniscape, surrogate-modeling, neural-operators, scientific-ml, ecology]
size_categories: [100K<n<1M]
configs: []   # filled by scripts/push_to_hub.py from the layout (one config per tier × task group)
---

# AmpScape

**v1.0 (2026-09-23).** Generated 2026-09-16 → 09-22 on Georgia Tech PACE-ICE with streaming, checksum-verified
upload; every tier passed a full Hub-vs-plan audit; the post-run precision pass (09-22/23) re-solved 129 722 rows so
that every T1/T1W/T1R/T3 row carries its true Kirchhoff residual. Pipeline tag `v1.0-pipeline` (freeze) and release tag
`v1.0` (GitHub and Hub revision). Cost: 16 552 core-hours. Full account: `docs/generation_postmortem.md`.

AmpScape is a benchmark of **circuit-theoretic landscape connectivity** solved with the reference
solvers Circuitscape.jl 5.17.1 and Omniscape.jl 0.6.2, for training and fairly comparing learned
surrogates. Each sample pairs a resistance raster and a source configuration with the exact solver
outputs (current-density maps, voltage maps, effective resistances, omnidirectional connectivity).

**Honest framing.** (1) The *solver is the ground truth*: outputs are stored raw (float32 maps,
float64 effective resistances), never normalised, clipped or post-processed; every sample records
solver versions, parameters, timings and residuals. (2) *Real landscapes, synthesized resistance*:
real tiles are genuine covariate stacks (ESA WorldCover, Copernicus DEM, GRIP4 roads, HydroRIVERS,
gHM), but the resistance surfaces are produced by resistance tables whose class ordering and term
structure follow the literature (Zeller et al. 2012; Cushman et al. 2006; Koen et al. 2014; Spear et
al. 2010; Brennan et al. 2022) while the **numeric values are AmpScape's own** — they are not
species-calibrated and must not be read as ecological truth for any taxon. (3) Synthetic landscapes
come from neutral landscape models and random fields with documented priors. (4) Omniscape is run
with `block_size = largest odd ≤ radius/10`, a deliberate, documented approximation of the
per-pixel (block 1) Omniscape whose fidelity was measured (≈ 2–5 % relative L2 at coarser blocks).

## Versions

- **v1.0** (2026-09-23) data revision. **v1.0.1** (2026-09-24) metadata: nested `lite` subset. **v1.0.2** (2026-09-26) metadata: XL amendment C3 corrected (synthetic XL train/val restored) and split lists rebuilt as cross-tier unions. Data files are identical across the three tags.

## Final counts (v1.0)

| tier | landscapes | configuration rows | synthetic / real | GB on the Hub | rows failing QC |
|---|---|---|---|---|---|
| S | 100,000 | 527,281 | 60,000 / 40,000 | 142.4 | 1 |
| M | 50,000 | 264,128 | 30,000 / 20,000 | 251.7 | 4 |
| L | 20,000 | 105,949 | 12,000 / 8,000 | 380.9 | 11 |
| XL | 4,000 | 21,006 | 2,400 / 1,600 | 281.7 | 7 |
| XXL | 400 | 2,008 | 210 / 190 | 100.7 | 2 |
| **total** | **174,400** | **920,372** | | **1157.4** | 25 |

Subsets (nested shard prefixes per tier; each also a Croissant FileSet, an index column `subset_<name>` and a split-list folder `splits/<name>/`): `mini` (0.6 GB, the first 3 S shards, 600 landscapes), `lite` (≈ 26 GB: 8 000 S + 2 400 M + 800 L landscapes, all tasks — added in 1.0.1 as metadata only), `core` (115.5 GB, 3 705 files: 20 000 S + 10 000 M + 5 000 L landscapes),
`full` (1 157.4 GB). The prefix subsets are drawn from the synthetic stream, so real tiles and the `ood_region` split appear only in `full`. Auxiliary evaluation sets and results under `aux/` (20.5 GB, `aux/README.md`).
Every tier and every task group is a self-contained set of HDF5 shards (`data/<tier>/<group>/shard-XXXXX.h5`, inputs
included), so any tier or task group can be downloaded alone (`snapshot_download(allow_patterns="data/L/T4/*")`).
The 25 rows failing QC after the precision pass (24 landscapes, all synthetic at contrast ≥ 10⁴) stay in the index
with their flags and are excluded from the split lists. Statistics figures: `docs/tables/dataset_statistics.md`.

## Generation incidents (summary; details in `docs/status/generation_log.md` and `docs/generation_postmortem.md`)

Eleven operational incidents occurred during the run, none of which left silently corrupted or missing data: scratch
quota exhaustion (a), a partial-finalize race (b) and a double submission (c) on tier S — repaired and confirmed
replaced shard by shard; duplicate supervisors after a login-node switch (d) and finals validated mid-write (e) —
leases and atomic renames; an undersized L walltime (f) — 62 shards silently timed out, re-solved; out-of-memory
kills on the `regions` CG+AMG fallback at XL/XXL (h); Circuitscape's hard 1e-4 residual check aborting T4/T3 solves
on contrast-10⁶ 2048² landscapes (i) — rescued by refinement and re-solved; corrupt outputs after OOM kills (j); and an
index column that briefly carried a staging file name. Every affected row was re-solved and every tier re-audited.

## Dataset structure

- `data/<tier>/<task_group>/shard-NNNNN.h5` — HDF5 shards, one group per sample, inputs + one
  configuration each (`T1` = pairwise current/Reff, `T1W` = wall-to-wall, `T1R` = habitat-patch
  regions, `T3` = advanced source/ground, `T4` = Omniscape). Any single tier or task group can be
  downloaded alone. Schema: `docs/schema.md` in the code repository.
- `index/<tier>.parquet` — one row per (sample, configuration): identifiers, family, generator or
  resistance table, tile, K, placement, solver, timings, residuals, QC flags, split, OOD flags,
  subset membership (`subset_mini`, `subset_lite`, `subset_core`, `subset_full`).
- `splits/<subset>/<split>.parquet` — sample ids across all tiers; subsets are nested (mini ⊂ lite ⊂ core ⊂ full). (v1.0.2: rebuilt as cross-tier unions — the v1.0/1.0.1 files held only the last published tier's ids; the per-tier `index/<tier>.parquet` `split` column was always complete.)
- `stats/norm_stats.json` — train-only normalisation statistics.
- `croissant.json` — Croissant 1.0 metadata (core + RAI fields).

Tiers: S 128² (100 m), M 256² (100 m), L 512² (200 m), XL 1024² (500 m), XXL 2048² (1 km).
This mini release: tier S only, 250 landscapes (200 synthetic, 50 real), 1 270 solved configurations.

## Splits and leakage

Real tiles are assigned by spatial macro-cells shared across tiers (equal-width 20° cells, one seeded
assignment per cell), so S–XL test regions never overlap S–XL training regions at any resolution;
synthetic landscapes by seed family. **XXL is test-only and its footprints (2 048 km, 32 tiles covering
≈ 90 % of land) unavoidably overlap finer-tier training cells — for XXL, `test_ood_scale` therefore isolates
*resolution* transfer, not spatial novelty; this is disclosed here and in the task specification.** A strict
subset, `test_ood_scale_strict` (≈ 6 XXL real tiles placed entirely inside non-training cells, zero overlap
with any training tile at any tier, verified geometrically), isolates both. Region hold-outs are
tile-level: a tile is `ood_region` when its own biome (Montane Grasslands & Shrublands, Mangroves) or
realm (Australasia) is held out. Other OOD sets: held-out resistance table (`forest_bird`), held-out
contrast (10⁶), held-out scale (XL/XXL for models trained ≤ L), and a synthetic→real flag. **XL train/val (amendment C3, corrected in v1.0.2):** 25 % of the XL landscapes are train/val so that models can also be trained at XL — real tiles by macro-cell, synthetic landscapes by seed family (XL: train 880, val 131, test_id 2,335, test_ood 254, ood_region 400). In v1.0/1.0.1 the seed-family rule was not applied (synthetic XL landscapes had no macro-cell and were all placed in test_id: train 228, val 0); v1.0.2 is a metadata-only correction of the XL index `split` column and the split lists — no data file changed. **Pilot caveat:** the mini's 50 real tiles over-represent the held-out regions
(20 of 50) because the Phase 2 pilot sampled those strata for coverage; this is not a v1.0 property.

## T4 targets: block-centred Omniscape with a measured approximation

Omniscape targets at M–XXL use `block_size = largest odd ≤ radius/10` (block 1, i.e. exact, at S). Against the exact
block-1 map the production M target deviates by 3.1 % relative L2 on average (tail to 25 % on fragmented high-contrast
landscapes; top-5 % IoU 0.95, pinch-point recall 0.95). Against the exact map the production L target (block 5) deviates by 2.8 % on average (60-sample reference, 2 samples above 5 %). Block-1 reference subsets at M (1 000 samples) and L (60)
are published under `aux/t4_bs1_reference/` with per-sample deviations and a > 5 % tail flag; T4 leaderboard metrics at M
and L are reported against these exact targets (`docs/t4_fidelity.md`).

Every auxiliary evaluation set and result the benchmark depends on is on the Hub under `aux/` (dev subset, mini build,
`test_ood_published`, the WP5 scale-probe set, the block-1 reference and block-size builds, dev baseline results):
`docs/aux_layout.md`.

## Scale split caveat

Pixel size, raster size and (for T4) the physical window radius co-vary across tiers (only S → M changes the raster
alone), so `test_ood_scale` measures combined scale transfer; a controlled probe set separating the axes is planned
(`docs/addendum_WP5_report.md`).

## Solver precision: every pairwise/advanced row carries its true residual (post-run precision pass)

After generation, every T1/T1W/T1R/T3 row whose Kirchhoff residual was above 1e-9, unmeasured (T1 `points` rows with
K ≥ 5 and T1R rows keep no per-pair voltages, so production never measured them), solved by the CG+AMG fallback, or
QC-failed was re-solved pair by pair with CHOLMOD on the reduced system plus iterative refinement and its true relative
residual recorded (`residual_rel` = max over pairs; per-pair values and methods in `solver_stats.resolved_post_run`;
`qc_flags` contains `resolved_post_run`; `solver_original` keeps the production solver where it changed). Per-tier
counts and the achieved-residual distribution: `docs/tables/precision_pass.md`. Rows that could not reach 1e-6 in
double precision (a few dozen synthetic landscapes at contrast ≥ 10⁴) are flagged `residual_high` with `qc_pass =
false` and their samples are excluded from the split lists — never silently kept. T4 (Omniscape) rows have no single
linear system; their solver's per-window residual check is enforced by Circuitscape (≤ 1e-4) with the rescue described
in `docs/t4_fidelity.md`.

## Absent configurations are labelled, not missing

Some planned source configurations are undefined on a given landscape — a wall-to-wall strip that is entirely NoData,
a real tile without two habitat patches for the focal-region task, a degenerate source/ground draw. Such samples keep
their other configurations, and the index column `skipped_configs` (and the sample meta) lists each absent
configuration with its task and reason, e.g. `regions (T1R: no eligible habitat patches …)`. Every other planned
configuration is present: the per-tier audit against the plan enforces it before a tier is declared complete.

## Reproducibility

Generation note: during the tier-S run the scratch disk filled and 149 S shards had to be re-finalized from their
intact solver outputs; no solve was lost and every shard was re-validated before upload.

Every sample records the solver versions, parameters, residuals and the pipeline tag/commit. Regenerating a shard from
`v1.0-pipeline` on the same CPU model reproduces every stored array bitwise; across CPU models (PACE-ICE node types)
CHOLMOD/BLAS results differ in the last bits (≤ 1.2e-9 relative on the checked shards), so cross-hardware reproducibility
is stated at that tolerance, not bitwise.

## Metrics caveat

The domain-level metrics (top-q % high-flow IoU, pinch-point recall, corridor Dice) use thresholds
that are **not validated against ecological outcomes**; we report them as comparative scores between
models and make no claim that any level is sufficient for conservation practice.

## Redistribution terms and attributions

AmpScape data are released under **CC BY 4.0**. The covariate channels and the published-resistance
evaluation set are *derived* from the sources below; the sources themselves are not redistributed
except where their licence permits and the derived channel is the source itself (the three published
resistance rasters, re-tiled). Required attributions:

| Source | Licence | Attribution / notice |
|---|---|---|
| ESA WorldCover 10 m 2021 v200 (land cover) | CC BY 4.0 | © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium |
| Copernicus DEM GLO-30 (elevation, slope) | Copernicus WorldDEM-30 licence | "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved". "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30". |
| GRIP4 global roads (distance, class) | stated as CC0 by PBL; catalogued as CC BY 4.0 elsewhere — attributed | Meijer et al. 2018, Environ. Res. Lett. 13:064006; PBL Netherlands Environmental Assessment Agency (GRIP4) |
| HydroRIVERS v1.0 (river distance, order) | CC BY 4.0 (HydroSHEDS licence) | Lehner & Grill 2013, Hydrol. Process. 27:2171–2186; www.hydrosheds.org |
| gHM v1 (human modification) | CC BY 4.0 | Kennedy et al. 2019, Glob. Change Biol. 25:811–826; figshare 10.6084/m9.figshare.7283087 |
| RESOLVE Ecoregions 2017 (stratification only; no raster stored) | CC BY 4.0 | Dinerstein et al. 2017, BioScience 67:534–545 |
| Eurac Alps landscape permeability (`test_ood_published`) | CC BY 4.0 | Marsoner, Simion, Giombini, Egarter Vigl (Eurac Research) 2022, Zenodo 10.5281/zenodo.6602481 |
| Northern raccoon resistance, Europe (`test_ood_published`) | CC BY 4.0 | figshare 10.6084/m9.figshare.27311484.v1 |
| Hawaiian gallinule resistance layers (`test_ood_published`) | CC0 1.0 | Dryad 10.5061/dryad.p90b87p; paper 10.1002/ece3.4296 |

Not used and not redistributed: WDPA (restrictive terms), OpenStreetMap (ODbL). Synthetic landscapes
are generated by AmpScape code (MIT). Solver outputs are produced by Circuitscape.jl 5.17.1 and
Omniscape.jl 0.6.2 (MIT). The one unresolved point is the exact GRIP4 licence statement (CC0 vs
CC BY 4.0 across catalogues); AmpScape attributes it and stores only non-reversible distance/class
rasters. See `docs/licenses.md` in the code repository for the full verification log.

## Collection process, preprocessing, uses, limitations, ethics, maintenance

To be completed for the full release from `docs/dataset_plan.md`, `docs/licenses.md` (upstream
attributions and the Copernicus WorldDEM-30 notices, which are reproduced verbatim in `LICENSE-DATA`)
and the generation statistics. Protected-area (WDPA) data are **not** used. Locations of real tiles
are public land-cover/terrain products at ≥ 100 m; no personal data.

## Citation

See `CITATION.cff`. Code: https://github.com/Xyrro/AmpScape (MIT). Data: CC BY 4.0 with upstream
attributions.
