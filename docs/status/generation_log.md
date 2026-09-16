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
