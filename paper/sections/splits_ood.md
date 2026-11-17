# Splits, subsets and out-of-distribution sets

<!-- Draft section for the AmpScape D&B paper. Every number is tagged with the repository file it was copied from;
     "[derived: …]" marks arithmetic on tagged numbers. Design history, plan expectations and derivation details are in paper/appendix_notes.md. -->

## Split design

Splits are assigned by the *unit of leakage* — the tile for real landscapes, the seed family for synthetic ones — never by sample [docs/dataset_plan.md §1], at base fractions train 0.8 / val 0.1 / test_id 0.1 under dataset seed 20260906 [configs/datasets/v1_0.yaml `splits`]; hold-outs are applied before this draw, so in-distribution splits contain no held-out biome, realm, table, tier or contrast [docs/dataset_plan.md §4].

**Real tiles: spatial macro-cells shared across tiers.** Because an S tile physically sits inside XL/XXL footprints, the globe is partitioned once into 104 equal-width macro-cells (20° latitude bands, ≈ 2,200 km wide at every latitude), each receiving one seeded assignment applied at every tier [docs/dataset_plan.md §5; ampscape/splits/spatial.py module docstring]; the assignment is a pure function of (cell, seed), frozen before generation, with the 70 land cells labelled 56 train / 7 val / 7 test_id, stratified by dominant RESOLVE realm [DECISIONS.md 2026-09-14]. No train/val tile bounding box intersects any test/OOD tile box at any tier (1,640 random tiles, 0 overlaps) [docs/dataset_plan.md §5]. XXL footprints are not parent regions — the 32 real XXL footprints merge into 13 continental components covering 72 % of the S tiles — so S–XL tiles are assigned by macro-cell only and XXL stays test-only [configs/datasets/v1_0.yaml `spatial_block`; DECISIONS.md 2026-09-14].

**Synthetic landscapes: seed families.** A base seed defines the landscape; its 4-neighbour ablation duplicate and any hard-case variant inherit its split, and seed ranges are tier-disjoint [docs/dataset_plan.md §5; configs/datasets/v1_0.yaml `tier_disjoint_seeds`]. The label is a sha256 hash of (dataset seed, "synthetic", seed family) cut at the fractions [ampscape/splits/spatial.py `synthetic_split`].

**XL train/val share (amendment C3).** 25 % of XL landscapes are train/val so that models can also be trained at XL; XXL remains test-only [docs/dataset_plan.md §5; configs/datasets/v1_0.yaml `xl_trainval_share: 0.25`]. In v1.0.2 the share is applied per seed family for synthetic XL landscapes and by macro-cell for real tiles, giving XL train 880 / val 131 / test_id 2,335 / test_ood 254 / ood_region 400, i.e. train+val = 1,011 (25.3 %) [CHANGELOG.md 1.0.2]. Earlier metadata releases (v1.0, v1.0.1) assigned XL differently (train 228 / val 0 / test_id 3,118) and are superseded by v1.0.2 with no data file changed [CHANGELOG.md 1.0.2; docs/dataset_card.md "Versions"].

**Nested subsets.** Splits are fixed and nested over the shard-prefix subsets of §3 (mini ⊂ lite ⊂ core ⊂ full; `lite` = shards S 0–39, M 0–23, L 0–39); each subset is a Croissant FileSet, an index column `subset_<name>` and a split-list folder `splits/<name>/`, and real tiles and `ood_region` appear only in `full` [docs/dataset_card.md; CHANGELOG.md 1.0.1].

## Out-of-distribution sets

A landscape can belong to several OOD sets (one boolean index column per set) [docs/dataset_plan.md §4]; held-out-table and held-out-contrast landscapes that the base draw would place in train/val are demoted to `test_ood` [ampscape/splits/assign.py module docstring].

