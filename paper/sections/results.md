# 7–8. Results

Every number in this section is copied from a regenerated table or report file; the source is tagged inline in
square brackets. Unless stated otherwise, errors are rel-L2 on the `test_id` split of the tier the model was trained
on, mean ± std over three seeds of the official configurations (30 epochs; §7 protocol). The "speed-up" column is the
median per-landscape wall-time ratio between the reference solver and batched GPU inference, as defined in §6. All
baselines reported here consumed 430.1 GPU-h across 401 jobs [docs/tables/gpu_usage.md].

The headline is a trade-off, not a replacement: the best learned surrogate reaches rel-L2 0.04–0.08 on T4 at four to
five orders of magnitude lower per-map cost than the production Omniscape run, but it is about 2× further from the exact
map than the production block solver at the same tier, it degrades with tier, it fails on magnitude under zero-shot
scale transfer, and only its *rankings* survive those failures.

## 7.1 In-distribution baselines at S, M and L (T2, F3)

Table T2 gives rel-L2 and MAE in log10 units; the companion table gives the ranking metrics and the speed-up. All
entries are from [paper/tables/baselines_sml.md]. T3 was run with U-Net and FNO only.

**Table T2 — rel-L2 (MAE log10) on test_id, mean ± std over 3 seeds** [paper/tables/baselines_sml.md]

| task | model | S | M | L |
|---|---|---|---|---|
| T1 | U-Net | 0.114 ± 0.007 (0.042 ± 0.002) | 0.212 ± 0.023 (0.103 ± 0.014) | 0.397 ± 0.012 (0.199 ± 0.008) |
| T1 | FNO | 0.199 ± 0.002 (0.111 ± 0.001) | 0.248 ± 0.016 (0.122 ± 0.001) | 0.361 ± 0.024 (0.146 ± 0.001) |
| T1 | ViT | 0.218 ± 0.028 (0.120 ± 0.027) | 0.419 ± 0.123 (0.240 ± 0.099) | 0.648 ± 0.033 (0.375 ± 0.003) |
| T1 | GNN | 0.561 ± 0.006 (0.256 ± 0.002) | 0.849 ± 0.005 (0.337 ± 0.002) | 1.067 ± 0.026 (0.416 ± 0.001) |
| T3 | U-Net | 0.111 ± 0.005 (0.052 ± 0.001) | 0.202 ± 0.006 (0.106 ± 0.002) | 0.379 ± 0.011 (0.202 ± 0.003) |
| T3 | FNO | 0.253 ± 0.001 (0.147 ± 0.002) | 0.284 ± 0.006 (0.163 ± 0.004) | 0.347 ± 0.004 (0.195 ± 0.004) |
| T4 | U-Net | 0.041 ± 0.002 (0.022 ± 0.001) | 0.051 ± 0.000 (0.025 ± 0.000) | 0.081 ± 0.001 (0.038 ± 0.001) |
| T4 | FNO | 0.051 ± 0.001 (0.038 ± 0.001) | 0.079 ± 0.001 (0.052 ± 0.001) | 0.120 ± 0.001 (0.073 ± 0.001) |
| T4 | ViT | 0.052 ± 0.001 (0.032 ± 0.001) | 0.094 ± 0.004 (0.056 ± 0.005) | 0.159 ± 0.004 (0.097 ± 0.003) |
| T4 | GNN | 0.066 ± 0.000 (0.038 ± 0.000) | 0.099 ± 0.001 (0.054 ± 0.001) | 0.142 ± 0.001 (0.074 ± 0.000) |

**Companion — ranking metrics and speed-up on test_id (Spearman / top-5 % IoU / pinch recall; median speed-up ×)**
[paper/tables/baselines_sml.md]

