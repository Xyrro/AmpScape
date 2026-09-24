"""Tests for ampscape.landscapes.synthetic: shapes, ranges, determinism, overlays."""

from __future__ import annotations

import json

import numpy as np
import pytest
from scipy import ndimage

from ampscape.landscapes import synthetic as syn

SHAPES = [(64, 64), (128, 128), (48, 96)]
GENERATORS = {
    "grf": {"length_scale": 8, "anisotropy": 2.0, "angle_deg": 30.0},
    "fractal": {"roughness": 0.5},
    "random_cluster": {"p": 0.5},
    "planar_gradient": {"direction_deg": 45.0},
    "edge_gradient": {"direction_deg": 90.0},
    "distance_gradient": {"n_sources": 3},
    "mosaic": {"n_elements": 12},
}


@pytest.mark.parametrize("name,params", GENERATORS.items())
@pytest.mark.parametrize("shape", SHAPES)
def test_generators_shape_range_dtype(name, params, shape):
    f = syn.generate_field(name, shape, params, np.random.default_rng(1))
    assert f.shape == shape and f.dtype == np.float32
    assert np.isfinite(f).all() and f.min() >= 0.0 and f.max() <= 1.0
    assert f.max() > 0.0  # not constant


@pytest.mark.parametrize("name,params", GENERATORS.items())
def test_generators_deterministic(name, params):
    a = syn.generate_field(name, (64, 64), params, np.random.default_rng(7))
    b = syn.generate_field(name, (64, 64), params, np.random.default_rng(7))
    c = syn.generate_field(name, (64, 64), params, np.random.default_rng(8))
    np.testing.assert_array_equal(a, b)
    if name not in ("planar_gradient", "edge_gradient"):  # deterministic by construction
        assert not np.array_equal(a, c)


def test_nlmpy_wrapper_restores_global_rng():
    np.random.seed(123)
    expected = np.random.get_state()[1].copy()
    np.random.seed(123)
    syn.midpoint_displacement((32, 32), 0.5, np.random.default_rng(0))
    assert np.array_equal(np.random.get_state()[1], expected)


def test_grf_correlation_length_increases_smoothness():
    rng = np.random.default_rng(0)
    rough = syn.gaussian_random_field((128, 128), 2, rng)
    smooth = syn.gaussian_random_field((128, 128), 32, rng)
    tv = lambda a: np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean()  # noqa: E731
    assert tv(rough) > 3 * tv(smooth)


def test_grf_anisotropy_direction():
    # principal axis along x (columns): variation along rows must exceed variation along columns
    f = syn.gaussian_random_field(
        (128, 128), 16, np.random.default_rng(3), anisotropy=4.0, angle_deg=0.0
    )
    var_along_x = np.abs(np.diff(f, axis=1)).mean()
    var_along_y = np.abs(np.diff(f, axis=0)).mean()
    assert var_along_y > 1.5 * var_along_x


def test_field_to_resistance_ranges():
    f = np.linspace(0, 1, 101, dtype=np.float32)
    for c in syn.CONTRAST_LEVELS:
        r = syn.field_to_resistance(f, c, "log")
        assert r.dtype == np.float32 and r.min() == 1.0 and np.isclose(r.max(), c)
        r2 = syn.field_to_resistance(f, c, "linear")
        assert r2.min() == 1.0 and np.isclose(r2.max(), c)
    with pytest.raises(ValueError):
        syn.field_to_resistance(f, 0.5)


def test_linear_barriers_geometry():
    m = syn.linear_barriers(
        (128, 128),
        1,
        3.0,
        np.random.default_rng(0),
        orientation_deg=0.0,
        orientation_jitter_deg=0.0,
    )
    assert m.any()
    rows = np.where(m.any(axis=1))[0]
    assert len(rows) <= 4  # a horizontal line of width 3 touches at most 4 rows
    # gaps reduce coverage
    m_gap = syn.linear_barriers(
        (128, 128),
        1,
        3.0,
        np.random.default_rng(0),
        orientation_deg=0.0,
        orientation_jitter_deg=0.0,
        gap_fraction=0.3,
        gap_length_px=4.0,
    )
    assert 0.55 < m_gap.sum() / m.sum() < 0.85


