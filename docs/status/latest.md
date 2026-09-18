# Status — 2026-09-19 (tiers S and M complete and audited; L running; addendum WP1/WP2 in progress)

- **Tier M complete**: 500 / 500 shards (50 000 landscapes) validated, uploaded and **audited clean** (full Hub-vs-plan audit
  gate in the driver); QC fail rate 0.002 % (one contrast-10⁶ configuration at the residual threshold); 251.5 GB on the Hub
  for M (394 GB total with S). One shard (434) needed a re-finalize after a write race between two finalize jobs; the driver
  now alerts on `.invalid` shards and re-finalizes solved-but-unfinalized shards itself.
- **Tier L started** (1 000 shards of 20, waves of 100, prepare-ahead one wave). Generation core-hours so far ≈ 3 850.
- **Addendum**: WP3 done; WP5 analysis done (probe design + ≈ 60 CPU-h estimate awaiting confirmation); WP1 part 1 done and the
  owner decision implemented (block-1 reference = official T4 surface at M/L, `--t4-reference` in the harness, tail flag,
  docs); the M reference is being grown to 1 000 samples (800 block-1 solves queued) and the three WP2 block-size builds
  (block 3 without artefact correction, block 7 with/without) are queued on the same samples; ICE changed the default QoS
  (explicit `coc-ice` now required — fixed in the profile after two silent submission failures).
