# Post-run precision pass — per-tier summary (from the index; every T1/T1W/T1R/T3 row carries its true Kirchhoff residual)

| tier | rows re-solved | of which `cg+amg` (now `cholmod`) | residual after: p50 / p90 / p99 / max | rows > 1e-9 (floor, recorded) | rows > 1e-6 (flagged, excluded from splits) | non-T4 rows unmeasured | non-T4 rows QC-fail (all) |
|---|---|---|---|---|---|---|---|
| S | 68,008 | 9 | 2.9e-13 / 3.4e-11 / 1.6e-09 / 5.0e-07 | 1,013 | 0 | 0 | 0 |
| M | 37,639 | 14 | 9.1e-13 / 1.9e-10 / 5.2e-09 / 1.4e-06 | 1,136 | 4 | 0 | 4 |
| L | 18,691 | 110 | 6.8e-12 / 4.9e-10 / 1.4e-08 / 1.5e-05 | 1,014 | 9 | 0 | 10 |
| XL | 4,774 | 47 | 6.9e-11 / 1.3e-09 / 4.3e-08 / 6.6e-06 | 551 | 5 | 0 | 6 |
| XXL | 610 | 9 | 2.7e-10 / 4.3e-09 / 2.0e-07 / 4.0e-05 | 147 | 2 | 0 | 2 |
| **total** | **129,722** | 189 | | 3,861 | 20 | 0 | 22 |

Rows above 1e-6 after CHOLMOD + up to three refinement steps (and LDLᵀ / AMG-PCG as last resorts) are all synthetic
landscapes at contrast ≥ 10⁴; they carry `residual_high`, `qc_pass = false`, and their samples are excluded from the
split lists (the rows stay in the index with their achieved residual). Provenance per re-solved row:
`qc_flags` contains `resolved_post_run`, `solver_original` holds the production solver when it changed, and
`solver_stats.resolved_post_run` (per-pair residuals, methods, refinement steps, consistency with the replaced maps).
