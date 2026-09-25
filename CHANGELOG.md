# Changelog

## [Unreleased] — Phase 10-full (GPU baselines)
- Scale-aware target variant (`train.py --target-norm scale`; `ampscape.models.common.target_scale`) and its zero-shot XL/XXL transfer rows; XL/XXL Omniscape geometry verified from the data (2026-09-25).
- WP7 many-query demonstration completed with U-Net T4 L (`docs/wp7_demo.md`; results under `aux/wp7/` on the Hub) (2026-09-25).
- Scale-transfer evaluation (`scripts/transfer_eval.py`): XL/XXL rows from the L-trained runs; harness metrics parallelised (`--workers`); XL training jobs abandoned (2026-09-24).
- Scratch: tile rasters under `data/tiles/v1.0/{tiles,resistance,quicklooks}` deleted with owner approval (metadata parquets kept); T4 M/L exact-reference evaluation path fixed and backfilled; WP7 demo job template (2026-09-24).
- GPU driver: strict-priority staging with eviction by furthest next use, draining of pinned groups, tier-major priority order; `offload_loop.sh` starter (2026-09-24).

## [1.0.1] — 2026-09-24 (metadata only; the v1.0 data revision is unchanged)

- Nested download subset `lite` (S shards 0–39, M 0–23, L 0–39: 8 000 + 2 400 + 800 landscapes, all tasks, ≈ 26 GB;
  mini ⊂ lite ⊂ core ⊂ full) as index column `subset_lite`, split lists `splits/lite/`, Croissant FileSet
  `subset-lite` (mini and core also gained FileSets); indexes and Croissant republished; card and loader docs updated.

## [1.0.0] — 2026-09-23

v1.0 data release: 174 400 landscapes / 902 904 rows / 1 157 GB on `Xirro/AmpScape` (revision `v1.0`), five audited tiers,
post-run precision pass, validated Croissant, final card, statistics figures, generation post-mortem.

### Post-run precision pass — 2026-09-22/23
- Every T1/T1W/T1R/T3 row above 1e-9, unmeasured, CG-fallback or QC-failed re-solved in place on the Hub with
  reduced-system CHOLMOD + refinement, true residual per pair recorded, currents/Reff recomputed, provenance kept
  (`resolved_post_run`, `solver_original`); QC-failed T4 rows re-run whole with the Circuitscape solve rescue; full
  audit after each tier; split lists exclude samples with QC-failing rows. Per-tier table: `docs/tables/precision_pass.md`.
- AmpScapeSolve: Circuitscape `solve_linear_system` rescue (incident (i)); Omniscape fallback solver; corrupt-outputs
  guard in `generate.py solve`; OOM-aware resubmission and the 50-job queue cap in the driver.
- Tooling: `scripts/precision_pass.py` (select / submit as a work queue / run / batched verified upload / status / publish),
  `julia/AmpScapeSolve.jl/scripts/resolve_rows.jl`, `scripts/precision_summary.py`; index shard names without `.part`.

### XL launch, parallel uploads, aux publication — 2026-09-21
- Tier L complete and audited (1 000 shards, QC fail 0.013 %, 380.5 GB); audit rule fixed for all-skipped task groups.
- XL: 667 shards planned and prepared; cpu probe (1 vs 4 cpus: no speed-up) → 1 cpu per task for XL/XXL; waves of 300.
- `sync_shards.py --worker k/N`: N parallel uploaders per tier with per-worker leases/staging and commit retry.
- `scripts/push_aux.py`: scratch-only evaluation assets published under `aux/` (dev subset, mini, WP5 probe set,
  WP1/WP2 block builds, `test_ood_published`, dev baseline results); `data/builds/published` regenerated.
- Scratch clean-up (owner-approved): S/M/L quicklooks deleted, task logs archived, superseded pilot builds removed;
  solver task logs no longer carry progress bars.

### Addendum WP1/WP2 at L — 2026-09-20
- `audit_tier.py`: a task-group file absent from the Hub is a discrepancy only when some sample of the shard still
  wants a configuration of that group after its skipped configurations are removed (L false positive on 41 shards
  whose every `regions` sample was skipped; generation log (g2)).
- L block-1 reference complete (60 samples: mean rel-L2 0.028, 2 of 60 flagged; index + summary on the Hub under
  `aux/t4_bs1_reference/L/`), L block-size Pareto rows (blocks 3/5/11, correction on/off; `docs/tables/t4_pareto_L.md`,
  `aux/t4_blocksize_baselines/L/` on the Hub). `aux_t4_blocks.py compare`: cross-file inputs lookup after a top-up,
  `tail_gt5pct` column written by the script, unreadable Hub samples skipped with a warning.