def test_patch_mosaic_classes():
    f = syn.gaussian_random_field((64, 64), 8, np.random.default_rng(0))
    out, cls, values = syn.patch_mosaic(f, 5, np.random.default_rng(1))
    assert cls.min() == 0 and cls.max() == 4 and len(values) == 5
    assert 0.0 in values and 1.0 in values
    assert set(np.unique(out)) <= set(np.float32(values))


def test_random_nodata_single_component():
    nd = syn.random_nodata((128, 128), 0.2, 8.0, np.random.default_rng(5))
    assert 0.1 < nd.mean() < 0.5
    _, n = ndimage.label(~nd, structure=np.ones((3, 3)))
    assert n == 1


def test_sample_landscape_contract():
    for seed in range(12):
        ls = syn.sample_landscape(seed, (64, 64))
        assert ls.resistance.shape == (64, 64) and ls.resistance.dtype == np.float32
        valid = ls.resistance[~ls.nodata_mask]
        assert valid.min() >= 1.0 and valid.max() <= ls.contrast + 1e-3
        assert np.all(ls.resistance[ls.nodata_mask] == 1.0)
        assert ls.contrast in syn.CONTRAST_LEVELS
        json.loads(ls.params_json())  # serialisable
        _, n = ndimage.label(~ls.nodata_mask, structure=np.ones((3, 3)))
        assert n == 1


def test_sample_landscape_deterministic_and_regenerable():
    a = syn.sample_landscape(42, (64, 64))
    b = syn.sample_landscape(42, (64, 64))
    np.testing.assert_array_equal(a.resistance, b.resistance)
    assert a.params == b.params
    c = syn.regenerate(a.params, 42)
    np.testing.assert_array_equal(a.resistance, c.resistance)
    assert not np.array_equal(a.resistance, syn.sample_landscape(43, (64, 64)).resistance)


def test_prior_covers_all_generators():
    seen = {syn.sample_landscape(s, (32, 32)).generator for s in range(60)}
    assert seen == set(syn.DEFAULT_PRIOR["generator_weights"])


# ---- v1.0 sampler (hard-case stratum, dataset plan §3) ----
def test_v1_sampler_strata_and_contracts():
    from collections import Counter

    hc, contrasts = Counter(), Counter()
    for s in range(100_000_000, 100_000_300):
        ls = syn.sample_landscape_v1(s, (64, 64))
        hc[ls.params["hard_case"]] += 1
        contrasts[ls.contrast] += 1
        assert (
            ls.resistance.shape == (64, 64)
            and 1.0 <= ls.resistance.min()
            and ls.resistance.max() <= ls.contrast
        )
        assert ls.resistance[ls.nodata_mask].max(initial=1.0) == 1.0
        if ls.params["hard_case"] == "rmax_saturated":
            v = ~ls.nodata_mask
            assert (ls.resistance[v] >= 0.999 * ls.contrast).mean() > 0.5
        if ls.params["hard_case"] == "large_nodata":
            assert 0.2 <= ls.nodata_mask.mean() <= 0.5
        if ls.params["hard_case"] is None:
            assert ls.contrast <= 10_000
    assert 0.1 < (300 - hc[None]) / 300 < 0.3  # ≈ 20 % hard
    assert contrasts[1_000_000] > 0 and contrasts[100_000] > 0


def test_v1_sampler_deterministic_and_regenerable():
    a = syn.sample_landscape_v1(100_000_042, (64, 64))
    b = syn.sample_landscape_v1(100_000_042, (64, 64))
    assert np.array_equal(a.resistance, b.resistance) and a.params == b.params
    assert syn.regenerate_v1(a.params, 100_000_042).params == a.params
    assert not np.array_equal(a.resistance, syn.sample_landscape(100_000_042, (64, 64)).resistance)


def test_corridor_walls_span_and_gaps():
    from scipy import ndimage

    rng = np.random.default_rng(3)
    mask, walls = syn.corridor_walls((96, 96), 1, rng)
    assert len(walls) == 1 and 1 <= len(walls[0]["gaps"]) <= 3
    # with the gaps closed the wall splits the raster into >= 2 components; with gaps it stays connected
    closed, _ = syn.corridor_walls((96, 96), 1, np.random.default_rng(3), gaps_range=(0, 0))
    _, n_closed = ndimage.label(~closed, structure=np.ones((3, 3)))
    _, n_open = ndimage.label(~mask, structure=np.ones((3, 3)))
    assert n_closed >= 2 and n_open == 1
