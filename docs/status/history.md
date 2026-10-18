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

---

# Status — 2026-09-19 (tiers S and M complete and audited; L running; addendum WP1/WP2 in progress)

- **Tier M complete**: 500 / 500 shards (50 000 landscapes) validated, uploaded and **audited clean** (full Hub-vs-plan audit
  gate in the driver); QC fail rate 0.002 % (one contrast-10⁶ configuration at the residual threshold); 251.5 GB on the Hub
  for M (394 GB total with S). One shard (434) needed a re-finalize after a write race between two finalize jobs; the driver
  now alerts on `.invalid` shards and re-finalizes solved-but-unfinalized shards itself.
- **Tier L started** (1 000 shards of 20, waves of 100, prepare-ahead one wave). Generation core-hours so far ≈ 3 850.
- **Addendum**: WP3 done; WP5 analysis done (probe design + ≈ 60 CPU-h estimate awaiting confirmation); WP1 part 1 done and the
  owner decision implemented (block-1 reference = official T4 surface at M/L, `--t4-reference` in the harness, tail flag,
  docs); the M reference is being grown to 1 000 samples (800 block-1 solves queued) and the three WP2 block-size builds
  (block 3 without artefact correction, block 7 with/without) are queued on the same samples; ICE changed the default QoS
  (explicit `coc-ice` now required — fixed in the profile after two silent submission failures).

---

# Status — 2026-09-19 (WP1 + WP2 delivered; L generating; supervisor incident closed)

- **Addendum WP1 (`docs/addendum_WP1_report.md`)**: 1 000-sample block-1 reference at M (official T4 evaluation surface):
  production block 3 deviates from exact by 0.029 rel-L2 mean (median 0.027), 4.7 % of samples above 5 % (11 % of
  synthetic, 1.4 % of real), top-5 % IoU 0.93, pinch recall 0.93; per-sample index with the tail flag published under
  `aux/t4_bs1_reference/M/` on the Hub; `evaluate.py --t4-reference`.
- **Addendum WP2 (`docs/addendum_WP2_report.md`, `docs/tables/t4_pareto_M.md`, `docs/figures/t4_pareto_M.png`)**: block-size
  Pareto at M — the artefact correction is worth 4× in rel-L2 at no cost (block 3: 0.029 vs 0.111 without); block 7 with
  correction 0.098 at 25 s; block-size error is nearly split-independent; `evaluate.py --t4-blocks` prints block rows beside
  a model. L rows and learned-model rows pending (L production; GPU allocation). **Stopped for confirmation.**
- **Generation**: S and M complete and audited; L wave 2 of 10 running (87 of 1 000 shards on the Hub), scratch 180 GB,
  ≈ 5 100 core-hours. Incident (d): a session restart on another login node started duplicate supervisors; caught in
  10 min, no double submission, cross-host leases added (`logs/lease_*.json`); the driver is being restarted under the
  lease protocol; the S/M/L sync loops from the previous session keep running on `login-ice-gnr-2`.

---

# Status — 2026-09-20 (L block-1 reference and L Pareto rows delivered; L final wave running)

- **Addendum WP1 at L (`docs/addendum_WP1_report.md` §6)**: the 60-sample L block-1 reference is complete (20 synthetic +
  40 real tiles over test_id / test_ood / ood_region). Production block 5 deviates from the exact map by 0.028 rel-L2 mean
  (test_id 0.032, test_ood 0.020, ood_region 0.028; max 0.058), non-source 0.033, top-5 % IoU 0.93, pinch recall 0.94;
  2 of 60 flagged above 5 % (both synthetic; no real tile). Block 1 at L costs 22× production (3.7 CPU-h per landscape,
  ≈ 225 CPU-h in total). Index with `tail_gt5pct` and summary published on the Hub under `aux/t4_bs1_reference/L/`; it is
  the L T4 evaluation surface (`evaluate.py --t4-reference aux/t4_bs1_reference/L_bs1`).
- **Addendum WP2 at L (`docs/addendum_WP2_report.md`, `docs/tables/t4_pareto_L.md`, `docs/figures/t4_pareto_L.png`)**: block
  3 / production 5 / 11 and 5-without-correction on the same 60 samples. Block 3 and block 5 are within 0.2–0.4 points of
  rel-L2 of each other at 2.5–2.9× the cost; block 11 loses 4–6 points for a 3.6× saving; the artefact correction is worth
  3–5× in rel-L2 at zero cost. The production block is the knee of the front at L as at M. Rows published under
  `aux/t4_blocksize_baselines/L/` on the Hub.
- **Tooling**: `aux_t4_blocks.py compare` looks a sample's inputs up across all inputs files (top-up re-chunking broke the
  first full run), writes the tail flag itself, and skips unreadable Hub samples with a warning.
- **Generation**: L 900 of 1 000 shards validated and on the Hub (QC fail 0.017 %), final wave 900–999 running since
  18:43Z (9-h walltime), scratch 193 GB, ≈ 9 300 core-hours, no alert, driver (lease on gnr-1) and L sync loop (gnr-2)
  alive. After the wave: driver audit gate → L tier-boundary report → XL planned and submitted automatically.
- **Pending**: learned-model rows for the Pareto tables and the probe-set evaluation (GPU allocation); WP4/6/7.

---

# Status — 2026-09-21 (tier L complete and audited; XL held for a core-hour budget decision)

## Tier L boundary

| item | value |
|---|---|
| shards validated, uploaded, audited | 1 000 of 1 000 (20 000 landscapes, 105 949 index rows) |
| full Hub-vs-plan audit | clean (0 discrepancies, 4 958 files: 4 000 T1/T1W/T3/T4 + 958 T1R) |
| QC fail rate | 0.013 % |
| GB on Hub | L 380.5 (S 142.2, M 251.5; total 774) |
| upload window | 09-19 03:23Z → 09-21 01:12Z (45.8 h), ≈ 21 shards/h |
| L core-hours (ampscape-L tasks) | 5 713 (runbook estimate 3 300; includes 569 in timed-out tasks and the idle second core of waves 1–4) |
| core-hours since 09-15, all ampscape-* jobs | 10 273 (production 9 466 + approved aux work 805) |
| scratch | 0 GB of L left locally; ≈ 190 GB total |

L per-landscape solve time, measured on the 662 completed single-core tasks: median 4.48 h per 20-landscape shard
(806 s per landscape), p99 5.26 h, max 5.48 h — the 9-h walltime held with no timeouts after the tail rule.

The first L audit flagged 41 shards; all were one false positive (the audit demanded a `T1R` file for shards whose every
`regions` sample was legitimately skipped — generation log (g2)); fixed in `audit_tier.py`, re-audit clean, no data
changed. The `regions` skip rate is ≈ 50 % of the planned samples at both M and L (labelled in `skipped_configs`).

## XL held — the budget cannot cover XL + XXL as planned (owner decision needed)

The runbook's per-tier table (§1) counted XL and XXL in *single-core* hours (2 150 + 1 200) while the cluster profile
allocates 4 cpus per XL task and 8 per XXL task for memory (`configs/cluster/ice.yaml`); Slurm accounting charges the
allocated cpus, so the table under-counted those tiers by 4× and 8×. With 10 273 core-hours used, 2 727 remain of the
13 000 budget.

Estimates from the measured L time (806 s per landscape, single core) scaled by the Phase-5 T4 ratio (L→XL 3.3×,
XL→XXL 5×):

| option | XL (4 000) | XXL (400) | total run | vs 13 000 |
|---|---|---|---|---|
| A. profile as is (4 / 8 cpus, no speedup) | ≈ 12 000–15 600 | ≈ 9 400–12 400 | ≈ 32 000–38 000 | 2.5–3× over |
| B. 1 cpu per task, memory-only allocation (`-c1 --mem 16G/20G`, allowed: no MaxMemPerCPU on coc-cpu) | ≈ 3 000–3 900 | ≈ 1 200–1 550 | ≈ 14 500–15 800 | +11–22 % |
| C. B plus the brief's original counts (XL 2 000, XXL 200; prefix streams make this a clean prefix of the v1.0 design) | ≈ 1 500–2 000 | ≈ 600–800 | ≈ 12 400–13 100 | within budget |
| D. multi-core allocation if CHOLMOD/BLAS speed-up is near-linear (unmeasured) | between A and B | | | |

Walltimes at 1 cpu stay within the 10-h profile (XL 6 landscapes × ≈ 2 700–3 300 s × tail 1.8; XXL 1 landscape).
The solver hands the allocated cores to BLAS/CHOLMOD (`solve_shard.sbatch`), so option D is possible only if the
speed-up is measured. **Action taken:** the driver was stopped before any XL submission (planning ran as a Slurm job;
the XL manifest exists). A 4-shard probe (2 shards at 1 cpu, 2 at 4 cpus, ≈ 60 core-h) measures the real XL
per-landscape time and the thread speed-up so the decision rests on numbers; results in `docs/status/generation_log.md`
when the probe finishes (≈ 6–8 h).

**Recommendation:** option B (1 cpu everywhere, full counts): the walltimes hold, XL/XXL remain test-only tiers of the
frozen design, and the overrun is 11–22 % of the budget (≈ 1 500–2 800 core-hours); if the probe shows a ≥ 2×
speed-up at 4 cpus, use it for XXL only (the largest single solves), otherwise 1 cpu throughout.

## Also delivered today
WP1/WP2 at L (60-sample block-1 reference, block-size Pareto rows) — see the 2026-09-20 entry.

---

# Status — 2026-09-21 08:30Z (XL launched at 1 cpu, 300 concurrent; parallel uploaders; aux publication running)

- **Owner decisions applied**: full counts, 30 000 core-hour gate, wall-clock optimisation, 4 parallel uploaders, waves
  300 (after the approved clean-up: quicklooks deleted, task logs archived 12 GB → 0.4 GB, superseded pilot builds
  removed; scratch 146 GB → settling to ≈ 95 GB).
- **XL probe → 1 cpu per task**: per landscape 1 500–4 030 s at both 1 and 4 cpus (means ≈ 2 400 vs ≈ 2 500 s;
  Omniscape/CHOLMOD 95 % of the time, no BLAS gain), so the ≥ 1.5× rule selects 1 cpu; XXL likewise 1 cpu (16 GB;
  20 GB for test shards). Estimated cost XL ≈ 2 800, XXL ≈ 1 150 core-hours (total run ≈ 14 500).
- **XL running**: wave 0–299 submitted 08:24Z (job 5882104), all 300 tasks running at once (cluster 418/1 384 cores
  busy); 4 sync workers `XL_w0..3` under leases; XXL pre-planned (job 5882430) so the boundary loses no time.
- **Completion estimate**: XL wave 2 ≈ 13–14Z, wave 3 (67 shards) ≈ 19Z, XL audited ≈ 2026-09-22 03Z; XXL (400 shards,
  2 waves of ≈ 3–5 h) ≈ 2026-09-22 14–16Z. Upload rate after (4 workers) reported when wave 1 lands.
- **Slip and fix**: `data/builds/published` (the 46-sample `test_ood_published` set, local-only) was deleted with the pilot
  builds before its reference check was read; regenerated identically (ids verified, QC 100 %) and, per the new owner
  rule, being published under `aux/test_ood_published/` together with every other scratch-only evaluation asset
  (`aux/dev/{S,M}`, `aux/mini`, `aux/scale_probe/`, `aux/t4_bs1_reference/{M,L}` full builds,
  `aux/t4_blocksize_baselines/{M,L}/*`, `aux/results/{predictions,runs_dev,runs_tune}`; ≈ 20 GB, `scripts/push_aux.py`,
  sha256-verified, log `logs/push_aux.log`). **No further deletions without listing exact paths first.**
- Not pushed (results of throwaway runs, listed for the owner): `runs/calib` (60 MB), `runs/smoke` (121 MB).

---

# Status — 2026-09-22 05:20Z (tier XL complete and audited; XXL starting; precision pass ready)

## Tier XL boundary

| item | value |
|---|---|
| shards validated, uploaded, audited | 667 of 667 (4 000 landscapes, 21 006 index rows) |
| full Hub-vs-plan audit | clean (0 discrepancies, 3 132 files) |
| QC fail rate | 0.033 % |
| GB on Hub | XL 281.3 (S 142.2, M 251.5, L 380.5; total 1 056) |
| upload window | 09-21 09:03Z → 09-22 04:08Z (19.1 h), 4 workers, peak hour 125 shards / 35 GB |
| XL core-hours (1 cpu per task) | 3 684 (estimate 2 800; 4 OOM re-runs and the probe included) |
| core-hours since 09-15, all ampscape-* jobs | 13 986 of the 30 000 gate |
| wall-clock XL | 20 h 51 from first submission (08:24Z) to audited complete (05:15Z) |
| scratch | 128 GB |

Incidents: (h) four shards OUT_OF_MEMORY on the `regions` CG+AMG fallback (root cause `PosDefException` in
Circuitscape's CHOLMOD path; profile 20 GB, automatic 48 GB re-runs) — no data lost; the fallback rows (47 at XL)
are re-solved by the post-run precision pass. Rows for that pass at XL: 2 225 above 1e-9, 2 526 unmeasured (non-T4).

## XXL
400 shards (1 landscape each; all test splits; 240 regions configs) planned and prepared ahead; the driver picked them
up at the boundary (`prepared_upto = 399`) and submits wave 0–299 at 1 cpu / 24 GB (test shards 28 GB), 10-h walltime,
4 uploaders; ≈ 3–5 h per shard → XXL audited ≈ 2026-09-22 16–20Z.

## Precision pass (owner 2026-09-21, two parts)
Tooling validated end-to-end (`docs/post_run_resolve_plan.md` §7, runbook §8); starts after XXL, tier by tier.

---

# Status — 2026-09-22 15:30Z (v1.0 generation complete: all five tiers audited; precision pass started)

## Tier XXL boundary and whole-run totals

| item | XXL | whole run |
|---|---|---|
| shards validated, uploaded, audited | 400 of 400 (400 landscapes, 2 008 rows) | 3 067 shards, 174 400 landscapes |
| audit | clean (1 708 files) | S, M, L, XL, XXL all clean |
| QC fail rate | 0.45 % (9 rows: 7 `regions` residual_high, 1 T4, 1 T3 — all repaired by the precision pass) | S 0.000 %, M 0.002 %, L 0.013 %, XL 0.033 %, XXL 0.45 % |
| GB on Hub (data/) | ≈ 100 | 1 155.8 |
| core-hours | 1 228 (1 cpu; 7 OOM re-runs at 176 GB) | 15 218 of the 30 000 gate |
| wall-clock | 06:18Z first upload → 15:24Z audited (10 h from submission) | S start 09-16 → 09-22 15:24Z |
| scratch | — | 117 GB |

Incident (i) resolved: Circuitscape's hard 1e-4 residual check aborted Omniscape maps and advanced solves on contrast-10⁶
2048² landscapes in both solvers; AmpScapeSolve now rescues exactly those solves by refinement (bit-identical
otherwise), validated on the failing landscape; the rows that failed before the change are repaired by the precision
pass at XXL. Index defect fixed (shard names carried the `.part` staging suffix); all published indexes clean.

## Precision pass (owner 2026-09-21) — started
Tier S selected and submitted (rows above 1e-9, unmeasured T1/T1R rows, `cg+amg` rows, QC-failed rows; 125 Slurm
tasks of 4 shards); then upload → full audit → M → L → XL → XXL; index republished once at the end.

---

# Status — 2026-09-23 20:45Z (precision pass complete on all tiers; v1.0 data ready for the tag)

- **Precision pass done (owner 2026-09-21, parts 1 and 2):** 129 722 T1/T1W/T1R/T3 rows re-solved in place on the Hub
  (S 68 008, M 37 639, L 18 691, XL 4 774, XXL 610) with reduced-system CHOLMOD + refinement; every such row now carries its
  true residual (0 unmeasured rows left); 189 former `cg+amg` rows are now `cholmod` with `solver_original` kept; 3 861
  rows sit at the double-precision floor above 1e-9 (recorded); **20 rows above 1e-6** (all synthetic at contrast
  ≥ 10⁴) are flagged `residual_high`, `qc_pass = false`, and their samples are excluded from the split lists; the two
  incident-(i) XXL rows are repaired. Per-tier table: `docs/tables/precision_pass.md`; datasheet section added.
- **Audits:** S, M, L, XL, XXL all clean after the pass; indexes and split lists republished once (final).
- **Cost:** ≈ 245 CPU-h of solves; generation + pass ≈ 15 500 core-hours of the 30 000 gate. Hub data ≈ 1.16 TB.
- **Operational notes:** Hub commit limit (128/h) → batched uploads; cluster `MaxSubmitPU` now 50 → work-queue workers;
  XL/XXL real-tile rows need 48–128 GB per worker; Circuitscape solve rescue installed at load time (precompile-safe).
- **Next (owner):** v1.0 tag; WP4/WP6/WP7 and the learned baselines await the GPU allocation.

---

# Status — 2026-09-23 (v1.0 tagged; stopping — everything after this is GPU work)

- Card finalised (in-progress notice removed; final counts, sizes, core-hours, incident and precision-pass summaries).
- Croissant regenerated from the final indexes and validated with mlcroissant (30 distributions, 5 record sets, 0
  errors); core subset 115.5 GB (3 705 files), mini 0.61 GB, full 1 157.4 GB; any tier or task group downloads alone
  (verified: `data/XXL/T1R/*` alone, self-contained inputs + outputs).
- Statistics figures and table: `docs/figures/dataset_stats_*.png`, `docs/tables/dataset_statistics.md` (contrast,
  biome/realm, NoData fraction, solve-time distributions, per-tier storage); also under `aux/` on the Hub.
- `docs/generation_postmortem.md`: timeline, all incidents with root causes and fixes, final cost (16 552 core-hours),
  runbook changes for reproduction.
- Tags: GitHub `v1.0`, Hub revision `v1.0`; `CITATION.cff` 1.0.0 (2026-09-23); recorded in DECISIONS.

---

# Status — 2026-09-24 09:20Z: Phase 10-full running; headline S and M/T1 results in

## Progress
- 19 of 132 runs finished (all S seed-1 and most S seed-2 runs; U-Net and FNO T1 at M seed 1); 18 legs queued or
  running; WP4 data-scaling at S started (unet n1000/n5000). Running table: `docs/tables/baselines_full.md`.
- Headline rel-L2 on test_id (seed 1): T1 S — U-Net 0.111, FNO 0.198, ViT 0.238; T1 M — U-Net 0.238, FNO 0.266
  (error roughly doubles from S to M for both); T4 S — U-Net 0.040, FNO 0.070, ViT 0.071 (T4 S below 0.05 as flagged
  earlier). M evaluation takes ≈ 45 min (FNO) in its own leg.
- Training is 3–7× under the budget estimates; the calendar estimate is bounded by staging and the 32-GPU-hour
  running cap, not by GPU time.

## Changes to the schedule and operation (all committed)
- Three M legs (fno T1 s1/s2, vit T1 s1) hit the 2-h walltime during evaluation before the evaluation-deferral patch;
  they resumed from `done.json` in fresh evaluation legs (no training lost). No timeout since the patch.
- Staging is now strict-priority with eviction by furthest next use and **draining**: groups pinned by running jobs
  that block a higher-priority group stop receiving new jobs until they can be evicted (evaluation-only legs exempt).
  Priorities are tier-major (S → M → L → XL inside P1/P2/P3), so the headline M/T4 runs stage before L.
- Scratch floor without the training cache is ≈ 143 GB (data/tiles 37, data/sources 20, data/dev 12, aux 18, runs,
  caches). Under the 265 GB guard the cache can hold ≈ 120 GB, so the L groups (T1 84 GB, T4 82 GB) cannot be
  staged together: L runs will proceed group by group (L/T1 U-Net and FNO, then L/T4), adding roughly one day to
  the L milestone. XL groups (61 + 61 GB) fit together.
- Offloader restarted correctly (`scripts/slurm/gpu/offload_loop.sh`); finished runs are on the Hub under
  `aux/results/runs_full/<run>/` and their predictions removed locally.

## For the owner (no action taken)
- Deleting `data/sources` (20 GB) and `data/tiles/v1.0` (37 GB) from scratch would let both L groups stay staged
  and remove the group-by-group serialisation. Both are re-downloadable/regenerable (sources from the manifest
  URLs; tiles from sources), and WP7 keeps its own copies of the 20 tiles under `aux/wp7/tiles`. I will not delete
  them without approval.
- The published real-tile set exists at S only, so M/L/XL runs report test_id / test_ood / ood_region (T4 M/L also
  the exact block-1 reference rows).

Next: headline M/T4 (U-Net, FNO), then L; weekly report or on schedule changes.

---

# Status — 2026-09-24 15:40Z: Phase 10-full — headline S, M and L results in (T1); L/T4 next

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | — | running |
| T4 U-Net | 0.040 | 0.051 | staging |
| T4 FNO | 0.070 | 0.079 | staging |
| T4 ViT | 0.071 | 0.099 | staging |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 at M against the exact block-1 map (test_id): U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms; the
  production block-3 solver is 0.029 at 111 s, block 7 with artifact correction 0.098 at 25 s
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 53 of 132 runs finished; 4 legs queued or running. Running table: `docs/tables/baselines_full.md`.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## For the owner (no action taken)
- Deleting from scratch `data/sources` (20 GB) and `data/tiles/v1.0` (37 GB) — both regenerable/re-downloadable,
  WP7 keeps its 20 tiles under `aux/wp7/tiles` — would let both L groups stay staged and remove the idle time at L
  (and at any re-run). Smaller candidates: `.uv_cache` (12 GB, package cache), `aux/wp7/v1` (4.5 GB, v1.0 T4 shards
  re-fetchable from the Hub), `data/dev` (12 GB, dev subset; on the Hub under aux/). I will not delete any of these
  without approval.

Next: L/T4 (U-Net, FNO, ViT × 3 seeds) → XL → WP4 completes → GNN; WP7 demo after the best T4 model at L.

---

# Status — 2026-09-24 23:15Z: Phase 10-full — headline S/M/L T1 in, L/T4 running; XL/XXL rows by scale transfer

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | staging |
| T4 FNO | 0.070 | 0.079 | staging |
| T4 ViT | 0.071 | 0.099 | staging |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 at M against the exact block-1 map (test_id): U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms; the
  production block-3 solver is 0.029 at 111 s, block 7 with artifact correction 0.098 at 25 s
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 53 of 132 runs finished; 4 legs queued or running. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

Next: L/T4 and L/T3 finish → transfer evaluations at XL/XXL → GNN (S, M, L) → GNN transfers; WP7 demo as soon as the best T4 model at L is known.

---

# Status — 2026-09-25 04:50Z: Phase 10-full — headline S/M/L for T1 and T4 in; WP7 demo launched

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

WP7 demo launched 04:48Z with U-Net T4 L seed 1 (the best T4 model at L; job 5934206, ≈ 4 h cap).

Next: L/T3 finishes → transfer evaluations at XL/XXL → GNN (S, M, L) → GNN transfers; WP7 report when the demo job ends.

---

# Status — 2026-09-25 05:10Z: Phase 10-full — headline S/M/L for T1 and T4 in; WP7 demo done

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: L/T3 finishes → transfer evaluations at XL/XXL → GNN (S, M, L) → GNN transfers; weekly report or on schedule changes.

---

# Status — 2026-09-25 10:00Z: Phase 10-full — S/M/L headline done, WP7 done; scale transfer running after a scratch-quota incident

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a different window geometry (block 33 vs block 9 at L), so T4 transfer is
  transfer across operators as well as scales. Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: L/T3 finishes → transfer evaluations at XL/XXL → GNN (S, M, L) → GNN transfers; weekly report or on schedule changes.

---

# Status — 2026-09-25 12:30Z: owner checks 1–3 answered; scale-aware variant queued; transfer phase running

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-09-25 22:45Z: owner checks 1–3 answered; scale-aware variant queued; transfer phase running again after a 12-h hold

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-09-26 02:50Z: v1.0.2 (metadata) published and tagged; transfer phase running

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## v1.0.2 (metadata only) — done 2026-09-26 02:40Z (owner approval)
- Audit of every hashed share: only the C3 macro-cell hash had a None key (synthetic XL). The block-order hash
  (real tiles, seed|stratum|block), the synthetic seed-family hash and the strict-XXL geometric check use defined keys;
  real-tile val cells at L are assigned by the block rule and were never subject to C3.
- Second defect found during the audit and fixed in the same release: the Hub split lists `splits/<subset>/<split>.parquet`
  held only the last published tier's ids (per-tier uploads overwrote each other; `splits/full/train.parquet` had L's
  12,613 ids). Rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 /
  ood_region 16,720); `publish_index` now builds them from every tier's index. The per-tier index `split` column was
  always complete, so loaders were unaffected.