| task | model | S | M | L |
|---|---|---|---|---|
| T1 | U-Net | 0.993 / 0.858 / 0.915; ×625 | 0.964 / 0.708 / 0.722; ×773 | 0.877 / 0.548 / 0.500; ×691 |
| T1 | FNO | 0.967 / 0.723 / 0.814; ×503 | 0.959 / 0.701 / 0.704; ×627 | 0.945 / 0.645 / 0.510; ×659 |
| T1 | ViT | 0.950 / 0.576 / 0.793; ×550 | 0.815 / 0.312 / 0.654; ×463 | 0.665 / 0.146 / 0.472; ×277 |
| T1 | GNN | 0.891 / 0.547 / 0.711; ×48 | 0.860 / 0.500 / 0.540; ×52 | 0.834 / 0.469 / 0.400; ×59 |
| T3 | U-Net | 0.989 / 0.826 / 0.890; ×319 | 0.959 / 0.715 / 0.766; ×223 | 0.859 / 0.522 / 0.557; ×303 |
| T3 | FNO | 0.930 / 0.639 / 0.695; ×219 | 0.916 / 0.611 / 0.634; ×276 | 0.888 / 0.541 / 0.492; ×374 |
| T4 | U-Net | 0.996 / 0.861 / 0.918; ×167,020 | 0.995 / 0.857 / 0.899; ×96,834 | 0.991 / 0.812 / 0.825; ×111,998 |
| T4 | FNO | 0.991 / 0.820 / 0.863; ×124,105 | 0.985 / 0.778 / 0.754; ×70,938 | 0.973 / 0.713 / 0.553; ×137,902 |
| T4 | ViT | 0.992 / 0.811 / 0.893; ×106,498 | 0.979 / 0.720 / 0.819; ×51,358 | 0.953 / 0.605 / 0.735; ×49,239 |
| T4 | GNN | 0.982 / 0.742 / 0.840; ×12,545 | 0.972 / 0.698 / 0.775; ×6,604 | 0.960 / 0.632 / 0.704; ×10,843 |

Three observations structure the section. First, the task families differ: T4 is the easier learning problem and
the one with the real compute problem — the U-Net stays at rel-L2 0.041–0.081 from S to L with Spearman ≥ 0.991 at
speed-ups of 10⁴–10⁵ over the production Omniscape run — whereas T1 and T3, globally coupled through a single sparse
solve, are harder for every model and give speed-ups of only 10²–10³ (×48–59 for the GNN) because a single
full-raster Circuitscape solve is already cheap; their value is as an operator-learning challenge and as a warm start
(§1) [paper/tables/baselines_sml.md]. Second, error grows with tier for every model and task: the best T1 result
goes from 0.114 at S to 0.361 at L, the best T4 result from 0.041 to 0.081 [paper/tables/baselines_sml.md]. Third,
ranking metrics degrade more slowly than magnitudes: between S and L the T4 U-Net's rel-L2 doubles (0.041 → 0.081)
and its pinch-point recall drops from 0.918 to 0.825 while its Spearman barely moves (0.996 → 0.991)
[paper/tables/baselines_sml.md].

## 7.2 T4 against the exact block-1 reference: the speed–accuracy trade-off (F2)

T4 training targets are production Omniscape maps at block ≈ radius/10 (block 3 at M, block 5 at L); for the
reference subsets we also computed the exact block-1 maps, so solver approximations and learned models share one
error-versus-cost axis (F2). Table 7.2 lists solver rows (block-1 reference subset of test_id; `ns_rel_l2` is the
non-source-pixel variant) and learned rows (3-seed means on the full `test_id` split, n = 4,823 at M and 1,927 at L;
cost = median GPU inference per landscape; no non-source variant available) from [paper/tables/t4_pareto_M.md] and
[paper/tables/t4_pareto_L.md].

**Table 7.2 — T4 error vs cost per landscape against the exact block-1 map, test_id (solver rows: reference subset; learned rows: full split)**

