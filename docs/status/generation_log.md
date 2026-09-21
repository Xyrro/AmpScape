# v1.0 generation log

## 2026-09-16T00:37+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 0 | 0 | 0 | 0 | 0 | nan% | 0.0 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **0**. Stop rule: not triggered.

## 2026-09-16T16:45+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 153 | 0 | 0 | 0.000% | 30.4 | 73.5 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **1686**. Stop rule: not triggered.


## Incident 2026-09-16 — scratch quota exhausted during tier S

All 500 S shards solved at once (the scheduler granted 500 cores) while finalize ran in a separate array and the
sync deleted only the final shard after upload, so raw intermediates (≈ 245 MB/shard) plus finals (≈ 130 MB/shard)
filled the 300 GB scratch quota at 11:26Z. The task-group split of shard 12 was truncated by the full disk and
retried every 15 min without being counted; 149 finals written after 11:26Z were truncated as well. Recovery
(15:30–16:30Z): partial staging files removed, 83.6 GB of raw intermediates of validated shards deleted, the 149
truncated finals deleted and **re-finalized from their intact solver outputs (no solve lost; all 500 shards
re-validated, 0 QC failures)**, sync rewritten (per-shard temporary split always cleaned, one commit per shard,
two-failure stop rule), finalize now deletes intermediates on success, scratch budget and wave sizes in the
runbook §5. Upload rate after the fix ≈ 125 shards/h.

## Incident 2026-09-16 (b) — partial finalize race on tier S

The tier-S finalize array polled the solver outputs and finalized a shard as soon as *every sample present* was
complete — but the solver adds samples one by one, so 73 shards (the first shards of each polling range) were
finalized with 178–199 of 200 samples (shard 104 with 5), passed schema validation (which did not check the sample
count) and were uploaded; their raw outputs were then deleted by the quota recovery. Fix: finalize now refuses a
shard until all manifest samples are solved, validation and finalize compare the sample count with the manifest,
and the 73 shards are re-prepared, re-solved (≈ 220 core-hours), re-finalized and re-uploaded (the Hub files are
overwritten in place; the index is re-published).

## Incident 2026-09-16 (c) — double submission of the tier-S repair

The repair solve of the 72 short shards was submitted twice (the first submission's output was hidden by a log filter
and the driver-independent `submit` did not check the queue), so two array tasks solved the same shards concurrently:
50 tasks failed on opening a locked outputs file, 19 shards ended with corrupted outputs (both tasks writing the same
HDF5 file). Repair: corrupt outputs deleted, the 19 shards re-prepared and re-solved alone (6 h walltime, in-task
finalize with the solver completion marker). Fix: `generate.py submit` now skips any shard that already has a
pending or running array task for the build. Also in this window: the first integrity check flagged 53 complete
shards as invalid because their meta predated `skipped_configs`; the check now re-derives undefined configurations
exactly (regenerating sources), and the published index carries `skipped_configs` with reasons per sample.
## 2026-09-17T08:48+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **2061**. Stop rule: not triggered.

## 2026-09-17T10:16+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **2061**. Stop rule: not triggered.

## 2026-09-17T10:17+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **2061**. Stop rule: not triggered.

## 2026-09-17T15:51+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 160 | 80 | 40 | 0 | 0 | 0.010% | 13.5 | 12.1 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **2336**. Stop rule: not triggered.

## 2026-09-18T22:11+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 499 | 499 | 0 | 1 | 0.002% | 250.8 | 0.2 |
| L | 1000 | 0 | 0 | 0 | 0 | 0 | nan% | 0.0 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **3794**. Stop rule: not triggered.

## 2026-09-18T23:25+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **3852**. Stop rule: not triggered.

## 2026-09-19T06:03+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 200 | 87 | 87 | 0 | 0 | 0.033% | 21.4 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **5123**. Stop rule: not triggered.


## Incident 2026-09-19 (d) — duplicate supervisors after a session restart on a different login node