- XL after the correction: train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400 (25.3 % train+val;
  synthetic share 0.3635 of the moved landscapes; 28 real val landscapes drawn among the kept cells).
- Published: `index/XL.parquet`, `splits/**`, card, Croissant 1.0.2 (validated, 0 warnings); local caches refreshed;
  13 transfer runs re-aggregated on the new XL test_id (`scripts/reaggregate_transfer.py`, per-sample metrics kept);
  CITATION 1.0.2; tags `v1.0.2` on GitHub and the Hub. CI: `tests/test_scripts_parse.py` (every script non-empty and
  parseable, shell syntax-checked) — 75 files.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-10-02 14:10Z: driver idle for six days (staging deadlock) — restarted under a keepalive; 84 training runs done, transfer/variant/GNN phases remain

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## 2026-10-02 reconnect: inventory, incident, restart

**Inventory (from disk and the Hub, `aux/results/runs_full/`):** all 84 training runs of P1–P3 and WP4 are complete
and on the Hub with results (every T4 M/L run also has its exact-reference evaluation). Scale transfer: 18 of 30
legs done (all T1 at XL and XXL, 3 seeds; T4 seed-1 at XL for U-Net/FNO/ViT) — remaining 12: T4 XL seeds 2–3 (6)
and T4 XXL (6). Not started: scale-aware variants (6 L runs + 10 transfers), GNN (18 runs), GNN transfers (12),
GNN variant (2 + 4). Nominal remaining 772 GPU-h (GNN 578 of it); at the measured 3–7× faster training the realistic
remainder is ≈ 200–300 GPU-h.

**Incident:** the driver and the offloader never died — both ran through the week — but the driver was deadlocked
since 26 Sep 03:30Z: after the XXL/T1 group was released it refused to stage XL/T4 because the transfer-group staging
limit (201 GB = 245 − 4 × 11) sat below the scratch floor plus one XL group (156 + 61 GB), so nothing could be staged
and the queue stayed empty for six days. Silent because the hold was logged only as "does not fit". Fix: the limit
is now measured against the hard 280 GB guard (280 − 3 × 11 = 247; three transfer legs in flight), and the monitor
has a watchdog that reports an empty queue while jobs are pending. Six calendar days lost; no results lost.

**Restart (detached):** `scripts/slurm/gpu/keepalive.sh` under `setsid nohup` restarts the driver whenever its lease
pid is dead and the offloader whenever none runs (every 5 min; `logs/keepalive.log`). One-line runbook entry in
`docs/phase10_full_schedule.md` §3. It survives a dead session; a login-node reboot still needs the line re-run
(PACE login nodes allow no user cron/systemd). Driver restarted 13:54Z; XL/T4 staging; T4 transfer legs next.

**Calendar estimate at the measured rates:** transfers ≈ 1 day (12 legs + the variants' 10), scale-aware L runs
≈ 0.5 day in parallel, GNN 18 runs ≈ 2–3 days (L/T4 GNN is the long pole, 2-h legs re-queued), GNN transfers and
variant ≈ 1 day → **≈ 4–5 calendar days** if nothing stalls. Weekly report, or on failures.

## v1.0.2 (metadata only) — done 2026-09-26 02:40Z (owner approval)
- Audit of every hashed share: only the C3 macro-cell hash had a None key (synthetic XL). The block-order hash
  (real tiles, seed|stratum|block), the synthetic seed-family hash and the strict-XXL geometric check use defined keys;
  real-tile val cells at L are assigned by the block rule and were never subject to C3.
- Second defect found during the audit and fixed in the same release: the Hub split lists `splits/<subset>/<split>.parquet`
  held only the last published tier's ids (per-tier uploads overwrote each other; `splits/full/train.parquet` had L's
  12,613 ids). Rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 /
  ood_region 16,720); `publish_index` now builds them from every tier's index. The per-tier index `split` column was
  always complete, so loaders were unaffected.
- XL after the correction: train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400 (25.3 % train+val;
  synthetic share 0.3635 of the moved landscapes; 28 real val landscapes drawn among the kept cells).
- Published: `index/XL.parquet`, `splits/**`, card, Croissant 1.0.2 (validated, 0 warnings); local caches refreshed;
  13 transfer runs re-aggregated on the new XL test_id (`scripts/reaggregate_transfer.py`, per-sample metrics kept);
  CITATION 1.0.2; tags `v1.0.2` on GitHub and the Hub. CI: `tests/test_scripts_parse.py` (every script non-empty and
  parseable, shell syntax-checked) — 75 files.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-10-03 03:00Z: transfer phase and scale-aware variants complete; GNN phase started

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.051 | 0.079 | 0.120 |
| T4 ViT | 0.052 | 0.099 | 0.159 |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## 2026-10-03: scale-aware target variant — result (seed 1, trained at L, zero-shot at XL/XXL; `paper/tables/scale_transfer.md`)

| task / model | L (trained) | XL zero-shot → scale-aware | XXL zero-shot → scale-aware |
|---|---|---|---|
| T4 U-Net | 0.080 | 0.515 → **0.189** | 0.749 → **0.312** |
| T4 FNO | 0.120 | 0.532 → **0.162** | 0.765 → **0.201** |
| T4 ViT | 0.161 | 0.538 → **0.203** | — |
| T1 U-Net | 0.369 | 1.250 → 0.957 | 4.43 → 0.987 |
| T1 FNO | 0.411 | 0.707 → **0.572** | 1.502 → **0.671** |
| T1 ViT | 0.617 | 0.768 → 0.656 | — |

(rel-L2 on test_id; zero-shot values are the 3-seed means of the official configs.) Making the target scale-free with
the quantity that sets the current magnitude — the Omniscape radius for T4, the valid-pixel count for T1 — removes most
of the zero-shot transfer error for T4 (the radius factor is exactly the 1 − 1/2 and 1 − 1/4 seen before) and for the
FNO on T1; the U-Net on T1 stays near rel-L2 1 at XL/XXL (its receptive field, not the magnitude, is the limit) and
the ViT's structural problem is unchanged. Rankings (Spearman) are the same as zero-shot in every case. No XL/XXL data
entered training or the inverse transform. At L the variant equals the official run for T4 (k = 1) and differs within
seed noise for T1. Figure: `paper/figures/scale_transfer.png`.

**Incident 2026-10-03 01:00–02:15Z (caught by the watchdog in an hour):** pre-staging the S/M groups for the gated GNN
phase pushed scratch over the transfer threshold and held the last five variant transfer legs, which in turn gated the
GNN phase. Fixed: no pre-staging for a gated phase; the hold may evict any group whose next use is later than the held
leg. GNN phase started 02:50Z (18 runs + 12 transfers + variant).

## 2026-10-02 reconnect: inventory, incident, restart

**Inventory (from disk and the Hub, `aux/results/runs_full/`):** all 84 training runs of P1–P3 and WP4 are complete
and on the Hub with results (every T4 M/L run also has its exact-reference evaluation). Scale transfer: 18 of 30
legs done (all T1 at XL and XXL, 3 seeds; T4 seed-1 at XL for U-Net/FNO/ViT) — remaining 12: T4 XL seeds 2–3 (6)
and T4 XXL (6). Not started: scale-aware variants (6 L runs + 10 transfers), GNN (18 runs), GNN transfers (12),
GNN variant (2 + 4). Nominal remaining 772 GPU-h (GNN 578 of it); at the measured 3–7× faster training the realistic
remainder is ≈ 200–300 GPU-h.

**Incident:** the driver and the offloader never died — both ran through the week — but the driver was deadlocked
since 26 Sep 03:30Z: after the XXL/T1 group was released it refused to stage XL/T4 because the transfer-group staging
limit (201 GB = 245 − 4 × 11) sat below the scratch floor plus one XL group (156 + 61 GB), so nothing could be staged
and the queue stayed empty for six days. Silent because the hold was logged only as "does not fit". Fix: the limit
is now measured against the hard 280 GB guard (280 − 3 × 11 = 247; three transfer legs in flight), and the monitor
has a watchdog that reports an empty queue while jobs are pending. Six calendar days lost; no results lost.

**Restart (detached):** `scripts/slurm/gpu/keepalive.sh` under `setsid nohup` restarts the driver whenever its lease
pid is dead and the offloader whenever none runs (every 5 min; `logs/keepalive.log`). One-line runbook entry in
`docs/phase10_full_schedule.md` §3. It survives a dead session; a login-node reboot still needs the line re-run
(PACE login nodes allow no user cron/systemd). Driver restarted 13:54Z; XL/T4 staging; T4 transfer legs next.

**Calendar estimate at the measured rates:** transfers ≈ 1 day (12 legs + the variants' 10), scale-aware L runs
≈ 0.5 day in parallel, GNN 18 runs ≈ 2–3 days (L/T4 GNN is the long pole, 2-h legs re-queued), GNN transfers and
variant ≈ 1 day → **≈ 4–5 calendar days** if nothing stalls. Weekly report, or on failures.

## v1.0.2 (metadata only) — done 2026-09-26 02:40Z (owner approval)
- Audit of every hashed share: only the C3 macro-cell hash had a None key (synthetic XL). The block-order hash
  (real tiles, seed|stratum|block), the synthetic seed-family hash and the strict-XXL geometric check use defined keys;
  real-tile val cells at L are assigned by the block rule and were never subject to C3.
- Second defect found during the audit and fixed in the same release: the Hub split lists `splits/<subset>/<split>.parquet`
  held only the last published tier's ids (per-tier uploads overwrote each other; `splits/full/train.parquet` had L's
  12,613 ids). Rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 /
  ood_region 16,720); `publish_index` now builds them from every tier's index. The per-tier index `split` column was
  always complete, so loaders were unaffected.
- XL after the correction: train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400 (25.3 % train+val;
  synthetic share 0.3635 of the moved landscapes; 28 real val landscapes drawn among the kept cells).
- Published: `index/XL.parquet`, `splits/**`, card, Croissant 1.0.2 (validated, 0 warnings); local caches refreshed;
  13 transfer runs re-aggregated on the new XL test_id (`scripts/reaggregate_transfer.py`, per-sample metrics kept);
  CITATION 1.0.2; tags `v1.0.2` on GitHub and the Hub. CI: `tests/test_scripts_parse.py` (every script non-empty and
  parseable, shell syntax-checked) — 75 files.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-10-04 16:00Z: Phase 10-full COMPLETE (166/166 jobs, 430 GPU-h); Phase 12 drafts in progress

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.051 | 0.079 | 0.120 |
| T4 ViT | 0.052 | 0.099 | 0.159 |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Phase 10-full — final summary (2026-10-04; tables `paper/tables/`, figures `paper/figures/`, all regenerated by `scripts/paper_figures.py`)

**Done:** 110 training runs (U-Net, FNO, ViT, GNN × T1/T4 and U-Net/FNO × T3, × S/M/L × 3 seeds; WP4; six
scale-aware variants), 56 transfer legs (XL/XXL), WP7. All on the Hub (`aux/results/runs_full/`). Cost 401 GPU jobs,
430.1 GPU-h vs ≈ 1,081 nominal (`docs/tables/gpu_usage.md`); 11 calendar days incl. 6 idle. Daemons stopped.

**Headline (rel-L2 on test_id, mean over 3 seeds; `paper/tables/baselines_sml.md`):**

| task | model | S | M | L |
|---|---|---|---|---|
| T1 | U-Net / FNO / ViT / GNN | 0.114 / 0.199 / 0.218 / 0.561 | 0.212 / 0.248 / 0.419 / 0.849 | 0.397 / 0.361 / 0.648 / 1.067 |
| T3 | U-Net / FNO | 0.111 / 0.253 | 0.202 / 0.284 | 0.379 / 0.347 |
| T4 | U-Net / FNO / ViT / GNN | 0.041 / 0.051 / 0.052 / 0.066 | 0.051 / 0.079 / 0.094 / 0.099 | 0.081 / 0.120 / 0.159 / 0.142 |

- T4 against the exact block-1 map (seed 1; `paper/tables/t4_pareto_{M,L}.md`): at M U-Net 0.051, FNO 0.079, GNN
  0.099 at 1–16 ms/landscape vs the production block-3 solver 0.029 at 111 s; at L U-Net 0.080, FNO 0.120, GNN 0.142
  at 5–66 ms vs block 5 at 0.032 and 566 s.
- The GNN is far behind on T1 (its multi-scale graph does not resolve long-range pairwise flow) and competitive on
  T4 (local Omniscape windows), the opposite of the convolutional models' relative strengths.
- Scale transfer (`paper/tables/scale_transfer.md`): zero-shot XL/XXL fails on magnitude (T4 rel-L2 ≈ 0.52 / 0.75
  for every model, = 1 − r_L/r_tier); the scale-aware target recovers T4 to 0.16–0.22 at XL and 0.20–0.34 at XXL
  (U-Net 0.189 / 0.312, FNO 0.162 / 0.201, GNN 0.223 / 0.341) and the FNO on T1 to 0.57 / 0.67; U-Net and GNN on T1
  stay near rel-L2 0.8–1.0 (receptive field). Rankings are unchanged by the variant.
- OOD at the training tier (`paper/ood_analysis.md`): held-out table + contrast costs ≤ 18 % (ViT L excepted);
  published real surfaces cost 30–52 % on T4 at S; the held-out-region split is *easier* (0.65–1.0×) because of its
  composition — to be presented as a leakage control, not a stress test.
