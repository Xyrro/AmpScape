# Appendix — Why zero-shot scale transfer of T4 fails by exactly 1 − r_train/r_eval, and why the scale-aware target removes it

Referenced from the results section (scale transfer). Facts used: Omniscape window radius per tier r = 16, 32, 64, 128,
256 px for S, M, L, XL, XXL with block size b = largest odd integer ≤ r/10 [configs/solver/omniscape_reference.yaml;
docs/t4_fidelity.md]; source strength s(x) ∈ [0, 1] = inverse-resistance suitability above its 0.5 quantile, rescaled
to a maximum of 1 per landscape, `source_threshold = 0` [docs/t4_fidelity.md]; target maps are cumulative current
`cum_current` summed over windows [docs/t4_fidelity.md]; measured zero-shot errors of the L-trained models at XL and
XXL: rel-L2 0.515 / 0.532 / 0.538 (U-Net / FNO / ViT) at XL and 0.749 / 0.765 (U-Net / FNO) at XXL on test_id, three
seeds each with std ≤ 0.002 [paper/tables/scale_transfer.md].

## A.1 Magnitude of the Omniscape cumulative current scales with the window radius

Omniscape visits every block centre t (one per b × b block) and solves one circuit per visit: every pixel x within
distance r of t injects a current proportional to its source strength s(x) and the target t is grounded; the per-visit
current maps are summed over all visits into the cumulative current C [docs/t4_fidelity.md]. Consider a pixel y of a
landscape and the visits whose window contains y.

1. **Injected current per visit** is Σ_{|x−t|≤r} s(x) ≈ s̄ · π r², where s̄ is the mean source strength of the window
   (sources are an input the model sees, so s̄ is treated as given; it does not depend on the tier).
2. **Current density at y within one visit.** The injected current flows towards the single grounded target t.
   For a pixel at distance ρ from t the current that passes through the pixel's row of the grid is the share of the
   injected current flowing through a front of length ∝ ρ, so the per-pixel current is ∝ (injected current within
   radius ρ of t) / ρ ∝ s̄ ρ² / ρ = s̄ ρ for ρ ≤ r, i.e. of order s̄ r over most of the window. On a heterogeneous
   resistance surface the proportionality constant depends on the local resistance structure, which is what the
   surrogate learns; the dependence on r is the same for every pixel.
3. **Number of visits covering y** is the number of block centres within distance r of y: ∝ (r / b)², and with
   b = r/10 this is a constant (≈ 100) independent of the tier.

Hence C(y) ∝ s̄ · r · g(y), where g collects the resistance-dependent, tier-independent factors. Doubling the
window radius doubles the cumulative current everywhere, to first order.

## A.2 The zero-shot transfer error

A model trained at tier L learns to output C_L ∝ r_L · s̄ · g. Evaluated zero-shot at a tier with radius r_eval on a
landscape with the same resistance statistics, it predicts P ≈ C_eval · (r_L / r_eval) (the same g, the wrong
magnitude). With κ = r_L / r_eval,

  rel-L2 = ‖P − C_eval‖₂ / ‖C_eval‖₂ = ‖(κ − 1) C_eval + ε‖₂ / ‖C_eval‖₂ ≈ 1 − κ = 1 − r_L / r_eval,

where ε is the model's intrinsic error (its in-tier rel-L2 is 0.08–0.16 [paper/tables/baselines_sml.md]) and the
approximation holds when (1 − κ)‖C‖ dominates ‖ε‖, which it does at XL and XXL. Predicted values: XL
1 − 64/128 = 0.50, XXL 1 − 64/256 = 0.75; measured: 0.515–0.538 and 0.749–0.765 [paper/tables/scale_transfer.md],
with the small excess over the prediction accounted for by ε added in quadrature. The near-identical values across
U-Net, FNO and ViT, and the std ≤ 0.002 across seeds, are consistent with an error that is set by the operator (the
radius), not by the model. Rank-based metrics are unaffected by a common factor, which is why Spearman stays at
0.93–0.96 while rel-L2 collapses [paper/tables/scale_transfer.md].

## A.3 The scale-aware target

The variant trains on k · C with k = r_ref / r_tier (r_ref = 64, tier L) [ampscape/models/common.py
`target_scale`], so that the regression target is k · C ∝ (r_ref / r_tier) · r_tier · s̄ · g = r_ref · s̄ · g —
independent of the tier. At evaluation the prediction is divided by k_eval = r_ref / r_eval, restoring
C_eval ∝ r_eval · s̄ · g. No quantity of the evaluation tier other than its radius (a protocol constant) enters,
and no XL/XXL data is used in training or in the inverse. What remains after the correction is the error that is not a
common factor: the measured scale-aware rel-L2 is 0.16–0.22 at XL and 0.20–0.34 at XXL against an in-tier 0.08–0.16
[paper/tables/scale_transfer.md]; this residual is the operator-learning transfer error proper (window geometry
changes by more than a factor — b and r both scale, the resistance field has different pixel size and extent — see
the resolution-versus-size caveat in the discussion).

## A.4 The pairwise analogue (T1)

For a pairwise solve a unit current is injected per source and extracted at the ground regardless of landscape size.
Under a uniform rescaling of the landscape by s per axis with the same resistance statistics, the current that
crosses any front spreads over ∝ s pixels, so the per-pixel current ∝ 1/s, while the valid pixel count N ∝ s².
The factor k = √(N_valid / N_ref) with N_ref = 512² [ampscape/models/common.py `target_scale`] makes k · C
invariant; it is computed from the input mask alone. The measured throughput error of the zero-shot T1 transfers
(0.5–0.9 at XL) [paper/tables/scale_transfer.md] is the signature of the same magnitude mismatch; the correction
helps the FNO (0.707 → 0.572 at XL, 1.502 → 0.671 at XXL) and the ViT but not the U-Net or GNN, whose errors at XL/XXL
remain near rel-L2 1 because their receptive fields do not cover the longer-range flow paths of the larger landscapes —
a structural, not a magnitude, limit.

## A.5 Assumptions and scope

The argument assumes (i) b/r fixed by the block rule, (ii) sources with tier-independent mean strength, (iii) the
same resistance statistics across tiers (real tiles at XL/XXL have coarser pixels, 500 m and 1 km, than L's 200 m
[docs/dataset_card.md], which changes the resistance statistics — part of the residual in A.3), and (iv) that the
window fits inside the landscape for most pixels (edge effects shrink the effective window near the boundary at
every tier alike). It explains the magnitude of the zero-shot error; it does not predict which model transfers best
once the magnitude is corrected.
