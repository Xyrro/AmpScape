# AmpScape — manuscript outline (Phase 12, drafted 2026-10-02)

Working title: **AmpScape: a benchmark for learned surrogates of circuit-theoretic landscape connectivity**

Target: NeurIPS 2027 Datasets & Benchmarks track (primary). Fallbacks: a data-descriptor journal (*Scientific
Data*) with the baselines moved to a companion methods paper, or an ecological-informatics / methods journal
(*Methods in Ecology and Evolution*, *Ecological Informatics*) with the operator-learning content shortened.
D&B checklist items: Hub hosting (`Xirro/AmpScape`), licence file (`docs/licenses.md`), datasheet (dataset card),
Croissant with RAI fields (validated), maintenance plan, DOI (to obtain at submission), code (GitHub `Xyrro/AmpScape`).

Framing rules carried from the review addendum (WP8): the headline is a **speed–accuracy–robustness trade-off**, not
"surrogates beat solvers"; the motivation is the *many-query* use of Omniscape and the documented cost of
omnidirectional runs; T1–T3 are included as an operator-learning challenge with the solver-acceleration metrics as
their practically relevant number; every number in the paper traces to a `docs/tables/` file.

## 1. Introduction (≈ 1 page)
- Two-tier motivation. (a) Omnidirectional connectivity (Omniscape) is expensive at the resolutions practitioners use
  — cite the documented runs (verified sources only; see `paper/sections/related_work.md`) and our own measured solve
  times per tier (`docs/tables/dataset_statistics.md`). (b) The *many-query* pattern — sensitivity analysis over
  resistance parameters, scenario comparison, resistance-surface optimisation — multiplies that cost; a single
  full-raster pairwise solve is cheap (state our timings plainly), so the acceleration case for T1–T3 is iterations
  saved as a warm start, not wall-clock replacement.
- What a benchmark needs that the PDE-surrogate literature does not provide: real-world coefficient fields with
  contrast up to 10⁶, singular per-sample sources/sinks instead of f ≡ 1, grids to 2048², systematic OOD splits, and
  decision-relevant metrics (pinch points, corridors, top-k masks).
- Contributions (numbered): the dataset (tiers, tasks, counts); the reference-solver protocol with measured fidelity
  (T4 blocking approximation quantified against block-1 references; precision pass with per-row residuals); the
  evaluation harness and metrics; baselines with three seeds and the scale-transfer and scale-aware-target studies;
  the many-query demonstration (WP7).
- Headline sentence (to be finalised with the results): at S/M/L the U-Net reaches rel-L2 0.04–0.08 on T4 at
  10³–10⁵× the solver speed, degrades to ≈ 0.4 on T1 at L and to ≈ 1 on zero-shot scale transfer to XL, while
  ranking metrics survive better than magnitudes (`docs/tables/baselines_full.md`, `docs/status/latest.md`).

## 2. Related work (≈ 0.75 page) — `paper/sections/related_work.md`
- Circuit theory for connectivity (McRae; Circuitscape 5; Omniscape) as ground truth.
- ML *for* connectivity (adjacent, not surrogate) and where-to-intervene tools (Barrier Mapper, Zonation, Marxan
  Connect, ConScape sensitivities) — never claim "no prior work on where to intervene".
- Learned surrogates for elliptic / Laplacian problems (FNO Darcy, PDEBench, HANO, MgNO, dilated-convolution and
  LOD multiscale neural operators) with the precise delta.
- Benchmark design modelled on PGLearn, with the asymmetry stated (OPF non-convex with real-time needs; this problem
  linear and costly only through repetition).
- Differentiability: exact connectivity solvers have closed-form sensitivities (2026 ConScape preprint) — never
  claim differentiability is unique to neural surrogates.

## 3. Problem and tasks (≈ 1 page) — `paper/sections/tasks_metrics.md`
- Resistance grids, 8-neighbour conductance network, Circuitscape conventions.
- T1 pairwise/advanced current maps (T1W wall-to-wall, T1R regions), T3 advanced mode with grounds, T4 Omniscape
  cumulative current (block-centred, block ≤ radius/10, measured against block-1 references).
- Inputs/targets as tensors; the log target transform; what is and is not predicted.

## 4. Dataset construction (≈ 1.5 pages) — `paper/sections/dataset_generation.md`
- Landscapes: synthetic families and real tiles (sources, licences), resistance tables as structural proxies
  (own numeric values, literature-informed), source configurations.
- Reference solver settings (CHOLMOD double precision; rescue path; post-run precision pass with per-row residuals
  and the QC exclusions), Omniscape geometry per tier, compute used, incidents that affect interpretation
  (`docs/generation_postmortem.md`).
