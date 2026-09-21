# Status — 2026-09-21 08:30Z (XL launched at 1 cpu, 300 concurrent; parallel uploaders; aux publication running)

- **Owner decisions applied**: full counts, 30 000 core-hour gate, wall-clock optimisation, 4 parallel uploaders, waves
  300 (after the approved clean-up: quicklooks deleted, task logs archived 12 GB → 0.4 GB, superseded pilot builds
  removed; scratch 146 GB → settling to ≈ 95 GB).
- **XL probe → 1 cpu per task**: per landscape 1 500–4 030 s at both 1 and 4 cpus (means ≈ 2 400 vs ≈ 2 500 s;
  Omniscape/CHOLMOD 95 % of the time, no BLAS gain), so the ≥ 1.5× rule selects 1 cpu; XXL likewise 1 cpu (16 GB;
  20 GB for test shards). Estimated cost XL ≈ 2 800, XXL ≈ 1 150 core-hours (total run ≈ 14 500).
- **XL running**: wave 0–299 submitted 08:24Z (job 5882104), all 300 tasks running at once (cluster 418/1 384 cores
  busy); 4 sync workers `XL_w0..3` under leases; XXL pre-planned (job 5882430) so the boundary loses no time.
- **Completion estimate**: XL wave 2 ≈ 13–14Z, wave 3 (67 shards) ≈ 19Z, XL audited ≈ 2026-09-22 03Z; XXL (400 shards,
  2 waves of ≈ 3–5 h) ≈ 2026-09-22 14–16Z. Upload rate after (4 workers) reported when wave 1 lands.
- **Slip and fix**: `data/builds/published` (the 46-sample `test_ood_published` set, local-only) was deleted with the pilot
  builds before its reference check was read; regenerated identically (ids verified, QC 100 %) and, per the new owner
  rule, being published under `aux/test_ood_published/` together with every other scratch-only evaluation asset
  (`aux/dev/{S,M}`, `aux/mini`, `aux/scale_probe/`, `aux/t4_bs1_reference/{M,L}` full builds,
  `aux/t4_blocksize_baselines/{M,L}/*`, `aux/results/{predictions,runs_dev,runs_tune}`; ≈ 20 GB, `scripts/push_aux.py`,
  sha256-verified, log `logs/push_aux.log`). **No further deletions without listing exact paths first.**
- Not pushed (results of throwaway runs, listed for the owner): `runs/calib` (60 MB), `runs/smoke` (121 MB).