| tier | method | n | cost s / landscape | rel-L2 | ns rel-L2 | MAE log10 | top-5 % IoU | pinch recall | Spearman | source |
|---|---|---|---|---|---|---|---|---|---|---|
| M | block 1 (exact) | 400 | 776 | 0 | 0 | 0 | 1 | 1 | 1 | [paper/tables/t4_pareto_M.md] |
| M | production block 3, artefact correction on | 400 | 111 | 0.0291 | 0.0371 | 0.0119 | 0.9357 | 0.9312 | 0.9983 | [paper/tables/t4_pareto_M.md] |
| M | block 3, correction off | 400 | 112 | 0.1105 | 0.1069 | 0.0260 | 0.6105 | 0.7658 | 0.9856 | [paper/tables/t4_pareto_M.md] |
| M | block 7, correction on | 400 | 25.5 | 0.0983 | 0.1064 | 0.0526 | 0.8081 | 0.8081 | 0.9845 | [paper/tables/t4_pareto_M.md] |
| M | block 7, correction off | 400 | 25.4 | 0.2918 | 0.3771 | 0.0679 | 0.5468 | 0.9662 | 0.9664 | [paper/tables/t4_pareto_M.md] |
| M | U-Net (learned, 3 seeds) | 4823 | 0.00109 | 0.0513 | – | 0.0251 | 0.8569 | 0.8993 | 0.9951 | [paper/tables/t4_pareto_M.md] |
| M | FNO (learned, 3 seeds) | 4823 | 0.00147 | 0.0787 | – | 0.0524 | 0.7784 | 0.7537 | 0.9847 | [paper/tables/t4_pareto_M.md] |
| M | ViT (learned, 3 seeds) | 4823 | 0.00205 | 0.0942 | – | 0.0561 | 0.7199 | 0.8193 | 0.9789 | [paper/tables/t4_pareto_M.md] |
| M | GNN (learned, 3 seeds) | 4823 | 0.0163 | 0.0989 | – | 0.0536 | 0.6983 | 0.7746 | 0.9720 | [paper/tables/t4_pareto_M.md] |
| L | block 1 (exact) | 24 | 1.23e+04 | 0 | 0 | 0 | 1 | 1 | 1 | [paper/tables/t4_pareto_L.md] |
| L | block 3, correction on | 24 | 1.65e+03 | 0.0280 | 0.0286 | 0.0079 | 0.9410 | 0.9347 | 0.9982 | [paper/tables/t4_pareto_L.md] |
| L | production block 5, correction on | 24 | 566 | 0.0315 | 0.0359 | 0.0135 | 0.9344 | 0.9319 | 0.9979 | [paper/tables/t4_pareto_L.md] |
| L | block 5, correction off | 24 | 638 | 0.1011 | 0.1141 | 0.0217 | 0.7710 | 0.9767 | 0.9870 | [paper/tables/t4_pareto_L.md] |
| L | block 11, correction on | 24 | 164 | 0.0854 | 0.0954 | 0.0409 | 0.8317 | 0.8183 | 0.9895 | [paper/tables/t4_pareto_L.md] |
| L | U-Net (learned, 3 seeds) | 1927 | 0.00652 | 0.0810 | – | 0.0377 | 0.8122 | 0.8254 | 0.9916 | [paper/tables/t4_pareto_L.md] |
| L | FNO (learned, 3 seeds) | 1927 | 0.00541 | 0.1198 | – | 0.0729 | 0.7132 | 0.5531 | 0.9735 | [paper/tables/t4_pareto_L.md] |
| L | ViT (learned, 3 seeds) | 1927 | 0.0141 | 0.1586 | – | 0.0973 | 0.6046 | 0.7348 | 0.9529 | [paper/tables/t4_pareto_L.md] |
| L | GNN (learned, 3 seeds) | 1927 | 0.0658 | 0.1416 | – | 0.0738 | 0.6321 | 0.7041 | 0.9604 | [paper/tables/t4_pareto_L.md] |

(i) The production targets approximate the exact map well: the blocking error is rel-L2 0.0291 at M and 0.0315 at L
with Spearman 0.998 [paper/tables/t4_pareto_M.md; paper/tables/t4_pareto_L.md], so a model's error against its
training target and against the exact map differ little — the U-Net's seed-1 rel-L2 against the exact map, 0.051 at
M and 0.080 at L [docs/status/latest.md], equals its three-seed mean against the production target, 0.051 and 0.081
[paper/tables/baselines_sml.md]. (ii) Omniscape's artefact correction matters more than the block size: block 3
without correction (0.1105) is worse than block 7 with it (0.0983) at M, and block 5 without correction (0.1011)
worse than block 11 with it (0.0854) at L [paper/tables/t4_pareto_M.md; paper/tables/t4_pareto_L.md]. (iii) The
learned models occupy a different part of the frontier rather than dominating it: at M the U-Net's 0.051 lies
between the production block-3 solver (0.029 at 111 s) and block 7 (0.098 at 25.5 s) in error but at 1–16 ms per
landscape; at L its 0.080 is comparable to block 11 (0.085 at 164 s) at 5–66 ms [docs/status/latest.md;
paper/tables/t4_pareto_L.md]. Inference costs 1.09 / 1.47 / 2.05 / 16.3 ms per landscape at M and
6.52 / 5.41 / 14.1 / 65.8 ms at L for U-Net / FNO / ViT / GNN (converted from the seconds in the source); the ViT
reaches 0.0942 at M and 0.1586 at L against the exact map, and the learned models' Spearman stays ≥ 0.972 at M and
≥ 0.953 at L, close to the block-7 and block-11 solvers (0.9845, 0.9895) [paper/tables/t4_pareto_M.md;
paper/tables/t4_pareto_L.md]. A practitioner who needs rel-L2 < 0.03 still needs the solver; one who needs hundreds
of maps at rel-L2 ≈ 0.05–0.08 does not.

