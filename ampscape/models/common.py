"""Shared pieces for the learned baselines: input assembly, target transform, masked loss, graph construction.

Inputs (all models, brief §12): channel 0 = standardised log-resistance (train-only mean/std, 0 at NoData),
channel 1 = NoData mask, then the task's source channels — T1: focal mask (any label); T3: source strength
scaled by the number of valid pixels and the ground mask; T4: Omniscape source strength (max 1).
Targets: log10(C + ε·max C) per map (ampscape.metrics.transforms), predicted directly; loss = masked MSE.
"""
from __future__ import annotations

import numpy as np
import torch

from ampscape.metrics.transforms import EPS

TASK_CHANNELS = {"T1": 3, "T1W": 3, "T1R": 3, "T3": 4, "T4": 3}
TASK_TARGET = {"T1": "cum_current", "T1W": "cum_current", "T1R": "cum_current", "T3": "current", "T4": "cum_current"}
TASK_CONFIG = {"T1": "points", "T1W": "wall_to_wall", "T1R": "regions", "T3": "advanced", "T4": "omniscape"}


def make_inputs(d: dict, task: str, stats: dict) -> np.ndarray:
    """(C, H, W) float32 input stack for one dataset item (numpy)."""
    nd = d["nodata"][0] > 0
    s = stats["log_resistance"]
    lr = (d["log_resistance"][0] - s["mean"]) / s["std"]
    lr = np.where(nd, 0.0, lr).astype(np.float32)
    chans = [lr, nd.astype(np.float32)]
    if task in ("T1", "T1W", "T1R"):
        chans.append((d["focal"][0] > 0).astype(np.float32))
    elif task == "T3":
        n_valid = max(int((~nd).sum()), 1)
        chans.append((d["source_strength"][0] * n_valid).astype(np.float32))
        chans.append(d["ground"][0].astype(np.float32))
    elif task == "T4":
        chans.append(d["source_strength"][0].astype(np.float32))
    else:
        raise ValueError(task)
    return np.stack(chans)


def make_target(d: dict, task: str) -> tuple[np.ndarray, np.ndarray]:
    """(target log-map (1, H, W), loss mask (1, H, W)) — NoData excluded, T1W strips excluded."""
    c = d[TASK_TARGET[task]][0].astype(np.float64)
    m = np.where(np.isfinite(c), c, 0.0)
    y = np.log10(np.maximum(m, 0.0) + EPS * max(float(m.max()), 1e-30)).astype(np.float32)
    mask = (d["nodata"][0] == 0) & np.isfinite(c)
    if task == "T1W":
        mask &= d["focal"][0] == 0
    return y[None], mask[None].astype(np.float32)


def inverse_target(y: np.ndarray) -> np.ndarray:
    """Back to current units: C = 10^y − ε·max(10^y), clipped at 0 (the floor is negligible; kept for symmetry)."""
    c = np.power(10.0, y.astype(np.float64))
    return np.maximum(c - EPS * c.max(), 0.0).astype(np.float32)


def masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    diff = (pred - target) ** 2 * mask
    return diff.sum() / mask.sum().clamp_min(1.0)


def grid_graph(resistance: np.ndarray, nodata: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """8-neighbour grid graph with Circuitscape's average-conductance edge weights.

    Returns (node_index (H, W) int64 with -1 at NoData, edge_index (2, E) int64 both directions, edge_weight (E,) float32
    = (1/R_i + 1/R_j)/2, diagonal edges divided by sqrt 2), normalised per node to sum 1 (row-stochastic).
    """
    H, W = resistance.shape
    valid = ~nodata
    idx = -np.ones((H, W), dtype=np.int64)
    idx[valid] = np.arange(int(valid.sum()))
    g = 1.0 / np.maximum(resistance.astype(np.float64), 1e-12)
    src, dst, wt = [], [], []
    for dy, dx, diag in ((0, 1, False), (1, 0, False), (1, 1, True), (1, -1, True)):
        a = idx[max(0, -dy):H - max(0, dy), max(0, -dx):W - max(0, dx)]
        b = idx[max(0, dy):H - max(0, -dy), max(0, dx):W - max(0, -dx)]
        ga = g[max(0, -dy):H - max(0, dy), max(0, -dx):W - max(0, dx)]
        gb = g[max(0, dy):H - max(0, -dy), max(0, dx):W - max(0, -dx)]
        ok = (a >= 0) & (b >= 0)
        w = 0.5 * (ga[ok] + gb[ok]) / (np.sqrt(2.0) if diag else 1.0)
        src += [a[ok], b[ok]]
        dst += [b[ok], a[ok]]
        wt += [w, w]
    src = np.concatenate(src) if src else np.zeros(0, np.int64)
    dst = np.concatenate(dst) if dst else np.zeros(0, np.int64)
    wt = np.concatenate(wt) if wt else np.zeros(0)
    deg = np.zeros(max(int(valid.sum()), 1))
    np.add.at(deg, dst, wt)
    wt = wt / np.maximum(deg[dst], 1e-12)
    return idx, np.stack([src, dst]), wt.astype(np.float32)
