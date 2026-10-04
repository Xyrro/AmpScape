# Appendix notes — material moved out of the main-text sections

<!-- Collected 2026-10-04 while trimming paper/sections/*.md to NeurIPS D&B main-paper length. Every passage below
was removed or compressed in the main text and is reproduced here verbatim (numbers and inline source tags
unchanged) so that it is available for the appendix, the datasheet or the post-mortem. Headings name the source
section. -->

## From dataset_generation.md

### Index count note (§3.1)
The v1.0 index holds 920,372 configuration rows (920,347 QC-pass) [docs/tables/final_counts.json]; the 902 904 quoted in the post-mortem and changelog at tag time was a stale pre-audit count and was corrected on 2026-10-02 [docs/generation_postmortem.md; CHANGELOG.md].

### Layout and splits (original wording, §3.1)
`lite` (≈ 26 GB: 8 000 S + 2 400 M + 800 L landscapes, added in v1.0.1) [docs/dataset_card.md]. Real tiles are split by spatial macro-cells shared across tiers (equal-width 20° cells) and synthetic landscapes by seed family; XXL is test-only, and `test_ood_scale_strict` (≈ 6 XXL real tiles with zero overlap with any training tile) isolates spatial novelty from resolution transfer [docs/dataset_card.md].

### Release history (§3.1)
v1.0 (2026-09-23) is the data revision; v1.0.1 (2026-09-24) added `lite` as metadata only; **v1.0.2 (2026-09-26) is also metadata-only**: the XL amendment C3 share had been applied by macro-cell hash, which synthetic landscapes lack, so all synthetic XL train/val landscapes had landed in test_id (train 228, val 0, test_id 3,118). v1.0.2 restores a per-seed-family share, giving XL train 880, val 131, test_id 2,335, test_ood 254, ood_region 400, and rebuilds the split lists as unions over all tiers (the v1.0/1.0.1 lists held only the last published tier's ids; the per-tier index `split` column was always complete) [CHANGELOG.md; docs/dataset_card.md; docs/tables/final_counts.json]. Data files are identical across the three tags [docs/dataset_card.md].

### Reference solver: why CHOLMOD and not CG+AMG (§3.2)
All T1/T1W/T1R/T3 solves use Circuitscape `solver = cholmod` (direct, double precision) rather than CG+AMG, because in Circuitscape 5.17.1 the CG tolerance is hard-coded (`rtol = 1e-6`, accepted if the residual is < 1e-4) and not exposed [DECISIONS.md]. Graphs are 8-neighbour with average conductance, the software default, set explicitly and recorded per sample [DECISIONS.md]. The Kirchhoff residual is computed in Julia from full-precision voltages before the float32 cast; the QC threshold is 1e-6 (the double-precision floor), and one CHOLMOD iterative-refinement step on the reduced/collapsed system fires whenever the residual exceeds 1e-8 [DECISIONS.md]. CG+AMG is allowed only as an automatic, flagged memory fallback [docs/dataset_plan.md].

### Omniscape block-size fidelity study (§3.2)
T4 uses Omniscape 0.6.2 with `solver: cholmod`, `correct_artifacts: true`, `source_threshold: 0.0` and sources from inverse resistance above the 0.5 quantile [configs/solver/omniscape_reference.yaml; docs/t4_fidelity.md]. Since `block_size` is part of the method (targets are block centres, cost ∝ 1/block²), it is fixed by the rule *block = largest odd integer ≤ radius/10* [docs/dataset_plan.md]. The rule came from a 3-sample-per-cell study: against the exact block-1 map, block 3 at S deviated by 4.49 % mean / 7.60 % max relative L2 and block 5 at M by 2.00 % / 2.45 %, while coarsening XL 17→33 changed `cum_current` by 2.47 % / 2.93 % and XXL 33→65 by 9.46 % / 11.85 % (both rejected) [docs/t4_fidelity.md]. The ≈ 1 % target was an extrapolation and proved optimistic: the production M target deviates from the exact map by 3.1 % relative L2 on average (median 2.8 %; 200 synthetic landscapes; top-5 % IoU 0.95, pinch-point recall 0.95), and the full 1 000-sample M reference gives mean 0.029 with 4.7 % of samples above 5 % (11 % of synthetic, 1.4 % of real) [docs/t4_fidelity.md]. At L (block 5, 60 samples) the mean is 0.028 (max 0.058; 2 of 60 above 5 %); block 1 costs 6.7× (M) and 22× (L) the production solve [docs/t4_fidelity.md]. These block-1 references (`aux/t4_bs1_reference/`) are the official T4 evaluation surface at M and L [docs/t4_fidelity.md].

### Generation compute (§3.2)
Generation ran on Georgia Tech PACE-ICE (Slurm) from 2026-09-16 to 2026-09-22 (6.6 days; XL 20 h 51, XXL 10 h), followed by a 29 h precision pass [docs/generation_postmortem.md]. Total cost was 16 552 core-hours: generation 14 379 (S 2 061, M 1 692, L 5 713, XL 3 684, XXL 1 228), precision pass 1 249, audits 30, auxiliary sets and probes 893 [docs/generation_postmortem.md]; T4 is ≈ 90 % of solve cost [docs/dataset_plan.md]. Shards were validated, uploaded, sha256-verified and deleted locally in a streaming loop; scratch peaked at 215 GB of a 300 GB quota [docs/generation_postmortem.md].

### Post-run precision pass, full statement and per-tier table (§3.2)
After generation, every T1/T1W/T1R/T3 row that was above 1e-9, unmeasured (T1 rows with K ≥ 5 and T1R rows keep no per-pair voltages [docs/dataset_card.md]), CG+AMG-solved or QC-failed was re-solved pair by pair with CHOLMOD on the reduced system plus up to three refinement steps, and its true residual recorded (`residual_rel`; per-pair values in `solver_stats.resolved_post_run`; `solver_original` where the solver changed) [docs/dataset_card.md; docs/tables/precision_pass.md]. Table 3 summarises: 129,722 rows re-solved, 189 originally `cg+amg`, 3,861 rows left between 1e-9 and 1e-6 (recorded, kept), and 20 rows unable to reach 1e-6 in double precision, all synthetic at contrast ≥ 10⁴, flagged `residual_high` with `qc_pass = false` [docs/tables/precision_pass.md]. Failed T4 rows were re-run whole [CHANGELOG.md].

**Table 3. Precision pass per tier** [docs/tables/precision_pass.md].

| tier | rows re-solved | of which cg+amg → cholmod | residual after p50 / p90 / p99 / max | rows > 1e-9 | rows > 1e-6 (flagged) |
|---|---|---|---|---|---|
| S | 68,008 | 9 | 2.9e-13 / 3.4e-11 / 1.6e-09 / 5.0e-07 | 1,013 | 0 |
| M | 37,639 | 14 | 9.1e-13 / 1.9e-10 / 5.2e-09 / 1.4e-06 | 1,136 | 4 |
| L | 18,691 | 110 | 6.8e-12 / 4.9e-10 / 1.4e-08 / 1.5e-05 | 1,014 | 9 |
| XL | 4,774 | 47 | 6.9e-11 / 1.3e-09 / 4.3e-08 / 6.6e-06 | 551 | 5 |
| XXL | 610 | 9 | 2.7e-10 / 4.3e-09 / 2.0e-07 / 4.0e-05 | 147 | 2 |
| total | 129,722 | 189 | | 3,861 | 20 |

### Quality control, completion rule (§3.2)
A shard counts as solved only when the solver's completion marker exists, and finalize checks the exact planned sample and configuration set [DECISIONS.md]. Each tier was audited on the Hub against the plan (sha256, sample ids, configurations, index rows) before completion [docs/dataset_card.md].

### Incidents that affect interpretation (§3.2)
Eleven operational incidents occurred, none of which left silently corrupted or missing data [docs/dataset_card.md]. Four matter for reading the data: (i) 72 S shards finalized with < 200 samples were re-solved and replaced, and 149 S shards were re-finalized after the scratch disk filled [docs/generation_postmortem.md; docs/dataset_card.md]; (ii) 62 L shards timed out silently and were re-solved [docs/generation_postmortem.md]; (iii) CHOLMOD raised `PosDefException` on high-contrast region-merged `regions` systems (3.5 % of XL regions rows), which ran as CG+AMG fallbacks during generation and were replaced by the precision pass [DECISIONS.md]; (iv) Circuitscape 5.17.1 aborts any solve with relative residual ≥ 1e-4, which killed whole Omniscape maps and T3 solves on contrast-10⁶ 2048² landscapes, so AmpScapeSolve installs replacement methods that refine such solves (bit-identical whenever the check passes) and counts them in `solver_params.rescued_solves` [docs/t4_fidelity.md]. T4 rows therefore carry no single residual; their per-window bound is the enforced ≤ 1e-4 with this rescue [docs/dataset_card.md].

## From splits_ood.md

### Macro-cell construction details
The globe is partitioned once into an equal-width grid of 20° latitude bands with n ≈ 360·cos(lat)/20 longitude cells per band — 104 cells, ≈ 2,200 km wide at every latitude — and each cell receives exactly one seeded assignment (`train`/`val`/`test_id`/`ood_region`) applied at every tier [docs/dataset_plan.md §5; ampscape/splits/spatial.py module docstring]. The assignment was frozen before generation as a pure function of (cell, seed): 70 of the 104 cells contain land and were labelled 56 train / 7 val / 7 test_id, stratified by each cell's dominant RESOLVE realm [DECISIONS.md 2026-09-14]. Tiles straddling cells with different assignments are excluded and resampled by the tile sampler; precedence is ood_region > test_id > val > train [ampscape/splits/spatial.py module docstring]. XXL footprints as parent regions are disabled (`parent_regions: false`) [configs/datasets/v1_0.yaml `spatial_block`; DECISIONS.md 2026-09-14].

### OOD-set design history and plan expectations
- `test_ood_region`: the unit is the tile: the earlier cell-level rule made 52 % of real dev tiles OOD and left no real `test_id` tile [configs/datasets/v1_0.yaml comment; DECISIONS.md 2026-09-14]. Plan expectation: ≈ 12 % of real tiles, ≈ 8,400 real landscapes [docs/dataset_plan.md §4].
- `test_ood_table`: plan expectation ≈ 14,000 real landscapes at S–L [docs/dataset_plan.md §4].
- `test_ood_contrast`: plan expectation ≈ 6,300 synthetic landscapes at S–L [docs/dataset_plan.md §4].
- `test_ood_scale_strict`: 6 XXL real tiles (30 landscapes) placed entirely inside non-training cells, zero overlap with any training tile at any tier, verified geometrically [docs/dataset_card.md]; built as XXL 32 + 6 strict accepted tiles [DECISIONS.md 2026-09-15]. Any overlap with a train/val tile raises an error at assignment time [ampscape/splits/assign.py `strict_scale_flags`].

### XL amendment C3 and the v1.0.2 correction (full record)
Amendment C3 makes 25 % of XL landscapes train/val so that models can also be trained at XL; XXL remains test-only [docs/dataset_plan.md §5; configs/datasets/v1_0.yaml `xl_trainval_share: 0.25`]. In v1.0/1.0.1 the share was applied by macro-cell hash, which synthetic landscapes do not have: they hashed the literal `None` (`stable_unit("None|20260906") = 0.348 ≥ 0.25`), so all 2,165 synthetic XL train/val landscapes moved to `test_id` and the real val cells all hashed out — XL train 228 / val 0 / test_id 3,118 / test_ood 254 / ood_region 400 [docs/status/latest.md "Owner checks" 2; CHANGELOG.md 1.0.2]. v1.0.2 (2026-09-26, metadata only) keeps the base label for synthetic XL landscapes with a per-seed-family share (0.3635 of the moved ones) and draws 28 real val landscapes among the kept cells: XL train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400, i.e. train+val = 1,011 (25.3 %) [CHANGELOG.md 1.0.2]. No data file changed; the XL index `split` column, split lists and Croissant were republished and 13 scale-transfer runs were re-aggregated on the corrected `test_id` [docs/dataset_card.md "Versions"; docs/status/latest.md "v1.0.2"]. The same release fixed the Hub split lists, which had held only the last published tier's ids; they were rebuilt as cross-tier unions (full: train 108,291 / val 18,934 / test_id 19,206 / test_ood 11,225 / ood_region 16,720), while the per-tier index `split` column was always complete [docs/status/latest.md "v1.0.2"].

### QC exclusion: residual rule and consistency check
Rows that cannot reach a 1e-6 residual in double precision are flagged `residual_high` with `qc_pass = false` and never silently kept [docs/dataset_card.md "Solver precision"]. Consistency check: the per-tier index counts (corrected XL) sum to train 108,292 / test_id 19,211 / test_ood 11,243 [derived: docs/tables/final_counts.json + CHANGELOG.md 1.0.2], i.e. 1 + 5 + 18 = 24 above the union lists — exactly the 24 QC-failing landscapes [derived; docs/dataset_card.md].

### Per-tier table note (original)
S, M, L, XXL and the QC column: `tiers.<tier>.splits` / `qc_fail_samples` in docs/tables/final_counts.json (index counts, before QC exclusion). XL: v1.0.2 figures from CHANGELOG.md 1.0.2; docs/tables/final_counts.json was updated to the same figures on 2026-10-02 (previously records the pre-correction XL row (train 228 / test_id 3,118 / test_ood 254 / ood_region 400).

### Nested subsets (original wording; sizes now stated in §3.1 only)
`mini`: 0.6 GB, the first 3 S shards, 600 landscapes; `lite`: ≈ 26 GB, 8,000 S + 2,400 M + 800 L landscapes (shards S 0–39, M 0–23, L 0–39; added in 1.0.1 as metadata only); `core`: 115.5 GB, 3,705 files, 20,000 S + 10,000 M + 5,000 L; `full`: 1,157.4 GB [docs/dataset_card.md; CHANGELOG.md 1.0.1].

## From baselines_protocol.md

### Tuning budget
The tuning pass that froze these configs ran on the dev subset within ≤ 6 GPU-h (FNO 32/64 modes, multi-scale GNN, one alternative each for U-Net and ViT, the distance channel for all) [DECISIONS.md 2026-09-14] and used 2.47 GPU-h over 16 runs [docs/tables/gpu_budget_tuned.md].

### Job mechanics
Jobs run on PACE-ICE `coc-gpu` L40S nodes (bf16, 48 GB) with A100 spill-over, as 2-hour legs that checkpoint and re-queue themselves (`train.py --resume --pause-exit`), ≤ 18 concurrent, because the per-user cap is 1 920 GPU-minutes of remaining walltime [docs/phase10_full_schedule.md §1]. Predictions (≈ 2.6 GB per finished S run) are offloaded to the Hub after sha256 verification [docs/phase10_full_schedule.md §4]. The transfer evaluation runs as 4-h resumable legs [docs/phase10_full_schedule.md §5].

### Why nothing is trained at XL
The card defines XL and XXL as held-out-scale tiers for models trained at ≤ L; their v1.0 splits held 228 (XL) and 0 (XXL) training landscapes and no validation split, so the first XL training legs were degenerate (`val_loss` 0, early stop at epoch 9) and single-process metrics at 1024² exceeded the 2-h leg. The nine XL training jobs were cancelled; nothing is trained at XL [docs/phase10_full_schedule.md §5; DECISIONS.md 2026-09-24].

### Scale-aware variant, planning note (superseded by the runs in results.md)
Planned: `<model>_<task>_L_s1_scalenorm` for U-Net, FNO, ViT × T1, T4, then the same zero-shot transfer; ≈ 30 GPU-h, plus 15–35 for the GNN variant; not started as of 2026-10-02 [docs/status/latest.md; DECISIONS.md 2026-09-25].

### Compute used (as of 2026-10-02)
Dev runs: 1.44 GPU-h (10 runs) [docs/tables/gpu_budget.md] and 2.47 GPU-h (16 tuning runs) [docs/tables/gpu_budget_tuned.md]. Full-scale training per run (T1, seed 1): U-Net 0.862 / 1.199 / 1.486 GPU-h at S / M / L; FNO 0.953 / 1.627 / 2.696; ViT 0.814 / 1.538 / 4.437 [docs/tables/baselines_full.md] — 3–7× below the plan's 30-epoch estimates [docs/status/latest.md]. At 2026-10-02: all 84 training runs of P1–P3 and WP4 complete; 18 of 30 transfer legs done; nominal remaining 772 GPU-h (GNN 578), realistically ≈ 200–300; plan 166 jobs ≈ 1,081 GPU-h nominal [docs/status/latest.md]. 182.4 GPU-hours consumed by 216 GPU jobs up to 2026-10-02 (training, evaluation and transfer legs, WP7 demo; scale-aware variants and GNN pending) [docs/tables/gpu_usage.md]. WP7: 36.3 CPU-h for the solver route versus 11.8 s on one GPU for 160 maps [docs/wp7_demo.md].

### Skeleton results table (superseded by results.md) — rel-L2 on test_id, seed 1, official configs
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

## From tasks_metrics.md

### Model inputs and targets (duplicate of baselines_protocol.md)
Baselines receive channel 0 = standardised log-resistance (train-only statistics, 0 at NoData), channel 1 = NoData mask, then the task's source channels (T1: focal mask; T3: source strength scaled by the valid-pixel count plus the ground mask; T4: Omniscape source strength), and predict log10(C + ε·max C) directly under a masked MSE loss [ampscape/models/common.py].

### Evaluation CLI and prediction-file format
`python scripts/evaluate.py --predictions <dir> --split <name> [--root ... --tier ... --subset ... --out <dir> --acceleration]` writes `results.json` and `results.md` [scripts/evaluate.py]. `--split` takes a comma-separated list; `--acceleration` runs the Julia warm-start evaluation on predicted voltages; `--t4-reference` selects the block-1 reference build (production as `bc_*`); `--t4-blocks` prints block-size baselines scored against the reference beside the model (WP2); `--workers` sets the metric processes [scripts/evaluate.py]. Predictions are framework-agnostic: `<dir>/predictions.h5` holds one group per sample and one subgroup per configuration with `cum_current` (float32 H×W; T1, T1W, T1R, T4), optional `voltage` (float32 H×W or P×H×W, first pair used, for the Kirchhoff residual and acceleration), optional `pairwise_current` (P×H×W), `reff` (float64 K×K; T2), `current` (float32 H×W; T3) and optional `flow_potential`/`normalized` (T4), plus a group attribute `inference_time_s` (per-configuration wall clock including preprocessing) used for the speed-up; `<dir>/meta.json` records model, task, tier, split, notes and seed [ampscape/eval/harness.py][docs/evaluation.md]. Only rows with `qc_pass` in the requested splits are evaluated, samples absent from the predictions file are skipped with the row count reported, samples are processed in sorted order with no randomness, and an oracle scores 0 error / 1.0 on every similarity metric while an all-zero predictor scores rel-L2 = 1 and top-q IoU = 0 [ampscape/eval/harness.py][docs/evaluation.md]. The transfer script is resumable, skipping splits whose predictions and metrics already exist [scripts/transfer_eval.py][scripts/train.py].

## From results.md

### Protocol and budget details (preamble)
Official configurations were trained for 30 epochs in 2-h resumable legs (§7 protocol). The GPU budget for everything reported was 430.1 GPU-h across 401 jobs, against a nominal plan of ≈ 1,081 GPU-h [docs/tables/gpu_usage.md].

### Training cost per run (§7.1)
Training cost was small — 0.72–2.49 GPU-h per U-Net or FNO run, 0.80–5.12 GPU-h for the ViT, 5.06–15.09 GPU-h for the GNN [paper/tables/baselines_sml.md].

### Data-scaling ablation cost (§7.3)
The ablation cost 5.1 GPU-h [docs/wp4_data_scaling.md].

### Per-family summary (original wording of "What the benchmark separates")
The four model families fail in different places, which is what makes the benchmark informative. The **U-Net** is the strongest model on T1 and T4 at S and M (T1 0.114 / 0.212; T4 0.041 / 0.051) and degrades fastest with tier, losing its T1 lead to the FNO at L (0.397 vs 0.361) [paper/tables/baselines_sml.md]; on T1 it cannot transfer to larger grids at all (rel-L2 ≈ 1 even with the scale-aware target) [paper/tables/scale_transfer.md]. The **FNO** is data-limited at S [docs/wp4_data_scaling.md], but has the best T1 result at L (0.361) and the highest T1 Spearman at every tier (0.967 / 0.959 / 0.945) [paper/tables/baselines_sml.md], and it transfers best: scale-aware T4 0.162 at XL and 0.201 at XXL, and, with the scale-aware target, the only T1 model below rel-L2 0.7 at XXL (0.671) [paper/tables/scale_transfer.md]. The **ViT** official configuration is competitive at S (T1 0.218, T4 0.052) and resolution-inappropriate above it: T1 0.419 ± 0.123 at M and 0.648 at L with top-5 % IoU 0.146, and the one case where a held-out table costs 49 % [paper/tables/baselines_sml.md; paper/tables/ood_degradation.md]. The **GNN** is far behind on T1 at every tier (0.561 / 0.849 / 1.067; its multi-scale graph does not resolve long-range pairwise flow) but competitive on T4 (0.066 / 0.099 / 0.142, ahead of the ViT at L), where the Omniscape window is local — the opposite of the convolutional models' relative strengths — at 6–10× the U-Net's training cost and roughly a tenth of its speed-up [paper/tables/baselines_sml.md; docs/status/latest.md]. No single family wins on accuracy, scale robustness, OOD robustness and cost at once; that trade-off, rather than any one number, is the result.

## From discussion.md

### Draft provenance note
The former "[TODO: not in docs]" markers were resolved on 2026-10-04 from docs/addendum_WP5_report.md and docs/phase_09_report.md.

### WP6 status
A multiscale operator of the HANO/MgNO family [41, 42] is not among the runs: WP6 was optional [docs/REVIEW_ADDENDUM_2026-09.md; docs/status/latest.md].

### WP5 probe set (limitation 5, full record)
A controlled 2×2 probe set separating the axes (256²/512² × 100 m/200 m at a fixed 12.8 km window; 360 landscapes, 47 CPU-h) was designed and built [docs/addendum_WP5_report.md §3, §5] and published under `aux/` [CHANGELOG.md, 2026-09-21], but its evaluation was not run for v1.0: no probe-cell results exist in docs/tables or the report [docs/addendum_WP5_report.md].

### XL amendment C3 metadata defect (former limitation 10)
XL amendment C3 had a metadata defect, corrected in v1.0.2. In v1.0/1.0.1 the 25 % train/val rule hashed a missing macro-cell id for synthetic XL landscapes (XL train 228 / val 0); v1.0.2 restores train 880 / val 131 / test_id 2,335 and rebuilds the split lists, no data file changed, XL transfer rows re-aggregated [docs/dataset_card.md; CHANGELOG.md]. Nothing was trained at XL, so no result depends on it [DECISIONS.md, 2026-09-25].

### Release history (Maintenance, original wording)
The data revision is `v1.0` (2026-09-23) on `Xirro/AmpScape`; `1.0.1` (2026-09-24, nested `lite` subset) and `1.0.2` (2026-09-26, C3 correction and split lists) are metadata-only tags on GitHub and the Hub with identical data files [docs/dataset_card.md; CHANGELOG.md].

### Strict-scale check wording (limitation 6, original)
`test_ood_scale_strict` (6 XXL tiles sampled inside test_id cells, with a finalize-time geometric check that no train/val tile of any tier intersects them) isolates both resolution and spatial novelty [docs/dataset_card.md; docs/addendum_WP5_report.md §2].
