# Status — 2026-10-20: review round 3 (second external review) — agreed points applied; L exact-reference top-up still solving

## Assessment of the review (owner: "do the ones you agreed with, and can improve our work and no harms")
Agreed and done: (1) independent T4 source-rule test; (2a) PCG on the same all-pair T1 target; (2b) a solver-free T4
baseline; (3a) more exact L references (running); (3b) bootstrap intervals by stratum; (5) decision-level analysis;
positioning sentence. Already covered: CPU/GPU/training/amortised costs (round 2), exact-vs-production targets.
Not done: learned baselines for T2/T1W/T1R (a deliberate round-2 decision), more published surfaces (licence search).

## Results
1. **T4 is not a fixed map of resistance.** 200 S + 100 M `test_id` landscapes re-solved under three unseen source
   rules (uniform, random field independent of R, (1/R)² habitat core; `scripts/review/r3_build_from_hub.py`). With the
   true sources the four ranked models reach rel-L2 0.094–0.163 (S) / 0.123–0.218 (M), 1.5–4.6× in-distribution,
   Spearman ≥ 0.77; with the production sources swapped in, every model lands within 1 % of the unchanged map's error
   (0.78–1.95). Models read their source channel. `docs/tables/review_round3_source_ood.md`, new Table 11.
2. **PCG on the real T1 target (all pairs, summed).** A converged AMG-PCG solve costs 0.62 / 2.96 / 16.6 s per T1
   landscape and 0.045 / 0.28 / 1.6 s per T3 landscape on one core. Two iterations beat every learned model on the
   **median** landscape of both tasks, but **not on the mean**: truncated iterates are erratic on high-contrast
   landscapes (non-monotone error). The round-2 claim had compared a subset median with a whole-split mean; the abstract,
   Section 7 and Appendix C are corrected (`docs/tables/review_round3_pcg.md`, Table 16 and Figure 10 redrawn).
3. **Solver-free T4 baseline (radius law + conductance), fitted once at S:** rel-L2 0.233 (M) / 0.253 (L) in
   15 / 82 ms on one core; the best learned model is 4.6× / 2.8× better. Rows in the Pareto tables and Figure 5.
   Fitted k = 0.775 ≈ the derived 2/3: a first numerical check of the radius law for the follow-up paper.
4. **Bootstrap intervals (2,000 landscape resamples):** within ±0.016 of every Table 2 mean except GNN T1 L (±0.042);
   every best-vs-runner-up order holds in all resamples. By stratum: real tiles are easier than synthetic; the pooled
   `test_ood` hides a held-out table that is *easier* (0.69–0.96) and a contrast-10⁶ part that is 1.23–4.17× harder
   (T4 1.82–3.29×). The OOD paragraph claim "held-out contrast costs little" is corrected. New Table 10.
5. **Decision-level analysis of the demo:** reproduced exactly (precision 0.657 / recall 0.941) under bf16 on an L40S;
   **in fp32 the same model gives 0.791 / 0.858** — bf16 rounding creates spurious local maxima (12,840 persistent
   candidates per tile vs the solver's 5,587). fp32 inference of the 160 maps took 3.71 s, so the speed claim stands.
   Precision 0.652–0.827 over thresholds; solving 6 of 8 tables lifts it to 0.962 at 75 % of the solver cost. Tables 19–20.
6. **Rounding issue found and fixed (predates this round):** Table 2, the OOD ratios and `paper/baselines.md` averaged
   per-seed values already rounded to 3 decimals. Now full precision from each run's `results.json`: T3 S FNO
   0.253 → 0.252, MgNO T4 S 0.359 → 0.358, T4 U-Net Spearman at L 0.991 → 0.992, OOD ratio ranges shifted in the third
   decimal (T4 M U-Net 1.200 → 1.191). `paper/baselines.md` also pooled tuned and untuned runs; now official runs only.

## Pending
- **L exact-reference top-up 60 → 120** (block-1 Omniscape, ≈ 3.3 h per landscape, throttled to ≤ 30 of my jobs so your
  other projects keep queue room): about half done. When finished: score models, production targets and the heuristic on
  all 120 (`r3_t4_eval.py reference`) and update Appendix F; the Pareto L rows stay on the original 24 `test_id` maps.
- The anonymity issue from earlier is unchanged: the paper names `Xirro/AmpScape`, and both that dataset and the GitHub repo are public.

## Checks
`main.pdf` 31 pages, nine content pages (cuts made to fit: details moved to appendices), 0 overfull / 0 undefined;
`check_draft_numbers.py --tex` 2,719 tokens, 0 untraceable. Incident: the throttled submitter's queue update broke on
`/` in paths and re-submitted M shards; duplicates cancelled by job ID, the affected outputs set aside
(`work/r3_discarded/`) and re-solved. Compute so far 146 CPU core-h, 0.19 GPU-h (projected ≈ 300 CPU core-h).