## 7.3 Data scaling at S (F6)

The WP4 ablation trains U-Net and FNO on T1 at S with n ∈ {1,000; 5,000; 20,000} landscapes, in a fixed-epoch regime
(30 epochs on the subset) and a fixed-step regime (≈ the optimisation steps of the official run), seed 1, and
compares with the official run on 61,577 landscapes [docs/wp4_data_scaling.md; paper/tables/wp4_data_scaling.md].

| model | n train | fixed-epoch rel-L2 | fixed-step rel-L2 (epochs) |
|---|---|---|---|
| U-Net | 1,000 | 0.496 | 0.368 (88) |
| U-Net | 5,000 | 0.316 | 0.139 (143) |
| U-Net | 20,000 | 0.188 | 0.103 (94) |
| U-Net | 61,577 (official) | 0.111 | — |
| FNO | 1,000 | 0.575 | 0.438 (39) |
| FNO | 5,000 | 0.357 | 0.298 (54) |
| FNO | 20,000 | 0.243 | 0.246 (36) |
| FNO | 61,577 (official) | 0.198 | — |

[paper/tables/wp4_data_scaling.md]

At a fixed step budget the U-Net saturates in data early — 20,000 landscapes give 0.103 and 5,000 give 0.139 against
0.111 for the official run on 61,577 — so the official 30-epoch protocol at S is budget-limited rather than
data-limited for the U-Net, whereas the FNO keeps improving with data in both regimes (0.438 → 0.298 → 0.246 → 0.198)
and is data-limited at S. Fixed-epoch training on small subsets understates both models by 1.3–2.3× rel-L2 at
1,000–5,000 landscapes, so the regime must be stated when quoting data efficiency [docs/wp4_data_scaling.md]. The
ablation does not by itself explain the S → M → L error growth of §7.1, since fixed-step rows at M and L were not run
[docs/wp4_data_scaling.md].

## 7.4 Scale transfer: zero-shot XL/XXL and the scale-aware target (F4)

Models trained at L were evaluated at XL (1024²) and XXL (2048²) without fine-tuning, with the official configuration
("zero-shot", 3 seeds) and with a variant whose training target is divided by a scale factor computed from the inputs
and the evaluation tier only — the Omniscape radius ratio for T4, the valid-pixel count for T1 ("scale-aware",
seed 1; no XL/XXL data enters training or the inverse transform) [paper/tables/scale_transfer.md;
docs/status/latest.md]. Rel-L2 on test_id:

| task | model | L zero-shot | XL zero-shot | XL scale-aware | XXL zero-shot | XXL scale-aware |
|---|---|---|---|---|---|---|
| T4 | U-Net | 0.081 ± 0.001 | 0.515 ± 0.002 | 0.189 | 0.749 ± 0.002 | 0.312 |
| T4 | FNO | 0.120 ± 0.001 | 0.532 ± 0.000 | 0.162 | 0.765 ± 0.001 | 0.201 |
| T4 | ViT | 0.159 ± 0.004 | 0.538 ± 0.000 | 0.203 | — | — |
| T4 | GNN | 0.142 ± 0.000 | 0.518 ± 0.002 | 0.223 | 0.748 ± 0.001 | 0.341 |
| T1 | U-Net | 0.397 ± 0.011 | 1.250 ± 0.421 | 0.957 | 4.425 ± 3.659 | 0.987 |
| T1 | FNO | 0.361 ± 0.024 | 0.707 ± 0.056 | 0.572 | 1.502 ± 0.387 | 0.671 |
| T1 | ViT | 0.648 ± 0.033 | 0.768 ± 0.006 | 0.656 | — | — |
| T1 | GNN | 1.067 ± 0.026 | 1.325 ± 0.064 | 0.796 | 2.174 ± 0.165 | 0.824 |

