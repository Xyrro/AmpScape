---
license: cc-by-4.0
pretty_name: AmpScape
task_categories: [image-to-image, other]
tags: [landscape-connectivity, circuitscape, omniscape, surrogate-modeling, neural-operators, scientific-ml, ecology]
size_categories: [100K<n<1M]
configs: []   # no dataset-viewer configs: the shards are HDF5 (not viewer-loadable); use ampscape.data.load_from_hub
---

# AmpScape

AmpScape is a benchmark for learned surrogates of circuit-theoretic landscape connectivity. It pairs 174,400 resistance
rasters on five tiers from 128² to 2048² pixels (60 % synthetic landscapes from neutral landscape models and random
fields, 40 % real tiles built from open global land-cover, terrain, road, river and human-modification layers) with the
exact outputs of the reference solvers Circuitscape.jl and Omniscape.jl: 920,372 configuration rows holding
current-density maps, voltage maps, effective resistances and omnidirectional connectivity, stored raw (float32 maps,
float64 effective resistances) with the solver's residual and provenance on every row. The data come with official
spatial splits, out-of-distribution test sets, a scale-transfer split, an evaluation harness with pixel, ranking,
non-source and physics metrics, baselines from five model families and a leaderboard. The resistance surfaces are
structural proxies built from literature-style tables, not species-calibrated truth; intended use is benchmarking and
screening, not final conservation decisions. Code, harness and documentation: https://github.com/Xyrro/AmpScape (MIT).

## Tasks

Every landscape carries one resistance raster `R` (H × W, R ≥ 1, NoData masked) and several source configurations.
Inputs are the raster, the NoData mask and the configuration's source channels; targets are the solver outputs.

| task | configuration | target(s) | notes |
|---|---|---|---|
| **T1** pairwise current | `points`: K ∈ [2, 8] single-pixel focal nodes, all K(K−1)/2 pairs | `cum_current` (H × W) | learned baselines provided |
| **T2** effective resistance | same run as T1 | `reff` (K × K, float64) | released without learned baselines |
| **T1W** wall-to-wall current | `wall_to_wall_NS`, `wall_to_wall_EW`: two edge strips as focal regions | `cum_current`; strip pixels masked in the metrics | released without learned baselines |
| **T1R** region-to-region current | `regions`: habitat patches as short-circuited focal regions | `cum_current` | released without learned baselines; present only where ≥ 2 eligible patches exist |
| **T3** advanced mode | `advanced`: source-strength raster and ground mask | `current`, `voltage` (H × W) | learned baselines provided |
| **T4** omnidirectional connectivity | `omniscape`: Omniscape over every source pixel within a radius, block-centred | `cum_current`, `flow_potential`, `normalized` (H × W) | learned baselines provided; radius / block per tier: S 16 / 1, M 32 / 3, L 64 / 5, XL 128 / 11, XXL 256 / 25 px |

Configurations that are undefined on a landscape (a strip entirely NoData, too few habitat patches) are listed with a
reason in the index column `skipped_configs`; everything else planned is present.

## Tiers, subsets and splits

| tier | raster · pixel | landscapes | configuration rows | synthetic / real | GB | train | val | test_id | test_ood | ood_region |
|---|---|---|---|---|---|---|---|---|---|---|
| S | 128² · 100 m | 100,000 | 527,281 | 60,000 / 40,000 | 142.4 | 63,303 | 10,917 | 9,850 | 6,460 | 9,470 |
| M | 256² · 100 m | 50,000 | 264,128 | 30,000 / 20,000 | 251.7 | 31,496 | 5,651 | 4,823 | 3,225 | 4,805 |
| L | 512² · 200 m | 20,000 | 105,949 | 12,000 / 8,000 | 380.9 | 12,613 | 2,235 | 1,928 | 1,279 | 1,945 |
| XL | 1024² · 500 m | 4,000 | 21,006 | 2,400 / 1,600 | 281.7 | 880 | 131 | 2,335 | 254 | 400 |
| XXL | 2048² · 1 km | 400 | 2,008 | 210 / 190 | 100.7 | 0 | 0 | 275 | 25 | 100 |
| **total** | | **174,400** | **920,372** | | **1,157.4** | | | | | |

Split counts are landscapes before quality-control exclusion. `test_ood` holds landscapes built with the held-out
`forest_bird` resistance table or at the held-out contrast 10⁶; `ood_region` holds real tiles of the held-out biomes
(Montane Grasslands & Shrublands, Mangroves) and realm (Australasia). Further boolean index columns mark the OOD sets:
`test_ood_region`, `test_ood_table`, `test_ood_contrast`, `test_ood_scale` (XL/XXL for models trained at ≤ L),
`test_ood_scale_strict` (XXL tiles overlapping no training tile at any tier), `test_ood_synth2real`,
`test_ood_published` (45 S tiles and 1 XXL tile with published resistance surfaces, under `aux/`). Real tiles are
assigned by spatial macro-cells shared across tiers, synthetic landscapes by seed family.

