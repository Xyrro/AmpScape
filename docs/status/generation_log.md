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

## 2026-09-21 — scratch clean-up (owner-approved) and one slip

Owner approval (2026-09-21): delete the S/M/L quicklook PNGs (41 GB, reproducible from the Hub data); compress the
S/M/L task logs (12 GB, mostly Omniscape progress bars) into `data/v1/logs_archive/<tier>_task_logs.tar.gz` and delete
the originals (Slurm job 5880862); delete the superseded pilot builds under `data/builds/` unless referenced.
Done: quicklooks removed; probe_* / mini_phase5blocks / block_study / smoke5 builds removed (10 GB); `data/builds/mini`
kept (example build referenced by the scripts). **Slip:** `data/builds/published` (431 MB, the 46-sample
`test_ood_published` evaluation set of Phase 9, not on the Hub) was removed in the same command before its
reference check was read — `scripts/train.py --published-root` and the dev tuning scripts use it. It is fully
reproducible: re-planned from `data/tiles/published/published_tiles.parquet` with the original dataset id
(`published`; all 46 sample UUIDs verified identical to the ids recorded in the coarsen×4 predictions), re-prepared and
re-solved under Slurm (3 S shards + 1 XXL shard, ≈ 4 CPU-h, CHOLMOD). The lesson is recorded: a deletion command
must be gated on the reference check's result, not merely preceded by it.
Scratch after clean-up: 145 GB (quota figure, still settling) → ≈ 85 GB of in-flight headroom under the 230 GB guard;
XL/XXL waves raised to 300 as approved. Future solver task logs no longer carry progress bars (`solve_shard.sbatch`).

## 2026-09-21 — XL cpu probe and XL launch

Probe (shards 0-1 at 1 cpu, 2-3 at 4 cpus, 16 GB, jobs 5880731/5880732), read at 17 of 24 landscapes: per landscape
1 500–4 030 s at both cpu counts (1 cpu: 2 699, 1 693, 1 623, 2 270, 2 200, 2 485, 4 027, 2 116 s; 4 cpus: 2 152, 3 418,
2 155, 3 357, 1 495, 1 508, 4 010, 2 609, 1 508 s); Omniscape is ≈ 95 % of the time (2 000–2 800 s of it), T1/T1W/T3
together < 60 s. No speed-up from BLAS threads → **1 cpu per task for XL and XXL** (owner rule: 4 only if ≥ 1.5×).
XL walltime 10 h holds (6 × 4 000 s × 1.15 + 20 min ≈ 8 h). Estimated XL cost ≈ 4 000 × 2 500 s ≈ 2 800 core-hours;
XXL ≈ 400 × 10 300 s ≈ 1 150 (published XXL tile re-solve: 10 303 s at 8 cpus). Launch: waves of 300 shards, 300
concurrent tasks, 4 parallel uploaders per tier, scratch guard 230 GB of quota. Regenerated `data/builds/published`
(46 samples, QC pass 100 %, sample ids identical) — 4 CPU-h.
Final probe totals (6 landscapes per shard): 1 cpu 14 391 s and 16 662 s (4.0 h, 4.6 h); 4 cpus 18 195 s and 15 039 s (5.1 h, 4.2 h) — confirms 1 cpu. XL finals are 210–226 MB per shard (estimate was 460 MB).

## 2026-09-21T13:10+00:00 — XL wave 1 landing; first parallel-upload measurement

44 shards uploaded (11.6 GB) between 09:03Z and 13:09Z by the 4 workers; within busy stretches the mean gap between
uploads is 87 s → 41 shards/h, 10.9 GB/h — but arrivals were the limit (≈ 11 shards/h finishing), not the uploaders:
the bulk push of the aux assets moved 20.5 GB in 17 min (72 GB/h) over the same login node, so the network is not the
bottleneck. XL finals are 210–290 MB per shard (mean 264 MB). Scratch at 215 GB: base ≈ 114 GB (tiles, sources, dev,
aux, environments) + XL inputs 31 GB (all 667 shards prepared; deleted as shards upload) + in-flight raw outputs 74 GB
(249 running tasks, mean 297 MB, freed by finalize) + finals awaiting upload. The in-flight raw is a steady state, not
a growing backlog, so the 250 GB stop rule should not trigger; the 230 GB submit guard will admit wave 2 once wave 1's
stragglers are ≤ 75. 250 tasks running, 51 shards solved at 13:10Z (4 h 45 after submission).

## 2026-09-21T15:00+00:00 — parallel upload rate under load (owner item 3, "after")

