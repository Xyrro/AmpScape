# Discussion, limitations, ethics and maintenance

<!-- Draft for Phase 12 §9 (plus the discussion half of §7–8). Every number is copied from a repository file and
tagged [source]. Reference labels [n] are those of paper/sections/related_work.md. -->

## What the results say: a speed–accuracy–robustness trade-off

**Speed.** On the omnidirectional task the surrogates are 10³–10⁵× faster than the solver: median T4 speed-ups run from
6,604× (GNN, M) to 167,020× (U-Net, S), against 48–773× on T1 and 219–374× on T3, where a single pairwise solve is
already cheap [paper/tables/baselines_sml.md] — a median 0–63 s per tier, against 52 s (S) to 10,212 s (XXL) for a T4
landscape [paper/tables/dataset_statistics.md]; the U-Net returns a T4 map in 1 ms at M and 5 ms at L
[docs/status/latest.md].

**Accuracy.** Omnidirectional current is the easy direction: U-Net T4 rel-L2 is 0.041 / 0.051 / 0.081 at S / M / L
(three-seed means) [paper/tables/baselines_sml.md]; against the exact block-1 map it sits at 0.051 (M) and 0.080 (L)
where the production block-3 and block-5 solvers sit at 0.029 and 0.032 [paper/tables/t4_pareto_M.md;
paper/tables/t4_pareto_L.md] — the cheapest point on the T4 error–cost front, not the most accurate. Pairwise current
is the hard direction: U-Net T1 error grows 0.114 → 0.212 → 0.397 from S to L, FNO 0.199 → 0.361, the GNN sits at
0.561–1.067, and T3 follows T1 (U-Net 0.111 → 0.379) [paper/tables/baselines_sml.md]. In-distribution T4 at S is
near-solved; the difficulty is in T1, scale transfer and the published tiles [DECISIONS.md, 2026-09-24].

**Robustness.** At the training tier a held-out table and contrast cost little — `test_ood` ratios 0.92–1.18 for every
model and task except the ViT on T1 at L (1.49), T4 the most sensitive (1.04–1.18) — while published real resistance
surfaces are the hardest in-tier set for T4 (1.30–1.52 at S) [paper/ood_analysis.md]. Zero-shot scale transfer of
L-trained models fails on magnitude: T4 rel-L2 ≈ 0.52 at XL and ≈ 0.75 at XXL for every model, equal to
1 − r_L/r_tier; T1 U-Net reaches 4.425 ± 3.659 at XXL [paper/tables/scale_transfer.md; docs/status/latest.md].
Rankings survive where magnitudes fail: zero-shot T4 Spearman at XL is 0.937–0.956 (GNN 0.928)
[paper/tables/scale_transfer.md], and in-tier rankings degrade less than magnitudes [paper/ood_analysis.md]. The
scale-aware target (T4 currents scaled by 64/r_tier, T1 by √(N_valid/512²)) removes most of the T4 magnitude error —
U-Net 0.515 → 0.189 at XL, 0.749 → 0.312 at XXL; FNO 0.162 / 0.201 — helps the FNO on T1 (0.707 → 0.572), leaves the
U-Net on T1 near rel-L2 1 (0.957 / 0.987) and changes no ranking [paper/tables/scale_transfer.md;
docs/status/latest.md]. It isolates one cause of the failure rather than fixing it: seed-1 only, with a T4 residual
(0.16–0.34) well above the in-tier 0.08–0.12.

## What the benchmark separates, and what it does not yet test

