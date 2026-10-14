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