### v1.0 generation + Phase 11 — 2026-09-15/16
- v1.0 freeze (`v1.0-pipeline` = 8491bbe): frozen cell assignment, tile-level hold-out, `test_ood_scale_strict`, decimated
  tile reader with resampling provenance, per-tier tile manifests, live streaming sync + scratch guard, runbook.
- v1.0 tile set (13 958 tiles, 69 790 rasters); tier S generation (100 000 landscapes, 500 shards) streaming to the public
  `Xirro/AmpScape`; autonomous tier driver for M → L → XL → XXL; two incidents (scratch quota; partial-finalize race)
  recorded in `docs/status/generation_log.md` with the fixes (one-commit uploads, sample-count validation, finalize
  guards, intermediates deleted on validated finalize).
- Phase 11: README, `docs/generation_guide.md`, `docs/contributing.md`, notebooks 01–05, CI workflow, connectivity test,
  ruff formatting of the whole tree; tuning pass and official baseline configs (`docs/tables/tuning_dev.md`).

### Dev subset + Phase 10 — 2026-09-14
- v1.0 planner (`ampscape/solve/plan_v1.py`, `scripts/plan_v1.py`): per-tier prefix streams; v1.0 synthetic sampler with the
  hard-case stratum (`sample_landscape_v1`, `corridor_walls`); T1R on synthetic mosaics; v1.0 tile stream
  (`scripts/build_v1_tiles.py`: grid-fit sampling with interior-box snapping, prefix extraction, per-tile random table,
  frozen XXL parents); `hard_case` / `design` index columns; stable XL hash.
- Learned baselines (`ampscape/models/{unet,fno,vit,gnn}.py`, `common.py`) and `scripts/train.py` (shared inputs, log10-ε
  targets, masked MSE, AdamW + cosine, early stopping, predictions in the harness format, evaluation through the harness);
  dev runs on T1/T3/T4 (`runs/dev`, `docs/tables/baselines_dev.md`), GPU accounting and v1.0 extrapolation
  (`scripts/gpu_budget.py`, `docs/tables/gpu_budget.md`), `scripts/collect_baselines.py`; `docs/phase_10_report.md`.
- Dev subset built (`data/dev/{S,M}`, `docs/dev_subset.md`): 3 000 S + 500 M, 66 CPU-h; region hold-out unit option and
  XXL parent regions switch in `v1_0.yaml` (owner decisions pending); torch from the cu126 index.

### Phase 9 — 2026-09-13
- `ampscape/metrics` (pixel, domain, reff, physics, efficiency, acceleration) with hand-computed tests; `ampscape/eval/harness.py`,
  `scripts/evaluate.py`, `docs/evaluation.md` (predictions format); oracle / zero-predictor anchors.
- `test_ood_published`: `ampscape/landscapes/published.py` (geometric-mean resampling to the nearest tier, provenance tag),
  `scripts/tile_published.py`, planner family `published`; build `data/builds/published` (45 S tiles from Eurac Alps and the
  Hawaiian gallinule layers, 1 XXL tile from the raccoon Europe map; all five configurations, CHOLMOD, CG baselines).
- Non-learned coarsen×4 baseline (`ampscape/models/coarsen.py`, `scripts/baseline_coarsen.py`, `tests/test_coarsen.py`)
  with documented scale rules (1/f current scaling for pairwise/advanced, focal in-fill, ground-wins blocks and
  injection-aware scaling for T3); evaluated on the mini test splits and on `test_ood_published` (`docs/phase_09_report.md`).
- Harness fixes found by the baseline: per-pair focal-current check, zero-flow pixels excluded from top-q sets and pinch
  points, published-tile root resolution in `prepare`.

### Phase 8 — 2026-09-07
- Licences and provenance: `docs/licenses.md` reconciled with the full source manifest (21 files) incl. the published
  resistance rasters, verification log and unverifiable-items list; full `CITATION.cff`; redistribution terms in the
  dataset card; `tests/test_licenses.py`; downloader `--register` for manual downloads (Dryad archive registered).

