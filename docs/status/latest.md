# Status — 2026-09-23 (v1.0 tagged; stopping — everything after this is GPU work)

- Card finalised (in-progress notice removed; final counts, sizes, core-hours, incident and precision-pass summaries).
- Croissant regenerated from the final indexes and validated with mlcroissant (30 distributions, 5 record sets, 0
  errors); core subset 115.5 GB (3 705 files), mini 0.61 GB, full 1 157.4 GB; any tier or task group downloads alone
  (verified: `data/XXL/T1R/*` alone, self-contained inputs + outputs).
- Statistics figures and table: `docs/figures/dataset_stats_*.png`, `docs/tables/dataset_statistics.md` (contrast,
  biome/realm, NoData fraction, solve-time distributions, per-tier storage); also under `aux/` on the Hub.
- `docs/generation_postmortem.md`: timeline, all incidents with root causes and fixes, final cost (16 552 core-hours),
  runbook changes for reproduction.
- Tags: GitHub `v1.0`, Hub revision `v1.0`; `CITATION.cff` 1.0.0 (2026-09-23); recorded in DECISIONS.
