# Phase 10-full on ICE — GPU schedule (owner decision 2026-09-24: no external allocation, 20 GPU-hour gate lifted)

## 1. What the account can use (measured 2026-09-24 02:30Z)

| item | value |
|---|---|
| partitions | `coc-gpu` (QoS `coc-ice`): L40S 32 (4 nodes × 8), A100 8, V100 22, A40 4, RTX 6000 8, MI210 4; `ice-gpu` (H100/H200) allowed by QoS but 26-h estimated wait |
| walltime | 16 h per job (`coc-gpu` MaxTime) |
| GPU cap | partition group cap 56 GPUs shared by all `coc` users; **per-user `MaxTRESRunMinsPU` gres/gpu = 1 920** (32 GPU-hours of *remaining* walltime across running jobs: with 16-h jobs only 2 run at once, with 2-h legs up to 16 — found in practice 06:00Z, `MaxGRESRunMinsPerUser` pending reason); 50 queued jobs per user |
| queue wait now | L40S and V100: ≈ 10 min (`sbatch --test-only`); A100: ≈ 1 h; H100 (`ice-gpu`): ≈ 26 h. Dev runs on 09-14 started within 1–17 min |
| chosen pool | L40S (bf16, 48 GB; 16 healthy GPUs on 2 nodes, 2 nodes excluded for ECC errors) with A100 spill-over; **2-hour legs** that checkpoint and re-queue themselves (`train.py --resume --pause-exit`), ≤ 18 concurrent jobs of ours |
| data | the trainer reads the Hub layout directly; groups are staged to `data/hfcache` on the login node per (tier, task group) and evicted when no pending job needs them (sizes: S 32/25/30 GB for T1/T3/T4, M 57/43/54, L 84/64/82, XL 61/47/61; scratch guard 230 GB) |
| bad nodes | `atl1-1-03-004-21-0` and `atl1-1-03-004-23-0` (uncorrectable ECC errors on one GPU each, probed 04:40Z) excluded; the driver adds any node that throws a CUDA/ECC error |

## 2. Plan (132 jobs, ≈ 949 GPU-hours; `scripts/slurm/gpu/gpu_driver.py --plan`)

Estimates are the 30-epoch scenario of `docs/tables/gpu_budget.md` (L40S, per seed), official configs, resumable
`scripts/slurm/gpu/train_full.sbatch` (train → evaluate through the harness on test_id / test_ood / ood_region and the
published tiles; T4 rows at M/L also against the exact block-1 reference and the block-size rows).

| priority | content | jobs | GPU-h | lands (at 10 concurrent, ≈ 10-min queue) |
|---|---|---|---|---|
| P1 headline | U-Net and FNO × T1 and T4 × S, M, L, XL, seed 1 | 16 | 55 | day 1 (L runs ≈ 11 h are the long pole) |
| P2 | U-Net T3, FNO T3, ViT T1, ViT T4 × tiers, seed 1 | 16 | 45 | day 1–2 |
| P3 | seeds 2 and 3 of the 8 non-GNN pairs × tiers | 64 | 201 | day 2–3 |
| WP4 | data-scaling at S: U-Net and FNO on T1, n ∈ {1k, 5k, 20k} (100k = the P1 run), fixed-epoch (30) and fixed-step (≈ 118k steps) variants, seed 1 | 12 | 15 | day 2 (after P1 S runs) |
| P4 | GNN T1 and T4 × tiers × 3 seeds (last; multi-day L/XL runs re-queue across the walltime) | 24 | 634 | day 3–6 |
| evaluation passes | inside each job; XL/XXL inference at batch 1 | — | ≈ 25 | — |
| WP7 | many-query demo with the best T4 model (after P1–P3 at L): 20 held-out real tiles × 5 tables + 3 random draws, true-solver route on CPU (≈ 30 CPU-h at L), model route on GPU | 1 | ≈ 5 | day 4–5 |
| **total** | | **133** | **≈ 980** | **≈ 6 calendar days** at the measured cap (4.1 days of pure GPU time at 10 concurrent + staging, queue and re-queue overhead) |

Ordering inside a priority: tier S → M → L → XL so that the small tiers report first; WP4 is inserted after the P1
S runs; GNN last because it is two thirds of the budget and its receptive field, not its cost, is the paper's point.

## 3. Operation

- `setsid nohup python scripts/slurm/gpu/gpu_driver.py >/dev/null 2>&1 < /dev/null &` (lease `logs/lease_gpu_driver.json`;
  state `logs/gpu_driver_state.json`; log `logs/gpu_driver.log`; alert file `logs/GPU_ALERT.txt`).
- Each job: `runs/full/<model>_<task>_<tier>_s<seed>/` with `config.json`, `log.csv`, `best.pt`, `last.pt`,
  `done.json`, `results.json`, `predictions/<group>/`, `eval_t4_reference/` (M/L T4).
- Results table: `python scripts/collect_baselines.py --runs runs/full --out docs/tables/baselines_full.md` (plus the
  T4 reference rows and `scripts/t4_pareto.py --runs` for the learned rows of the Pareto tables).
- Reports: weekly, and on anything that changes the schedule (queue waits > 2 h, a failing job class, scratch).

## 4. Storage rule for runs (2026-09-24)

A finished S run holds ≈ 2.6 GB of predictions (26 k test items), so 133 runs would exceed the 300 GB scratch quota.
`scripts/slurm/gpu/offload_runs.py --loop 1800` pushes every finished run (results, config, log, best.pt, predictions,
T4-reference evaluation) to `aux/results/runs_full/<run>/` on the Hub with sha256 verification and then removes the
local `predictions/*.h5` and `last.pt`; results, config, log and best.pt stay local. Tables are built from the local
`results.json` files; predictions are re-downloadable per run for figures.