The operator session restarted on `login-ice-gnr-1` while the driver and the S/M/L sync supervisors from the previous
session were still running on `login-ice-gnr-2`; the pid-file liveness check (`kill -0`) cannot see processes on
another node, so the driver and an L sync loop were started a second time (05:59Z). Detected within ten minutes and
held via `logs/ALERT.txt`; the duplicate driver exited on the alert and the duplicate L sync loop was killed (06:1xZ).
No double submission occurred (one L array in the queue; `generate.py submit` skips shards with queued/running tasks)
and no shard was touched twice (uploads are marker-gated). Fix (commit b0fb76c): cross-host single-instance leases
(`logs/lease_<name>.json` with host, pid, owner, timestamp; a fresh lease held by another host/pid makes a new
instance stand down) for the driver and every sync loop. Rule from now on: check `logs/lease_*.json` (host + age)
before starting any supervisor, never trust a pid file across login nodes. Follow-up (06:40Z): the restarted driver
alerted "L sync supervisor not running" for the same reason (its liveness check read the host-local pid file); the
check now uses the sync lease's freshness on any host. The duplicate L sync's lease made the real L loop on the other
node stand down for one 25-min lease window; no data was affected.
## 2026-09-19T07:07+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 200 | 87 | 87 | 0 | 0 | 0.033% | 21.4 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **5331**. Stop rule: not triggered.

## 2026-09-19T08:51+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 200 | 165 | 157 | 0 | 0 | 0.024% | 38.6 | 1.9 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **5660**. Stop rule: not triggered.


## Note 2026-09-19 — waves stalled by aux job names

The driver submits the next wave only when no array of the tier is queued or running, and it tested that with a
job-name *prefix* (`ampscape-L…`), so the auxiliary arrays `ampscape-M_bs1`, `ampscape-M_b3_ca0`, … (block-size
studies) and `ampscape-L_bs1` counted as tier work: several M waves and L wave 3 waited for hours behind them. Fixed
(exact name match, commit 08:53Z); wave 3 of L went out ten seconds after the restart. Also widened the driver's sync
liveness window to 60 min: a sync cycle is a 15-min sleep plus up to ~15 min of uploads, and the lease is refreshed
once per cycle.

## Incident 2026-09-19 (e) — finals validated while still being written (root cause of M 434 and L 189)

`finalize` wrote the final shard directly under its final name while the sync loop lists `shards/*.h5` every 15 min:
a final caught mid-write failed to open ("bad object header"), was marked `.invalid`, and the driver alerted; both
shards were re-finalized from their intact outputs (no solve lost). Fix: finalize writes `<shard>.h5.part` and
renames atomically on completion; the sync skips `.part` files and any final younger than three minutes.
## 2026-09-19T12:19+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 300 | 178 | 170 | 0 | 0 | 0.027% | 41.6 | 1.8 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **6381**. Stop rule: not triggered.

## 2026-09-19T17:11+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 400 | 338 | 329 | 0 | 0 | 0.029% | 80.9 | 2.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **7254**. Stop rule: not triggered.


## Incident 2026-09-19 (f) — L walltime undersized; timed-out shards never resubmitted

Walltime for L shards was 04:00:00 (runbook estimate 590 s × 20 = 3.3 h). Measured on 6 760 finalized L landscapes:
median 604 s, p90 939 s, p99 1 072 s, max 1 198 s per landscape (slowest: GRF and `random_cluster` landscapes, several
`rmax_saturated`), i.e. **3.6 h median / 3.9 h max of solve per 20-landscape shard before ~4 min Julia start-up and the
finalize step** — 62 of the 400 shards of waves 1–4 timed out. They were never re-queued because both the submit filter
and the driver treated an existing outputs file as "solved"; the sync backlog stayed small, so the waves kept going.
Cost: 569 core-hours were spent in timed-out L tasks (2 cores × 4 h × 62 + partial), but the solver is resumable and
1 165 of the 1 240 landscapes in those shards are complete inside the partial outputs, so the loss is ≈ 75 landscapes ×
~10 min plus 62 Julia start-ups ≈ 20 core-hours of solve; the larger waste is the second allocated core (BLAS threads
only) on every L task since the tier started (≈ 40 % of L core-hours). S and M also had 16 + 1 timed-out tasks
(64 + 4 core-hours), all re-run at the time. Fixes: "solved" = solver completion marker (submit filter and driver);
the driver re-queues every submitted shard without a marker at each 10-min cycle regardless of running arrays (the
submit guard skips queued/running shards; alert after three rounds); walltimes from the measured tail —
shard_size × p99 × 1.15 + 20 min: L 08:00 (20 landscapes), XL 10:00 (6), XXL 10:00 (1); L now 1 core.
## 2026-09-20T00:27+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 600 | 500 | 500 | 0 | 0 | 0.023% | 123.6 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **7939**. Stop rule: not triggered.

