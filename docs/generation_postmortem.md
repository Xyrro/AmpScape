# AmpScape v1.0 generation — post-mortem

Scope: the v1.0 run on Georgia Tech PACE-ICE (Slurm, account `coc`, QoS `coc-ice`), 2026-09-16 → 2026-09-23: five
tiers (S 128² … XXL 2048²), 174 400 landscapes, 902 904 configuration rows, 1 157 GB on `Xirro/AmpScape`, followed by
the post-run precision pass. Sources: `docs/status/generation_log.md` (every entry), `DECISIONS.md`, `logs/driver.log`.

## 1. Timeline

| when (UTC) | event |
|---|---|
| 09-14 | v1.0 freeze (`v1.0-pipeline` = 8491bbe); owner: run on ICE, public Hub repo, 13 000 core-hour budget |
| 09-16 00:37 | tier S launched (500 shards × 200 landscapes); streaming sync loop |
| 09-16 | incidents (a) scratch quota exhausted, (b) partial-finalize race, (c) double submission — fixed; S repaired |
| 09-17 10:17 | tier M (driver, waves of 80); S audit clean 09-17 |
| 09-18 23:25 | M complete and audited; tier L (waves of 100) |
| 09-19 | incidents (d) duplicate supervisors on two login nodes → leases; (e) finals validated mid-write → atomic rename; (f) L walltime undersized (62 shards timed out silently) → tail-based walltimes, marker-based "solved", per-cycle resubmission; (g) `residual_after` KeyError |
| 09-21 03:34 | L complete; first audit falsely flagged 41 shards (g2: all-skipped T1R) → audit rule fixed, clean 03:33 |
| 09-21 | budget stop: XL/XXL core-hour estimates had been single-core hours while the profile allocated 4/8 cpus; owner: cost is not a constraint, optimise wall-clock, 30 000-hour gate; XL probe → 1 cpu; parallel uploaders; waves of 300 |
| 09-21 08:24 | XL launched (300 concurrent tasks, 4 uploaders); (h) OOM on the `regions` CG+AMG fallback (36–42 GB) → 20 GB profile, 48/176 GB re-runs; scratch clean-up (quicklooks, logs, pilot builds); slip: `data/builds/published` deleted and regenerated; all scratch-only evaluation assets published under `aux/` |
| 09-22 05:15 | XL complete and audited (20 h 51); XXL launched (pre-planned, pre-prepared) |
| 09-22 06:16 | (i) Omniscape CHOLMOD abort on a contrast-10⁶ 2048² mosaic; false QC-rate alert on a 5-row sample; second alert at 1.11 % → threshold 5 % for XXL with the repair path; index `.part` defect fixed; (j) OOM leftovers corrupt the outputs file → set aside automatically |
| 09-22 15:24 | **all tiers complete and audited**; 15 218 core-hours |
| 09-22 15:30 → 09-23 20:44 | precision pass S → M → L → XL → XXL (129 722 rows), five clean audits, indexes republished; (k) Hub commit limit, cluster submit limit 500 → 50, memory-killed XL/XXL workers, package precompile |
| 09-23 | finalisation: card, Croissant, statistics figures, v1.0 tag |

## 2. Incidents, root causes, fixes