The tasks separate families along interpretable axes: the GNN's multi-scale graph does not resolve long-range pairwise
flow (T1 L 1.067) but is competitive on the locally windowed T4 (0.142 vs ViT 0.159 at L), the reverse of the
convolutional models' strengths [docs/status/latest.md; paper/tables/baselines_sml.md]; data scaling separates budget
from data limits — at the official step budget the U-Net saturates by 20,000 landscapes at S (0.103 vs 0.111 on 61,577)
while the FNO keeps improving (0.438 → 0.298 → 0.246 → 0.198) [docs/wp4_data_scaling.md]; and the block-size rows put a
non-learned approximation on the same cost axis [paper/tables/t4_pareto_M.md]. Not yet tested: a multiscale operator of
the HANO/MgNO family [41, 42] [docs/REVIEW_ADDENDUM_2026-09.md; docs/status/latest.md]; training at XL (XL rows are
transfers of L models [DECISIONS.md, 2026-09-24]); fixed-step training at M/L, the direct test of how much S → L error
growth is budget rather than scale [docs/wp4_data_scaling.md]; and the warm-start metric for T1/T3 on learned
baselines. That track is implemented (AMG-PCG iterations and wall time to the reference residual from the predicted
voltage vs a zero start, `scripts/warm_start_eval.jl`, same preconditioner and matrix as the stored `cg_baseline`)
[DECISIONS.md, 2026-09-06, 2026-09-13] but was run only on the non-learned coarsen ×4 baseline at S on the dev build
(70 systems: iterations 11 → 10, median reduction 6.9 %, time 28 → 22 ms; no gain on the 68 published-tile systems,
14 → 14), where PCG converges in ≈ 11 iterations and leaves little headroom; it becomes informative at XL/XXL with a
learned voltage [docs/phase_09_report.md]. No full-baseline run carries it [docs/tables/baselines_full.md].

## Implications for practice

The surrogates pay where the solver is called many times on the same landscapes — sensitivity to resistance
parameters, scenario comparison, resistance optimisation [15, 16, 17]. WP7 is the concrete case: on 20 held-out real L
tiles × 8 tables the U-Net reproduced the solver's study-level conclusions — top-5 % stability across tables 0.458 vs
0.463, consensus-core IoU 0.825, table ranking Spearman 0.991 with the same most-influential table on every tile,
persistent pinch-point recall 0.941 — in 11.8 s on one GPU against 36.3 CPU-h (≈ ×11,000 after training once)
[docs/wp7_demo.md]. Its weak point is pinch-point precision, 0.657 at 3 px and as low as 0.169 on one tile
[docs/wp7_demo.md; paper/tables/wp7_per_tile.md]: the surrogate finds the solver's pinch points and adds spurious ones;
hence screen with the surrogate and verify every map that enters a decision with the solver. For T1–T3 the practical
number is not wall-clock replacement — a pairwise solve takes seconds [paper/tables/dataset_statistics.md] — but the
operator-learning difficulty itself and, for applied use, the iterations saved when a prediction warm-starts the
solver [paper/outline.md].

## Limitations

1. **Resistance tables are structural proxies, not ecological truth.** Class ordering and term structure follow the
   literature; the numeric values are AmpScape's own and not species-calibrated [docs/dataset_card.md].
2. **A faster approximation does not reduce resistance-surface uncertainty.** Surfaces are uncertain inputs [14, 17];
   speed lets a user explore that uncertainty (WP7), it does not remove it.
3. **Learned models degrade OOD and across scale** (published surfaces +30–52 % on T4 at S; zero-shot transfer fails
   on magnitude) [paper/ood_analysis.md; paper/tables/scale_transfer.md]; final decision maps should be solver-verified.
4. **T4 targets carry a quantified blocking approximation.** Block = largest odd ≤ radius/10 (S 1, M 3, L 5, XL 11,
   XXL 25). Against block 1 the production M target deviates by 0.029 mean rel-L2 on the 1,000-sample reference (worst
   0.254; top-5 % IoU 0.945, pinch recall 0.953), with 4.7 % of samples above 5 % — fragmented landscapes at contrast
   ≥ 10⁴, real tiles never above 8 %; the L target by 0.028 mean, 0.058 worst, 2 of 60 above 5 %; block 1 costs 22×
   production [docs/t4_fidelity.md]. T4 leaderboard metrics at M and L are therefore computed against the block-1
   subsets; at XL/XXL only the production target exists and the M/L figures are the stated bound [docs/t4_fidelity.md].
   The best model's M error (0.051) exceeds the label deviation (0.029), but not by a wide margin
   [paper/tables/t4_pareto_M.md].
