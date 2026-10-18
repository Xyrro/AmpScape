# Omniscape wall time versus Julia threads (review round 2, point 1)

Production T4 configuration per tier (radius / block: M 32 / 3, L 64 / 5; artefact correction on; CHOLMOD window solver) on the
first landscapes of the `test_id` reference subsets, `parallelize = true` with the given number of Julia threads on one
CPU node; 1 thread = the production setting (`parallelize = false`). Same landscapes at every thread count.
Host: atl1-1-01-005-4-2.pace.gatech.edu.

| tier | threads | n landscapes | wall s per landscape (median) | mean | speed-up vs 1 thread | parallel efficiency |
|---|---|---|---|---|---|---|
| M | 1 | 4 | 75.6 | 78.7 | 1.00× | 1.00 |
| M | 8 | 4 | 46.2 | 52.0 | 1.64× | 0.20 |
| M | 24 | 4 | 46.7 | 52.7 | 1.62× | 0.07 |
| L | 1 | 2 | 277.0 | 277.0 | 1.00× | 1.00 |
| L | 8 | 2 | 151.5 | 151.5 | 1.83× | 0.23 |
| L | 24 | 2 | 149.4 | 149.4 | 1.85× | 0.08 |

## Like-for-like speed-up of the T4 surrogates and break-even number of maps

Inference cost per landscape and training cost of the official runs from `paper/tables/t4_pareto_{M,L}.md` and
`docs/tables/baselines_full.md` (seed mean); solver cost per landscape from this timing (median). Break-even = maps after
which training once plus inference costs less GPU/CPU wall time than the solver: N ≥ T_train / (t_solver − t_inference).
The GPU-hour and the CPU-node-hour are not priced equally; the table reports wall time only.

| tier | model | rel-L2 vs exact map | inference s / map (GPU) | train GPU-h | solver s / map, 1 thread | speed-up, 1 thread | solver s / map, max threads | speed-up, max threads | break-even maps (1 thread) | break-even maps (max threads) |
|---|---|---|---|---|---|---|---|---|---|---|
| M | U-Net | 0.0510 | 0.00328 | 1.97 | 76 | 23,057× | 46.7 (24 threads) | 14,235× | 94 | 152 |
| M | FNO | 0.0761 | 0.00300 | 3.13 | 76 | 25,208× | 46.7 (24 threads) | 15,564× | 149 | 241 |
| L | U-Net | 0.0903 | 0.00652 | 1.55 | 277 | 42,487× | 149.4 (24 threads) | 22,916× | 20 | 37 |
| L | FNO | 0.1199 | 0.00281 | 0.91 | 277 | 98,581× | 149.4 (24 threads) | 53,172× | 12 | 22 |