[paper/tables/scale_transfer.md]; ViT has no XXL rows in that table.

Zero-shot transfer fails on magnitude in a regular way for T4: every model lands at rel-L2 ≈ 0.52 at XL and ≈ 0.75
at XXL, which equals 1 − r_L/r_tier, the fraction of the current magnitude that the larger Omniscape radius adds and
an L-trained model cannot know about [docs/status/latest.md]. Removing that factor from the target recovers T4 to
0.16–0.22 at XL and 0.20–0.34 at XXL [docs/status/latest.md] — still well above in-tier errors, but no longer
dominated by a known scale factor. For T1 the FNO also benefits (0.707 → 0.572 at XL, 1.502 → 0.671 at XXL), whereas
the U-Net and GNN stay near rel-L2 0.8–1.0 at both tiers — their receptive field, not the magnitude, is the limit —
and the ViT's structural problem is unchanged [docs/status/latest.md; paper/tables/scale_transfer.md]. Rankings
survive what magnitudes do not: for the zero-shot T4 U-Net, Spearman is 0.992 at L, 0.946 at XL and 0.904 at XXL and
top-5 % IoU 0.812, 0.596 and 0.505 while rel-L2 goes 0.081 → 0.515 → 0.749; the FNO keeps Spearman
0.973 → 0.956 → 0.941; and the scale-aware variant leaves every Spearman value where the zero-shot run put it (T4
U-Net XL 0.946 for both; T4 FNO XXL 0.941 vs 0.940) [paper/tables/scale_transfer.md; docs/status/latest.md]. The one
genuinely unstable case is the zero-shot T1 U-Net at XXL, rel-L2 4.425 ± 3.659 and Spearman 0.461 ± 0.034
[paper/tables/scale_transfer.md]. A surrogate trained at one resolution can therefore still *rank* locations at a
larger one, but its absolute currents must be rescaled or re-trained.

## 7.5 OOD degradation at the training tier (T3, F7)

Table T3 gives rel-L2 on the three in-tier test splits (and the published-surface set at S) and the ratios to
`test_id`; `test_ood` holds the held-out resistance table (forest_bird) and the held-out contrast 10⁶, `ood_region`
the held-out biomes and realm, `published` the real tiles with published resistance surfaces [paper/tables/ood_degradation.md].

**Table T3 — rel-L2 per split, mean over 3 seeds, and ratios to test_id** [paper/tables/ood_degradation.md]

