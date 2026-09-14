# Phase 10 report — dev subset and learned baselines

Date: 2026-09-14. Status: **complete, awaiting owner decisions** (split rules, GPU sizing) before Phase 11.

## 1. Dev subset (`data/dev`, a true prefix of v1.0)

See `docs/dev_subset.md` for the full design. In short: 3 000 S + 500 M landscapes drawn from the v1.0 streams
(tier-disjoint synthetic seeds with the hard-case stratum; stratified real-tile stream, prefix-extracted, × 5
tables incl. a per-tile random table), all tasks, CHOLMOD reference, CG baselines on every test/OOD sample, splits
by the v1.0 spatial rule. 66 CPU-hours on ICE (below the 150 core-hour report threshold), 4.9 GB of shards, 100 %
QC at S and 99.9 % at M (two contrast-10⁶ configurations at residual 1.0e-6, the threshold).

**Two split findings need your decision** (labels only; recomputed at finalize, samples unchanged):
1. cell-level biome hold-out turned 52 % of the real S tiles into `ood_region` and left no real `test_id` tile →
   now tile-level by default (`test_ood_region.unit: tile`);
2. the 32 v1.0 XXL footprints merge into 13 continental parent regions covering 72 % of S tiles, and held-out
   parents propagate OOD to 12 of them → parent regions disabled for dev (`parent_regions: false`); S–XL tiles are
   assigned by macro-cell, XXL stays test-only, the S-inside-XXL overlap is ≤ 0.004 % of an XXL tile.

## 2. Learned baselines (`ampscape/models`, `scripts/train.py`)

All four models share the pipeline in `ampscape/models/common.py` and `scripts/train.py`: inputs = standardised
log-resistance (train-only mean 3.08 / std 2.23 of log R over valid pixels), NoData mask, and the task's source
channels (T1: focal mask; T3: source strength × n_valid and the ground mask; T4: Omniscape source strength);
target = log10(C + ε·max C) of the reference map (ε = 1e-6), predicted directly; masked MSE (NoData excluded);
AdamW (weight decay 1e-4), cosine schedule, gradient clipping 1.0, batch 16, bf16 autocast (FNO in fp32: complex
spectral weights), early stopping on the validation loss (patience 12, cap 120 epochs, 75-min budget), seed 0.
Predictions are written in the harness format (`predictions.h5`, per-sample GPU-synchronised inference time,
batch-amortised) and scored by `scripts/evaluate.py`; `config.json`, `log.csv`, `best.pt`, `results.json` per run
under `runs/dev/<model>_<task>/`.

| model | architecture (`MODEL_CONFIGS`) | params | lr | notes |
|---|---|---|---|---|
| `unet` | 4-level U-Net, base width 32 (32→512), GroupNorm + GELU, transposed-conv decoder | 7.77 M | 1e-3 | fully convolutional: evaluated on the XXL published tile too |
| `fno` | FNO-2d: lifting (+ coordinate channels), 4 spectral layers, width 32, 16 × 16 modes, pointwise skips, GELU, projection | 2.11 M | 1e-3 (re-run 3e-4) | resolution-agnostic; evaluated on XXL too |
| `vit` | patch-4 conv embedding, dim 192, 6 pre-norm blocks × 6 heads (global attention over 32 × 32 tokens), learned position embedding (interpolated for other sizes), 2-stage transposed-conv decoder + full-resolution conv skip | 3.03 M | 3e-4 | "ViT-based encoder-decoder" (brief §12.4); global attention limits it to S/M |
| `gnn` | grid-as-graph: nodes = valid pixels, 8-neighbour edges weighted by Circuitscape's average-conductance rule (row-normalised); 12 residual message-passing layers h ← h + MLP([h, Σ w (h_j − h_i)]), dim 64 | 0.16 M | 1e-3 | exact graph structure; receptive field = 12 hops |


## 3. Results (dev S; test_id, test_ood, ood_region; test_ood_published)

Full table (all metrics, all splits, `n`): `docs/tables/baselines_dev.md`; per-run JSON under `runs/dev/`. Means over
samples; rel-L2 in current units, mae in log10-ε space; speed-up = reference solver wall time / batch-amortised GPU
inference time (data loading excluded), median.

