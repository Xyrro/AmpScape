# Status — 2026-09-20 (L block-1 reference and L Pareto rows delivered; L final wave running)

- **Addendum WP1 at L (`docs/addendum_WP1_report.md` §6)**: the 60-sample L block-1 reference is complete (20 synthetic +
  40 real tiles over test_id / test_ood / ood_region). Production block 5 deviates from the exact map by 0.028 rel-L2 mean
  (test_id 0.032, test_ood 0.020, ood_region 0.028; max 0.058), non-source 0.033, top-5 % IoU 0.93, pinch recall 0.94;
  2 of 60 flagged above 5 % (both synthetic; no real tile). Block 1 at L costs 22× production (3.7 CPU-h per landscape,
  ≈ 225 CPU-h in total). Index with `tail_gt5pct` and summary published on the Hub under `aux/t4_bs1_reference/L/`; it is
  the L T4 evaluation surface (`evaluate.py --t4-reference aux/t4_bs1_reference/L_bs1`).
- **Addendum WP2 at L (`docs/addendum_WP2_report.md`, `docs/tables/t4_pareto_L.md`, `docs/figures/t4_pareto_L.png`)**: block
  3 / production 5 / 11 and 5-without-correction on the same 60 samples. Block 3 and block 5 are within 0.2–0.4 points of
  rel-L2 of each other at 2.5–2.9× the cost; block 11 loses 4–6 points for a 3.6× saving; the artefact correction is worth
  3–5× in rel-L2 at zero cost. The production block is the knee of the front at L as at M. Rows published under
  `aux/t4_blocksize_baselines/L/` on the Hub.
- **Tooling**: `aux_t4_blocks.py compare` looks a sample's inputs up across all inputs files (top-up re-chunking broke the
  first full run), writes the tail flag itself, and skips unreadable Hub samples with a warning.
- **Generation**: L 900 of 1 000 shards validated and on the Hub (QC fail 0.017 %), final wave 900–999 running since
  18:43Z (9-h walltime), scratch 193 GB, ≈ 9 300 core-hours, no alert, driver (lease on gnr-1) and L sync loop (gnr-2)
  alive. After the wave: driver audit gate → L tier-boundary report → XL planned and submitted automatically.
- **Pending**: learned-model rows for the Pareto tables and the probe-set evaluation (GPU allocation); WP4/6/7.
