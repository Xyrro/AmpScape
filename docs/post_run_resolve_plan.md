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

## 6. Owner decision 2026-09-21 — approved in two parts, both before the v1.0 tag

1. Part 1 as planned (§1–4): all ≈ 180 `solver = cg+amg` T1R rows.
2. **Part 2:** every reference row with residual above 1e-9 or unmeasured. Target ≤ 1e-9; where double precision
   floors above that, record the achieved residual. Any row that cannot reach 1e-6 gets the QC flag and is excluded
   from the splits, never silently kept. Tier by tier, full audit after each tier, index republished once at the
   end; report counts, achieved-residual distribution and cost per tier. Store the per-pair residual for every T1R
   row. Start after XXL finishes; do not slow generation.

### 6.1 Measured scope of part 2 (non-T4 rows; T4/Omniscape has no single-system residual and is out of scope)

| tier | rows above 1e-9 (mostly `advanced`) | unmeasured `regions` (T1R) | unmeasured `points` (T1, K = 5–8, pair maps not kept) | shards touched | pair solves |
|---|---|---|---|---|---|
| S | 4 907 | 5 677 | 57 420 | 500 of 500 | 1 135 367 |
| M | 6 198 | 2 766 | 28 668 | 500 of 500 | 569 689 |
| L | 6 028 | 1 127 | 11 470 | 1 000 of 1 000 | 233 517 |
| XL (3 600 of 4 000 samples) | 2 043 | 190 | 2 075 | 601 of 667 | 43 192 |
| XXL | — (≈ 100 expected) | ≈ 60 | ≈ 200 | ≈ 400 | ≈ 3 000 |

The ≈ 19 000 figure in the owner's instruction is the "above 1e-9" column. The unmeasured T1 `points` rows (K ≥ 5,
whose pair maps are not stored) are ≈ 100 000 more rows; measuring them means solving all their pairs (that is the
measurement). Two readings, both implementable with the same tool:

- **(a) full:** above-1e-9 + unmeasured T1R + unmeasured T1 points ≈ 128 000 rows, ≈ 2.0 M pair solves
  (S ≈ 0.05 s, M ≈ 0.3 s, L ≈ 1.5 s, XL ≈ 3 s, XXL ≈ 15 s per pair incl. refactorisation) ≈ 250 CPU-h; every T1/T1R
  file of every shard rewritten and re-uploaded (≈ 300 GB, ≈ 9 h at the measured 35 GB/h); audits ≈ 25 core-h;
  ≈ 2–3 days of wall-clock after XXL.
- **(b) as literally scoped:** above-1e-9 rows + all T1R rows (≈ 29 000 rows, ≈ 60 000 pair solves, ≈ 15 CPU-h;
  ≈ 2 000 shards' files still touched because `advanced` rows are spread over every shard → ≈ 200 GB re-upload).

The tool selects rows by a rule (`solver == cg+amg` or `residual_rel > 1e-9` or `residual_rel` unmeasured, per
config list), so the choice between (a) and (b) is one flag. **Default: (a)** — it is the only reading under which
no reference row stays unmeasured, matches "never silently kept", and cost is not a constraint (owner 2026-09-21);
the owner is asked to confirm or restrict to (b) in the status report.

### 6.2 Row treatment (all parts)

Per pair: reduced system (ground node/region removed, source region collapsed) → CHOLMOD → one refinement step →
true residual; a second step if > 1e-9; LDLᵀ / PCG-refined as last resorts. Node currents by `node_current_map`,
`reff` from the source voltage, `cum_current` = Σ pairs; `advanced` = one solve with the source/ground strengths.
Written in place in the Hub task-group file: outputs, `solver_stats.residual_per_pair` (every T1R and T1 row gets
one), `resolved_post_run = {date, method, residual_before, residual_after}`, `solver_original` if the solver
changed; index columns `residual_rel` (max over pairs), `solve_time_s`, `qc_flags` (`resolved_post_run`, and
`residual_high` with `qc_pass = false` when > 1e-6 after all attempts → dropped from the split lists), new column
`solver_original`. Consistency check against the replaced result reported per row (rel-L2 of `cum_current`,
max rel diff of `reff`).