## 2026-09-20T08:35+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 800 | 700 | 657 | 0 | 0 | 0.019% | 181.0 | 14.2 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **8670**. Stop rule: not triggered.


## Note 2026-09-20 — false "sync supervisor not running" alerts

The L sync loop's upload cycles grew beyond an hour once real L shards (≈ 0.3 GB each, 75 per cycle) started landing,
and the loop wrote its lease only at the start of a cycle, so the driver's 1-h liveness window fired twice (09:07Z,
09:15Z) while the loop was busy uploading; no data affected, generation paused ≈ 10 min. Fix: the sync refreshes its
lease after every uploaded shard and the driver's window is 2 h.

## Incident 2026-09-20 (g) — one L shard failed on every resubmission (solver KeyError)

Shard 737 (real L tiles) died in the first two minutes of each of three resubmissions: a pairwise configuration
whose reduced system is not positive definite (an ungrounded component) took the "refinement skipped" branch added on
2026-09-16, which returned without the `residual_after` field the caller reads. Fixed (the branch reports the
unrefined residual), precompiled, shard re-queued; the driver's three-round rule caught it as designed. No other S/M/L
task log shows the error.
## 2026-09-20T13:35+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 800 | 799 | 754 | 0 | 0 | 0.017% | 237.1 | 15.4 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **9283**. Stop rule: not triggered.

## 2026-09-20T22:00+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| S | 500 | 500 | 500 | 500 | 0 | 0 | 0.000% | 142.2 | 0.0 |
| M | 500 | 500 | 500 | 500 | 0 | 0 | 0.002% | 251.5 | 0.0 |
| L | 1000 | 1000 | 900 | 900 | 0 | 0 | 0.015% | 322.6 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **10144**. Stop rule: not triggered.

## Incident 2026-09-21 (g2) — L audit false positive: "missing on Hub: T1R" on 41 shards

The L audit (job 5879007, 1 h 07) reported 41 shards with discrepancies, all of one kind: `missing on Hub:
data/L/T1R/shard-XXXXX.h5`. In each of these shards every sample with a planned `regions` configuration had it
legitimately skipped (`regions (T1R: no eligible habitat patches …)`, recorded in `skipped_configs`), so finalize
wrote no T1R part and the sync uploaded none; the sample-level checks (ids, configs minus skipped, index rows) all
passed. The audit derived the expected task-group files from the *planned* configurations before it knew the
skipped ones, so it demanded a file that could not exist. M never hit this because its shards hold 100 samples
(no M shard had every `regions` sample skipped); L shards hold 20. The `regions` skip rate is the same at both tiers
(M 50.3 % of the 28 960 planned, L 47.1 % of 11 603 — mostly real tiles whose largest component has < 2 habitat
patches), a labelled property of the data (`skipped_configs`), not a defect. Fix (`scripts/audit_tier.py`): a group
without a Hub file is an error only if some sample still wants a configuration of that group after skipping;
otherwise it is recorded as `absent_groups_all_skipped`. No data was changed; the driver exited on the alert as
designed and is restarted after the re-audit (job 5879589) comes back clean. Cost: ≈ 9 core-h for the two audits.

## 2026-09-21T03:33+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| L | 1000 | 1000 | 1000 | 1000 | 0 | 0 | 0.013% | 380.5 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **10273**. Stop rule: not triggered.

