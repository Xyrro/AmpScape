# Phase 11 report — documentation, tutorials, tests, CI

Date: 2026-09-16 (written while the v1.0 generation runs; brief §13).

## Delivered

| item | where | notes |
|---|---|---|
| README | `README.md` | pitch, install (`uv sync --extra dev`, Julia only for generation), 10-minute quickstart (`load_from_hub(..., subset="mini")`, `train.py`, `evaluate.py`), baselines, layout, citation/licence |
| docs | `docs/task_specification.md`, `docs/schema.md`, `docs/dataset_card.md` (datasheet, in-progress notice, reproducibility statement, incident note), `docs/licenses.md`, **`docs/generation_guide.md`** (rebuild from scratch: sources → tiles → plan/prepare/solve/finalize/stream → splits → reproducibility), **`docs/contributing.md`**, `docs/generation_runbook.md`, phase reports 01–11 | |
| notebooks | `notebooks/01_quickstart`, `02_train_unet`, `03_evaluate_and_compare`, `04_visualize_samples`, `05_rebuild_mini_dataset` | executable once the mini subset index is on the Hub (published with tier S); 05 needs Julia |
| tests | `tests/` — generators (shapes, ranges, determinism, v1 sampler), resistance mapping, **source generation connectivity** (`test_sources_connectivity.py`, new), schema validation, metrics (hand-computed), data loader, splits, planner, coarsen baseline, licences | 130 passing offline (`-m "not julia and not slow and not gpu"`) |
| CI | `.github/workflows/ci.yml` | job `python`: ruff lint + format check, offline pytest; job `julia-and-smoke`: Julia package tests (Circuitscape/Omniscape instantiated), then a 5-sample mini-pipeline smoke test (plan → prepare → solve → finalize → schema validation) |
| lint | whole tree `ruff format`-ed and `ruff check` clean (83 files reformatted, no semantic change; pipeline tag unaffected) | |

## Download subsets (published with each tier's index)

`subset_mini` = the first 3 S shards (600 landscapes, all tasks, ≈ 0.4 GB), `subset_core` = the first 100 S / 100 M /
250 L shards (≈ 20k + 10k + 5k landscapes), `subset_full` = everything; split lists per subset under `splits/<subset>/`.

## Generation status at the time of writing

Tier S: 500 shards solved; 72 shards are being re-solved after the partial-finalize incident (`docs/status/generation_log.md`),
the rest is on the Hub; the autonomous driver waits for S to be complete before M. CI observed **green** on GitHub for `c131636` (both jobs: lint + offline tests; Julia tests + 5-sample smoke pipeline).
Two CI-only findings fixed on the way: `ruff` classified `ampscape` as third-party on a clean checkout (`known-first-party`
pinned), and the root `.gitignore` pattern `data` had silently kept `ampscape/data/` (the loader package) out of the
repository since Phase 7 — it is now tracked and the pattern is `/data/`.

## Open items

- Notebook execution against the Hub is verified once `index/S.parquet` with the subset columns is re-published after the
  S repair (the loader path itself is exercised by `tests/test_data_loader.py` on local builds).
- Croissant regeneration for v1.0 (`scripts/export_croissant.py`) at completion (Phase 12 package).
