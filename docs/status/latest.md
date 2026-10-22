# Status — 2026-10-22: L exact reference republished at 120 maps (owner approval), dataset card updated, full recheck

## Done (owner: "approved, check everything after")
1. **L exact reference 60 → 120 is now official.** The 60 new block-1 maps were merged into `aux/t4_bs1_reference/L_bs1`
   (shards 60–119); production vs exact on all 120: mean rel-L2 0.0303 (test_id 0.0321, test_ood 0.0319, ood_region
   0.0270), max 0.2032 (synthetic, contrast 10⁶), 6 of 120 above 5 %, all synthetic. The three L block-size builds
   (block 3, block 5 without correction, block 11) were extended to the same 120 landscapes (180 solves) so the Pareto
   rows stay like-for-like; block 11 test_id stays 0.0854.
2. **All 28 L T4 runs re-scored** with the official harness on their stored test predictions (fetched from the Hub to
   node-local disk): every row now n = 48 test_id maps. Pareto L: U-Net 0.0850 (was 0.0903 on 24), FNO 0.1148, GNN
   0.1375, ViT 0.1541; production 0.0321; radius-law heuristic 0.2573 (learning 3.0× better, was 2.8×).
3. **Hub pushes (all checksum-verified, 0 mismatches):** `aux/t4_bs1_reference/L` (+125 files), the three
   `aux/t4_blocksize_baselines/L/*` builds (+28 files each), the leaderboard (168 entries; exactly the four T4 L
   reference rows changed), the dataset card (one sentence: 0.030 at L on the 120-landscape reference; round-trip
   byte-identical). The re-scored per-run evaluations were already re-pushed by the offloader (spot-checked).
4. **Paper updated:** reference sizes (48 / 32 / 40 at L), production fidelity 0.0321, Pareto quotes, heuristic ratio,
   exact-solve cost on the figure's basis (median per landscape 7.2× at M, 19.8× at L; the text had 6.7× / 22× from
   older subsets), fidelity-figure caption, checklist (seven limitations; bootstrap intervals named).
5. **Two older labelling errors fixed:** the demonstration model's "rel-L2 0.080 against the exact map" was its error
   against the production target on test_id (against the exact map it is 0.085); `docs/wp7_demo.md` corrected. My own
   status line of 2026-10-20 said all six L tail landscapes were at contrast ≥ 10⁴ or large NoData — one is a contrast-100
   fractal landscape; corrected in `docs/t4_fidelity.md`, the card and this page.

## Checks
Clean rebuild: 31 pages, nine content pages, 0 overfull, 0 undefined references/citations; `check_draft_numbers.py
--tex` 2,728 tokens, 0 untraceable, 0 untagged; all 31 pages inspected; full test suite 703 passed / 6 skipped; Hub
reference index (120 rows), block-11 rows (120) and leaderboard files verified against local copies.

## Still yours
- **Anonymity:** the paper names `Xirro/AmpScape`, and both that dataset and the GitHub repo are public. Unchanged.
- Backups kept: `work/L_bs1_backup_2026-10-22/`, `work/blocks_backup_2026-10-22/`,
  `work/eval_t4_reference_L_backup_2026-10-22/`, `work/leaderboard_backup_2026-10-22/`,
  `work/dataset_card_before_2026-10-22.md`.
