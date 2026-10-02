# Baselines and protocol

*Draft section. Every number is copied from a repository file and tagged with its source; facts absent from the documentation are marked `[TODO: not in docs]`. Tags pointing at code constants rather than docstrings or tables are flagged "(code)".*

## Baseline models and official configurations

All learned baselines share one input stack and one target. Inputs: channel 0 = standardised log-resistance (train-only mean/std, 0 at NoData), channel 1 = NoData mask, then the task's source channels — T1: focal mask (any label); T3: source strength scaled by the number of valid pixels plus the ground mask; T4: Omniscape source strength (max 1) [ampscape/models/common.py module docstring]. An optional extra channel, the Euclidean distance to the nearest source/focal pixel divided by max(H, W), was offered to every model in the tuning pass as a global cue for local architectures [ampscape/models/common.py `distance_channel` docstring]. The target is log10(C + ε·max C) per map, predicted directly, with a masked MSE that excludes NoData and the T1W strips [ampscape/models/common.py docstrings]; ε = 1e-6, chosen over log1p because the ε-shifted log is scale-invariant and bounds the dynamic range to 6 decades below the map maximum [ampscape/metrics/transforms.py docstring].

- **U-Net** — 4-level encoder–decoder, GroupNorm + GELU [ampscape/models/unet.py docstring]; official config `base` (width 32, 4 levels), no extra channel: the wide variant was within single-seed noise (+3 % at 2.2× the parameters) and the distance channel hurt [ampscape/models/__init__.py `OFFICIAL` comment (code)]. 7.766 M parameters [docs/tables/baselines_full.md].
- **FNO** — 2-D Fourier Neural Operator, resolution-agnostic; the number of retained modes is the only spatial hyper-parameter [ampscape/models/fno.py docstring]. Official config `m64` (width 32, 64 modes, 4 layers) plus the distance channel — the only configuration in which FNO recovered on T1 (dev rel-L2 1.14 → 0.34) [ampscape/models/__init__.py (code)]. 33.563 M parameters [docs/tables/baselines_full.md]. FNO trains in fp32 (complex spectral weights); the others use bf16 autocast [DECISIONS.md 2026-09-14].
- **ViT** — patch-4 convolutional embedding, pre-norm blocks with global attention, learned positional embedding bilinearly interpolated to other grid sizes, convolutional decoder with a full-resolution skip [ampscape/models/vit.py docstring]. Official config: patch 4, dim 192, depth 6, learned 32×32 positional embedding, fixed across tiers (at L: interpolated to 128×128, global attention over 16,384 tokens) [DECISIONS.md 2026-09-24]; patch 2 and the distance channel did not help [ampscape/models/__init__.py (code)]. 3.025 M parameters [docs/tables/baselines_full.md].
- **GNN** — grid-as-graph: nodes = valid pixels, 8-neighbour edges weighted by Circuitscape's average-conductance rule, residual message passing on conductance-weighted neighbour differences; receptive field = number of hops [ampscape/models/gnn.py docstring]. Official config: the two-level `MultiScaleGridGNN` (message passing on a 4×-coarsened graph, scattered back and refined on the fine graph) [ampscape/models/gnn.py class docstring] plus the distance channel (dev T1 1.04 → 0.69, T4 0.17 → 0.15) [ampscape/models/__init__.py (code)]; 0.24 M parameters [docs/tables/gpu_budget_tuned.md].

The tuning pass that froze these configs ran on the dev subset within ≤ 6 GPU-h (FNO 32/64 modes, multi-scale GNN, one alternative each for U-Net and ViT, the distance channel for all) [DECISIONS.md 2026-09-14] and used 2.47 GPU-h over 16 runs [docs/tables/gpu_budget_tuned.md].

## Training protocol

Each run trains one model on one task at one tier for 30 epochs with AdamW, a cosine schedule, early stopping on the validation loss and a fixed seed [scripts/train.py docstring; epochs: docs/status/latest.md]; three seeds per (model, task, tier) [docs/phase10_full_schedule.md §2]. Patience is 8 epochs in production jobs [scripts/slurm/gpu/train_full.sbatch (code); script default 6]; learning rate 1e-3 for U-Net, FNO and GNN and 3e-4 for the ViT (AdamW defaults of the scripts) [scripts/train.py DEFAULT_LR]. Per-tier batch sizes: S 16 / M 8 / L 4, GNN 8 / 4 / 1 [scripts/slurm/gpu/gpu_driver.py `TIER_RES` (code); batch 4 at L confirmed for the ViT in DECISIONS.md 2026-09-24]. The fixed epoch budget meets training sets of 100 k / 30.7 k / 12.3 k landscapes at S / M / L [docs/status/latest.md].