Four nested subsets (shard prefixes per tier; each an index column `subset_<name>`, a split-list folder
`splits/<name>/` and a Croissant FileSet):

| subset | size | landscapes | contents |
|---|---|---|---|
| `mini` | 0.6 GB | 600 S | first 3 S shards, all task groups |
| `lite` | ≈ 26 GB | 8,000 S + 2,400 M + 800 L | all task groups |
| `core` | 115.5 GB | 20,000 S + 10,000 M + 5,000 L | all task groups |
| `full` | 1,157.4 GB | 174,400 | everything; the only subset with real tiles and `ood_region` |

Layout: `data/<tier>/<task_group>/shard-NNNNN.h5` (task groups `T1`, `T1W`, `T1R`, `T3`, `T4`; one HDF5 group per
sample with inputs and outputs, so any tier or task group downloads alone), `index/<tier>.parquet` (one row per
sample × configuration: identifiers, family, generator or table, tile, solver, timings, residuals, QC flags, split,
OOD flags, subset membership), `splits/<subset>/<split>.parquet`, `stats/norm_stats.json` (train-only normalisation
statistics), `croissant.json` (Croissant 1.0 with RAI fields). Schema: `docs/schema.md` in the code repository.
Hub revisions: `v1.0` (data) and `v1.0.2` (current metadata); data files are identical across them.

## Loading

```python
# pip install "ampscape @ git+https://github.com/Xyrro/AmpScape"

from ampscape.data import load_from_hub

# one tier × task group of the lite subset: only its shards are downloaded (lite: 8,000 S + 2,400 M + 800 L landscapes)
train = load_from_hub("T4", "M", split="train", subset="lite")
item = train[0]
item["resistance"], item["nodata"]          # (1, 256, 256) float32 raster and NoData mask
item["source_strength"], item["cum_current"] # T4 input channel and target
item["meta"]                                 # family, generator or table, tile, solver provenance

# raw files instead of the loader
from huggingface_hub import snapshot_download
snapshot_download("Xirro/AmpScape", repo_type="dataset", allow_patterns=["data/L/T4/*", "index/L.parquet", "splits/**"])
```

Baselines predict `log10(C + 1e-6 · max C)` under a masked MSE; `scripts/train.py` in the code repository reproduces
every official run, and `scripts/evaluate.py` scores any predictions file in the harness format.

## Metrics and leaderboard

The harness (`ampscape.eval.harness`, `docs/evaluation.md`) reports, per task and split: relative L2 on raw currents
(the primary metric), MAE in log10-ε space, MSE, SSIM/PSNR; top-q % IoU of the highest-current pixels (q = 1, 5, 10),
corridor Dice, pinch-point recall, Spearman rank correlation; the same metrics outside source, focal and ground pixels;
Kirchhoff residual, focal-current error, non-negativity and throughput error of predicted voltages; speed-up over the
production solver (one solve per CPU core) and, optionally, the warm-start acceleration of the reference solver. At M
and L the official T4 metrics are computed against exact block-1 Omniscape references on the `test_id` reference
subsets (`aux/t4_bs1_reference/`). The domain metrics use conventional thresholds that are not validated against
ecological outcomes.

The leaderboard lives in this repository: `aux/leaderboard/results.jsonl` (append-only entries) and
`aux/leaderboard/README.md` (tables per task × tier × split). Its first entries are the official baselines (U-Net,
FNO, ViT, GNN, MgNO; three seeds; one configuration per model × task × tier selected on validation loss; XL/XXL rows
of L-trained models are zero-shot). To submit, run `scripts/submit_results.py validate` on a predictions directory and
open an issue titled `Leaderboard: <model> <task> <tier> <split>` in the code repository; the full specification is
`docs/submission.md`. Baseline predictions, checkpoints and metrics are under `aux/results/`; auxiliary evaluation
sets are described in `aux/README.md`.

## Known limitations and provenance

- Reference solvers: Circuitscape.jl 5.17.1 and Omniscape.jl 0.6.2, CHOLMOD in double precision, average-conductance
  8-neighbour graphs; every sample stores the solver version, parameters, timing and residual.
- T4 targets at M and above use Omniscape's `block_size` (largest odd integer ≤ radius / 10) with artefact correction;
  against the exact block-1 map the production target deviates by mean relative L2 0.029 at M (1,000-landscape
  reference, 4.7 % of landscapes above 5 %) and 0.030 at L (120-landscape reference, 6 above 5 %, all synthetic; the
  largest, 0.203, at contrast 10⁶), and block 1 is exact at S.
