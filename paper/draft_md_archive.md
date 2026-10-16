<!-- ARCHIVED 2026-10-16: this Markdown draft was superseded by the LaTeX submission in paper/neurips/ (main.tex, built to main.pdf). It is kept for the record; its numbers were current at commit 24a5991 and are not regenerated. -->

# AmpScape: a benchmark for learned surrogates of circuit-theoretic landscape connectivity

<!-- Draft assembled 2026-10-15 from paper/sections/*, the regenerated tables under paper/tables/ and docs/tables/, and the
appendices. Every number in the main text and the appendix is copied from the repository file named in the square-bracket
tag that follows it; `scripts/verify/check_draft_numbers.py` verifies every numeric token against those files. Reference
numbers [n] are those of paper/sections/related_work.md (list at the end of the main text). Target: NeurIPS Datasets &
Benchmarks, 9 pages of main text; the appendix holds the full tables, the fidelity and precision-pass records, the
licence block and the derivation. -->

**Abstract.** Circuit theory models animal movement as current flow across a resistance raster. The omnidirectional variant (Omniscape) and the many-query uses of the pairwise solver (sensitivity analysis, scenario comparison, resistance-surface optimisation) make the solver the bottleneck of connectivity studies. AmpScape pairs 174,400 resistance landscapes — 60 % synthetic, 40 % real tiles built from open global layers — with exact Circuitscape.jl / Omniscape.jl outputs on five resolution tiers from 128² to 2048² pixels, 920,372 configuration rows and 1,157.4 GB [docs/dataset_card.md]. Every row carries its solver residual; the block-centred Omniscape approximation is measured against exact references rather than assumed. The benchmark defines pairwise, advanced-mode and omnidirectional tasks with pixel, ranking, non-source and physics metrics, spatial and distributional out-of-distribution splits, and a zero-shot scale-transfer split. Official baselines (U-Net, FNO, ViT, GNN, MgNO; three seeds; configurations tuned per tier and selected per task on validation loss alone) show a speed–accuracy–robustness trade-off: the U-Net reaches rel-L2 0.041 / 0.042 / 0.081 on the omnidirectional task at S / M / L at 10⁴–10⁵× the solver's speed [paper/tables/baselines_sml.md], pairwise current is much harder (best rel-L2 0.114 / 0.187 / 0.299 [paper/tables/baselines_sml.md]), zero-shot transfer to larger tiers fails on magnitude by a factor the window geometry predicts, and only rankings survive. A many-query demonstration reproduces a 160-map screening study's conclusions at 11,077× lower cost [docs/wp7_demo.md]. Data, code, harness, leaderboard and Croissant metadata are released under CC BY 4.0 and MIT.

## 1 Introduction

Circuit-theoretic connectivity [1, 2] turns a resistance raster into a resistor network and reads movement potential from the current that flows between habitat patches. Two things make its solvers expensive. The omnidirectional variant, Omniscape [6, 7], solves one circuit per source block inside a moving window around every pixel: documented production runs took 140 h on 55 CPUs per species [18] or 196 h for one regional map [21] [paper/sections/related_work.md], and in AmpScape's own reference generation the median omnidirectional solve rises from 52 s per landscape at 128² to 9,821 s at 2048² [docs/tables/dataset_statistics.md]. A single pairwise solve is cheap — a median of 0 to 63 s per landscape across our tiers [docs/tables/dataset_statistics.md] — but resistance surfaces are uncertain inputs [14], so the solver is called repeatedly inside optimisation loops, scenario sweeps and uncertainty analyses [15, 16, 17]: the *many-query* pattern, not the single solve, is the cost. Learned surrogates for elliptic problems are an established line of work (Section 2), but the public benchmarks have coefficient contrasts of 6 rather than 10⁶, a uniform forcing rather than per-sample point sources and grounds, grids far below 2048², and no out-of-distribution structure tied to geography.

**Contributions.** (i) *The dataset*: 174,400 landscapes on five tiers (S 128², 100 m; M 256², 100 m; L 512², 200 m; XL 1024², 500 m; XXL 2048², 1 km), 60 % synthetic with a hard-case stratum and 40 % real tiles from open global layers, each solved under five resistance tables [docs/dataset_card.md]. (ii) *A reference-solver protocol with measured fidelity*: every pairwise and advanced-mode row carries its true Kirchhoff residual, and the block-centred Omniscape targets are measured against exact block-1 references (mean rel-L2 0.029 at M, 0.028 at L) that become the official evaluation surface at those tiers [docs/t4_fidelity.md]. (iii) *A harness* with pixel, ranking, non-source-pixel, physics and efficiency metrics, a framework-agnostic prediction format and a leaderboard. (iv) *Baselines*: five model families, three seeds, configurations tuned per tier and selected per task on validation loss alone, with scale-transfer, out-of-distribution, data-scaling and solver-acceleration studies. (v) *A many-query demonstration* on a 160-map screening study [docs/wp7_demo.md].

The headline is a trade-off, not a replacement. On the omnidirectional task the best surrogate reaches rel-L2 0.041, 0.042 and 0.081 at S, M and L at median speed-ups of 167,020×, 32,789× and 111,998× over the production solver [paper/tables/baselines_sml.md]; against the exact map it sits at 0.051 (M) and 0.090 (L) where the production block solver sits at 0.029 and 0.032 [paper/tables/t4_pareto_M.md; paper/tables/t4_pareto_L.md]. Pairwise current is harder for every model (best rel-L2 0.114 / 0.187 / 0.299 [paper/tables/baselines_sml.md]), zero-shot transfer to XL and XXL fails on magnitude by exactly the factor the larger window injects (rel-L2 ≈ 0.50 and ≈ 0.75, Appendix A), and ranking metrics survive where magnitudes do not.

## 2 Related work

**Circuit theory as ground truth.** McRae's isolation by resistance [1] and its connectivity tool [2] solve Kirchhoff's equations on the raster graph; Circuitscape.jl uses CG+AMG and CHOLMOD solvers [4, 5], Omniscape applies it in a circular moving window around every source pixel [6, 7], gflow parallelises pairwise solves [8], ConScape covers the randomised-shortest-path continuum [9, 10], and current density has been computed at global extent [11]. Each solve is a sparse symmetric positive-definite system with one unknown per pixel; nearly-linear-time solvers [12] and effective-resistance sketches [13] exist in theory, but production workloads use CG+AMG or CHOLMOD. Because resistance surfaces are uncertain [14], solvers are called repeatedly: ResistanceGA runs Circuitscape inside a genetic algorithm [15], model-based inference embeds the resistance distance in a Gaussian Markov random field [16], and cost-uncertainty studies re-solve under perturbed tables [17].

**Documented Omniscape cost and the block-size mitigation.** Dertien and Baldwin [18] needed "55 CPUs and 350 GB RAM (approximately 140 h)" per species for Omniscape, "a level of high-throughput computing capacity likely not available to most conservation practitioners"; a regional 30 m run in British Columbia is logged at 196 h [21]; an Omniscape.jl issue reports 1.4 M pixels per window solve [20] [paper/sections/related_work.md]. The standard mitigation is `block_size`, which the documentation says reduces compute time with "only negligable [sic] differences" [22] and which Belote et al. [23] set to 10 % of the window radius [paper/sections/related_work.md]. AmpScape quantifies this approximation against exact block-1 solutions (Section 4.2) and reports learned models and block-size rows on one cost axis.

**Where to intervene, and ML for connectivity.** Barrier Mapper [24], Pinchpoint Mapper [25], Zonation [26, 27], Marxan Connect [28] and GECOT [29] prioritise interventions; Van Moorter et al. [30] derive analytical sensitivities of landscape functionality across least-cost, circuit-theoretic and randomised-shortest-path models, and JAXScape provides differentiable, GPU-accelerated distances [31]. Exact solvers are therefore differentiable and accelerator-capable; the case for a surrogate is amortised cost across many queries. Machine learning has been used *around* connectivity — reinforcement learning for graph-based indices [32], CNN dispersal inference from genotypes [33] — but our searches (protocol in the supplement) found no learned surrogate of Circuitscape or Omniscape and no public benchmark of solver-computed circuit-theory outputs.

**Learned surrogates for elliptic problems, and benchmark design.** Circuitscape's system discretises ∇·(σ∇φ) = f with point sources and grounds, so the closest lineage is operator learning on Darcy flow: FNO [34], PDEBench [35], the neuraloperator library [36], U-Net baselines [37, 38] and graph networks on the discretisation graph [39, 40]; multiscale and high-contrast coefficients are the recognised hard case — HANO [41], MgNO [42], dilated-convolution [43] and LOD-based [44] operators, ConDiff [45] — and learned preconditioners accelerate rather than replace the solver [46, 47]. The delta is in the data: the standard Darcy-rough coefficient has "a contrast of 6" with "f(x) ≡ 1" [43] [paper/sections/related_work.md], whereas AmpScape has real coefficient fields, contrast up to 10⁶, per-sample singular sources, grids to 2048², systematic OOD splits and decision-relevant metrics. The release follows PGLearn [48] and OPFData / OPF-Learn [49, 50] — reference solver, instance families, complete solutions, Hub hosting — with the asymmetry stated that AC-OPF is non-convex and re-solved at operational cadence whereas our forward problem is linear and costly only through repetition; PDEBench, The Well and AirfRANS supply the pattern of uniform HDF5 shards, dataset cards and explicit OOD tasks [35, 51, 52], and Datasheets for Datasets and the NeurIPS call set the documentation and Croissant requirements [53, 54].

## 3 Problem and tasks

**Setting.** Each sample pairs a resistance raster R (H×W, R ≥ 1, NoData masked) and a source configuration with the exact output of Circuitscape.jl 5.17.1 or Omniscape.jl 0.6.2 [docs/task_specification.md]. The raster becomes a graph with one node per valid pixel and 8-neighbour edges of Circuitscape's default average conductance g_ij = (g_i + g_j)/2, g = 1/R; for an injection vector b the voltages solve L v = b and the stored current map is Circuitscape's node current density [docs/task_specification.md]. The reference solver is CHOLMOD in double precision; every sample records its achieved residual ‖L v − b‖₂/‖b‖₂; outputs are stored raw [docs/task_specification.md].

**Tasks.** *T1 — pairwise current mapping*: Circuitscape `pairwise` mode with K ∈ [2, 8] single-pixel focal nodes and all K(K−1)/2 pairs (node i grounded, 1 A injected at node j); target `cum_current` (H×W), the per-pair maps (P×H×W) for K ≤ 4, and the K×K effective-resistance matrix as the T2 target [docs/task_specification.md]. *T1W — wall-to-wall*: K = 2 focal regions formed by opposite edge strips in two orientations, strip pixels excluded from all metrics; *T1R — focal regions*: habitat patches as short-circuited regions [docs/task_specification.md; configs/tasks/sources_default.yaml]. *T3 — advanced mode*: source raster values are injected currents and grounds are ideal (one edge, all edges or 1–3 patches); targets `current` and `voltage` [docs/task_specification.md]. *T4 — omnidirectional connectivity*: Omniscape grounds in turn every pixel with source strength above `source_threshold` (= 0) on a grid of stride `block_size`, injects current ∝ S from all sources within `radius` px and sums the window maps; sources are inverse-resistance suitability above the 0.5 quantile rescaled to max 1 [docs/t4_fidelity.md]. Production radius / block per tier: S 16 / 1, M 32 / 3, L 64 / 5, XL 128 / 11, XXL 256 / 25 px (block = largest odd integer ≤ radius/10), `correct_artifacts = true` [docs/t4_fidelity.md]. Block 1 is exact; larger blocks give the block-centred map, a documented approximation (Section 4.2).

**Inputs and targets for learning.** Baselines receive channel 0 = standardised log-resistance (train-only statistics, 0 at NoData), channel 1 = NoData mask, then the task's source channels (T1: focal mask; T3: scaled source strength plus ground mask; T4: Omniscape source strength), and predict log10(C + ε·max C) under a masked MSE that excludes NoData and the T1W strips [ampscape/models/common.py]; ε = 1e-6 [ampscape/metrics/transforms.py]. The ε-shifted log is scale-invariant and bounds the dynamic range to 6 decades below the map maximum [ampscape/metrics/transforms.py].

## 4 Dataset construction

### 4.1 Landscapes, tasks, layout

**Tiers and counts.** Table 1 gives the final counts. A landscape is one resistance raster; each of its source configurations is a configuration row. The synthetic / real share is 60 / 40 at every tier [docs/dataset_card.md].

**Table 1. Final counts per tier (v1.0)** [docs/dataset_card.md].

| tier | landscapes | configuration rows | synthetic / real | GB on the Hub | rows failing QC |
|---|---|---|---|---|---|
| S | 100,000 | 527,281 | 60,000 / 40,000 | 142.4 | 1 |
| M | 50,000 | 264,128 | 30,000 / 20,000 | 251.7 | 4 |
| L | 20,000 | 105,949 | 12,000 / 8,000 | 380.9 | 11 |
| XL | 4,000 | 21,006 | 2,400 / 1,600 | 281.7 | 7 |
| XXL | 400 | 2,008 | 210 / 190 | 100.7 | 2 |
| total | 174,400 | 920,372 | | 1157.4 | 25 |

**Real landscapes** are covariate stacks from ESA WorldCover, Copernicus DEM, GRIP4 roads, HydroRIVERS and gHM: 13 958 tiles and 69 790 resistance rasters [CHANGELOG.md]. Each tile yields five landscapes, one per resistance table — four expert-style tables and one seeded random table per tile; the `forest_bird` table (r_max 100 versus 1000 for the others) is held out [docs/dataset_plan.md; DECISIONS.md]. Only class ordering and term structure follow the literature; the numeric values are AmpScape's own, not species-calibrated truth [docs/dataset_card.md]. **Synthetic landscapes** come from neutral landscape models and random fields, with 20 % in a hard stratum (contrast 10⁵ and 10⁶, r_max-saturated, narrow corridors, large NoData); the contrast ladder is {10, …, 10⁶}, with 10⁶ reserved for `test_ood_contrast` [docs/dataset_plan.md; DECISIONS.md].

**Task groups and layout.** Every landscape receives `points` (T1), two wall-to-wall strips (T1W), an `advanced` configuration (T3) and an Omniscape configuration (T4); landscapes with ≥ 2 eligible habitat patches also get `regions` (T1R), and undefined configurations are listed with their reason in `skipped_configs` rather than solved [docs/dataset_plan.md; docs/dataset_card.md]. The Hub layout is `data/<tier>/<task_group>/shard-NNNNN.h5`, `index/<tier>.parquet` (one row per sample × configuration), split lists, normalisation statistics and `croissant.json`; any tier or task group can be downloaded alone, and four nested shard-prefix subsets — `mini` (0.6 GB, 600 S landscapes), `lite` (≈ 26 GB: 8 000 S + 2 400 M + 800 L), `core` (115.5 GB: 20 000 S + 10 000 M + 5 000 L) and `full` (1 157.4 GB) — each have an index column, split lists and a Croissant FileSet [docs/dataset_card.md]. The data are hosted as `Xirro/AmpScape` under CC BY 4.0 with Croissant 1.0 metadata (RAI fields, validated with 0 errors and 0 warnings); v1.0 is the data revision and v1.0.1 / v1.0.2 are metadata-only tags [docs/dataset_card.md; DECISIONS.md].

### 4.2 Reference solver, precision pass and Omniscape fidelity

All T1/T1W/T1R/T3 targets are computed with the direct CHOLMOD solver in double precision; the Kirchhoff residual is computed from full-precision voltages before the float32 cast, one iterative-refinement step fires above 1e-8 and the QC threshold is 1e-6 [DECISIONS.md]. A post-run precision pass re-solved every row whose residual was above 1e-9, unmeasured, CG+AMG-solved or QC-failed — 129,722 rows — with CHOLMOD on the reduced system plus up to three refinement steps, recording the true residual per row: 3,861 rows remain between 1e-9 and 1e-6 (kept) and 20 rows, all synthetic at contrast ≥ 10⁴, are flagged `residual_high` with `qc_pass = false` (Appendix D) [docs/tables/precision_pass.md]. The 25 rows failing QC (24 landscapes) stay in the index with their flags and are excluded from the split lists [docs/dataset_card.md].

T4 targets use Omniscape.jl 0.6.2 (`solver: cholmod`, `correct_artifacts: true`) [configs/solver/omniscape_reference.yaml]. Because `block_size` is part of the method, it is fixed per tier by the rule above, and the block-centred approximation is *measured*: on the 1 000-sample M reference the production block-3 target deviates from the exact block-1 map by mean rel-L2 0.029 with 4.7 % of samples above 5 %; the L target (block 5, 60 samples) by mean 0.028 (max 0.058; 2 of 60 above 5 %); block 1 costs 6.7× (M) and 22× (L) the production solve [docs/t4_fidelity.md]. These block-1 references (`aux/t4_bs1_reference/`) are the official T4 evaluation surface at M and L [docs/t4_fidelity.md]. Median T4 solve times are 52 / 107 / 702 / 3087 / 9821 s per landscape at S / M / L / XL / XXL, against 0 / 1 / 4 / 17 / 63 s for a pairwise solve [docs/tables/dataset_statistics.md].

Generation took 16 552 core-hours including the precision pass [docs/generation_postmortem.md]; each tier was audited on the Hub against the plan (sha256, sample ids, configurations, index rows), regeneration on the same CPU model is bitwise reproducible, and across CPU models results differ by ≤ 1.2e-9 relative [docs/dataset_card.md].

## 5 Splits and out-of-distribution design

Splits are assigned by the *unit of leakage* — the tile for real landscapes, the seed family for synthetic ones — at base fractions train 0.8 / val 0.1 / test_id 0.1, with hold-outs applied before the draw [docs/dataset_plan.md]. Because an S tile physically sits inside XL/XXL footprints, the globe is partitioned once into 104 equal-width macro-cells, each receiving one seeded assignment applied at every tier (70 land cells: 56 train / 7 val / 7 test_id, stratified by realm); no train/val tile box intersects any test tile box at any tier, and XXL stays test-only [docs/dataset_plan.md; DECISIONS.md]. Seed ranges are tier-disjoint [configs/datasets/v1_0.yaml], and 25 % of XL landscapes are train/val so that models can also be trained at XL [CHANGELOG.md].

**OOD sets** (one boolean index column each) [configs/datasets/v1_0.yaml]: `test_ood_region` — real tiles whose biome is Montane Grasslands & Shrublands or Mangroves or whose realm is Australasia; `test_ood_table` — all landscapes built with the `forest_bird` table; `test_ood_contrast` — synthetic contrast 10⁶; `test_ood_scale` — XL/XXL evaluated by models trained at ≤ L; `test_ood_scale_strict` — 6 XXL real tiles with zero overlap with any training tile at any tier [docs/dataset_card.md]; `test_ood_synth2real` — a loader flag restricting training to synthetic landscapes; `test_ood_published` — 45 S tiles and 1 XXL tile with published resistance surfaces (Eurac Alps, Hawaiian gallinule, Northern raccoon) under `aux/` [docs/dataset_card.md]. Held-out-table and held-out-contrast landscapes that the base draw would place in train/val are demoted to `test_ood` [ampscape/splits/assign.py]. Pixel size, raster size and the T4 window radius co-vary across tiers, so `test_ood_scale` measures combined scale transfer; XXL footprints overlap finer-tier training cells, so at XXL the set isolates resolution transfer, not spatial novelty, and only the strict subset isolates both [docs/dataset_card.md].

**Table 2. Landscapes per split and tier** (index counts before QC exclusion; XL from the v1.0.2 correction) [docs/tables/final_counts.json; CHANGELOG.md].

| tier | train | val | test_id | test_ood | ood_region |
|---|---|---|---|---|---|
| S | 63,303 | 10,917 | 9,850 | 6,460 | 9,470 |
| M | 31,496 | 5,651 | 4,823 | 3,225 | 4,805 |
| L | 12,613 | 2,235 | 1,928 | 1,279 | 1,945 |
| XL | 880 | 131 | 2,335 | 254 | 400 |
| XXL | 0 | 0 | 275 | 25 | 100 |

## 6 Metrics and evaluation protocol

Maps are compared in log10_eps(C) = log10(C + ε·max C) [ampscape/metrics/transforms.py]. **Pixel**: MAE in log10-ε space (primary for current maps), MSE and relative L2 on raw values, SSIM/PSNR secondary; NoData and T1W strip pixels masked [ampscape/metrics/pixel.py]. **Domain** [ampscape/metrics/domain.py]: top-q % IoU between the q % highest-current valid pixels of prediction and target (q ∈ {1, 5, 10}); corridor Dice above the 10 % quantile; pinch-point recall, where target pinch points are local maxima (7×7 window) within the target's top 5 % and a hit is a predicted local maximum within 3 px; Spearman rank correlation of valid pixels. These thresholds are conventions, not validated ecological criteria [docs/dataset_card.md]. **Non-source pixels**: because currents are singular at injection pixels, rel-L2, MAE and top-q IoU are also computed outside source, focal and ground pixels plus a 2-px halo [ampscape/metrics/nonsource.py]. **Physics**: the Kirchhoff residual when a voltage is predicted, focal-current error, non-negativity and a throughput error [ampscape/metrics/physics.py]. **Efficiency**: speed-up = recorded solver wall time / inference time, with batch-1 inference at XL/XXL [ampscape/metrics/efficiency.py; scripts/transfer_eval.py]. **Acceleration**: AMG-preconditioned CG iterations and wall time to the reference tolerance when warm-started from a predicted voltage versus from zero, with the same preconditioner and matrix as the stored baselines [ampscape/metrics/acceleration.py].

Results are reported on `test_id` and every OOD split, three seeds per configuration (mean ± std), with early stopping on `val` [docs/TASK_BRIEF.md]. Rel-L2 is additionally reported as the median over seeds: it is a ratio of squared sums dominated by the few highest-current landscapes, so one seed that misses them moves the mean by more than the seed spread of every other metric — at L the three GNN seeds give 0.789, 0.925 and 1.108 on test_id while their MAE and Spearman agree within 0.02 [docs/tables/baselines_full.md]. Predictions are framework-agnostic (`predictions.h5` plus `meta.json`, Appendix F) and are scored by `scripts/evaluate.py` [ampscape/eval/harness.py; docs/evaluation.md]. At M and L the primary T4 metrics are computed against the exact block-1 map on the reference subsets (400 / 300 / 300 landscapes for test_id / test_ood / ood_region at M; 24 / 16 / 20 at L), block-centred metrics secondary [docs/tables/t4_pareto_M.md; docs/tables/t4_pareto_L.md; DECISIONS.md]. The leaderboard (`aux/leaderboard/` on the Hub) accepts the same prediction format; entries are validated, appended by a maintainer and never edited [docs/submission.md].

## 7 Baselines and results

### 7.1 Models, protocol and configuration selection

All learned baselines share the inputs and target of Section 3. **U-Net**: 4-level encoder–decoder, base width 32 (7.8 M parameters), tuned width-64 variant `w64` (31.0 M). **FNO**: 64 retained modes plus a distance-to-source channel, width 32 (33.6 M), tuned width-48 variant `w48` (75.5 M). **ViT**: patch-4 embedding, global attention (dim 192, depth 6), a learned 32×32 positional embedding interpolated to other grids (3.0 M); the tuned `p16g16` variant uses patch 16 on a native 16×16 grid at M. **GNN**: grid-as-graph message passing with a 4×-coarsened second level (`ms`, 0.2 M), tuned 8×-coarsened variant `ms8` [ampscape/models/unet.py; ampscape/models/fno.py; ampscape/models/vit.py; ampscape/models/gnn.py; docs/tables/tuning_full.md]. **MgNO**: the multigrid neural operator of He et al. [42], vendored from the authors' MIT release (0.58 M), run with seed 1 at S and M on T1 and T4 [docs/wp6_implementations.md; paper/tables/baselines_sml.md]. Non-learned rows: **coarsen ×4** (solve on a 4×-coarsened grid and upsample) and Omniscape **block-size rows** with and without artefact correction [ampscape/models/coarsen.py; docs/tables/t4_pareto_M.md].

Each run trains one model on one task at one tier for 30 epochs with AdamW, a cosine schedule, patience 8 and a fixed seed, three seeds per (model, task, tier), with train-only normalisation statistics of the training tier used at every evaluation tier [scripts/train.py; docs/phase10_full_schedule.md; scripts/transfer_eval.py]. **Configuration selection.** One alternative configuration per model was trained at M and L on T1 (seed 1) and compared with the official one on the best validation loss [docs/tables/tuning_full.md]. The winning variants were re-trained with three seeds on every task, and the official configuration is chosen *per model × task × tier on validation loss alone*: the tuned configuration is official only if its mean best validation loss over seeds is below the pre-tuning mean by more than the pre-tuning standard error (std / √3); test metrics are never read and no decision is carried across tasks [docs/tables/tuning_decisions.md]. Appendix B.5 lists the fifteen decisions: the tuned configuration is official for FNO w48 at every task at M and L, U-Net w64 at T1 and T4 M, ViT p16g16 at T1 M and GNN ms8 at T1 M, T1 L and T4 L; the pre-tuning configuration stays official for U-Net T3 M (−1.4 %, inside the seed spread), ViT T4 M (+16.8 %) and GNN T4 M (+8.0 %), and for U-Net and ViT at L no candidate beat the official configuration [docs/tables/tuning_decisions.md; docs/tables/tuning_full.md]. All baselines, transfers, ablations and the demonstration consumed 701.5 GPU-hours across 773 jobs [docs/tables/gpu_usage.md].

### 7.2 In-distribution results at S, M and L

**Table 3. Rel-L2 on test_id, mean ± std [median] over 3 seeds, official configurations; MgNO seed 1** [paper/tables/baselines_sml.md]. Figure 1 (`paper/figures/error_vs_tier.png`) plots the same rows with the speed-up.

| task | model | S | M | L |
|---|---|---|---|---|
| T1 | U-Net | 0.114 ± 0.007 [0.111] | 0.187 ± 0.022 [0.187] | 0.397 ± 0.012 [0.392] |
| T1 | FNO | 0.199 ± 0.002 [0.199] | 0.208 ± 0.003 [0.209] | 0.299 ± 0.012 [0.297] |
| T1 | ViT | 0.218 ± 0.028 [0.229] | 0.306 ± 0.012 [0.299] | 0.648 ± 0.033 [0.644] |
| T1 | GNN | 0.561 ± 0.006 [0.563] | 0.607 ± 0.027 [0.600] | 0.941 ± 0.160 [0.925] |
| T1 | MgNO | 0.220 | 0.412 | – |
| T3 | U-Net | 0.111 ± 0.005 [0.110] | 0.202 ± 0.006 [0.202] | 0.379 ± 0.011 [0.374] |
| T3 | FNO | 0.253 ± 0.001 [0.252] | 0.255 ± 0.003 [0.254] | 0.323 ± 0.002 [0.323] |
| T4 | U-Net | 0.041 ± 0.002 [0.041] | 0.042 ± 0.001 [0.041] | 0.081 ± 0.001 [0.081] |
| T4 | FNO | 0.051 ± 0.001 [0.051] | 0.073 ± 0.001 [0.073] | 0.116 ± 0.000 [0.116] |
| T4 | ViT | 0.052 ± 0.001 [0.052] | 0.094 ± 0.004 [0.093] | 0.159 ± 0.004 [0.161] |
| T4 | GNN | 0.066 ± 0.000 [0.066] | 0.099 ± 0.001 [0.099] | 0.142 ± 0.001 [0.142] |
| T4 | MgNO | 0.044 | 0.189 | – |

Three observations structure the results. First, the task families differ: T4 is the easier learning problem and the one with the real compute problem — the U-Net stays at rel-L2 0.041–0.081 from S to L with Spearman 0.996 / 0.996 / 0.991 at median speed-ups of 167,020× / 32,789× / 111,998× over the production Omniscape run — whereas T1 and T3, globally coupled through one sparse solve, are harder for every model and give speed-ups of only 10²–10³ (U-Net T1 625× / 537× / 691×) because a full-raster pairwise solve is already cheap [paper/tables/baselines_sml.md]. Second, error grows with tier for every model and task: the best T1 result goes from 0.114 at S to 0.299 at L and the best T4 result from 0.041 to 0.081 [paper/tables/baselines_sml.md]. Third, ranking metrics degrade more slowly than magnitudes: between S and L the T4 U-Net's rel-L2 doubles (0.041 → 0.081) and its pinch-point recall drops from 0.918 to 0.825 while its Spearman moves from 0.996 to 0.991 [paper/tables/baselines_sml.md].

The families fail in different places. The U-Net is strongest on T1 and T4 at S and M but degrades fastest with tier and loses its T1 lead to the FNO at L (0.397 vs 0.299); the FNO has the best T1 result at L, the highest T1 Spearman at every tier and, as Section 7.4 shows, the best transfer; the ViT is competitive at S (T1 0.218, T4 0.052) and resolution-inappropriate at L even after tuning (T1 0.648 with top-5 % IoU 0.146); the GNN is far behind on T1 at every tier (0.561 / 0.607 / 0.941, with the largest seed disagreement on rel-L2 at L, median 0.925) but competitive on the locally windowed T4 (0.066 / 0.099 / 0.142, ahead of the ViT at L) at 5.06–9.44 GPU-h per run against 0.79–1.97 for the U-Net [paper/tables/baselines_sml.md]. MgNO (seed 1, 0.58 M parameters) matches the U-Net on T4 at S (0.044 vs 0.041) but falls to 0.189 at M and to 0.220 / 0.412 on T1 [paper/tables/baselines_sml.md]. No single family wins on accuracy, scale robustness, OOD robustness and cost at once; that trade-off, rather than any one number, is the result.

### 7.3 T4 against the exact reference: the speed–accuracy frontier

For the reference subsets we computed exact block-1 maps, so solver approximations and learned models share one error-versus-cost axis (Figure 2, `paper/figures/t4_pareto_{M,L}.png`). Table 4 lists the test_id rows.

**Table 4. T4 rel-L2 against the exact block-1 map on the test_id reference subset (n = 400 at M, 24 at L), cost per landscape (solver: single-core wall time; learned: median batch-amortised GPU inference)** [paper/tables/t4_pareto_M.md; paper/tables/t4_pareto_L.md].

| tier | method | cost s / landscape | rel-L2 | top-5 % IoU | pinch recall | Spearman |
|---|---|---|---|---|---|---|
| M | block 1 (exact) | 776 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| M | production block 3, correction on | 111 | 0.0291 | 0.9357 | 0.9312 | 0.9983 |
| M | block 3, correction off | 112 | 0.1105 | 0.6105 | 0.7658 | 0.9856 |
| M | block 7, correction on | 25.5 | 0.0983 | 0.8081 | 0.8081 | 0.9845 |
| M | U-Net (w64, 3 seeds) | 0.00328 | 0.0510 | 0.8532 | 0.9035 | 0.9957 |
| M | FNO (w48, 3 seeds) | 0.003 | 0.0761 | 0.7872 | 0.7530 | 0.9866 |
| M | ViT (3 seeds) | 0.00205 | 0.0931 | 0.7202 | 0.8145 | 0.9822 |
| M | GNN (3 seeds) | 0.0164 | 0.0928 | 0.7034 | 0.7770 | 0.9783 |
| M | MgNO (1 seed) | 0.000925 | 0.1864 | 0.5794 | 0.7271 | 0.9526 |
| L | block 1 (exact) | 1.23e+04 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| L | block 3, correction on | 1.65e+03 | 0.0280 | 0.9410 | 0.9347 | 0.9982 |
| L | production block 5, correction on | 566 | 0.0315 | 0.9344 | 0.9319 | 0.9979 |
| L | block 11, correction on | 164 | 0.0854 | 0.8317 | 0.8183 | 0.9895 |
| L | U-Net (3 seeds) | 0.00652 | 0.0903 | 0.7930 | 0.7803 | 0.9894 |
| L | FNO (w48, 3 seeds) | 0.00281 | 0.1199 | 0.7200 | 0.5272 | 0.9746 |
| L | ViT (3 seeds) | 0.0153 | 0.1603 | 0.6044 | 0.6715 | 0.9490 |
| L | GNN (ms8, 3 seeds) | 0.0445 | 0.1475 | 0.6170 | 0.6341 | 0.9538 |

(i) The production targets approximate the exact map well — rel-L2 0.0291 at M and 0.0315 at L — so a model's error against its training target and against the exact map differ little (U-Net 0.042 vs 0.0510 at M, 0.081 vs 0.0903 at L) [paper/tables/t4_pareto_M.md; paper/tables/t4_pareto_L.md; paper/tables/baselines_sml.md]. (ii) Omniscape's artefact correction matters more than the block size: block 3 without correction (0.1105) is worse than block 7 with it (0.0983) at M [paper/tables/t4_pareto_M.md]. (iii) The learned models occupy a different part of the frontier rather than dominating it: at M the U-Net's 0.0510 lies between the production solver (0.0291 at 111 s) and block 7 (0.0983 at 25.5 s) at 0.00328 s per landscape; at L its 0.0903 is comparable to block 11 (0.0854 at 164 s) at 0.00652 s [paper/tables/t4_pareto_M.md; paper/tables/t4_pareto_L.md]. Whoever needs rel-L2 < 0.03 still needs the solver; whoever needs hundreds of maps at ≈ 0.05–0.09 does not.

### 7.4 Scale transfer: zero-shot XL/XXL and the scale-aware target

Models trained at L were evaluated at XL (1024²) and XXL (2048²) without fine-tuning, with the official configuration (zero-shot, 3 seeds) and with a variant whose training target is divided by a factor computed from the inputs and the evaluation tier only — the Omniscape radius ratio r_L/r_tier for T4, √(N_valid/512²) for T1 ("scale-aware", seed 1; no XL/XXL data enters training or the inverse) [paper/tables/scale_transfer.md; ampscape/models/common.py]. The ViT's interpolated positional embedding stops at XL [docs/phase10_full_schedule.md]. Figure 3 (`paper/figures/scale_transfer.png`) plots Table 5.

**Table 5. Rel-L2 on test_id at L, XL and XXL (zero-shot: mean ± std [median] over 3 seeds; scale-aware: seed 1)** [paper/tables/scale_transfer.md].

| task | model | L | XL zero-shot | XL scale-aware | XXL zero-shot | XXL scale-aware |
|---|---|---|---|---|---|---|
| T4 | U-Net | 0.081 ± 0.001 | 0.515 ± 0.002 [0.515] | 0.189 | 0.749 ± 0.002 [0.749] | 0.312 |
| T4 | FNO | 0.116 ± 0.000 | 0.531 ± 0.002 [0.532] | 0.157 | 0.764 ± 0.001 [0.764] | 0.197 |
| T4 | ViT | 0.159 ± 0.004 | 0.538 ± 0.000 [0.538] | 0.203 | – | – |
| T4 | GNN | 0.142 ± 0.001 | 0.498 ± 0.003 [0.497] | 0.308 | 0.739 ± 0.002 [0.738] | 0.438 |
| T1 | U-Net | 0.397 ± 0.011 | 1.250 ± 0.421 [1.026] | 0.957 | 4.425 ± 3.659 [4.015] | 0.987 |
| T1 | FNO | 0.299 ± 0.011 | 0.617 ± 0.010 [0.611] | 0.700 | 1.352 ± 0.092 [1.393] | 0.762 |
| T1 | ViT | 0.648 ± 0.033 | 0.768 ± 0.006 [0.767] | 0.656 | – | – |
| T1 | GNN | 0.941 ± 0.160 | 1.415 ± 0.821 [0.978] | 7.509 | 1.615 ± 0.582 [1.334] | 1.405 |

Zero-shot transfer fails on magnitude in a regular way for T4: every model lands at rel-L2 0.498–0.538 at XL and 0.739–0.764 at XXL, which equals 1 − r_L/r_tier, the share of the current magnitude that the larger Omniscape radius adds and an L-trained model cannot know about (Appendix A derives it: 0.50 and 0.75) [paper/tables/scale_transfer.md]. Removing that factor from the target recovers T4 to 0.157–0.308 at XL and 0.197–0.438 at XXL — still above in-tier errors, but no longer set by a known factor; the FNO transfers best (0.157 / 0.197) [paper/tables/scale_transfer.md]. For T1 the picture is mixed: the scale-aware target helps the FNO at XXL (1.352 → 0.762) but not at XL (0.617 → 0.700), the U-Net stays near rel-L2 1 at both tiers (0.957 / 0.987) — its receptive field, not the magnitude, is the limit — and the GNN variant diverges at XL (7.509) [paper/tables/scale_transfer.md]. Rankings survive what magnitudes do not: the zero-shot T4 U-Net keeps Spearman 0.992 / 0.946 / 0.904 and top-5 % IoU 0.812 / 0.596 / 0.505 at L / XL / XXL while its rel-L2 goes 0.081 → 0.515 → 0.749, and the FNO keeps Spearman 0.975 / 0.958 / 0.942 [paper/tables/scale_transfer.md]. The one unstable case is the zero-shot T1 U-Net at XXL (4.425 ± 3.659, Spearman 0.461 ± 0.034) [paper/tables/scale_transfer.md]. A surrogate trained at one resolution can therefore still *rank* locations at a larger one, but its absolute currents must be rescaled or re-trained.

### 7.5 Out-of-distribution degradation at the training tier

Appendix B.3 gives rel-L2 on the in-tier test splits and the ratios to `test_id` for every model (Figure 4, `paper/figures/ood_degradation.png`).

A held-out resistance table and contrast cost little at the training tier: the `test_ood` ratio is 0.920–1.200 for every model, task and tier except the ViT on T1 at L (1.486, its structurally failing configuration); T4 is the most sensitive family (1.039–1.200) [paper/tables/ood_degradation.md]. Published real resistance surfaces are the hardest in-tier set for T4 (S only: ratios 1.273–1.524, U-Net 1.524) while T1 and T3 stay within 0.941–1.145 of `test_id`; since T4 surrogates are the ones that would run on practitioners' own surfaces, this is the number to quote beside the headline [paper/tables/ood_degradation.md; paper/ood_analysis.md]. The held-out-region split is *easier* than `test_id` for every model, task and tier (ratios 0.655–0.982) [paper/tables/ood_degradation.md], which is not evidence of spatial robustness: the split is real-tile only and the held-out biomes and realm differ in composition — at S, `ood_region` has a real share of 1.00 and a p90 contrast of 595 against 0.38 and 10,000 for `test_id` [paper/ood_analysis.md]. Errors track landscape difficulty more than spatial novelty, so `ood_region` is a spatial-leakage control (test regions never overlap training regions), not a stress test.

### 7.6 Data scaling, solver acceleration

**Data scaling.** U-Net and FNO were trained on T1 at S with n ∈ {1,000; 5,000; 20,000} landscapes in a fixed-epoch regime (30 epochs) and a fixed-step regime (≈ the official run's optimisation steps), seed 1, against the official run on 61,577 landscapes [paper/tables/wp4_data_scaling.md]. At a fixed step budget the U-Net saturates early — 20,000 landscapes give 0.103 and 5,000 give 0.139 against 0.111 for the full run — so the official 30-epoch protocol at S is budget-limited rather than data-limited for the U-Net, whereas the FNO keeps improving with data (0.438 → 0.298 → 0.246 → 0.198) [paper/tables/wp4_data_scaling.md]. Fixed-epoch training on small subsets understates both models (U-Net 0.496 vs 0.368 at 1,000), so the regime must be stated when quoting data efficiency [paper/tables/wp4_data_scaling.md].

**Solver acceleration.** For T1–T3 the practically relevant question is whether a predicted voltage shortens the exact solve. The official U-Net and FNO were trained with the voltage map as target (T3, and the first pair of each T1 landscape; seed 1) and the AMG-preconditioned CG of the reference solver was warm-started from the prediction on every test_id and test_ood system at S, M and L, to a relative residual of 1e-6 (Appendix B.6) [docs/tables/acceleration.md]. There is no gain anywhere: on T3 test_id the U-Net start takes 10 → 10 iterations at S, 12 → 13 at M and 17 → 19 at L, with wall time 763.2 → 858.6 ms at L [docs/tables/acceleration.md]. The predicted maps are accurate in the MAE sense, but their relative Kirchhoff residual is 82.5–3.87e+03 times that of the zero vector [docs/tables/acceleration.md]: a pixel-wise error of a few per cent is high-frequency, the Laplacian amplifies it, and PCG removes it in the same iterations it needs from zero. The value of the surrogates on these tasks is the cheaper *map*, not a better initial guess; acceleration would require a residual-aware objective, which this benchmark leaves open.

## 8 Many-query demonstration

The case for a T4 surrogate is the study that needs many maps per landscape. We ran the best T4 model at L (U-Net, seed 1; rel-L2 0.080 against the exact block-1 map on test_id) on 20 held-out real L tiles × 8 resistance tables (four expert tables, the v1.0 random draw and three extra random draws solved with the production pipeline), 160 maps in all, and asked whether the study-level conclusions a practitioner would draw from the surrogate match those drawn from the solver [docs/wp7_demo.md] (Figure 5, `paper/figures/wp7_demo.png`).

**Table 6. Study-level agreement between the solver route and the surrogate route** [docs/wp7_demo.md].

| conclusion | solver route | model route | agreement |
|---|---|---|---|
| stability of the top-5 % regions across tables (mean pairwise IoU) | 0.463 | 0.458 | mean abs. difference of the IoU matrices 0.019 |
| consensus core (top-5 % in ≥ 75 % of tables), fraction of valid pixels | 0.0357 | — | IoU model-vs-solver core 0.825 (median 0.843) |
| ranking of tables by effect vs the generic table | — | — | Spearman 0.991; same most-influential table in 100 % of tiles; top-3 overlap 0.98 |
| persistent pinch points (≥ 50 % of tables) | 5586.6 per tile | — | recall 0.941, precision 0.657 (3-px tolerance) |
| per-map accuracy (context) | — | rel-L2 vs solver mean 0.054, worst table 0.100 | |
| total cost for 160 maps | 36.3 CPU-h (817 s per map, 1 core) | 11.8 s on one GPU (74 ms per map) + training once | ×11077 |

Every study-level conclusion is reproduced — the stability estimate is 0.458 against the solver's 0.463, the consensus core overlaps at IoU 0.825, the table ranking has Spearman 0.991 with the same most-influential table on every tile, persistent pinch points are recovered with recall 0.941 — at 11,077× lower cost after training once [docs/wp7_demo.md]. The weak point is pinch-point *precision*, 0.657: the surrogate proposes more persistent pinch points than the solver confirms, so a candidate list drawn from it should be solver-verified before it becomes a decision map.

## 9 Discussion, limitations, ethics and maintenance

**What the benchmark separates.** The tasks separate the model families along interpretable axes: the GNN's multi-scale graph does not resolve long-range pairwise flow (T1 L 0.941) but is competitive on the locally windowed T4 (0.142 vs ViT 0.159 at L), the reverse of the convolutional models' strengths [paper/tables/baselines_sml.md]; data scaling separates budget from data limits; the block-size rows put a non-learned approximation on the same cost axis [paper/tables/t4_pareto_M.md]; and the per-task selection rule shows that a configuration tuned on one task does not transfer — the width-64 U-Net and the ms8 GNN win T1 at M but not T3 or T4 there, while ms8 wins both tasks at L [docs/tables/tuning_decisions.md]. Not yet tested: training at XL (every XL/XXL row is a transfer of an L model), fixed-step training at M/L, MgNO at L and with three seeds, and the controlled resolution-versus-size probe set published under `aux/` [docs/addendum_WP5_report.md].

**Limitations.** (1) Resistance tables are structural proxies, not ecological truth, and a faster approximation does not reduce resistance-surface uncertainty — it lets a user explore it (Section 8) [docs/dataset_card.md]. (2) Learned models degrade on published surfaces and across scale; final decision maps should be solver-verified [paper/tables/ood_degradation.md]. (3) T4 targets carry a quantified blocking approximation (mean rel-L2 0.029 at M, 0.028 at L); at XL/XXL only the production target exists, with the M/L figures as the stated bound [docs/t4_fidelity.md]. (4) Pixel size, raster size and the Omniscape radius are confounded in the scale split, and T4 scale transfer also crosses an operator change (block 5 → 11 → 25) [docs/dataset_card.md; docs/t4_fidelity.md]. (5) XXL footprints overlap finer-tier training cells; only `test_ood_scale_strict` isolates both resolution and spatial novelty [docs/dataset_card.md]. (6) The held-out-region split is a leakage control, not a stress test [paper/ood_analysis.md]. (7) The ViT's official configuration is resolution-inappropriate above S [DECISIONS.md]. (8) The scale-aware variants, the data-scaling ablation, MgNO and the demonstration are single-seed; the official S/M/L rows use three seeds [paper/tables/scale_transfer.md; paper/tables/wp4_data_scaling.md; docs/wp7_demo.md]. (9) Domain-metric thresholds are not validated against ecological outcomes [docs/dataset_card.md].

**Claims the paper does not make.** Not "Circuitscape is slow": a pairwise solve takes seconds at every tier [docs/tables/dataset_statistics.md]; the documented cost is omnidirectional and many-query [18–23]. Not "exact solvers are not differentiable" [30, 31]. Not "no prior work on where to intervene" [24–30].

**Ethics and intended use.** No personal data: real tiles derive from public land-cover and terrain products at ≥ 100 m, and no protected-area polygons are used [docs/dataset_card.md]. Every stored covariate comes from a source whose licence permits redistribution of derived rasters — ESA WorldCover, HydroRIVERS, gHM and RESOLVE (CC BY 4.0), Copernicus DEM GLO-30 (with its notices), the published-resistance rasters (CC BY 4.0, CC0) — and the data are released under CC BY 4.0 with the attribution block and Copernicus notices verbatim (Appendix E) [docs/licenses.md; docs/dataset_card.md]. One point is stated as unresolved: GRIP4 is CC0 by its publisher and CC BY 4.0 in secondary catalogues; we attribute under the stricter reading and store only non-reversible distance and class rasters [docs/licenses.md]. Intended use is screening — many-query exploration, model comparison, operator-learning research — not final decisions.

**Maintenance.** Versioned Hub revisions (`v1.0` data, `v1.0.2` metadata), `CHANGELOG.md` and `DECISIONS.md` in the code repository, scripted regeneration from the frozen `v1.0-pipeline` tag, CI over the test suite, a licence-consistency test over the source manifest and a parse test over every script, issues on GitHub, and a DOI minted at submission [docs/dataset_card.md; CHANGELOG.md].

**Reproducibility.** Data: `Xirro/AmpScape` on the Hugging Face Hub (CC BY 4.0), with `index/<tier>.parquet`, split lists, Croissant metadata and per-sample solver provenance; code: `github.com/Xyrro/AmpScape` (MIT) with a locked Python environment (`uv.lock`), the Julia solver wrapper, the generation driver, the evaluation harness (`scripts/evaluate.py`), the training and transfer scripts, and the leaderboard tooling (`docs/submission.md`); every table and figure in this paper is regenerated by `scripts/paper_figures.py` from the published result files under `aux/results/` and every number is tagged with its source file. The datasheet is the dataset card (`docs/dataset_card.md`), and the generation record with its incidents is the post-mortem (`docs/generation_postmortem.md`). Compute: 16 552 CPU core-hours for generation and the precision pass [docs/generation_postmortem.md]; 701.5 GPU-hours for everything learned [docs/tables/gpu_usage.md].

## References

1. McRae, B. H. (2006). Isolation by resistance. *Evolution* 60(8):1551–1561.
2. McRae, B. H., Dickson, B. G., Keitt, T. H., & Shah, V. B. (2008). Using circuit theory to model connectivity in ecology, evolution, and conservation. *Ecology* 89(10):2712–2724.
3. Adriaensen, F., et al. (2003). The application of 'least-cost' modelling as a functional landscape model. *Landscape and Urban Planning* 64(4):233–247.
4. Anantharaman, R., Hall, K., Shah, V. B., & Edelman, A. (2020). Circuitscape in Julia: High performance connectivity modelling to support conservation decisions. *Proc. JuliaCon Conf.* 1(1):58.
5. Hall, K. R., et al. (2021). Circuitscape in Julia: Empowering dynamic approaches to connectivity assessment. *Land* 10(3):301.
6. McRae, B. H., et al. (2016). Conserving Nature's Stage: Mapping omnidirectional connectivity for resilient terrestrial landscapes in the Pacific Northwest. The Nature Conservancy.
7. Landau, V. A., Shah, V. B., Anantharaman, R., & Hall, K. R. (2021). Omniscape.jl: Software to compute omnidirectional landscape connectivity. *JOSS* 6(57):2829.
8. Leonard, P. B., et al. (2017). gflow: software for modelling circuit theory-based connectivity at any scale. *MEE* 8(4):519–526.
9. Van Moorter, B., et al. (2023). Accelerating advances in landscape connectivity modelling with the ConScape library. *MEE* 14(1):133–145.
10. Panzacchi, M., et al. (2016). Predicting the continuum between corridors and barriers to animal movements using Step Selection Functions and Randomized Shortest Paths. *J. Anim. Ecol.* 85(1):32–42.
11. Brennan, A., et al. (2022). Functional connectivity of the world's protected areas. *Science* 376(6597):1101–1104.
12. Koutis, I., Miller, G. L., & Peng, R. (2010). Approaching optimality for solving SDD linear systems. *FOCS 2010*, 235–244.
13. Spielman, D. A., & Srivastava, N. (2011). Graph sparsification by effective resistances. *SIAM J. Comput.* 40(6):1913–1926.
14. Zeller, K. A., McGarigal, K., & Whiteley, A. R. (2012). Estimating landscape resistance to movement: a review. *Landscape Ecology* 27(6):777–797.
15. Peterman, W. E. (2018). ResistanceGA: An R package for the optimization of resistance surfaces using genetic algorithms. *MEE* 9(6):1638–1647.
16. Hanks, E. M., & Hooten, M. B. (2013). Circuit theory and model-based inference for landscape connectivity. *JASA* 108(501):22–33.
17. Bowman, J., et al. (2020). Effects of cost surface uncertainty on current density estimates from circuit theory. *PeerJ* 8:e9617.
18. Dertien, J. S., & Baldwin, R. F. (2023). Does scale or method matter for conservation? Application of directional and omnidirectional connectivity models in spatial prioritizations. *Frontiers in Conservation Science* 4.
19. Martinez-Cillero, R., et al. (2023). Functional connectivity modelling and biodiversity Net Gain in England: Recommendations for practitioners. *J. Environ. Manage.* 328:116857.
20. Omniscape.jl issue #92 (2021-03-09). https://github.com/Circuitscape/Omniscape.jl/issues/92
21. Heckford, bc-connectivity repository (README and reports), 2026. https://github.com/Heckford/bc-connectivity
22. Omniscape.jl User Guide, `block_size`. https://docs.circuitscape.org/Omniscape.jl/stable/usage/
23. Belote, R. T., Barnett, K., Zeller, K., Brennan, A., & Gage, J. (2022). Examining local and regional ecological connectivity throughout North America. *Landscape Ecology* 37:2977–2990.
24. McRae, B. H., Hall, S. A., Beier, P., & Theobald, D. M. (2012). Where to restore ecological connectivity? Detecting barriers and quantifying restoration benefits. *PLoS ONE* 7(12):e52604.
25. Linkage Mapper tools (Pinchpoint Mapper, Barrier Mapper, Centrality Mapper). https://linkagemapper.org/linkage-mapper-tools/
26. Moilanen, A., et al. (2005). Prioritizing multiple-use landscapes for conservation: methods for large multi-species planning problems. *Proc. R. Soc. B* 272(1575):1885–1891.
27. Moilanen, A., et al. (2022). Novel methods for spatial prioritization with applications in conservation, land use planning and ecological impact avoidance. *MEE* 13(5):1062–1072.
28. Daigle, R. M., et al. (2020). Operationalizing ecological connectivity in spatial conservation planning with Marxan Connect. *MEE* 11(4):570–579.
29. Hamonic, F., Vaxès, Y., Couëtoux, B., & Albert, C. H. (2025). GECOT: Graph-based ecological connectivity optimization tool. *MEE* 16(9):1914–1922.
30. Van Moorter, B., et al. (2026). A unified framework for prioritizing habitat and connectivity conservation through analytical sensitivity. bioRxiv 2026.01.05.697654.
31. Boussange, V. (2025). JAXScape: A minimal JAX library for connectivity modelling at scale. Zenodo 10.5281/zenodo.15267703.
32. Equihua, J., Beckmann, M., & Seppelt, R. (2024). Connectivity conservation planning through deep reinforcement learning. *MEE* 15(4):779–790.
33. Smith, C. C. R., Tittes, S., Ralph, P. L., & Kern, A. D. (2023). Dispersal inference from population genetic variation using a convolutional neural network. *Genetics* 224(2):iyad068.
34. Li, Z., et al. (2021). Fourier neural operator for parametric partial differential equations. *ICLR 2021*.
35. Takamoto, M., et al. (2022). PDEBench: An extensive benchmark for scientific machine learning. *NeurIPS 2022 Datasets and Benchmarks*.
36. Kossaifi, J., et al. (2024). A library for learning neural operators. arXiv:2412.10354.
37. Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for biomedical image segmentation. *MICCAI 2015*.
38. Gupta, J. K., & Brandstetter, J. (2022). Towards multi-spatiotemporal-scale generalized PDE modeling. arXiv:2209.15616.
39. Battaglia, P. W., et al. (2018). Relational inductive biases, deep learning, and graph networks. arXiv:1806.01261.
40. Pfaff, T., Fortunato, M., Sanchez-Gonzalez, A., & Battaglia, P. W. (2021). Learning mesh-based simulation with graph networks. *ICLR 2021*.
41. Liu, X., Xu, B., Cao, S., & Zhang, L. (2024). Mitigating spectral bias for the multiscale operator learning. *J. Comput. Phys.* 506:112944.
42. He, J., Liu, X., & Xu, J. (2024). MgNO: Efficient parameterization of linear operators via multigrid. *ICLR 2024*.
43. Xu, B., Liu, X., & Zhang, L. (2024). Dilated convolution neural operator for multiscale partial differential equations. arXiv:2408.00775.
44. Haltmayer, M., et al. (2026). Deep learning-based surrogate modelling of the LOD method for multiscale problems. arXiv:2607.12570.
45. Trifonov, V., et al. (2024). ConDiff: A challenging dataset for neural solvers of partial differential equations. arXiv:2406.04709.
46. Lan, K. W., et al. (2024). A neural-preconditioned Poisson solver for mixed Dirichlet and Neumann boundary conditions. *ICML 2024*.
47. Li, Y., Chen, P. Y., Du, T., & Matusik, W. (2023). Learning preconditioners for conjugate gradient PDE solvers. *ICML 2023*.
48. Klamkin, M., Tanneau, M., & Van Hentenryck, P. (2025). PGLearn — An open-source learning toolkit for optimal power flow. arXiv:2505.22825.
49. Lovett, S., et al. (2024). OPFData: Large-scale datasets for AC optimal power flow with topological perturbations. arXiv:2406.07234.
50. Joswig-Jones, T., Baker, K., & Zamzam, A. S. (2021). OPF-Learn: An open-source framework for creating representative AC optimal power flow datasets. arXiv:2111.01228.
51. Ohana, R., McCabe, M., et al. (2024). The Well: a large-scale collection of diverse physics simulations for machine learning. *NeurIPS 2024 Datasets and Benchmarks*.
52. Bonnet, F., Mazari, J. A., Cinnella, P., & Gallinari, P. (2022). AirfRANS: High fidelity computational fluid dynamics dataset for approximating Reynolds-averaged Navier–Stokes solutions. *NeurIPS 2022 Datasets and Benchmarks*.
53. Gebru, T., et al. (2021). Datasheets for datasets. *CACM* 64(12):86–92.
54. NeurIPS 2026 Evaluations & Datasets Track, Call for Papers. https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets

Full citation details with access dates: `paper/sections/related_work.md`.

---

# Appendix

## A Why zero-shot T4 scale transfer fails by 1 − r_train/r_eval, and why the scale-aware target removes it

Facts used: Omniscape window radius per tier r = 16, 32, 64, 128, 256 px for S, M, L, XL, XXL with block size b = largest odd integer ≤ r/10 [docs/t4_fidelity.md]; source strength s(x) ∈ [0, 1] = inverse-resistance suitability above its 0.5 quantile rescaled to a maximum of 1 per landscape [docs/t4_fidelity.md]; targets are cumulative current summed over windows [docs/t4_fidelity.md]; measured zero-shot errors of the L-trained models on test_id: rel-L2 0.515 / 0.531 / 0.538 / 0.498 (U-Net / FNO / ViT / GNN) at XL and 0.749 / 0.764 / 0.739 (U-Net / FNO / GNN) at XXL, three seeds each with std ≤ 0.003 [paper/tables/scale_transfer.md].

**A.1 Magnitude scales with the window radius.** Omniscape visits every block centre t and solves one circuit per visit: every pixel x within distance r of t injects a current proportional to s(x) and t is grounded; the per-visit maps are summed into the cumulative current C. (1) The injected current per visit is Σ_{|x−t|≤r} s(x) ≈ s̄ · π r², with s̄ the mean source strength of the window (an input the model sees, independent of the tier). (2) Within one visit the injected current flows towards the single grounded target; for a pixel at distance ρ from t the current crossing a front of length ∝ ρ is ∝ s̄ ρ²/ρ = s̄ ρ, of order s̄ r over most of the window; the resistance-dependent proportionality constant is what the surrogate learns and its dependence on r is the same for every pixel. (3) The number of visits covering a pixel is the number of block centres within distance r, ∝ (r/b)², a constant (≈ 100) under the block rule [derived: b ≈ r/10]. Hence C(y) ∝ s̄ · r · g(y), where g collects the resistance-dependent, tier-independent factors: doubling the radius doubles the cumulative current to first order.

**A.2 The zero-shot error.** A model trained at L learns C_L ∝ r_L · s̄ · g. Evaluated at radius r_eval on a landscape with the same resistance statistics it predicts P ≈ C_eval · (r_L/r_eval): the same g, the wrong magnitude. With κ = r_L/r_eval, rel-L2 = ‖P − C_eval‖₂/‖C_eval‖₂ = ‖(κ − 1) C_eval + ε‖₂/‖C_eval‖₂ ≈ 1 − κ, where ε is the model's intrinsic error (its in-tier rel-L2 is 0.081–0.159 [paper/tables/baselines_sml.md]) and the approximation holds when (1 − κ)‖C‖ dominates ‖ε‖. Predicted: XL 1 − 64/128 = 0.50, XXL 1 − 64/256 = 0.75 [derived: radii from docs/t4_fidelity.md]; measured 0.498–0.538 and 0.739–0.764, the small excess accounted for by ε in quadrature [paper/tables/scale_transfer.md]. The near-identical values across four architectures with std ≤ 0.003 across seeds are consistent with an error set by the operator, not the model. Rank metrics ignore a common factor, which is why Spearman stays at 0.894–0.958 at XL while rel-L2 collapses [paper/tables/scale_transfer.md].

**A.3 The scale-aware target.** The variant trains on k · C with k = r_ref/r_tier, r_ref = 64 [ampscape/models/common.py], so the regression target k · C ∝ r_ref · s̄ · g is tier-independent; at evaluation the prediction is divided by k_eval, restoring C_eval ∝ r_eval · s̄ · g. No quantity of the evaluation tier other than its radius (a protocol constant) enters, and no XL/XXL data is used in training or in the inverse. What remains is the error that is not a common factor: 0.157–0.308 at XL and 0.197–0.438 at XXL against in-tier 0.081–0.159 [paper/tables/scale_transfer.md] — the operator-learning transfer error proper, since b and r both scale and the resistance field has a different pixel size and extent.

**A.4 The pairwise analogue.** For a pairwise solve a unit current is injected per source regardless of landscape size. Under a uniform rescaling by s per axis the current crossing any front spreads over ∝ s pixels, so the per-pixel current ∝ 1/s while the valid pixel count N ∝ s²; k = √(N_valid/N_ref) with N_ref = 512² [ampscape/models/common.py] makes k · C invariant and is computed from the input mask alone. The measured throughput error of the zero-shot T1 transfers (0.434–0.985 at XL) is the signature of the same mismatch [paper/tables/scale_transfer.md]; the correction helps the FNO at XXL (1.352 → 0.762) but not the U-Net (0.957 / 0.987 at XL / XXL), whose receptive field does not cover the longer flow paths of larger landscapes — a structural, not a magnitude, limit [paper/tables/scale_transfer.md].

**A.5 Assumptions.** (i) b/r fixed by the block rule; (ii) sources with tier-independent mean strength; (iii) the same resistance statistics across tiers (real XL/XXL tiles have coarser pixels than L, part of the residual in A.3); (iv) the window fits inside the landscape for most pixels. The argument explains the magnitude of the zero-shot error; it does not predict which model transfers best once the magnitude is corrected.

## B Full result tables

Every table below is regenerated by `scripts/paper_figures.py` (B.1–B.4) or `scripts/tuning_effect.py` / `scripts/acceleration_table.py` (B.5–B.6) from the published result files; the figures are `paper/figures/error_vs_tier.png`, `t4_pareto_{M,L}.png`, `scale_transfer.png`, `ood_degradation.png`, `wp4_data_scaling.png` and `wp7_demo.png`.

### B.1 Learned baselines on test_id, all metrics [paper/tables/baselines_sml.md]

See `paper/tables/baselines_sml.md` for the complete table (one row per task × tier × model: rel-L2 mean ± std and median, MAE log10, top-5 % IoU, pinch recall, Spearman, median speed-up, training GPU-h per run); Table 3 of the main text reproduces its rel-L2 columns, and Section 7.2 quotes its Spearman, IoU, pinch-recall, speed-up and GPU-h values.

### B.2 Learned baselines on every evaluation split [paper/baselines.md]

`paper/baselines.md` lists every task × tier × split × model row with rel-L2 (mean ± std and median), MAE log10, top-5 % IoU, pinch recall, Spearman, corridor Dice, SSIM and median speed-up; the non-learned coarsen ×4 rows are in `docs/tables/baselines_full.md`.

### B.3 OOD degradation, all tasks [paper/tables/ood_degradation.md]

| task | tier | model | test_id [median] | test_ood [median] | ood_region [median] | published [median] | test_ood / id | ood_region / id | published / id |
|---|---|---|---|---|---|---|---|---|---|
| T1 | S | FNO | 0.199 [0.199] | 0.200 [0.201] | 0.135 [0.135] | 0.188 [0.188] | 1.005 | 0.679 | 0.941 |
| T1 | S | GNN | 0.561 [0.563] | 0.528 [0.529] | 0.476 [0.479] | 0.610 [0.608] | 0.941 | 0.847 | 1.087 |
| T1 | S | MgNO | 0.220 [0.220] | 0.214 [0.214] | 0.170 [0.170] | 0.223 [0.223] | 0.973 | 0.773 | 1.014 |
| T1 | S | U-Net | 0.114 [0.111] | 0.121 [0.120] | 0.086 [0.085] | 0.109 [0.110] | 1.061 | 0.751 | 0.959 |
| T1 | S | ViT | 0.218 [0.229] | 0.215 [0.224] | 0.155 [0.163] | 0.221 [0.238] | 0.986 | 0.711 | 1.015 |
| T1 | M | FNO | 0.208 [0.209] | 0.205 [0.206] | 0.138 [0.140] | – | 0.982 | 0.661 | – |
| T1 | M | GNN | 0.607 [0.600] | 0.572 [0.560] | 0.518 [0.520] | – | 0.942 | 0.853 | – |
| T1 | M | MgNO | 0.412 [0.412] | 0.420 [0.420] | 0.364 [0.364] | – | 1.019 | 0.883 | – |
| T1 | M | U-Net | 0.187 [0.187] | 0.182 [0.184] | 0.144 [0.144] | – | 0.975 | 0.770 | – |
| T1 | M | ViT | 0.306 [0.299] | 0.295 [0.290] | 0.247 [0.240] | – | 0.965 | 0.808 | – |
| T1 | L | FNO | 0.299 [0.297] | 0.303 [0.305] | 0.232 [0.232] | – | 1.016 | 0.778 | – |
| T1 | L | GNN | 0.941 [0.925] | 0.927 [0.924] | 0.923 [0.903] | – | 0.985 | 0.982 | – |
| T1 | L | U-Net | 0.397 [0.392] | 0.387 [0.387] | 0.348 [0.340] | – | 0.976 | 0.876 | – |
| T1 | L | ViT | 0.648 [0.644] | 0.963 [0.692] | 0.628 [0.622] | – | 1.486 | 0.968 | – |
| T3 | S | FNO | 0.253 [0.252] | 0.234 [0.234] | 0.170 [0.171] | 0.289 [0.285] | 0.927 | 0.674 | 1.145 |
| T3 | S | U-Net | 0.111 [0.110] | 0.114 [0.114] | 0.073 [0.073] | 0.126 [0.128] | 1.024 | 0.655 | 1.138 |
| T3 | M | FNO | 0.255 [0.254] | 0.242 [0.241] | 0.172 [0.171] | – | 0.952 | 0.677 | – |
| T3 | M | U-Net | 0.202 [0.202] | 0.198 [0.201] | 0.146 [0.147] | – | 0.980 | 0.722 | – |
| T3 | L | FNO | 0.323 [0.323] | 0.297 [0.297] | 0.250 [0.250] | – | 0.920 | 0.773 | – |
| T3 | L | U-Net | 0.379 [0.374] | 0.357 [0.352] | 0.321 [0.321] | – | 0.941 | 0.848 | – |
| T4 | S | FNO | 0.051 [0.051] | 0.055 [0.055] | 0.034 [0.034] | 0.066 [0.065] | 1.079 | 0.678 | 1.303 |
| T4 | S | GNN | 0.066 [0.066] | 0.075 [0.075] | 0.047 [0.047] | 0.090 [0.090] | 1.136 | 0.707 | 1.359 |
| T4 | S | MgNO | 0.044 [0.044] | 0.048 [0.048] | 0.031 [0.031] | 0.056 [0.056] | 1.091 | 0.705 | 1.273 |
| T4 | S | U-Net | 0.041 [0.041] | 0.049 [0.049] | 0.031 [0.031] | 0.063 [0.063] | 1.177 | 0.742 | 1.524 |
| T4 | S | ViT | 0.052 [0.052] | 0.055 [0.055] | 0.034 [0.034] | 0.071 [0.071] | 1.058 | 0.660 | 1.359 |
| T4 | M | FNO | 0.073 [0.073] | 0.079 [0.079] | 0.048 [0.048] | – | 1.087 | 0.665 | – |
| T4 | M | GNN | 0.099 [0.099] | 0.105 [0.105] | 0.069 [0.069] | – | 1.064 | 0.696 | – |
| T4 | M | MgNO | 0.189 [0.189] | 0.208 [0.208] | 0.177 [0.177] | – | 1.101 | 0.937 | – |
| T4 | M | U-Net | 0.042 [0.041] | 0.050 [0.050] | 0.031 [0.030] | – | 1.200 | 0.736 | – |
| T4 | M | ViT | 0.094 [0.093] | 0.098 [0.097] | 0.065 [0.063] | – | 1.039 | 0.686 | – |
| T4 | L | FNO | 0.116 [0.116] | 0.125 [0.125] | 0.079 [0.079] | – | 1.078 | 0.684 | – |
| T4 | L | GNN | 0.142 [0.142] | 0.136 [0.136] | 0.100 [0.100] | – | 0.960 | 0.708 | – |
| T4 | L | U-Net | 0.081 [0.081] | 0.089 [0.090] | 0.064 [0.063] | – | 1.103 | 0.786 | – |
| T4 | L | ViT | 0.159 [0.161] | 0.152 [0.154] | 0.125 [0.127] | – | 0.960 | 0.790 | – |

Composition of the test splits (v1.0.2 index): at S, test_id has 9,850 landscapes with a real share of 0.38 and a p90 contrast of 10,000; test_ood 6,460 landscapes, real share 0.83, p90 contrast 1,000,000; ood_region 9,470 landscapes, real share 1.00, p90 contrast 595 [paper/ood_analysis.md].

### B.4 Scale transfer, all splits and metrics [paper/tables/scale_transfer.md]

`paper/tables/scale_transfer.md` holds every (task, model, variant, evaluation tier, split) row — rel-L2 mean ± std and median, Spearman, top-5 % IoU and throughput error. Table 5 reproduces the test_id rel-L2 columns.

### B.5 Configuration selection and the effect of the per-tier tuning on the test metrics

**Table B.5a. Official configuration per model × task × tier** (best validation loss, mean ± std over the three pre-tuning seeds versus the mean of the three tuned seeds) [docs/tables/tuning_decisions.md].

| tier | task | model | variant | val loss pre-tuning | tuned | Δ | official |
|---|---|---|---|---|---|---|---|
| M | T1 | U-Net | w64 | 0.0295 ± 0.0060 | 0.0239 | -19.0 % | tuned |
| M | T1 | FNO | w48 | 0.0495 ± 0.0003 | 0.0461 | -6.9 % | tuned |
| M | T1 | ViT | p16g16 | 0.1336 ± 0.0820 | 0.0504 | -62.3 % | tuned |
| M | T1 | GNN | ms8 | 0.2156 ± 0.0008 | 0.1603 | -25.6 % | tuned |
| M | T3 | U-Net | w64 | 0.0276 ± 0.0010 | 0.0272 | -1.4 % | pre-tuning |
| M | T3 | FNO | w48 | 0.0630 ± 0.0020 | 0.0555 | -11.9 % | tuned |
| M | T4 | U-Net | w64 | 0.0035 ± 0.0001 | 0.0031 | -12.5 % | tuned |
| M | T4 | FNO | w48 | 0.0118 ± 0.0001 | 0.0110 | -6.5 % | tuned |
| M | T4 | ViT | p16g16 | 0.0134 ± 0.0024 | 0.0157 | +16.8 % | pre-tuning |
| M | T4 | GNN | ms8 | 0.0120 ± 0.0002 | 0.0129 | +8.0 % | pre-tuning |
| L | T1 | FNO | w48 | 0.0626 ± 0.0003 | 0.0600 | -4.1 % | tuned |
| L | T1 | GNN | ms8 | 0.3204 ± 0.0068 | 0.2693 | -15.9 % | tuned |
| L | T3 | FNO | w48 | 0.0863 ± 0.0028 | 0.0789 | -8.6 % | tuned |
| L | T4 | FNO | w48 | 0.0212 ± 0.0004 | 0.0206 | -2.7 % | tuned |
| L | T4 | GNN | ms8 | 0.0220 ± 0.0001 | 0.0202 | -8.3 % | tuned |

**Table B.5b. Test_id rel-L2, pre-tuning → tuned (mean ± std over three seeds), with the official choice of Table B.5a** [docs/tables/tuning_effect.md].

| task | tier | model | official | rel-L2 pre-tuning → tuned (Δ) | rel-L2 median pre-tuning → tuned |
|---|---|---|---|---|---|
| T1 | L | FNO | tuned | 0.361 ± 0.024 → 0.299 ± 0.012 (-17.3 %) | 0.364 → 0.297 |
| T1 | L | GNN | tuned | 1.067 ± 0.026 → 0.941 ± 0.160 (-11.8 %) | 1.075 → 0.925 |
| T1 | M | FNO | tuned | 0.248 ± 0.016 → 0.208 ± 0.003 (-16.1 %) | 0.244 → 0.209 |
| T1 | M | GNN | tuned | 0.849 ± 0.005 → 0.607 ± 0.027 (-28.5 %) | 0.851 → 0.600 |
| T1 | M | U-Net | tuned | 0.212 ± 0.023 → 0.187 ± 0.022 (-11.7 %) | 0.199 → 0.187 |
| T1 | M | ViT | tuned | 0.419 ± 0.123 → 0.306 ± 0.012 (-27.0 %) | 0.435 → 0.299 |
| T3 | L | FNO | tuned | 0.347 ± 0.004 → 0.323 ± 0.002 (-6.8 %) | 0.345 → 0.323 |
| T3 | M | FNO | tuned | 0.284 ± 0.006 → 0.255 ± 0.003 (-10.2 %) | 0.285 → 0.254 |
| T3 | M | U-Net | pre-tuning | 0.202 ± 0.006 → 0.192 ± 0.009 (-5.0 %) | 0.202 → 0.195 |
| T4 | L | FNO | tuned | 0.120 ± 0.001 → 0.116 ± 0.000 (-3.3 %) | 0.120 → 0.116 |
| T4 | L | GNN | tuned | 0.142 ± 0.001 → 0.142 ± 0.001 (+0.0 %) | 0.142 → 0.142 |
| T4 | M | FNO | tuned | 0.079 ± 0.001 → 0.073 ± 0.001 (-7.6 %) | 0.079 → 0.073 |
| T4 | M | GNN | pre-tuning | 0.099 ± 0.001 → 0.103 ± 0.001 (+4.7 %) | 0.099 → 0.103 |
| T4 | M | U-Net | tuned | 0.051 ± 0.000 → 0.042 ± 0.001 (-18.3 %) | 0.051 → 0.041 |
| T4 | M | ViT | pre-tuning | 0.094 ± 0.004 → 0.103 ± 0.001 (+8.8 %) | 0.093 → 0.103 |

The two cases where the validation rule keeps the pre-tuning configuration against a *better* test rel-L2 (U-Net T3 M, −5.0 %) or a *worse* one (ViT and GNN T4 M, +8.8 % and +4.7 %) show why the rule reads validation loss only [docs/tables/tuning_effect.md]. The candidate pass itself (one T1 seed per candidate at M and L) is in `docs/tables/tuning_full.md`.

### B.6 Solver acceleration, all rows [docs/tables/acceleration.md]

| task | tier | model | split | systems | iters zero → warm | iter reduction | time zero → warm (ms) | time reduction | warm-start residual | converged |
|---|---|---|---|---|---|---|---|---|---|---|
| T1V | L | fno | test_id | 1928 | 16 → 18 | -7.7 % | 517.9 → 580.5 | -7.5 % | 34.7 | 100.0 % |
| T1V | L | fno | test_ood | 1278 | 25 → 26 | -7.1 % | 860.1 → 930.0 | -7.3 % | 91.1 | 100.0 % |
| T1V | M | fno | test_id | 4823 | 12 → 12 | +0.0 % | 102.5 → 105.7 | -4.5 % | 22.2 | 100.0 % |
| T1V | M | fno | test_ood | 3225 | 16 → 16 | +0.0 % | 141.3 → 143.4 | -1.8 % | 22.2 | 100.0 % |
| T1V | S | fno | test_id | 9850 | 9 → 10 | +0.0 % | 23.2 → 23.4 | -0.8 % | 11 | 100.0 % |
| T1V | S | fno | test_ood | 6460 | 11 → 12 | +0.0 % | 30.2 → 30.7 | -0.2 % | 11.4 | 100.0 % |
| T3 | L | fno | test_id | 1928 | 17 → 18 | -5.6 % | 757.0 → 808.7 | -6.2 % | 1.62e+03 | 100.0 % |
| T3 | L | fno | test_ood | 1275 | 23 → 24 | -4.2 % | 1159.8 → 1221.1 | -4.4 % | 1.89e+03 | 100.0 % |
| T3 | M | fno | test_id | 4823 | 12 → 13 | +0.0 % | 119.9 → 120.9 | -0.5 % | 559 | 100.0 % |
| T3 | M | fno | test_ood | 3222 | 16 → 16 | +0.0 % | 167.2 → 169.3 | -0.5 % | 653 | 100.0 % |
| T3 | S | fno | test_id | 9850 | 10 → 10 | +0.0 % | 19.3 → 19.7 | -0.1 % | 181 | 100.0 % |
| T3 | S | fno | test_ood | 6460 | 11 → 11 | +0.0 % | 25.4 → 25.6 | +0.0 % | 212 | 100.0 % |
| T1V | L | unet | test_id | 1928 | 16 → 17 | -6.7 % | 739.5 → 821.4 | -7.4 % | 22.5 | 100.0 % |
| T1V | L | unet | test_ood | 1278 | 25 → 26 | -5.6 % | 1248.0 → 1320.7 | -5.7 % | 22.5 | 100.0 % |
| T1V | M | unet | test_id | 4823 | 12 → 12 | -5.6 % | 86.9 → 91.6 | -6.5 % | 19.4 | 100.0 % |
| T1V | M | unet | test_ood | 3225 | 16 → 17 | -4.8 % | 129.4 → 137.6 | -5.7 % | 17.6 | 100.0 % |
| T1V | S | unet | test_id | 9850 | 9 → 9 | +0.0 % | 14.4 → 14.4 | +0.0 % | 5.06 | 100.0 % |
| T1V | S | unet | test_ood | 6460 | 11 → 11 | +0.0 % | 19.2 → 19.3 | +0.1 % | 4.69 | 100.0 % |
| T3 | L | unet | test_id | 1928 | 17 → 19 | -9.1 % | 763.2 → 858.6 | -9.5 % | 3.32e+03 | 100.0 % |
| T3 | L | unet | test_ood | 1275 | 23 → 25 | -8.8 % | 1164.0 → 1281.7 | -8.8 % | 3.87e+03 | 100.0 % |
| T3 | M | unet | test_id | 4823 | 12 → 13 | -2.9 % | 99.9 → 102.3 | -1.0 % | 580 | 100.0 % |
| T3 | M | unet | test_ood | 3222 | 16 → 16 | -4.5 % | 140.7 → 144.5 | -4.5 % | 783 | 100.0 % |
| T3 | S | unet | test_id | 9850 | 10 → 10 | +0.0 % | 19.3 → 19.1 | +0.1 % | 82.5 | 100.0 % |
| T3 | S | unet | test_ood | 6460 | 11 → 11 | +0.0 % | 25.4 → 24.5 | +0.1 % | 109 | 100.0 % |

Medians over systems; "reduction" is the median of 1 − warm/zero per system; the warm-start residual is the relative Kirchhoff residual of the predicted voltage relative to the zero start (= 1). CPU, Julia, the same preconditioner, matrix and tolerance as the stored baselines [docs/tables/acceleration.md].

### B.7 Data scaling, all rows [paper/tables/wp4_data_scaling.md]

| model | n train | regime | rel-L2 | MAE log10 | top-5 % IoU | epochs | train GPU-h |
|---|---|---|---|---|---|---|---|
| FNO | 1,000 | ep30 | 0.575 | 0.255 | 0.416 | 30 | 0.15 |
| FNO | 1,000 | steps | 0.438 | 0.243 | 0.462 | 39 | 0.19 |
| FNO | 5,000 | ep30 | 0.357 | 0.180 | 0.577 | 30 | 0.22 |
| FNO | 5,000 | steps | 0.298 | 0.173 | 0.597 | 54 | 0.36 |
| FNO | 20,000 | ep30 | 0.243 | 0.137 | 0.665 | 30 | 0.41 |
| FNO | 20,000 | steps | 0.246 | 0.138 | 0.664 | 36 | 0.48 |
| FNO | 61,577 | full | 0.198 | 0.112 | 0.719 | 29 | 0.95 |
| U-Net | 1,000 | ep30 | 0.496 | 0.213 | 0.484 | 30 | 0.17 |
| U-Net | 1,000 | steps | 0.368 | 0.162 | 0.607 | 88 | 0.35 |
| U-Net | 5,000 | ep30 | 0.316 | 0.155 | 0.604 | 30 | 0.15 |
| U-Net | 5,000 | steps | 0.139 | 0.076 | 0.818 | 143 | 0.76 |
| U-Net | 20,000 | ep30 | 0.188 | 0.072 | 0.771 | 30 | 0.31 |
| U-Net | 20,000 | steps | 0.103 | 0.042 | 0.877 | 94 | 0.94 |
| U-Net | 61,577 | full | 0.111 | 0.042 | 0.857 | 30 | 0.86 |

## C Omniscape fidelity: the block rule and its measurement [docs/t4_fidelity.md]

The block rule (block = largest odd integer ≤ radius/10) came from a 3-sample-per-cell study against the exact block-1 map: block 3 at S deviated by 4.49 % mean / 7.60 % max relative L2 and block 5 at M by 2.00 % / 2.45 %, while coarsening XL 17→33 changed the cumulative current by 2.47 % / 2.93 % and XXL 33→65 by 9.46 % / 11.85 % (both rejected); block 1 was 6.4× (S) and 22.6× (M) more expensive at those anchors [docs/t4_fidelity.md]. The ≈ 1 % target was an extrapolation and proved optimistic: the production M block deviates from the exact map by 3.1 % relative L2 on average on 200 synthetic test/OOD landscapes (median 2.8 %, top-5 % IoU 0.95, pinch-point recall 0.95), and the full 1 000-sample M reference gives mean rel-L2 0.029 (median 0.027) with 4.7 % of samples above 5 % (11 % of synthetic, 1.4 % of real tiles; real tiles never above 8 %) [docs/t4_fidelity.md]. At L (block 5, 60 samples) the mean is 0.028 (max 0.058; 2 of 60 above 5 %); block 1 costs 6.7× (M) and 22× (L) the production solve [docs/t4_fidelity.md]. Omniscape geometry per tier — radius 16 / 32 / 64 / 128 / 256 px (1.6 / 3.2 / 12.8 / 64 / 256 km), block 1 / 3 / 5 / 11 / 25 — and the per-split reference-subset rows (block 1, production block, coarser blocks with and without artefact correction) are in `docs/t4_fidelity.md` and `paper/tables/t4_pareto_{M,L}.md`. T4 rows carry no single residual; each window solve is bounded by Circuitscape's enforced relative residual ≤ 1e-4, with a rescue path for the contrast-10⁶ solves that the stock package aborts [docs/dataset_card.md; docs/t4_fidelity.md].

## D Precision pass [docs/tables/precision_pass.md]

| tier | rows re-solved | of which cg+amg → cholmod | residual after: p50 / p90 / p99 / max | rows > 1e-9 (recorded) | rows > 1e-6 (flagged) |
|---|---|---|---|---|---|
| S | 68,008 | 9 | 2.9e-13 / 3.4e-11 / 1.6e-09 / 5.0e-07 | 1,013 | 0 |
| M | 37,639 | 14 | 9.1e-13 / 1.9e-10 / 5.2e-09 / 1.4e-06 | 1,136 | 4 |
| L | 18,691 | 110 | 6.8e-12 / 4.9e-10 / 1.4e-08 / 1.5e-05 | 1,014 | 9 |
| XL | 4,774 | 47 | 6.9e-11 / 1.3e-09 / 4.3e-08 / 6.6e-06 | 551 | 5 |
| XXL | 610 | 9 | 2.7e-10 / 4.3e-09 / 2.0e-07 / 4.0e-05 | 147 | 2 |
| total | 129,722 | 189 | | 3,861 | 20 |

Rows above 1e-6 after CHOLMOD plus up to three refinement steps (and LDLᵀ / AMG-PCG as last resorts) are all synthetic landscapes at contrast ≥ 10⁴; they carry `residual_high`, `qc_pass = false`, and their samples are excluded from the split lists. Provenance per re-solved row: `qc_flags` contains `resolved_post_run`, `solver_original` holds the production solver when it changed, and `solver_stats.resolved_post_run` keeps the per-pair residuals and methods [docs/tables/precision_pass.md]. Generation ran from 2026-09-16 to 2026-09-22 followed by a 29 h precision pass, 16 552 core-hours in all (generation 14 379, precision pass 1 249, audits 30, auxiliary sets and probes 893); the eleven operational incidents and their resolutions are in the post-mortem [docs/generation_postmortem.md].

## E Licences and attributions [docs/licenses.md]

| layer | version | licence | derived rasters redistributed |
|---|---|---|---|
| ESA WorldCover land cover, 10 m | 2021 v200 | CC BY 4.0 | class codes |
| Copernicus DEM GLO-30 | 2021 release (© DLR 2010-2014, © Airbus 2014-2018) | Copernicus licence, Art. 4 rights of use, Art. 6 notices reproduced | elevation, slope |
| GRIP4 global roads | v4, 2018 | CC0 by the publisher; CC BY 4.0 in secondary catalogues (attributed as CC BY 4.0) | distance-to-road only |
| HydroRIVERS | v1.0 | CC BY 4.0 | distance-to-river only |
| gHM global Human Modification | v1, 1 km | CC BY 4.0 | gHM |
| RESOLVE Ecoregions 2017 | 2017 | CC BY 4.0 | stratification only (biome / realm) |
| Eurac Alps permeability | 2022 | CC BY 4.0 | published resistance tiles |
| Hawaiian gallinule resistance | 2020 | CC0 1.0 | published resistance tiles |
| Northern raccoon Europe maps | 2025 | CC BY 4.0 | published resistance tiles |

WDPA protected-area polygons (restrictive licence) and OpenStreetMap (ODbL share-alike) are not used [docs/licenses.md]. Every file in the source manifest (21 entries, 5.45 GB) has a recorded licence and sha256, enforced by `tests/test_licenses.py` [docs/licenses.md]. The dataset is released under CC BY 4.0; code and the solver wrapper under MIT; Circuitscape.jl 5.17.1 and Omniscape.jl 0.6.2 are MIT [docs/dataset_card.md]. The full attribution block and the Copernicus notices are reproduced in the dataset card and `LICENSE-DATA`.

## F Evaluation CLI and prediction format [scripts/evaluate.py; ampscape/eval/harness.py; docs/evaluation.md]

`python scripts/evaluate.py --predictions <dir> --split <name>[,<name>] [--root <data root> --tier <tier> --subset <name> --out <dir> --acceleration --t4-reference <aux build> --t4-blocks <builds> --workers <n>]` writes `results.json` and `results.md`. `<dir>/predictions.h5` holds one group per sample and one subgroup per configuration with `cum_current` (float32 H×W; T1, T1W, T1R, T4), optional `voltage` (float32 H×W or P×H×W), optional `pairwise_current` (P×H×W), `reff` (float64 K×K; T2), `current` (float32 H×W; T3) and optional `flow_potential` / `normalized` (T4), plus a group attribute `inference_time_s` per configuration (wall clock including preprocessing); `<dir>/meta.json` records model, task, tier, split, seed and notes. Only `qc_pass` rows of the requested splits are evaluated, samples absent from the file are skipped with the row count reported, processing is deterministic in sorted order, an oracle scores 0 error / 1.0 on every similarity metric and an all-zero predictor scores rel-L2 = 1 and top-q IoU = 0 [docs/evaluation.md]. The leaderboard entry schema, the validator and the submission procedure are in `docs/submission.md`.

## G Dataset statistics [docs/tables/dataset_statistics.md]

Contrast (log10, p10 / p50 / p90): synthetic 1.00 / 3.00 / 4.00 at every tier with a maximum of 1e+06; real 0.76 / 1.79 / 2.79 at S rising to 2.00 / 3.00 / 3.00 at XXL with a maximum of 1e+03 [docs/tables/dataset_statistics.md]. Real landscapes cover 14 RESOLVE biomes and 7 realms (largest: Palearctic 16,760 landscapes, Neotropic 15,405, Nearctic 12,005, Australasia 10,470) [docs/tables/dataset_statistics.md]. NoData fraction of real tiles: p50 0.002, p90 0.159, max 0.896 [docs/tables/dataset_statistics.md]. Storage per tier and task group, solve-time distributions per configuration and the figures `docs/figures/dataset_stats_{contrast,biome_realm,nodata,solve_times,storage}.png` are in `docs/tables/dataset_statistics.md`.
