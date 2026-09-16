# AmpScape

**A benchmark of circuit-theoretic landscape connectivity for learned surrogates.** Every sample pairs a resistance
raster and a source configuration with the exact outputs of the reference solvers (Circuitscape.jl 5.17.1,
Omniscape.jl 0.6.2): current-density maps, voltage maps, effective resistances and omnidirectional connectivity —
plus official splits, out-of-distribution test sets, metrics, baselines and a reproducible generation pipeline.

- Dataset (Hugging Face, public, v1.0 generation in progress): https://huggingface.co/datasets/Xirro/AmpScape
- Task specification: `docs/task_specification.md` · schema: `docs/schema.md` · datasheet / card: `docs/dataset_card.md`
- Evaluation: `docs/evaluation.md` · licences: `docs/licenses.md` · how to rebuild: `docs/generation_guide.md`

| task | input → target | reference |
|---|---|---|
| **T1** pairwise current mapping (points / wall-to-wall / regions) | resistance + focal nodes → cumulative current map | Circuitscape pairwise, CHOLMOD |
| **T2** effective resistance | same → K×K Reff matrix | Circuitscape pairwise |
| **T3** advanced-mode flow | resistance + source strengths + grounds → current and voltage maps | Circuitscape advanced |
| **T4** omnidirectional connectivity | resistance + source raster → cumulative / normalised current, flow potential | Omniscape |

Tiers S (128², 100 m) … XXL (2048², 1 km); 60 % synthetic landscapes (documented priors incl. a hard-case
stratum), 40 % real tiles (ESA WorldCover, Copernicus DEM, GRIP4, HydroRIVERS, gHM) × five resistance tables.

## Install

```bash
git clone https://github.com/Xyrro/AmpScape && cd AmpScape
uv sync --extra dev                      # Python 3.11 venv (pinned in uv.lock; torch from the cu126 index)
# the solver is only needed to *generate* data or run the acceleration metric:
julia --project=julia/AmpScapeSolve.jl -e 'using Pkg; Pkg.instantiate()'
```

## Quickstart (10 minutes, GPU optional)

```python
from ampscape.data import load_from_hub
ds = load_from_hub("T1", "S", split="train", subset="mini")   # ≈ 0.4 GB: 3 shards, all tasks
x = ds[0]                                                      # dict of numpy arrays + metadata
print(x["resistance"].shape, x["cum_current"].shape, x["meta"]["generator"])
```

```bash
# train the official U-Net baseline on the mini subset and evaluate it through the harness
python scripts/train.py --model unet --task T1 --tier S --root <local mini root> --out runs/quick/unet_T1 --epochs 10
python scripts/evaluate.py --predictions runs/quick/unet_T1/predictions/S_S_test_id --split test_id --root <local mini root>
```

Notebooks: `notebooks/01_quickstart.ipynb` … `05_rebuild_mini_dataset.ipynb`.

## Baselines

`scripts/train.py --model {unet,fno,vit,gnn}` — official configurations in `ampscape.models.OFFICIAL`
(U-Net base; FNO 64 modes + distance channel; ViT base; multi-scale GNN + distance channel), results on the dev
subset in `docs/tables/baselines_dev.md` and `docs/tables/tuning_dev.md`; the non-learned coarsen-solve-upsample
baseline in `scripts/baseline_coarsen.py`. Predictions format and metrics: `docs/evaluation.md`.

## Repository layout

`ampscape/` (landscapes, sources, resistance, solve, splits, io, data, metrics, eval, models) · `julia/AmpScapeSolve.jl`
(solver wrapper, QC, CG baselines) · `scripts/` (generation driver, planners, evaluation, training, sync) ·
`configs/` (dataset design, sources, solver preset, cluster profiles, frozen splits) · `docs/` (specification,
plan, reports, runbooks) · `tests/`.

## Citation

See `CITATION.cff`. Code: MIT. Data: CC BY 4.0 with the upstream attributions in `docs/licenses.md`.
