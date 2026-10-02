# GPU usage of Phase 10-full (Slurm accounting, queried 2026-10-02)

| item | value |
|---|---|
| GPU jobs since 2026-09-24 (training legs, evaluation legs, transfer legs, WP7 demo) | 216 |
| GPU-hours consumed (sum of elapsed × allocated GPUs) | 182.4 |
| phases covered | P1–P3 (84 training runs incl. re-queued legs), WP4, 18 transfer legs, WP7 demo, abandoned XL legs |
| not yet included | scale-aware variants (6 runs + transfers), GNN (18 runs + transfers + variant) |

Query: `sacct -u $USER -S 2026-09-24 -X --name=<phase10 job names> -o JobName,ElapsedRaw,AllocTRES,State -P`, summing
`ElapsedRaw × gres/gpu` over jobs with a GPU allocation. The budget document `docs/tables/gpu_budget.md` estimated
≈ 949 GPU-h nominal for the plan; measured training is 3–7× faster than the estimate.
