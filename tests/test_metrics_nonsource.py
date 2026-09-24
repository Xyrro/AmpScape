"""Hand-computed cases for the non-source-pixel metrics (review addendum WP3)."""

import numpy as np

from ampscape.metrics.nonsource import all_nonsource, nonsource_mask


def test_focal_halo_exclusion():
    base = np.ones((5, 5), bool)
    focal = np.zeros((5, 5), np.int32)
    focal[0, 0] = 1  # one focal pixel in the corner; halo 1 excludes the 2x2 corner block
    m = nonsource_mask("points", base, focal=focal, halo=1)
    assert m.sum() == 25 - 4 and not m[:2, :2].any() and m[2:, :].all() and m[:, 2:].all()


def test_advanced_and_omniscape_masks():
    base = np.ones((3, 3), bool)
    S = np.zeros((3, 3))
    S[1, 1] = 0.5
    G = np.zeros((3, 3), np.int8)
    G[0, 0] = 1
    m = nonsource_mask("advanced", base, source_strength=S, ground=G, halo=0)
    assert m.sum() == 7 and not m[1, 1] and not m[0, 0]
    m4 = nonsource_mask("omniscape", base, source_strength=S)
    assert m4.sum() == 8 and not m4[1, 1]


def test_nonsource_rel_l2_by_hand():
    # target = 1 everywhere except a singular source pixel (100); prediction errs by 0.5 on two matrix pixels only.
    t = np.ones((4, 4))
    t[0, 0] = 100.0
    p = t.copy()
    p[3, 3] = 1.5
    p[2, 2] = 0.5
    focal = np.zeros((4, 4), np.int32)
    focal[0, 0] = 1
    ns = nonsource_mask("points", np.ones((4, 4), bool), focal=focal, halo=0)
    r = all_nonsource(p, t, ns, np.ones((4, 4), bool))
    # non-source pixels: 15 ones; error vector has two entries of 0.5 -> ||e|| = sqrt(0.5) ; ||t|| = sqrt(15)
    assert np.isclose(r["ns_rel_l2"], np.sqrt(0.5) / np.sqrt(15))
    assert np.isclose(r["ns_fraction"], 15 / 16)
    # including the source pixel the same errors are swamped: rel-L2 = sqrt(0.5)/sqrt(15+100^2)
    from ampscape.metrics.pixel import rel_l2

    assert rel_l2(p, t, np.ones((4, 4), bool)) < r["ns_rel_l2"] / 10
