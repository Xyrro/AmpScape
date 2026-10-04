# 3. The AmpScape dataset and its generation

<!-- Every number below is copied from a repository document and tagged with its source. -->

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

The v1.0 index holds 920,372 configuration rows (920,347 QC-pass) [docs/tables/final_counts.json]; the 902 904 quoted in the post-mortem and changelog at tag time was a stale pre-audit count and was corrected on 2026-10-02 [docs/generation_postmortem.md; CHANGELOG.md].

**Real landscapes.** Real tiles are genuine covariate stacks (ESA WorldCover, Copernicus DEM, GRIP4 roads, HydroRIVERS, gHM) [docs/dataset_card.md]: 13 958 tiles and 69 790 resistance rasters [CHANGELOG.md], with S 8 000, M 4 000, L 1 600, XL 320 and XXL 32 tiles [docs/dataset_plan.md]. Each tile yields 5 landscapes, one per resistance table: four expert-style tables (`generic_hm`, `large_mammal`, `amphibian`, `forest_bird`) and one seeded random table per tile (`random_lm`) [docs/dataset_plan.md]; `forest_bird` (r_max 100 versus 1000 for the others [DECISIONS.md]) is held out. Only class ordering and term structure follow the literature; the numeric values are AmpScape's own and are not species-calibrated ecological truth [docs/dataset_card.md].

**Synthetic landscapes.** Synthetic rasters come from neutral landscape models and random fields (GRF, fractal, random cluster, planar/edge/distance gradients, mosaic) with 20 % of synthetic landscapes in a named hard stratum: contrast 10⁵ and 10⁶, r_max-saturated, narrow corridors and large NoData [docs/dataset_plan.md]. The contrast ladder is {10, …, 10⁶}, with 10⁶ reserved for `test_ood_contrast` [DECISIONS.md]; real tiles reach at most 1e+03 [docs/tables/dataset_statistics.md].

**Task groups.** Every landscape receives `points` (T1: pairwise current maps and effective resistances, K ∈ [2, 8] focal nodes), two wall-to-wall strips (T1W), an `advanced` source/ground configuration (T3) and an Omniscape configuration (T4); landscapes with ≥ 2 eligible habitat patches (≈ 40 % of real tiles, plus synthetic patch mosaics) also get `regions` (T1R) [docs/dataset_plan.md]. Per-pair maps are stored only for K ≤ 4 [DECISIONS.md]. Outputs are raw float32 maps and float64 effective resistances, never normalised or clipped, with solver versions, parameters, timings and residuals per sample [docs/dataset_card.md]. Configurations undefined on a landscape (an all-NoData strip, no habitat patches, a degenerate source/ground draw) are listed with their reason in `skipped_configs` rather than solved [docs/dataset_card.md].

**Layout, subsets, splits.** The Hub layout is `data/<tier>/<task_group>/shard-NNNNN.h5` (one HDF5 group per sample), `index/<tier>.parquet` (one row per sample × configuration), `splits/<subset>/<split>.parquet`, `stats/norm_stats.json` and `croissant.json` [docs/dataset_card.md]; any tier or task group can be downloaded alone [docs/dataset_card.md]. Four nested shard-prefix subsets (mini ⊂ lite ⊂ core ⊂ full), each with an index column, split lists and a Croissant FileSet: `mini` (0.6 GB, the first 3 S shards, 600 landscapes), `lite` (≈ 26 GB: 8 000 S + 2 400 M + 800 L landscapes, added in v1.0.1), `core` (115.5 GB, 3 705 files: 20 000 S + 10 000 M + 5 000 L) and `full` (1 157.4 GB) [docs/dataset_card.md]. Prefix subsets are drawn from the synthetic stream, so real tiles and `ood_region` exist only in `full`; auxiliary evaluation sets live under `aux/` (20.5 GB) [docs/dataset_card.md]. Real tiles are split by spatial macro-cells shared across tiers (equal-width 20° cells) and synthetic landscapes by seed family; XXL is test-only, and `test_ood_scale_strict` (≈ 6 XXL real tiles with zero overlap with any training tile) isolates spatial novelty from resolution transfer [docs/dataset_card.md]. The 25 rows failing QC (24 landscapes) stay in the index with flags and are excluded from the split lists [docs/dataset_card.md].

