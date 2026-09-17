# Status history

Newest entries at the bottom. Each entry mirrors `docs/status/latest.md` at the time of a stop.

---

# Status — 2026-09-05 (end of Phase 1)

Phase 1 complete (cluster inspected, toolchain isolated on scratch, scaffold, solver smoke test, prior art, task spec).
Blockers raised: 300 GB scratch vs v1.0 size; NeurIPS 2026 deadline passed; spec open questions (per-pair maps, CRS, OSM, Omniscape r/b, HF org).
Report: `docs/phase_01_report.md`.

---

# Status — 2026-09-05 (end of Phase 2)

**Phase 2 complete; waiting for confirmation to start Phase 3.**

- Synthetic generators done (7 families + overlays + NoData + contrast ladder), 38 tests, gallery in `docs/figures/synthetic_gallery.png`.
- Real-tile pipeline done; pilot extracted **60 tiles, 14 biomes, 5 realms** at tier S (128 px @ 100 m, local UTM), manifest + checksums, quicklooks. Map: `docs/figures/pilot_tiles_map.png`.
- Sources verified and downloaded (2.76 GB, sha256 manifest): WorldCover 2021 v200, Copernicus DEM GLO-30/90 (windowed COG reads), GRIP4 (regions 1,2,3,5,7), HydroRIVERS (5 regions), gHM v1, RESOLVE 2017. Licences in `docs/licenses.md`.
- Owner decisions applied (CHOLMOD, avg-conductance, UTM, GRIP4, K ≤ 4, Xirro, NeurIPS 2027, Croissant); storage plan in `docs/compute_env.md` §10.

**Decisions needed from the owner**
1. Hugging Face storage: free private quota is 100 GB; v1.0 ≈ 215 GB. Options: PRO account, make repo public, or cap v1.0 ≈ 90 GB while private.
2. Approve downloading the remaining GRIP4 regions 4 and 6 + HydroRIVERS as/si/ar/gr (~2.3 GB; cumulative sources ≈ 5.1 GB, crossing the 5 GB gate) for full-scale global tiling.

Full report: `docs/phase_02_report.md`.

---

# Status — 2026-09-05 (end of Phase 3)

**Phase 3 complete; waiting for confirmation to start Phase 4.**

- Resistance tables done: `generic_hm`, `large_mammal`, `amphibian`, `forest_bird`, `random_lm_20260905` (YAML + pydantic schema + citations). Values are AmpScape's own, literature-ordered.
- Applied to all 60 pilot tiles: 300 rasters, all in [1, r_max], masks consistent, 11 tests green (70 total in the repo). Gallery: `docs/figures/pilot_resistance_gallery.png`.
- Owner decisions applied: HF storage deferred to Phase 5; download gate = single > 5 GB or cumulative > 20 GB; full GRIP4 + HydroRIVERS set downloaded (4.87 GB cumulative, sha256 manifest); neighbour-rule wording corrected (average conductance **is** the Circuitscape default); GRIP4/OSM wording fixed; WDPA not downloaded (habitat-patch focal regions planned instead).

**Nothing blocking.** One note: `forest_bird` saturates on three Andean tiles above 3000 m (by design; will be QC-flagged in Phase 5).

Full report: `docs/phase_03_report.md`.

---

# Status — 2026-09-05 (end of Phase 4)

**Phase 4 complete; waiting for confirmation to start Phase 5 (solver pipeline + mini run).**

- Focal-node / source generators done (`ampscape/sources`): points with per-node mixed placement, wall-to-wall strips, habitat-patch regions, T3 source/ground, T4 Omniscape sources; every configuration checked on an **exact reconstruction of the Circuitscape graph** (unit-tested against the source formulas).
- Config with documented defaults: `configs/tasks/sources_default.yaml` (sha256 recorded per sample); tier scaling built in.
- Pilot build: **1865 configurations, all connected**; anywhere-placement fraction 0.312 (target 0.3); regions on 23/60 tiles. Gallery: `docs/figures/pilot_sources_gallery.png`.
- Verified in Circuitscape that repeated point-raster labels are one short-circuited region (T1W design settled).
- Tests: 21 new, 91 passing overall.

