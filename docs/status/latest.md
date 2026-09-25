# Status — 2026-09-25 10:00Z: Phase 10-full — S/M/L headline done, WP7 done; scale transfer running after a scratch-quota incident

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.533 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | 0.080 |
| T4 FNO | 0.070 | 0.079 | 0.120 |
| T4 ViT | 0.071 | 0.099 | running |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 against the exact block-1 map (test_id): at M U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms vs the
  production block-3 solver 0.029 at 111 s and block 7 with artifact correction 0.098 at 25 s; at L U-Net 0.080 at
  5 ms, FNO 0.120 at 7 ms vs production block 5 at 0.032 and 566 s. U-Net T4 L seeds 1–3: 0.080 / 0.082 / 0.081
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 70 of 144 jobs finished (training runs); L/T3 running, transfer evaluations and GNN next. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Scale transfer (L-trained models at XL, first rows; `<run>/results_transfer.json`)

| trained at L → XL, test_id | rel-L2 | throughput error | Spearman | top-5 % IoU |
|---|---|---|---|---|
| T1 U-Net (s1 / s3) | 1.70 / 1.03 | 0.94 / 0.93 | 0.70 / 0.74 | 0.42 |
| T1 FNO (s1 / s3) | 0.75 / 0.74 | 0.62 / 0.71 | 0.93 / 0.92 | 0.56 |
| T1 ViT (s3) | 0.77 | 0.53 | 0.66 | 0.14 |
| T4 U-Net / FNO / ViT (s1) | 0.51 / 0.53 / 0.54 | — | 0.94 / 0.95 / 0.93 | 0.60 / 0.66 / 0.56 |

- Zero-shot scale transfer of the official baselines fails on magnitude and partly survives on ranking: T1 predictions
  at XL carry the wrong total current (throughput error 0.5–0.9; the target is absolute log-current and the injected
  current per pixel changes with landscape size), while FNO keeps the pixel ranking (Spearman 0.93). For T4 the
  three models agree at rel-L2 ≈ 0.5 with Spearman ≥ 0.93 — consistent with a near-constant magnitude factor, and
  note that the XL Omniscape target uses a different window geometry (block 33 vs block 9 at L), so T4 transfer is
  transfer across operators as well as scales. Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Incident 09:09Z: scratch quota reached (300 GB)
- Nine concurrent XL transfer legs each wrote up to 13 GB of predictions (FNO at 1024²) before their metrics ran;
  the 280 GB guard only governs staging. Effects: transfer legs died on write errors (resumable, no metrics lost),
  the offloader could not push (the Hub client needs local temp space), one config file was caught mid-rewrite.
- Fixes (committed): transfer legs drop predictions after their metrics except seed-1 test_id; the offloader pushes
  per split; ≤ 2 transfer legs in flight below 265 GB (4 once the quota breathes); robust JSON reads. To recover
  I deleted transfer predictions whose metrics were already stored (seed 2/3, 19 GB — exactly what the new policy
  drops) and incomplete prediction files of the killed legs (15 GB, no metrics, re-predicted on resume); paths are in
  the session log. Scratch 300 → 220 GB; driver and offloader restarted 09:42Z.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

## WP7 many-query demonstration — done (`docs/wp7_demo.md`, `aux/wp7/demo_summary.md` on the Hub)
U-Net T4 L seed 1 on 20 held-out real L tiles × 8 tables (160 maps): the surrogate reproduces the study-level
conclusions of the solver — top-5 % stability across tables 0.458 vs 0.463 (IoU matrices differ by 0.019), consensus
core IoU 0.825, table-effect ranking Spearman 0.991 with the same most-influential table on every tile, persistent
pinch-point recall 0.94 (precision 0.66 at 3 px); per-map rel-L2 0.054 mean, 0.100 worst table. Cost: 36.3 CPU-h for
the solver route vs 11.8 s on one GPU (≈ ×11,000 after training once).

Next: L/T3 finishes → transfer evaluations at XL/XXL → GNN (S, M, L) → GNN transfers; weekly report or on schedule changes.
