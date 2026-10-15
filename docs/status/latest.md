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
