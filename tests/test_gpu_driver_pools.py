"""GPU driver: per-QoS pool choice (2026-10-13) and scratch-free GNN legs."""

from __future__ import annotations

import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/slurm/gpu"))
g = importlib.import_module("gpu_driver")


def _rows(n_coc=0, n_coe=0, pd_h100_coc=0):
    rows = [f"phase10-a{i}|coc-ice|gres/gpu:l40s:1|R" for i in range(n_coc - pd_h100_coc)]
    rows += [f"phase10-p{i}|coc-ice|gres/gpu:h100:1|PD" for i in range(pd_h100_coc)]
    rows += [f"phase10-b{i}|coe-ice|gres/gpu:h100:1|R" for i in range(n_coe)]
    return rows


def test_choose_pool_prefers_h100_then_spills_and_respects_qos_budgets():
    assert g.choose_pool([]) == ("ice-gpu", "coc-ice", "gpu:h100:1")
    # 3 pending on coc-ice H100 → next pool (coe-ice H100)
    assert g.choose_pool(_rows(n_coc=3, pd_h100_coc=3)) == ("coe-gpu", "coe-ice", "gpu:h100:1")
    # coc-ice at its 16-leg budget → coe-ice pools only
    assert g.choose_pool(_rows(n_coc=16))[1] == "coe-ice"
    # both budgets full → None
    assert g.choose_pool(_rows(n_coc=16, n_coe=16)) is None
    # non-phase10 jobs (probes, CPU jobs) do not count
    assert g.choose_pool(["probe-x|coc-ice|gres/gpu:h100:1|PD"] * 5) == ("ice-gpu", "coc-ice", "gpu:h100:1")


def test_local_fetch_only_for_gnn_training_legs():
    assert g.local_fetch({"model": "gnn"})
    assert not g.local_fetch({"model": "gnn", "kind": "transfer"})
    assert not g.local_fetch({"model": "unet"})
    assert g.gnn_phase({"model": "gnn", "tag": "RERUN_M"}) and g.gnn_phase({"model": "unet", "tag": "P4"})
