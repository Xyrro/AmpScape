# Status — 2026-10-18 07:10Z: review round 2 applied — like-for-like costs, cheap baselines, MgNO/scale-aware seeds, XL-trained run; paper rebuilt at nine pages

## Done (owner: "fix the ones you agreed with … up to 16 GPU-hours … check the correctness")
1. **Like-for-like speed-ups (point 1).** Production Omniscape re-timed with its own parallelisation on one CPU node
   (`scripts/review/omniscape_threads.*`): 1.64× at M and 1.85× at L on 8 threads, nothing more at 24. The paper
   now states every speed-up's basis, the like-for-like figures (14,235× / 22,916× at M / L for the U-Net; 5,955× for
   the demonstration), the training cost and the break-even number of maps (37 maps at L; 13 for the demo). New
   Appendix C with `tab_threads`, `tab_breakeven` (`docs/tables/review_round2_threads.md`).
2. **Cheap numerical baselines (point 4).** Truncated AMG-PCG after k iterations and coarsen-×4 on `test_id` subsets
   (`scripts/review/cheap_baselines.sbatch`): two PCG iterations reach rel-L2 0.038 / 0.048 / 0.324 on T3 at S / M / L
   against 0.111 / 0.202 / 0.323 for the best learned model, at 0.02–0.65 s per landscape on one core. T1/T3 are
   reframed as operator-learning stress tests; table + figure in Appendix C (`docs/tables/review_round2_cheap.md`).
3. **Text fixes (points 3, 6, 9, 10):** T2/T1W/T1R declared released without learned baselines; rel-L2 the single
   primary metric; pinch-point precision 0.657 in the same sentence as 11,077× (abstract included); abstract and
   introduction lead with the operator-learning framing and cite adoption (1,936 Scopus citations of McRae et al.
   2008; 459 applications reviewed by Dickson et al. 2019).
4. **New runs (points 2, 7, 8; 14.64 of the 16 GPU-h cap, H100 on `ice-gpu`/`coc-ice`; three legs lost to a known bad
   node and resubmitted):** MgNO seeds 2–3 at S/M on T1/T4 — MgNO **diverges in 4 of 6 T4 runs and 2 of 6 T1 runs**
   under the shared protocol (training loss → 1e6–1e21 in the first epochs); reported as an instability, not patched
   (`docs/tables/review_round2_mgno.md`). Scale-aware seeds 2–3 for U-Net and FNO w48 on T4 at L: U-Net 0.194 ± 0.008
   at XL and 0.321 ± 0.015 at XXL (was seed-1 0.189 / 0.312), FNO 0.158 ± 0.001 at XL. One U-Net T4 run trained at XL
   on its 880 landscapes: rel-L2 0.249 on XL test_id, between zero-shot (0.515) and scale-aware (0.194) from L. The
   ViT at L was *not* re-tuned: the tuning pass had tried patch-16/patch-8 there (+47.8 % / +63.5 %); now stated.
5. **Correctness checks:** every table and figure regenerated from `runs/full` (Pareto rows pool the scale-aware
   seeds; in-tier tables exclude the XL-trained run), `main.pdf` rebuilt (29 pages; **nine content pages**, references
   start at the top of page 10), build log 0 overfull / 0 missing glyphs, `check_draft_numbers.py --tex` 2,268 tokens
   / 0 untraceable / 0 untagged, every changed page inspected at print size, `tests/test_no_pattern_kills.py` passes.

## Full recheck (owner: "check everything again")
Clean rebuild (0 overfull boxes, 0 missing glyphs, 0 undefined references or citations, all 52 cited keys in the
bibliography, every `\ref` label present, no hard-coded appendix letters), every generated table and figure
regenerated and byte-identical to the committed ones, 2,268 numeric tokens all traceable, all 29 pages viewed at print
size. Two defects found and fixed: the MgNO divergence count in the text said 1 of 6 T1 runs (the table says 2 of 6,
first exploding epoch up to 4, not 3) — corrected; the Appendix D heading sat alone at the foot of page 21 below the
Appendix C tables — now starts its own page.

## Dataset card (owner: rewrite for users)
`docs/dataset_card.md` rewritten and pushed as the Hub README (round-trip verified): description, task table,
tier/subset/split table with sizes, lite-subset loading example, metrics and leaderboard pointer, one-sentence
limitations and provenance, licence table, BibTeX citation. 2,604 → 2,026 words. Dates, incidents, run histories and
operational notes moved verbatim to the new `docs/datasheet.md`, linked from the card with the post-mortem. Front
matter and `croissant.json` pointer unchanged (front matter validated with `DatasetCard.load`).

## Not done, by design (stated as limitations in the paper)
Converged (non-budget-limited) retraining of every configuration, new operator families, published resistance
surfaces at M/L, an exact T4 reference at XL/XXL, FNO scale-aware seeds at XXL (budget).

## Open for the owner
- **Leaderboard re-seeded and pushed (your approval 2026-10-18 05:56Z):** 168 entries on the Hub, sha256-verified;
  all 34 Table 2 cells present with rel-L2 agreeing to the third decimal; the four block-1 rows at L equal the four
  official learned rows of Table 7 (scale-aware variants are not leaderboard entries, as before).
- Scratch deletion rows: still waiting for your choice; nothing deleted. `aux/review_round2/` stays until submission,
  as you asked.

## Operations
GPU use for this step: 14.64 GPU-h (`scripts/review/gpu_budget.sh`). CPU: two Slurm jobs (≈ 1.5 node-hours).
Offloader loop and keepalive running. GitHub main = origin after this push.
