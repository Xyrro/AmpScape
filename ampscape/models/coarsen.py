"""Non-learned baseline (brief §12.1): coarsen the resistance ×f, solve with the reference solver on the
coarse grid, upsample the outputs back.

Coarsening rules (documented): resistance → geometric mean over f×f blocks; NoData → block is NoData if
more than half of it is; focal labels → any pixel of the block carries the label (a region may grow);
source strength → block sum (T3, keeps Σ S = 1) or block mean (T4); ground → any. Omniscape radius and
block size are divided by f (block rounded to the nearest odd ≥ 1). Outputs: current maps are
upsampled bilinearly; Reff is taken as is (same focal labels). Inference time = coarsening + coarse
solve + upsampling.
"""

from __future__ import annotations

import json
import time

import h5py
import numpy as np
from scipy import ndimage

GZIP = {"compression": "gzip", "compression_opts": 4}


def block_reduce(a: np.ndarray, f: int, how: str) -> np.ndarray:
    H, W = a.shape
    b = a[: H - H % f, : W - W % f].reshape(H // f, f, W // f, f)
    if how == "gmean":
        return np.exp(np.log(np.maximum(b, 1e-12)).mean(axis=(1, 3)))
    if how == "mean":
        return b.mean(axis=(1, 3))
    if how == "sum":
        return b.sum(axis=(1, 3))
    if how == "any":
        return b.max(axis=(1, 3))
    if how == "majority_bool":
        return b.mean(axis=(1, 3)) > 0.5
    raise ValueError(how)


def coarsen_labels(focal: np.ndarray, f: int) -> np.ndarray:
    H, W = focal.shape
    b = focal[: H - H % f, : W - W % f].reshape(H // f, f, W // f, f).max(axis=(1, 3))
    return b.astype(np.int32)


def upsample(a: np.ndarray, f: int, shape: tuple[int, int]) -> np.ndarray:
    z = ndimage.zoom(np.asarray(a, dtype=np.float64), f, order=1)
    out = np.zeros(shape, dtype=np.float32)
    h, w = min(shape[0], z.shape[0]), min(shape[1], z.shape[1])
    out[:h, :w] = z[:h, :w]
    return out


def write_coarse_inputs(final_h5: str, out_h5: str, sample_ids: list[str], f: int = 4) -> dict[str, dict]:
    """Build a Julia-solvable inputs shard at 1/f resolution from a final shard; returns per-sample timings."""
    timings = {}
    with h5py.File(final_h5, "r") as fi, h5py.File(out_h5, "w") as fo:
        g_all = fo.create_group("samples")
        for sid in sample_ids:
            t0 = time.perf_counter()
            gs = fi[sid]
            R = gs["inputs"]["resistance"][...]
            nd = gs["inputs"]["nodata_mask"][...] > 0
            Rc = block_reduce(np.where(nd, np.nan, R), f, "gmean")
            ndc = block_reduce(nd.astype(float), f, "majority_bool") | ~np.isfinite(Rc)
            Rc = np.where(ndc, 1.0, np.nan_to_num(Rc, nan=1.0)).astype(np.float32)
            g = g_all.create_group(sid)
            meta = json.loads(gs.attrs["meta"])
            g.attrs["tier"] = meta["tier"]
            g.attrs["omni_radius"] = max(1, int(round(meta["omniscape"]["radius"] / f)))
            bs = max(1, int(round(meta["omniscape"]["block_size"] / f)))
            g.attrs["omni_block_size"] = bs if bs % 2 == 1 else bs + 1
            g.attrs["cg_baseline"] = 0
            g.attrs["meta"] = json.dumps({**meta, "coarsen_factor": f})
            gi = g.create_group("inputs")
            gi.create_dataset("resistance", data=Rc, **GZIP)
            gi.create_dataset("nodata_mask", data=ndc.astype(np.uint8), **GZIP)
            gc_all = g.create_group("configs")
            for cname, gc in gs["configs"].items():
                kind = gc.attrs["kind"]
                gco = gc_all.create_group(cname)
                gco.attrs["kind"] = kind
                if "focal_mask" in gc["inputs"]:
                    fc = coarsen_labels(gc["inputs"]["focal_mask"][...], f)
                    fc[ndc] = 0
                    gco.create_dataset("focal_mask", data=fc, **GZIP)
                if "source_strength" in gc["inputs"]:
                    how = "sum" if kind == "advanced" else "mean"
                    sc = block_reduce(gc["inputs"]["source_strength"][...].astype(np.float64), f, how)
                    sc[ndc] = 0
                    gco.create_dataset("source_strength", data=sc.astype(np.float32), **GZIP)
                if "ground" in gc["inputs"]:
                    gr = block_reduce(gc["inputs"]["ground"][...].astype(float), f, "any") > 0
                    gr[ndc] = False
                    gco.create_dataset("ground", data=gr.astype(np.int8), **GZIP)
                if kind == "omniscape":
                    gco.attrs["source_threshold"] = float(gc.attrs.get("source_meta", "{}") and json.loads(gc.attrs["source_meta"]).get("source_threshold", 0.0))
            timings[sid] = time.perf_counter() - t0
    return timings


def write_predictions(final_h5: str, coarse_outputs_h5: str, pred_h5: str, f: int, coarsen_time: dict[str, float],
                      append: bool = False) -> int:
    """Upsample coarse solver outputs into the predictions format; inference_time = coarsen + solve + upsample."""
    n = 0
    with h5py.File(final_h5, "r") as fi, h5py.File(coarse_outputs_h5, "r") as fc, h5py.File(pred_h5, "a" if append else "w") as fp:
        for sid in fc["samples"]:
            if sid not in fi or "complete" not in fc["samples"][sid].attrs:
                continue
            shape = fi[sid]["inputs"]["resistance"].shape
            gp = fp.require_group(sid)
            for cname, go in fc["samples"][sid]["outputs"].items():
                st = json.loads(go.attrs["stats"])
                t0 = time.perf_counter()
                g = gp.require_group(cname)
                for k in go:
                    a = go[k][...]
                    if k in ("cum_current", "current", "voltage", "flow_potential", "normalized", "pairwise_current"):
                        if a.ndim == 3:
                            up = np.stack([upsample(x, f, shape) for x in a])
                        else:
                            up = upsample(a, f, shape)
                        if k == "cum_current" and cname == "advanced":
                            continue
                        if k in ("cum_current", "current", "pairwise_current"):
                            up = up / (f * f) if False else up      # node currents are per node: no area scaling (documented)
                        g.create_dataset(k, data=up.astype(np.float32), **GZIP)
                    elif k == "reff":
                        g.create_dataset(k, data=a.astype(np.float64))
                    elif k in ("labels", "pair_index"):
                        g.create_dataset(k, data=a)
                g.attrs["inference_time_s"] = float(coarsen_time.get(sid, 0.0) + st["wall_s"] + (time.perf_counter() - t0))
                g.attrs["coarse_solver"] = st["solver"]
            n += 1
    return n
