# Status — 2026-09-23 20:45Z (precision pass complete on all tiers; v1.0 data ready for the tag)

- **Precision pass done (owner 2026-09-21, parts 1 and 2):** 129 722 T1/T1W/T1R/T3 rows re-solved in place on the Hub
  (S 68 008, M 37 639, L 18 691, XL 4 774, XXL 610) with reduced-system CHOLMOD + refinement; every such row now carries its
  true residual (0 unmeasured rows left); 189 former `cg+amg` rows are now `cholmod` with `solver_original` kept; 3 861
  rows sit at the double-precision floor above 1e-9 (recorded); **20 rows above 1e-6** (all synthetic at contrast
  ≥ 10⁴) are flagged `residual_high`, `qc_pass = false`, and their samples are excluded from the split lists; the two
  incident-(i) XXL rows are repaired. Per-tier table: `docs/tables/precision_pass.md`; datasheet section added.
- **Audits:** S, M, L, XL, XXL all clean after the pass; indexes and split lists republished once (final).
- **Cost:** ≈ 245 CPU-h of solves; generation + pass ≈ 15 500 core-hours of the 30 000 gate. Hub data ≈ 1.16 TB.
- **Operational notes:** Hub commit limit (128/h) → batched uploads; cluster `MaxSubmitPU` now 50 → work-queue workers;
  XL/XXL real-tile rows need 48–128 GB per worker; Circuitscape solve rescue installed at load time (precompile-safe).
- **Next (owner):** v1.0 tag; WP4/WP6/WP7 and the learned baselines await the GPU allocation.
