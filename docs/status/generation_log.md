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
before starting any supervisor, never trust a pid file across login nodes.