| task | tier | model | test_id | test_ood | ood_region | published | test_ood / id | ood_region / id | published / id |
|---|---|---|---|---|---|---|---|---|---|
| T1 | S | U-Net | 0.114 | 0.121 | 0.086 | 0.109 | 1.061 | 0.751 | 0.959 |
| T1 | S | FNO | 0.199 | 0.200 | 0.135 | 0.188 | 1.005 | 0.679 | 0.941 |
| T1 | S | ViT | 0.218 | 0.215 | 0.155 | 0.221 | 0.986 | 0.711 | 1.015 |
| T1 | S | GNN | 0.561 | 0.528 | 0.476 | 0.610 | 0.941 | 0.847 | 1.087 |
| T1 | M | U-Net | 0.212 | 0.210 | 0.160 | – | 0.994 | 0.756 | – |
| T1 | M | FNO | 0.248 | 0.245 | 0.176 | – | 0.988 | 0.707 | – |
| T1 | M | ViT | 0.419 | 0.413 | 0.360 | – | 0.986 | 0.858 | – |
| T1 | M | GNN | 0.849 | 0.823 | 0.814 | – | 0.969 | 0.959 | – |
| T1 | L | U-Net | 0.397 | 0.387 | 0.348 | – | 0.976 | 0.876 | – |
| T1 | L | FNO | 0.361 | 0.375 | 0.298 | – | 1.039 | 0.826 | – |
| T1 | L | ViT | 0.648 | 0.963 | 0.628 | – | 1.486 | 0.968 | – |
| T1 | L | GNN | 1.067 | 1.094 | 1.064 | – | 1.025 | 0.997 | – |
| T3 | S | U-Net | 0.111 | 0.114 | 0.073 | 0.126 | 1.024 | 0.655 | 1.138 |
| T3 | S | FNO | 0.253 | 0.234 | 0.170 | 0.289 | 0.927 | 0.674 | 1.145 |
| T3 | M | U-Net | 0.202 | 0.198 | 0.146 | – | 0.980 | 0.722 | – |
| T3 | M | FNO | 0.284 | 0.278 | 0.199 | – | 0.981 | 0.700 | – |
| T3 | L | U-Net | 0.379 | 0.357 | 0.321 | – | 0.941 | 0.848 | – |
| T3 | L | FNO | 0.347 | 0.319 | 0.274 | – | 0.921 | 0.790 | – |
| T4 | S | U-Net | 0.041 | 0.049 | 0.031 | 0.063 | 1.177 | 0.742 | 1.524 |
| T4 | S | FNO | 0.051 | 0.055 | 0.034 | 0.066 | 1.079 | 0.678 | 1.303 |
| T4 | S | ViT | 0.052 | 0.055 | 0.034 | 0.071 | 1.058 | 0.660 | 1.359 |
| T4 | S | GNN | 0.066 | 0.075 | 0.047 | 0.090 | 1.136 | 0.707 | 1.359 |
| T4 | M | U-Net | 0.051 | 0.060 | 0.037 | – | 1.176 | 0.732 | – |
| T4 | M | FNO | 0.079 | 0.085 | 0.054 | – | 1.085 | 0.682 | – |
| T4 | M | ViT | 0.094 | 0.098 | 0.065 | – | 1.039 | 0.686 | – |
| T4 | M | GNN | 0.099 | 0.105 | 0.069 | – | 1.064 | 0.696 | – |
| T4 | L | U-Net | 0.081 | 0.089 | 0.064 | – | 1.103 | 0.786 | – |
| T4 | L | FNO | 0.120 | 0.127 | 0.085 | – | 1.061 | 0.706 | – |
| T4 | L | ViT | 0.159 | 0.152 | 0.125 | – | 0.960 | 0.790 | – |
| T4 | L | GNN | 0.142 | 0.136 | 0.102 | – | 0.962 | 0.718 | – |

A held-out resistance table and contrast cost little at the training tier: `test_ood` ratios are 0.92–1.18 for
every model and task at S–L except the ViT on T1 at L (1.49, its structurally failing configuration); T4 is the most
sensitive family (1.04–1.18) [paper/ood_analysis.md]. Published real resistance surfaces are the hardest in-tier set
for T4 (S only: ratios 1.30–1.52, U-Net 1.52) while T1 and T3 stay within ±15 % of `test_id`; since T4 surrogates are
the ones that would run on practitioners' own surfaces, this is the number to quote beside the headline
[paper/ood_analysis.md]. The held-out-region split is *easier* than `test_id` for every model, task and tier (ratios
0.65–1.00, typically 0.70–0.85), which is not evidence of spatial robustness: the split is real-tile only, and the
held-out biomes (montane grasslands and shrublands, mangroves) and realm (Australasia) differ in composition — at S,
`ood_region` has a real share of 1.00 and a p90 contrast of 595 against 0.38 and 10,000 for `test_id`; at L the p90
contrasts are 1,000 and 10,000 [paper/ood_analysis.md]. Errors track landscape difficulty more than spatial novelty,
so `ood_region` is a spatial-leakage control (test regions never overlap training regions), not a stress test; any
robustness claim using it would need matched difficulty, and, as in §7.4, its ranking metrics degrade less than its
magnitudes [paper/ood_analysis.md].

## 8. Many-query demonstration (F5)

The case for a T4 surrogate is the study that needs many maps per landscape, not the single map. We ran the best T4
model at L (U-Net, seed 1; rel-L2 0.080 against the exact block-1 map on test_id) on 20 held-out real L tiles × 8
resistance tables (four expert tables, the v1.0 random draw and three extra random draws solved with the production
pipeline, QC 100 %), 160 maps in all, and asked whether the study-level conclusions a practitioner would draw from the
surrogate match those drawn from the solver [docs/wp7_demo.md].