| task | split (n) | model | mae_log10eps | rel_l2 | top5_iou | pinch_recall | spearman | corridor_dice | speed-up |
|---|---|---|---|---|---|---|---|---|---|
| T1 | test_id (351) | **unet** | 0.145 | **0.251** | 0.650 | 0.726 | 0.946 | 0.810 | 728× |
| | | vit | 0.433 | 0.574 | 0.243 | 0.684 | 0.642 | 0.408 | 546× |
| | | gnn | 0.613 | 1.038 | 0.406 | 0.537 | 0.566 | 0.552 | 25× |
| | | fno (lr 1e-3 / 3e-4) | 0.598 / 0.601 | 1.144 / 1.132 | 0.107 / 0.102 | 0.343 / 0.215 | 0.606 / 0.598 | 0.300 / 0.286 | 722× |
| | | coarsen4 (n = 328) | 0.113 | 0.464 | 0.570 | 0.393 | 0.937 | 0.783 | 3.6× |
| T1 | test_ood (184) | unet | 0.135 | 0.263 | 0.660 | 0.686 | 0.945 | 0.814 | 679× |
| | | vit / gnn / fno | 0.414 / 0.584 / 0.562 | 0.588 / 1.004 / 9.83 | 0.241 / 0.411 / 0.097 | 0.630 / 0.440 / 0.326 | 0.638 / 0.529 / 0.591 | 0.370 / 0.562 / 0.258 | |
| | | coarsen4 (180) | 0.124 | 0.492 | 0.531 | 0.306 | 0.919 | 0.749 | 4.2× |
| T1 | ood_region (300) | unet | 0.081 | 0.196 | 0.738 | 0.770 | 0.970 | 0.867 | 718× |
| | | vit / gnn / fno | 0.381 / 0.566 / 0.563 | 0.576 / 1.157 / 1.188 | 0.239 / 0.471 / 0.094 | 0.740 / 0.613 / 0.415 | 0.642 / 0.548 / 0.612 | 0.358 / 0.594 / 0.254 | |
| | | coarsen4 | 0.073 | 0.451 | 0.634 | 0.427 | 0.959 | 0.832 | 3.9× |
| T1 | published S (45) | unet / vit / gnn / fno | 0.110 / 0.377 / 0.568 / 0.578 | 0.248 / 0.615 / 1.293 / 1.322 | 0.637 / 0.285 / 0.376 / 0.137 | 0.609 / 0.602 / 0.308 / 0.316 | 0.952 / 0.670 / 0.572 / 0.609 | 0.807 / 0.436 / 0.531 / 0.315 | |
| T1 | published XXL (1) | unet / fno | 1.700 / 0.870 | 0.906 / 1.772 | 0.193 / 0.013 | 0.037 / 0.024 | 0.070 / 0.538 | 0.312 / 0.127 | 440× / 177× |
| T3 | test_id (351) | **unet** | 0.175 | **0.303** | 0.587 | 0.650 | 0.914 | 0.769 | 311× |
| | | fno | 0.305 | 0.543 | 0.342 | 0.467 | 0.741 | 0.553 | 309× |
| | | coarsen4 | 0.134 | 0.295 | 0.622 | 0.348 | 0.927 | 0.796 | 2.2× |
| T3 | test_ood (184) | unet / fno / coarsen4 | 0.166 / 0.290 / 0.124 | 0.301 / 0.520 / 0.320 | 0.541 / 0.347 / 0.561 | 0.581 / 0.438 / 0.269 | 0.934 / 0.783 / 0.927 | 0.764 / 0.571 / 0.763 | |
| T3 | ood_region (300) | unet / fno / coarsen4 | 0.116 / 0.245 / 0.081 | 0.239 / 0.493 / 0.246 | 0.619 / 0.366 / 0.678 | 0.703 / 0.486 / 0.381 | 0.942 / 0.761 / 0.958 | 0.803 / 0.571 / 0.841 | |
| T3 | published S (45) | unet / fno | 0.142 / 0.302 | 0.359 / 0.632 | 0.538 / 0.235 | 0.563 / 0.430 | 0.924 / 0.628 | 0.747 / 0.431 | |
| T3 | published XXL (1) | unet / fno | 1.826 / 1.484 | 18.7 / 8.6 | 0.191 / 0.178 | 0.327 / 0.169 | 0.270 / 0.584 | 0.291 / 0.264 | |
| T4 | test_id (351) | **unet** | **0.063** | **0.093** | 0.743 | 0.834 | 0.987 | 0.895 | 1.9e5× |
| | | fno / gnn / vit | 0.155 / 0.127 / 0.280 | 0.121 / 0.170 / 0.165 | 0.649 / 0.562 / 0.562 | 0.636 / 0.655 / 0.770 | 0.964 / 0.949 / 0.937 | 0.838 / 0.782 / 0.781 | 1.9e5× / 6.7e3× / 1.4e5× |
| | | coarsen4 | 0.479 | 0.727 | 0.580 | 0.500 | 0.923 | 0.774 | 45× |
| T4 | test_ood (184) | unet / fno / gnn / vit / coarsen4 | 0.069 / 0.136 / 0.110 / 0.132 / 0.484 | 0.121 / 0.148 / 0.196 / 0.177 / 0.736 | 0.632 / 0.540 / 0.438 / 0.424 / 0.479 | 0.747 / 0.561 / 0.551 / 0.703 / 0.365 | 0.955 / 0.913 / 0.834 / 0.832 / 0.885 | 0.807 / 0.735 / 0.633 / 0.608 / 0.698 | |
| T4 | ood_region (300) | unet / fno / gnn / vit / coarsen4 | 0.071 / 0.176 / 0.111 / 0.313 / 0.476 | 0.076 / 0.100 / 0.137 / 0.145 / 0.715 | 0.701 / 0.581 / 0.478 / 0.462 / 0.596 | 0.856 / 0.647 / 0.646 / 0.798 / 0.509 | 0.986 / 0.966 / 0.944 / 0.927 / 0.951 | 0.865 / 0.785 / 0.702 / 0.680 / 0.798 | |
| T4 | published S (45) | unet / fno / gnn / vit | 0.107 / 0.213 / 0.113 / 0.225 | 0.160 / 0.177 / 0.273 / 0.230 | 0.717 / 0.617 / 0.534 / 0.509 | 0.799 / 0.578 / 0.607 / 0.624 | 0.975 / 0.935 / 0.935 / 0.877 | 0.881 / 0.815 / 0.770 / 0.739 | |
| T4 | published XXL (1) | unet / fno | 1.128 / 1.195 | 0.928 / 0.938 | 0.271 / 0.448 | 0.417 / 0.648 | 0.891 / 0.955 | 0.561 / 0.745 | |

