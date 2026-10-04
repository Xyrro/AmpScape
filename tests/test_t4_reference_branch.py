"""The exact block-1 reference must drive the primary T4 metrics (regression test for the unreachable branch found
on 2026-10-05: the comparison lived inside the pairwise-kind block, so `--t4-reference` was a no-op)."""

from __future__ import annotations

import h5py
import numpy as np

from ampscape.eval.harness import evaluate_sample


def _case():
    rng = np.random.default_rng(0)
    H = W = 16
    R = rng.uniform(1, 100, (H, W)).astype(np.float32)
    nd = np.zeros((H, W), np.float32)
    prod = rng.uniform(0, 1, (H, W)).astype(np.float32)  # block-centred production target
    ref = prod * 2.0  # exact block-1 map (any distinct map)
    src = rng.uniform(0, 1, (H, W)).astype(np.float32)
    f = h5py.File("mem.h5", "w", driver="core", backing_store=False)
    gs = f.create_group("sample")
    gs.create_dataset("inputs/resistance", data=R)
    gs.create_dataset("inputs/nodata_mask", data=nd)
    gc = gs.create_group("configs/omniscape")
    gc.create_dataset("inputs/source_strength", data=src)
    gc.create_dataset("outputs/cum_current", data=prod)
    gp = f.create_group("pred")
    gp.create_dataset("cum_current", data=ref)  # the prediction equals the exact map
    gp.attrs["inference_time_s"] = 0.01
    return f, gs, gc, gp, R, nd, ref


def test_reference_drives_primary_metrics():
    f, gs, gc, gp, R, nd, ref = _case()
    out = evaluate_sample("omniscape", gs, gc, gp, R, nd, t4_reference={"s": ref}, sid="s")
    assert out["t4_target"] == "block1_reference"
    assert out["rel_l2"] < 1e-6  # prediction == reference
    assert out["bc_rel_l2"] > 0.1  # production target differs
    f.close()


def test_without_reference_uses_production():
    f, gs, gc, gp, R, nd, ref = _case()
    out = evaluate_sample("omniscape", gs, gc, gp, R, nd, t4_reference=None, sid="s")
    assert "t4_target" not in out and "bc_rel_l2" not in out
    assert out["rel_l2"] > 0.1
    f.close()