- WP4 (`docs/wp4_data_scaling.md`): under the official step budget the U-Net saturates by 20k landscapes at S; the
  FNO stays data-limited. WP7 (`docs/wp7_demo.md`): study-level conclusions reproduced at ≈ ×11,000 lower cost.

**Phase 12 state:** outline, five section drafts (dataset/generation, tasks/metrics, splits/OOD, baselines/protocol,
related work with 62 verified sources), OOD analysis, figure script with 12 figures and 8 tables. Results and
discussion sections are being drafted from the final tables now.

## 2026-10-03: scale-aware target variant — result (seed 1, trained at L, zero-shot at XL/XXL; `paper/tables/scale_transfer.md`)

| task / model | L (trained) | XL zero-shot → scale-aware | XXL zero-shot → scale-aware |
|---|---|---|---|
| T4 U-Net | 0.080 | 0.515 → **0.189** | 0.749 → **0.312** |
| T4 FNO | 0.120 | 0.532 → **0.162** | 0.765 → **0.201** |
| T4 ViT | 0.161 | 0.538 → **0.203** | — |
| T1 U-Net | 0.369 | 1.250 → 0.957 | 4.43 → 0.987 |
| T1 FNO | 0.411 | 0.707 → **0.572** | 1.502 → **0.671** |
| T1 ViT | 0.617 | 0.768 → 0.656 | — |

(rel-L2 on test_id; zero-shot values are the 3-seed means of the official configs.) Making the target scale-free with
the quantity that sets the current magnitude — the Omniscape radius for T4, the valid-pixel count for T1 — removes most
of the zero-shot transfer error for T4 (the radius factor is exactly the 1 − 1/2 and 1 − 1/4 seen before) and for the
FNO on T1; the U-Net on T1 stays near rel-L2 1 at XL/XXL (its receptive field, not the magnitude, is the limit) and
the ViT's structural problem is unchanged. Rankings (Spearman) are the same as zero-shot in every case. No XL/XXL data
entered training or the inverse transform. At L the variant equals the official run for T4 (k = 1) and differs within
seed noise for T1. Figure: `paper/figures/scale_transfer.png`.

**Incident 2026-10-03 01:00–02:15Z (caught by the watchdog in an hour):** pre-staging the S/M groups for the gated GNN
phase pushed scratch over the transfer threshold and held the last five variant transfer legs, which in turn gated the
GNN phase. Fixed: no pre-staging for a gated phase; the hold may evict any group whose next use is later than the held
leg. GNN phase started 02:50Z (18 runs + 12 transfers + variant).

## 2026-10-02 reconnect: inventory, incident, restart

**Inventory (from disk and the Hub, `aux/results/runs_full/`):** all 84 training runs of P1–P3 and WP4 are complete
and on the Hub with results (every T4 M/L run also has its exact-reference evaluation). Scale transfer: 18 of 30
legs done (all T1 at XL and XXL, 3 seeds; T4 seed-1 at XL for U-Net/FNO/ViT) — remaining 12: T4 XL seeds 2–3 (6)
and T4 XXL (6). Not started: scale-aware variants (6 L runs + 10 transfers), GNN (18 runs), GNN transfers (12),
GNN variant (2 + 4). Nominal remaining 772 GPU-h (GNN 578 of it); at the measured 3–7× faster training the realistic
remainder is ≈ 200–300 GPU-h.

**Incident:** the driver and the offloader never died — both ran through the week — but the driver was deadlocked
since 26 Sep 03:30Z: after the XXL/T1 group was released it refused to stage XL/T4 because the transfer-group staging
limit (201 GB = 245 − 4 × 11) sat below the scratch floor plus one XL group (156 + 61 GB), so nothing could be staged
and the queue stayed empty for six days. Silent because the hold was logged only as "does not fit". Fix: the limit
is now measured against the hard 280 GB guard (280 − 3 × 11 = 247; three transfer legs in flight), and the monitor
has a watchdog that reports an empty queue while jobs are pending. Six calendar days lost; no results lost.

**Restart (detached):** `scripts/slurm/gpu/keepalive.sh` under `setsid nohup` restarts the driver whenever its lease
pid is dead and the offloader whenever none runs (every 5 min; `logs/keepalive.log`). One-line runbook entry in
`docs/phase10_full_schedule.md` §3. It survives a dead session; a login-node reboot still needs the line re-run
(PACE login nodes allow no user cron/systemd). Driver restarted 13:54Z; XL/T4 staging; T4 transfer legs next.

**Calendar estimate at the measured rates:** transfers ≈ 1 day (12 legs + the variants' 10), scale-aware L runs
≈ 0.5 day in parallel, GNN 18 runs ≈ 2–3 days (L/T4 GNN is the long pole, 2-h legs re-queued), GNN transfers and
variant ≈ 1 day → **≈ 4–5 calendar days** if nothing stalls. Weekly report, or on failures.

## v1.0.2 (metadata only) — done 2026-09-26 02:40Z (owner approval)
- Audit of every hashed share: only the C3 macro-cell hash had a None key (synthetic XL). The block-order hash
  (real tiles, seed|stratum|block), the synthetic seed-family hash and the strict-XXL geometric check use defined keys;
  real-tile val cells at L are assigned by the block rule and were never subject to C3.
- Second defect found during the audit and fixed in the same release: the Hub split lists `splits/<subset>/<split>.parquet`
  held only the last published tier's ids (per-tier uploads overwrote each other; `splits/full/train.parquet` had L's
  12,613 ids). Rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 /
  ood_region 16,720); `publish_index` now builds them from every tier's index. The per-tier index `split` column was
  always complete, so loaders were unaffected.
- XL after the correction: train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400 (25.3 % train+val;
  synthetic share 0.3635 of the moved landscapes; 28 real val landscapes drawn among the kept cells).
- Published: `index/XL.parquet`, `splits/**`, card, Croissant 1.0.2 (validated, 0 warnings); local caches refreshed;
  13 transfer runs re-aggregated on the new XL test_id (`scripts/reaggregate_transfer.py`, per-sample metrics kept);
  CITATION 1.0.2; tags `v1.0.2` on GitHub and the Hub. CI: `tests/test_scripts_parse.py` (every script non-empty and
  parseable, shell syntax-checked) — 75 files.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-10-04 20:30Z: Phase 10-full COMPLETE (166/166 jobs, 430 GPU-h); Phase 12 draft package complete

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.051 | 0.079 | 0.120 |
| T4 ViT | 0.052 | 0.099 | 0.159 |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Phase 10-full — final summary (2026-10-04; tables `paper/tables/`, figures `paper/figures/`, all regenerated by `scripts/paper_figures.py`)

**Done:** 110 training runs (U-Net, FNO, ViT, GNN × T1/T4 and U-Net/FNO × T3, × S/M/L × 3 seeds; WP4; six
scale-aware variants), 56 transfer legs (XL/XXL), WP7. All on the Hub (`aux/results/runs_full/`). Cost 401 GPU jobs,
430.1 GPU-h vs ≈ 1,081 nominal (`docs/tables/gpu_usage.md`); 11 calendar days incl. 6 idle. Daemons stopped.

**Headline (rel-L2 on test_id, mean over 3 seeds; `paper/tables/baselines_sml.md`):**

| task | model | S | M | L |
|---|---|---|---|---|
| T1 | U-Net / FNO / ViT / GNN | 0.114 / 0.199 / 0.218 / 0.561 | 0.212 / 0.248 / 0.419 / 0.849 | 0.397 / 0.361 / 0.648 / 1.067 |
| T3 | U-Net / FNO | 0.111 / 0.253 | 0.202 / 0.284 | 0.379 / 0.347 |
| T4 | U-Net / FNO / ViT / GNN | 0.041 / 0.051 / 0.052 / 0.066 | 0.051 / 0.079 / 0.094 / 0.099 | 0.081 / 0.120 / 0.159 / 0.142 |

- T4 against the exact block-1 map (seed 1; `paper/tables/t4_pareto_{M,L}.md`): at M U-Net 0.051, FNO 0.079, GNN
  0.099 at 1–16 ms/landscape vs the production block-3 solver 0.029 at 111 s; at L U-Net 0.080, FNO 0.120, GNN 0.142
  at 5–66 ms vs block 5 at 0.032 and 566 s.
- The GNN is far behind on T1 (its multi-scale graph does not resolve long-range pairwise flow) and competitive on
  T4 (local Omniscape windows), the opposite of the convolutional models' relative strengths.
- Scale transfer (`paper/tables/scale_transfer.md`): zero-shot XL/XXL fails on magnitude (T4 rel-L2 ≈ 0.52 / 0.75
  for every model, = 1 − r_L/r_tier); the scale-aware target recovers T4 to 0.16–0.22 at XL and 0.20–0.34 at XXL
  (U-Net 0.189 / 0.312, FNO 0.162 / 0.201, GNN 0.223 / 0.341) and the FNO on T1 to 0.57 / 0.67; U-Net and GNN on T1
  stay near rel-L2 0.8–1.0 (receptive field). Rankings are unchanged by the variant.
- OOD at the training tier (`paper/ood_analysis.md`): held-out table + contrast costs ≤ 18 % (ViT L excepted);
  published real surfaces cost 30–52 % on T4 at S; the held-out-region split is *easier* (0.65–1.0×) because of its
  composition — to be presented as a leakage control, not a stress test.
- WP4 (`docs/wp4_data_scaling.md`): under the official step budget the U-Net saturates by 20k landscapes at S; the
  FNO stays data-limited. WP7 (`docs/wp7_demo.md`): study-level conclusions reproduced at ≈ ×11,000 lower cost.

**Phase 12 state (complete as a draft package):** `paper/outline.md`; seven section drafts under `paper/sections/`
(dataset/generation, tasks/metrics, splits/OOD, baselines/protocol, related work with 62 verified sources + source
table, results, discussion/limitations/ethics/maintenance) with every number tagged to its source file and no TODO
markers left (the only unavailable fact — non-source rel-L2 of learned models against the block-1 map — is stated as
such); brief §14 deliverables `paper/baselines.md`, `paper/dataset_statistics.md`, `paper/ood_analysis.md`; one script
(`scripts/paper_figures.py`) regenerates 12 figures and 8 tables under `paper/`. Open for the owner: the two
practitioner cost quotes flagged in `paper/sections/related_work_sources.md` need a human check; the public repo
surfaces in novelty searches (double-blind); DOI at submission.

## 2026-10-03: scale-aware target variant — result (seed 1, trained at L, zero-shot at XL/XXL; `paper/tables/scale_transfer.md`)

| task / model | L (trained) | XL zero-shot → scale-aware | XXL zero-shot → scale-aware |
|---|---|---|---|
| T4 U-Net | 0.080 | 0.515 → **0.189** | 0.749 → **0.312** |
| T4 FNO | 0.120 | 0.532 → **0.162** | 0.765 → **0.201** |
| T4 ViT | 0.161 | 0.538 → **0.203** | — |
| T1 U-Net | 0.369 | 1.250 → 0.957 | 4.43 → 0.987 |
| T1 FNO | 0.411 | 0.707 → **0.572** | 1.502 → **0.671** |
| T1 ViT | 0.617 | 0.768 → 0.656 | — |

(rel-L2 on test_id; zero-shot values are the 3-seed means of the official configs.) Making the target scale-free with
the quantity that sets the current magnitude — the Omniscape radius for T4, the valid-pixel count for T1 — removes most
of the zero-shot transfer error for T4 (the radius factor is exactly the 1 − 1/2 and 1 − 1/4 seen before) and for the
FNO on T1; the U-Net on T1 stays near rel-L2 1 at XL/XXL (its receptive field, not the magnitude, is the limit) and
the ViT's structural problem is unchanged. Rankings (Spearman) are the same as zero-shot in every case. No XL/XXL data
entered training or the inverse transform. At L the variant equals the official run for T4 (k = 1) and differs within
seed noise for T1. Figure: `paper/figures/scale_transfer.png`.

**Incident 2026-10-03 01:00–02:15Z (caught by the watchdog in an hour):** pre-staging the S/M groups for the gated GNN
phase pushed scratch over the transfer threshold and held the last five variant transfer legs, which in turn gated the
GNN phase. Fixed: no pre-staging for a gated phase; the hold may evict any group whose next use is later than the held
leg. GNN phase started 02:50Z (18 runs + 12 transfers + variant).

## 2026-10-02 reconnect: inventory, incident, restart

**Inventory (from disk and the Hub, `aux/results/runs_full/`):** all 84 training runs of P1–P3 and WP4 are complete
and on the Hub with results (every T4 M/L run also has its exact-reference evaluation). Scale transfer: 18 of 30
legs done (all T1 at XL and XXL, 3 seeds; T4 seed-1 at XL for U-Net/FNO/ViT) — remaining 12: T4 XL seeds 2–3 (6)
and T4 XXL (6). Not started: scale-aware variants (6 L runs + 10 transfers), GNN (18 runs), GNN transfers (12),
GNN variant (2 + 4). Nominal remaining 772 GPU-h (GNN 578 of it); at the measured 3–7× faster training the realistic
remainder is ≈ 200–300 GPU-h.

**Incident:** the driver and the offloader never died — both ran through the week — but the driver was deadlocked
since 26 Sep 03:30Z: after the XXL/T1 group was released it refused to stage XL/T4 because the transfer-group staging
limit (201 GB = 245 − 4 × 11) sat below the scratch floor plus one XL group (156 + 61 GB), so nothing could be staged
and the queue stayed empty for six days. Silent because the hold was logged only as "does not fit". Fix: the limit
is now measured against the hard 280 GB guard (280 − 3 × 11 = 247; three transfer legs in flight), and the monitor
has a watchdog that reports an empty queue while jobs are pending. Six calendar days lost; no results lost.

**Restart (detached):** `scripts/slurm/gpu/keepalive.sh` under `setsid nohup` restarts the driver whenever its lease
pid is dead and the offloader whenever none runs (every 5 min; `logs/keepalive.log`). One-line runbook entry in
`docs/phase10_full_schedule.md` §3. It survives a dead session; a login-node reboot still needs the line re-run
(PACE login nodes allow no user cron/systemd). Driver restarted 13:54Z; XL/T4 staging; T4 transfer legs next.

**Calendar estimate at the measured rates:** transfers ≈ 1 day (12 legs + the variants' 10), scale-aware L runs
≈ 0.5 day in parallel, GNN 18 runs ≈ 2–3 days (L/T4 GNN is the long pole, 2-h legs re-queued), GNN transfers and
variant ≈ 1 day → **≈ 4–5 calendar days** if nothing stalls. Weekly report, or on failures.

## v1.0.2 (metadata only) — done 2026-09-26 02:40Z (owner approval)
- Audit of every hashed share: only the C3 macro-cell hash had a None key (synthetic XL). The block-order hash
  (real tiles, seed|stratum|block), the synthetic seed-family hash and the strict-XXL geometric check use defined keys;
  real-tile val cells at L are assigned by the block rule and were never subject to C3.
- Second defect found during the audit and fixed in the same release: the Hub split lists `splits/<subset>/<split>.parquet`
  held only the last published tier's ids (per-tier uploads overwrote each other; `splits/full/train.parquet` had L's
  12,613 ids). Rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 /
  ood_region 16,720); `publish_index` now builds them from every tier's index. The per-tier index `split` column was
  always complete, so loaders were unaffected.
- XL after the correction: train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400 (25.3 % train+val;
  synthetic share 0.3635 of the moved landscapes; 28 real val landscapes drawn among the kept cells).
- Published: `index/XL.parquet`, `splits/**`, card, Croissant 1.0.2 (validated, 0 warnings); local caches refreshed;
  13 transfer runs re-aggregated on the new XL test_id (`scripts/reaggregate_transfer.py`, per-sample metrics kept);
  CITATION 1.0.2; tags `v1.0.2` on GitHub and the Hub. CI: `tests/test_scripts_parse.py` (every script non-empty and
  parseable, shell syntax-checked) — 75 files.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-10-04 21:30Z: Phase 13 (post-review work items) running; harness defect found and fixed

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.051 | 0.079 | 0.120 |
| T4 ViT | 0.052 | 0.099 | 0.159 |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Phase 13 — owner's six items (started 2026-10-04 evening)

**Editing rule applied** to all `paper/sections/*.md` (operational narrative removed; one reproducibility paragraph;
moved material in `paper/appendix_notes.md`). Several sections remain above the length targets with dense content
only; the cut to a 9-page main text happens when `paper/draft.md` is assembled (step 6).

**Item 1 — solver-acceleration metric.** The official T1/T3 models predict current maps, so the warm start needs
voltage-predicting counterparts: `train.py --target voltage` (same floor-log transform) for T3; six seed-1 runs
(U-Net, FNO × S/M/L, ≈ 9 GPU-h) are training/queued, and a waiter submits the CPU warm-start evaluations
(`evaluate.py --acceleration`, test_id and test_ood) per finished run. T1 `points` shards store no pair voltages, so
the first pair of every T1 landscape (ground = lowest label, source = second label, unit current — the pair the
metric uses) is being pre-solved on CPU (`pair1_voltage.jl`, 45 array tasks, `aux/t1_pair1/`, ≈ 90 CPU-h); the
same voltage head then trains on those systems as task `T1V` (six runs, ≈ 9 GPU-h) once the pre-solves are
complete. Table and results paragraph follow.

**Item 2 — per-tier tuning at M/L.** Plan and cost in `docs/tuning_plan_full.md`: 13 single-seed T1 runs (U-Net
wide/w64, FNO m96/w48, ViT patch and positional grid sized to the tier, GNN ×8 multiscale), ≈ 47 GPU-h, selection
on val only; running under the GPU driver now (M/T1 staging). Re-runs for changed configs are costed when the
winners are known.

**Item 3 — derivation.** `paper/appendix_derivation.md`: the zero-shot T4 error equals 1 − r_train/r_eval because the
cumulative current scales with the window radius (injected current ∝ r², spread ∝ r, visits per pixel constant at
b = r/10); the scale-aware factor cancels it; the T1 analogue and the assumptions are stated.

**Item 4 — WP6.** MgNO has an MIT, pure-PyTorch official implementation reproducing the paper's 0.57 M parameters:
vendored as model `mgno` (`ampscape/models/mgno.py`, `docs/THIRD_PARTY_LICENSES.md`), smoke-tested; four seed-1 runs
(T1/T4 × S/M, ≈ 6 GPU-h) are in the driver plan. HANO's public repository no longer contains the published model in
runnable form; recorded in `docs/wp6_implementations.md` and `docs/prior_art.md`; it stays in related work.

**Item 5 — submission format.** `docs/submission.md`, `scripts/submit_results.py` (validate / make-entry / append /
seed-baselines), 30 tests; the leaderboard (`aux/leaderboard/results.jsonl` + rendered README) is seeded locally
with 142 entries and will be pushed after the tuning pass.

**Harness defect (found while building item 5, fixed, affects reported numbers):** the T4 exact block-1 comparison
branch was unreachable, so every learned-model "vs block-1" number so far (reference evaluations, Pareto learned
rows, the status headline, the results draft) was the production-target number on the full test_id split. Fixed with
a regression test; the evaluation is now restricted to the reference subset (400 M / 24 L landscapes) so learned and
solver rows share the surface. The 28 wrong evaluation directories are set aside; the driver recomputes them from the
Hub-stored predictions when M/T4 and L/T4 are staged, after which the Pareto tables, the status headline and the
results section are regenerated. The solver block rows, the in-tier production-target rows and every other table are
unaffected.