Reading:
- **U-Net is the only learned model that beats the non-learned coarsen-×4 baseline on T1** (rel-L2 0.25 vs 0.46;
  pinch-point recall 0.73 vs 0.39), and on T3 it merely matches it (0.30 vs 0.30, worse mae); on T4 every learned
  model beats coarsening by a wide margin (U-Net 0.09 vs 0.73), Omniscape's local moving-window target being the
  most learnable. Speed-ups are 10²–10⁵× (batch-amortised GPU inference vs the single-core reference solve).
- **FNO and GNN fail on T1** (rel-L2 ≥ 1.0, i.e. worse than predicting zero): 16 retained Fourier modes cannot
  represent point-source currents (a second FNO run with lr 3e-4 confirms it is not the optimiser), and 12
  message-passing hops cover 12 pixels of a 128-pixel grid. Both are informative negative results for the
  benchmark; deeper GNNs and more modes are the obvious follow-ups. The ViT variant sits in between.
- **OOD gaps are small at this size and sometimes inverted**: ood_region (held-out biomes/realm, many low-contrast
  tiles) is *easier* than test_id for every model; test_ood (forest_bird table, contrast 10⁶) costs U-Net 5–30 %
  in rel-L2; the published rasters (S) are within 10–20 % of test_id. The real OOD challenge shows up in
  **resolution/scale transfer**: on the single XXL published tile the fully convolutional models collapse
  (T1 rel-L2 0.91, T3 > 8, T4 0.93 — no better than the zero predictor), so `test_ood_scale` will be the hard axis.
- Physics: none of the learned models is conservative (`phys_kirchhoff_residual` is undefined without a voltage
  head; `phys_neg_fraction` = 0 by construction of the log target); T1 focal-current error is not enforced.


## 4. GPU-hours and extrapolation to v1.0

Measured on one L40S (bf16 autocast except FNO), `runs/dev/*/log.csv`, `docs/tables/gpu_budget.md`:

| model | task | params (M) | train items | epochs run (best) | s / epoch | GPU-h / epoch | training GPU-h |
|---|---|---|---|---|---|---|---|
| unet | T1 | 7.77 | 1 786 | 119 (107) | 3.4 | 0.0009 | 0.113 |
| unet | T3 | 7.77 | 1 839 | 96 (84) | 2.9 | 0.0008 | 0.077 |
| unet | T4 | 7.77 | 1 839 | 57 (45) | 3.0 | 0.0008 | 0.048 |
| fno | T1 | 2.11 | 1 786 | 18 (6) | 3.5 | 0.0010 | 0.017 |
| fno | T3 | 2.11 | 1 839 | 69 (57) | 2.9 | 0.0008 | 0.055 |
| fno | T4 | 2.11 | 1 839 | 82 (70) | 3.0 | 0.0008 | 0.068 |
| vit | T1 | 3.03 | 1 786 | 61 (49) | 3.7 | 0.0010 | 0.063 |
| vit | T4 | 3.03 | 1 839 | 33 (21) | 3.1 | 0.0009 | 0.028 |
| gnn | T1 | 0.16 | 1 786 | 30 (18) | 29.1 | 0.0081 | 0.243 |
| gnn | T4 | 0.16 | 1 839 | 89 (77) | 29.6 | 0.0082 | 0.731 |

