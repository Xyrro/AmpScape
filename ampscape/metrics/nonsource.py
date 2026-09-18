"""Non-source-pixel metrics (review addendum WP3).

Currents are singular at injection pixels, so pixel errors there dominate and hide the error on the *matrix* — the
non-source pixels where corridors and pinch points live. These metrics restrict the pixel and top-q metrics to
pixels with zero source strength (T4), and for T1/T3 to pixels outside the focal nodes / sources / grounds plus a
small exclusion halo (Chebyshev radius `halo`, default 2 px) around them. The masks come from the stored inputs
(`focal_mask`, `source_strength`, `ground`), which exist for every task, so nothing is guessed.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from ampscape.metrics import domain, pixel

DEFAULT_HALO = 2


def nonsource_mask(
    kind: str,
    base_mask: np.ndarray,
    focal: np.ndarray | None = None,
    source_strength: np.ndarray | None = None,
    ground: np.ndarray | None = None,
    halo: int = DEFAULT_HALO,
) -> np.ndarray:
    """Boolean mask of evaluable non-source pixels.

    kind in {points, wall_to_wall, regions}: focal pixels (any label) and a `halo` around them are excluded;
    kind == advanced: source pixels (strength > 0) and ground pixels plus the halo are excluded;
    kind == omniscape: pixels with source strength > 0 are excluded (no halo: sources are diffuse, not singular).
    """
    m = np.asarray(base_mask, bool).copy()
    if kind in ("points", "wall_to_wall", "regions"):
        if focal is None:
            raise ValueError("focal mask required")
        src = np.asarray(focal) > 0
    elif kind == "advanced":
        if source_strength is None or ground is None:
            raise ValueError("source_strength and ground required")
        src = (np.asarray(source_strength) > 0) | (np.asarray(ground) > 0)
    elif kind == "omniscape":
        if source_strength is None:
            raise ValueError("source_strength required")
        return m & ~(np.asarray(source_strength) > 0)
    else:
        raise ValueError(kind)
    if halo > 0 and src.any():
        src = ndimage.binary_dilation(src, structure=np.ones((2 * halo + 1, 2 * halo + 1), bool))
    return m & ~src


def all_nonsource(
    pred, target, ns_mask: np.ndarray, total_mask: np.ndarray | None = None
) -> dict[str, float]:
    """rel-L2, log10-ε MAE and top-q IoU (q = 1, 5, 10) on the non-source mask, plus the fraction of evaluable pixels kept."""
    out = {
        "ns_rel_l2": pixel.rel_l2(pred, target, ns_mask),
        "ns_mae_log10eps": pixel.mae_log(pred, target, ns_mask),
        "ns_top1_iou": domain.top_q_iou(pred, target, ns_mask, 1.0),
        "ns_top5_iou": domain.top_q_iou(pred, target, ns_mask, 5.0),
        "ns_top10_iou": domain.top_q_iou(pred, target, ns_mask, 10.0),
    }
    denom = (
        int(np.asarray(total_mask, bool).sum())
        if total_mask is not None
        else int(np.asarray(ns_mask).size)
    )
    out["ns_fraction"] = float(np.asarray(ns_mask, bool).sum() / max(denom, 1))
    return out
