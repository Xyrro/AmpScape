"""Hand-computed cases for every metric family."""

from __future__ import annotations

import numpy as np
import pytest

from ampscape.metrics import domain, efficiency, physics, pixel, reff
from ampscape.metrics.transforms import EPS


def test_pixel_metrics_hand_cases():
    t = np.array([[1.0, 2.0], [3.0, 4.0]])
    p = np.array([[1.0, 2.0], [3.0, 8.0]])
    assert pixel.mse(p, t) == pytest.approx(16 / 4)
    assert pixel.rel_l2(p, t) == pytest.approx(4 / np.sqrt(30))
    # log10-eps MAE: only the (1,1) pixel differs; shift eps*max(t) = 4e-6
    expect = abs(np.log10(8 + 4 * EPS) - np.log10(4 + 4 * EPS)) / 4
    assert pixel.mae_log(p, t) == pytest.approx(expect, rel=1e-9)
    # masking removes the differing pixel
    m = np.array([[1, 1], [1, 0]], bool)
    assert pixel.mse(p, t, m) == 0 and pixel.mae_log(p, t, m) == 0 and pixel.rel_l2(p, t, m) == 0
    assert pixel.psnr(t, t) == float("inf") and pixel.ssim(np.random.rand(16, 16), np.random.rand(16, 16)) < 1.0
    assert pixel.ssim(np.tile(t, (8, 8)), np.tile(t, (8, 8))) == pytest.approx(1.0)


def test_domain_metrics_hand_cases():
    t = np.zeros((10, 10))
    t[2, 2], t[7, 7], t[5, 5] = 10, 9, 8            # three top pixels (3 % of 100)
    p = t.copy()
    m = np.ones((10, 10), bool)
    assert domain.top_q_iou(p, t, m, 3.0) == 1.0 and domain.corridor_dice(p, t, m, 3.0) == 1.0
    p2 = np.zeros((10, 10))
    p2[2, 2], p2[7, 7], p2[0, 0] = 10, 9, 8          # one of three moved
    assert domain.top_q_iou(p2, t, m, 3.0) == pytest.approx(2 / 4)     # |∩|=2, |∪|=4
    assert domain.corridor_dice(p2, t, m, 3.0) == pytest.approx(2 * 2 / 6)
    # pinch points: the three maxima; prediction with a maximum near (2,2) and (7,7) only -> recall 2/3
    assert domain.pinch_points(t, m, 5.0, min_distance=1).sum() == 3   # with min_distance=3 the two strong peaks suppress (5,5)
    p3 = np.zeros((10, 10))
    p3[2, 3], p3[7, 6], p3[0, 9] = 5, 5, 5
    assert domain.pinch_point_recall(p3, t, m, top_percent=5.0, min_distance=1, radius=1) == pytest.approx(2 / 3)
    # Spearman: monotone transform -> 1, reversed -> -1
    a = np.arange(16, dtype=float).reshape(4, 4)
    assert domain.spearman(a**2, a) == pytest.approx(1.0) and domain.spearman(-a, a) == pytest.approx(-1.0)
    # masking: excluded pixels do not count towards q
    m2 = m.copy()
    m2[2, 2] = False
    assert domain.top_q_mask(t, m2, 2.0).sum() == 2 and not domain.top_q_mask(t, m2, 2.0)[2, 2]


def test_reff_metrics_hand_cases():
    t = np.array([[0, 1, 2], [1, 0, 4], [2, 4, 0]], float)
    p = np.array([[0, 2, 2], [2, 0, 4], [2, 4, 0]], float)  # one pair doubled
    assert reff.rel_error(p, t) == pytest.approx(1 / 3)
    assert reff.mae_log(p, t) == pytest.approx(np.log10(2) / 3)
    assert reff.spearman_pairs(t * 3, t) == pytest.approx(1.0)
    # nearest neighbour: node0->1 (t) but node0->{1,2} tie in p (argmin picks 1) -> agreement 1.0; break it:
    p2 = np.array([[0, 5, 2], [5, 0, 4], [2, 4, 0]], float)
    assert reff.nearest_neighbour_agreement(p2, t) == pytest.approx(1 / 3)  # node0->2, node1->2 (was 0), node2->0 (same)
    assert reff.symmetry(t) == 0 and reff.symmetry(np.array([[0, 1], [3, 0]], float)) > 0
    # padded 8x8 with a validity mask
    P = np.full((8, 8), np.nan)
    P[:3, :3] = p
    T = np.full((8, 8), np.nan)
    T[:3, :3] = t
    valid = ~np.isnan(T)
    assert reff.rel_error(P, T, valid) == pytest.approx(1 / 3)


def test_physics_metrics_hand_cases():
    f = np.zeros((4, 4), np.int32)
    f[0, 0], f[3, 3], f[0, 3] = 1, 2, 3
    c = np.zeros((4, 4))
    c[0, 0], c[3, 3], c[0, 3] = 2.0, 2.0, 1.0       # cumulative over 3 pairs: labels 1,2 in 2 pairs each -> expected 2; label 3 in 2 pairs -> expected 2
    pairs = [(1, 2), (1, 3), (2, 3)]
    assert physics.focal_current_error(c, f, pairs) == pytest.approx((0 + 0 + 0.5) / 3)
    assert physics.focal_current_error(np.where(f > 0, 1.0, 0.0), f, None) == 0.0
    nn = physics.nonnegativity(np.array([[1.0, -0.5], [2.0, 0.0]]))
    assert nn["neg_fraction"] == 0.25 and nn["neg_min_over_max"] == -0.25
    assert physics.throughput_error(np.ones((2, 2)) * 2, np.ones((2, 2))) == pytest.approx(1.0)
    # Kirchhoff residual on an exact solve is ~0 (re-uses the QC implementation)
    import scipy.sparse.linalg as spla

    from ampscape.landscapes.synthetic import sample_landscape
    from ampscape.sources import build_conductance_graph, laplacian

    ls = sample_landscape(3, (16, 16))
    R, nd = ls.resistance, ls.nodata_mask
    G, idx = build_conductance_graph(R, nd)
    L = laplacian(G).tocsc()
    valid = idx >= 0
    rc = np.argwhere(valid)
    s, g = tuple(rc[0]), tuple(rc[-1])
    keep = np.ones(L.shape[0], bool)
    keep[idx[g]] = False
    b = np.zeros(L.shape[0])
    b[idx[s]] = 1.0
    v = np.zeros(L.shape[0])
    v[keep] = spla.spsolve(L[keep][:, keep].tocsc(), b[keep])
    vmap = np.zeros(R.shape)
    vmap[valid] = v[idx[valid]]
    inj = np.zeros(R.shape)
    inj[s] = 1.0
    gnd = np.zeros(R.shape, bool)
    gnd[g] = True
    assert physics.kirchhoff_residual(R, nd, vmap, inj, grounded=gnd) < 1e-9


def test_efficiency():
    assert efficiency.speedup(10.0, 0.1) == 100.0 and np.isnan(efficiency.speedup(10.0, 0.0))
    s = efficiency.summarize_speedup([10, 20, 40], [1, 1, 1])
    assert s["speedup_median"] == 20 and s["speedup_geomean"] == pytest.approx(20.0)