Dev training total **1.44 GPU-h** for the ten runs; every GPU job of this phase (smoke tests, calibration, the eight
runs killed by a faulty GPU, re-runs, evaluation passes) sums to **1.8 GPU-h** of the 20 GPU-hour gate. (The epoch
cap, not the 75-min budget, ended every run; early stopping fired in all of them.)

Extrapolation to v1.0 training (`scripts/gpu_budget.py`; recommended ladder S 100k / M 50k / L 20k / XL 4k, dev-measured
train share 0.61 (S) / 0.72 (M), XL 25 % train slice; per-sample time ∝ pixels; three seeds; per model × task):

| scenario | unet T1 / T3 / T4 | fno T1 / T3 / T4 | vit T1 / T4 | gnn T1 / T4 | **total** |
|---|---|---|---|---|---|
| epochs = dev best epoch × √(dev/v1.0 train size), min 5 | 31 / 20 / 12 | 4 / 14 / 18 | 16 / 6 | 49 / 195 | **365 GPU-h** |
| 30 epochs at every tier (or the dev best epoch if larger) | 74 / 48 / 27 | 21 / 32 / 42 | 37 / 18 | 179 / 453 | **933 GPU-h** |

Reading for sizing: **≈ 1 000 L40S-hours covers the full v1.0 baseline matrix (10 model × task combinations, three
seeds, S–XL) under the conservative rule; ≈ 400 under the optimistic one.** The GNN is half of the bill (16 ms per
sample-epoch, 8× the convolutional models) and ViT at L/XL needs windowed attention (16 384 tokens at 512²);
excluded: T1W/T1R/T2 heads, hyper-parameter search, the physics-informed variant, and XXL inference (batch-1,
≈ 1 GPU-h per fully convolutional model). The ms/sample figures come from 1.8k-item epochs where per-step overheads
dominate, so they are upper bounds for well-batched training at scale; A100/H100 would be 1.5–3× faster.


## 5. Difficulty check (owner item 4)

No model reaches rel-L2 below 0.05 on `test_id` at S. The best values are U-Net T4 **0.093** (Omniscape with a
16-pixel radius is the most local, hence easiest, target), U-Net T1 0.251, U-Net T3 0.303; the second-best
architecture per task is 1.3–2.3× worse (FNO T4 0.121, ViT T1 0.574, FNO T3 0.543). Pinch-point recall and
top-5 % IoU stay far from saturation (U-Net T1: 0.73 / 0.65). The tasks are therefore not too easy at this size;
T4 at S is the one to watch when v1.0 scales up — its margin to the 0.05 threshold is smallest, but a single seed
on 1.8k training landscapes says little about the asymptote, and the OOD gaps (below) are what the benchmark is
about.


## 6. Environment notes, tests, open items

- Environment: the ICE GPU nodes run driver 575 / CUDA 12.9; PyPI's torch 2.14 wheel targets CUDA 13.0 and refuses
  to initialise, so `pyproject.toml` now pins torch/torchvision to the cu126 wheel index (`uv sync --extra dev`).
  Eight of the ten first submissions landed on one node with an uncorrectable-ECC GPU and died in 3 s; they were
  resubmitted with `--exclude` (the failed jobs cost 0.01 GPU-h).
- Dev-subset pipeline fixes found on the way: undefined wall-to-wall / advanced configurations are skipped instead
  of aborting a shard (large-NoData hard cases), coarse-grid baseline configurations whose focal nodes merge or
  disconnect are skipped, `assign.py` import block, stable XL hash.
- Tests: 129 passing (`pytest --ignore=tests/test_real_network.py`); new `tests/test_plan_v1.py`, v1 sampler tests,
  coarsen tests.
- Open for the owner: (1) region hold-out unit and XXL parent regions (§1); (2) GPU request size (§4); (3) whether
  T2 (Reff head), T1W and T1R get learned baselines in v1.0 (not in this phase's scope); (4) FNO/GNN configuration
  — both underfit T1 at this budget (§3); a wider FNO (more modes) and a deeper GNN are the obvious next steps.