**Nothing blocking.** Carried forward: `frac_at_rmax` QC flag, Omniscape r/b timing, HF storage decision (all Phase 5).

Full report: `docs/phase_04_report.md`.

---

# Status — 2026-09-05 (end of Phase 5, MANDATORY GATE)

**Phase 5 complete; stopped at the gate. Nothing will be scaled until the owner decides on §9 of `docs/phase_05_report.md`.**

- Solver wrapper (`AmpScapeSolve.jl`) + Python driver + Slurm array template done; smoke (5), mini (250 samples, 1,270 configs, **100 % QC pass**), probes M/L/XL (5 each) and XXL (1) all solved with CHOLMOD.
- **Reference solver validated:** CHOLMOD vs CG+AMG on 10 samples agree to 6e-7 (cum current), 3e-8 (Reff), 4e-6 (T3), 4e-7 (T4); CHOLMOD residuals 1e-11–1e-14 vs 1e-6–3e-5 for CG; both bitwise deterministic single-threaded; CG+AMG aborted an Omniscape solve on a contrast-10⁴ landscape → CHOLMOD is the reference for T4 too.
- **Cost driver = Omniscape (T4)**: 6.2 s (S), 48 s (M), 178 s (L), 13 min (XL, block 17), 74 min (XXL, block 33) per solve; everything else is ≤ 13 s up to XL. Adopted XL block 33 / XXL block 65 (≈ 4× cheaper).
- **Budget:** brief's ladder ≈ **7,400 CPU-hours, 451 GB**. 500 CPU-hours buys ≈ 26.5k S / 1.9k M / 300 L / 200 XL / 15 XXL at 4 cores per job (43 GB), or ≈ 106k S / 7.8k M / 1.3k L / 600 XL / 60 XXL at 1 core per job (167 GB, needs a one-shard check). Storage: 0.93 MB (S) → 139 MB (XXL) per sample.
- QC exclusions: 0 hard failures; 3 configurations of one contrast-10⁴ landscape flagged `rmax_saturated` (kept in index, excluded from train/val). Residual threshold set to 1e-6 (double-precision floor ≈ 1e-8 at contrast 10⁴).
- Incident: a stale shared Julia cache across CPU types caused a > 20 min precompile hang; fixed with a portable `JULIA_CPU_TARGET` and login-node precompile in `generate.py submit`.

**Owner decisions needed:** (1) ladder/budget and whether T4 is solved on a subset; 1-core jobs for S/M; (2) HF storage plan; (3) confirm Omniscape XL r128/b33, XXL r256/b65; (4) the correct `HF_ORG` (placeholder "<correct name>" was not filled in).

Full report: `docs/phase_05_report.md`.

---

# Status — 2026-09-05 (dataset plan written; STOPPED, no v1.0 generation launched)

**`docs/dataset_plan.md` is complete.** Compute-agnostic v1.0 design; ICE is pipeline/mini/dev only.

- **Coverage:** 174,400 landscapes (S 100k, M 50k, L 20k, XL 4k, XXL 400; 60 % synthetic / 40 % real; 13,952 real tiles × 5 tables incl. one seeded random table per tile), **902,904 solves** across T1/T2/T1W/T1R/T3/T4 (+3,000 4-neighbour ablation solves). Every family × table × source configuration × task × tier cell is non-zero. Named `hard` stratum = 20 % of synthetic (contrast 10⁴, r_max-saturated, narrow corridors, large NoData).
- **Omniscape block size (fidelity study, 12 paired solves):** coarsening rejected (XL 17→33: 2.5–2.9 % rel. L2; XXL 33→65: 5.9–11.9 %); anchors vs the exact block-1 map: S b3 = 4.5 %, M b5 = 2.0 %. **Adopted rule: block = largest odd ≤ radius/10** (S 1, M 3, L 5, XL 11, XXL 25), the setting that stays within ≈ 1 % of exact by extrapolation; the Phase-5 blocks (S 3 … XXL 33) are kept as a priced option.
- **Cost (measured, CHOLMOD, single-threaded):** recommended ladder ≈ **11,309 CPU-hours, ≈ 812 GB** with the fidelity blocks (≈ 3,981 CPU-h with the Phase-5 blocks); brief's baseline ladder ≈ 7,586 CPU-h / 552 GB. Wall-clock ≈ 4.7 days at 100 cores, 0.9 d at 500, 0.5 d at 1,000. T4 > 90 % of compute; XXL needs 9.5 GB per job.
- **Recommended deviations from the brief:** L 10k→20k, XL 2k→4k, XXL 200→400 (per-cell OOD-scale statistics); named hard-case stratum; random table per tile; ≥ 150 real S tiles per biome; `forest_bird` as the held-out table; 2 biomes + 1 realm as held-out regions; Omniscape b/r ≤ 0.10.
- **Portability:** `configs/cluster/{ice,template}.yaml`, profile-aware `generate.py submit`, `docs/run_guide.md`; requirements: Julia 1.11.3, depot on scratch, `JULIA_CPU_TARGET`, Python from `uv.lock`, no network in jobs.
- **Gaps (Phase 6):** `narrow_corridor` generator, NoData prior extension, real tiles at M–XXL, per-tier seed ranges / cross-tier tile exclusion, per-tile random table, HDF5 schema + splits + sync tool, 4-neighbour duplicates in the planner; mini was generated with the Phase-5 blocks and would be regenerated under the fidelity rule.

