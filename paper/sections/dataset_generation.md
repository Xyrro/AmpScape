# 3. The AmpScape dataset and its generation

<!-- Every number below is copied from a repository document and tagged with its source. The generation record (compute, incidents, per-tier precision-pass statistics, fidelity study) is kept in paper/appendix_notes.md for the appendix. -->

## 3.1 Dataset description

**Tiers and landscapes.** AmpScape spans five resolution tiers, S 128² (100 m), M 256² (100 m), L 512² (200 m), XL 1024² (500 m) and XXL 2048² (1 km) [docs/dataset_card.md], totalling 174,400 landscapes [docs/tables/final_counts.json] in a fixed 60 % synthetic / 40 % real share at every tier [docs/dataset_plan.md] (Table 1). A *landscape* is one resistance raster; each of its source configurations is a separate *configuration row*.

**Table 1. Final counts per tier (v1.0)** [docs/tables/final_counts.json; docs/dataset_card.md].

| tier | landscapes | configuration rows | synthetic / real | shards (files) | GB on the Hub | rows failing QC |
|---|---|---|---|---|---|---|
| S | 100,000 | 527,281 | 60,000 / 40,000 | 1000 | 142.4 | 1 |
| M | 50,000 | 264,128 | 30,000 / 20,000 | 1000 | 251.7 | 4 |
| L | 20,000 | 105,949 | 12,000 / 8,000 | 2000 | 380.9 | 11 |
| XL | 4,000 | 21,006 | 2,400 / 1,600 | 1333 | 281.7 | 7 |
| XXL | 400 | 2,008 | 210 / 190 | 755 | 100.7 | 2 |
| total | 174,400 | 920,372 | | | 1157.4 | 25 |

The v1.0 index holds 920,372 configuration rows (920,347 QC-pass) [docs/tables/final_counts.json].

**Real landscapes.** Real tiles are genuine covariate stacks (ESA WorldCover, Copernicus DEM, GRIP4 roads, HydroRIVERS, gHM) [docs/dataset_card.md]: 13 958 tiles and 69 790 resistance rasters [CHANGELOG.md], with S 8 000, M 4 000, L 1 600, XL 320 and XXL 32 tiles [docs/dataset_plan.md]. Each tile yields 5 landscapes, one per resistance table: four expert-style tables (`generic_hm`, `large_mammal`, `amphibian`, `forest_bird`) and one seeded random table per tile (`random_lm`) [docs/dataset_plan.md]; `forest_bird` (r_max 100 versus 1000 for the others [DECISIONS.md]) is held out. Only class ordering and term structure follow the literature; the numeric values are AmpScape's own and are not species-calibrated ecological truth [docs/dataset_card.md].

**Synthetic landscapes.** Synthetic rasters come from neutral landscape models and random fields (GRF, fractal, random cluster, planar/edge/distance gradients, mosaic) with 20 % of synthetic landscapes in a named hard stratum: contrast 10⁵ and 10⁶, r_max-saturated, narrow corridors and large NoData [docs/dataset_plan.md]. The contrast ladder is {10, …, 10⁶}, with 10⁶ reserved for `test_ood_contrast` [DECISIONS.md]; real tiles reach at most 1e+03 [docs/tables/dataset_statistics.md].

**Task groups.** Every landscape receives `points` (T1: pairwise current maps and effective resistances, K ∈ [2, 8] focal nodes), two wall-to-wall strips (T1W), an `advanced` source/ground configuration (T3) and an Omniscape configuration (T4); landscapes with ≥ 2 eligible habitat patches (≈ 40 % of real tiles, plus synthetic patch mosaics) also get `regions` (T1R) [docs/dataset_plan.md]. Per-pair maps are stored only for K ≤ 4 [DECISIONS.md]. Outputs are raw float32 maps and float64 effective resistances, never normalised or clipped, with solver versions, parameters, timings and residuals per sample [docs/dataset_card.md]. Configurations undefined on a landscape (an all-NoData strip, no habitat patches, a degenerate source/ground draw) are listed with their reason in `skipped_configs` rather than solved [docs/dataset_card.md].

**Layout, subsets, splits.** The Hub layout is `data/<tier>/<task_group>/shard-NNNNN.h5` (one HDF5 group per sample), `index/<tier>.parquet` (one row per sample × configuration), `splits/<subset>/<split>.parquet`, `stats/norm_stats.json` and `croissant.json` [docs/dataset_card.md]; any tier or task group can be downloaded alone [docs/dataset_card.md]. Four nested shard-prefix subsets (mini ⊂ lite ⊂ core ⊂ full), each with an index column, split lists and a Croissant FileSet: `mini` (0.6 GB, the first 3 S shards, 600 landscapes), `lite` (≈ 26 GB: 8 000 S + 2 400 M + 800 L landscapes), `core` (115.5 GB, 3 705 files: 20 000 S + 10 000 M + 5 000 L) and `full` (1 157.4 GB) [docs/dataset_card.md]. Prefix subsets are drawn from the synthetic stream, so real tiles and `ood_region` exist only in `full`; auxiliary evaluation sets live under `aux/` (20.5 GB) [docs/dataset_card.md]. Real tiles are split by spatial macro-cells shared across tiers and synthetic landscapes by seed family; XXL is test-only (§4) [docs/dataset_card.md]. The 25 rows failing QC (24 landscapes) stay in the index with flags and are excluded from the split lists [docs/dataset_card.md].

