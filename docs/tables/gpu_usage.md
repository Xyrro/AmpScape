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
