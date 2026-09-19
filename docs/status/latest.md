# Status — 2026-09-19 (WP1 + WP2 delivered; L generating; supervisor incident closed)

- **Addendum WP1 (`docs/addendum_WP1_report.md`)**: 1 000-sample block-1 reference at M (official T4 evaluation surface):
  production block 3 deviates from exact by 0.029 rel-L2 mean (median 0.027), 4.7 % of samples above 5 % (11 % of
  synthetic, 1.4 % of real), top-5 % IoU 0.93, pinch recall 0.93; per-sample index with the tail flag published under
  `aux/t4_bs1_reference/M/` on the Hub; `evaluate.py --t4-reference`.
- **Addendum WP2 (`docs/addendum_WP2_report.md`, `docs/tables/t4_pareto_M.md`, `docs/figures/t4_pareto_M.png`)**: block-size
  Pareto at M — the artefact correction is worth 4× in rel-L2 at no cost (block 3: 0.029 vs 0.111 without); block 7 with
  correction 0.098 at 25 s; block-size error is nearly split-independent; `evaluate.py --t4-blocks` prints block rows beside
  a model. L rows and learned-model rows pending (L production; GPU allocation). **Stopped for confirmation.**
- **CI**: green again from `849ca68` (unused locals and lambdas fixed); commits touching only `docs/status`, `docs/tables`,
  `docs/figures`, `DECISIONS.md` or `CHANGELOG.md` no longer trigger CI.
- **Approved work in flight**: L block-1 reference (first 20 samples solving; topped up as L real shards land), WP5 probe set
  (60 real L tiles × 4 cells + 60 synthetic seeds × 2 sizes = 360 samples solving under `aux/scale_probe/probe_L`).
- **Root cause of the corrupted finals (M 434, L 189) found and fixed**: the sync loop validated finals while finalize was still
  writing them; finalize now renames atomically and the sync skips in-progress files (verified clean on wave 3 of L). The
  driver also no longer counts aux arrays as tier work (that had stalled waves behind the block-size studies).
- **L block-1 reference**: first 20 samples solving (block 1 at L ≈ 4–5 h per sample; resumable resubmission chained); the
  block-3 / block-11 / block-5-without-correction rows at L are queued on the same samples.
- **Generation**: S and M complete and audited; L wave 2 of 10 running (87 of 1 000 shards on the Hub), scratch 180 GB,
  ≈ 5 100 core-hours. Incident (d): a session restart on another login node started duplicate supervisors; caught in
  10 min, no double submission, cross-host leases added (`logs/lease_*.json`); the driver is being restarted under the
  lease protocol; the S/M/L sync loops from the previous session keep running on `login-ice-gnr-2`.
