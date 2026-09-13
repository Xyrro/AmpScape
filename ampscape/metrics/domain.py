"""Domain-level metrics (brief §11). Thresholds are conventions, not validated ecological criteria
(see the dataset card); they are reported for comparison between models only.

* top-q % IoU: IoU between the sets of the q % highest-current valid pixels of prediction and target.
* corridor Dice: Dice coefficient of the corridor masks (pixels above the q-quantile), q = 10 % default.
* pinch-point recall: pinch points of the target = local maxima (3×3 neighbourhood, `min_distance`
  px apart) whose value is in the top p % of valid pixels; recall = fraction of them that have a
  predicted local maximum within `radius` px.
* Spearman rank correlation of valid pixel values.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage, stats


def _prep(pred, target, mask):
    p = np.asarray(pred, dtype=np.float64).squeeze()
    t = np.asarray(target, dtype=np.float64).squeeze()
    m = np.ones(t.shape, bool) if mask is None else np.asarray(mask, bool).squeeze()
    return p, t, m


def top_q_mask(a: np.ndarray, mask: np.ndarray, q_percent: float) -> np.ndarray:
    """Boolean mask of the q % highest values among masked-in pixels (q counted over the masked-in pixels;
    zero-valued pixels are never part of the set, so the set is smaller than q % when fewer pixels carry flow)."""
    n = int(round(mask.sum() * q_percent / 100.0))
    out = np.zeros(a.shape, bool)
    if n <= 0:
        return out
    idx = np.flatnonzero(mask & (a > 0))
    order = idx[np.argsort(-a.ravel()[idx], kind="stable")[:n]]
    out.ravel()[order] = True
    return out


def top_q_iou(pred, target, mask=None, q_percent: float = 5.0) -> float:
    p, t, m = _prep(pred, target, mask)
    a, b = top_q_mask(p, m, q_percent), top_q_mask(t, m, q_percent)
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else float("nan")


def corridor_dice(pred, target, mask=None, q_percent: float = 10.0) -> float:
    p, t, m = _prep(pred, target, mask)
    a, b = top_q_mask(p, m, q_percent), top_q_mask(t, m, q_percent)
    s = a.sum() + b.sum()
    return float(2 * np.logical_and(a, b).sum() / s) if s else float("nan")


def spearman(pred, target, mask=None) -> float:
    p, t, m = _prep(pred, target, mask)
    if m.sum() < 3 or np.ptp(t[m]) == 0 or np.ptp(p[m]) == 0:
        return float("nan")                   # undefined for a constant prediction (e.g. all zeros)
    return float(stats.spearmanr(p[m], t[m]).statistic)


def local_maxima(a: np.ndarray, mask: np.ndarray, min_distance: int = 3) -> np.ndarray:
    size = 2 * min_distance + 1
    mx = ndimage.maximum_filter(np.where(mask, a, -np.inf), size=size, mode="nearest")
    return (a == mx) & mask & np.isfinite(a)


def pinch_points(target: np.ndarray, mask: np.ndarray, top_percent: float = 5.0, min_distance: int = 3) -> np.ndarray:
    """Local maxima (plateaus of zero flow excluded) that are also in the top-p % set."""
    return local_maxima(target, mask, min_distance) & top_q_mask(target, mask, top_percent) & (target > 0)


def pinch_point_recall(pred, target, mask=None, top_percent: float = 5.0, min_distance: int = 3, radius: int = 3) -> float:
    """Fraction of target pinch points with a predicted local maximum within `radius` pixels (NaN if none)."""
    p, t, m = _prep(pred, target, mask)
    gt = pinch_points(t, m, top_percent, min_distance)
    if not gt.any():
        return float("nan")
    pm = local_maxima(p, m, min_distance) & top_q_mask(p, m, top_percent)
    near = ndimage.maximum_filter(pm.astype(np.uint8), size=2 * radius + 1, mode="constant") > 0
    return float(np.logical_and(gt, near).sum() / gt.sum())


def all_domain(pred, target, mask=None) -> dict[str, float]:
    return {"top1_iou": top_q_iou(pred, target, mask, 1.0), "top5_iou": top_q_iou(pred, target, mask, 5.0),
            "top10_iou": top_q_iou(pred, target, mask, 10.0), "corridor_dice_q10": corridor_dice(pred, target, mask, 10.0),
            "pinch_recall": pinch_point_recall(pred, target, mask), "spearman": spearman(pred, target, mask)}