| id | what happened | root cause | fix (code / process) |
|---|---|---|---|
| a | sync stuck, `Disk quota exceeded` (scratch 300 GB) | intermediates and finals of 500 S shards kept until upload; one commit per file | validated shards' raw files deleted at finalize; one Hub commit per shard with per-shard temp staging; waves sized to the scratch budget; two-failure stop rule; quota-based guard |
| b | 72 S shards finalized with < 200 samples | finalize ran while the solver was still writing (resumable tasks) | solver completion marker written last; finalize requires it; sample-count and planned-configuration integrity check; re-solved and replaced (72/72 confirmed) |
| c | 19 corrupt outputs | a repair array submitted while the original tasks still ran | `submit` skips shards with a queued/running task; driver never double-submits |
| — | 53 M shards falsely `.invalid` | legacy meta without `skipped_configs` | skipped configurations re-derived exactly by source regeneration (serialised: NLMpy global RNG) |
| d | duplicate supervisors after a session restart on another login node | pid files are host-local | cross-host leases `logs/lease_*.json` (25-min freshness, refreshed per uploaded shard) |
| — | `Invalid qos specification` | ICE default QoS changed | profile sets `qos: coc-ice` |
| e | finals validated while still being written (M 434, L 189) | non-atomic final write | write `.h5.part`, `os.replace`; sync skips files younger than 3 min |
| f | 62 L shards timed out silently, never re-queued; 569 core-h in timed-out tasks | walltime from the median; "outputs exist" counted as solved; 2 cores allocated for a single-threaded solver | walltime = shard × p99 × 1.15 + 20 min (L 9 h, XL/XXL 10 h); "solved" = completion marker; resubmission every driver cycle; 1 core |
| g | shard 737 `KeyError residual_after` | `refine_voltage!` did not set the field when Cholesky failed | field set on failure |
| g2 | L audit flagged 41 shards "missing T1R" | audit expected a task-group file even when every planned `regions` config of the shard was legitimately skipped | absent group is a discrepancy only if a non-skipped configuration wants it |
| — | budget stop before XL | runbook counted XL/XXL in single-core hours; profile allocated 4/8 cpus (charged) | owner decision: 30 000-hour gate, wall-clock optimisation; probe → 1 cpu (no BLAS gain) |
| h | XL/XXL OOM (16 → 32 GB, later 176 GB) | `regions` (T1R) CHOLMOD raises `PosDefException` on high-contrast region-merged Laplacians; Circuitscape's CG+AMG fallback needs 36–42 GB at 1024² | fallback rows kept, memory sized for the fallback, OOM-aware resubmission (memory sticks for the shard), corrupt-outputs guard (j); rows later re-solved by the precision pass with reduced-system CHOLMOD |
| — | `data/builds/published` deleted with the pilot builds | deletion ran before its reference check was read | regenerated identically (ids verified); every scratch-only evaluation asset published under `aux/`; rule: no deletion without listing exact paths |
| i | Omniscape/T3 solves aborted on contrast-10⁶ 2048² landscapes (both solvers) | Circuitscape 5.17.1 `solve_linear_system` throws when the relative residual is ≥ 1e-4 (unrefined CHOLMOD; capped CG) | AmpScapeSolve installs replacements at load time: refinement where Circuitscape would throw, bit-identical otherwise, counted per row; T4/T3 rows that had failed re-run by the precision pass; QC-rate rule needs ≥ 20 shards / 200 rows, XXL threshold 5 % |
| — | index `shard` column carried `.h5.part` | index rows written while the final was the staging file | fixed at the source; all indexes republished |
| k | precision pass: commit rate limit (128/h), submit limit 500 → 50, memory-killed workers, uncached package | Hub and cluster policy; real-tile T1 rows with K = 8 at 1024²/2048²; method replacement during precompilation | batched uploads (20 shards/commit, back-off); work-queue workers; 48–128 GB workers with automatic 96/176 GB re-runs; `__init__`-time replacements; explicit GC between pairs |

## 3. Final cost

| item | value |
|---|---|
| core-hours, all `ampscape-*`/`precision-*`/`audit-*` jobs since 09-15 | **16 552** (generation tiers 14 379; precision pass 1 249 incl. Julia start-ups; audits 30; aux/probes/planning/prepare/diagnostics 893) of the 30 000-hour gate |
| by tier (generation tasks) | S 2 061, M 1 692, L 5 713, XL 3 684, XXL 1 228 |
| wall-clock, generation | 09-16 00:37 → 09-22 15:24 (6.6 days; XL 20 h 51, XXL 10 h) |
| wall-clock, precision pass | 29 h |
| data on the Hub | 1 157 GB (S 142, M 252, L 381, XL 282, XXL 101) + 20.5 GB `aux/`; core subset 115 GB, mini 0.6 GB |
| scratch peak | 215 GB (quota 300); base 114 GB without in-flight data |
| QC | 25 of 902 904 rows fail QC after the pass (24 samples excluded from split lists); 3 861 rows carry a residual between 1e-9 and 1e-6 (double-precision floor, recorded) |

## 4. Runbook changes anyone reproducing this needs

1. **Solved = completion marker**, never "outputs exist"; finalize refuses partial shards; `.h5.part` + atomic rename.
2. **Walltimes from the measured tail** (p99 × 1.15 + start-up), not the median; the driver resubmits missing shards every cycle and raises memory for shards that ever went OUT_OF_MEMORY; unreadable outputs files are set aside automatically.
3. **Cluster limits are not constants:** the QoS submit limit dropped from 500 to 50 jobs mid-run and the default QoS changed once; read them at submission (`sacctmgr show qos`), pack shards per task, and use long-lived work-queue workers when the limit is small.
4. **Hub limits:** 128 commits per hour → batch many shards per commit; verify sha256 after every commit; the login node's network is not the bottleneck (35–70 GB/h).
5. **Scratch:** keep a quota-based guard (not `du` of one directory), delete raw intermediates on validated finalize, never keep quicklooks/logs of finished tiers on scratch, size waves by in-flight raw output (steady state ≈ concurrency × mean partial output).
6. **Memory:** the `regions` CG+AMG fallback and real-tile T1 rows need 36–50 GB at 1024² and 128–176 GB at 2048²; the reduced-system CHOLMOD path of the precision pass needs 48/128 GB per worker at XL/XXL.
7. **Solver:** Circuitscape 5.17.1's 1e-4 residual check aborts whole maps; keep the rescue (`AmpScapeSolve.__init__`) and count rescued solves; CHOLMOD alone does not reach 1e-9 on contrast ≥ 10⁴ problems — refine.
8. **Audit and publish from the per-shard index rows**, never from a derived copy; one shard-name spelling; an absent task-group file is a discrepancy only when a non-skipped configuration needs it.
9. **Operational hygiene:** cross-host leases for every long-lived loop, detached supervisors with pid locks, no deletion without listing exact paths, no evaluation asset that exists only on scratch (`aux/`).
