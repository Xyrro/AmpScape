"""Effective-resistance metrics (T2): over the K(K−1)/2 pairs of a K×K matrix (mask handles padding)."""

from __future__ import annotations

import numpy as np
from scipy import stats


def _pairs(pred: np.ndarray, target: np.ndarray, valid: np.ndarray | None):
    p, t = np.asarray(pred, dtype=np.float64), np.asarray(target, dtype=np.float64)
    K = t.shape[0] if valid is None else int(np.asarray(valid).any(axis=1).sum())
    iu = np.triu_indices(K, k=1)
    return p[:K, :K][iu], t[:K, :K][iu], K


def rel_error(pred, target, valid=None) -> float:
    p, t, _ = _pairs(pred, target, valid)
    return float(np.mean(np.abs(p - t) / t)) if t.size else float("nan")


def mae_log(pred, target, valid=None) -> float:
    p, t, _ = _pairs(pred, target, valid)
    return float(np.mean(np.abs(np.log10(np.maximum(p, 1e-12)) - np.log10(t)))) if t.size else float("nan")


def spearman_pairs(pred, target, valid=None) -> float:
    p, t, _ = _pairs(pred, target, valid)
    if t.size < 3 or np.ptp(p) == 0 or np.ptp(t) == 0:
        return float("nan")
    return float(stats.spearmanr(p, t).statistic)


def nearest_neighbour_agreement(pred, target, valid=None) -> float:
    """Fraction of nodes whose lowest-Reff partner is the same in prediction and target."""
    p, t = np.asarray(pred, dtype=np.float64), np.asarray(target, dtype=np.float64)
    K = t.shape[0] if valid is None else int(np.asarray(valid).any(axis=1).sum())
    if K < 2:
        return float("nan")
    p, t = p[:K, :K].copy(), t[:K, :K].copy()
    np.fill_diagonal(p, np.inf)
    np.fill_diagonal(t, np.inf)
    return float(np.mean(np.argmin(p, axis=1) == np.argmin(t, axis=1)))


def symmetry(pred, valid=None) -> float:
    """‖P − Pᵀ‖ / ‖P‖ over the valid block (0 for a symmetric prediction)."""
    p = np.asarray(pred, dtype=np.float64)
    K = p.shape[0] if valid is None else int(np.asarray(valid).any(axis=1).sum())
    p = p[:K, :K]
    n = np.linalg.norm(p)
    return float(np.linalg.norm(p - p.T) / n) if n > 0 else 0.0


def all_reff(pred, target, valid=None) -> dict[str, float]:
    return {"reff_rel_error": rel_error(pred, target, valid), "reff_mae_log10": mae_log(pred, target, valid),
            "reff_spearman": spearman_pairs(pred, target, valid), "reff_nn_agreement": nearest_neighbour_agreement(pred, target, valid),
            "reff_symmetry": symmetry(pred, valid)}
