# Status — 2026-09-22 05:20Z (tier XL complete and audited; XXL starting; precision pass ready)

## Tier XL boundary

| item | value |
|---|---|
| shards validated, uploaded, audited | 667 of 667 (4 000 landscapes, 21 006 index rows) |
| full Hub-vs-plan audit | clean (0 discrepancies, 3 132 files) |
| QC fail rate | 0.033 % |
| GB on Hub | XL 281.3 (S 142.2, M 251.5, L 380.5; total 1 056) |
| upload window | 09-21 09:03Z → 09-22 04:08Z (19.1 h), 4 workers, peak hour 125 shards / 35 GB |
| XL core-hours (1 cpu per task) | 3 684 (estimate 2 800; 4 OOM re-runs and the probe included) |
| core-hours since 09-15, all ampscape-* jobs | 13 986 of the 30 000 gate |
| wall-clock XL | 20 h 51 from first submission (08:24Z) to audited complete (05:15Z) |
| scratch | 128 GB |

Incidents: (h) four shards OUT_OF_MEMORY on the `regions` CG+AMG fallback (root cause `PosDefException` in
Circuitscape's CHOLMOD path; profile 20 GB, automatic 48 GB re-runs) — no data lost; the fallback rows (47 at XL)
are re-solved by the post-run precision pass. Rows for that pass at XL: 2 225 above 1e-9, 2 526 unmeasured (non-T4).

## XXL
400 shards (1 landscape each; all test splits; 240 regions configs) planned and prepared ahead; the driver picked them
up at the boundary (`prepared_upto = 399`) and submits wave 0–299 at 1 cpu / 24 GB (test shards 28 GB), 10-h walltime,
4 uploaders; ≈ 3–5 h per shard → XXL audited ≈ 2026-09-22 16–20Z.

## Precision pass (owner 2026-09-21, two parts)
Tooling validated end-to-end (`docs/post_run_resolve_plan.md` §7, runbook §8); starts after XXL, tier by tier.