5. **Resolution and size are confounded in the scale split.** Pixel size (100 m / 100 m / 200 m / 500 m / 1 km), raster
   size (128² … 2048²) and the Omniscape radius (raster/8 in pixels, hence 1.6 → 256 km) co-vary across tiers; only
   S → M changes one factor at a time, so from M upward `test_ood_scale` mixes pixel-count extrapolation, coarser pixels
   and a larger physical window [docs/addendum_WP5_report.md §1; docs/dataset_card.md]. A controlled 2×2 probe set
   separating the axes (256²/512² × 100 m/200 m at a fixed 12.8 km window; 360 landscapes) is published under `aux/`
   [docs/addendum_WP5_report.md §3, §5; CHANGELOG.md, 2026-09-21] but not yet evaluated: no probe-cell results exist in
   this release [docs/addendum_WP5_report.md].
6. **XXL footprints overlap finer-tier training cells.** XXL is test-only; its 32 tiles (2,048 km) cover ≈ 90 % of land,
   so its scale split isolates resolution, not spatial novelty; `test_ood_scale_strict` (6 XXL tiles sampled inside
   test_id cells, with a geometric check that no train/val tile of any tier intersects them) isolates both, and XL tiles
   are cell-assigned and overlap-free by construction [docs/dataset_card.md; docs/addendum_WP5_report.md §2].
7. **The held-out-region split is easier by composition** (ratios 0.65–1.00; real-tile only, p90 contrast 595–1,000
   vs 10,000 on `test_id`). It is a spatial-leakage control, not a stress test [paper/ood_analysis.md].
8. **The ViT official config is resolution-inappropriate above S** (fixed across tiers: patch 4, dim 192, depth 6, a
   32×32 positional embedding interpolated to 128×128 at L, attention over 16,384 tokens); training did not diverge,
   the degradation is structural, and the number stands with this note [DECISIONS.md, 2026-09-24].
9. **T4 scale transfer crosses an operator change**: the Omniscape radius doubles above L (64 → 128 → 256 px, block
   5 → 11 → 25), so zero-shot T4 transfer is across operators as well as scales [docs/t4_fidelity.md; docs/status/latest.md].
10. **Nothing is trained at XL.** The XL train/val split exists (v1.0.2: train 880 / val 131 / test_id 2,335) but every
    XL and XXL row is a transfer of an L-trained model, so no result depends on it [docs/dataset_card.md; CHANGELOG.md;
    DECISIONS.md, 2026-09-25].
11. **Seed-1-only studies**: the scale-aware variants, WP4, the exact-reference Pareto rows and WP7
    [paper/tables/scale_transfer.md; paper/tables/wp4_data_scaling.md; paper/tables/t4_pareto_M.md; docs/wp7_demo.md];
    the official S/M/L rows use three seeds [paper/tables/baselines_sml.md].
12. **Domain-metric thresholds are not validated against ecological outcomes**; they are comparative scores between
    models [docs/dataset_card.md].

## Claims the paper does not make

- Not "Circuitscape is slow": a pairwise solve takes seconds at every tier [paper/tables/dataset_statistics.md]; the
  documented cost is omnidirectional and many-query [18–23].
- Not "exact solvers are not differentiable": analytical sensitivities [30] and differentiable, GPU-accelerated
  connectivity libraries [31] exist; the case for a surrogate is amortised cost [paper/sections/related_work.md].
- Not "no prior work on where to intervene": Barrier Mapper, Pinchpoint Mapper, Zonation, Marxan Connect, GECOT and
  ConScape sensitivities [24–30] exist and AmpScape does not replace them [paper/sections/related_work.md].
- No number from the reviewer's toy pilot (own re-implementation, r = 12 px, CPU only); it motivated WP1–WP7 and is
  never cited as a project result [docs/REVIEW_ADDENDUM_2026-09.md].

## Ethics and intended use

