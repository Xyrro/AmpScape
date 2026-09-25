# Status — 2026-09-25 22:45Z: owner checks 1–3 answered; scale-aware variant queued; transfer phase running again after a 12-h hold

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
  note that the XL Omniscape target uses a window twice as large (radius 128 vs 64 at L; block 11 vs 5), so T4
  transfer is transfer across operators as well as scales (verified on every XL/XXL row, see check 1). Both are benchmark findings, reported as measured (official protocol,
  no re-calibration). The transfer script was cross-checked on training-tier data where possible; the pattern is
  consistent across seeds and models.
- Remaining splits (test_ood, ood_region) and XXL follow as the transfer jobs run.

## Owner checks (2026-09-25)

**1. Omniscape geometry, read from the data** (`solver_stats.solver_params` on every T4 output group on the Hub, staged
copies): XL — all 4,000 rows `block_size 11, radius 128`; XXL — all 400 rows `block_size 25, radius 256`; L (the 100
WP7 v1 rows as a spot check) `block_size 5, radius 64`; all `solver cholmod`, `correct_artifacts true`,
`fallback_used false`. The adopted rule block ≤ radius/10 holds (XL 11 ≤ 12.8, XXL 25 ≤ 25.6); the card's fidelity
statement is correct and no target needs regenerating. (My 10:00Z note quoting "block 33" came from an early
DECISIONS row about the *cost probe*, not from the data; corrected above.)

**2. XL train/val vs amendment C3.** C3 is implemented in `ampscape/splits/assign.py` as: apply the base split
(train 0.8 / val 0.1 / test_id 0.1 by seed family), then keep an XL landscape in train/val only if
`stable_unit(f"{block_id}|{seed}") < 0.25`. `block_id` exists only for real tiles (macro-cell of the tile); synthetic
landscapes carry `block_id = None`, and `stable_unit("None|20260906") = 0.348 ≥ 0.25`, so **every synthetic XL
train/val landscape (2,165 of 2,400) was moved to test_id**, and of the real tiles only the 25 % of macro-cells that
hash below the share kept their rows: 228 train, and the real val cells all hashed out (val = 0). Result: XL train
228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 instead of ≈ 1,000 train+val. XXL is test-only by design
(unchanged). Nothing in the v1.0 *data* is affected; the released model results are unaffected too (nothing was
trained at XL; the XL/XXL rows are zero-shot transfers evaluated on test_id).

*Proposed metadata fix (1.0.2, index `split` column + `splits/full/*.parquet` + Croissant; data revision unchanged):*
for synthetic XL landscapes apply the C3 share per seed family, `stable_unit(f"{seed_family}|{seed}|xl") < share`,
with share = 0.278 so that synthetic train+val ≈ 600 (25 % of the 2,400 synthetic landscapes; simulated with 0.25:
470 train / 77 val); for real tiles keep the macro-cell rule but draw val cells among the kept cells at the base
10 % ratio (today 0). Expected XL: ≈ 830–1,000 train+val (≈ 21–25 %), test_id ≈ 2,300 (still ≥ 5× the XXL test).
Consequences: the transfer rows on XL test_id are re-aggregated from the stored per-sample metrics (no recompute);
mini/lite/core are unaffected (XL is full-only); the datasheet split table and the card's XL sentence change.
Not applied — awaiting your go-ahead.

**3. Scale-aware target variant** (`--target-norm scale`, `ampscape.models.common.target_scale`; documented in the
code): T1/T3 target = log10(k·C + ε·max) with k = sqrt(N_valid / 512²) — under a uniform rescaling by s per axis
with the same injected current (T1's injection does not change with tier by construction) current per pixel column
∝ 1/s and N_valid ∝ s²; T4: k = 64 / r_tier — Omniscape currents accumulate ∝ r·s̄ (window injects ∝ r²·s̄, spreads
over ∝ r, a pixel sits in ∝ (r/b)² windows with b ≈ r/10), which is exactly the ×2 seen at XL. k is computed from the
inputs / the evaluation tier only; the prediction is divided by k before the harness, so metrics stay in absolute
current units and no XL/XXL data enters the training or the inverse. At L the variant's target equals the official
one numerically (k = 1 at 512², r = 64), so any difference is the transfer.
Runs: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4 (official configs otherwise), then the same
zero-shot XL/XXL transfer (tags SN/SNX, after the current transfer phase); GNN variant after the GNN phase (SN4/SNX4).
*GPU cost estimate* (measured L seed-1 times): training 17.5 GPU-h (U-Net 1.5+1.6, FNO 2.7+2.8, ViT 4.4+4.6) +
evaluation legs ≈ 4.5 + transfers ≈ 7.5 (XL 6 × ≈ 0.6 h, XXL 4 × ≈ 1 h) ≈ **30 GPU-h**; GNN variant ≈ 15–35 GPU-h
more (its official L runs are not measured yet). Smoke-tested on the mini build before queueing.

## Incident 10:00Z–22:35Z: transfer phase silently held for 12 h
- After the quota recovery the driver refused transfer legs while scratch was above the 255 GB threshold, but the
  four staged XL/XXL groups (166 GB) plus the floor kept scratch at 272 GB, nothing triggered an eviction, and the
  hold was silent. Fix (22:35Z): when transfer legs are held by scratch the driver evicts staged groups whose next
  use is later than the first runnable transfer; the hold is logged; transfer jobs are ordered task-major (T1 then
  T4) so only one task's XL/XXL groups need to stay staged; the threshold is 245 GB with 4 legs in flight. The
  first XL T1 legs went out at 22:35Z. Plan: 166 jobs ≈ 1,081 GPU-h nominal (the scale-aware variants added 46 nominal;
  measured rates are 3–7× lower).

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

Next: transfer evaluations at XL/XXL → scale-aware variants at L + their transfers → GNN (S, M, L) → GNN transfers and variant; weekly report or on schedule changes.