**Hosting and licences.** The data are hosted as `Xirro/AmpScape` on the Hugging Face Hub under CC BY 4.0 with Croissant 1.0 metadata (RAI fields) validated by `mlcroissant` (0 errors, 0 warnings) [docs/dataset_card.md; DECISIONS.md]; code and solvers (Circuitscape.jl 5.17.1, Omniscape.jl 0.6.2) are MIT [docs/dataset_card.md]. Upstream attributions are reproduced in the card and `LICENSE-DATA`; the one unresolved item is the GRIP4 licence statement (CC0 vs CC BY 4.0 across catalogues), for which only non-reversible distance/class rasters are stored [docs/dataset_card.md].

**Releases.** v1.0 (2026-09-23) is the data revision; v1.0.1 (2026-09-24) added `lite` as metadata only; **v1.0.2 (2026-09-26) is also metadata-only**: the XL amendment C3 share had been applied by macro-cell hash, which synthetic landscapes lack, so all synthetic XL train/val landscapes had landed in test_id (train 228, val 0, test_id 3,118). v1.0.2 restores a per-seed-family share, giving XL train 880, val 131, test_id 2,335, test_ood 254, ood_region 400, and rebuilds the split lists as unions over all tiers (the v1.0/1.0.1 lists held only the last published tier's ids; the per-tier index `split` column was always complete) [CHANGELOG.md; docs/dataset_card.md; docs/tables/final_counts.json]. Data files are identical across the three tags [docs/dataset_card.md].

## 3.2 Generation pipeline

**Reference solver.** All T1/T1W/T1R/T3 solves use Circuitscape `solver = cholmod` (direct, double precision) rather than CG+AMG, because in Circuitscape 5.17.1 the CG tolerance is hard-coded (`rtol = 1e-6`, accepted if the residual is < 1e-4) and not exposed [DECISIONS.md]. Graphs are 8-neighbour with average conductance, the software default, set explicitly and recorded per sample [DECISIONS.md]. The Kirchhoff residual is computed in Julia from full-precision voltages before the float32 cast; the QC threshold is 1e-6 (the double-precision floor), and one CHOLMOD iterative-refinement step on the reduced/collapsed system fires whenever the residual exceeds 1e-8 [DECISIONS.md]. CG+AMG is allowed only as an automatic, flagged memory fallback [docs/dataset_plan.md].

**Omniscape block-size rule.** T4 uses Omniscape 0.6.2 with `solver: cholmod`, `correct_artifacts: true`, `source_threshold: 0.0` and sources from inverse resistance above the 0.5 quantile [configs/solver/omniscape_reference.yaml; docs/t4_fidelity.md]. Since `block_size` is part of the method (targets are block centres, cost ∝ 1/block²), it is fixed by the rule *block = largest odd integer ≤ radius/10* (Table 2) [docs/dataset_plan.md]. The rule came from a 3-sample-per-cell study: against the exact block-1 map, block 3 at S deviated by 4.49 % mean / 7.60 % max relative L2 and block 5 at M by 2.00 % / 2.45 %, while coarsening XL 17→33 changed `cum_current` by 2.47 % / 2.93 % and XXL 33→65 by 9.46 % / 11.85 % (both rejected) [docs/t4_fidelity.md]. The ≈ 1 % target was an extrapolation and proved optimistic: the production M target deviates from the exact map by 3.1 % relative L2 on average (median 2.8 %; 200 synthetic landscapes; top-5 % IoU 0.95, pinch-point recall 0.95), and the full 1 000-sample M reference gives mean 0.029 with 4.7 % of samples above 5 % (11 % of synthetic, 1.4 % of real) [docs/t4_fidelity.md]. At L (block 5, 60 samples) the mean is 0.028 (max 0.058; 2 of 60 above 5 %); block 1 costs 6.7× (M) and 22× (L) the production solve [docs/t4_fidelity.md]. These block-1 references (`aux/t4_bs1_reference/`) are the official T4 evaluation surface at M and L [docs/t4_fidelity.md].

**Table 2. Omniscape geometry per tier** [docs/t4_fidelity.md; configs/solver/omniscape_reference.yaml]; median T4 solve times from [docs/tables/dataset_statistics.md].

| tier | pixel | radius (px / km) | block_size (b/r) | median T4 solve (s) |
|---|---|---|---|---|
| S | 100 m | 16 / 1.6 | 1 (exact) | 52 |
| M | 100 m | 32 / 3.2 | 3 (0.094) | 107 |
| L | 200 m | 64 / 12.8 | 5 (0.078) | 702 |
| XL | 500 m | 128 / 64 | 11 (0.086) | 3087 |
| XXL | 1 km | 256 / 256 | 25 (0.098) | 9821 |

**Compute.** Generation ran on Georgia Tech PACE-ICE (Slurm) from 2026-09-16 to 2026-09-22 (6.6 days; XL 20 h 51, XXL 10 h), followed by a 29 h precision pass [docs/generation_postmortem.md]. Total cost was 16 552 core-hours: generation 14 379 (S 2 061, M 1 692, L 5 713, XL 3 684, XXL 1 228), precision pass 1 249, audits 30, auxiliary sets and probes 893 [docs/generation_postmortem.md]; T4 is ≈ 90 % of solve cost [docs/dataset_plan.md]. Shards were validated, uploaded, sha256-verified and deleted locally in a streaming loop; scratch peaked at 215 GB of a 300 GB quota [docs/generation_postmortem.md].

**Post-run precision pass.** After generation, every T1/T1W/T1R/T3 row that was above 1e-9, unmeasured (T1 rows with K ≥ 5 and T1R rows keep no per-pair voltages [docs/dataset_card.md]), CG+AMG-solved or QC-failed was re-solved pair by pair with CHOLMOD on the reduced system plus up to three refinement steps, and its true residual recorded (`residual_rel`; per-pair values in `solver_stats.resolved_post_run`; `solver_original` where the solver changed) [docs/dataset_card.md; docs/tables/precision_pass.md]. Table 3 summarises: 129,722 rows re-solved, 189 originally `cg+amg`, 3,861 rows left between 1e-9 and 1e-6 (recorded, kept), and 20 rows unable to reach 1e-6 in double precision, all synthetic at contrast ≥ 10⁴, flagged `residual_high` with `qc_pass = false` [docs/tables/precision_pass.md]. Failed T4 rows were re-run whole [CHANGELOG.md].

**Table 3. Precision pass per tier** [docs/tables/precision_pass.md].

| tier | rows re-solved | of which cg+amg → cholmod | residual after p50 / p90 / p99 / max | rows > 1e-9 | rows > 1e-6 (flagged) |
|---|---|---|---|---|---|
| S | 68,008 | 9 | 2.9e-13 / 3.4e-11 / 1.6e-09 / 5.0e-07 | 1,013 | 0 |
| M | 37,639 | 14 | 9.1e-13 / 1.9e-10 / 5.2e-09 / 1.4e-06 | 1,136 | 4 |
| L | 18,691 | 110 | 6.8e-12 / 4.9e-10 / 1.4e-08 / 1.5e-05 | 1,014 | 9 |
| XL | 4,774 | 47 | 6.9e-11 / 1.3e-09 / 4.3e-08 / 6.6e-06 | 551 | 5 |
| XXL | 610 | 9 | 2.7e-10 / 4.3e-09 / 2.0e-07 / 4.0e-05 | 147 | 2 |
| total | 129,722 | 189 | | 3,861 | 20 |

**Quality control.** QC flags (`residual_high`, `nonfinite_output`, `isolated_focal`, `omniscape_edge_artifact`, …) set `qc_pass = false`; `rmax_saturated` excludes from train/val only; `fallback_solver` is informational [DECISIONS.md]. A shard counts as solved only when the solver's completion marker exists, and finalize checks the exact planned sample and configuration set [DECISIONS.md]. Each tier was audited on the Hub against the plan (sha256, sample ids, configurations, index rows) before completion; regeneration on the same CPU model is bitwise reproducible, and across CPU models results differ by ≤ 1.2e-9 relative [docs/dataset_card.md].

**Incidents that affect interpretation.** Eleven operational incidents occurred, none of which left silently corrupted or missing data [docs/dataset_card.md]. Four matter for reading the data: (i) 72 S shards finalized with < 200 samples were re-solved and replaced, and 149 S shards were re-finalized after the scratch disk filled [docs/generation_postmortem.md; docs/dataset_card.md]; (ii) 62 L shards timed out silently and were re-solved [docs/generation_postmortem.md]; (iii) CHOLMOD raised `PosDefException` on high-contrast region-merged `regions` systems (3.5 % of XL regions rows), which ran as CG+AMG fallbacks during generation and were replaced by the precision pass [DECISIONS.md]; (iv) Circuitscape 5.17.1 aborts any solve with relative residual ≥ 1e-4, which killed whole Omniscape maps and T3 solves on contrast-10⁶ 2048² landscapes, so AmpScapeSolve installs replacement methods that refine such solves (bit-identical whenever the check passes) and counts them in `solver_params.rescued_solves` [docs/t4_fidelity.md]. T4 rows therefore carry no single residual; their per-window bound is the enforced ≤ 1e-4 with this rescue [docs/dataset_card.md].

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