**Hosting and licences.** The data are hosted as `Xirro/AmpScape` on the Hugging Face Hub under CC BY 4.0 with Croissant 1.0 metadata (RAI fields) validated by `mlcroissant` (0 errors, 0 warnings) [docs/dataset_card.md; DECISIONS.md]; code and solvers (Circuitscape.jl 5.17.1, Omniscape.jl 0.6.2) are MIT [docs/dataset_card.md]. Upstream attributions are reproduced in the card and `LICENSE-DATA`; the one unresolved item is the GRIP4 licence statement (CC0 vs CC BY 4.0 across catalogues), for which only non-reversible distance/class rasters are stored [docs/dataset_card.md].

**Release.** The current release is v1.0.2 (2026-09-26): v1.0 (2026-09-23) is the data revision, and v1.0.1 and v1.0.2 are metadata-only tags (the `lite` subset; the XL split assignment of §4) whose data files are identical to v1.0 [CHANGELOG.md; docs/dataset_card.md].

## 3.2 Generation and reproducibility

All T1/T1W/T1R/T3 targets are computed with Circuitscape.jl 5.17.1 using the direct CHOLMOD solver in double precision (`solver = cholmod`) on 8-neighbour graphs with average conductance, the software default, set explicitly and recorded per sample [DECISIONS.md]. The Kirchhoff residual is computed in Julia from full-precision voltages before the float32 cast; one CHOLMOD iterative-refinement step on the reduced/collapsed system fires whenever it exceeds 1e-8, and the QC threshold is 1e-6, the double-precision floor [DECISIONS.md]. A post-run precision pass re-solved every row whose residual was above 1e-9, unmeasured, CG+AMG-solved or QC-failed — 129,722 rows, 189 of them originally `cg+amg` — pair by pair with CHOLMOD on the reduced system plus up to three refinement steps, recording the true residual per row (`residual_rel`; `solver_original` where the solver changed): 3,861 rows remain between 1e-9 and 1e-6 (recorded, kept) and 20 rows, all synthetic at contrast ≥ 10⁴, cannot reach 1e-6 in double precision and are flagged `residual_high` with `qc_pass = false` [docs/dataset_card.md; docs/tables/precision_pass.md]. T4 targets are computed with Omniscape.jl 0.6.2 (`solver: cholmod`, `correct_artifacts: true`, `source_threshold: 0.0`, sources from inverse resistance above the 0.5 quantile) [configs/solver/omniscape_reference.yaml; docs/t4_fidelity.md]. Because `block_size` is part of the method (targets are block centres, cost ∝ 1/block²), it is fixed per tier as the largest odd integer ≤ radius/10 (Table 2) [docs/dataset_plan.md], and the block-centred approximation is measured against exact block-1 maps: the production M target (block 3) deviates from the exact map by mean 0.029 relative L2 on the 1 000-sample reference with 4.7 % of samples above 5 %, and the L target (block 5, 60 samples) by mean 0.028 (max 0.058; 2 of 60 above 5 %); block 1 costs 6.7× (M) and 22× (L) the production solve, and these block-1 references (`aux/t4_bs1_reference/`) are the official T4 evaluation surface at M and L [docs/t4_fidelity.md]. T4 rows carry no single residual; each window solve is bounded by Circuitscape's enforced relative residual ≤ 1e-4 [docs/dataset_card.md]. QC flags (`residual_high`, `nonfinite_output`, `isolated_focal`, `omniscape_edge_artifact`, …) set `qc_pass = false`; `rmax_saturated` excludes from train/val only; `fallback_solver` is informational [DECISIONS.md]. Each tier was audited on the Hub against the plan (sha256, sample ids, configurations, index rows); regeneration on the same CPU model is bitwise reproducible, and across CPU models results differ by ≤ 1.2e-9 relative [docs/dataset_card.md].

**Table 2. Omniscape geometry per tier** [docs/t4_fidelity.md; configs/solver/omniscape_reference.yaml]; median T4 solve times from [docs/tables/dataset_statistics.md].

| tier | pixel | radius (px / km) | block_size (b/r) | median T4 solve (s) |
|---|---|---|---|---|
| S | 100 m | 16 / 1.6 | 1 (exact) | 52 |
| M | 100 m | 32 / 3.2 | 3 (0.094) | 107 |
| L | 200 m | 64 / 12.8 | 5 (0.078) | 702 |
| XL | 500 m | 128 / 64 | 11 (0.086) | 3087 |
| XXL | 1 km | 256 / 256 | 25 (0.098) | 9821 |

The complete generation record — compute, per-tier precision-pass statistics, the fidelity study behind the block rule and the operational incidents that affect interpretation — is given in the post-mortem and in the dataset card (datasheet) [docs/generation_postmortem.md; docs/dataset_card.md].

### Sources used
- docs/dataset_card.md
- docs/tables/final_counts.json
- docs/tables/dataset_statistics.md
- docs/tables/precision_pass.md
- docs/generation_postmortem.md
- docs/t4_fidelity.md
- docs/dataset_plan.md
- configs/solver/omniscape_reference.yaml
- DECISIONS.md
- CHANGELOG.md