Phase 5 decisions applied (CHOLMOD all tasks, residual 1e-6, T4 everywhere, HF_ORG = Xirro, HF storage deferred).

---

# Status — 2026-09-06 (end of Phase 6)

**Phase 6 complete; waiting for confirmation to start Phase 7.** Rename to AmpScape pushed (repo `Xyrro/AmpScape`).

- Schema v0.2 + validator (`ampscape/io/schema.py`, `docs/schema.md`), Zarr export, streaming sync (validate → upload → verify → delete; dry-run default, pushes gated).
- Splits: 20° macro-cells shared across tiers (5° rejected: footprint cascade turned the globe into test), seed-family for synthetic, holdouts/OOD flags, XL 25 % train/val; cross-tier overlap test passes with 0 overlaps.
- Mini regenerated under the radius/10 rule (S block 1): 250 samples, 1 270 configs, 232 MB, 100 % QC pass, all shards schema-valid; T4 53.7 s/solve at S (8.7× block 3). Old mini kept as `mini_phase5blocks`.
- Plan amendments C1–C5 applied to `configs/datasets/v1_0.yaml` and `docs/dataset_plan.md`; litter of empty Omniscape project dirs fixed and removed.
- Tests: 106 passing (8 new). Nothing blocking.

Full report: `docs/phase_06_report.md`.

---

# Status — 2026-09-06 (Phase 7 code complete; HF push blocked on login)

- Macro-cell check: previous 20° lon/lat grid could not hold XXL tiles anywhere (0 % fit); adopted equal-width 20° grid + XXL footprints as regions; placeability uniform in latitude, 0 geometric cross-tier overlaps.
- Phase 7: `AmpScapeDataset` + `load_from_hub`, HF layout by tier × task group (any tier/task downloads alone), nested mini/core/full subsets, Croissant 1.0 + RAI (validated, 0 errors), push script with verified uploads, dataset card draft with the honest framing. Mini staged: 38 files, 300 MB. Tests: 110 passing.
- ICE feasibility: v1.0 (11 300 core-h) would finish in ≈ 1–5 days on ICE by the limits alone (`docs/compute_env.md` §8.2); policy and the 300 GB scratch are the real constraints.
- Paper note recorded: mini's real tiles skew to held-out regions (pilot artifact).

**Blocked:** the login node has no Hugging Face token (`hf auth whoami` → Not logged in). After `hf auth login`, the real push, the download-alone check and the sync delete test run.

---

# Status — 2026-09-07 (external-review items done; Phase 7 complete; HF end-to-end test passed)