| conclusion | solver route | model route | agreement |
|---|---|---|---|
| stability of the top-5 % regions across tables (mean pairwise IoU) | 0.463 | 0.458 | mean abs. difference of the IoU matrices 0.019 |
| consensus core (top-5 % in ≥ 75 % of tables), fraction of valid pixels | 0.0357 | — | IoU model-vs-solver 0.825 (median 0.843) |
| ranking of tables by effect vs the generic table | — | — | Spearman 0.991; same most-influential table in 100 % of tiles; top-3 overlap 0.98 |
| persistent pinch points (≥ 50 % of tables) | 5,586.6 per tile | — | recall 0.941, precision 0.657 (3-px tolerance) |
| per-map accuracy (context) | — | rel-L2 vs solver mean 0.054, worst table 0.100 | |
| total cost for 160 maps | 36.3 CPU-h (817 s per map, 1 core) | 11.8 s on one GPU (74 ms per map) + training once | ×11,077 |

[docs/wp7_demo.md]

Every study-level conclusion is reproduced — the stability estimate differs by 0.005, the consensus core overlaps at
IoU 0.825, the table ranking has Spearman 0.991 with the same most-influential table on every tile, persistent pinch
points are recovered with recall 0.941 — at ≈ ×11,000 lower cost after training once [docs/wp7_demo.md]. Per tile
[paper/tables/wp7_per_tile.md], the core IoU ranges from 0.674 (L_nea_b02_0401) to 0.943 (L_neo_b02_0303), the
ranking Spearman is 1.000 on 14 of 20 tiles and 0.964 on the other six, `top1_table_agree` holds on all 20, and
persistent-pinch recall is 0.872–0.998. The weak point is pinch-point *precision*: 0.657 on average and as low as
0.169 (L_afr_b07_0986) and 0.216 (L_afr_b07_0233) [paper/tables/wp7_per_tile.md] — the surrogate proposes more
persistent pinch points than the solver confirms, so a candidate list drawn from it should be solver-verified before
it becomes a decision map.

## What the benchmark separates

The four families fail in different places: the U-Net is strongest on T1 and T4 at S and M (T1 0.114 / 0.212; T4
0.041 / 0.051) but degrades fastest with tier, losing its T1 lead to the FNO at L (0.397 vs 0.361) and not
transferring on T1 at all (rel-L2 ≈ 1 even with the scale-aware target); the FNO is data-limited at S but has the
best T1 result at L (0.361), the highest T1 Spearman at every tier (0.967 / 0.959 / 0.945) and the best transfer
(scale-aware T4 0.162 at XL and 0.201 at XXL; the only T1 model below rel-L2 0.7 at XXL, 0.671); the ViT official
configuration is competitive at S (T1 0.218, T4 0.052) and resolution-inappropriate above it (T1 0.419 ± 0.123 at M
and 0.648 at L with top-5 % IoU 0.146, and the one case where a held-out table costs 49 %); and the GNN is far behind
on T1 at every tier (0.561 / 0.849 / 1.067) but competitive on the locally windowed T4 (0.066 / 0.099 / 0.142, ahead
of the ViT at L), at 6–10× the U-Net's training cost and roughly a tenth of its speed-up [paper/tables/baselines_sml.md;
paper/tables/scale_transfer.md; paper/tables/ood_degradation.md; docs/wp4_data_scaling.md; docs/status/latest.md].
No single family wins on accuracy, scale robustness, OOD robustness and cost at once; that trade-off, rather than
any one number, is the result.

## Sources used

- paper/tables/baselines_sml.md — T2, companion table, §7.1, closing paragraph
- paper/tables/t4_pareto_M.md, paper/tables/t4_pareto_L.md — solver and learned rows of Table 7.2, §7.2
- docs/status/latest.md ("Phase 10-full — final summary") — seed-1 learned errors quoted in §7.2 (i) and (iii), ms/landscape ranges, 1 − r_L/r_tier observation, scale-aware ranges, GNN characterisation
- paper/tables/wp4_data_scaling.md, docs/wp4_data_scaling.md — §7.3
- paper/tables/scale_transfer.md — §7.4, closing paragraph
- paper/tables/ood_degradation.md, paper/ood_analysis.md — T3, §7.5
- docs/wp7_demo.md, paper/tables/wp7_per_tile.md — §8
- docs/tables/gpu_usage.md — GPU budget in the preamble

Not sourced: the non-source-pixel rel-L2 (`ns_rel_l2`) of the learned models against the block-1 map is not
available in the regenerated Pareto tables and is shown as "–".
