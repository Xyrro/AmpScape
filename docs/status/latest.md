# Status — 2026-09-17 (tier S complete and audited; driver running M)

- **Tier S complete**: 500 / 500 shards (100 000 landscapes, 522 629 configuration rows) validated with the full integrity check
  (planned sample ids and configurations, manifest count, Hub sha256) and on the public `Xirro/AmpScape`; **full audit clean**
  (500 shards, 2 500 Hub files, 0 discrepancies); the 72 repaired shards replaced their Hub copies (same paths, new checksums,
  72 / 72 confirmed). QC fail rate 0.000 %. Core-hours 2 061 (incl. the repairs). GB on Hub (`data/S/`) 142. Upload rate
  after the sync fix ≈ 125 shards/h.
- Incidents (a) quota, (b) partial finalize, (c) double submission — all in `docs/status/generation_log.md`, each with its
  structural fix (one-commit uploads + intermediate cleanup; solver completion marker + full-integrity validation;
  submit guard against queued/running tasks). The published index carries `skipped_configs` with reasons per sample.
- **Driver restarted**: M → L → XL → XXL in waves per the runbook, with a full audit required at every tier boundary.
- Phase 11 delivered; CI green.
