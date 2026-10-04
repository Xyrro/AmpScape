# Baselines and protocol

*Draft section. Every number is copied from a repository file and tagged with its source. Tags pointing at code constants rather than docstrings or tables are flagged "(code)". Compute consumed, the tuning budget and the superseded skeleton results table are kept in paper/appendix_notes.md.*

## Baseline models and official configurations

All learned baselines share one input stack and one target. Inputs: channel 0 = standardised log-resistance (train-only mean/std, 0 at NoData), channel 1 = NoData mask, then the task's source channels — T1: focal mask (any label); T3: source strength scaled by the number of valid pixels plus the ground mask; T4: Omniscape source strength (max 1) [ampscape/models/common.py module docstring]; an optional extra channel, the Euclidean distance to the nearest source/focal pixel divided by max(H, W), was offered to every model in tuning as a global cue for local architectures [ampscape/models/common.py `distance_channel` docstring]. The target is log10(C + ε·max C) per map, predicted directly under a masked MSE that excludes NoData and the T1W strips [ampscape/models/common.py docstrings]; ε = 1e-6, chosen over log1p because the ε-shifted log is scale-invariant and bounds the dynamic range to 6 decades below the map maximum [ampscape/metrics/transforms.py docstring].

- **U-Net** — 4-level encoder–decoder, GroupNorm + GELU [ampscape/models/unet.py docstring]; official config `base` (width 32, 4 levels, 7.766 M parameters [docs/tables/baselines_full.md]), no extra channel: the wide variant was within single-seed noise (+3 % at 2.2× the parameters) and the distance channel hurt [ampscape/models/__init__.py `OFFICIAL` comment (code)].
- **FNO** — 2-D Fourier Neural Operator, resolution-agnostic, with the number of retained modes as the only spatial hyper-parameter [ampscape/models/fno.py docstring]; official config `m64` (width 32, 64 modes, 4 layers; 33.563 M parameters [docs/tables/baselines_full.md]) plus the distance channel, the only configuration in which FNO recovered on T1 (dev rel-L2 1.14 → 0.34) [ampscape/models/__init__.py (code)]. FNO trains in fp32 (complex spectral weights); the others use bf16 autocast [DECISIONS.md 2026-09-14].
- **ViT** — patch-4 convolutional embedding, pre-norm blocks with global attention, learned positional embedding bilinearly interpolated to other grid sizes, convolutional decoder with a full-resolution skip [ampscape/models/vit.py docstring]; official config patch 4, dim 192, depth 6, learned 32×32 positional embedding (3.025 M parameters [docs/tables/baselines_full.md]), fixed across tiers (at L: interpolated to 128×128, global attention over 16,384 tokens) [DECISIONS.md 2026-09-24]; patch 2 and the distance channel did not help [ampscape/models/__init__.py (code)].
- **GNN** — grid-as-graph: nodes = valid pixels, 8-neighbour edges weighted by Circuitscape's average-conductance rule, residual message passing on conductance-weighted neighbour differences, receptive field = number of hops [ampscape/models/gnn.py docstring]; official config the two-level `MultiScaleGridGNN` (message passing on a 4×-coarsened graph, scattered back and refined on the fine graph) [ampscape/models/gnn.py class docstring] plus the distance channel (dev T1 1.04 → 0.69, T4 0.17 → 0.15) [ampscape/models/__init__.py (code)]; 0.24 M parameters [docs/tables/gpu_budget_tuned.md].

These configurations were frozen by a tuning pass on the dev subset (FNO 32/64 modes, multi-scale GNN, one alternative each for U-Net and ViT, the distance channel for all) [DECISIONS.md 2026-09-14].

## Training protocol

Each run trains one model on one task at one tier for 30 epochs with AdamW, a cosine schedule, early stopping on the validation loss and a fixed seed [scripts/train.py docstring; epochs: docs/status/latest.md]; three seeds per (model, task, tier) [docs/phase10_full_schedule.md §2]. Patience is 8 epochs [scripts/slurm/gpu/train_full.sbatch (code); script default 6]; learning rate 1e-3 for U-Net, FNO and GNN and 3e-4 for the ViT [scripts/train.py DEFAULT_LR]; batch sizes S 16 / M 8 / L 4, GNN 8 / 4 / 1 [scripts/slurm/gpu/gpu_driver.py `TIER_RES` (code); batch 4 at L confirmed for the ViT in DECISIONS.md 2026-09-24]. The fixed epoch budget meets training sets of 100 k / 30.7 k / 12.3 k landscapes at S / M / L [docs/status/latest.md]. Runs use L40S GPUs (bf16, 48 GB) with A100 spill-over [docs/phase10_full_schedule.md §1]. Normalisation statistics are train-only [ampscape/models/common.py docstring] and per tier: a model is always evaluated with the statistics of its training tier (`config.json`), including at transfer tiers [scripts/transfer_eval.py docstring].

