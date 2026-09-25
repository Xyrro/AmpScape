# WP7 — many-query demonstration (2026-09-25)

Best T4 model at L: `unet_T4_L_s1` (rel-L2 0.080 vs the exact block-1 map on test_id). 20 held-out real L tiles × 8 resistance tables (4 expert tables, the v1.0 `random_lm` draw, 3 extra draws `random_lm2..4` solved with the production pipeline, QC 100 %). Question: do the conclusions of a many-table screening study drawn from the surrogate match those drawn from the solver? Produced by `scripts/wp7_demo.py run` (GPU job 5934206, 79 s); per-tile rows on the Hub under `aux/wp7/demo_results.parquet`.


| conclusion | solver route | model route | agreement |
|---|---|---|---|
| stability of the top-5 % regions across tables (mean pairwise IoU) | 0.463 | 0.458 | mean abs. difference of the IoU matrices 0.019 |
| consensus core (top-5 % in ≥ 75 % of tables), fraction of valid pixels | 0.0357 | — | IoU model-vs-solver core 0.825 (median 0.843) |
| ranking of tables by effect vs `generic_hm` | — | — | Spearman 0.991; same most-influential table in 100% of tiles; top-3 overlap 0.98 |
| persistent pinch points (≥ 50 % of tables) | 5586.6 per tile | — | recall 0.941, precision 0.657 (3-px tolerance) |
| per-map accuracy (context) | — | rel-L2 vs solver mean 0.054, worst table 0.100 | |
| total cost for 160 maps | 36.3 CPU-h (817 s per map, 1 core) | 11.8 s on one GPU (74 ms per map) + training once | ×11077 |

Per-tile rows: `aux/wp7/demo_results.parquet`. Tables: the four expert tables, the v1.0 per-tile `random_lm` draw and
three extra random draws (`random_lm2..4`, aux/wp7). Solver times are the recorded Omniscape wall times (CHOLMOD, 1 core).