- Statistics (figure): contrast, biome/realm, NoData, solve-time distributions, per-tier storage.
- Formats, subsets (mini ⊂ lite ⊂ core ⊂ full), Croissant, versions (v1.0 data; 1.0.1 and 1.0.2 metadata).

## 5. Splits and OOD design (≈ 0.75 page) — `paper/sections/splits_ood.md`
- Spatial macro-cells, seed families, nested subsets; OOD sets (region, table, contrast, scale, synthetic→real,
  published tiles, strict scale subset); XL amendment C3 and its v1.0.2 correction; the XXL overlap caveat.

## 6. Metrics and evaluation protocol (≈ 0.5 page) — `paper/sections/tasks_metrics.md`
- Pixel, domain (top-k IoU, pinch-point recall, corridor dice, Spearman), non-source-pixel variants, physics checks,
  efficiency/speed-up, T4 exact-reference surface, batch-1 inference at XL/XXL, harness and prediction format.

## 7. Baselines and results (≈ 2 pages) — `paper/sections/baselines_protocol.md`, results tables pending
- Official configs (U-Net, FNO, ViT, GNN), protocol (30 epochs, 3 seeds, 2-h resumable legs), non-learned baselines
  (coarsen, block-size Pareto).
- Results: S/M/L table (mean ± std over 3 seeds; `docs/tables/baselines_full.md`); T4 error–cost Pareto at M and L
  (`docs/tables/t4_pareto_{M,L}.md`); data-scaling (WP4); scale transfer XL/XXL zero-shot and the scale-aware-target
  variant; OOD degradation per split; GNN (pending).
- Headline figure: error vs tier per model/task with the solver cost axis — the speed–accuracy–robustness trade-off.

## 8. Many-query demonstration (≈ 0.5 page) — `docs/wp7_demo.md`
- 20 held-out real L tiles × 8 tables: study-level conclusions from the surrogate vs the solver (stability, consensus
  core, table ranking, persistent pinch points), with the cost comparison and the weakest point (pinch precision).

## 9. Limitations, ethics, maintenance (≈ 0.75 page)
- Limitations to state: resistance tables are structural proxies, not ecological truth; a faster approximation does
  not reduce resistance-surface uncertainty; learned models degrade OOD and final decision maps should be verified
  with the solver; T4 targets carry a quantified blocking approximation; the resolution-versus-size confound (WP5)
  in the scale split; the XXL footprint overlap; zero-shot scale transfer fails on magnitude; the ViT official config
  is resolution-inappropriate above S.
- Claims to avoid: "Circuitscape is slow" without qualification; "exact solvers are not differentiable"; "no prior
  work on where to intervene"; citing pilot numbers as project results.
- Ethics: no personal data; real tiles from open global layers with licences listed; intended use (screening, not
  final decisions). Maintenance: versioned Hub revisions, CHANGELOG, issue tracker, re-generation scripts.

## Appendix
- Datasheet (dataset card), generation post-mortem, precision-pass tables, full per-split tables, hyper-parameters,
  compute (GPU-hours per phase), licence texts, Croissant snippet, split-list and index schema.

## Figure and table plan (regenerated by `scripts/paper_figures.py`)
| id | content | source |
|---|---|---|
| F1 | dataset statistics panel (contrast, biome/realm, NoData, solve times, storage) | `scripts/dataset_stats_figures.py` → `docs/figures/dataset_stats_*.png` |
| F2 | T4 error vs cost at M and L (solver block sizes + learned models) | `docs/tables/t4_pareto_{M,L}.md` |
| F3 | error vs tier per model and task (S–M–L) with speed-up | `docs/tables/baselines_full.md` |
| F4 | scale transfer: L-trained models at XL (and XXL), zero-shot vs scale-aware target | `runs/full/*/results_transfer.json` → `docs/tables/scale_transfer.md` |
| F5 | WP7 many-query agreement and cost | `aux/wp7/demo_results.parquet`, `docs/wp7_demo.md` |
| F6 | WP4 data scaling at S (fixed-epoch vs fixed-step) | `docs/tables/baselines_full.md` → `paper/tables/wp4_data_scaling.md` |
| F7 | OOD degradation at the training tier (ratios to test_id) | `paper/tables/ood_degradation.md`, `paper/ood_analysis.md` |
| T1 | per-tier counts and sizes | `docs/tables/final_counts.json` |
| T2 | S/M/L baselines, mean ± std over seeds (test_id: `paper/tables/baselines_sml.md`; all splits: `paper/baselines.md`) | `docs/tables/baselines_full.md` |
| T3 | OOD degradation per split | `docs/tables/baselines_full.md` |
| T4 | GNN and scale-aware variant rows | `paper/tables/baselines_sml.md`, `paper/tables/scale_transfer.md` (complete 2026-10-04) |
