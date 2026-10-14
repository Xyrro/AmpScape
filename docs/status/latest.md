# Status — 2026-10-14 00:45Z: phase 15 half done (T1 L runs finished, T4 L legs running); all 28 recomputed T4 reference evaluations replaced on the Hub; tables regenerate once phase 15 and the GNN L candidate finish

## Done since 17:25Z
- **Phase 15 launched** (owner approval; ≈ 32 GPU-h): the 27 jobs of `docs/plans/phase15_plan.json` run behind the
  phase 13c/14 remainder in one plan file (`docs/plans/phase13c_15_plan.json`). The four FNO T1 L legs (3 seeds +
  scale-aware) started 21:12Z on H200; the five T4 L legs follow once L/T1 is evicted and L/T4 staged; the 16 XL/XXL
  transfer legs run after their source runs on L40S.
- **H200 first.** Probe of the phase 15 config (FNO w48 + dist, T1 L, packed, batch 4): 103 s/epoch on H200 vs 188 s
  on H100 (1.8×; 2-s queue wait on coe-gpu for both). Pool order is now coe-gpu H200 → ice-gpu H200 → coe-gpu H100 →
  ice-gpu H100 → L40S → A100; coe-gpu before ice-gpu because ice-gpu reaches only the 6 shared H200 nodes (1 free GPU
  at 21:15Z; the first four legs sat on "Priority" and were cancelled before any epoch and resubmitted on coe-gpu).
- **T4 reference evaluations on the Hub.** All 28 T4 M/L runs with a recomputed exact-reference evaluation were already
  offloaded, and the `.offloaded` mark made the offloader skip them — the Hub still held the superseded
  `eval_t4_reference/`. The offloader now re-pushes an offloaded run's `eval_t4_reference/` whenever its sha256 differs
  from `.hub_pushed.json` (`reference_stale`, `tests/test_offload_reference.py`): the 12 M runs were replaced at 21:05Z;
  the 16 L runs (official + scale-aware U-Net/FNO/ViT/GNN) get their CPU recompute as soon as L/T4 is staged
  (≈ 22:30Z) and are re-pushed within 10 min of it. Tables/figures are regenerated only after the sha check over
  `runs/full/*_T4_[ML]_s*` passes.
- Housekeeping: a 16:18Z driver restart had left a 41.7 GB partial M/T1 staging without marker on scratch (neither used
  nor evicted); evicted by hand, scratch 257 → 218 GB.
- `scripts/tuning_effect.py` → `docs/tables/tuning_effect.md`: pre-tuning official runs vs tier-tuned `_t2` re-runs per
  task / tier / split (mean ± std over seeds, Δ %), plus the configuration-change table from `tuning_full.json`
  (generated at the end, with the regenerated tables).

## Since 21:30Z
- **T4 reference evaluations on the Hub: done.** The 16 L recomputes ran 00:28–00:39Z (CPU, predictions fetched onto the
  node's local disk) and the offloader replaced the Hub copies; sha256 of `eval_t4_reference/results.json` matches
  `.hub_pushed.json` for all 28 T4 M/L runs (checked 00:39Z).
- FNO w48 T1 L: the 3 seeds + scale-aware variant finished 22:10Z (val loss 0.0597–0.0607 vs official m64 0.0628) and
  are offloaded; the four T4 L legs started 00:18–00:39Z on H200 (103 s/epoch) → ≈ 01:45Z.
- Driver scratch accounting (three fixes, `DECISIONS.md` 2026-10-13/14): evictions only when they make the target fit;
  fit tests count stagings the quota reading has not shown yet and the predictions running legs will still write
  (legs held when their predictions would not fit under 295 GB); backfills fetch onto the CPU node. Cost: the T4 L legs
  started ≈ 00:18Z instead of 23:05Z.
- Node-local GNN legs keyed their evaluation groups `M_T4_M_<split>` (root dir name) instead of `hfcache_M_<split>`:
  fixed in place (`scripts/fix_local_root_tags.py`) and in the template; the two finished GNN T4 M re-runs got their
  reference evaluation with M/T4 fetched onto the CPU node (6.6 min each).
- Login-node memory: two stagings peaked at 2.6 GiB `memory.current` while the offloader pushed predictions at the
  same time (staging alone stays ≈ 1.1–1.2 GiB); no OOM, keepalive sweep at 2.5 GiB. To watch.

## Running
- Phase 15: T4 L legs (4) ≈ 01:45Z; then L/T4 evicted, L/T3 staged, T3 L legs (3) ≈ 03:15Z; XL/XXL transfer legs (16,
  L40S, sources done) once XL/T1 + XXL/T1 fit beside the L groups → ≈ 05:00–06:00Z.
- Phase 14: gnn_T1_M_s3_t2 at epoch 24 → ≈ 01:15Z; GNN L tuning candidate (ms8) at epoch 21 → ≈ 03:00Z.

## Next (this session, no further gate)
1. GNN L decision (`scripts/tuning_select.py`), 2. `scripts/paper_figures.py` (baselines table, T4 Pareto M/L,
error-vs-tier, scale transfer, WP4, OOD, all-splits), `tuning_effect.py`, acceleration table, 3. report what the tuning
changed per model and tier relative to the pre-tuning table. A GNN L config change would need ≈ 3 × 9 GPU-h of GNN L
re-runs — that would be a new gate.