- **Contrast ladder to 10⁶:** all CHOLMOD residuals at 10⁵ and 10⁶ (tiers S and XXL; T1, T1W, T3) below 1e-6. The apparent XXL wall-to-wall failures were a residual-normalisation inconsistency for short-circuited regions (now the collapsed-system residual everywhere). Iterative refinement (trigger > 1e-8, our own CHOLMOD factorisation, maps regenerated) implemented and recorded per sample; it fired once (2.75e-8 → 6.6e-9, +17 s). Uniform threshold 1e-6 kept.
- **Acceleration track:** explicit AMG-PCG baseline in `SolveStats.cg_baseline` (Krylov mis-preconditioning found and removed), recorded only for test/OOD samples (plan-time splits; XXL_test profile, ~14.5 GB); mini carries baselines for all T3 and K ≤ 4 T1 solves.
- **Solver cross-check re-run:** PCG vs CHOLMOD 1.9e-9 (current), 2e-11 (Reff); Circuitscape cg+amg vs CHOLMOD 6e-7 / 3e-9; **no stored output anywhere came from a CG path** (2 660 configurations checked). Phase 5 report bannered.
- **HF end-to-end test:** mini pushed to private `Xirro/AmpScape` (21 shards, sha256-verified, 0 mismatches); `load_from_hub("T4","S")` fetched one task group alone (22 files, 65 MB, 7 s); sync validate→upload→verify→delete exercised on the smoke build (test files then removed from the repo). Publication route recorded: v1.0 assembled on a ≥ 1 TB-scratch cluster and published in one public push; streaming sync kept as fallback.
- **Published resistance rasters:** Eurac Alps (CC BY 4.0) and raccoon Europe (CC BY 4.0) downloaded and in the manifest (sources 5.15 GB); **Dryad blocks scripted downloads** (401/403) — the Hawaiian gallinule archive needs a browser download by the owner. `test_ood_published` planned for Phase 9.
- log10(C + ε·max C) transform, SSIM/PSNR secondary, unvalidated-threshold caveat, survey doc: done. Tests: 111 passing.

**Needs owner:** browser download of Dryad `f_wet_negbin.zip` (10.5061/dryad.p90b87p) into `data/sources/`; go-ahead for Phase 8.

---

# Status — 2026-09-07 (end of Phase 8)

**Phase 8 complete; waiting for confirmation to start Phase 9.**