Jobs run on PACE-ICE `coc-gpu` L40S nodes (bf16, 48 GB) with A100 spill-over, as 2-hour legs that checkpoint and re-queue themselves (`train.py --resume --pause-exit`), ≤ 18 concurrent, because the per-user cap is 1 920 GPU-minutes of remaining walltime [docs/phase10_full_schedule.md §1]. Normalisation statistics are train-only [ampscape/models/common.py docstring] and per tier: a model is always evaluated with the statistics of its training tier (`config.json`), including at transfer tiers [scripts/transfer_eval.py docstring]. Predictions (≈ 2.6 GB per finished S run) are offloaded to the Hub after sha256 verification [docs/phase10_full_schedule.md §4].

## Evaluation protocol

Every run is evaluated on `test_id`, `test_ood` and `ood_region`, and at S also on the published tiles [docs/phase10_full_schedule.md §2; `--published-tiers` default S, scripts/train.py]. Metrics: MAE in log10-ε space, rel-L2, top-5 % IoU, pinch-point recall, Spearman, corridor Dice, SSIM and median speed-up [docs/tables/baselines_full.md header].

**T4 at M and L.** Production targets are block-centred Omniscape maps; the block-1 (exact) reference subsets are the official T4 evaluation surface at M and L, block-centred metrics secondary [DECISIONS.md 2026-09-18]. The subsets hold 400 / 300 / 300 (test_id / test_ood / ood_region) landscapes at M and 24 / 16 / 20 at L; the same tables give the solver's own error-vs-cost rows — at M the production block-3 solver reaches rel-L2 0.0291 at 111 s per landscape, at L production block 5 reaches 0.0315 at 566 s versus 1.23e+04 s for block 1 [docs/tables/t4_pareto_M.md; docs/tables/t4_pareto_L.md].

**XL and XXL are zero-shot scale transfer, not training.** The card defines XL and XXL as held-out-scale tiers for models trained at ≤ L; their v1.0 splits held 228 (XL) and 0 (XXL) training landscapes and no validation split, so the first XL training legs were degenerate (`val_loss` 0, early stop at epoch 9) and single-process metrics at 1024² exceeded the 2-h leg. The nine XL training jobs were cancelled; nothing is trained at XL [docs/phase10_full_schedule.md §5; DECISIONS.md 2026-09-24]. Instead every L-trained run is evaluated at XL and XXL at batch 1 with the training tier's statistics (`scripts/transfer_eval.py`, 4-h resumable legs); XXL only for fully convolutional models (U-Net, FNO, GNN), since the ViT's interpolated positional embedding stops at XL [docs/phase10_full_schedule.md §5]. For T4 this is also transfer across operators: the XL target uses block 11 / radius 128 and XXL block 25 / radius 256 versus block 5 / radius 64 at L [docs/status/latest.md, check 1]. No re-calibration is applied [docs/status/latest.md].

## Scale-aware target variant

`--target-norm scale` replaces the absolute target by log10(k·C + ε·max) with a tier-computable k: for T1/T3, k = sqrt(N_valid / N_ref), N_ref = 512² (under a uniform rescaling by s per axis with the same injected current, current per pixel column scales as 1/s and the valid pixel count as s²); for T4, k = r_ref / r_tier with r_ref = 64, because Omniscape currents accumulate as C ∝ r·s̄ (each window injects ∝ r²·s̄ over ∝ r pixels and a pixel sits in ∝ (r/b)² windows with b ≈ r/10). Both factors depend only on the inputs and the evaluation tier; the inverse divides the prediction by k, so metrics stay in absolute current units [ampscape/models/common.py `target_scale` docstring]. At L the variant equals the official target numerically (k = 1), so any difference is the transfer [docs/status/latest.md, check 3]. Planned: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4, then the same zero-shot transfer; ≈ 30 GPU-h, plus 15–35 for the GNN variant; not started as of 2026-10-02 [docs/status/latest.md; DECISIONS.md 2026-09-25].

## Non-learned baselines

**Coarsen ×4**: geometric-mean resistance and majority NoData over f×f blocks, any-label focal pixels, block-summed (T3) or block-mean (T4) sources, a reference CHOLMOD solve on the coarse grid, bilinear upsampling (pairwise/advanced maps divided by f, coarse focal pixels in-filled, true focal pixels reset to 1 A); inference time = coarsening + solve + upsampling [ampscape/models/coarsen.py docstring; DECISIONS.md 2026-09-13]. **Block-size rows** (T4): Omniscape at larger blocks with and without artifact correction, timed per landscape against block 1 [docs/tables/t4_pareto_M.md; docs/tables/t4_pareto_L.md].

## Compute used so far

