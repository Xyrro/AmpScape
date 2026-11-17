"""Packed training items: the exact tensors `Items.__getitem__` produces (x, y, mask, scale, ids), written once per
(job, split) to contiguous .npy memmaps on the compute node's local NVMe and read back with no decoding.

Why (2026-10-13 probes, U-Net/FNO at M): an epoch is bound by the input pipeline — every item is 6–8 gzip-4 chunked
HDF5 arrays decoded in the loader workers (6 workers 170 s/epoch, 12 workers 94 s; the GPU type makes no difference,
L40S = H200). Packing is one pass of the same loader (≈ one epoch with 12 workers), after which epochs read memmaps.
The pack is keyed by everything that determines the tensors (task, tier, split, model-side input/target options,
normalisation stats, max_train) so that a job on the same node reuses an existing pack; a flock serialises packers.
GNN items (graph structures of variable size) are not packed."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import pathlib
import time

import numpy as np
import torch

FIELDS = ("x", "y", "mask")


def pack_key(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()[:16]


def pack_items(
    items: torch.utils.data.Dataset,
    out_dir: pathlib.Path,
    spec: dict,
    *,
    workers: int = 12,
    batch: int = 16,
    collate=None,
    log=print,
) -> pathlib.Path:
    """Write items[i] for all i into out_dir/{x,y,mask}.npy (+ meta.json with sample_id/config/scale and the spec).
    Returns out_dir. Idempotent: an existing complete pack with the same spec is reused; concurrent callers on the
    same node wait on out_dir.lock and then reuse it."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    done = out_dir / "meta.json"
    with open(out_dir / ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        if done.exists():
            try:
                meta = json.loads(done.read_text())
                if meta.get("spec") == spec and all((out_dir / f"{f}.npy").exists() for f in FIELDS):
                    log(f"pack reused: {out_dir} ({meta['n']} items)")
                    return out_dir
            except (OSError, json.JSONDecodeError):
                pass
        t0 = time.monotonic()
        n = len(items)
        dl = torch.utils.data.DataLoader(
            items, batch_size=batch, shuffle=False, num_workers=workers, collate_fn=collate
        )
        mm: dict[str, np.memmap] = {}
        ids, cfgs, scales = [], [], []
        pos = 0
        for b in dl:
            k = b["x"].shape[0]
            for f in FIELDS:
                arr = b[f].numpy()
                if f not in mm:
                    mm[f] = np.lib.format.open_memmap(
                        out_dir / f"{f}.npy.tmp", mode="w+", dtype=arr.dtype, shape=(n, *arr.shape[1:])
                    )
                mm[f][pos : pos + k] = arr
            ids.extend(b["sample_id"])
            cfgs.extend(b["config"])
            scales.extend(float(s) for s in b["scale"])
            pos += k
        assert pos == n, (pos, n)
        for f, m in mm.items():
            m.flush()
            del m
            os.replace(out_dir / f"{f}.npy.tmp", out_dir / f"{f}.npy")
        done.write_text(
            json.dumps(
                {
                    "spec": spec,
                    "n": n,
                    "sample_id": ids,
                    "config": cfgs,
                    "scale": scales,
                    "seconds": round(time.monotonic() - t0, 1),
                    "bytes": sum((out_dir / f"{f}.npy").stat().st_size for f in FIELDS),
                }
            )
        )
        log(
            f"packed {n} items to {out_dir} in {time.monotonic() - t0:.0f} s "
            f"({sum((out_dir / f'{f}.npy').stat().st_size for f in FIELDS) / 1e9:.1f} GB)"
        )
    return out_dir


class PackedItems(torch.utils.data.Dataset):
    """Reads a pack written by pack_items; yields the same dict as Items (non-graph)."""

    def __init__(self, out_dir: str | os.PathLike):
        self.dir = pathlib.Path(out_dir)
        meta = json.loads((self.dir / "meta.json").read_text())
        self.n = meta["n"]
        self.sample_id, self.config, self.scale = meta["sample_id"], meta["config"], meta["scale"]
        self._mm: dict[str, np.memmap] | None = None

    def _open(self) -> dict[str, np.memmap]:
        if self._mm is None:  # opened lazily in each worker process
            self._mm = {f: np.load(self.dir / f"{f}.npy", mmap_mode="r") for f in FIELDS}
        return self._mm

    def __getstate__(self):
        d = self.__dict__.copy()
        d["_mm"] = None
        return d

    def __len__(self):
        return self.n

    def __getitem__(self, i: int) -> dict:
        mm = self._open()
        out = {f: np.array(mm[f][i]) for f in FIELDS}
        out.update({"sample_id": self.sample_id[i], "config": self.config[i], "scale": self.scale[i]})
        return out
