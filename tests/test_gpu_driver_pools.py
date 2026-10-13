"""GPU driver: per-QoS pool choice (2026-10-13) and scratch-free GNN legs."""

from __future__ import annotations

import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/slurm/gpu"))
g = importlib.import_module("gpu_driver")


def _rows(n_coe=0, n_coc=0, pd_h200_coe=0):
    rows = [f"phase10-a{i}|coe-ice|gres/gpu:h100:1|R" for i in range(n_coe - pd_h200_coe)]
    rows += [f"phase10-p{i}|coe-ice|gres/gpu:h200:1|PD|Priority" for i in range(pd_h200_coe)]
    rows += [f"phase10-b{i}|coc-ice|gres/gpu:h200:1|R" for i in range(n_coc)]
    return rows


def test_choose_pool_prefers_coe_h200_then_spills_and_respects_qos_budgets():
    assert g.choose_pool([]) == ("coe-gpu", "coe-ice", "gpu:h200:1")
    # 3 pending on coe-ice H200 → next pool (coc-ice H200 on ice-gpu)
    assert g.choose_pool(_rows(n_coe=3, pd_h200_coe=3)) == ("ice-gpu", "coc-ice", "gpu:h200:1")
    # coe-ice at its 16-leg budget → coc-ice pools only
    assert g.choose_pool(_rows(n_coe=16))[1] == "coc-ice"
    # both budgets full → None
    assert g.choose_pool(_rows(n_coe=16, n_coc=16)) is None
    # legs pending only because they were just submitted (reason None) are not backlog
    assert g.choose_pool(["phase10-n|coe-ice|gres/gpu:h200:1|PD|None"] * 5) == ("coe-gpu", "coe-ice", "gpu:h200:1")
    # non-phase10 jobs (probes, CPU jobs) do not count
    assert g.choose_pool(["probe-x|coe-ice|gres/gpu:h200:1|PD"] * 5) == ("coe-gpu", "coe-ice", "gpu:h200:1")


def test_local_fetch_only_for_gnn_training_legs():
    assert g.local_fetch({"model": "gnn"})
    assert not g.local_fetch({"model": "gnn", "kind": "transfer"})
    assert not g.local_fetch({"model": "unet"})
    assert g.gnn_phase({"model": "gnn", "tag": "RERUN_M"}) and g.gnn_phase({"model": "unet", "tag": "P4"})


def test_evictions_only_when_they_make_the_target_fit():
    # 251 GB used, XXL/T1 (21 GB) evictable, L/T3 (64 GB) wanted: 251 - 21 + 64 = 294 > 280 → do not evict
    assert not g.evictions_suffice(251, [21], 64, 280)
    # once the L/T1 legs finish, L/T1 (84 GB) joins the candidates: 251 - 105 + 64 = 210 → evict
    assert g.evictions_suffice(251, [21, 84], 64, 280)
    assert g.evictions_suffice(200, [], 64, 280)