**Scratch incident 20:20Z:** staging three T3 groups by hand on top of two groups left from the GNN phase filled the
quota; two voltage-head runs and ≈ 300 pre-solve shards failed and were redone; staging now goes only through the
driver (plan files, pinned groups). Driver and keepalive restarted 21:05Z; offloader paused while CPU evaluations
read local predictions.

**Order of the remaining work:** warm-start evaluations → T1V runs → tuning selection and re-runs → T4 reference
recompute → MgNO runs → regenerate tables/figures/sections → leaderboard push → `paper/draft.md` (step 6).

## Phase 10-full — final summary (2026-10-04; tables `paper/tables/`, figures `paper/figures/`, all regenerated by `scripts/paper_figures.py`)

**Done:** 110 training runs (U-Net, FNO, ViT, GNN × T1/T4 and U-Net/FNO × T3, × S/M/L × 3 seeds; WP4; six
scale-aware variants), 56 transfer legs (XL/XXL), WP7. All on the Hub (`aux/results/runs_full/`). Cost 401 GPU jobs,
430.1 GPU-h vs ≈ 1,081 nominal (`docs/tables/gpu_usage.md`); 11 calendar days incl. 6 idle. Daemons stopped.

**Headline (rel-L2 on test_id, mean over 3 seeds; `paper/tables/baselines_sml.md`):**

| task | model | S | M | L |
|---|---|---|---|---|
| T1 | U-Net / FNO / ViT / GNN | 0.114 / 0.199 / 0.218 / 0.561 | 0.212 / 0.248 / 0.419 / 0.849 | 0.397 / 0.361 / 0.648 / 1.067 |
| T3 | U-Net / FNO | 0.111 / 0.253 | 0.202 / 0.284 | 0.379 / 0.347 |
| T4 | U-Net / FNO / ViT / GNN | 0.041 / 0.051 / 0.052 / 0.066 | 0.051 / 0.079 / 0.094 / 0.099 | 0.081 / 0.120 / 0.159 / 0.142 |

- T4 against the exact block-1 map (seed 1; `paper/tables/t4_pareto_{M,L}.md`): at M U-Net 0.051, FNO 0.079, GNN
  0.099 at 1–16 ms/landscape vs the production block-3 solver 0.029 at 111 s; at L U-Net 0.080, FNO 0.120, GNN 0.142
  at 5–66 ms vs block 5 at 0.032 and 566 s.
- The GNN is far behind on T1 (its multi-scale graph does not resolve long-range pairwise flow) and competitive on
  T4 (local Omniscape windows), the opposite of the convolutional models' relative strengths.
- Scale transfer (`paper/tables/scale_transfer.md`): zero-shot XL/XXL fails on magnitude (T4 rel-L2 ≈ 0.52 / 0.75
  for every model, = 1 − r_L/r_tier); the scale-aware target recovers T4 to 0.16–0.22 at XL and 0.20–0.34 at XXL
  (U-Net 0.189 / 0.312, FNO 0.162 / 0.201, GNN 0.223 / 0.341) and the FNO on T1 to 0.57 / 0.67; U-Net and GNN on T1
  stay near rel-L2 0.8–1.0 (receptive field). Rankings are unchanged by the variant.
- OOD at the training tier (`paper/ood_analysis.md`): held-out table + contrast costs ≤ 18 % (ViT L excepted);
  published real surfaces cost 30–52 % on T4 at S; the held-out-region split is *easier* (0.65–1.0×) because of its
  composition — to be presented as a leakage control, not a stress test.
- WP4 (`docs/wp4_data_scaling.md`): under the official step budget the U-Net saturates by 20k landscapes at S; the
  FNO stays data-limited. WP7 (`docs/wp7_demo.md`): study-level conclusions reproduced at ≈ ×11,000 lower cost.

**Phase 12 state (complete as a draft package):** `paper/outline.md`; seven section drafts under `paper/sections/`
(dataset/generation, tasks/metrics, splits/OOD, baselines/protocol, related work with 62 verified sources + source
table, results, discussion/limitations/ethics/maintenance) with every number tagged to its source file and no TODO
markers left (the only unavailable fact — non-source rel-L2 of learned models against the block-1 map — is stated as
such); brief §14 deliverables `paper/baselines.md`, `paper/dataset_statistics.md`, `paper/ood_analysis.md`; one script
(`scripts/paper_figures.py`) regenerates 12 figures and 8 tables under `paper/`. Open for the owner: the two
practitioner cost quotes flagged in `paper/sections/related_work_sources.md` need a human check; the public repo
surfaces in novelty searches (double-blind); DOI at submission.

## 2026-10-03: scale-aware target variant — result (seed 1, trained at L, zero-shot at XL/XXL; `paper/tables/scale_transfer.md`)

| task / model | L (trained) | XL zero-shot → scale-aware | XXL zero-shot → scale-aware |
|---|---|---|---|
| T4 U-Net | 0.080 | 0.515 → **0.189** | 0.749 → **0.312** |
| T4 FNO | 0.120 | 0.532 → **0.162** | 0.765 → **0.201** |
| T4 ViT | 0.161 | 0.538 → **0.203** | — |
| T1 U-Net | 0.369 | 1.250 → 0.957 | 4.43 → 0.987 |
| T1 FNO | 0.411 | 0.707 → **0.572** | 1.502 → **0.671** |
| T1 ViT | 0.617 | 0.768 → 0.656 | — |

(rel-L2 on test_id; zero-shot values are the 3-seed means of the official configs.) Making the target scale-free with
the quantity that sets the current magnitude — the Omniscape radius for T4, the valid-pixel count for T1 — removes most
of the zero-shot transfer error for T4 (the radius factor is exactly the 1 − 1/2 and 1 − 1/4 seen before) and for the
FNO on T1; the U-Net on T1 stays near rel-L2 1 at XL/XXL (its receptive field, not the magnitude, is the limit) and
the ViT's structural problem is unchanged. Rankings (Spearman) are the same as zero-shot in every case. No XL/XXL data
entered training or the inverse transform. At L the variant equals the official run for T4 (k = 1) and differs within
seed noise for T1. Figure: `paper/figures/scale_transfer.png`.

**Incident 2026-10-03 01:00–02:15Z (caught by the watchdog in an hour):** pre-staging the S/M groups for the gated GNN
phase pushed scratch over the transfer threshold and held the last five variant transfer legs, which in turn gated the
GNN phase. Fixed: no pre-staging for a gated phase; the hold may evict any group whose next use is later than the held
leg. GNN phase started 02:50Z (18 runs + 12 transfers + variant).

## 2026-10-02 reconnect: inventory, incident, restart

**Inventory (from disk and the Hub, `aux/results/runs_full/`):** all 84 training runs of P1–P3 and WP4 are complete
and on the Hub with results (every T4 M/L run also has its exact-reference evaluation). Scale transfer: 18 of 30
legs done (all T1 at XL and XXL, 3 seeds; T4 seed-1 at XL for U-Net/FNO/ViT) — remaining 12: T4 XL seeds 2–3 (6)
and T4 XXL (6). Not started: scale-aware variants (6 L runs + 10 transfers), GNN (18 runs), GNN transfers (12),
GNN variant (2 + 4). Nominal remaining 772 GPU-h (GNN 578 of it); at the measured 3–7× faster training the realistic
remainder is ≈ 200–300 GPU-h.

**Incident:** the driver and the offloader never died — both ran through the week — but the driver was deadlocked
since 26 Sep 03:30Z: after the XXL/T1 group was released it refused to stage XL/T4 because the transfer-group staging
limit (201 GB = 245 − 4 × 11) sat below the scratch floor plus one XL group (156 + 61 GB), so nothing could be staged
and the queue stayed empty for six days. Silent because the hold was logged only as "does not fit". Fix: the limit
is now measured against the hard 280 GB guard (280 − 3 × 11 = 247; three transfer legs in flight), and the monitor
has a watchdog that reports an empty queue while jobs are pending. Six calendar days lost; no results lost.

**Restart (detached):** `scripts/slurm/gpu/keepalive.sh` under `setsid nohup` restarts the driver whenever its lease
pid is dead and the offloader whenever none runs (every 5 min; `logs/keepalive.log`). One-line runbook entry in
`docs/phase10_full_schedule.md` §3. It survives a dead session; a login-node reboot still needs the line re-run
(PACE login nodes allow no user cron/systemd). Driver restarted 13:54Z; XL/T4 staging; T4 transfer legs next.

**Calendar estimate at the measured rates:** transfers ≈ 1 day (12 legs + the variants' 10), scale-aware L runs
≈ 0.5 day in parallel, GNN 18 runs ≈ 2–3 days (L/T4 GNN is the long pole, 2-h legs re-queued), GNN transfers and
variant ≈ 1 day → **≈ 4–5 calendar days** if nothing stalls. Weekly report, or on failures.

## v1.0.2 (metadata only) — done 2026-09-26 02:40Z (owner approval)
- Audit of every hashed share: only the C3 macro-cell hash had a None key (synthetic XL). The block-order hash
  (real tiles, seed|stratum|block), the synthetic seed-family hash and the strict-XXL geometric check use defined keys;
  real-tile val cells at L are assigned by the block rule and were never subject to C3.
- Second defect found during the audit and fixed in the same release: the Hub split lists `splits/<subset>/<split>.parquet`
  held only the last published tier's ids (per-tier uploads overwrote each other; `splits/full/train.parquet` had L's
  12,613 ids). Rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 /
  ood_region 16,720); `publish_index` now builds them from every tier's index. The per-tier index `split` column was
  always complete, so loaders were unaffected.
- XL after the correction: train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400 (25.3 % train+val;
  synthetic share 0.3635 of the moved landscapes; 28 real val landscapes drawn among the kept cells).
- Published: `index/XL.parquet`, `splits/**`, card, Croissant 1.0.2 (validated, 0 warnings); local caches refreshed;
  13 transfer runs re-aggregated on the new XL test_id (`scripts/reaggregate_transfer.py`, per-sample metrics kept);
  CITATION 1.0.2; tags `v1.0.2` on GitHub and the Hub. CI: `tests/test_scripts_parse.py` (every script non-empty and
  parseable, shell syntax-checked) — 75 files.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

---

# Status — 2026-10-05 05:30Z: item 1 result (no warm-start gain at S/M); tuning at M favours every per-tier candidate; L tier and reference recompute queued

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.051 | 0.079 | 0.120 |
| T4 ViT | 0.052 | 0.099 | 0.159 |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Phase 13 — owner's six items (started 2026-10-04 evening)

**Editing rule applied** to all `paper/sections/*.md` (operational narrative removed; one reproducibility paragraph;
moved material in `paper/appendix_notes.md`). Several sections remain above the length targets with dense content
only; the cut to a 9-page main text happens when `paper/draft.md` is assembled (step 6).

**Item 1 — result so far (`docs/acceleration_report.md`, `docs/tables/acceleration.md`):** no acceleration at S or M —
10 → 10 and 12 → 13 PCG iterations, wall time within ±5 %; the predicted voltage maps are accurate (median per-landscape
MAE 0.05–0.14 V on ≈ 1 V fields) but their Kirchhoff residual is 80–580× the zero start's (pixel-wise errors are
high-frequency; PCG removes them in the same ≈ 10–16 iterations it needs from zero). Reported as a negative result with
the explanation; L and the T1 first-pair rows pending (their runs are queued behind scratch).

**Item 1 — solver-acceleration metric (setup).** The official T1/T3 models predict current maps, so the warm start needs
voltage-predicting counterparts: `train.py --target voltage` (same floor-log transform) for T3; six seed-1 runs
(U-Net, FNO × S/M/L, ≈ 9 GPU-h) are training/queued, and a waiter submits the CPU warm-start evaluations
(`evaluate.py --acceleration`, test_id and test_ood) per finished run. T1 `points` shards store no pair voltages, so
the first pair of every T1 landscape (ground = lowest label, source = second label, unit current — the pair the
metric uses) is being pre-solved on CPU (`pair1_voltage.jl`, 45 array tasks, `aux/t1_pair1/`, ≈ 90 CPU-h); the
same voltage head then trains on those systems as task `T1V` (six runs, ≈ 9 GPU-h) once the pre-solves are
complete. Table and results paragraph follow.

**Item 2 — preliminary (M tier, val loss, `scripts/tuning_select.py`):** every candidate beats the official config by
more than the seed spread — U-Net w64 −41 %, FNO w48 −7 %, ViT patch-16/native-grid −75 % (the resolution-sized ViT
works), GNN ×8 multiscale −19 % (run still in progress). If L confirms, all four configs change at both tiers:
≈ 60 re-runs plus transfers and scale-aware variants, ≈ 300 GPU-h — the exact estimate is recorded before launch.
MgNO at M (T1): rel-L2 0.412 with 0.58 M parameters (U-Net 0.238 / 7.8 M, FNO 0.266 / 33.6 M).

**Item 2 — per-tier tuning at M/L (plan).** Plan and cost in `docs/tuning_plan_full.md`: 13 single-seed T1 runs (U-Net
wide/w64, FNO m96/w48, ViT patch and positional grid sized to the tier, GNN ×8 multiscale), ≈ 47 GPU-h, selection
on val only; running under the GPU driver now (M/T1 staging). Re-runs for changed configs are costed when the
winners are known.

**Item 3 — derivation.** `paper/appendix_derivation.md`: the zero-shot T4 error equals 1 − r_train/r_eval because the
cumulative current scales with the window radius (injected current ∝ r², spread ∝ r, visits per pixel constant at
b = r/10); the scale-aware factor cancels it; the T1 analogue and the assumptions are stated.

**Item 4 — WP6.** MgNO has an MIT, pure-PyTorch official implementation reproducing the paper's 0.57 M parameters:
vendored as model `mgno` (`ampscape/models/mgno.py`, `docs/THIRD_PARTY_LICENSES.md`), smoke-tested; four seed-1 runs
(T1/T4 × S/M, ≈ 6 GPU-h) are in the driver plan. HANO's public repository no longer contains the published model in
runnable form; recorded in `docs/wp6_implementations.md` and `docs/prior_art.md`; it stays in related work.

**Item 5 — submission format.** `docs/submission.md`, `scripts/submit_results.py` (validate / make-entry / append /
seed-baselines), 30 tests; the leaderboard (`aux/leaderboard/results.jsonl` + rendered README) is seeded locally
with 142 entries and will be pushed after the tuning pass.

**Harness defect (found while building item 5, fixed, affects reported numbers):** the T4 exact block-1 comparison
branch was unreachable, so every learned-model "vs block-1" number so far (reference evaluations, Pareto learned
rows, the status headline, the results draft) was the production-target number on the full test_id split. Fixed with
a regression test; the evaluation is now restricted to the reference subset (400 M / 24 L landscapes) so learned and
solver rows share the surface. The 28 wrong evaluation directories are set aside; the driver recomputes them from the
Hub-stored predictions when M/T4 and L/T4 are staged, after which the Pareto tables, the status headline and the
results section are regenerated. The solver block rows, the in-tier production-target rows and every other table are
unaffected.

**Scratch incident 20:20Z:** staging three T3 groups by hand on top of two groups left from the GNN phase filled the
quota; two voltage-head runs and ≈ 300 pre-solve shards failed and were redone; staging now goes only through the
driver (plan files, pinned groups). Driver and keepalive restarted 21:05Z; offloader paused while CPU evaluations
read local predictions.

**Order of the remaining work:** warm-start evaluations → T1V runs → tuning selection and re-runs → T4 reference
recompute → MgNO runs → regenerate tables/figures/sections → leaderboard push → `paper/draft.md` (step 6).

## Phase 10-full — final summary (2026-10-04; tables `paper/tables/`, figures `paper/figures/`, all regenerated by `scripts/paper_figures.py`)

**Done:** 110 training runs (U-Net, FNO, ViT, GNN × T1/T4 and U-Net/FNO × T3, × S/M/L × 3 seeds; WP4; six
scale-aware variants), 56 transfer legs (XL/XXL), WP7. All on the Hub (`aux/results/runs_full/`). Cost 401 GPU jobs,
430.1 GPU-h vs ≈ 1,081 nominal (`docs/tables/gpu_usage.md`); 11 calendar days incl. 6 idle. Daemons stopped.

**Headline (rel-L2 on test_id, mean over 3 seeds; `paper/tables/baselines_sml.md`):**

| task | model | S | M | L |
|---|---|---|---|---|
| T1 | U-Net / FNO / ViT / GNN | 0.114 / 0.199 / 0.218 / 0.561 | 0.212 / 0.248 / 0.419 / 0.849 | 0.397 / 0.361 / 0.648 / 1.067 |
| T3 | U-Net / FNO | 0.111 / 0.253 | 0.202 / 0.284 | 0.379 / 0.347 |
| T4 | U-Net / FNO / ViT / GNN | 0.041 / 0.051 / 0.052 / 0.066 | 0.051 / 0.079 / 0.094 / 0.099 | 0.081 / 0.120 / 0.159 / 0.142 |

- T4 against the exact block-1 map (seed 1; `paper/tables/t4_pareto_{M,L}.md`): at M U-Net 0.051, FNO 0.079, GNN
  0.099 at 1–16 ms/landscape vs the production block-3 solver 0.029 at 111 s; at L U-Net 0.080, FNO 0.120, GNN 0.142
  at 5–66 ms vs block 5 at 0.032 and 566 s.
- The GNN is far behind on T1 (its multi-scale graph does not resolve long-range pairwise flow) and competitive on
  T4 (local Omniscape windows), the opposite of the convolutional models' relative strengths.
- Scale transfer (`paper/tables/scale_transfer.md`): zero-shot XL/XXL fails on magnitude (T4 rel-L2 ≈ 0.52 / 0.75
  for every model, = 1 − r_L/r_tier); the scale-aware target recovers T4 to 0.16–0.22 at XL and 0.20–0.34 at XXL
  (U-Net 0.189 / 0.312, FNO 0.162 / 0.201, GNN 0.223 / 0.341) and the FNO on T1 to 0.57 / 0.67; U-Net and GNN on T1
  stay near rel-L2 0.8–1.0 (receptive field). Rankings are unchanged by the variant.
- OOD at the training tier (`paper/ood_analysis.md`): held-out table + contrast costs ≤ 18 % (ViT L excepted);
  published real surfaces cost 30–52 % on T4 at S; the held-out-region split is *easier* (0.65–1.0×) because of its
  composition — to be presented as a leakage control, not a stress test.
- WP4 (`docs/wp4_data_scaling.md`): under the official step budget the U-Net saturates by 20k landscapes at S; the
  FNO stays data-limited. WP7 (`docs/wp7_demo.md`): study-level conclusions reproduced at ≈ ×11,000 lower cost.