- `docs/licenses.md` reconciled with all 21 manifest entries (5.45 GB) incl. the three published resistance rasters (gallinule archive registered from the owner's manual download); verification log; `CITATION.cff` complete; redistribution terms in the dataset card; licence consistency test.
- Unverifiable: the exact GRIP4 licence statement (CC0 vs CC BY 4.0 vs one ODbL listing) — attributed as CC BY 4.0, derived rasters only. Manual check recommended before publication for WorldCover, HydroRIVERS, RESOLVE (licences read from site text via search).
- Refinement sentence added to the task spec and the dataset card. Tests: 112 passing.

Full report: `docs/phase_08_report.md`.

---

# Status — 2026-09-13 (end of Phase 9)

**Phase 9 complete; waiting for confirmation to start Phase 10 (learned baselines).**

- Metrics package (`ampscape/metrics`: pixel in log10-ε space, domain, Reff, physics, efficiency, solver acceleration) with hand-computed unit tests; `scripts/evaluate.py` + documented predictions format (`docs/evaluation.md`), deterministic, works on any subset.
- `test_ood_published` built and finalised: 45 S tiles (Eurac Alps, Hawaiian gallinule) + 1 XXL tile (raccoon Europe), resistance as given, geometric-mean resampling rule, provenance in every tile; 46 samples / 230 configs, 100 % QC, CHOLMOD, CG baselines; XXL solve 3 h (Omniscape 2.9 h, 9.6 GB).
- Coarsen-×4 → CHOLMOD → upsample baseline run through `evaluate.py` on the mini test splits (T1 mae_log10eps 0.093 / rel-L2 0.43 / top-5 IoU 0.59; T3 0.089 / 0.26 / 0.59; T4 0.47 / 0.73 / 0.57; speed-up 2.4–4.7×, Omniscape ≈ 60×) and on `test_ood_published`; results tables in `docs/phase_09_report.md`. Getting a physically comparable baseline needed three documented scale rules (1/f current scaling, focal in-fill, ground-wins T3 blocks) — all in `DECISIONS.md`.
- Findings: a coarse-solve warm start does not accelerate PCG (S: 11 → 10 iterations; XXL: worse); Circuitscape leaves a node that is both source and ground ungrounded; `refine_voltage!` now survives an ungrounded component.
- Tests: 122 passing. No downloads, no HF pushes; ICE usage well under the gates.

Full report: `docs/phase_09_report.md`.

---

# Status — 2026-09-14 (dev subset + Phase 10)

**Dev subset built, Phase 10 complete; waiting for owner decisions** (split rules, GPU sizing) before Phase 11.

- **Dev subset** `data/dev`: 3 000 S + 500 M landscapes as a true prefix of v1.0 (tier-disjoint synthetic seeds with the
  hard-case stratum, prefix-extracted stratified real tiles × 5 tables incl. per-tile random tables), all tasks, CHOLMOD,
  100 % / 99.9 % QC, 66 CPU-h, 4.9 GB; splits by the v1.0 rule (`docs/dev_subset.md`).
- **Two split findings need a decision** (labels only): cell-level biome hold-out made 52 % of real S tiles OOD (now
  tile-level by default); the 32 v1.0 XXL parent footprints merge into 13 continental regions covering 72 % of S tiles
  (parent regions disabled for dev). Both are config switches in `configs/datasets/v1_0.yaml`.
- **Learned baselines** (U-Net, FNO, ViT-based, grid-GNN; shared inputs / log10-ε targets / masked MSE; `scripts/train.py`)
  trained on T1 and T4 (all four) and T3 (U-Net, FNO), single seed, evaluated through `evaluate.py` on test_id,
  test_ood, ood_region and test_ood_published alongside the coarsen baseline (`docs/tables/baselines_dev.md`).
  test_id rel-L2: U-Net T1 0.25 / T3 0.30 / T4 0.09; U-Net is the only model beating the non-learned baseline on T1,
  FNO and GNN fail on T1 (≥ 1.0), all models collapse on the XXL published tile (scale transfer is the hard axis).
- **No task is too easy**: best test_id rel-L2 0.093 (T4), above the 0.05 flag.
- **GPU**: 1.44 GPU-h for the ten dev runs (1.8 GPU-h for every GPU job of the phase); v1.0 extrapolation 365 GPU-h
  (optimistic epoch rule) to 933 GPU-h (30 epochs per tier), three seeds, S–XL, L40S — GNN is half of it.
- Environment: torch pinned to the cu126 wheels (ICE driver is CUDA 12.9); one faulty-GPU node killed eight jobs (resubmitted).
- Tests: 129 passing.

Full report: `docs/phase_10_report.md`.

---

# Status — 2026-09-15 (v1.0 freeze checklist)

**Checklist a–f done except the reproducibility verdict (b, running); waiting for approval to launch tier S.**

| item | result |
|---|---|
| a. pipeline freeze | no pending change affects stored outputs (the tuning pass touched models only); tag **`v1.0-pipeline` = `8491bbe`**, pushed; `pipeline_tag` + `pipeline_git_sha` recorded in every shard root, sample meta and index row |
| b. reproducibility | four dev shards regenerated from the tagged tree (S shards 0 synthetic / 18 real, M shards 0 / 8; 2.3–3.7 h each): **M 0, M 8 and S 0 are bitwise identical in every dataset** (1 239 / 1 440 / 3 107 datasets; only timing, host and provenance attributes differ). **S 18 is not**: 392 of 3 354 datasets differ in the last bits (max relative difference 1.2e-9; Reff, voltages, pair maps) with matching residual-level stats — it is the one shard whose dev solve ran on a different CPU node (Gold 6226 vs the node used for the other three), i.e. CHOLMOD/BLAS results are bitwise reproducible on identical hardware and agree to ~1e-9 relative across ICE node types. Per the rule, and independently because the C2 land-cover rule changed the real S tiles, **the dev subset is regenerated as part of v1.0 rather than reused**; the datasheet states reproducibility as bitwise on identical hardware, ≤ 1e-9 relative across CPU types |
| c. v1.0 real tiles | `data/tiles/v1.0`: **S 8 000 / M 4 000 / L 1 600 / XL 320 / XXL 32 + 6 strict** accepted (71 / 36 / 10 / 5 / 1 rejected, prefix mode, lists extended by 5 % with the prefix verified identical), 6.5 h of Slurm extraction with the new decimated reader (XXL 7.6 min per tile). Strata: 166 biome × realm × gHM-tercile strata at S (median 66 tiles); **short of the plan's floor of 150 S tiles per biome: Mangroves 128 (an OOD-only biome) and RESOLVE "N/A" polygons 28** (28 S / 14 M / 14 L / 1 XL tiles carry biome "N/A"; flagged, kept). Every other biome ≥ 244 at S; realms Palearctic 1 936 … Oceania 15. Resistance rasters (5 per tile) being built (job 5786761) |
| d. Hub | `Xirro/AmpScape` is **public** with the in-progress notice at the top of the card; the 39 dev-era files (mini shards, index, splits, stats, croissant) were removed first — the repo holds only README and .gitattributes until the first S shards land |
| e. streaming sync | `sync_shards.py --live`: validate → split by task group → upload → verify Hub sha256 → `.uploaded` → delete final + staged files, index rows/markers/quicklooks kept; `--publish-index` re-publishes `index/<tier>.parquet` + split lists; a shard failing verification twice gets `.upload_failed` and the loop stops; `generate.py submit` refuses above **200 GB** under `data/` (`limits.scratch_pause_gb`) |
| f. runbook | `docs/generation_runbook.md`: order S → M → L → XL → XXL, shard sizes for ≈ 3.2 h shards (S 200, M 100, L 20, XL 6 @ 4 cpus, XXL 1 @ 8 cpus), arrays ≤ 400 tasks under the 512-core cap, ≈ 11 300 core-hours incl. overhead, ≈ 840 GB streamed; resume procedure; `scripts/generation_log.py` appends the daily summary to `docs/status/generation_log.md`; stop rule (QC fail > 1 % in a tier or a shard failing upload twice) |

Also done from the same message:
- Decisions 1, 2, 4 and the generation decision recorded (`DECISIONS.md`); XXL / `test_ood_scale` disclosure in the task spec and the card; `test_ood_scale_strict` = 6 XXL tiles sampled inside test_id cells only (3 cells qualify) with a geometric zero-overlap check at finalize.
- **Tuning pass (2.69 GPU-h, 16 runs, `docs/tables/tuning_dev.md`)**: FNO recovers on T1 with 64 modes + the distance-to-source channel (rel-L2 1.14 → 0.34); the GNN improves with a 4×-coarsened graph level + distance (1.04 → 0.69) but stays behind the U-Net; the wide U-Net and patch-2 ViT are within single-seed noise; the distance channel does not help the convolutional models. **Frozen official configs** (`ampscape.models.OFFICIAL`): U-Net base, FNO m64+dist, ViT base, GNN multi-scale+dist. Cumulative GPU use this phase 4.5 h of the 20-h gate. GPU request noted at 1 000 GPU-h in `docs/tables/gpu_budget.md`.
- Found and fixed on the way: the macro-cell split depended on which cells held tiles (now frozen for the whole grid, `configs/splits/cell_assignment_v1.json`, 70 land cells 56/7/7); the tile reader read full-resolution windows (XXL impossible) — now decimated from COG overviews with the C2 rules and per-channel provenance; DEM gaps counted over land only; per-tier tile manifests for concurrent extraction.
- Consequence for the dev subset: S land cover now follows the C2 majority rule (was nearest), so the **real** half of dev is not bitwise reproducible and is regenerated as part of v1.0 (owner's fallback); the synthetic half is.

Tests: 129 passing. Next on approval: `plan_v1.py --tier S --n 100000 --out data/v1/S --shard-size 200`, prepare, submit in two arrays (400 + 100), start `sync_loop.sh`; report when the first 10 % of S shards are validated and on the Hub; Phase 11 starts once S is running.

---

# Status — 2026-09-16 (tier S generation running; quota incident fixed)

- **Tier S**: 500 / 500 shards solved, finalized and validated (QC fail 0.000 %); **153 uploaded and verified** on the public
  `Xirro/AmpScape` at 16:46Z (50th shard at 16:00Z), 347 finals waiting; upload rate ≈ 125 shards/h after the fix
  (one Hub commit per shard) → S fully on the Hub in ≈ 3 h. Core-hours used: 1 686 (solves + prepare + finalize +
  re-finalize). GB on Hub (`data/S/`): 30.4. Scratch: 199 GB of 300 (was 300/300).
- **Incident**: all 500 S shards ran at once; finalize ran in a separate array; the sync deleted only the final after
  upload, so raw intermediates (≈ 245 MB/shard) + finals (≈ 130 MB/shard) filled the 300 GB quota at 11:26Z; the split
  of shard 12 was truncated and retried every 15 min; 149 finals written after that point were truncated too.
- **Fixes (owner items 1–5)**: partial staging files removed; 83.6 GB of raw inputs/outputs of validated shards deleted,
  the 149 truncated finals deleted and re-finalized from their intact outputs (10 Slurm tasks, 0 QC failures);
  sync rewritten (per-shard temporary split always removed, one commit per shard, sha256 verified per file, attempt
  counter with `.upload_failed` after two consecutive failures, unreadable finals marked `.invalid` and skipped);
  finalize deletes raw intermediates after a validated write (inside the array task for all further tiers);
  generation log fixed (solved count from finals/markers, GB on Hub from the Hub listing, concurrent-deletion safe);
  scratch budget and wave sizes in `docs/generation_runbook.md` §5 (M: waves of 80 shards, submit the next wave only
  when the upload backlog is below one wave and `data/` < 200 GB).
- Next: M is **not** submitted until the S backlog is uploaded (rule 2); Phase 11 (docs, notebooks, CI, datasheet) starts now.

---

# Status — 2026-09-16 evening (tier S repair, autonomous driver armed, Phase 11 delivered)

- **Tier S**: two incidents (scratch quota; partial-finalize race that shipped 72 shards with 178–199 of 200 samples,
  shard 104 with 5) — both recorded in `docs/status/generation_log.md`. Fixes: one Hub commit per shard with per-shard
  temporary staging, sample-count validation against the manifest (sync and finalize), finalize refuses partially
  solved shards and deletes intermediates on success, two-failure stop rule. The 72 shards were re-prepared and are being
  re-solved (array 5834442, ≈ 3 h), then re-finalized and re-uploaded in place; the other 428 shards are on the Hub.
- **Autonomous driver** (`scripts/slurm/v1/generation_driver.py`, detached) waits for S to be complete, then runs
  M → L → XL → XXL in waves per the runbook §5, reports at tier boundaries (`logs/tier_boundary_<tier>.txt`), and stops on
  the stop rule / scratch > 250 GB / a dead sync supervisor (`logs/ALERT.txt`).
- **Phase 11** delivered (`docs/phase_11_report.md`): README, generation guide, contributing guide, notebooks 01–05, CI
  workflow (lint, offline tests, Julia tests, 5-sample smoke), connectivity test; tree ruff-formatted; 130 tests passing.
- Scratch 172 GB of 300; GB on Hub (data/S) ≈ 60; core-hours ≈ 1 700 + 220 for the repair.

---

# Status — 2026-09-17 (tier S complete and audited; driver running M)

- **Tier S complete**: 500 / 500 shards (100 000 landscapes, 522 629 configuration rows) validated with the full integrity check
  (planned sample ids and configurations, manifest count, Hub sha256) and on the public `Xirro/AmpScape`; **full audit clean**
  (500 shards, 2 500 Hub files, 0 discrepancies); the 72 repaired shards replaced their Hub copies (same paths, new checksums,
  72 / 72 confirmed). QC fail rate 0.000 %. Core-hours 2 061 (incl. the repairs). GB on Hub (`data/S/`) 142. Upload rate
  after the sync fix ≈ 125 shards/h.
- Incidents (a) quota, (b) partial finalize, (c) double submission — all in `docs/status/generation_log.md`, each with its
  structural fix (one-commit uploads + intermediate cleanup; solver completion marker + full-integrity validation;
  submit guard against queued/running tasks). The published index carries `skipped_configs` with reasons per sample.
- **Driver restarted**: M → L → XL → XXL in waves per the runbook, with a full audit required at every tier boundary.
- Phase 11 delivered; CI green.
