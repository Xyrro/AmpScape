# Per-tier tuning pass at M and L (item 2, 2026-10-05) — plan and cost estimate

Rule: tuned on **val only** (selection by val rel-L2 of the training-tier val split, seed 1, T1); test splits are
not looked at until the per-tier official configs are frozen. One seed per candidate; the official config is the
reference candidate (its val rel-L2 comes from the existing seed-1 run). A per-tier config replaces the official one
only if it improves val rel-L2 by more than the seed spread of the official run (std over the three seeds in
`paper/tables/baselines_sml.md`); otherwise the official config stays. Every model whose config changes at a tier is
re-run with three seeds on all its tasks at that tier (T1, T4; T3 for U-Net/FNO), and the tables/figures are
regenerated (`scripts/paper_figures.py`).

| model | official | M candidates | L candidates | rationale |
|---|---|---|---|---|
| U-Net | base 32, 4 levels | wide (48), w64 (64) | wide (48) | width (owner) |
| FNO | width 32, 64 modes, + dist | m96 (96 modes), w48 (width 48) | m96, w48 | modes for 256²/512²; channel width |
| ViT | patch 4, dim 192, depth 6, learned 32×32 pos. (interpolated) | p8g32 (patch 8, native 32×32 grid), p16g16 | p16g32 (native grid), p8g64 (4096 tokens) | patch size and positional grid sized to the tier (no interpolation) |
| GNN | multiscale ×4 + dist | ms8 (×8 coarse level) | ms8 | coarser second level for larger landscapes |

Cost estimate (measured official seed-1 training GPU-h × a factor for the larger config): U-Net M 1.6 × (1.5, 2.5),
L 1.5 × 1.5 → 8.7 GPU-h; FNO M 1.6 × (1.5, 1.5), L 2.7 × (1.5, 1.5) → 12.9; ViT M ≈ 1.0 + 0.8, L ≈ 2.5 + 5 → 9.3;
GNN M ≈ 6 (×8 level is cheaper than ×4), L ≈ 10 → 16. **Total ≈ 47 GPU-h for 13 runs (≤ 50).** Re-run cost after
freezing is estimated separately once the winners are known (upper bound if every config changed at both tiers:
4 models × 2 tiers × tasks × 3 seeds ≈ 60 runs ≈ 180–250 GPU-h at measured rates).

Runs are named `<model>_T1_<tier>_s1_tune_<variant>` under `runs/tune_full/`; selection table
`docs/tables/tuning_full.md`; the frozen per-tier configs go into `ampscape/models/__init__.py` (`OFFICIAL_BY_TIER`)
and `DECISIONS.md`.
