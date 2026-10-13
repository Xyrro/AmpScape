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
- Staging is strict-priority (08:20Z): the data of the highest-priority pending jobs is staged first; when it does not
  fit, staged groups that no running job uses are evicted (furthest next use first), and groups pinned by running
  jobs stop receiving new jobs ("draining") until their legs finish and they can be evicted. Without this the P3 S
  seeds kept the S groups pinned and the headline M/L runs waited.
- Offloader: `bash scripts/slurm/gpu/offload_loop.sh 600` (starts `offload_runs.py --loop 600` once; see §4).
- **Restart after a dead session or a login-node reboot (runbook, 2026-10-02)** — one line, idempotent, detached:
  `setsid nohup bash scripts/slurm/gpu/keepalive.sh > /dev/null 2>&1 < /dev/null &`
  The keepalive (pid in `logs/keepalive.pid`, log `logs/keepalive.log`) restarts the driver whenever its lease pid is
  dead and the offloader whenever no copy runs, every 5 min; both are resumable, nothing is lost by a restart. It
  survives the session that launched it; a login-node reboot kills it (no cron/systemd for users on PACE login
  nodes) — run the line again. Health check: `tail logs/keepalive.log logs/gpu_driver.log; squeue -u $USER`.

- **Login-node memory (2026-10-13).** Each user runs in a 4 GB memory cgroup (`/sys/fs/cgroup/user.slice/user-$(id -u).slice`,
  `memory.max`); the kernel did not reclaim our clean page cache (≈ 3.85 GB of `file` in `memory.stat` after scratch
  I/O), `memory.reclaim` is not writable by the user, and the cgroup OOM-killed instead: on 2026-10-10 the driver's Hub
  staging subprocesses died within seconds in a loop (no job submitted) and the owner's tmux/screen attaches and SSH
  session were SIGKILLed; on 2026-10-13 the first fix (drop the cache *after* a group) was not enough — `snapshot_download`
  with 8 workers filled the slice in seconds, the L/T1 and M/T4 staging subprocesses were killed at 20–25 %, and the
  OOM killer also took the Claude CLI session that was fixing it. Rules now:
  1. **During a transfer, not after it.** `stage_data.py stage` downloads per file with `--workers 2` (hf_hub_download),
     fsyncs + advises DONTNEED each file on completion, and runs `ampscape.io.pagecache.CacheSweeper` (a thread that
     sweeps the group dir, the `.cache/huggingface/download` temp dir, index/splits and `$HF_HOME/xet` every 5 s).
     `push_aux.py` (offloader, aux uploads) runs the same sweeper over the source dir and the xet cache for the whole
     push, plus the per-file drop after each commit. Test (2026-10-13 06:39Z, login node, logged `memory.current` every
     5 s): staging 101 new M/T4 shards (10.4 GB, 2 workers, 70 s) peaked at 1.08 GiB (0.82 GiB before), never above
     1.5 GiB; `python scripts/slurm/gpu/stage_data.py stage --tier M --group T4 --max-files 240` reproduces it (partial
     stage, no marker).
  2. The keepalive still runs `scripts/evict_cache.py` every 10 min and whenever `memory.current` > 2.5 GiB (lines in
     `logs/keepalive.log`); manual: `python scripts/evict_cache.py`; check: `cat .../memory.current`, OOM count:
     `grep oom_kill .../memory.events`.
  3. Nothing on the login node reads or writes large files without `drop_file_cache` / a sweeper
     (`ampscape/io/pagecache.py`; `tests/test_pagecache.py`).
- **No pattern kills (2026-10-13 audit, widened the same day).** Stop a daemon via its lease / pid file only
  (`logs/lease_<name>.json`, `logs/keepalive.pid`; the offloader by the pid of the exact `python scripts/slurm/gpu/offload_runs.py`
  line). The audit covered every tracked file (scripts, package, Julia, tests, Makefile), `work/`, the git hooks and the
  Claude settings/hooks: no `pkill`, `killall`, `kill -9`, `pgrep -f`, `kill -f`, `killpg` or `xargs kill` anywhere; the only
  `kill`s are `kill -0 <pid>` liveness probes and `kill $(cat <pidfile>)`. `tests/test_no_pattern_kills.py` scans the
  same scope and fails on any selector that could match tmux, screen, sshd, bash or the Claude CLI.

