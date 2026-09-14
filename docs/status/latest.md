# Status — 2026-09-14 (dev subset + Phase 10)

**Dev subset built, Phase 10 complete; waiting for owner decisions** (split rules, GPU sizing) before Phase 11.

- **Dev subset** `data/dev`: 3 000 S + 500 M landscapes as a true prefix of v1.0 (tier-disjoint synthetic seeds with the
  hard-case stratum, prefix-extracted stratified real tiles × 5 tables incl. per-tile random tables), all tasks, CHOLMOD,
  100 % / 99.9 % QC, 66 CPU-h, 4.9 GB; splits by the v1.0 rule (`docs/dev_subset.md`).
- **Two split findings need a decision** (labels only): cell-level biome hold-out made 52 % of real S tiles OOD (now
  tile-level by default); the 32 v1.0 XXL parent footprints merge into 13 continental regions covering 72 % of S tiles
  (parent regions disabled for dev). Both are config switches in `configs/datasets/v1_0.yaml`.
- **Learned baselines** (U-Net, FNO, ViT-based, grid-GNN; shared inputs / log10-ε targets / masked MSE; `scripts/train.py`)
  trained on T1 and T4 (all four) and T3 (U-Net, FNO), single seed, evaluated through `evaluate.py` on test_id,
  test_ood, ood_region and test_ood_published alongside the coarsen baseline (`docs/tables/baselines_dev.md`).
  test_id rel-L2: U-Net T1 0.25 / T3 0.30 / T4 0.09; U-Net is the only model beating the non-learned baseline on T1,
  FNO and GNN fail on T1 (≥ 1.0), all models collapse on the XXL published tile (scale transfer is the hard axis).
- **No task is too easy**: best test_id rel-L2 0.093 (T4), above the 0.05 flag.
- **GPU**: 1.44 GPU-h for the ten dev runs (1.8 GPU-h for every GPU job of the phase); v1.0 extrapolation 365 GPU-h
  (optimistic epoch rule) to 933 GPU-h (30 epochs per tier), three seeds, S–XL, L40S — GNN is half of it.
- Environment: torch pinned to the cu126 wheels (ICE driver is CUDA 12.9); one faulty-GPU node killed eight jobs (resubmitted).
- Tests: 129 passing.

Full report: `docs/phase_10_report.md`.
