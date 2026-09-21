# Post-run pass: re-solve the `solver = cg+amg` rows at reference precision (plan, 2026-09-21)

Owner instruction (2026-09-21, incident (h)): fallback rows must match the reference precision; test 1e-9 on the
shard-83 diagnostic sample; if reachable, plan a pass before the v1.0 tag that re-solves every `solver = cg+amg`
row at 1e-9 with sufficient memory and replaces it in place, then re-run the audit; report count and cost first.

## 1. Is 1e-9 reachable? Yes — with a direct solve, not with CG

Diagnostic job 5887428 (`julia/AmpScapeSolve.jl/scripts/diag_regions_precision.jl`) on the shard-83 sample
`6f1492da…` (XL, fractal, contrast 10⁶, 5 regions of 15–119 k pixels, 10 region pairs; the sample on which
Circuitscape's CHOLMOD path raised `PosDefException`). For every pair the reduced system was built exactly as
`refine_voltage!` does (grounded region removed, source region collapsed to one node, 0.86–1.01 M free nodes):

| method | pairs solved | relative residual (min / median / max), before refinement | time per pair | peak memory |
|---|---|---|---|---|
| CHOLMOD on the reduced system | 10 / 10 | 2.6e-10 / 4.2e-9 / 7.6e-8 | 3 s | 5.8 GB |
| CHOLMOD LDLᵀ | 10 / 10 | 1.1e-10 / 3.4e-9 / 1.6e-7 | 8–18 s | 5.8 GB |
| AMG-PCG (Ruge–Stüben), recursive residual to 1e-12 | 10 / 10 | true residual 1.9e-10 / 2.2e-9 / 9.1e-8 (1 000–1 850 iterations) | 180–375 s | 5.8 GB |

The direct factorisation always succeeds on this formulation (the failure is inside Circuitscape's own regions path,
not a property of the matrix) and its unrefined residual is at the double-precision floor for a conditioning of
10⁶–10⁷ (1e-10–1e-7). One step of iterative refinement with the same factorisation — what the production pipeline
applies to every CHOLMOD row (their median residual after refinement is 2e-11, p99 ≈ 1e-8) — brings that below 1e-9;
CG alone cannot be trusted below ≈ 1e-8 (its recursive residual reaches 1e-12 while the true residual stalls at
1e-9–1e-7). So the pass uses **CHOLMOD on the reduced system + one refinement step, per pair, with the true residual
verified per pair** (target ≤ 1e-9; a second refinement step if not; LDLᵀ then PCG-refined only as last resorts,
reported). Circuitscape's CG tolerance is hard-coded, which is why the fallback rows were never at 1e-9 by construction.

## 2. Rows to re-solve (every `solver = cg+amg` row; all are `regions`, i.e. T1R)

| tier | rows | samples | shards affected | measured residual today |
|---|---|---|---|---|
| S | 9 | 9 | 9 | 2 above 1e-9, 7 below or unmeasured |
| M | 14 | 14 | 14 | 7 unmeasured (no pair maps), 7 below 1e-9 |
| L | 110 | 110 | 102 | 32 unmeasured, 13 above 1e-9 (max 2.1e-7), 65 below |
| XL | 39 of 3 600 samples so far → ≈ 43 expected | ≈ 43 | ≈ 43 | 9 unmeasured, 12 above 1e-9 (max 5.2e-6) |
| XXL | 240 regions planned, ≈ 120 solved, ≈ 4 expected | ≈ 4 | ≈ 4 | — |
| **total** | **≈ 180** | ≈ 180 | ≈ 172 | |

"Unmeasured": T1R outputs keep only `cum_current`, `reff`, `pair_index`, `labels` (no per-pair voltages), so for
these rows neither the Kirchhoff residual nor the refinement ran in production (`residual_rel = NaN`,
`qc_flags = fallback_solver`). The pass measures every pair.

## 3. What the pass does (per affected sample; `scripts/resolve_fallback_rows.py` + a Julia entry point)

1. Read the shard's inputs (re-prepared from the manifest, deterministic) and the current T1R outputs from the Hub.
2. For each region pair: reduced system → CHOLMOD → refinement → verify residual ≤ 1e-9; node currents by
   `node_current_map` (Circuitscape's definition, region pixels carry the merged node's current); `reff` from the
   source region's voltage; `cum_current` = Σ pairs.
3. Consistency check against the replaced CG result: relative L2 of `cum_current` and max relative difference of
   `reff` (expected ≤ 1e-5; every case reported).
4. Rewrite the sample's `regions` group in `data/<tier>/T1R/shard-XXXXX.h5` in place; `solver_stats`: `solver =
   "cholmod"`, `solver_original = "cg+amg"`, `resolved_post_run = {date, residual per pair, method}`; index row:
   `solver = cholmod`, `residual_rel`, `solve_time_s`, `qc_flags += resolved_post_run`, new column
   `solver_original` (provenance, as required). Local intermediates deleted after the verified upload.
5. Upload the rewritten T1R files (one commit per shard, sha256 verified), republish `index/<tier>.parquet`,
   re-run `audit_tier.py` for every affected tier (full Hub-vs-plan audit), update the datasheet with the per-tier
   counts of re-solved rows and the residual distribution after the pass.

## 4. Cost

| item | estimate |
|---|---|
| solves: ≈ 180 samples × ≤ 10 pairs × (3 s + refinement) at XL, ≈ 15 s per pair at XXL, < 1 s at S–L | ≈ 3–5 CPU-h (memory ≤ 6 GB at XL, ≈ 24 GB at XXL) |
| re-prepare inputs for ≈ 172 shards | ≈ 2 CPU-h |
| download + rewrite + re-upload ≈ 172 T1R files (S 20 MB … XXL 300 MB each) | ≈ 10 GB, ≈ 1 h on the login node |
| audits: S, M, L, XL, XXL (full Hub-vs-plan; L took 1 h 07 on 4 cores) | ≈ 25 core-h, ≈ 6 h wall (tiers in parallel) |
| **total** | **≈ 35 core-h, one working day of wall-clock after XXL completes** |

## 5. Related, for a separate decision

1.1 % of the CHOLMOD reference rows also sit above 1e-9 (S 4 905, M 6 198, L 6 015, XL ≈ 2 000; above 1e-8: 122 /
160 / 196 / 109; maxima 5e-7 / 2.8e-6 / 2.4e-5 / 3.5e-6): the rows where refinement was skipped (ungrounded
components, `rmax_saturated`) or where the residual is unmeasured by design (T4 `omniscape` rows, and `points` /
`regions` rows without pair maps). Bringing every measured row under 1e-9 would extend the same pass to ≈ 19 000
rows (≈ 600 CPU-h at the same per-pair cost); rows without pair maps cannot be checked without keeping per-pair
voltages. Not part of this plan unless the owner asks.