- **`test_ood_region`** — real tiles whose own biome is *Montane Grasslands & Shrublands* or *Mangroves* (RESOLVE biome numbers 10, 14) or whose realm is *Australasia*; the unit is the tile [configs/datasets/v1_0.yaml `ood.test_ood_region`; DECISIONS.md 2026-09-14].
- **`test_ood_table`** — all real landscapes built with the structurally different `forest_bird` table (r_max 100, elevation bands) are test-only; training sees generic_hm, large_mammal, amphibian and random [docs/dataset_plan.md §4].
- **`test_ood_contrast`** — synthetic contrast 10⁶ is never in train/val; training includes up to 10⁵ [configs/datasets/v1_0.yaml `ood.test_ood_contrast`].
- **`test_ood_scale`** — XL/XXL test landscapes evaluated by models trained on tiers ≤ L only; the in-distribution XL test for XL-trained models is `test_id` at XL [configs/datasets/v1_0.yaml `ood.test_ood_scale`]. XXL footprints (2,048 km, 32 tiles covering ≈ 90 % of land) overlap finer-tier training cells, so at XXL the set isolates *resolution* transfer, not spatial novelty; pixel size, raster size and the T4 window radius co-vary across tiers, so it measures combined scale transfer [docs/dataset_card.md; docs/dataset_card.md "Scale split caveat"].
- **`test_ood_scale_strict`** — 6 XXL real tiles (30 landscapes; `test_ood_scale_strict` in the XXL index [data/hfcache/index/XXL.parquet]) placed entirely inside non-training cells with zero overlap with any training tile at any tier, verified geometrically at assignment time [docs/dataset_card.md; DECISIONS.md 2026-09-15; ampscape/splits/assign.py `strict_scale_flags`].
- **`test_ood_synth2real`** — a flag only: evaluation on all real `test_id`, training restricted to `family = synthetic` by a loader flag; no extra samples [docs/dataset_plan.md §4].
- **`test_ood_published`** — published resistance surfaces used as given (Eurac Alps, CC BY 4.0; Northern raccoon Europe, CC BY 4.0; Hawaiian gallinule, CC0) with AmpScape's source configurations and all applicable tasks [docs/dataset_plan.md §5.4]: 45 S tiles (Eurac 30, gallinule 15) and 1 XXL tile (raccoon), under `aux/` [CHANGELOG.md Phase 9; DECISIONS.md 2026-09-13; docs/dataset_card.md].

## QC exclusion rule

The 25 rows failing QC after the precision pass (24 landscapes, all synthetic at contrast ≥ 10⁴) stay in the index with their flags and are excluded from the split lists [docs/dataset_card.md]. `qc_pass = False` flags are excluded everywhere; `rmax_saturated` is excluded from train/val only; `fallback_solver` is informational [DECISIONS.md 2026-09-05 "QC flag semantics"].

## Per-tier split counts (landscapes)

| tier | train | val | test_id | test_ood | ood_region | QC-failing landscapes |
|---|---|---|---|---|---|---|
| S | 63,303 | 10,917 | 9,850 | 6,460 | 9,470 | 1 |
| M | 31,496 | 5,651 | 4,823 | 3,225 | 4,805 | 4 |
| L | 12,613 | 2,235 | 1,928 | 1,279 | 1,945 | 10 |
| XL (v1.0.2) | 880 | 131 | 2,335 | 254 | 400 | 7 |
| XXL | 0 | 0 | 275 | 25 | 100 | 2 |

Index counts before QC exclusion [docs/tables/final_counts.json `tiers.<tier>.splits`, `qc_fail_samples`; XL: CHANGELOG.md 1.0.2]. Subset membership per tier: core 20,000 S / 10,000 M / 5,000 L, mini 600 S [docs/tables/final_counts.json].

**Subset and OOD-set sizes (v1.0.2 split lists, QC-failing samples excluded; `splits/<subset>/<split>.parquet` on the Hub):**
mini train 481 / val 54 / test_id 50 / test_ood 15; lite 8,753 / 1,126 / 1,120 / 196; core 27,439 / 3,456 / 3,461 / 637;
full 108,291 / 18,934 / 19,206 / 11,225 (+ ood_region 16,720) [CHANGELOG.md 1.0.2; data/hfcache/splits]. Within `test_ood`
the two hold-outs do not overlap: 9,336 landscapes carry the held-out resistance table only and 1,907 the held-out
contrast only (index flags `test_ood_table` / `test_ood_contrast`, all tiers, before QC exclusion) [data/hfcache/index/*.parquet].

## Sources used

- docs/dataset_card.md — "Final counts", "Dataset structure", "Splits and leakage", "Scale split caveat", "Solver precision", "Versions"
- docs/dataset_plan.md — §1, §4, §5, §5.4
- docs/tables/final_counts.json — `tiers.<tier>.splits`, `qc_fail_samples`, `core_samples`, `mini_samples`
- docs/tables/dataset_statistics.md — consulted; no split counts taken from it
- CHANGELOG.md — 1.0.2, 1.0.1 and Phase 9 entries
- DECISIONS.md — rows 2026-09-05 (QC flag semantics), 2026-09-13 (published tiles), 2026-09-14 (frozen cell assignment; tile-level hold-out; XXL parents disabled), 2026-09-15 (tile set), 2026-09-26 (v1.0.2)
- ampscape/splits/assign.py — module docstring, `strict_scale_flags` docstring
- ampscape/splits/spatial.py — module docstring, `synthetic_split`
- configs/datasets/v1_0.yaml — `splits`, `ood`
- docs/status/latest.md — "v1.0.2 (metadata only)", "Owner checks" item 2