- **GPU pools and packed input (2026-10-13).** Training legs are routed by `choose_pool` over two QoS budgets (per-user
  per-QoS: 1 920 GPU-min and 50 jobs each): coc-ice → `ice-gpu` H100, H200, `coc-gpu` L40S, A100; coe-ice → `coe-gpu`
  H100, H200 (16 two-hour legs per QoS, spill when ≥ 3 of ours are pending on a type, ≤ 45 queued in total);
  transfer/evaluation legs stay on L40S/coc-ice. **GNN legs** fetch their group from the Hub to the node's NVMe at job
  start (`LOCALDATA=1`, ≈ 20 min, reused on the same node) and never pin scratch. Non-GNN legs run with `PACK=1`: `train.py --packed-dir` packs the train/val tensors once per job to the
  node's local NVMe (`/tmp/ampscape_$USER/pack/<key>`, reused by later legs on the same node, 2-day cleanup) — the
  epoch is then GPU-bound (U-Net M 56 s on H200 vs 170 s before; FNO 59 vs 208 s; `docs/tables/gpu_probe.md`).
  Probe one configuration: `sbatch ... --export=ALL,MODEL=unet,TASK=T4,TIER=M,BATCH=8,WORKERS=6,PACK=1 scripts/slurm/gpu/gpu_probe.sbatch`.

## 4. Storage rule for runs (2026-09-24)

A finished S run holds ≈ 2.6 GB of predictions (26 k test items), so 133 runs would exceed the 300 GB scratch quota.
`scripts/slurm/gpu/offload_runs.py --loop 600` pushes every finished run (results, config, log, best.pt, predictions,
T4-reference evaluation) to `aux/results/runs_full/<run>/` on the Hub with sha256 verification and then removes the
local `predictions/*.h5` and `last.pt`; results, config, log and best.pt stay local. Tables are built from the local
`results.json` files; predictions are re-downloadable per run for figures.


## 5. XL and XXL rows: scale transfer, not training (2026-09-24 22:40Z)

The card defines XL and XXL as held-out-scale tiers ("XL/XXL for models trained ≤ L"); their v1.0 splits hold 228
(XL) and 0 (XXL) training landscapes and no validation split, so the first XL training legs were degenerate (228
samples, `val_loss` 0, early stop at epoch 9) and their single-process metrics at 1024² exceeded the 2-h leg. The
nine XL training jobs were cancelled and moved to `runs/abandoned_xl_training/` (deleted 2026-10-02 with owner approval); nothing is trained at XL.

Instead every L-trained run is evaluated at XL and at XXL (fully convolutional models only: U-Net, FNO, GNN; the
ViT's interpolated positional embedding stops at XL) on `test_id`, `test_ood`, `ood_region` at batch 1 with the
training tier's normalisation statistics — `scripts/transfer_eval.py`, job template
`scripts/slurm/gpu/transfer_eval.sbatch` (4-h legs, 8 cores, resumable per split). The harness metrics now run in
parallel processes (`evaluate.py --workers`, `ampscape.eval.harness.evaluate(workers=…)`; identical per-sample
results, verified on the smoke predictions). Results: `<run>/results_transfer.json` (`eval["hfcache_<tier>_<split>"]`)
and `<run>/eval_transfer/<tag>/`, pushed to the same Hub folder as the run and listed in the baselines table as
`<run> → XL`. Plan: 144 jobs ≈ 933 GPU-h (XF 30 jobs after P3, XF4 12 GNN transfers after P4). XXL groups: T1 22 GB,
T4 23 GB.

## 6. Outcome (2026-10-04)

Plan completed 2026-10-04 15:30Z: 166 jobs — 84 official training runs (4 models × T1/T4, U-Net/FNO on T3, × S/M/L
× 3 seeds), 12 WP4 runs, 30 zero-shot transfer legs (L-trained → XL/XXL), 6 scale-aware-target runs at L + 10
transfers, 18 GNN runs + 12 transfers + the GNN scale-aware variant (2 + 4). Nothing was trained at XL (§5). All
results are on the Hub under `aux/results/runs_full/<run>/` (results, config, log, best.pt, T4 reference
evaluations, transfer metrics; predictions kept for seed-1 test_id). Measured cost: 401 GPU jobs, 430.1 GPU-h
(`docs/tables/gpu_usage.md`) against ≈ 1,081 GPU-h nominal; calendar 11 days, of which 6 lost to the staging
deadlock of 26 Sep – 2 Oct (§3 keepalive and watchdog added afterwards). Tables and figures:
`scripts/paper_figures.py` → `paper/tables/`, `paper/figures/`; reports: `docs/status/latest.md`,
`docs/wp4_data_scaling.md`, `docs/wp7_demo.md`, `paper/ood_analysis.md`.

Incidents that changed the driver during the phase, for the post-mortem: evaluation legs timing out (deferral),
host-memory OOM from an unbounded open-file cache, the per-user running-GPU cap (2-h legs), scratch quota from
transfer predictions (drop after metrics, per-split offload, concurrency cap), staging limits below the scratch floor
(idle 6 days; keepalive + watchdog), circular hold between pre-staging and transfer legs, concurrent XL/XXL legs
racing on one summary file (locked merge, one leg per run), the empty transfer script committed during the quota
incident (CI parse test).