### Phase 7 — 2026-09-06
- Owner decisions on the contrast probe: CHOLMOD iterative refinement (`refine_voltage!`, our own CHOLMOD factorisation of the
  reduced/collapsed system, maps regenerated via `node_current_map`), CG baseline only for test/OOD samples (plan-time
  splits, `XXL_test` profile entry), solver cross-check re-run (PCG vs CHOLMOD vs Circuitscape cg+amg), published
  resistance rasters downloaded, mini pushed to the private HF repo, publication route decided.
- External review: contrast ladder to 10⁶ (10⁶ test-only) with residual probes at S/XXL; solver-acceleration track
  (`SolveStats.cg_baseline`, explicit AMG-PCG zero/warm start) documented in the task spec and brief §11;
  log10(C + ε·max C) transform (`ampscape.metrics.transforms`) replaces log1p, SSIM/PSNR secondary; unvalidated-threshold
  caveat in brief §17 and the dataset card; `docs/survey_resistance_surfaces.md`.
- `ampscape/data`: `AmpScapeDataset` (lazy shards, torch adapter, train-only normalisation stats, subsets, OOD filters),
  `load_from_hub`; `ampscape/io/hf_layout.py` (per-tier × task-group shards, index, nested splits); `subsets.py`.
- `scripts/export_croissant.py` (Croissant 1.0 + RAI, validated), `scripts/push_to_hub.py` (create private repo, verified uploads,
  dry-run default), `docs/dataset_card.md` draft; mini staged in `data/hf/AmpScape` (38 files, 300 MB).
- Splits revised to hierarchical regions (equal-width 20° grid + XXL footprints); ICE feasibility note; paper note on mini skew.

### Phase 6 — 2026-09-06
- `ampscape/io/schema.py`: HDF5 shard schema v0.2 (`MetaModel`, `validate_shard`, `docs/schema.md`); `zarr_export.py`.
- `ampscape/io/sync.py` + `scripts/sync_shards.py`: validate → upload → sha256-verify → delete (dry-run default, pushes gated).
- `ampscape/splits`: 20° macro-cell assignment shared across tiers, straddling exclusion, footprint safety net, seed-family
  splits, OOD flags/holdouts, `splits/*.parquet` written by `generate.py finalize`; cross-tier overlap test.
- Plan amendments C1–C5 in `configs/datasets/v1_0.yaml` and `docs/dataset_plan.md`; mini regenerated under the radius/10
  rule (S block 1, version 0.2.0-mini); old mini kept as `mini_phase5blocks`.

### Rename — 2026-09-06
- EcoFlowBench → **AmpScape**: package `ampscape`, `AmpScapeSolve.jl`, `Xirro/AmpScape`, `AMPSCAPE_*` env vars, CLI `ampscape`;
  scratch path and history unchanged. `CITATION.cff` and `docs/dataset_card.md` (draft) added under the new name.

### Dataset plan — 2026-09-05
- `docs/dataset_plan.md` (generated by `scripts/write_dataset_plan.py` from `configs/datasets/v1_0.yaml`): coverage matrix,
  hard-case stratum, OOD sets, split/leakage rules, measured cost table with wall-clock at 100/500/1000 cores, portability,
  gap analysis, recommended deviations from the brief.
- Omniscape block-size fidelity study (12 paired solves, S–XXL): coarser blocks rejected; radius/8 rule recommended.
- Cluster profiles `configs/cluster/{ice,template}.yaml`, profile-aware `generate.py submit`, `docs/run_guide.md`.
- Phase 5 decisions applied (CHOLMOD everywhere, residual 1e-6, T4 on every landscape, HF_ORG = Xirro, HF storage deferred).

### Phase 5 follow-up — 2026-09-05 (dataset plan)
- `docs/dataset_plan.md` (generated by `scripts/dataset_plan_tables.py` from `configs/datasets/v1_0.yaml`):
  coverage matrix, hard-case stratum, OOD sets, split/leakage rules, cost table, portability, gap analysis.
- Cluster profiles `configs/cluster/{ice,template}.yaml`; `generate.py submit --profile`; `docs/run_guide.md`.
- Omniscape block-size fidelity study (`examples/omniscape_block_study.jl`, `scripts/slurm/block_study.sbatch`): 12 runs;
  coarser XL/XXL blocks rejected; adopted rule block = largest odd ≤ radius/10 (S 1, M 3, L 5, XL 11, XXL 25).

### Phase 5 — 2026-09-05 (mandatory gate reached)
- `AmpScapeSolve.jl`: `solve_pairwise` / `solve_advanced` / `solve_omniscape` with `SolveStats`, exact-graph
  residual in Julia, batch `solve_shard` over HDF5 shards (resumable), `scripts/solve_shard.jl`,
  `examples/solver_comparison.jl`; deps HDF5, JSON, SparseArrays + stdlibs.
