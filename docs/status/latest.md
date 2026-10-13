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
