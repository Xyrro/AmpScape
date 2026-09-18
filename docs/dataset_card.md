---
license: cc-by-4.0
pretty_name: AmpScape
task_categories: [image-to-image, other]
tags: [landscape-connectivity, circuitscape, omniscape, surrogate-modeling, neural-operators, scientific-ml, ecology]
size_categories: [100K<n<1M]
configs: []   # filled by scripts/push_to_hub.py from the layout (one config per tier × task group)
---

# AmpScape

> **v1.0 generation in progress — shards are being added; index and card finalised on completion.**
> Started 2026-09-15 on Georgia Tech PACE-ICE with streaming upload (each shard is validated, uploaded and
> checksum-verified before it appears here). Tier order S → M → L → XL → XXL. Until completion, `index/<tier>.parquet`
> and `splits/full/*.parquet` cover the shards uploaded so far and are re-published as tiers grow; the card, the
> Croissant file and the baseline tables are updated at the end. Pipeline tag: `v1.0-pipeline`.

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

## Dataset structure

- `data/<tier>/<task_group>/shard-NNNNN.h5` — HDF5 shards, one group per sample, inputs + one
  configuration each (`T1` = pairwise current/Reff, `T1W` = wall-to-wall, `T1R` = habitat-patch
  regions, `T3` = advanced source/ground, `T4` = Omniscape). Any single tier or task group can be
  downloaded alone. Schema: `docs/schema.md` in the code repository.
- `index/<tier>.parquet` — one row per (sample, configuration): identifiers, family, generator or
  resistance table, tile, K, placement, solver, timings, residuals, QC flags, split, OOD flags,
  subset membership (`subset_mini`, `subset_core`, `subset_full`).
- `splits/<subset>/<split>.parquet` — sample ids; subsets are nested (mini ⊂ core ⊂ full).
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
contrast (10⁶), held-out scale (XL/XXL for models trained ≤ L), and a synthetic→real flag. **Pilot caveat:** the mini's 50 real tiles over-represent the held-out regions
(20 of 50) because the Phase 2 pilot sampled those strata for coverage; this is not a v1.0 property.

## Scale split caveat

Pixel size, raster size and (for T4) the physical window radius co-vary across tiers (only S → M changes the raster
alone), so `test_ood_scale` measures combined scale transfer; a controlled probe set separating the axes is planned
(`docs/addendum_WP5_report.md`).

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
