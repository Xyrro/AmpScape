"""ampscape.data.packed: a pack reproduces the loader's tensors exactly, is reused when the spec matches, and is
rebuilt when it does not."""

from __future__ import annotations

import numpy as np
import torch

from ampscape.data.packed import PackedItems, pack_items, pack_key


class _Items(torch.utils.data.Dataset):
    def __init__(self, n=11, c=3, h=8):
        g = np.random.default_rng(0)
        self.x = g.standard_normal((n, c, h, h)).astype(np.float32)
        self.y = g.standard_normal((n, 1, h, h)).astype(np.float32)
        self.m = (g.random((n, 1, h, h)) > 0.3).astype(np.float32)

    def __len__(self):
        return len(self.x)

    def __getitem__(self, i):
        return {"x": self.x[i], "y": self.y[i], "mask": self.m[i], "sample_id": f"s{i}", "config": "c", "scale": 1.0 + i}


def _collate(batch):
    out = {k: torch.from_numpy(np.stack([b[k] for b in batch])) for k in ("x", "y", "mask")}
    out["sample_id"] = [b["sample_id"] for b in batch]
    out["config"] = [b["config"] for b in batch]
    out["scale"] = [float(b["scale"]) for b in batch]
    return out


def test_pack_roundtrip_and_reuse(tmp_path):
    items = _Items()
    spec = {"task": "T4", "split": "train"}
    d = pack_items(items, tmp_path / "p", spec, workers=0, batch=4, collate=_collate, log=lambda *_: None)
    pk = PackedItems(d)
    assert len(pk) == len(items)
    for i in (0, 5, 10):
        a, b = items[i], pk[i]
        for f in ("x", "y", "mask"):
            assert np.array_equal(a[f], b[f]) and b[f].dtype == np.float32
        assert (b["sample_id"], b["config"], b["scale"]) == (a["sample_id"], a["config"], a["scale"])
    logs = []
    pack_items(items, d, spec, workers=0, batch=4, collate=_collate, log=logs.append)
    assert logs and logs[0].startswith("pack reused")
    logs.clear()
    pack_items(items, d, dict(spec, split="val"), workers=0, batch=4, collate=_collate, log=logs.append)
    assert logs and logs[0].startswith("packed")
    assert pack_key(spec) != pack_key(dict(spec, split="val"))
