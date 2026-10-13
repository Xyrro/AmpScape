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
