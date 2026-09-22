# Status — 2026-09-22 15:30Z (v1.0 generation complete: all five tiers audited; precision pass started)

## Tier XXL boundary and whole-run totals

| item | XXL | whole run |
|---|---|---|
| shards validated, uploaded, audited | 400 of 400 (400 landscapes, 2 008 rows) | 3 067 shards, 174 400 landscapes |
| audit | clean (1 708 files) | S, M, L, XL, XXL all clean |
| QC fail rate | 0.45 % (9 rows: 7 `regions` residual_high, 1 T4, 1 T3 — all repaired by the precision pass) | S 0.000 %, M 0.002 %, L 0.013 %, XL 0.033 %, XXL 0.45 % |
| GB on Hub (data/) | ≈ 100 | 1 155.8 |
| core-hours | 1 228 (1 cpu; 7 OOM re-runs at 176 GB) | 15 218 of the 30 000 gate |
| wall-clock | 06:18Z first upload → 15:24Z audited (10 h from submission) | S start 09-16 → 09-22 15:24Z |
| scratch | — | 117 GB |

Incident (i) resolved: Circuitscape's hard 1e-4 residual check aborted Omniscape maps and advanced solves on contrast-10⁶
2048² landscapes in both solvers; AmpScapeSolve now rescues exactly those solves by refinement (bit-identical
otherwise), validated on the failing landscape; the rows that failed before the change are repaired by the precision
pass at XXL. Index defect fixed (shard names carried the `.part` staging suffix); all published indexes clean.

## Precision pass (owner 2026-09-21) — started
Tier S selected and submitted (rows above 1e-9, unmeasured T1/T1R rows, `cg+amg` rows, QC-failed rows; 125 Slurm
tasks of 4 shards); then upload → full audit → M → L → XL → XXL; index republished once at the end.
