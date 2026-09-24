# `aux/` on the Hub — auxiliary evaluation sets and results (never scratch-only; owner rule 2026-09-21)

Everything evaluation or the paper depends on that is not part of the v1.0 tiers lives under `aux/` in
`Xirro/AmpScape`, pushed by `scripts/push_aux.py` (sha256-verified; record `<src>/.hub_pushed.json`).

| path | what | local source | used by |
|---|---|---|---|
| `aux/dev/S`, `aux/dev/M` | dev subset (3 000 S + 500 M landscapes, v1.0 design and seeds): finalized shards, index, manifests, splits, stats | `data/dev/{S,M}` | Phase 10 baselines, tuning pass (`docs/tables/baselines_dev.md`, `tuning_dev.md`) |
| `aux/mini` | the example/mini build (250 S samples) | `data/builds/mini` | notebooks, smoke tests |
| `aux/test_ood_published` | 46 landscapes on published resistance surfaces (Eurac Alps, Hawaiian gallinule, raccoon Europe; `test_ood_published`) | `data/builds/published` | `scripts/train.py --published-root`, coarsen×4 baseline |
| `aux/scale_probe/probe_L` (+ `aux/scale_probe/*.parquet`, `tiles/`, `resistance/`) | WP5 scale-probe set: 360 landscapes over cells A–D (pixel size × raster size × window radius) | `aux/scale_probe/` | `docs/addendum_WP5_report.md` evaluation recipe |
| `aux/t4_bs1_reference/{M,L}` | block-1 (exact) Omniscape reference: `index.parquet` (+ `tail_gt5pct`), `summary.md`, and the full builds (`inputs/`, `outputs/`, manifest, selection) | `aux/t4_bs1_reference/{M_bs1,L_bs1}` | official T4 evaluation surface at M/L (`evaluate.py --t4-reference`) |
| `aux/t4_blocksize_baselines/{M,L}/<build>` | WP2 block-size builds (blocks 3/7 at M, 3/11 at L, correction on/off) with `vs_bs1` results and the Pareto tables/figures | `aux/t4_blocksize_baselines/` | `docs/addendum_WP2_report.md`, `evaluate.py --t4-blocks` |
| `aux/results/predictions` | non-learned baseline predictions and evaluations (coarsen×4, oracle, zeros; mini, dev, published) | `data/predictions/` | Phase 9/10 tables |
| `aux/results/runs_dev`, `aux/results/runs_tune` | dev baselines and tuning runs: configs, logs, checkpoints (`best.pt`), predictions, `results.json` | `runs/dev`, `runs/tune` | `docs/tables/baselines_dev.md`, `tuning_dev.md`, `docs/tables/gpu_budget.md` |

Not pushed (throwaway): `runs/calib`, `runs/smoke`. Re-running `scripts/slurm/v1/push_aux_all.sh` pushes only new or
changed files. Layout of a pushed build: `shards/shard-XXXXX.h5` (finalized, all task groups in one file — the format
`scripts/evaluate.py --root` reads), `index/`, `index.parquet`, `manifest.parquet`, `build.json`, `splits/`, `stats/`.