Dev runs: 1.44 GPU-h (10 runs) [docs/tables/gpu_budget.md] and 2.47 GPU-h (16 tuning runs) [docs/tables/gpu_budget_tuned.md]. Full-scale training per run (T1, seed 1): U-Net 0.862 / 1.199 / 1.486 GPU-h at S / M / L; FNO 0.953 / 1.627 / 2.696; ViT 0.814 / 1.538 / 4.437 [docs/tables/baselines_full.md] — 3–7× below the plan's 30-epoch estimates [docs/status/latest.md]. At 2026-10-02: all 84 training runs of P1–P3 and WP4 complete; 18 of 30 transfer legs done; nominal remaining 772 GPU-h (GNN 578), realistically ≈ 200–300; plan 166 jobs ≈ 1,081 GPU-h nominal [docs/status/latest.md]. 182.4 GPU-hours consumed by 216 GPU jobs up to 2026-10-02 (training, evaluation and transfer legs, WP7 demo; scale-aware variants and GNN pending) [docs/tables/gpu_usage.md]. WP7: 36.3 CPU-h for the solver route versus 11.8 s on one GPU for 160 maps [docs/wp7_demo.md].

## Skeleton results table — rel-L2 on test_id, seed 1, official configs

All values [docs/tables/baselines_full.md] unless noted. XL/XXL columns are zero-shot transfers of the L-trained seed-1 model.

| task | model | S | M | L | L → XL | L → XXL |
|---|---|---|---|---|---|---|
| T1 | coarsen ×4 (non-learned) | 0.464 | [pending] | [pending] | — | — |
| T1 | U-Net | 0.111 | 0.238 | 0.392 | 1.735 | 8.271 |
| T1 | FNO | 0.198 | 0.266 | 0.364 | 0.745 | 1.662 |
| T1 | ViT | 0.238 | 0.533 | 0.644 (structural, DECISIONS.md 2026-09-24) | 0.763 | n/a |
| T1 | GNN | [pending] | [pending] | [pending] | [pending] | [pending] |
| T1 | U-Net / FNO / ViT, scale-aware | — | — | [pending] | [pending] | [pending] |
| T3 | coarsen ×4 (non-learned) | 0.295 | [pending] | [pending] | — | — |
| T3 | U-Net | 0.116 | 0.202 | [pending] | [pending] | [pending] |
| T3 | FNO | 0.254 | 0.277 | [pending] | [pending] | [pending] |
| T4 | coarsen ×4 (non-learned) | 0.727 | [pending] | [pending] | — | — |
| T4 | U-Net | 0.040 | 0.051 † | 0.080 † | 0.513 | 0.749 |
| T4 | FNO | 0.051 | 0.079 † | 0.120 † | 0.533 | 0.765 |
| T4 | ViT | 0.052 | 0.099 † | [pending] (seed 2: 0.154) | 0.538 | n/a |
| T4 | GNN | [pending] | [pending] | [pending] | [pending] | [pending] |
| T4 | U-Net / FNO / ViT, scale-aware | — | — | [pending] | [pending] | [pending] |
| T4 | production solver (block 3 at M / block 5 at L) † | — | 0.0291 | 0.0315 | — | — |

† Against the exact block-1 reference subset (400 landscapes at M, 24 at L on test_id) [docs/status/latest.md; docs/tables/t4_pareto_M.md; docs/tables/t4_pareto_L.md]. XXL rows exist for seed 1 only; T4 XXL seeds 2–3 [pending]. Note: docs/status/latest.md lists T4 FNO S = 0.070 and ViT S = 0.071, whereas docs/tables/baselines_full.md gives 0.051 and 0.052 on test_id (its published-S rows are 0.069 / 0.071) — to be reconciled before submission.

## Sources used

- docs/tables/baselines_full.md
- docs/tables/t4_pareto_M.md
- docs/tables/t4_pareto_L.md
- docs/tables/gpu_budget.md
- docs/tables/gpu_budget_tuned.md
- docs/phase10_full_schedule.md
- docs/status/latest.md
- docs/wp7_demo.md
- DECISIONS.md (rows 2026-09-13, 2026-09-14, 2026-09-18, 2026-09-24, 2026-09-25)
- ampscape/models/common.py, unet.py, fno.py, vit.py, gnn.py, coarsen.py docstrings
- ampscape/models/__init__.py `MODEL_CONFIGS` / `OFFICIAL` constants and comment (code, flagged)
- ampscape/metrics/transforms.py module docstring (ε value; outside the enumerated list, flagged)
- scripts/train.py and scripts/transfer_eval.py docstrings; scripts/train.py argparse help for `--target-norm`, `--published-tiers`, `--variant`, `--extra`
- scripts/slurm/gpu/gpu_driver.py `TIER_RES` / `GNN_BATCH` and scripts/slurm/gpu/train_full.sbatch `PATIENCE` (code, flagged)
- configs/baselines/: directory does not exist