**Phase 12 state (complete as a draft package):** `paper/outline.md`; seven section drafts under `paper/sections/`
(dataset/generation, tasks/metrics, splits/OOD, baselines/protocol, related work with 62 verified sources + source
table, results, discussion/limitations/ethics/maintenance) with every number tagged to its source file and no TODO
markers left (the only unavailable fact — non-source rel-L2 of learned models against the block-1 map — is stated as
such); brief §14 deliverables `paper/baselines.md`, `paper/dataset_statistics.md`, `paper/ood_analysis.md`; one script
(`scripts/paper_figures.py`) regenerates 12 figures and 8 tables under `paper/`. Open for the owner: the two
practitioner cost quotes flagged in `paper/sections/related_work_sources.md` need a human check; the public repo
surfaces in novelty searches (double-blind); DOI at submission.

## 2026-10-03: scale-aware target variant — result (seed 1, trained at L, zero-shot at XL/XXL; `paper/tables/scale_transfer.md`)

| task / model | L (trained) | XL zero-shot → scale-aware | XXL zero-shot → scale-aware |
|---|---|---|---|
| T4 U-Net | 0.080 | 0.515 → **0.189** | 0.749 → **0.312** |
| T4 FNO | 0.120 | 0.532 → **0.162** | 0.765 → **0.201** |
| T4 ViT | 0.161 | 0.538 → **0.203** | — |
| T1 U-Net | 0.369 | 1.250 → 0.957 | 4.43 → 0.987 |
| T1 FNO | 0.411 | 0.707 → **0.572** | 1.502 → **0.671** |
| T1 ViT | 0.617 | 0.768 → 0.656 | — |

(rel-L2 on test_id; zero-shot values are the 3-seed means of the official configs.) Making the target scale-free with
the quantity that sets the current magnitude — the Omniscape radius for T4, the valid-pixel count for T1 — removes most
of the zero-shot transfer error for T4 (the radius factor is exactly the 1 − 1/2 and 1 − 1/4 seen before) and for the
FNO on T1; the U-Net on T1 stays near rel-L2 1 at XL/XXL (its receptive field, not the magnitude, is the limit) and
the ViT's structural problem is unchanged. Rankings (Spearman) are the same as zero-shot in every case. No XL/XXL data
entered training or the inverse transform. At L the variant equals the official run for T4 (k = 1) and differs within
seed noise for T1. Figure: `paper/figures/scale_transfer.png`.

**Incident 2026-10-03 01:00–02:15Z (caught by the watchdog in an hour):** pre-staging the S/M groups for the gated GNN
phase pushed scratch over the transfer threshold and held the last five variant transfer legs, which in turn gated the
GNN phase. Fixed: no pre-staging for a gated phase; the hold may evict any group whose next use is later than the held
leg. GNN phase started 02:50Z (18 runs + 12 transfers + variant).

## 2026-10-02 reconnect: inventory, incident, restart

**Inventory (from disk and the Hub, `aux/results/runs_full/`):** all 84 training runs of P1–P3 and WP4 are complete
and on the Hub with results (every T4 M/L run also has its exact-reference evaluation). Scale transfer: 18 of 30
legs done (all T1 at XL and XXL, 3 seeds; T4 seed-1 at XL for U-Net/FNO/ViT) — remaining 12: T4 XL seeds 2–3 (6)
and T4 XXL (6). Not started: scale-aware variants (6 L runs + 10 transfers), GNN (18 runs), GNN transfers (12),
GNN variant (2 + 4). Nominal remaining 772 GPU-h (GNN 578 of it); at the measured 3–7× faster training the realistic
remainder is ≈ 200–300 GPU-h.

**Incident:** the driver and the offloader never died — both ran through the week — but the driver was deadlocked
since 26 Sep 03:30Z: after the XXL/T1 group was released it refused to stage XL/T4 because the transfer-group staging
limit (201 GB = 245 − 4 × 11) sat below the scratch floor plus one XL group (156 + 61 GB), so nothing could be staged
and the queue stayed empty for six days. Silent because the hold was logged only as "does not fit". Fix: the limit
is now measured against the hard 280 GB guard (280 − 3 × 11 = 247; three transfer legs in flight), and the monitor
has a watchdog that reports an empty queue while jobs are pending. Six calendar days lost; no results lost.

**Restart (detached):** `scripts/slurm/gpu/keepalive.sh` under `setsid nohup` restarts the driver whenever its lease
pid is dead and the offloader whenever none runs (every 5 min; `logs/keepalive.log`). One-line runbook entry in
`docs/phase10_full_schedule.md` §3. It survives a dead session; a login-node reboot still needs the line re-run
(PACE login nodes allow no user cron/systemd). Driver restarted 13:54Z; XL/T4 staging; T4 transfer legs next.

**Calendar estimate at the measured rates:** transfers ≈ 1 day (12 legs + the variants' 10), scale-aware L runs
≈ 0.5 day in parallel, GNN 18 runs ≈ 2–3 days (L/T4 GNN is the long pole, 2-h legs re-queued), GNN transfers and
variant ≈ 1 day → **≈ 4–5 calendar days** if nothing stalls. Weekly report, or on failures.

## v1.0.2 (metadata only) — done 2026-09-26 02:40Z (owner approval)
- Audit of every hashed share: only the C3 macro-cell hash had a None key (synthetic XL). The block-order hash
  (real tiles, seed|stratum|block), the synthetic seed-family hash and the strict-XXL geometric check use defined keys;
  real-tile val cells at L are assigned by the block rule and were never subject to C3.
- Second defect found during the audit and fixed in the same release: the Hub split lists `splits/<subset>/<split>.parquet`
  held only the last published tier's ids (per-tier uploads overwrote each other; `splits/full/train.parquet` had L's
  12,613 ids). Rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 /
  ood_region 16,720); `publish_index` now builds them from every tier's index. The per-tier index `split` column was
  always complete, so loaders were unaffected.
- XL after the correction: train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400 (25.3 % train+val;
  synthetic share 0.3635 of the moved landscapes; 28 real val landscapes drawn among the kept cells).
- Published: `index/XL.parquet`, `splits/**`, card, Croissant 1.0.2 (validated, 0 warnings); local caches refreshed;
  13 transfer runs re-aggregated on the new XL test_id (`scripts/reaggregate_transfer.py`, per-sample metrics kept);
  CITATION 1.0.2; tags `v1.0.2` on GitHub and the Hub. CI: `tests/test_scripts_parse.py` (every script non-empty and
  parseable, shell syntax-checked) — 75 files.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.

# Status — 2026-10-13 06:50Z: login-node OOM fixed at the source (sweeper during transfers, tested); phase 14 (tuned-config M re-runs) launched behind the phase 13c remainder

## Incident and fix (owner report 2026-10-13)
- With the keepalive and driver running, tmux/screen attaches were SIGKILLed and the owner's SSH session closed; later
  the Claude CLI session was killed while fixing it. Cause: the login node's 4 GB per-user memory cgroup does not
  reclaim clean page cache from our scratch I/O and OOM-kills instead (`memory.events` oom_kill 11 by 06:35Z). Dropping
  the cache *after* a staged group (the 02:00Z fix) was too late: `snapshot_download` with 8 workers filled the slice in
  seconds and the L/T1 and M/T4 staging subprocesses died at 23 % / 20 % (log lines ending in a progress bar).
- Kill-pattern audit (the other suspect): none in any tracked file, `work/`, git hooks or Claude settings/hooks — only
  `kill -0 <pid>` liveness probes and `kill $(cat <pidfile>)`. `tests/test_no_pattern_kills.py` now scans that scope
  (172 files). Stale `sync_L` pid/lease and the dead keepalive/driver leases removed.
- Fix (`ampscape.io.pagecache.CacheSweeper`, `stage_data.py`, `push_aux.py`; `tests/test_pagecache.py`): downloads per
  file with 2 workers, fsync + DONTNEED on each completed file, and a sweeper thread advising DONTNEED over the group /
  download-temp / xet-cache directories every 5 s for the whole transfer; the uploader (offloader) runs the same
  sweeper over the run directory and the xet cache. Keepalive sweep (every 10 min / above 2.5 GiB) unchanged.
- Acceptance test (login node, `memory.current` logged every 5 s): 101 new M/T4 shards, 10.4 GB in 70 s with 2
  workers — peak 1.08 GiB (0.82 before; requirement < 1.5 GiB). Live check after the restart: 1.0–1.3 GiB while the
  driver staged M/T4 and the offloader pushed runs concurrently.
- Runbook `docs/phase10_full_schedule.md` §3 and `CLAUDE.md` updated (rule: keep the cache low *during* transfers;
  acceptance test; widened audit scope).

## Phase 14 launched (owner approval 2026-10-13; 20 GPU-h gate lifted for it)
- Plan `docs/plans/phase13c_14_plan.json` = the 55 phase 13c jobs (40 done, 15 pending ≈ 38 GPU-h: six L tuning
  candidates, two T1V voltage heads at L, two at S running, three MgNO runs, two T4 reference backfills) followed by the 30
  phase 14 re-runs (`RERUN_M`, ≈ 117 GPU-h nominal): U-Net w64 (T1/T3/T4), FNO w48 (T1/T3/T4), ViT p16g16 (T1/T4),
  GNN ms8 (T1/T4), seeds 1–3, names `<model>_<task>_M_s<seed>_t2`. Keepalive restarted 06:42Z (pid in
  `logs/keepalive.pid`), driver 06:43Z (85 jobs, est 187 GPU-h), offloader 06:43Z. The driver was idle between
  2026-10-10 18:45Z and 2026-10-13 06:15Z (OOM-killed staging; no jobs lost).
- Storage: scratch 203 GB at launch; L/T1 (84 GB) waits for S/T1 to drain (three S jobs running), M/T4 is being staged.

## Tuning pass — what changed (`docs/tables/tuning_full.md`, selection on val only, T1 seed 1)

| tier | model | official → chosen | best val loss | params | decision |
|---|---|---|---|---|---|
| M | U-Net | base → **w64** | 0.0364 → 0.0213 (−41 %) | 7.8 → 31.0 M | re-run (phase 14) |
| M | FNO | m64 → **w48** | 0.0498 → 0.0463 (−7 %) | 33.6 → 75.5 M | re-run (phase 14) |
| M | ViT | patch 4 / grid 32 → **p16g16** | 0.2222 → 0.0559 (−75 %) | 3.0 M | re-run (phase 14) |
| M | GNN | ms → **ms8** | 0.2150 → 0.1633 (−24 %) | 0.2 M | re-run (phase 14) |
| L | all four | official kept *provisionally* | — | — | six candidates still pending |

- Every M candidate beat the official config by more than the official seed spread, so all four configs change at M.
- **L re-runs:** undecided — the L candidates (U-Net wide, FNO m96/w48, ViT p16g32/p8g64, GNN ms8; ≈ 28 GPU-h) are the
  first pending jobs of the merged plan. If any beats its official L config by more than the seed spread, an L re-run
  phase (3 seeds, all tasks, plus XL/XXL transfers and the scale-aware variant for that model) is costed and proposed
  before launch; the M re-runs do not depend on it.

## Other outstanding items
- **Item 1, solver-acceleration metric:** T3 rows complete at S/M/L for U-Net and FNO (`docs/tables/acceleration.md`):
  no acceleration anywhere — iterations 10 → 10 (S), 12 → 13 (M), 17 → 18/19 (L); time within −10 … +0.1 %; the
  warm-start residual is 80–3,900× the zero start's. Reported as a negative result with the explanation. T1V (first
  pair) heads: M runs trained (warm-start evaluations being backfilled by CPU jobs), S running, L pending.
- **Item 3, derivation:** done (`paper/appendix_derivation.md`, zero-shot T4 error = 1 − r_train/r_eval).
- **Item 4, WP6:** MgNO vendored (MIT, 0.57 M params); T1 M done (rel-L2 0.412 test_id, in `paper/baselines.md`);
  T1 S running, T4 S and T4 M pending. HANO not runnable from its public repository (documented).
- **Item 5, submission format:** done (`docs/submission.md`, `scripts/submit_results.py`, tests); leaderboard seeded
  locally with 142 entries, **not pushed** (Hub push is a gate — needs owner approval).
- **Item 6, `paper/draft.md`:** not assembled; waits for the M re-runs (tables, figures and sections regenerate from
  the tuned runs), then the leaderboard push and the 9-page cut.

Next: driver works through 13c remainder → phase 14; L re-run decision when the six L candidates finish (≈ 1 day);
weekly report or on schedule changes.

# Status — 2026-10-13 08:20Z: GPU policy check and probes; input pipeline fixed (packed node-local items, 2–3.5× per epoch); driver routes to H200/H100 first; plan reordered GNN-last