No personal data: real tiles derive from public land-cover and terrain products at ≥ 100 m, and no protected-area
(WDPA) polygons are used [docs/dataset_card.md]. Every stored covariate comes from a source whose licence permits
redistribution of derived rasters — ESA WorldCover, HydroRIVERS, gHM and RESOLVE (CC BY 4.0), Copernicus DEM GLO-30
(with its notices), the published-resistance rasters (CC BY 4.0, CC0) — and the data are released under CC BY 4.0 with
the attribution block and Copernicus notices verbatim [docs/licenses.md; docs/dataset_card.md]. One point is stated as
unresolved: GRIP4 is CC0 by its publisher and CC BY 4.0 in secondary catalogues; we attribute under the stricter reading
and store only non-reversible distance and class rasters; OpenStreetMap (ODbL) is not used [docs/licenses.md]. Intended
use is screening — many-query exploration, model comparison, operator-learning research — not final decisions.

## Maintenance

The current release is `1.0.2` on `Xirro/AmpScape`; `v1.0` is the data revision and the later tags are metadata-only
with identical data files [docs/dataset_card.md; CHANGELOG.md]. Changes are logged in `CHANGELOG.md`, decisions in
`DECISIONS.md`. Regeneration is scripted from the frozen `v1.0-pipeline` tag (bitwise on the same CPU model, ≤ 1.2e-9
relative across models [docs/dataset_card.md]) and the post-mortem lists the runbook changes a reproducer needs
[docs/generation_postmortem.md]. Auxiliary evaluation sets and baseline results are on the Hub under `aux/` (20.5 GB)
[docs/dataset_card.md; docs/status/latest.md]. CI runs the test suite, a licence-consistency test over the source
manifest and a parse test over all 75 scripts [CHANGELOG.md; docs/licenses.md; docs/status/latest.md]; issues are
tracked on GitHub `Xyrro/AmpScape` (MIT) and a DOI will be minted at submission [paper/outline.md]. Compute: 16,552
core-hours for generation and the precision pass [docs/dataset_card.md], 430.1 GPU-hours for the baselines
[docs/status/latest.md].

## Sources used

- paper/outline.md — framing rules, limitation and claims-to-avoid lists, warm-start framing, DOI/GitHub
- paper/tables/baselines_sml.md — S/M/L rel-L2, speed-ups, seed counts
- paper/tables/ood_degradation.md — per-split rel-L2 (summarised in paper/ood_analysis.md)
- paper/tables/scale_transfer.md — zero-shot and scale-aware XL/XXL rows, Spearman, seed counts
- paper/tables/t4_pareto_M.md, paper/tables/t4_pareto_L.md — exact-reference errors and solver costs
- paper/tables/wp4_data_scaling.md, docs/wp4_data_scaling.md — data-scaling rows and findings
- paper/tables/wp7_per_tile.md, docs/wp7_demo.md — many-query agreement, per-tile precision, cost
- paper/tables/dataset_statistics.md — solve times per tier
- paper/ood_analysis.md — OOD ratios, split composition, rankings-vs-magnitudes
- docs/status/latest.md — inference times, GNN finding, GPU-hours, CI script count, operator-change note
- docs/t4_fidelity.md — block rule, radii, measured block-1 deviations, cost ratio
- docs/dataset_card.md — tables as proxies, tiers, XXL overlap and strict subset, scale caveat, C3, licences, no personal data, versions, reproducibility, metrics caveat, core-hours
- docs/generation_postmortem.md — runbook for reproducers
- docs/licenses.md — source licences, GRIP4 ambiguity, OSM/WDPA not used, licence test
- DECISIONS.md — T4-at-S finding, ViT config note, XL-by-transfer, acceleration track, C3 check
- CHANGELOG.md — 1.0.1 / 1.0.2 contents, CI tests, WP5 probe set under aux/
- docs/REVIEW_ADDENDUM_2026-09.md — WP6 optional, pilot numbers never cited, WP8 framing
- docs/addendum_WP5_report.md — §1 tier table and confound statement, §2 XXL/XL geographic independence, §3/§5 probe-set design and build (no evaluation results)
- docs/phase_09_report.md — acceleration-track definition and the coarsen-baseline warm-start numbers at S (dev build, published set)
- docs/tables/baselines_full.md — absence of an acceleration column on the full baselines
- paper/sections/related_work.md — reference labels [14]–[31], [41], [42]
