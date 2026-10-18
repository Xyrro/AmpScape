# GPU usage of Phase 10-full (Slurm accounting, final, queried 2026-10-04)

| item | value |
|---|---|
| GPU jobs 2026-09-24 → 2026-10-04 (training legs, evaluation legs, transfer legs, WP7 demo, abandoned XL legs, duplicates) | 401 |
| GPU-hours consumed (sum of elapsed × allocated GPUs) | 430.1 |
| plan | 166 jobs: 84 official training runs (P1–P3), 12 WP4, 30 zero-shot transfer legs, 6 scale-aware L runs + 10 transfers, 18 GNN runs + 12 transfers, GNN scale-aware 2 + 4 |
| nominal plan estimate (`docs/tables/gpu_budget.md`, 30-epoch scenario) | ≈ 1,081 GPU-h |
| measured / nominal | 0.40 (training 3–7× faster than the per-epoch estimates; idle and duplicate legs included) |
| calendar | 2026-09-24 → 2026-10-04 (11 days), of which 6 days idle (26 Sep → 2 Oct staging deadlock) |

Query: `sacct -u $USER -S 2026-09-24 -X -o JobName,ElapsedRaw,AllocTRES -P`, jobs named `phase10-*` with a GPU
allocation, summing `ElapsedRaw × gres/gpu`.

## Final total at the paper draft (queried 2026-10-15 22:00Z)

| item | value |
|---|---|
| GPU jobs 2026-09-24 → 2026-10-15 (Phase 10-full baselines, WP4, transfers, scale-aware variants, GNN, WP7, MgNO, voltage heads for the acceleration metric, tuning candidates and the tuned re-runs of phases 13–16, probes, duplicates and abandoned legs) | 773 |
| GPU-hours consumed (sum of elapsed × allocated GPUs) | 701.5 |

Query: `sacct -u $USER -S 2026-09-24 -E now -X -P -o JobID,JobName,ElapsedRaw,AllocTRES`, every job with a `gres/gpu`
allocation, summing `ElapsedRaw × gres/gpu` (CPU-only backfills excluded). Breakdown of the tuning phases:
`docs/tables/gpu_usage_tuning.md`.

## Total after review round 2 (queried 2026-10-18 04:50Z)

| item | value |
|---|---|
| GPU jobs 2026-09-24 → 2026-10-18 (everything above + review round 2; the owner's unrelated `pgu-*` jobs on the same account excluded) | 797 |
| GPU-hours consumed, review round 2 included (sum of elapsed × allocated GPUs) | 717.2 |
| of which review round 2 (`r2-*`: MgNO seeds 2–3 at S/M on T1/T4, scale-aware seeds 2–3 of U-Net and FNO w48 on T4 at L with XL/XXL (U-Net) and XL (FNO) transfers, U-Net T4 trained at XL; three legs lost to a known bad node) | 14.64 (22 jobs; cap 16) |

Query: `sacct -u $USER -S 2026-09-24 -E now -X -P -o JobID,JobName,ElapsedRaw,AllocTRES`, every job with a `gres/gpu`
allocation whose name does not start with `pgu-`, summing `ElapsedRaw × gres/gpu`.