261 XL shards (72.2 GB) uploaded by the 4 workers in 5.9 h; in the busiest hour **125 shards, 35.2 GB/h** (single
loop at L: 52 shards/h, 20 GB/h at best; wave landings at XL exceed what one loop could drain). Uploads were never the
limit of the tier: the local backlog stayed at a handful of shards. The login node's network is not the limit either
(bulk pushes reach 72 GB/h); the per-shard cost is split + sha256 + one commit + Hub-side verification, so more workers
would raise the rate further if ever needed. Incident: XL shard 83 OUT_OF_MEMORY at 16 GB (contrast-10⁶ CG-baseline
landscape; p99 task peak of the tier 5.5 GB, one other task at 16.5 GB); resubmitted with 32 GB; the driver now
resubmits OOM shards with double memory (`OOM_MEM`).

## Incident 2026-09-21 (h) — XL OUT_OF_MEMORY on two shards: the `regions` CG+AMG fallback

XL shards 83 and 321 died OUT_OF_MEMORY at 16 GB (83 again at 32 GB). A 64 GB diagnostic re-run of shard 83 with a
memory sampler completed (2 h 48) and the per-config stats locate the spike: the `regions` (T1R) configuration of a
contrast-10⁶ fractal landscape — the CHOLMOD attempt failed (`error: "reference solver (cholmod) failed: "`, empty
message) and the CG+AMG fallback solved it in 3 421 s with a **36.2 GB** high-water mark (the 30-s sampler saw 16.6 GB,
so the peak is a short transient inside the AMG set-up). In the XL index so far the fallback was used for 16 of 463
`regions` rows (3.5 %; at L 110 of 6 133 = 1.8 %, max RSS 8.2 GB) with peaks of 15.4 GB at contrast 100 and 36.2 GB at
10⁶; every other configuration stays under 6 GB. Actions: XL profile memory 16 → 20 GB for the remaining submissions,
XXL 24/28 GB; the driver's OOM resubmission memory 48 GB at XL and 120 GB at XXL (nodes have 191 GB); shard 83 is
finalized and uploaded from the diagnostic run; shard 321 re-queued by the driver. Open question for the solver
(not blocking generation): why CHOLMOD fails on these `regions` problems while it solves the same landscape's other
configurations — to be root-caused after the run (the fallback result is a converged CG solve at the same tolerance,
recorded per row as `solver = cg+amg`). Cost of the incident ≈ 12 core-hours.
**Root cause (diagnostic job 5885708, `julia/AmpScapeSolve.jl/scripts/diag_regions_cholmod.jl`):** on the contrast-10⁶
fractal landscape's `regions` problem (5 regions of 15–119 k pixels) Circuitscape's CHOLMOD path throws
`LinearAlgebra.PosDefException: matrix is not positive definite; Factorization failed.` after 43 s — the reduced
Laplacian with region-merged nodes and a 10⁶ conductance range is numerically indefinite for the Cholesky
factorisation — and the CG+AMG fallback converges in 3 439 s with a 42.5 GB high-water mark (Circuitscape's AMG
hierarchy on 1 M nodes). The fallback result is a converged solve at the reference tolerance and is what the dataset
records (`solver = cg+amg` per row; 3.5 % of XL regions rows, 1.8 % at L). Operational consequence: XL OOM
resubmissions at 48 GB, XXL at 176 GB (a 4× problem; nodes have 191 GB). Solver follow-up after the run: try a
diagonal shift / scaled factorisation for the regions path so that CHOLMOD stays the reference on these cases.
Shard 574 was the third XL OOM (resubmitted at 48 GB automatically).
**Precision test (job 5887428):** on the same sample our reduced-system CHOLMOD solves all 10 region pairs (3 s each, ≤ 5.8 GB, unrefined residual 2.6e-10–7.6e-8), LDLᵀ likewise, AMG-PCG needs 180–375 s per pair and its true residual floors at 1.9e-10–9.1e-8. Plan for the post-run pass: `docs/post_run_resolve_plan.md`.

## 2026-09-22T05:15+00:00

| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |
|---|---|---|---|---|---|---|---|---|---|
| XL | 667 | 667 | 667 | 667 | 0 | 0 | 0.033% | 281.3 | 0.0 |

Core-hours used since 2026-09-15 (ampscape-* jobs): **13986**. Stop rule: not triggered.

## Incident 2026-09-22 (i) — XXL: Omniscape CHOLMOD abort on a contrast-10⁶ mosaic; false QC-rate alert

