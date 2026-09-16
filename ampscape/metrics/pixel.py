"""Pixel-level metrics on maps (brief §11), all masked: NoData pixels and, for T1W, the strip pixels are excluded.

Maps are compared in log10(C + ε·max C) space for the log metrics (``transforms.log10_eps``); MSE and
relative L2 are computed on the raw values; SSIM and PSNR are secondary metrics computed on the
log-transformed maps scaled to [0, 1] by the target's range.
"""

from __future__ import annotations

import numpy as np

from ampscape.metrics.transforms import log10_eps


def _masked(pred: np.ndarray, target: np.ndarray, mask: np.ndarray | None):
    p = np.asarray(pred, dtype=np.float64).squeeze()
    t = np.asarray(target, dtype=np.float64).squeeze()
    if p.shape != t.shape:
        raise ValueError(f"shape mismatch {p.shape} vs {t.shape}")
    m = np.ones(t.shape, bool) if mask is None else np.asarray(mask, bool).squeeze()
    return p, t, m


def mse(pred, target, mask=None) -> float:
    p, t, m = _masked(pred, target, mask)
    return float(np.mean((p[m] - t[m]) ** 2))


def mae_log(pred, target, mask=None) -> float:
    """MAE in log10(C + ε·max C) space; ε·max is taken from the target so both maps share the shift."""
    p, t, m = _masked(pred, target, mask)
    cmax = float(np.max(t[m])) if m.any() else 0.0
    if cmax <= 0:
        return 0.0
    from ampscape.metrics.transforms import EPS

    lp = np.log10(np.maximum(p, 0.0) + EPS * cmax)
    lt = np.log10(np.maximum(t, 0.0) + EPS * cmax)
    return float(np.mean(np.abs(lp[m] - lt[m])))


def rel_l2(pred, target, mask=None) -> float:
    p, t, m = _masked(pred, target, mask)
    denom = np.linalg.norm(t[m])
    return float(np.linalg.norm(p[m] - t[m]) / denom) if denom > 0 else float("nan")


def _to01(a, lo, hi):
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0) if hi > lo else np.zeros_like(a)


def psnr(pred, target, mask=None) -> float:
    """PSNR (dB) of the log10-ε maps scaled to [0, 1] by the target's range (secondary metric)."""
    p, t, m = _masked(pred, target, mask)
    lp, lt = log10_eps(np.where(m, p, 0)), log10_eps(np.where(m, t, 0))
    lo, hi = float(lt[m].min()), float(lt[m].max())
    e = np.mean((_to01(lp, lo, hi)[m] - _to01(lt, lo, hi)[m]) ** 2)
    return float("inf") if e == 0 else float(10 * np.log10(1.0 / e))


def ssim(pred, target, mask=None) -> float:
    """SSIM of the log10-ε maps scaled to [0, 1] (secondary metric); masked pixels are set to the target value."""
    from skimage.metrics import structural_similarity

    p, t, m = _masked(pred, target, mask)
    lp, lt = log10_eps(np.where(m, p, 0)), log10_eps(np.where(m, t, 0))
    lo, hi = float(lt[m].min()), float(lt[m].max())
    a, b = _to01(lp, lo, hi), _to01(lt, lo, hi)
    a = np.where(m, a, b)
    return float(structural_similarity(a, b, data_range=1.0))


def all_pixel(pred, target, mask=None) -> dict[str, float]:
    return {
        "mse": mse(pred, target, mask),
        "mae_log10eps": mae_log(pred, target, mask),
        "rel_l2": rel_l2(pred, target, mask),
        "ssim": ssim(pred, target, mask),
        "psnr_db": psnr(pred, target, mask),
    }