- Every T1/T1W/T1R/T3 row carries its measured relative Kirchhoff residual (`residual_rel`); a post-run precision pass
  re-solved 129,722 rows with CHOLMOD plus refinement so that 3,861 rows lie between 10⁻⁹ and 10⁻⁶ and only 20 rows,
  all synthetic at contrast ≥ 10⁴, remain above 10⁻⁶.
- Those 20 rows and the other quality-control failures (25 rows, 24 landscapes in total) stay in the index with
  `qc_pass = false` and are excluded from every split list.
- v1.0.2 is a metadata-only correction: XL synthetic landscapes had all been placed in `test_id` in v1.0/1.0.1 (train
  228, val 0); the seed-family rule now gives XL train 880 and val 131, and the split lists were rebuilt as cross-tier
  unions; no data file changed.
- XXL footprints (2,048 km) overlap finer-tier training cells, so `test_ood_scale` at XXL measures resolution transfer;
  only `test_ood_scale_strict` isolates spatial novelty as well; pixel size, raster size and the T4 radius co-vary
  across tiers.
- Resistance tables follow the literature in class ordering and term structure but their numeric values are AmpScape's
  own; real landscapes are real covariate stacks with synthesised resistance.
- Regeneration from the frozen pipeline tag `v1.0-pipeline` is bitwise on the same CPU model and agrees to ≤ 1.2 × 10⁻⁹
  relative across CPU models.

The generation record, incidents and their resolutions are in `docs/generation_postmortem.md`; the full datasheet
(composition, collection, splits and leakage design, precision pass, absent configurations) is `docs/datasheet.md`;
per-tier statistics are in `docs/tables/dataset_statistics.md` (all in the code repository).

## Licence and attributions

AmpScape data are released under **CC BY 4.0**; code and the solver wrapper under MIT. The covariate channels and the
published-resistance evaluation set are derived from the sources below; the sources themselves are not redistributed
except where their licence permits and the derived channel is the source itself (the three published resistance
rasters, re-tiled). Required attributions:

| Source | Licence | Attribution / notice |
|---|---|---|
| ESA WorldCover 10 m 2021 v200 (land cover) | CC BY 4.0 | © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium |
| Copernicus DEM GLO-30 (elevation, slope) | Copernicus WorldDEM-30 licence | "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved". "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30". |
| GRIP4 global roads (distance, class) | CC0 by the publisher; CC BY 4.0 in secondary catalogues — attributed | Meijer et al. 2018, Environ. Res. Lett. 13:064006; PBL Netherlands Environmental Assessment Agency (GRIP4) |
| HydroRIVERS v1.0 (river distance, order) | CC BY 4.0 (HydroSHEDS licence) | Lehner & Grill 2013, Hydrol. Process. 27:2171–2186; www.hydrosheds.org |
| gHM v1 (human modification) | CC BY 4.0 | Kennedy et al. 2019, Glob. Change Biol. 25:811–826; figshare 10.6084/m9.figshare.7283087 |
| RESOLVE Ecoregions 2017 (stratification only; no raster stored) | CC BY 4.0 | Dinerstein et al. 2017, BioScience 67:534–545 |
| Eurac Alps landscape permeability (`test_ood_published`) | CC BY 4.0 | Marsoner, Simion, Giombini, Egarter Vigl (Eurac Research) 2022, Zenodo 10.5281/zenodo.6602481 |
| Northern raccoon resistance, Europe (`test_ood_published`) | CC BY 4.0 | figshare 10.6084/m9.figshare.27311484.v1 |
| Hawaiian gallinule resistance layers (`test_ood_published`) | CC0 1.0 | Dryad 10.5061/dryad.p90b87p; paper 10.1002/ece3.4296 |

Not used and not redistributed: WDPA (restrictive terms), OpenStreetMap (ODbL). Synthetic landscapes are generated by
AmpScape code (MIT); solver outputs by Circuitscape.jl 5.17.1 and Omniscape.jl 0.6.2 (MIT). Real tiles derive from
public products at ≥ 100 m resolution; no personal data. Full verification log: `docs/licenses.md`; the Copernicus
notices are reproduced verbatim in `LICENSE-DATA`.

## Citation

```bibtex
@dataset{ampscape2026,
  title   = {AmpScape: a benchmark for learned surrogates of circuit-theoretic landscape connectivity},
  author  = {Xiao, Yao},
  year    = {2026},
  version = {1.0.2},
  url     = {https://huggingface.co/datasets/Xirro/AmpScape},
  note    = {Data CC BY 4.0, code MIT; see CITATION.cff for the upstream sources to cite alongside}
}
```

Please also cite Circuitscape.jl (Anantharaman et al. 2020) and Omniscape.jl (Landau et al. 2021), and the upstream
data sources listed above when their derived channels are used.