## Policy check (owner's question)
- QoS `coc-ice`: MaxSubmitPU 50, MaxTRESRunMinsPU gres/gpu = 1 920 min (32 GPU-h concurrent) — per user **per QoS**.
  `coe-ice` (also in the account's QoS list) carries the same limits and is a separate budget by Slurm semantics; it is
  the QoS for `coe-gpu`, where 25 of the 37 H100/H200 nodes live. `ice-gpu` (AllowQos=ALL) reaches 6 H100 + 6 H200 nodes
  under coc-ice. The driver uses ice-gpu/coc-gpu only; whether to use coe-gpu/coe-ice as a second 32 GPU-h budget is the
  owner's call (it would double concurrency, not per-job speed).
- Queue waits: 2–5 s on every pool at 07:02Z (H200 via ice-gpu and coe-gpu, H100, L40S); later H200 waits of 27 s,
  473 s, and one probe pending > 20 min on "Priority" (2 free H200 GPUs at the time) — H100 had ≥ 60 free GPUs all
  morning. The cu126 torch 2.14 wheel runs on H200/H100 (sm 9.0) under driver 615.71 (CUDA 13.4).

## Per-epoch probes (T4, M tier, official batch 8; `docs/tables/gpu_probe.md`)
| loader | workers | U-Net L40S | U-Net H200 | FNO L40S | FNO H200 |
|---|---|---|---|---|---|
| HDF5 (as run until today) | 6 | 170 s | 169 s | 208 s | 197 s |
| HDF5 | 12 | 94 s | 100 s | — | 116 s |
| (a) group copied to node NVMe, HDF5 | 12 | 93 s | — | — | — |
| (b) batch 16 + prefetch 4, HDF5 | 12 | 108 s | — | — | — |
| **(c) packed memmaps on node NVMe** | 6 / 12 | **87 s** | **56 s** | **183 s** | **59 s** |

- The epoch was bound by gzip-4/HDF5 decoding in the loader workers: the GPU type made no difference (H200 1.0–1.06×),
  12 workers nearly halved it, a local copy of the files changed nothing (CPU-bound, not I/O-bound), a larger batch did
  not help. Packing the loader's own tensors once per job (`ampscape/data/packed.py`, 41 GB in 57–95 s on the node's
  NVMe RAID; byte-identical items; RNG state preserved → the packed run reproduces the HDF5 run's losses exactly) makes
  the epoch GPU-bound: U-Net 3.0× and FNO 3.5× faster on H200 than before; FNO alone is 3.1× faster on H200 than on L40S.
- L tier: probe running (U-Net + FNO on T1 L, group fetched to the node's NVMe directly since scratch cannot hold L/T1
  until the M/T4 legs end) — numbers follow in this file.
- Applied (driver restarted 07:53Z, commit dec252d): every non-GNN training leg runs `PACK=1`; legs go to `ice-gpu` H200
  → H100 → `coc-gpu` L40S → A100 (spill after 3 pending on a type), all under coc-ice. GNN keeps the HDF5/graph path.
  Probing cost ≈ 2.5 GPU-h (three probes re-run after I deleted their output directory while they ran — my error).

## Plan order and storage
- The merged plan had the six GNN M re-runs in tier order; three started at 07:00–07:20Z and would have pinned M/T4 for
  ≈ 12 h while neither L/T1 nor M/T1 fits beside it under the 280 GB guard — all other work would have idled until ≈ 19:00Z.
  Cancelled them (1 epoch each; they resume from last.pt), restored "GNN strictly last", driver restarted on the reordered
  plan. Scratch 267 GB; incomplete M/T1 and L/T4 download fragments (10 GB, no staged marker) and probe outputs removed.

## Calendar (pending work: 42 jobs; measured L40S/HDF5 hours → projected with packing + H200)
| block | jobs | before (GPU-h) | after (GPU-h) | notes |
|---|---|---|---|---|
| 13c remainder: L tuning candidates, T1V L, MgNO, T4 reference backfills | 12 | 34 | 20 | GNN L tune (10 h) unchanged |
| phase 14 non-GNN M re-runs (U-Net w64, FNO w48, ViT p16g16) | 24 | 52 | 19 | ≈ 0.5–0.8 h per run on H200 |
| phase 14 GNN M re-runs | 6 | 65 | 65 | loader-bound by graph construction, not probed |
| total | 42 | 151 | 104 | GNN = 72 % of what remains |

Wall-clock, storage-serialized (one 150 GB staging window): M/T4 legs end ≈ 10:00Z → L/T1 staged → L tuning + T1V L
(≈ 2 h on H200) → M/T1, M/T3 re-runs (≈ 3 h) → GNN tail (7 jobs × 10–11 h in parallel; needs M/T4 + M/T1 + L/T1 staged in
turn) → **≈ 2026-10-14 05:00–15:00Z** (the range is the GNN L candidate's placement). Before (L40S, HDF5, original order):
the GNN-pinning deadlock plus 151 GPU-h at ≤ 16 concurrent legs ≈ 2026-10-15 00:00Z. The L re-run decision (six L
candidates) now lands ≈ 12:30Z today instead of tomorrow.

Next: L probe numbers → this file; owner decisions: (1) coe-gpu/coe-ice as a second budget, (2) a 12-worker/graph-caching
probe for the GNN (the remaining 72 %).

# Status — 2026-10-13 08:20Z: GPU policy check and probes; input pipeline fixed (packed node-local items, 2–3.5× per epoch); driver routes to H200/H100 first; plan reordered GNN-last

## Policy check (owner's question)
- QoS `coc-ice`: MaxSubmitPU 50, MaxTRESRunMinsPU gres/gpu = 1 920 min (32 GPU-h concurrent) — per user **per QoS**.
  `coe-ice` (also in the account's QoS list) carries the same limits and is a separate budget by Slurm semantics; it is
  the QoS for `coe-gpu`, where 25 of the 37 H100/H200 nodes live. `ice-gpu` (AllowQos=ALL) reaches 6 H100 + 6 H200 nodes
  under coc-ice. The driver uses ice-gpu/coc-gpu only; whether to use coe-gpu/coe-ice as a second 32 GPU-h budget is the
  owner's call (it would double concurrency, not per-job speed).
- Queue waits: 2–5 s on every pool at 07:02Z (H200 via ice-gpu and coe-gpu, H100, L40S); later H200 waits of 27 s,
  473 s, and one probe pending > 20 min on "Priority" (2 free H200 GPUs at the time) — H100 had ≥ 60 free GPUs all
  morning. The cu126 torch 2.14 wheel runs on H200/H100 (sm 9.0) under driver 615.71 (CUDA 13.4).

## Per-epoch probes (T4, M tier, official batch 8; `docs/tables/gpu_probe.md`)
| loader | workers | U-Net L40S | U-Net H200 | FNO L40S | FNO H200 |
|---|---|---|---|---|---|
| HDF5 (as run until today) | 6 | 170 s | 169 s | 208 s | 197 s |
| HDF5 | 12 | 94 s | 100 s | — | 116 s |
| (a) group copied to node NVMe, HDF5 | 12 | 93 s | — | — | — |
| (b) batch 16 + prefetch 4, HDF5 | 12 | 108 s | — | — | — |
| **(c) packed memmaps on node NVMe** | 6 / 12 | **87 s** | **56 s** | **183 s** | **59 s** |

- The epoch was bound by gzip-4/HDF5 decoding in the loader workers: the GPU type made no difference (H200 1.0–1.06×),
  12 workers nearly halved it, a local copy of the files changed nothing (CPU-bound, not I/O-bound), a larger batch did
  not help. Packing the loader's own tensors once per job (`ampscape/data/packed.py`, 41 GB in 57–95 s on the node's
  NVMe RAID; byte-identical items; RNG state preserved → the packed run reproduces the HDF5 run's losses exactly) makes
  the epoch GPU-bound: U-Net 3.0× and FNO 3.5× faster on H200 than before; FNO alone is 3.1× faster on H200 than on L40S.
- L tier (T1, batch 4, packed, H100; the group fetched straight to the node's NVMe in 19 min because scratch cannot hold
  L/T1 until the M/T4 legs end): U-Net 115 s/epoch vs 178 s in the official L40S/HDF5 run (1.55×), FNO 88 s vs 322 s
  (3.7×). The H200 twin of that probe waited 67 min on "Priority" and was cancelled; pool order is now H100 → H200 →
  L40S → A100 (driver restarted 09:05Z).
- Applied (driver restarted 07:53Z, commit dec252d): every non-GNN training leg runs `PACK=1`; legs go to `ice-gpu` H100
  → H200 → `coc-gpu` L40S → A100 (spill after 3 pending on a type), all under coc-ice. GNN keeps the HDF5/graph path.
  Probing cost ≈ 2.5 GPU-h (three probes re-run after I deleted their output directory while they ran — my error).

## Plan order and storage
- The merged plan had the six GNN M re-runs in tier order; three started at 07:00–07:20Z and would have pinned M/T4 for
  ≈ 12 h while neither L/T1 nor M/T1 fits beside it under the 280 GB guard — all other work would have idled until ≈ 19:00Z.
  Cancelled them (1 epoch each; they resume from last.pt), restored "GNN strictly last", driver restarted on the reordered
  plan. Scratch 267 GB; incomplete M/T1 and L/T4 download fragments (10 GB, no staged marker) and probe outputs removed.

## Calendar (pending work: 42 jobs; measured L40S/HDF5 hours → projected with packing + H200)
| block | jobs | before (GPU-h) | after (GPU-h) | notes |
|---|---|---|---|---|
| 13c remainder: L tuning candidates, T1V L, MgNO, T4 reference backfills | 12 | 34 | 20 | GNN L tune (10 h) unchanged |
| phase 14 non-GNN M re-runs (U-Net w64, FNO w48, ViT p16g16) | 24 | 52 | 19 | ≈ 0.5–0.8 h per run on H200 |
| phase 14 GNN M re-runs | 6 | 65 | 65 | loader-bound by graph construction, not probed |
| total | 42 | 151 | 104 | GNN = 72 % of what remains |

Wall-clock, storage-serialized (one 150 GB staging window): M/T4 legs end ≈ 10:00Z → L/T1 staged → L tuning + T1V L
(≈ 2 h on H200) → M/T1, M/T3 re-runs (≈ 3 h) → GNN tail (7 jobs × 10–11 h in parallel; needs M/T4 + M/T1 + L/T1 staged in
turn) → **≈ 2026-10-14 05:00–15:00Z** (the range is the GNN L candidate's placement). Before (L40S, HDF5, original order):
the GNN-pinning deadlock plus 151 GPU-h at ≤ 16 concurrent legs ≈ 2026-10-15 00:00Z. The L re-run decision (six L
candidates) now lands ≈ 12:30Z today instead of tomorrow.

Next: L probe numbers → this file; owner decisions: (1) coe-gpu/coe-ice as a second budget, (2) a 12-worker/graph-caching
probe for the GNN (the remaining 72 %).

# Status — 2026-10-13 17:05Z: packed input + H100/H200 pools in production; two QoS budgets; GNN legs off scratch; phase 14 M re-runs 24/30 done; L decision: FNO w48 re-runs needed (phase 15 plan, gated)

## Owner follow-ups (both done)
1. **GNN legs fetch their data group to the node's NVMe** (`train_full.sbatch LOCALDATA=1`): the probe's fetch had run on
   the compute node itself over outbound HTTPS (no proxy; `docs/compute_env.md` line 108) — the CLAUDE.md "no internet on
   compute nodes" assumption was outdated and is corrected. One lock-protected copy per node per group, reused by later
   legs on that node, 2-day cleanup; scratch staging stays as the fallback. The driver neither stages nor pins scratch
   groups for GNN legs and no longer holds them: all seven GNN jobs (six M re-runs, the L tuning candidate) started at
   16:22Z on H100 across both QoS while L/T1 stayed staged for the L candidates.
2. **coe-ice is a separate budget** — `scontrol show assoc_mgr` shows per-user per-QoS counters (coc-ice 1920(442)
   GPU-min / 50(7) jobs, coe-ice 0 / 0). The driver fills two pools of 16 two-hour legs (coc-ice: ice-gpu H100, H200,
   coc-gpu L40S, A100; coe-ice: coe-gpu H100, H200), ≤ 45 queued in total. Spill counts only legs pending with a real
   reason (just-submitted legs briefly show PD/None and had spilled two legs onto an H200 queue).

## Epoch time before → after packing (per epoch; before = L40S, HDF5 loader, 6 workers)
| run | before | after | GPU | speed-up |
|---|---|---|---|---|
| U-Net T4 M (probe, official) | 170 s | 56 s | H200 | 3.0× |
| FNO T4 M (probe, official) | 208 s | 59 s | H200 | 3.5× |
| U-Net w64 T1/T3 M (production re-runs) | 254 s | 108–111 s | H100 | 2.3× |
| FNO w48 T1 M (production re-run) | 361–371 s | 84 s | H200 | 4.3× |
| U-Net T1 L (probe, official) | 178 s | 115 s | H100 | 1.55× |
| FNO T1 L (probe, official) | 322 s | 88 s | H100 | 3.7× |

Packed items are byte-identical to the HDF5 loader's and, with the RNG state preserved, a packed run reproduces the
HDF5 run's losses exactly (`docs/tables/gpu_probe.md`). GNN legs keep the HDF5 graph path (unchanged epoch time).

## Progress
- Phase 14: 24 of 30 M re-runs done (all U-Net w64, FNO w48, ViT p16g16); the 6 GNN re-runs are running (started 16:22Z).
- 13c remainder: MgNO ×4, T1V S/M, T4 reference backfills done; the five non-GNN L tuning candidates finished 16:56Z;
  T1V L: FNO running, U-Net resubmitted on H100; GNN L candidate running.

## L re-run decision (val loss, seed 1, selection rule: beat the official by more than its seed spread)
| model | official L | best candidate | decision |
|---|---|---|---|
| U-Net | 0.0887 ± 0.0056 | wide 0.0832 (−6.1 %) | inside the spread → official kept |
| FNO | 0.0628 ± 0.0003 | **w48 0.0605 (−3.7 %)** | **config changes → L re-runs** |
| ViT | 0.2636 ± 0.0038 | p16g32 0.3895 (+48 %) | official kept |
| GNN | 0.3126 ± 0.0068 | ms8 — running (table row = epoch 1) | decided ≈ 2026-10-14 03:00Z |

Phase 15 plan file `docs/plans/phase15_plan.json`: 9 FNO w48 L runs (T1/T3/T4 × 3 seeds, ≈ 1.1 GPU-h each on H100
packed) + 2 scale-aware variants + 16 XL/XXL transfer legs (L40S) = **≈ 32 GPU-h**, ≈ 3–4 h wall with the two pools.
Above the 20 GPU-h gate → **waiting for the owner's approval**; the M-tier FNO rows already use w48.

## Revised completion estimate
- Current plan (13c + 14): the six GNN M re-runs and the GNN L candidate are the tail — ≈ 10–11 GPU-h each at
  ≈ 18–20 min/epoch (loader-bound by graph construction) in 2-h legs, local fetch ≈ 20 min per node → **≈ 2026-10-14 04:00Z**
  (before today's changes: ≈ 2026-10-15 00:00Z; this morning's estimate: 2026-10-14 05:00–15:00Z).
- Phase 15, if approved now: runs alongside the GNN tail in the free legs of both pools → done ≈ 2026-10-13 22:00Z.
- Then: regenerate tables/figures/sections from the tuned runs, leaderboard push (gate), `paper/draft.md`.

Next: GNN L decision when `gnn_T1_L_s1_tune_ms8` finishes; owner: phase 15 go/no-go.

# Status — 2026-10-13 17:25Z: packed input + H100/H200 pools in production; two QoS budgets; GNN legs off scratch; phase 14 M re-runs 24/30 done; L decision: FNO w48 re-runs needed (phase 15 plan, gated)

## Owner follow-ups (both done)
1. **GNN legs fetch their data group to the node's NVMe** (`train_full.sbatch LOCALDATA=1`): the probe's fetch had run on
   the compute node itself over outbound HTTPS (no proxy; `docs/compute_env.md` line 108) — the CLAUDE.md "no internet on
   compute nodes" assumption was outdated and is corrected. One lock-protected copy per node per group, reused by later
   legs on that node, 2-day cleanup; scratch staging stays as the fallback. The driver neither stages nor pins scratch
   groups for GNN legs and no longer holds them: all seven GNN jobs (six M re-runs, the L tuning candidate) started at
   16:22Z on H100 across both QoS while L/T1 stayed staged for the L candidates.
2. **coe-ice is a separate budget** — `scontrol show assoc_mgr` shows per-user per-QoS counters (coc-ice 1920(442)
   GPU-min / 50(7) jobs, coe-ice 0 / 0). The driver fills two pools of 16 two-hour legs (coc-ice: ice-gpu H100, H200,
   coc-gpu L40S, A100; coe-ice: coe-gpu H100, H200), ≤ 45 queued in total. Spill counts only legs pending with a real
   reason (just-submitted legs briefly show PD/None and had spilled two legs onto an H200 queue).

## Epoch time before → after packing (per epoch; before = L40S, HDF5 loader, 6 workers)
| run | before | after | GPU | speed-up |
|---|---|---|---|---|
| U-Net T4 M (probe, official) | 170 s | 56 s | H200 | 3.0× |
| FNO T4 M (probe, official) | 208 s | 59 s | H200 | 3.5× |
| U-Net w64 T1/T3 M (production re-runs) | 254 s | 108–111 s | H100 | 2.3× |
| FNO w48 T1 M (production re-run) | 361–371 s | 84 s | H200 | 4.3× |
| U-Net T1 L (probe, official) | 178 s | 115 s | H100 | 1.55× |
| FNO T1 L (probe, official) | 322 s | 88 s | H100 | 3.7× |

Packed items are byte-identical to the HDF5 loader's and, with the RNG state preserved, a packed run reproduces the
HDF5 run's losses exactly (`docs/tables/gpu_probe.md`). GNN legs keep the HDF5 graph path (unchanged epoch time).

## Progress
- Phase 14: 24 of 30 M re-runs done (all U-Net w64, FNO w48, ViT p16g16); the 6 GNN re-runs are running (started 16:22Z).
- 13c remainder: MgNO ×4, T1V S/M, T4 reference backfills done; the five non-GNN L tuning candidates finished 16:56Z;
  T1V L: FNO running, U-Net resubmitted on H100; GNN L candidate running.

## L re-run decision (val loss, seed 1, selection rule: beat the official by more than its seed spread)
| model | official L | best candidate | decision |
|---|---|---|---|
| U-Net | 0.0887 ± 0.0056 | wide 0.0832 (−6.1 %) | inside the spread → official kept |
| FNO | 0.0628 ± 0.0003 | **w48 0.0605 (−3.7 %)** | **config changes → L re-runs** |
| ViT | 0.2636 ± 0.0038 | p16g32 0.3895 (+48 %) | official kept |
| GNN | 0.3126 ± 0.0068 | ms8 — running (table row = epoch 1) | decided ≈ 2026-10-14 03:00Z |

Phase 15 plan file `docs/plans/phase15_plan.json`: 9 FNO w48 L runs (T1/T3/T4 × 3 seeds, ≈ 1.1 GPU-h each on H100
packed) + 2 scale-aware variants + 16 XL/XXL transfer legs (L40S) = **≈ 32 GPU-h**, ≈ 3–4 h wall with the two pools.
Above the 20 GPU-h gate → **waiting for the owner's approval**; the M-tier FNO rows already use w48.

## Measured on the GNN legs (node-local data, H100)
- Fetch from the Hub to the node's NVMe, 16 workers: M/T1 53 GB in 586 s, M/T4 51 GB in 503 s (286 s on a node that
  already had part of it), L/T1 79 GB in 752 s — ≈ 100 MB/s per node, seven nodes in parallel.
- GNN epoch: 715–766 s at M on H100 reading local NVMe vs 1 110 s on L40S from scratch this morning (1.5×); 1 105 s at L.
  → 30 epochs ≈ 6.2 h at M, 9.2 h at L (2-h legs; a leg landing on a fresh node re-fetches ≈ 10 min).
- Driver fix (17:20Z): a drain never takes a group whose next pending training use precedes the target's — L/T1 had been
  drained for L/T4, wanted only by CPU backfill evaluations, which held the pending U-Net T1V L run for 50 min.
- Surfaced: the 16 finished T4 L runs (official, scale-aware) still carry only the pre-2026-10-05 reference evaluation
  (`eval_t4_reference_prodtarget_wrong`); their recompute (CPU, needs L/T4 staged) is queued by the driver's backfill
  after the T1V L run — the Hub copies of those evaluations are the wrong ones until then.

## Revised completion estimate
- Current plan (13c + 14): the six GNN M re-runs end ≈ 2026-10-14 00:00Z and the GNN L candidate ≈ 02:30Z (started
  16:22Z; measured epoch times above) → **≈ 2026-10-14 02:30Z** for the GPU work, plus the 16 T4 L reference
  recomputes on CPU (≈ 20–30 min each, parallel) — before today's changes ≈ 2026-10-15 00:00Z; this morning's estimate
  2026-10-14 05:00–15:00Z.
- Phase 15, if approved now: runs alongside the GNN tail in the free legs of both pools → done ≈ 2026-10-13 22:00Z.
- Then: regenerate tables/figures/sections from the tuned runs, leaderboard push (gate), `paper/draft.md`.

Next: GNN L decision when `gnn_T1_L_s1_tune_ms8` finishes; owner: phase 15 go/no-go.


# Status — 2026-10-13 21:30Z: phase 15 launched (FNO w48 L re-runs, H200 first); Hub copies of the recomputed T4 reference evaluations being replaced; tables regenerate once the 16 L recomputes and the GNN L candidate are in

## Done since 17:25Z
- **Phase 15 launched** (owner approval; ≈ 32 GPU-h): the 27 jobs of `docs/plans/phase15_plan.json` run behind the
  phase 13c/14 remainder in one plan file (`docs/plans/phase13c_15_plan.json`). The four FNO T1 L legs (3 seeds +
  scale-aware) started 21:12Z on H200; the five T4 L legs follow once L/T1 is evicted and L/T4 staged; the 16 XL/XXL
  transfer legs run after their source runs on L40S.
- **H200 first.** Probe of the phase 15 config (FNO w48 + dist, T1 L, packed, batch 4): 103 s/epoch on H200 vs 188 s
  on H100 (1.8×; 2-s queue wait on coe-gpu for both). Pool order is now coe-gpu H200 → ice-gpu H200 → coe-gpu H100 →
  ice-gpu H100 → L40S → A100; coe-gpu before ice-gpu because ice-gpu reaches only the 6 shared H200 nodes (1 free GPU
  at 21:15Z; the first four legs sat on "Priority" and were cancelled before any epoch and resubmitted on coe-gpu).
- **T4 reference evaluations on the Hub.** All 28 T4 M/L runs with a recomputed exact-reference evaluation were already
  offloaded, and the `.offloaded` mark made the offloader skip them — the Hub still held the superseded
  `eval_t4_reference/`. The offloader now re-pushes an offloaded run's `eval_t4_reference/` whenever its sha256 differs
  from `.hub_pushed.json` (`reference_stale`, `tests/test_offload_reference.py`): the 12 M runs were replaced at 21:05Z;
  the 16 L runs (official + scale-aware U-Net/FNO/ViT/GNN) get their CPU recompute as soon as L/T4 is staged
  (≈ 22:30Z) and are re-pushed within 10 min of it. Tables/figures are regenerated only after the sha check over
  `runs/full/*_T4_[ML]_s*` passes.
- Housekeeping: a 16:18Z driver restart had left a 41.7 GB partial M/T1 staging without marker on scratch (neither used
  nor evicted); evicted by hand, scratch 257 → 218 GB.
- `scripts/tuning_effect.py` → `docs/tables/tuning_effect.md`: pre-tuning official runs vs tier-tuned `_t2` re-runs per
  task / tier / split (mean ± std over seeds, Δ %), plus the configuration-change table from `tuning_full.json`
  (generated at the end, with the regenerated tables).

## Running
- Phase 14 GNN M re-runs (6, H100, node-local data): five at epoch 19–21 of 30 at 21:30Z (≈ 750 s/epoch → ≈ 23:45Z),
  one at epoch 12 (restarted after a node's ECC error at 18:42Z → ≈ 01:15Z).
- GNN L tuning candidate (ms8): epoch 12 of 30 at 1 114 s/epoch → ≈ 03:00Z → L decision for GNN, `scripts/tuning_select.py` re-run.
- Phase 15: T1 L legs ≈ 22:10Z; L/T4 staging + T4 L legs + 16 recomputes ≈ 23:30Z; XL/XXL transfer legs ≈ 01:30Z.

## Next (this session, no further gate)
1. Verify the 16 L reference re-pushes (sha check), 2. GNN L decision, 3. `scripts/paper_figures.py` (baselines table,
T4 Pareto M/L, error-vs-tier, scale transfer, WP4, OOD, all-splits), `tuning_effect.py`, acceleration table, 4. report
what the tuning changed per model and tier relative to the pre-tuning table. A GNN L config change would need
≈ 3 × 9 GPU-h of GNN L re-runs — that would be a new gate.


# Status — 2026-10-14 00:45Z: phase 15 half done (T1 L runs finished, T4 L legs running); all 28 recomputed T4 reference evaluations replaced on the Hub; tables regenerate once phase 15 and the GNN L candidate finish

## Done since 17:25Z
- **Phase 15 launched** (owner approval; ≈ 32 GPU-h): the 27 jobs of `docs/plans/phase15_plan.json` run behind the
  phase 13c/14 remainder in one plan file (`docs/plans/phase13c_15_plan.json`). The four FNO T1 L legs (3 seeds +
  scale-aware) started 21:12Z on H200; the five T4 L legs follow once L/T1 is evicted and L/T4 staged; the 16 XL/XXL
  transfer legs run after their source runs on L40S.
- **H200 first.** Probe of the phase 15 config (FNO w48 + dist, T1 L, packed, batch 4): 103 s/epoch on H200 vs 188 s
  on H100 (1.8×; 2-s queue wait on coe-gpu for both). Pool order is now coe-gpu H200 → ice-gpu H200 → coe-gpu H100 →
  ice-gpu H100 → L40S → A100; coe-gpu before ice-gpu because ice-gpu reaches only the 6 shared H200 nodes (1 free GPU
  at 21:15Z; the first four legs sat on "Priority" and were cancelled before any epoch and resubmitted on coe-gpu).
- **T4 reference evaluations on the Hub.** All 28 T4 M/L runs with a recomputed exact-reference evaluation were already
  offloaded, and the `.offloaded` mark made the offloader skip them — the Hub still held the superseded
  `eval_t4_reference/`. The offloader now re-pushes an offloaded run's `eval_t4_reference/` whenever its sha256 differs
  from `.hub_pushed.json` (`reference_stale`, `tests/test_offload_reference.py`): the 12 M runs were replaced at 21:05Z;
  the 16 L runs (official + scale-aware U-Net/FNO/ViT/GNN) get their CPU recompute as soon as L/T4 is staged
  (≈ 22:30Z) and are re-pushed within 10 min of it. Tables/figures are regenerated only after the sha check over
  `runs/full/*_T4_[ML]_s*` passes.
- Housekeeping: a 16:18Z driver restart had left a 41.7 GB partial M/T1 staging without marker on scratch (neither used
  nor evicted); evicted by hand, scratch 257 → 218 GB.
- `scripts/tuning_effect.py` → `docs/tables/tuning_effect.md`: pre-tuning official runs vs tier-tuned `_t2` re-runs per
  task / tier / split (mean ± std over seeds, Δ %), plus the configuration-change table from `tuning_full.json`
  (generated at the end, with the regenerated tables).

## Since 21:30Z
- **T4 reference evaluations on the Hub: done.** The 16 L recomputes ran 00:28–00:39Z (CPU, predictions fetched onto the
  node's local disk) and the offloader replaced the Hub copies; sha256 of `eval_t4_reference/results.json` matches
  `.hub_pushed.json` for all 28 T4 M/L runs (checked 00:39Z).
- FNO w48 T1 L: the 3 seeds + scale-aware variant finished 22:10Z (val loss 0.0597–0.0607 vs official m64 0.0628) and
  are offloaded; the four T4 L legs started 00:18–00:39Z on H200 (103 s/epoch) → ≈ 01:45Z.
- Driver scratch accounting (three fixes, `DECISIONS.md` 2026-10-13/14): evictions only when they make the target fit;
  fit tests count stagings the quota reading has not shown yet and the predictions running legs will still write
  (legs held when their predictions would not fit under 295 GB); backfills fetch onto the CPU node. Cost: the T4 L legs
  started ≈ 00:18Z instead of 23:05Z.
- Node-local GNN legs keyed their evaluation groups `M_T4_M_<split>` (root dir name) instead of `hfcache_M_<split>`:
  fixed in place (`scripts/fix_local_root_tags.py`) and in the template; the two finished GNN T4 M re-runs got their
  reference evaluation with M/T4 fetched onto the CPU node (6.6 min each).
- Login-node memory: two stagings peaked at 2.6 GiB `memory.current` while the offloader pushed predictions at the
  same time (staging alone stays ≈ 1.1–1.2 GiB); no OOM, keepalive sweep at 2.5 GiB. To watch.

## Running
- Phase 15: T4 L legs (4) ≈ 01:45Z; then L/T4 evicted, L/T3 staged, T3 L legs (3) ≈ 03:15Z; XL/XXL transfer legs (16,
  L40S, sources done) once XL/T1 + XXL/T1 fit beside the L groups → ≈ 05:00–06:00Z.
- Phase 14: gnn_T1_M_s3_t2 at epoch 24 → ≈ 01:15Z; GNN L tuning candidate (ms8) at epoch 21 → ≈ 03:00Z.

## Next (this session, no further gate)
1. GNN L decision (`scripts/tuning_select.py`), 2. `scripts/paper_figures.py` (baselines table, T4 Pareto M/L,
error-vs-tier, scale transfer, WP4, OOD, all-splits), `tuning_effect.py`, acceleration table, 3. report what the tuning
changed per model and tier relative to the pre-tuning table. A GNN L config change would need ≈ 3 × 9 GPU-h of GNN L
re-runs — that would be a new gate.


# Status — 2026-10-14 07:40Z: phases 14 and 15 complete; all tables/figures regenerated with the tuned configs; T4 reference evaluations replaced on the Hub; GNN L config change gated (phase 16 plan)

## Done
- **Phase 15 (owner approval 21:00Z, ≈ 32 GPU-h, used 22.8):** 9 FNO w48 L re-runs (T1/T3/T4 × 3 seeds), 2 scale-aware
  variants, 16 XL/XXL transfer legs — all finished by 07:01Z; every run and transfer result is on the Hub
  (`aux/results/runs_full/`). Pool order H200 first (103 s/epoch vs 188 s on H100 for FNO w48 L; `docs/tables/gpu_probe.md`).
- **Phase 14:** the six GNN M re-runs and the GNN L candidate finished (node-local data, H100).
- **T4 reference evaluations:** all 28 T4 M/L runs (official, scale-aware; M and L) have the recomputed exact-reference
  evaluation on the Hub — sha256 of `eval_t4_reference/results.json` matches `.hub_pushed.json` for every run
  (the offloader re-pushes recomputed evaluations of offloaded runs; before 2026-10-13 21:05Z the Hub held the superseded ones).
- **Tables and figures regenerated** (`scripts/paper_figures.py`, commit 4401eeb): `docs/tables/baselines_full.md`
  (all runs), `paper/baselines.md`, `paper/tables/{baselines_sml,ood_degradation,scale_transfer,t4_pareto_M,t4_pareto_L}.md`
  and the matching figures; tier-tuned `_t2` runs supersede the pre-tuning run of the same seed in every panel (also the
  scale-aware `_t2_scalenorm` variant); `docs/tables/acceleration.md` (+ T1V S/M/L rows), `docs/tables/tuning_effect.md`
  (before/after per task, tier, split), `docs/tables/gpu_usage_tuning.md` (151 GPU-h since 2026-10-13 00:00Z).

## What the tuning changed (test_id rel-L2, mean over 3 seeds, official → tuned; `docs/tables/tuning_effect.md`)
| tier | model | config | T1 | T3 | T4 | params |
|---|---|---|---|---|---|---|
| M | U-Net | base → w64 | 0.212 → 0.187 (−12 %) | 0.202 → 0.192 (−5 %) | 0.051 → 0.042 (−18 %) | 7.8 → 31 M |
| M | FNO | m64 → w48 | 0.248 → 0.208 (−16 %) | 0.284 → 0.255 (−10 %) | 0.079 → 0.073 (−8 %) | 33.6 → 75.5 M |
| M | ViT | base → p16g16 | 0.419 → 0.306 (−27 %) | – | 0.094 → 0.103 (**+9 %**) | 3.0 M |
| M | GNN | ms → ms8 | 0.849 → 0.607 (−29 %) | – | 0.099 → 0.103 (**+5 %**) | 0.2 M |
| L | U-Net | base kept | – | – | – | |
| L | FNO | m64 → w48 | 0.361 → 0.299 (−17 %) | 0.347 → 0.323 (−7 %) | 0.120 → 0.116 (−3 %) | 33.6 → 75.5 M |
| L | ViT | base kept | – | – | – | |
| L | GNN | ms → ms8 **(re-runs gated)** | val loss 0.313 → 0.264 (−15 %) | | | |

Out-of-distribution splits move the same way (test_ood, ood_region in the table). Two selections did not transfer to T4:
the tuned ViT and GNN at M are better on T1 (−27 %, −29 %) but worse on T4 (+9 %, +5 %); by the selection rule (T1
validation loss) they are the official M configs — flagged for the owner's judgement. The GNN L candidate (ms8) beats
the official config by 15 % on validation loss, far outside the seed spread, so the rule changes the GNN L config too:
`docs/plans/phase16_plan.json` (6 GNN L runs ≈ 9.3 GPU-h each, 2 scale-aware, 16 transfer legs; **≈ 114 GPU-h, gate**).
Reusing the candidate itself as seed 1 of T1 would save ≈ 11 GPU-h. Until then the L tables carry the official GNN rows.

## Operations notes (details in DECISIONS.md 2026-10-13/14)
- Driver fixes overnight: scratch accounting (quota lag, predictions of running legs, eviction only when it makes the
  target fit, transfer-only groups under the transfer limit, transfer hold protecting only runnable legs, CPU backfills
  pin their group); backfills fetch predictions / M-T4 onto the CPU node; plan entries `local: true`; node-local legs
  keyed their evaluation groups by the local root's name (repaired in place, template fixed).
- GPU budget: 151 GPU-h since 2026-10-13 00:00Z (GNN M re-runs + L candidate 59, U-Net/FNO/ViT M re-runs 48,
  phase 15 23, 13c remainder 11, candidates 6, probes 4). The scale-aware FNO T4 L leg ran 3× slower on two H200 nodes
  than on a third — node-specific, cause unknown, one node excluded.
- Login-node memory: stagings peaked at 2.4–2.6 GiB `memory.current` twice while the offloader pushed predictions at
  the same time (1.0–1.4 GiB otherwise); no OOM. Both daemons (driver idle: all jobs done; offloader) keep running.
- GitHub: main pushed after every status update from now on (owner, 06:10Z).

## Next (owner decisions)
1. Phase 16 go/no-go (GNN L re-runs, ≈ 114 GPU-h; or ≈ 103 with the candidate reused as seed 1).
2. Whether the T4 M rows should keep the T1-selected ViT/GNN configs or the pre-tuning ones (rule vs per-task selection).
3. Then: leaderboard push (gate), `paper/draft.md`, acceleration metric write-up.


# Status — 2026-10-15 07:20Z: official configs chosen per model × task × tier on validation loss (tables regenerated); phase 16 (GNN L re-runs) launched; remaining items

## 1. Per-task configuration selection (owner rule, applied)
`scripts/tuning_decisions.py` → `docs/tables/tuning_decisions.md` / `.json`: the tuned configuration is official for a
(model, task, tier) only if its best validation loss, mean over seeds, beats the pre-tuning mean by more than the
pre-tuning standard error (seed std / √n); never on test metrics, never carried across tasks. Where only the T1 tuning
candidate exists, the seed-1 rule decides T1 alone.

| tier | model | tuned variant | T1 | T3 | T4 |
|---|---|---|---|---|---|
| M | U-Net | w64 | tuned (−19 %) | **pre-tuning** (−1.4 %, inside the spread) | tuned (−12 %) |
| M | FNO | w48 | tuned (−7 %) | tuned (−12 %) | tuned (−7 %) |
| M | ViT | p16g16 | tuned (−62 %) | – | **pre-tuning** (+17 %) |
| M | GNN | ms8 | tuned (−26 %) | – | **pre-tuning** (+8 %) |
| L | FNO | w48 | tuned (−4 %) | tuned (−9 %) | tuned (−3 %) |
| L | GNN | ms8 | tuned (−15 %, candidate rule; 3 seeds after phase 16) | – | decided after phase 16 |
| L | U-Net, ViT | – | pre-tuning (candidates inside the spread / worse) | | |

Every consumer reads the decisions file: `paper_figures.prefer_tuned` (baselines panels, OOD table, all-splits
table), the scale-transfer panel (also the scale-aware variant), the T4 Pareto tables, `tuning_effect.py` (now with an
"official" column) and the leaderboard seeder (`submit_results.py seed-baselines`). Tables/figures regenerated
(commit a151c88): the T4 M rows for ViT and GNN and the T3 M row for U-Net are back on the pre-tuning runs. The rule
is stated in `paper/sections/baselines_protocol.md` ("Configuration selection").

## 2. Phase 16 (owner approval, ≈ 114 GPU-h)
- The L candidate `gnn_T1_L_s1_tune_ms8` was trained under the official protocol (same code path as every `_t2`
  re-run, same data and normalisation statistics, batch 1, patience 8, seed 1; only the intended variant, the GPU type
  and the node-local data path differ — for FNO the candidate and the re-run gave identical metrics), so it is reused
  as seed 1: `runs/full/gnn_T1_L_s1_t2` is a copy (`REUSED_FROM.txt`). Saves ≈ 9 GPU-h.
- Launched 07:10Z (`docs/plans/phase13c_16_plan.json`): GNN T1 L seeds 2–3, GNN T4 L seeds 1–3, two scale-aware
  variants — seven runs on H200 with node-local data (five on one node sharing the copy) — plus 16 XL/XXL transfer
  legs (two already running for the reused seed). ≈ 105 GPU-h; GNN L epochs took 1 105–1 137 s on H100, H200 to be
  measured → training ≈ 9–10 h → **≈ 2026-10-15 17:30Z**, transfers and the T4 reference evaluations after.
- Then: `tuning_decisions.py` at L (GNN T1 with three seeds, GNN T4), regeneration, updated `tuning_effect.md`.

## 3. Remaining items (state as of now)
- **Derivation:** done — `paper/appendix_derivation.md` (zero-shot T4 error = 1 − r_train/r_eval; the scale-aware
  target removes it); referenced from the results section.
- **WP6 (MgNO / HANO):** MgNO vendored (MIT, 0.57 M params) and run at T1 S/M and T4 S/M (seed 1; rows in
  `paper/baselines.md`, MgNO in the error-vs-tier figure); HANO not runnable from its public repository
  (`docs/wp6_implementations.md`). Open: MgNO at L and seeds 2–3 if the owner wants it as a full baseline (≈ 10 GPU-h
  at L per task with packing — not planned).
- **Submission format:** done — `docs/submission.md`, `scripts/submit_results.py` (validate / make-entry / append /
  seed-baselines, now following the per-task decisions), tests; leaderboard seeded locally, **Hub push is a gate**
  (re-seed after phase 16, then push on approval).
- **`paper/draft.md`:** not assembled. All inputs exist (sections under `paper/sections/`, tables, figures,
  appendix); it waits for phase 16 so the L rows are final, then one pass to assemble and cut to length.
- **Acceleration metric (item 1):** `docs/tables/acceleration.md` complete for T3 and T1V heads at S/M/L — no
  acceleration anywhere (iterations 9–25 unchanged, time −8 … +0 %); the write-up for the paper is pending with the draft.

## Operations
- Driver idle-restarts between plans are harmless (keepalive, "all jobs done"); scratch 249 GB; login-node memory
  0.8 GiB. GitHub: pushed after every status update (main = origin).

# Status — 2026-10-15 20:45Z: phase 16 complete (GNN L re-runs, 79 GPU-h); GNN ms8 official at T1 L and T4 L; tables, figures and leaderboard regenerated; remaining items

## 1. Phase 16 (approved ≈ 114 GPU-h; used 79.4)
- Seven GNN L runs (T1 seeds 2–3, T4 seeds 1–3, two scale-aware variants) trained on H200 with node-local data,
  1 033–1 332 s per epoch (same as H100), 26–30 epochs each; seed 1 of T1 L is the reused tuning candidate
  (`REUSED_FROM.txt`, official protocol verified). All 16 XL/XXL transfer legs and the exact T4 reference
  evaluations of the four T4 L runs are done; every result file is on the Hub with its current hash
  (501 files checked over all T4 M/L and L runs — one pre-existing stale `results_transfer.json` of the pre-tuning
  `gnn_T4_L_s1`, updated 15 min after its 2026-10-04 push, is being re-pushed by the offloader).
- One incident: the H200 of `gnn_T4_L_s1_t2` (node `atl1-1-03-014-16-0`, GPU index 2) was silently faulted
  ("GPU requires reset", no memory ever allocated, no CUDA error raised, slurmstepd NVML errors). Detected after
  53 min with an empty `log.csv`, the job was cancelled by id, the node added to `logs/gpu_bad_nodes.txt` by hand and
  the driver resubmitted the run on another node (1.1 GPU-h lost; symptom and check recorded in
  `docs/phase10_full_schedule.md`, bad-nodes row).
- GPU usage: 71.7 GPU-h training/evaluation legs + 7.8 GPU-h transfers (`docs/tables/gpu_usage_tuning.md`);
  cumulative since 2026-10-13: 230.3 GPU-h.

## 2. Configuration decisions at L (validation loss only, `docs/tables/tuning_decisions.md`)

| tier | task | model | pre-tuning val loss (mean ± std, 3 seeds) | ms8 (mean, 3 seeds) | Δ | official |
|---|---|---|---|---|---|---|
| L | T1 | GNN | 0.3204 ± 0.0068 | 0.2693 | −15.9 % | **tuned (ms8)** |
| L | T4 | GNN | 0.0220 ± 0.0001 | 0.0202 | −8.3 % | **tuned (ms8)** |

Unlike at M (where ms8 was worse on T4, +8 %), the variant improves both tasks at L. The full matrix is unchanged
otherwise: tuned official for FNO w48 at T1/T3/T4 (M, L), U-Net w64 at T1/T4 M, ViT p16g16 at T1 M, GNN ms8 at T1 M;
pre-tuning for U-Net T3 M, ViT T4 M, GNN T4 M; U-Net and ViT at L stay pre-tuning. 15 decisions, 12 tuned.

## 3. Effect on the test metrics (`docs/tables/tuning_effect.md`, test_id, mean ± std over 3 seeds, official → tuned)

| task | tier | rel-L2 | MAE (log10) | Spearman |
|---|---|---|---|---|
| T1 | L | 1.067 ± 0.026 → 0.941 ± 0.160 (−11.8 %) | 0.416 → 0.382 (−8.2 %) | 0.834 → 0.861 |
| T4 | L | 0.142 ± 0.001 → 0.142 ± 0.001 (0.0 %) | 0.074 → 0.071 (−4.5 %) | 0.960 → 0.962 |

OOD splits move the same way (T1 test_ood −15.3 %, ood_region −13.2 %; T4 −0.2 % / −1.3 %). The ms8 T1 L seeds
disagree on rel-L2 (0.79 / 0.93 / 1.11) while their MAE and Spearman agree within 0.02 — rel-L2 at L is dominated by
a few high-current landscapes. Scale transfer (`paper/tables/scale_transfer.md`, now 3 seeds for GNN): T1 zero-shot
rel-L2 0.94 (L) → 1.42 ± 0.82 (XL) → 1.62 ± 0.58 (XXL); T4 0.142 → 0.498 → 0.739; the scale-aware T1 variant is worse
than zero-shot at XL (7.5) and similar at XXL (1.4).

## 4. Regenerated
`scripts/tuning_select.py`, `tuning_decisions.py`, `paper_figures.py --skip-stats`, `tuning_effect.py`,
`acceleration_table.py`: `docs/tables/{tuning_full,tuning_decisions,tuning_effect,baselines_full}.md`,
`paper/baselines.md`, `paper/tables/{baselines_sml,ood_degradation,scale_transfer,t4_pareto_L}.md`, figures
`error_vs_tier`, `ood_degradation`, `scale_transfer`, `t4_pareto_L`. Leaderboard rebuilt from scratch
(`submit_results.py seed-baselines`, 165 entries: 123 in-tier + 42 zero-shot; the previous file was kept aside in
`work/` because its id-based de-duplication would have retained the pre-tuning GNN L entries). Hub push of
`aux/leaderboard/` remains a gate.

## 5. Remaining items
- **Derivation:** done — `paper/appendix_derivation.md`.
- **WP6 (MgNO / HANO):** MgNO vendored and run at T1 S/M and T4 S/M (seed 1); HANO not runnable
  (`docs/wp6_implementations.md`). MgNO at L / seeds 2–3 not planned (≈ 10 GPU-h per task at L).
- **Submission format:** done — `docs/submission.md`, `scripts/submit_results.py`, 22 tests pass; leaderboard
  re-seeded with the final official baselines; Hub push on approval.
- **`paper/draft.md`:** not assembled; all inputs are now final (the L rows no longer change). Next step on
  go-ahead: assemble from `paper/sections/*`, the regenerated tables/figures and the appendices, refresh
  `paper/sections/results.md` (written 2026-10-05, before the tuned configurations), and cut to length.
- **Acceleration metric:** `docs/tables/acceleration.md` complete (no acceleration anywhere); paper write-up with
  the draft.

## Operations
No jobs queued; the plan is exhausted (driver idle-restarts by the keepalive are harmless). Offloader loop running.
Scratch 150 GB, login-node memory ≈ 1.1 GiB. GitHub: pushed after this update (main = origin).

# Status — 2026-10-16 02:00Z: leaderboard live, median rel-L2 in every main table, paper/draft.md assembled, verification pass complete (docs/verification_report.md)

## Owner requests of 2026-10-15, both done
1. **Leaderboard pushed** to `Xirro/AmpScape` under `aux/leaderboard/` (results.jsonl + README; official baselines as
   the first entries: in-tier S/M/L, zero-shot XL/XXL, T4 block-1 rows at M and L); the submission format is on the
   dataset card; `docs/submission.md` names the live location.
2. **Median rel-L2** next to the mean in every main results table (baselines, OOD, scale transfer, T4 Pareto, tuning
   effect, all-splits table), with one note in the metrics section.
3. **`paper/draft.md` exists** (commit 0a1d0d0, refined since): outline order, refreshed results and discussion with
   the tuned configurations, the per-task selection rule, the GNN L result, MgNO rows, the acceleration table and the
   derivation appendix; appendix with the full tables, fidelity, precision pass, licences, CLI and dataset statistics.
   Every number carries a source tag and `scripts/verify/check_draft_numbers.py` finds all 1,508 numeric tokens in
   their files. Main text ≈ 5,800 words plus six tables — above the 9-page target; a final cut is the next pass.

## Verification pass (owner request, as a reviewer: GitHub and Hub only) — `docs/verification_report.md`
| item | result |
|---|---|
| 1 fresh clone at `v1.0.2` on a compute node, lockfile env, `lite` loader, tests, `evaluate.py` on a published baseline | PASS (8/8 metrics match at printed precision; 198 tests pass); also at `main` (440 tests; whole `lite` = 517 shards / 25 GB). Undocumented: `uv` bootstrap, HF read token (private dataset), ssh clone |
| 2 regenerate every table/figure from the Hub only | PASS — byte-identical after publishing the acceleration evaluations that had never been pushed |
| 3 every number in the draft traced to its source file | PASS — 1,508 tokens, 0 untraceable |
| 4 card / Croissant / CITATION vs the index | PASS — 97/97 after fixes (Croissant date, `aux/` size, viewer-config note, Hub revisions stated) |
| 5 full Hub audit | tiers S, XXL, XL clean; M and L: first pass flagged 19 / 12 shards, all Hub CDN transfer errors with every sha256 matching, re-audit with the xet backend disabled clean → all five tiers PASS (3,067 shards, 14,798 files, 0 discrepancies). `aux/`: 9,443 files / 605 GB — two defective prediction files found and repaired (one had wrong size metadata on complete content, one was corrupt and was regenerated on a GPU; metrics unchanged); root cause fixed in the offloader |

Fixes committed: `load_from_hub` downloads only the subset's shards (it fetched the whole tier × group before: 30 GB
for "lite S/T1" at the tag, 1.9 GB now; test); acceleration evaluations published and in the offloader include list;
offloader ships only in-tier predictions with the whole-run push (test); Croissant `datePublished` = UTC tag date;
card statements corrected and re-pushed; stale push records and a stale doc copy refreshed; derivation appendix
updated to the current numbers; final GPU total 701.5 GPU-h / 773 jobs in `docs/tables/gpu_usage.md`.

## Owner decisions needed
- **Code tag for the paper** (`v1.0.2` predates the baseline scripts and the T4 reference branch; proposal `v1.1.0-paper`).
- **Reviewer access**: when the Hub repository becomes public; until then the README should say a read token is needed.
- **Draft length**: cut from ≈ 5,800 to ≈ 4,800 words of main text (candidates: Section 2, 4.1, 7.2 prose, Table 5 rows).

## Operations
No training queued; GPU use for the verification 1.0 GPU-h (two regeneration legs). Scratch ≈ 230 GB with XL/T4 and
XXL/T1 staged (evictable). Offloader loop and keepalive running. GitHub main = origin.

# Status — 2026-10-16 03:20Z: style memo written, paper rewritten as a NeurIPS 2026 LaTeX submission (9 content pages), PDF built

## Done (owner request 2026-10-16)
1. **Literature pass on form** — `docs/paper_style_memo.md`: PDEBench, The Well, PGLearn, OGB, EngiBench (NeurIPS 2025
   D&B) and Bubbleformer (NeurIPS 2025 spotlight; track label not shown publicly), the NeurIPS checklist, the 2026
   formatting instructions and the Evaluations & Datasets call. Structural counts (words, sections, figures, tables,
   sentence length) parsed from the arXiv HTML; first page / Figure 1 patterns, data overview, tasks, baselines,
   results, table style, tone, appendix contents and the 16 checklist items.
2. **LaTeX submission** — `paper/neurips/main.tex` with `neurips_2026.sty` (revision 2026-01-29, `eandd` track
   option, submission mode), built with Tectonic 0.17.0 → **`paper/neurips/main.pdf`** (28 pages: 9 content pages,
   references from page 10, appendices A–I, checklist). Markdown draft retired to `paper/draft_md_archive.md`.
3. **Figures** — seven main-text figures and the appendix set, all from `scripts/paper_figures.py --tex`
   (`scripts/paper_figdata.py` extracts the raster arrays from the Hub once); tables from
   `scripts/paper_tables_tex.py`. Every number traceable: `check_draft_numbers.py --tex` → 2,000 tokens, 0 untraceable.
4. **Change summary** — `docs/paper_tex_changes.md` (one page).

## Open for the owner
- Nine pages with no slack; Figures 2 and 3 are printed at 60 % / 50 % width.
- Camera-ready needs the `final` option, author block and a code tag (see `docs/verification_report.md`).

## Operations
GPU use for this step: none. Scratch ≈ 230 GB (XL/T4, XXL/T1 staged; `paper/figdata/` 455 MB, git-ignored).
Offloader loop and keepalive running. GitHub main = origin after this push.

---

# Status — 2026-10-17 04:40Z: paper print-legibility pass complete (every page re-checked at print size)

## Done (owner request 2026-10-16/17: "recheck the paper carefully, i found many bugs, especially in the images …
make sure there's nothing like this anymore … also check for every parts of the paper at the end … pictures in part D
they combined together, it's too small to read")
1. **Figures** — every figure is now drawn at the width it is printed (`FULLW = 5.5` in, `HALFW = 2.64` in), so the
   font sizes in `scripts/paper_figures.py` are the font sizes on paper (the first PDF scaled 7-inch figures by 0.79
   and Figures 2/3 to 60 % / 50 %). Figure 2 re-laid out as a 3 × 10 grid (tiers as columns), Figure 3 as one row per
   task with in-distribution and OOD side by side, Figures 5/6 as native half-width designs. Every overlap found in the
   page-by-page audit removed (Figure 1 text block, Figure 4 legend and log ticks, Figure 5 annotations, OOD tier
   letters, curve titles, fidelity/WP7 titles and axis labels, precision legends). **Appendix D statistics redrawn**
   as four separate full-width figures in the paper style instead of four shrunk PNG copies.
2. **Tables** — headers printed raw LaTeX (`\rightarrow`, `\Delta`, `test\_id`) → math-aware escaper; Table 5 was
   empty → fixed `md_rows`; five wide tables were `\resizebox`-shrunk to ≈ 5 pt → slimmer columns at `\scriptsize`,
   no scaling, no overfull box; Table 1 `²`/`·` glyphs; `--` flags keep their double hyphens.
3. **Bibliography** — author lists were split at commas (`McRae and B. H.`), titles lower-cased (`julia`, `jax`),
   arXiv ids inside titles, unprintable dashes → all repaired (`references.bib`).
4. **Checklist / end matter** — hard-coded appendix letters had drifted (licences cited as Appendix I) → `\ref`s;
   `placeins` float barriers so no figure precedes its section heading; data-scaling figure next to its table.
5. **Verification** — `main.pdf` rebuilt (27 pages; 9 content pages, references from page 10); build log: 0 overfull
   boxes, 0 missing characters; `check_draft_numbers.py --tex`: 2,131 numeric tokens, 0 untraceable, 0 untagged;
   `tests/test_no_pattern_kills.py` passes; all 27 pages rendered and inspected (text, tables, figures, references,
   checklist). Details: `docs/paper_tex_changes.md` ("Print-legibility pass").

## Open for the owner
- Nine pages with no slack (unchanged).
- Scratch deletion: the inventory and recommendations from 2026-10-16 are waiting for your choice of rows; nothing
  has been deleted.
- Screenshot paths you pasted are on your Mac; attach them or `scp` to `work/screenshots/` if any bug is still open.
- Appendix float pages (Table 8 alone on p. 16, Figure 9 alone on p. 19) are LaTeX float pages, not defects; say so if
  you want them packed differently.

## Operations
GPU use for this step: none. Login-node work: figure regeneration (≈ 4 min, 1.2 GB peak) and Tectonic builds.
Offloader loop and keepalive running. GitHub main = origin after this push.

---

# Status — 2026-10-17 05:50Z: paper target set to NeurIPS 2027; print-legibility pass complete (two rounds)

## Done (owner request 2026-10-16/17: "recheck the paper carefully, i found many bugs, especially in the images …
make sure there's nothing like this anymore … also check for every parts of the paper at the end … pictures in part D
they combined together, it's too small to read")
1. **Figures** — every figure is now drawn at the width it is printed (`FULLW = 5.5` in, `HALFW = 2.64` in), so the
   font sizes in `scripts/paper_figures.py` are the font sizes on paper (the first PDF scaled 7-inch figures by 0.79
   and Figures 2/3 to 60 % / 50 %). Figure 2 re-laid out as a 3 × 10 grid (tiers as columns), Figure 3 as one row per
   task with in-distribution and OOD side by side, Figures 5/6 as native half-width designs. Every overlap found in the
   page-by-page audit removed (Figure 1 text block, Figure 4 legend and log ticks, Figure 5 annotations, OOD tier
   letters, curve titles, fidelity/WP7 titles and axis labels, precision legends). **Appendix D statistics redrawn**
   as four separate full-width figures in the paper style instead of four shrunk PNG copies.
2. **Tables** — headers printed raw LaTeX (`\rightarrow`, `\Delta`, `test\_id`) → math-aware escaper; Table 5 was
   empty → fixed `md_rows`; five wide tables were `\resizebox`-shrunk to ≈ 5 pt → slimmer columns at `\scriptsize`,
   no scaling, no overfull box; Table 1 `²`/`·` glyphs; `--` flags keep their double hyphens.
3. **Bibliography** — author lists were split at commas (`McRae and B. H.`), titles lower-cased (`julia`, `jax`),
   arXiv ids inside titles, unprintable dashes → all repaired (`references.bib`).
4. **Checklist / end matter** — hard-coded appendix letters had drifted (licences cited as Appendix I) → `\ref`s;
   `placeins` float barriers so no figure precedes its section heading; data-scaling figure next to its table.
5. **Verification** — `main.pdf` rebuilt (27 pages; 9 content pages, references from page 10); build log: 0 overfull
   boxes, 0 missing characters; `check_draft_numbers.py --tex`: 2,131 numeric tokens, 0 untraceable, 0 untagged;
   `tests/test_no_pattern_kills.py` passes; all 27 pages rendered and inspected (text, tables, figures, references,
   checklist). Details: `docs/paper_tex_changes.md` ("Print-legibility pass").

## Open for the owner
- **Venue corrected to NeurIPS 2027** (your note). The 2027 style file and call do not exist yet (neurips.cc has no
  2027 page on 2026-10-17), so the paper still builds with `neurips_2026.sty` and the preamble overrides the notice to
  "41st … NeurIPS 2027"; the 2026 E&D call stays cited as the latest published guidance. When the 2027 kit appears:
  swap the style file, delete the override, re-check page limit, track option and checklist (`DECISIONS.md`).
- Nine pages with no slack (unchanged).
- Scratch deletion: the inventory and recommendations from 2026-10-16 are waiting for your choice of rows; nothing
  has been deleted.
- Screenshot paths you pasted are on your Mac; attach them or `scp` to `work/screenshots/` if any bug is still open.
- Second round after your review: all legends moved outside the axes; Figure 1's "elevation" title and arrows no
  longer touch the panels; Table 11 and the data-scaling figure share one float, so the lone-figure page is gone;
  float pages are top-aligned; Figure 16's threshold labels moved from the plot into the legend. Pages 16 and 18 still hold one wide table each (Tables 8 and 10 are too tall to share a
  page with their neighbours); that is the normal LaTeX float page and I suggest leaving it.

## Operations
GPU use for this step: none. Login-node work: figure regeneration (≈ 4 min, 1.2 GB peak) and Tectonic builds.
Offloader loop and keepalive running. GitHub main = origin after this push.

---

# Status — 2026-10-18 06:30Z: review round 2 applied — like-for-like costs, cheap baselines, MgNO/scale-aware seeds, XL-trained run; paper rebuilt at nine pages

## Done (owner: "fix the ones you agreed with … up to 16 GPU-hours … check the correctness")
1. **Like-for-like speed-ups (point 1).** Production Omniscape re-timed with its own parallelisation on one CPU node
   (`scripts/review/omniscape_threads.*`): 1.64× at M and 1.85× at L on 8 threads, nothing more at 24. The paper
   now states every speed-up's basis, the like-for-like figures (14,235× / 22,916× at M / L for the U-Net; 5,955× for
   the demonstration), the training cost and the break-even number of maps (37 maps at L; 13 for the demo). New
   Appendix C with `tab_threads`, `tab_breakeven` (`docs/tables/review_round2_threads.md`).
2. **Cheap numerical baselines (point 4).** Truncated AMG-PCG after k iterations and coarsen-×4 on `test_id` subsets
   (`scripts/review/cheap_baselines.sbatch`): two PCG iterations reach rel-L2 0.038 / 0.048 / 0.324 on T3 at S / M / L
   against 0.111 / 0.202 / 0.323 for the best learned model, at 0.02–0.65 s per landscape on one core. T1/T3 are
   reframed as operator-learning stress tests; table + figure in Appendix C (`docs/tables/review_round2_cheap.md`).
3. **Text fixes (points 3, 6, 9, 10):** T2/T1W/T1R declared released without learned baselines; rel-L2 the single
   primary metric; pinch-point precision 0.657 in the same sentence as 11,077× (abstract included); abstract and
   introduction lead with the operator-learning framing and cite adoption (1,936 Scopus citations of McRae et al.
   2008; 459 applications reviewed by Dickson et al. 2019).
4. **New runs (points 2, 7, 8; 14.64 of the 16 GPU-h cap, H100 on `ice-gpu`/`coc-ice`; three legs lost to a known bad
   node and resubmitted):** MgNO seeds 2–3 at S/M on T1/T4 — MgNO **diverges in 4 of 6 T4 runs and 2 of 6 T1 runs**
   under the shared protocol (training loss → 1e6–1e21 in the first epochs); reported as an instability, not patched
   (`docs/tables/review_round2_mgno.md`). Scale-aware seeds 2–3 for U-Net and FNO w48 on T4 at L: U-Net 0.194 ± 0.008
   at XL and 0.321 ± 0.015 at XXL (was seed-1 0.189 / 0.312), FNO 0.158 ± 0.001 at XL. One U-Net T4 run trained at XL
   on its 880 landscapes: rel-L2 0.249 on XL test_id, between zero-shot (0.515) and scale-aware (0.194) from L. The
   ViT at L was *not* re-tuned: the tuning pass had tried patch-16/patch-8 there (+47.8 % / +63.5 %); now stated.
5. **Correctness checks:** every table and figure regenerated from `runs/full` (Pareto rows pool the scale-aware
   seeds; in-tier tables exclude the XL-trained run), `main.pdf` rebuilt (29 pages; **nine content pages**, references
   start at the top of page 10), build log 0 overfull / 0 missing glyphs, `check_draft_numbers.py --tex` 2,268 tokens
   / 0 untraceable / 0 untagged, every changed page inspected at print size, `tests/test_no_pattern_kills.py` passes.

## Full recheck (owner: "check everything again")
Clean rebuild (0 overfull boxes, 0 missing glyphs, 0 undefined references or citations, all 52 cited keys in the
bibliography, every `\ref` label present, no hard-coded appendix letters), every generated table and figure
regenerated and byte-identical to the committed ones, 2,268 numeric tokens all traceable, all 29 pages viewed at print
size. Two defects found and fixed: the MgNO divergence count in the text said 1 of 6 T1 runs (the table says 2 of 6,
first exploding epoch up to 4, not 3) — corrected; the Appendix D heading sat alone at the foot of page 21 below the
Appendix C tables — now starts its own page.

## Not done, by design (stated as limitations in the paper)
Converged (non-budget-limited) retraining of every configuration, new operator families, published resistance
surfaces at M/L, an exact T4 reference at XL/XXL, FNO scale-aware seeds at XXL (budget).

## Open for the owner
- **Leaderboard re-seeded and pushed (your approval 2026-10-18 05:56Z):** 168 entries on the Hub, sha256-verified;
  all 34 Table 2 cells present with rel-L2 agreeing to the third decimal; the four block-1 rows at L equal the four
  official learned rows of Table 7 (scale-aware variants are not leaderboard entries, as before).
- Scratch deletion rows: still waiting for your choice; nothing deleted. `aux/review_round2/` stays until submission,
  as you asked.

## Operations
GPU use for this step: 14.64 GPU-h (`scripts/review/gpu_budget.sh`). CPU: two Slurm jobs (≈ 1.5 node-hours).
Offloader loop and keepalive running. GitHub main = origin after this push.