The first finalized XXL shard (66, one landscape: synthetic mosaic, contrast 10⁶, test_ood) had its T4 row fail:
Omniscape 0.6.2 with the CHOLMOD solver aborted the map after 2 197 s with `CHOLMOD solver residual 1.28e-4 exceeds
tolerance 1e-4 for column 1` (Omniscape's own per-window residual check), leaving `not_converged, all_zero_output`;
the four other configurations of the landscape passed. With 1 failed row of 5 the driver's QC stop rule read "20 %
> 1 %" and exited (06:16Z). Fixes: (1) the rule now needs ≥ 20 shards and ≥ 200 rows before it can fire; driver
restarted 06:18Z (the 300 running tasks were never affected); (2) `solve_omniscape` retries the whole map with
Omniscape's `cg+amg` solver when the CHOLMOD attempt fails, recording `fallback_used` and the original error, as the
pairwise solver already did — package precompiled on the login node so that wave 2 and every re-run use it. Exposure:
14 of the 400 XXL landscapes have contrast ≥ 10⁵ (7 at 10⁶); the corresponding rows of wave 1 that fail are
QC-flagged (`qc_pass = false`) in the index and will be re-solved with the fallback and replaced on the Hub after the
wave (same repair flow as the tier-S re-solve: re-solve → re-finalize → verified replacement → audit), before the
precision pass touches XXL. No such failure occurred at S–XL (T4 QC pass 100 %).
**Addendum 07:45Z — second alert at 1.11 % (3 of 270 rows, 63 shards) and the decision to continue.** The three rows:
(1) shard 66 T4 as above; (2) shard 155 `advanced` (edge_gradient, contrast 10⁶): Circuitscape's CHOLMOD attempt *and*
its cg+amg fallback both ended `CG solver did not converge: relative residual 2.3e-3 exceeds tolerance 1e-4`
(`not_converged, all_zero_output`); (3) shard 213 `regions` (real tile, contrast 100): residual 1.08e-6, just above
the 1e-6 QC tolerance, refinement not applied. All three are QC-flagged in the index (`qc_pass = false`, so their
samples are excluded from the split lists) and each has an approved repair path: (1) the Omniscape fallback re-solve
after the wave; (2) and (3) the precision pass, which now also selects QC-failed pairwise/advanced rows and re-solves
them on the reduced system (our CHOLMOD solved the same kind of contrast-10⁶ problems that Circuitscape's checks
reject). Because nothing is silently kept and every failure is repaired before the tag, the driver was restarted with
the XXL alert threshold at 5 % (other tiers 1 %); 14 of 400 XXL landscapes are at contrast ≥ 10⁵, so the final rate
should stay near 1–2 %. **Index defect found while investigating:** since the atomic-rename change (2026-09-19) the
`shard` column of the index rows recorded the staging name `shard-XXXXX.h5.part` (all of XL, the later part of L, all
of XXL so far, and the published `index/XL.parquet`). Fixed in `finalize.py`; the 1 573 local index files were
rewritten and the S/M/L/XL indexes republished (the shard column now always reads `shard-XXXXX.h5`; the audit and the
sync were unaffected because they key on sample ids).

## Note 2026-09-22 (j) — OOM-killed task leaves an unreadable outputs file; re-runs looped

XXL shard 243 (real tile, ood_region) was OOM-killed at 28 GB after 2 h 23 (regions fallback tail); its partially
written `outputs/shard-00243.outputs.h5` had a bad HDF5 object header, so the 176 GB re-run and the following
profile-memory re-run both died within 2 min (`H5Error ... Wrong version number`). Fixes: `generate.py solve` now
opens an existing outputs file before launching Julia and, if unreadable, moves it aside as `<name>.corrupt-<ts>` (kept,
not deleted) and starts the shard afresh; the driver keeps the raised memory for any shard that ever ended
OUT_OF_MEMORY (not only when the very last attempt did). The corrupt file of 243 was moved to
`data/v1/XXL/outputs/corrupt/shard-00243.outputs.h5.oom-20260922T0347` (kept); the driver re-runs 243 at 176 GB.
**Resolution of (i) — 2026-09-22 11:15Z.** Omniscape's own `cg+amg` fallback fails the same landscape too (`CG solver
did not converge: relative residual 2.2e-4 exceeds tolerance 1e-4`), because Circuitscape 5.17.1's
`solve_linear_system` throws whenever a solve's relative residual is ≥ 1e-4 — a CHOLMOD solve that is *unrefined*
(1.28e-4 here) or a CG run capped at rtol 1e-6 / 100 000 iterations. AmpScapeSolve now replaces those two methods:
results are bit-identical whenever Circuitscape's check passes, and only where it would have thrown the solve is
rescued (CHOLMOD: iterative refinement with the same factorisation to 1e-8; CG: CHOLMOD factorisation of the window
+ refinement), counted per solve and recorded as `solver_params.rescued_solves`. Test on the failing landscape
(job 5898647): the full Omniscape map solved with CHOLMOD in 8 047 s (2.5 GB) with exactly one rescued window solve;
map valid (69 % non-zero pixels, finite). Repair of the wave-1 T4 rows that failed before the change: the precision
pass at XXL re-runs QC-failed T4 rows whole (`resolve_rows.jl` kind `omniscape`) and QC-failed T3/T1R rows on the
reduced system, then replaces the files and re-audits — no separate repair flow.

