"""Hand-computed checks for the coarsen-solve-upsample baseline helpers."""
import numpy as np

from ampscape.models.coarsen import block_reduce, coarsen_labels, infill_focal, upsample


def test_block_reduce_geometric_mean_and_nodata():
    r = np.array([[1.0, 100.0], [1.0, 100.0]])
    assert np.isclose(block_reduce(r, 2, "gmean")[0, 0], 10.0)     # exp(mean(log)) = 10
    nd = np.array([[1, 1, 0, 0], [1, 0, 0, 0]], dtype=bool)          # left block 3/4 nodata, right block 0/4
    out = block_reduce(nd.astype(float), 2, "majority_bool")
    assert out[0, 0] == 1 and out[0, 1] == 0


def test_coarsen_labels_any():
    focal = np.zeros((4, 4), dtype=np.int32)
    focal[0, 0] = 2
    c = coarsen_labels(focal, 2)
    assert c.shape == (2, 2) and c[0, 0] == 2 and c.sum() == 2


def test_infill_focal_nearest_non_focal():
    a = np.array([[9.0, 1.0, 2.0]])
    focal = np.array([[1, 0, 0]])
    assert infill_focal(a, focal).tolist() == [[1.0, 1.0, 2.0]]
    assert infill_focal(a, np.zeros_like(focal)).tolist() == a.tolist()


def test_upsample_shape_and_constant():
    a = np.full((2, 2), 3.0)
    up = upsample(a, 2, (4, 4))
    assert up.shape == (4, 4) and np.allclose(up, 3.0)


def test_coarsen_advanced_ground_wins_and_renormalises():
    from ampscape.models.coarsen import coarsen_advanced
    S = np.zeros((4, 4)); S[0, 0] = 0.5; S[2, 2] = 0.5          # one source block overlaps the ground
    G = np.zeros((4, 4)); G[1, 1] = 1
    sc, gr = coarsen_advanced(S, G, np.zeros((2, 2), bool), 2)
    assert gr[0, 0] and not gr[1, 1]
    assert sc[0, 0] == 0 and np.isclose(sc[1, 1], 1.0) and np.isclose(sc.sum(), 1.0)