## Evaluation protocol

Every run is evaluated on `test_id`, `test_ood` and `ood_region`, and at S also on the published tiles [docs/phase10_full_schedule.md §2; `--published-tiers` default S, scripts/train.py]. Metrics: MAE in log10-ε space, rel-L2, top-5 % IoU, pinch-point recall, Spearman, corridor Dice, SSIM and median speed-up [docs/tables/baselines_full.md header].

**T4 at M and L.** Production targets are block-centred Omniscape maps; the block-1 (exact) reference subsets are the official T4 evaluation surface at M and L, block-centred metrics secondary [DECISIONS.md 2026-09-18]. The subsets hold 400 / 300 / 300 (test_id / test_ood / ood_region) landscapes at M and 24 / 16 / 20 at L, and the same tables give the solver's own error-vs-cost rows: at M the production block-3 solver reaches rel-L2 0.0291 at 111 s per landscape, at L production block 5 reaches 0.0315 at 566 s versus 1.23e+04 s for block 1 [docs/tables/t4_pareto_M.md; docs/tables/t4_pareto_L.md].

**XL and XXL are zero-shot scale transfer, not training.** XL and XXL are held-out-scale tiers for models trained at ≤ L; nothing is trained at XL [docs/phase10_full_schedule.md §5; DECISIONS.md 2026-09-24]. Every L-trained run is evaluated at XL and XXL at batch 1 with the training tier's statistics (`scripts/transfer_eval.py`), XXL only for the fully convolutional models (U-Net, FNO, GNN) since the ViT's interpolated positional embedding stops at XL [docs/phase10_full_schedule.md §5]. For T4 this is also transfer across operators — the XL target uses block 11 / radius 128 and XXL block 25 / radius 256 versus block 5 / radius 64 at L [docs/status/latest.md, check 1] — and no re-calibration is applied [docs/status/latest.md].

## Scale-aware target variant

`--target-norm scale` replaces the absolute target by log10(k·C + ε·max) with a tier-computable k: for T1/T3, k = sqrt(N_valid / N_ref), N_ref = 512² (under a uniform rescaling by s per axis with the same injected current, current per pixel column scales as 1/s and the valid pixel count as s²); for T4, k = r_ref / r_tier with r_ref = 64, because Omniscape currents accumulate as C ∝ r·s̄ (each window injects ∝ r²·s̄ over ∝ r pixels and a pixel sits in ∝ (r/b)² windows with b ≈ r/10). Both factors depend only on the inputs and the evaluation tier; the inverse divides the prediction by k, so metrics stay in absolute current units [ampscape/models/common.py `target_scale` docstring]. At L the variant equals the official target numerically (k = 1), so any difference is the transfer [docs/status/latest.md, check 3]. The variant is trained as `<model>_<task>_L_s1_scalenorm` (seed 1) on T1 and T4 at L and then transferred zero-shot exactly like the official runs [DECISIONS.md 2026-09-25; paper/tables/scale_transfer.md].

## Non-learned baselines

**Coarsen ×4**: geometric-mean resistance and majority NoData over f×f blocks, any-label focal pixels, block-summed (T3) or block-mean (T4) sources, a reference CHOLMOD solve on the coarse grid, bilinear upsampling (pairwise/advanced maps divided by f, coarse focal pixels in-filled, true focal pixels reset to 1 A); inference time = coarsening + solve + upsampling [ampscape/models/coarsen.py docstring; DECISIONS.md 2026-09-13]. **Block-size rows** (T4): Omniscape at larger blocks with and without artifact correction, timed per landscape against block 1 [docs/tables/t4_pareto_M.md; docs/tables/t4_pareto_L.md].

## Compute

All baselines reported in this paper — training, evaluation, zero-shot transfer and the many-query demonstration — consumed 430.1 GPU-hours [docs/tables/gpu_usage.md].

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
