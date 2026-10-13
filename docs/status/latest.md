# Status — 2026-10-13 21:30Z: phase 15 launched (FNO w48 L re-runs, H200 first); Hub copies of the recomputed T4 reference evaluations being replaced; tables regenerate once the 16 L recomputes and the GNN L candidate are in

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

## Running
- Phase 14 GNN M re-runs (6, H100, node-local data): five at epoch 19–21 of 30 at 21:30Z (≈ 750 s/epoch → ≈ 23:45Z),
  one at epoch 12 (restarted after a node's ECC error at 18:42Z → ≈ 01:15Z).
- GNN L tuning candidate (ms8): epoch 12 of 30 at 1 114 s/epoch → ≈ 03:00Z → L decision for GNN, `scripts/tuning_select.py` re-run.
- Phase 15: T1 L legs ≈ 22:10Z; L/T4 staging + T4 L legs + 16 recomputes ≈ 23:30Z; XL/XXL transfer legs ≈ 01:30Z.

## Next (this session, no further gate)
1. Verify the 16 L reference re-pushes (sha check), 2. GNN L decision, 3. `scripts/paper_figures.py` (baselines table,
T4 Pareto M/L, error-vs-tier, scale transfer, WP4, OOD, all-splits), `tuning_effect.py`, acceleration table, 4. report
what the tuning changed per model and tier relative to the pre-tuning table. A GNN L config change would need
≈ 3 × 9 GPU-h of GNN L re-runs — that would be a new gate.
