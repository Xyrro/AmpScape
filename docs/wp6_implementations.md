# WP6 — Official implementations of MgNO and HANO: availability, licence, usability

Checked 2026-10-05 via web search / fetch only (no clone, no install). Both repositories belong to the same
author account (`xlliu2017`, Xinliang Liu, co-author of both papers). Paper texts were read from the arXiv
PDFs (2310.19809v3, 2210.10890v3); repository facts come from the GitHub API, raw file fetches and the commit
history. Parameter counts marked "analytic" were computed by hand from the layer definitions (script in the
session scratchpad; the MgNO count reproduces the paper's figure exactly, which validates the method).

**Verdicts**

| Model | Verdict | One-line reason |
|---|---|---|
| MgNO | **USABLE** | MIT; ~150 lines of pure PyTorch (`MgNO_DC`); resolution-agnostic; paper config reproducible (0.57 M params, analytic count matches); only adapter is `num_channel_f = in_channels` + an `output_dim` fix. |
| HANO | **NOT USABLE** (as an official baseline) | MIT, but the repository no longer contains a verifiable implementation of the published architecture: the shipped `HANO` is a different, unpublished "multigrid-attention" model; the paper's model survives only as a Copilot-migrated `hano_legacy.py` whose only config contradicts the paper, is not wired to any experiment, and is tied to 2^k+1 grids; git history was rewritten and the README carries a fabricated citation. |

---

## (a) MgNO — He, Liu, Xu, "MgNO: Efficient Parameterization of Linear Operators via Multigrid", ICLR 2024 (arXiv 2310.19809)

### Repository
- URL: https://github.com/xlliu2017/MgNO (default branch `main`; 31 stars; GitHub API `license.spdx_id = MIT`).
- Provenance: the paper's reproducibility statement says the code is "included in the supplementary files"; the
  public repo is the authors' release (commits `c05317b` "Initial commit", `52b9f35` "init", `0f70fa4`, `3a68a90`
  "Update LICENSE.txt", all 2024-03-15). On 2026-03-17 a Copilot agent PR (#2, merged `203ad93`) added
  docstrings, a `_build_activation` helper and README restructuring. I fetched `models.py` at both
  `3a68a900bcccdb2246fd86ede4b001440a56c152` (original) and `main` and compared `MgIte`, `MgIte_init`, `Restrict`,
  `MgConv_DC`, `MgNO_DC` line by line: kernel sizes, strides, paddings, bias flags, V-cycle order and the final
  projection are identical; only docstrings and the activation-lookup were changed. Either commit can be vendored;
  pin the original `3a68a90` to stay closest to the ICLR artefact.
- Root files: `Adam.py`, `LICENSE.txt`, `README.md`, `darcy.py`, `helm.py`, `models.py` (43.6 kB), `navier.py`,
  `requirements.txt`, `utilities3.py`, `baselines/`.

### Licence
- File `LICENSE.txt`, MIT License, "Copyright (c) 2024 Xinliang Liu". SPDX: `MIT`. Vendoring permitted provided
  the copyright + permission notice is kept.

### Framework and pinned dependencies
- README: "Python >= 3.8, PyTorch >= 1.13, CUDA recommended"; install = `pip install -r requirements.txt`.
- `requirements.txt` (exact pins): `h5py==3.7.0`, `numpy==1.23.5`, `scipy==1.9.3`, `timm==0.6.12`, `torch==1.13.0`,
  `torchinfo==1.7.2`, `tqdm==4.64.1`. Installing this file verbatim would downgrade torch and numpy and therefore
  conflicts with our `.venv` (torch 2.13.0+cu130). **Not needed:** `models.py` imports only `numpy`, `torch`,
  `torchinfo.summary` (introspection only) and `utilities3.count_params` (local helper). The model classes use
  `nn.Conv2d`, `nn.ConvTranspose2d`, `nn.GELU` and tuples — nothing version-sensitive. `timm` is never imported by
  the Darcy model.

### Darcy model: entry point, config, resolution behaviour
- Class `MgNO_DC` in `models.py` (used for Darcy rough, Darcy multiscale and Pipe; `MgNO_DC_smooth` for Darcy
  smooth; `MgNO_NS`, `MgNO_helm*` for the other benchmarks).
- Signature: `MgNO_DC(num_layer, num_channel_u, num_channel_f, num_classes, num_iteration, in_chans=1,
  normalizer=None, output_dim=1, activation='gelu', padding_mode='zeros')`. Note: `in_chans`, `num_classes` and
  `output_dim` are accepted but **unused**; the input channel count is `num_channel_f`, and the head is hard-coded
  `nn.Conv2d(num_channel_u, 1, kernel_size=1, bias=False)` (scalar output map). Forward: `u = act(MgConv_DC(u) +
  Conv1x1(u))` for `num_layer` layers, then the 1x1 head, then optional `normalizer.decode`.
- `MgConv_DC` = one multi-channel V-cycle: per level, `num_iteration[l][0]` pre-smoothing steps `u <- u + S(f - A u)`
  (`A`: 3x3 conv u->f, `S`: 3x3 conv f->u, both `bias=False`, `padding=1`, `padding_mode='zeros'`; the first step is
  `u = S f`), restriction `Pi` (3x3, stride 2, u->u) and `R` (3x3, stride 2, f->f), prolongation `ConvTranspose2d`
  4x4 stride 2 padding 1, then `num_iteration[l][1]` post-smoothing steps on the way up. No LayerNorm (the
  Helmholtz variants hard-code `LayerNorm([C,101,101])` etc.; `MgConv_DC`/`MgNO_DC` contain **no hard-coded
  resolution**).
- Paper config, Darcy (Table 7): 6 levels, channels [24,24,24,24,24,24], 3x3 convs with zeros padding 1,
  R = 3x3 stride 2, P = ConvTranspose 4x4 stride 2, no layer norm, 4 layers (rough, multiscale; 5 for smooth),
  GELU. README command for both Darcy rough and Darcy multiscale:
  `python darcy.py --data darcy20c6|a4f1 --model_type MgNO_DC --sample_x --normalizer --normalizer_type GN [--GN]
  --num_channel_u 24 --num_layer 4 --num_iteration 10 10 10 10 10 20 --lr 5e-4 --batch_size 8 --epochs 500`
  (`--GN` additionally standardises the input for a4f1). `argparse` with `type=list` turns `"10"` into `['1','0']`
  and `darcy.py` casts to int, so `num_iteration = [[1,0],[1,0],[1,0],[1,0],[1,0],[2,0]]` (six levels, one
  pre-smoothing step per level, two on the coarsest, no post-smoothing). Table 7 prints the smoothing list as
  `[[1,1],...,[2]]`; the README/argparse form is the one whose parameter count matches Table 1, so treat the
  paper table as a typo. Training: Adam, OneCycleLR cosine, lr 5e-4 -> 2.5e-6, batch 8, H1 loss
  (`utilities3.HsLoss(d=2,p=2,k=1)`), 500 epochs (rough) / 300 (multiscale), one A100.
- Data: `darcy20c6` = `darcy_alpha2_tau5_512_{train,test}.mat` (512^2, 1280/112/112), `--sample_x` slices
  `coeff[:, ::2, ::2]` -> 256^2; `a4f1` = `mul_tri_{train,test}.mat` (1023^2 P1-FEM, 1000/100/100), `::4` -> 256^2.
  Input is the single coefficient channel `(N,1,H,W)` (no coordinate channels); target `(N,H,W)` standardised by a
  `GaussianNormalizer` (scalar mean/std) whose `decode` is applied inside the model.
- Parameter count: paper Table 1 (Darcy rough, 256^2): **MgNO 0.57 M**, MgNO-high-in 0.85 M (512^2 input).
  Analytic count of `MgNO_DC(4, 24, 1, 1, [[1,0]]*5+[[2,0]])` = **572,661** (matches). With a 3-channel input
  (`num_channel_f=3`) = 578,685. Reported errors (x1e-2): rough L2 0.339 / H1 1.380; multiscale 0.715 / 1.756;
  6.6 s per training iteration-epoch on an A100.
- 128^2 and 256^2 single-channel grids: supported without change. Six levels mean five stride-2 restrictions
  (256 -> 8, 128 -> 4); 3x3/stride-2/pad-1 convs and 4x4/stride-2/pad-1 transposed convs are exact inverses for
  even sizes, so H and W must be divisible by 2^(levels-1) = 32 (both our resolutions are). Zero padding
  implements the Dirichlet boundary, which matches our maps (zero current/voltage outside the domain is not our
  convention but nodata is zero-filled by the loader, and the paper itself uses zeros for Darcy).

### Pure-PyTorch module? Vendoring plan
Yes. **Verdict: USABLE.**
1. Copy from `models.py` @ `3a68a90` the classes `MgIte`, `MgIte_init`, `Restrict`, `MgConv_DC`, `MgNO_DC`
   (and the activation lookup) into `ampscape/models/mgno.py` (about 150 lines). Drop the `torchinfo` and
   `utilities3` imports and the `__main__` block. Do not copy `darcy.py`, `utilities3.py`, `Adam.py`.
2. Keep the licence: file header `# Adapted from https://github.com/xlliu2017/MgNO (commit 3a68a90), MIT License,
   Copyright (c) 2024 Xinliang Liu` plus the full MIT text in `THIRD_PARTY_LICENSES.md` (new file; also list it in
   `docs/licenses.md`'s software section when that is written). Cite He, Liu & Xu (ICLR 2024) in the baselines
   table.
3. Adapter for our loader (`ampscape.models.common.make_inputs` -> `(B, C, H, W)` with C = 3 for T1/T1W/T1R
   [log R, nodata mask, focal], 4 for T3 [+ ground], 3 for T4, +1 with the `dist` channel):
   `class MgNO(nn.Module)` wrapper with signature `MgNO(in_channels, out_channels=1, width=24, layers=4, levels=6,
   coarse_iters=2, padding_mode="zeros")` that builds `MgNO_DC(num_layer=layers, num_channel_u=width,
   num_channel_f=in_channels, num_classes=out_channels, num_iteration=[[1,0]]*(levels-1)+[[coarse_iters,0]],
   normalizer=None)`. Two one-line edits to the vendored class, both documented in the header: replace the
   hard-coded head `nn.Conv2d(num_channel_u, 1, ...)` by `nn.Conv2d(num_channel_u, output_dim, ...)` (T3 predicts
   voltage + current), and assert `H % 2**(levels-1) == 0`. Target standardisation stays in our loader
   (`normalizer=None`); no coordinate channels (the paper uses none).
4. Register `"mgno"` in `ampscape/models/__init__.py::build_model` and `MODEL_CONFIGS` with
   `{"width": 24, "layers": 4, "levels": 6}` as the paper configuration, plus a `"w32"` variant for the width sweep.
5. Smoke tests (CPU, no data): forward/backward at 128^2 and 256^2 with C = 3 and 4; `sum(p.numel())` ==
   578,685 for C = 3, width 24, 4 layers, 6 levels; output shape `(B, out_channels, H, W)`; `torch.compile` not
   required. Train on tier S first (the model is ~10x smaller than our FNO-m64).

---

## (b) HANO — Liu, Xu, Cao, Zhang, "Mitigating spectral bias for the multiscale operator learning" (arXiv 2210.10890; J. Comput. Phys. 506:112944, 2024)

### Repository
- URL: https://github.com/xlliu2017/HANO — this is the URL printed in the paper (JCP §3.9 "The code and datasets
  can be accessed at ... github.com/xlliu2017/HANO"). GitHub API: created 2023-05-21, `license.spdx_id = MIT`,
  4 stars, no tags.
- History: `main` contains **21 commits, all dated 2026-05-31 to 2026-10-01 and all authored by
  `copilot-swe-agent[bot]`** (merged by the owner): "Refactor repository into hano package structure", "Implement
  multigrid HANO backbone", "Migrate HANO implementation", "Polish HANO legacy config notes", "docs: promote NeurIPS
  2023 HANO paper in README" (PR #2, merged 2026-10-01). The 2023 commits are no longer on any branch (branches:
  `main` and three `copilot/*`), so the code that produced the paper's numbers cannot be checked out.
- Root files: `.gitignore`, `Error_Spectrum.png`, `FNO_multiscale.py`, `LICENSE.txt`, `README.md`, `T_lossfunc.py`,
  `baseline.png`, `environment.yml`, `eval.py`, `ex_darcyrough.py` / `ex_darcysmooth.py` / `ex_multiscale.py` /
  `ex_ns.py` (6-line `runpy` shims to `experiments/`), `models.py` (re-export shim), `requirements.txt`,
  `spectral_bias.png`, `train.py`, `utils.py`; folders `experiments/`, `hano/` (`data.py`, `losses.py`,
  `trainer.py`, `utils.py`, `models/{__init__,baselines,components,fno,hano,hano_legacy}.py`), `scripts/`
  (`train.py`, `eval.py`), `spectral_bias/`. No `setup.py`/`pyproject.toml`, although the README says
  `pip install -e .`.
- README integrity: the README (added by Copilot PR #2) cites a "NeurIPS 2023" paper
  `@inproceedings{liu2023hano, author = {Liu, Xinliang and Yao, Bo and Ying, Lexing and Xing, Eric P.}, ...
  url = {https://arxiv.org/abs/2311.10189}}`. arXiv 2311.10189 is "TAPA-CS: Enabling Scalable Accelerator Design on
  Distributed HBM-FPGAs" (Prakriya et al.), unrelated; the real paper is arXiv 2210.10890 by Liu, Xu, Cao, Zhang,
  and HANO was not a NeurIPS 2023 paper. The README also claims the new multigrid-attention backbone is "described
  in the JCP 2024 follow-up"; the JCP text (read in full) describes hierarchical window attention, not that
  backbone. **Do not cite the README; cite only arXiv 2210.10890 / JCP 506:112944.**

### Licence
- File `LICENSE.txt`, MIT License, "Copyright (c) 2021 Shuhao Cao" (co-author; the code base descends from Cao's
  Galerkin-transformer release). SPDX: `MIT`. Licence-wise the code could be vendored.

### Framework and pinned dependencies
- README: "PyTorch >= 1.12, timm, scipy, h5py, tqdm, torchinfo". `requirements.txt` is byte-identical to MgNO's
  (`torch==1.13.0`, `timm==0.6.12`, `numpy==1.23.5`, `scipy==1.9.3`, `h5py==3.7.0`, `torchinfo==1.7.2`,
  `tqdm==4.64.1`); `environment.yml` pins Python 3.9.13, pytorch 1.13.1 + CUDA 11.6 and ~60 unrelated pip packages
  (wandb, ray, deepxde, code-server, ...).
- Conflicts with torch 2.x: the pins themselves (would downgrade torch/numpy); `hano/models/components.py` and
  `hano_legacy.py` import `timm.models.layers` (`DropPath`, `to_2tuple`, `trunc_normal_`) — a path deprecated
  since timm 0.9 (still importable with a warning in timm 1.x; the three symbols are trivially replaceable);
  `hano/data.py` uses `scipy.interpolate.interp2d`, removed in SciPy 1.14, so the training pipeline does not run on
  a current SciPy without edits. The current `hano/models/hano.py` itself imports only `torch`.

### What the repository actually contains
Two different models are both called HANO:
1. `hano/models/hano.py::HANO2d` (aliases `HANO`, `MgConv_DC_3`; what `experiments/ex_darcyrough.py`,
   `ex_multiscale.py` and `scripts/train.py` run). Introduced by the Copilot commit "Implement multigrid HANO
   backbone". Architecture: 3x3 conv patch embedding -> `num_layers` x `MultigridAttentionBlock` (V-cycle whose
   smoother `Conv2dAttention` generates 2 keys + 2 values per pixel with a 3x3 conv, applies a 2-way softmax over
   `einsum("bchw,bgchw->bghw")`, GroupNorm; channel width `(level+1) x feature_dim`; stride-2 3x3 restrictions of
   state/key/value; 4x4 stride-2 transposed-conv prolongation) -> 3x3 output conv -> Dirichlet crop + zero pad ->
   `(B, H, W, 1)`. Config for "Darcy rough": `feature_dim 64, num_layers 1, num_iterations [[1,0],[1,0],[1,0]],
   patch_size 4, subsample_attn 2, patch_padding 1, res_input 513, res_att 257, res_output 256, xGN True, H1 loss,
   batch 8, 500 epochs` (the patch/attention keys are ignored by `HANO2d`); "multiscale": `num_iterations
   [[2,0],[4,0],[2,0]]`, `res_input 1024`, 300 epochs. Analytic parameter counts: **5,244,800** (Darcy rough) and
   8,490,112 (multiscale). This is pure PyTorch and resolution-agnostic — but it is **not the architecture of
   arXiv 2210.10890/JCP 2024** (no window attention, no reduce/decompose hierarchy, no spectral decoder) and has
   no paper of its own. Pre-trained checkpoints `darcyrough_res256.pt`, `multiscale_res256.pt` (Google Drive) are
   for this model and cannot be matched to the paper's tables.
2. `hano/models/hano_legacy.py::LegacyHANO2d` (alias `LegacyHANO`), "preserved for reference". This is the paper's
   design: `PatchEmbed` (conv, kernel `patch_size`, stride `subsample_attn`, padding `patch_padding`, LayerNorm)
   -> `HAttention` (Swin-style `HTransformerBlock` window attention in `ReduceLayer`s with `PatchMerging` 2x2
   down-sampling, `DecomposeLayer` reconstruction with skip additions) -> `Decodermap` (FNO-style
   `SpectralConv2d` x `num_spectral_layers`, pads by `F_padding`, crops to `res_output`) -> MLP -> Dirichlet crop.
   Required config keys: `in_dim` (default 1), `feature_dim`, `res_att`, `patch_size`, `subsample_attn`,
   `patch_padding`, `depths`, `num_heads`, `window_size`, `F_modes`, `F_width`, `num_spectral_layers`,
   `mlp_hidden_dim`, `F_padding`, `res_output`, `boundary_condition`, `y_norm`. Problems:
   - Paper Table 1 config: patch size 4 / padding 0, **5 levels**, down-sampling ratio 4, feature dimension
     {32,32,32,32,32}, window size {3,3,3,3,3}, LayerNorm after attention, **2 cycles**. The only config in the repo
     that carries legacy keys (`scripts/train.py`: `depths [1,1,1]`, `num_heads [1,1,1]`, `window_size [4,4,4]`,
     `feature_dim 64`, `patch_size 4`, `F_modes 12`, `num_spectral_layers 5`) is 3 levels, dim 64, window 4 — and
     that script sets `model = "HANO"`, which `hano/trainer.py` maps to the *new* `HANO2d` (which silently turns
     `depths` into `num_iterations`). `LegacyHANO2d` is not instantiated anywhere.
   - Resolution handling is tied to the authors' 2^k+1 FEM-node grids: `res_input 513 -> res_att 257 -> res_output
     256` (decoder pads then crops). `HTransformerBlock` partitions windows with a plain `view(B, H//ws, ws, W//ws,
     ws, C)` and has no padding path, so `res_att` must be divisible by the window size at every level; with the
     stored config (257, window 4) it is not. Whether the migrated module runs at all cannot be established
     without executing it (which WP6 excludes). For our 128^2/256^2 inputs one would have to invent a new
     embedding/crop convention (e.g. pad to 129/257), i.e. a different model from the paper's.
   - The paper reports no Darcy parameter count (only Navier-Stokes 7,629,350 and Helmholtz 11.35 M); Table 2 gives
     Darcy rough runtime 9.62 s and 1.21 GB memory, errors (x1e-2, H1-trained) rough L2 0.343 +- 0.006 / H1 1.846
     +- 0.023, multiscale 0.580 / 1.749. There is no way to confirm that any configuration of `hano_legacy.py`
     reproduces these numbers.

### Pure-PyTorch module? Verdict
Licence (MIT) and framework (PyTorch; `timm` only for three replaceable helpers in the legacy path) would allow
vendoring. **Verdict: NOT USABLE** as an "official HANO" baseline, because:
1. the model the repository ships and trains as `HANO` is an unpublished architecture unrelated to the paper;
2. the paper's architecture exists only as a bot-migrated legacy module with no runnable experiment, a config
   that contradicts the paper's Table 1, hard assumptions on 2^k+1 attention grids, and no surviving original
   history — any number we produced could not honestly be labelled "HANO (official implementation)";
3. the repository's own documentation is unreliable (fabricated citation, wrong paper attribution), so results
   would need caveats that defeat the purpose of an official baseline.

Fallbacks (owner's choice, not done in WP6): (i) keep HANO as related work only (current state of
`docs/prior_art.md` and the paper's related-work section); (ii) treat our existing Swin/ViT-UNet baseline
(`ampscape/models/vit.py`) as the hierarchical-attention representative; (iii) if a HANO-style model is wanted,
re-implement from Table 1 of the JCP paper and label it "HANO-style re-implementation (unverified against the
authors' code)". Option (iii) is a separate work package.

---

## Shared notes
- Both repositories' `requirements.txt` files are identical and pin torch 1.13.0; neither pin is needed for the
  model code we would vendor. Our `.venv` has torch 2.13.0+cu130.
- Both repositories were restructured by Copilot agents in 2026 (MgNO: docstrings only, verified equivalent; HANO:
  architecture replaced, history rewritten). Any future re-check should pin commit hashes, not `main`.
- Datasets (Google Drive) were not downloaded (out of WP6 scope; no gate needed).
