# Status — 2026-09-21 (tier L complete and audited; XL held for a core-hour budget decision)

## Tier L boundary

| item | value |
|---|---|
| shards validated, uploaded, audited | 1 000 of 1 000 (20 000 landscapes, 105 949 index rows) |
| full Hub-vs-plan audit | clean (0 discrepancies, 4 958 files: 4 000 T1/T1W/T3/T4 + 958 T1R) |
| QC fail rate | 0.013 % |
| GB on Hub | L 380.5 (S 142.2, M 251.5; total 774) |
| upload window | 09-19 03:23Z → 09-21 01:12Z (45.8 h), ≈ 21 shards/h |
| L core-hours (ampscape-L tasks) | 5 713 (runbook estimate 3 300; includes 569 in timed-out tasks and the idle second core of waves 1–4) |
| core-hours since 09-15, all ampscape-* jobs | 10 273 (production 9 466 + approved aux work 805) |
| scratch | 0 GB of L left locally; ≈ 190 GB total |

L per-landscape solve time, measured on the 662 completed single-core tasks: median 4.48 h per 20-landscape shard
(806 s per landscape), p99 5.26 h, max 5.48 h — the 9-h walltime held with no timeouts after the tail rule.

The first L audit flagged 41 shards; all were one false positive (the audit demanded a `T1R` file for shards whose every
`regions` sample was legitimately skipped — generation log (g2)); fixed in `audit_tier.py`, re-audit clean, no data
changed. The `regions` skip rate is ≈ 50 % of the planned samples at both M and L (labelled in `skipped_configs`).

## XL held — the budget cannot cover XL + XXL as planned (owner decision needed)

The runbook's per-tier table (§1) counted XL and XXL in *single-core* hours (2 150 + 1 200) while the cluster profile
allocates 4 cpus per XL task and 8 per XXL task for memory (`configs/cluster/ice.yaml`); Slurm accounting charges the
allocated cpus, so the table under-counted those tiers by 4× and 8×. With 10 273 core-hours used, 2 727 remain of the
13 000 budget.

Estimates from the measured L time (806 s per landscape, single core) scaled by the Phase-5 T4 ratio (L→XL 3.3×,
XL→XXL 5×):

| option | XL (4 000) | XXL (400) | total run | vs 13 000 |
|---|---|---|---|---|
| A. profile as is (4 / 8 cpus, no speedup) | ≈ 12 000–15 600 | ≈ 9 400–12 400 | ≈ 32 000–38 000 | 2.5–3× over |
| B. 1 cpu per task, memory-only allocation (`-c1 --mem 16G/20G`, allowed: no MaxMemPerCPU on coc-cpu) | ≈ 3 000–3 900 | ≈ 1 200–1 550 | ≈ 14 500–15 800 | +11–22 % |
| C. B plus the brief's original counts (XL 2 000, XXL 200; prefix streams make this a clean prefix of the v1.0 design) | ≈ 1 500–2 000 | ≈ 600–800 | ≈ 12 400–13 100 | within budget |
| D. multi-core allocation if CHOLMOD/BLAS speed-up is near-linear (unmeasured) | between A and B | | | |

Walltimes at 1 cpu stay within the 10-h profile (XL 6 landscapes × ≈ 2 700–3 300 s × tail 1.8; XXL 1 landscape).
The solver hands the allocated cores to BLAS/CHOLMOD (`solve_shard.sbatch`), so option D is possible only if the
speed-up is measured. **Action taken:** the driver was stopped before any XL submission (planning ran as a Slurm job;
the XL manifest exists). A 4-shard probe (2 shards at 1 cpu, 2 at 4 cpus, ≈ 60 core-h) measures the real XL
per-landscape time and the thread speed-up so the decision rests on numbers; results in `docs/status/generation_log.md`
when the probe finishes (≈ 6–8 h).

**Recommendation:** option B (1 cpu everywhere, full counts): the walltimes hold, XL/XXL remain test-only tiers of the
frozen design, and the overrun is 11–22 % of the budget (≈ 1 500–2 800 core-hours); if the probe shows a ≥ 2×
speed-up at 4 cpus, use it for XXL only (the largest single solves), otherwise 1 cpu throughout.

## Also delivered today
WP1/WP2 at L (60-sample block-1 reference, block-size Pareto rows) — see the 2026-09-20 entry.