- `ampscape/solve`: manifest (UUID5 sample ids, shards), prepare (inputs HDF5), QC (§7.2 + owner rules),
  finalize (final shard layout + Parquet index), quicklooks + contact sheet; `scripts/generate.py`
  (plan/prepare/solve/submit/finalize/status) and `scripts/slurm/solve_shard.sbatch`; `scripts/analyze_build.py`.
- Omniscape reference solver switched to CHOLMOD (cg+amg aborts on high-contrast windows).
- Smoke build (5 samples) validated end-to-end through a Slurm array; mini run (250 samples, 1,270 configs,
  100 % QC pass) and scaling probes M/L/XL (5 each) + XXL (1) completed; JIT warm-up; portable
  JULIA_CPU_TARGET + login-node precompile after a pidfile hang; QC residual threshold 1e-6.
- `docs/phase_05_report.md` generated by `scripts/write_phase05_report.py` (solver validation, determinism,
  time/memory/storage per tier, budget extrapolation: brief ladder ≈ 7,300 CPU-h, 500 CPU-h ladders).

### Phase 4 — 2026-09-05
- `ampscape/sources`: exact Circuitscape graph reconstruction (`graph.py`), config schema with tier scaling,
  generators for point focal nodes (mixed placement), wall-to-wall strips, habitat-patch regions, T3 source/ground
  rasters, T4 Omniscape sources; every configuration connectivity-checked on the exact graph; 21 tests.
- `configs/tasks/sources_default.yaml` with documented defaults; `scripts/build_sources.py`.
- Pilot: 1,865 configurations (60 tiles × 5 tables + 50 synthetic), all connected; `sources.parquet`, gallery.
- Verified with Circuitscape (`examples/region_check.jl`) that repeated point-raster labels form one focal region.

### Phase 3 — 2026-09-05
- `ampscape/resistance`: pydantic YAML schema (`ResistanceTable`), `apply_table` mapping, `perturb_table`.
- Five tables in `configs/resistance_tables/` (generic_hm, large_mammal, amphibian, forest_bird, random_lm_20260905) with citations.
- `scripts/build_resistance.py`: 300 resistance rasters (60 tiles × 5 tables), manifest, stats, gallery figure; 11 tests.
- Owner decisions: HF storage deferred to Phase 5; download gate refined (single > 5 GB or cumulative > 20 GB); GRIP4/HydroRIVERS full set downloaded (4.87 GB cumulative).

### Phase 2 — 2026-09-05
- Synthetic generators (`ampscape/landscapes/synthetic.py`) with documented priors and 38 tests; gallery figure.
- Real-tile pipeline: `real.py` (UTM grids, windowed COG readers, distance rasters, GeoTIFF I/O),
  `sampling.py` (biome × realm × gHM-tercile stratification), scripts `download_sources.py`,
  `sample_tiles.py`, `extract_tiles.py`, `plot_tiles.py`; offline + network tests.
- Pilot: 60 accepted tiles (14 biomes, 5 realms) at tier S with manifest, checksums, quicklooks.
- `docs/licenses.md` (verified sources), `docs/compute_env.md` §10 storage plan, owner decisions applied.
- Fixed: NaN-fill merge bug when a tile straddles several DEM source tiles.

### Phase 0/1 — 2026-09-05
- Cluster inspection of PACE-ICE recorded in `docs/compute_env.md` (partitions, QoS, GPUs, storage, network).
- Isolated toolchain on scratch: `scripts/env.sh`, uv-managed Python 3.11.16 (`pyproject.toml`, `uv.lock`),
  Julia 1.11.3 depot with Circuitscape.jl 5.17.1 + Omniscape.jl 0.6.2 (`julia/AmpScapeSolve.jl`),
  GDAL 3.9.3 CLI env (`scripts/setup_gdal_env.sh`).
- Repository scaffold per brief §2.2 (empty Python subpackages, config dirs, Julia package skeleton, tests).
- Solver smoke test (`julia/AmpScapeSolve.jl/examples/smoke_test.jl`) verified against shipped reference outputs.
- `docs/prior_art.md` (42 verified references) and `docs/task_specification.md` (T1/T1W/T2/T3/T4/T5 tensor specs).
- `DECISIONS.md` entries for solver choice (CHOLMOD), neighbour combination, environment layout.
