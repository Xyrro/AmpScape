# Status — 2026-10-15 20:45Z: phase 16 complete (GNN L re-runs, 79 GPU-h); GNN ms8 official at T1 L and T4 L; tables, figures and leaderboard regenerated; remaining items

## 1. Phase 16 (approved ≈ 114 GPU-h; used 79.4)
- Seven GNN L runs (T1 seeds 2–3, T4 seeds 1–3, two scale-aware variants) trained on H200 with node-local data,
  1 033–1 332 s per epoch (same as H100), 26–30 epochs each; seed 1 of T1 L is the reused tuning candidate
  (`REUSED_FROM.txt`, official protocol verified). All 16 XL/XXL transfer legs and the exact T4 reference
  evaluations of the four T4 L runs are done; every result file is on the Hub with its current hash
  (501 files checked over all T4 M/L and L runs — one pre-existing stale `results_transfer.json` of the pre-tuning
  `gnn_T4_L_s1`, updated 15 min after its 2026-10-04 push, is being re-pushed by the offloader).
- One incident: the H200 of `gnn_T4_L_s1_t2` (node `atl1-1-03-014-16-0`, GPU index 2) was silently faulted
  ("GPU requires reset", no memory ever allocated, no CUDA error raised, slurmstepd NVML errors). Detected after
  53 min with an empty `log.csv`, the job was cancelled by id, the node added to `logs/gpu_bad_nodes.txt` by hand and
  the driver resubmitted the run on another node (1.1 GPU-h lost; symptom and check recorded in
  `docs/phase10_full_schedule.md`, bad-nodes row).
- GPU usage: 71.7 GPU-h training/evaluation legs + 7.8 GPU-h transfers (`docs/tables/gpu_usage_tuning.md`);
  cumulative since 2026-10-13: 230.3 GPU-h.

## 2. Configuration decisions at L (validation loss only, `docs/tables/tuning_decisions.md`)

| tier | task | model | pre-tuning val loss (mean ± std, 3 seeds) | ms8 (mean, 3 seeds) | Δ | official |
|---|---|---|---|---|---|---|
| L | T1 | GNN | 0.3204 ± 0.0068 | 0.2693 | −15.9 % | **tuned (ms8)** |
| L | T4 | GNN | 0.0220 ± 0.0001 | 0.0202 | −8.3 % | **tuned (ms8)** |

Unlike at M (where ms8 was worse on T4, +8 %), the variant improves both tasks at L. The full matrix is unchanged
otherwise: tuned official for FNO w48 at T1/T3/T4 (M, L), U-Net w64 at T1/T4 M, ViT p16g16 at T1 M, GNN ms8 at T1 M;
pre-tuning for U-Net T3 M, ViT T4 M, GNN T4 M; U-Net and ViT at L stay pre-tuning. 15 decisions, 12 tuned.

## 3. Effect on the test metrics (`docs/tables/tuning_effect.md`, test_id, mean ± std over 3 seeds, official → tuned)

| task | tier | rel-L2 | MAE (log10) | Spearman |
|---|---|---|---|---|
| T1 | L | 1.067 ± 0.026 → 0.941 ± 0.160 (−11.8 %) | 0.416 → 0.382 (−8.2 %) | 0.834 → 0.861 |
| T4 | L | 0.142 ± 0.001 → 0.142 ± 0.001 (0.0 %) | 0.074 → 0.071 (−4.5 %) | 0.960 → 0.962 |

OOD splits move the same way (T1 test_ood −15.3 %, ood_region −13.2 %; T4 −0.2 % / −1.3 %). The ms8 T1 L seeds
disagree on rel-L2 (0.79 / 0.93 / 1.11) while their MAE and Spearman agree within 0.02 — rel-L2 at L is dominated by
a few high-current landscapes. Scale transfer (`paper/tables/scale_transfer.md`, now 3 seeds for GNN): T1 zero-shot
rel-L2 0.94 (L) → 1.42 ± 0.82 (XL) → 1.62 ± 0.58 (XXL); T4 0.142 → 0.498 → 0.739; the scale-aware T1 variant is worse
than zero-shot at XL (7.5) and similar at XXL (1.4).

## 4. Regenerated
`scripts/tuning_select.py`, `tuning_decisions.py`, `paper_figures.py --skip-stats`, `tuning_effect.py`,
`acceleration_table.py`: `docs/tables/{tuning_full,tuning_decisions,tuning_effect,baselines_full}.md`,
`paper/baselines.md`, `paper/tables/{baselines_sml,ood_degradation,scale_transfer,t4_pareto_L}.md`, figures
`error_vs_tier`, `ood_degradation`, `scale_transfer`, `t4_pareto_L`. Leaderboard rebuilt from scratch
(`submit_results.py seed-baselines`, 165 entries: 123 in-tier + 42 zero-shot; the previous file was kept aside in
`work/` because its id-based de-duplication would have retained the pre-tuning GNN L entries). Hub push of
`aux/leaderboard/` remains a gate.

## 5. Remaining items
- **Derivation:** done — `paper/appendix_derivation.md`.
- **WP6 (MgNO / HANO):** MgNO vendored and run at T1 S/M and T4 S/M (seed 1); HANO not runnable
  (`docs/wp6_implementations.md`). MgNO at L / seeds 2–3 not planned (≈ 10 GPU-h per task at L).
- **Submission format:** done — `docs/submission.md`, `scripts/submit_results.py`, 22 tests pass; leaderboard
  re-seeded with the final official baselines; Hub push on approval.
- **`paper/draft.md`:** not assembled; all inputs are now final (the L rows no longer change). Next step on
  go-ahead: assemble from `paper/sections/*`, the regenerated tables/figures and the appendices, refresh
  `paper/sections/results.md` (written 2026-10-05, before the tuned configurations), and cut to length.
- **Acceleration metric:** `docs/tables/acceleration.md` complete (no acceleration anywhere); paper write-up with
  the draft.

## Operations
No jobs queued; the plan is exhausted (driver idle-restarts by the keepalive are harmless). Offloader loop running.
Scratch 150 GB, login-node memory ≈ 1.1 GiB. GitHub: pushed after this update (main = origin).
