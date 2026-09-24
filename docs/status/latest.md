# Status — 2026-09-24 23:15Z: Phase 10-full — headline S/M/L T1 in, L/T4 running; XL/XXL rows by scale transfer

## Headline rel-L2 on test_id (seed 1, 30 epochs, official configs)

| task | S | M | L |
|---|---|---|---|
| T1 U-Net | 0.111 | 0.238 | 0.392 |
| T1 FNO | 0.198 | 0.266 | 0.364 |
| T1 ViT | 0.238 | 0.238 | 0.644 (structural, see DECISIONS) |
| T4 U-Net | 0.040 | 0.051 | staging |
| T4 FNO | 0.070 | 0.079 | staging |
| T4 ViT | 0.071 | 0.099 | staging |

- T1 error grows with tier for both U-Net and FNO (S → L: ×3.5 and ×1.8). Two effects are confounded in the
  official configs: larger landscapes (longer-range flow) and a smaller fixed-epoch training set (100 k / 30.7 k /
  12.3 k landscapes at S / M / L, 30 epochs each; U-Net L trains in 1.5 GPU-h and its validation loss is still
  falling at epoch 30). WP4 (data-scaling at S, running) and the fixed-step variants separate these; a longer-epoch
  L run is a candidate addition once the plan is through.
- T4 at M against the exact block-1 map (test_id): U-Net 0.051 at 1 ms/landscape, FNO 0.079 at 1.5 ms; the
  production block-3 solver is 0.029 at 111 s, block 7 with artifact correction 0.098 at 25 s
  (`runs/full/<run>/eval_t4_reference/results.md`, backfilled by CPU jobs where the training job skipped it).
- 53 of 132 runs finished; 4 legs queued or running. Running table: `docs/tables/baselines_full.md`.

## Schedule change (22:40Z): XL and XXL rows by scale transfer
- XL is a held-out-scale tier (card; 228 train / 0 val landscapes): the first XL training legs were degenerate and
  their single-process metrics at 1024² exceeded a 2-h leg. All XL training was cancelled; every L-trained run is
  instead evaluated at XL and XXL (`scripts/transfer_eval.py`, 42 jobs ≈ 66 GPU-h, after P3 / after the GNNs).
  Plan now 144 jobs ≈ 933 GPU-h. Harness metrics run in parallel processes (identical results, verified).
- Owner items done: tile rasters deleted (scratch 285 → 251 GB); T4-at-S finding recorded; ViT L checked (no
  divergence, resolution-inappropriate official config) — all in DECISIONS.md.

## Operation
- Fixed today: the in-job T4 reference evaluation looked for predictions under the wrong path and the M reference
  was not local — path fixed in the job template, M reference fetched, and the driver backfills any finished T4 M/L
  run with a CPU job (≈ 9 min at M). Driver: strict-priority tier-major staging, draining, eviction protection,
  scratch guard 280 GB, GNN strictly last (one early GNN job cancelled at start).
- Storage-bound at L: with ≈ 130 GB of scratch outside the training cache, L/T1 (84 GB) and L/T4 (82 GB) cannot
  be staged together. L/T4 waits for the last L/T1 legs (ViT seeds, ≈ 1–2 h), during which only 4 of 18 GPU slots
  are used. XL groups (61 + 61 GB) fit together.

Next: L/T4 and L/T3 finish → transfer evaluations at XL/XXL → GNN (S, M, L) → GNN transfers; WP7 demo as soon as the best T4 model at L is known.
