"""Non-learned baseline (brief §12.1): coarsen the resistance ×f, solve with the reference solver on the
coarse grid, upsample the outputs back.

Coarsening rules (documented): resistance → geometric mean over f×f blocks; NoData → block is NoData if
more than half of it is; focal labels → any pixel of the block carries the label (a region may grow);
source strength → block sum (T3, keeps Σ S = 1) or block mean (T4); ground → any, and a block that holds both
source and ground becomes ground only (Circuitscape leaves such nodes ungrounded), sources on coarse components
without a ground are dropped (majority NoData can isolate islands), sources renormalised. Omniscape radius and
block size are divided by f (block rounded to the nearest odd ≥ 1). Outputs: current maps are
upsampled bilinearly and, for pairwise/advanced maps, divided by f (a coarse node collects the flow crossing f fine
pixels of width; Omniscape maps are left unscaled because their sources were mean-pooled); coarse focal pixels are
in-filled from their nearest non-focal neighbour before upsampling; for T3 the coarse injection (block-summed sources)
is removed before scaling and the fine injection added back (node current = through-flow + injection); focal
pixels are reset to the exact 1 A per pair; Reff is taken as is (same focal labels). Inference time = coarsening +
coarse solve + upsampling.
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


def coarsen_nodata(R: np.ndarray, nd: np.ndarray, f: int) -> tuple[np.ndarray, np.ndarray]:
    """Geometric-mean resistance and majority NoData of a fine landscape at 1/f."""
    Rc = block_reduce(np.where(nd, np.nan, R), f, "gmean")
    ndc = block_reduce(nd.astype(float), f, "majority_bool") | ~np.isfinite(Rc)
    return np.where(ndc, 1.0, np.nan_to_num(Rc, nan=1.0)).astype(np.float32), ndc


def coarsen_advanced(
    S: np.ndarray, G: np.ndarray, ndc: np.ndarray, f: int
) -> tuple[np.ndarray, np.ndarray]:
    """Coarse T3 sources (block sum) and ground (any); ground wins where a block holds both, sources renormalised.

    Circuitscape leaves a node that is both source and ground ungrounded (verified on the mini: 27 of 32 coarse
    ground nodes sat at up to 4.7 V), so mixed blocks must be resolved before the coarse solve.
    """
    sc = block_reduce(S.astype(np.float64), f, "sum")
    gr = block_reduce(G.astype(float), f, "any") > 0
    sc[ndc] = 0
    gr[ndc] = False
    total = sc.sum()
    sc[gr] = 0
    # a coarse component (8-connected non-NoData pixels) without a ground node cannot carry current: drop its sources
    lab, n = ndimage.label(~ndc, structure=np.ones((3, 3)))
    if n > 1:
        grounded = np.isin(lab, np.unique(lab[gr & (lab > 0)]))
        sc[~grounded] = 0
    if sc.sum() > 0 and total > 0:
        sc *= total / sc.sum()
    return sc, gr


def write_coarse_inputs(
    final_h5: str, out_h5: str, sample_ids: list[str], f: int = 4
) -> dict[str, dict]:
    """Build a Julia-solvable inputs shard at 1/f resolution from a final shard; returns per-sample timings."""
    timings = {}
    skipped: list[tuple[str, str]] = []
    with h5py.File(final_h5, "r") as fi, h5py.File(out_h5, "w") as fo:
        g_all = fo.create_group("samples")
        for sid in sample_ids:
            t0 = time.perf_counter()
            gs = fi[sid]
            R = gs["inputs"]["resistance"][...]
            nd = gs["inputs"]["nodata_mask"][...] > 0
            Rc, ndc = coarsen_nodata(R, nd, f)
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
                if "focal_mask" in gc["inputs"]:
                    fc = coarsen_labels(gc["inputs"]["focal_mask"][...], f)
                    fc[ndc] = 0
                    fine_labels = set(np.unique(gc["inputs"]["focal_mask"][...])) - {0}
                    comp, _ = ndimage.label(~ndc, structure=np.ones((3, 3)))
                    if set(np.unique(fc)) - {0} != fine_labels or len(set(comp[fc > 0])) != 1:
                        # a focal label vanished under coarsening (NoData majority), or the coarse focal nodes no longer
                        # share one component (Circuitscape writes no map for disconnected pairs)
                        skipped.append((sid, cname))
                        continue
                gco = gc_all.create_group(cname)
                gco.attrs["kind"] = kind
                if "focal_mask" in gc["inputs"]:
                    gco.create_dataset("focal_mask", data=fc, **GZIP)
                if kind == "advanced":
                    sc, gr = coarsen_advanced(
                        gc["inputs"]["source_strength"][...], gc["inputs"]["ground"][...], ndc, f
                    )
                    if sc.sum() <= 0 or not gr.any():
                        del gc_all[cname]
                        skipped.append((sid, cname))
                        continue
                    gco.create_dataset("source_strength", data=sc.astype(np.float32), **GZIP)
                    gco.create_dataset("ground", data=gr.astype(np.int8), **GZIP)
                elif "source_strength" in gc["inputs"]:
                    sc = block_reduce(
                        gc["inputs"]["source_strength"][...].astype(np.float64), f, "mean"
                    )
                    sc[ndc] = 0
                    gco.create_dataset("source_strength", data=sc.astype(np.float32), **GZIP)
                if kind == "omniscape":
                    gco.attrs["source_threshold"] = float(
                        gc.attrs.get("source_meta", "{}")
                        and json.loads(gc.attrs["source_meta"]).get("source_threshold", 0.0)
                    )
            timings[sid] = time.perf_counter() - t0
    if skipped:
        print(
            f"coarsen: {len(skipped)} configurations undefined on the coarse grid and skipped: {skipped[:5]}{' ...' if len(skipped) > 5 else ''}"
        )
    return timings


def infill_focal(a: np.ndarray, focal_coarse: np.ndarray) -> np.ndarray:
    """Replace coarse focal pixels by the value of the nearest non-focal coarse pixel.

    A coarse focal node carries the full injected current of its pair; upsampled naively it stamps a block of f x f
    fine pixels (a strip f fine pixels wide) with that value, of which only the true focal pixels should carry it.
    """
    m = focal_coarse > 0
    if not m.any() or m.all():
        return a
    idx = ndimage.distance_transform_edt(m, return_distances=False, return_indices=True)
    return a[tuple(idx)]


def write_predictions(
    final_h5: str,
    coarse_outputs_h5: str,
    pred_h5: str,
    f: int,
    coarsen_time: dict[str, float],
    append: bool = False,
) -> int:
    """Upsample coarse solver outputs into the predictions format; inference_time = coarsen + solve + upsample."""
    n = 0
    with (
        h5py.File(final_h5, "r") as fi,
        h5py.File(coarse_outputs_h5, "r") as fc,
        h5py.File(pred_h5, "a" if append else "w") as fp,
    ):
        for sid in fc["samples"]:
            if sid not in fi or "complete" not in fc["samples"][sid].attrs:
                continue
            shape = fi[sid]["inputs"]["resistance"].shape
            gp = fp.require_group(sid)
            for cname, go in fc["samples"][sid]["outputs"].items():
                st = json.loads(go.attrs["stats"])
                t0 = time.perf_counter()
                g = gp.require_group(cname)
                focal = None
                if (
                    cname in fi[sid]["configs"]
                    and "focal_mask" in fi[sid]["configs"][cname]["inputs"]
                ):
                    focal = fi[sid]["configs"][cname]["inputs"]["focal_mask"][...]
                    focal_c = coarsen_labels(focal, f)
                pi = go["pair_index"][...] if "pair_index" in go else None
                s_fine = None
                if cname == "advanced" and cname in fi[sid]["configs"]:
                    s_fine = fi[sid]["configs"][cname]["inputs"]["source_strength"][...].astype(
                        np.float64
                    )
                    _, ndc = coarsen_nodata(
                        fi[sid]["inputs"]["resistance"][...],
                        fi[sid]["inputs"]["nodata_mask"][...] > 0,
                        f,
                    )
                    s_coarse, _ = coarsen_advanced(
                        s_fine, fi[sid]["configs"][cname]["inputs"]["ground"][...], ndc, f
                    )
                for k in go:
                    a = go[k][...]
                    if k in (
                        "cum_current",
                        "current",
                        "voltage",
                        "flow_potential",
                        "normalized",
                        "pairwise_current",
                    ):
                        if k == "current" and s_fine is not None:
                            # node current = max(inflow, outflow) = inflow + injected at source nodes; the coarse node
                            # injects the block sum (f^2 fine sources) while its through-flow scales with f -> remove the
                            # coarse injection before scaling and add back the fine injection afterwards
                            a = a - s_coarse[: a.shape[0], : a.shape[1]]
                        if (
                            k in ("cum_current", "current", "pairwise_current")
                            and focal is not None
                        ):
                            if a.ndim == 3:
                                a = np.stack(
                                    [
                                        infill_focal(
                                            x,
                                            np.isin(focal_c, pi[q]) if pi is not None else focal_c,
                                        )
                                        for q, x in enumerate(a)
                                    ]
                                )
                            else:
                                a = infill_focal(a, focal_c)
                        if a.ndim == 3:
                            up = np.stack([upsample(x, f, shape) for x in a])
                        else:
                            up = upsample(a, f, shape)
                        if k == "cum_current" and cname == "advanced":
                            continue
                        if (
                            k in ("cum_current", "current", "pairwise_current")
                            and cname != "omniscape"
                        ):
                            # pairwise / advanced: a coarse node collects the flow crossing a width of f fine pixels ->
                            # divide by f for current per fine pixel; focal pixels (exactly 1 A per pair) are restored
                            # below. Omniscape sources were mean-pooled, so its maps are already per-pixel scale.
                            up = up / f
                            if k == "current" and s_fine is not None:
                                up = np.maximum(up + s_fine, 0.0)
                        g.create_dataset(k, data=up.astype(np.float32), **GZIP)
                    elif k == "reff":
                        g.create_dataset(k, data=a.astype(np.float64))
                    elif k in ("labels", "pair_index"):
                        g.create_dataset(k, data=a)
                if focal is not None:
                    if "pairwise_current" in g:
                        pc = g["pairwise_current"][...]
                        for q in range(pc.shape[0]):
                            labs = pi[q] if pi is not None else np.unique(focal[focal > 0])
                            pc[q][np.isin(focal, labs)] = 1.0
                        g["pairwise_current"][...] = pc
                        g["cum_current"][...] = pc.sum(axis=0)
                    elif "cum_current" in g and cname.startswith("wall"):
                        c = g["cum_current"][...]
                        c[focal > 0] = 1.0
                        g["cum_current"][...] = c
                g.attrs["inference_time_s"] = float(
                    coarsen_time.get(sid, 0.0) + st["wall_s"] + (time.perf_counter() - t0)
                )
                g.attrs["coarse_solver"] = st["solver"]
            n += 1
    return n
