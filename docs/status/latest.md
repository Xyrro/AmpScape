# Status — 2026-09-16 (tier S generation running; quota incident fixed)

- **Tier S**: 500 / 500 shards solved, finalized and validated (QC fail 0.000 %); **153 uploaded and verified** on the public
  `Xirro/AmpScape` at 16:46Z (50th shard at 16:00Z), 347 finals waiting; upload rate ≈ 125 shards/h after the fix
  (one Hub commit per shard) → S fully on the Hub in ≈ 3 h. Core-hours used: 1 686 (solves + prepare + finalize +
  re-finalize). GB on Hub (`data/S/`): 30.4. Scratch: 199 GB of 300 (was 300/300).
- **Incident**: all 500 S shards ran at once; finalize ran in a separate array; the sync deleted only the final after
  upload, so raw intermediates (≈ 245 MB/shard) + finals (≈ 130 MB/shard) filled the 300 GB quota at 11:26Z; the split
  of shard 12 was truncated and retried every 15 min; 149 finals written after that point were truncated too.
- **Fixes (owner items 1–5)**: partial staging files removed; 83.6 GB of raw inputs/outputs of validated shards deleted,
  the 149 truncated finals deleted and re-finalized from their intact outputs (10 Slurm tasks, 0 QC failures);
  sync rewritten (per-shard temporary split always removed, one commit per shard, sha256 verified per file, attempt
  counter with `.upload_failed` after two consecutive failures, unreadable finals marked `.invalid` and skipped);
  finalize deletes raw intermediates after a validated write (inside the array task for all further tiers);
  generation log fixed (solved count from finals/markers, GB on Hub from the Hub listing, concurrent-deletion safe);
  scratch budget and wave sizes in `docs/generation_runbook.md` §5 (M: waves of 80 shards, submit the next wave only
  when the upload backlog is below one wave and `data/` < 200 GB).
- Next: M is **not** submitted until the S backlog is uploaded (rule 2); Phase 11 (docs, notebooks, CI, datasheet) starts now.
