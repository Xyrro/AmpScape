# Generation guide — rebuilding AmpScape from scratch

Everything is deterministic given the pipeline tag, the configs and the seeds; the only external inputs are the
source rasters/vectors listed in `data/sources/manifest.json` (`scripts/download_sources.py`).

## 0. Environment
`uv sync --extra dev`; Julia 1.11 with `julia/AmpScapeSolve.jl` instantiated (Circuitscape 5.17.1, Omniscape 0.6.2);
a cluster profile in `configs/cluster/<name>.yaml` (copy `template.yaml`); `source scripts/env.sh` sets caches,
`JULIA_CPU_TARGET` and `AMPSCAPE_*`. Portability notes: `docs/run_guide.md`, `docs/compute_env.md`.

## 1. Sources (login node, network)
`python scripts/download_sources.py` (Copernicus DEM and WorldCover are read as COG windows at extraction time; gHM,
GRIP4, HydroRIVERS, RESOLVE ecoregions are downloaded once). Licences: `docs/licenses.md`.

## 2. Real tiles (`scripts/build_v1_tiles.py`)
```
sample  --out data/tiles/v1.0 --tiers S M L XL XXL XXL_strict   # frozen lists: seeds 20260906·10 + tier index
extract --out data/tiles/v1.0 --tier S --first-accepted 8000     # prefix mode, per-tier manifests (Slurm: scripts/slurm/v1/extract_tier.sh)
merge   --out data/tiles/v1.0
resist  --out data/tiles/v1.0                                    # 5 resistance rasters per tile (4 expert + per-tile random)
```
Rules: stratified round-robin over biome × realm × gHM tercile; S–XL centres fit one 20° macro-cell (snapped into the
interior box otherwise); XXL not cell-fitted; `XXL_strict` inside test cells only; rejected tiles skipped, never
replaced; resampling per layer as in `configs/datasets/v1_0.yaml` (majority / mean / min, decimated from COG overviews).

## 3. Plan → prepare → solve → finalize → stream (per tier)
```
python scripts/plan_v1.py --tier S --n 100000 --out data/v1/S --shard-size 200 --tiles data/tiles/v1.0 --dataset-version 1.0.0
sbatch scripts/slurm/v1/prepare_shards.sh data/v1/S 0 199        # inputs for a wave (no network)
python scripts/generate.py submit --build data/v1/S --shards 0-199 --max-concurrent 200
setsid nohup scripts/slurm/v1/sync_loop.sh data/v1/S S >/dev/null 2>&1 < /dev/null &
```
The array task solves a shard (`solve_shard.jl`, CHOLMOD, CG baselines on test/OOD samples), finalizes it (QC on the
exact graph, schema validation, sample count vs manifest, quicklooks) and deletes the raw intermediates; the sync
supervisor splits each validated shard by task group, uploads it in one commit, verifies the Hub checksums, deletes it
locally and re-publishes `index/<tier>.parquet` + split lists. The autonomous driver
(`scripts/slurm/v1/generation_driver.py`) runs the tiers M → L → XL → XXL in waves sized for the scratch budget
(`docs/generation_runbook.md`).

## 4. Splits
Frozen macro-cell assignment `configs/splits/cell_assignment_v1.json` (seed 20260906); tile-level biome/realm hold-out;
synthetic by seed family; hold-outs (forest_bird table, contrast 10⁶, XL/XXL scale, `test_ood_scale_strict`,
published rasters) applied by `ampscape.splits.assign.add_splits` at publish time. Subsets: mini (first 3 S shards),
core (first 100 S / 100 M / 250 L shards), full.

## 5. Reproducibility
Sample ids are UUID5 of (dataset, family, key); every sample records solver versions, parameters, residuals,
`pipeline_tag`/`pipeline_git_sha`; regenerating a shard on the same CPU model reproduces every array bitwise, across
CPU models to ≤ 1.2e-9 relative (`scripts/compare_shards.py`). Dev subset (`docs/dev_subset.md`) = the first 3 000 S /
500 M landscapes of the same streams.
