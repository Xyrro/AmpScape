"""PyTorch dataset over AmpScape shards (brief §9, Phase 7).

    ds = AmpScapeDataset(task="T1", split="train", tier="S", root="data/builds/mini")
    sample = ds[0]   # dict of tensors

``root`` is either a finalized build (``index.parquet`` + ``shards/*.h5``, all configs per shard) or an
HF-layout directory (``index/<tier>.parquet`` + ``data/<tier>/<task_group>/*.h5``) — e.g. the local
snapshot returned by :func:`load_from_hub`. Shard files are opened lazily and cached per process, so
the dataset is safe with DataLoader workers (each worker opens its own handles).

Returned tensors (all float32 unless stated; raw solver outputs, never normalised here):

| task | inputs | targets |
|---|---|---|
| T1 / T1W / T1R | ``resistance`` (1,H,W), ``log_resistance``, ``nodata`` (1,H,W), ``focal`` (1,H,W int32), ``focal_onehot`` (K_max,H,W) | ``cum_current`` (1,H,W); K ≤ 4: ``pairwise_current``, ``voltage`` (P,H,W), ``pair_index`` |
| T2 | as T1 + ``focal_table`` (K,3) [label,row,col] | ``reff`` (K,K) float64, ``reff_mask`` |
| T3 | ``resistance``, ``nodata``, ``source_strength`` (1,H,W), ``ground`` (1,H,W) | ``current``, ``voltage`` (1,H,W) |
| T4 | ``resistance``, ``nodata``, ``source_strength`` | ``cum_current``, ``flow_potential``, ``normalized`` (1,H,W) |

``normalize=True`` applies train-only statistics (``stats/norm_stats.json``, see
:func:`compute_norm_stats`) to the *inputs* (log-resistance); targets stay raw and
``log_targets`` (log10(C + ε·max C), ε = 1e-6) is the transform used by losses and metrics.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Callable

import h5py
import numpy as np
import pandas as pd

TASK_CONFIGS = {
    "T1": ["points"],
    "T2": ["points"],
    "T1W": ["wall_to_wall_NS", "wall_to_wall_EW"],
    "T1R": ["regions"],
    "T3": ["advanced"],
    "T4": ["omniscape"],
}
K_MAX = 8


def _load_index(root: pathlib.Path, tier: str | None) -> pd.DataFrame:
    if (root / "index.parquet").exists():
        idx = pd.read_parquet(root / "index.parquet")
        idx["path"] = [str(root / "shards" / s) for s in idx.shard]
    elif (root / "index").exists():
        files = (
            sorted((root / "index").glob("*.parquet"))
            if tier is None
            else [root / "index" / f"{tier}.parquet"]
        )
        idx = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        idx["path"] = [str(root / p) for p in idx.hf_path]
    else:
        raise FileNotFoundError(f"no index under {root}")
    return idx


class AmpScapeDataset:
    """Indexable dataset of (sample, config) items for one task; framework-agnostic (numpy) with a torch adapter."""

    def __init__(
        self,
        task: str,
        split: str | list[str] | None = "train",
        tier: str | None = "S",
        root: str | pathlib.Path = "data/builds/mini",
        subset: str | None = None,
        qc_pass_only: bool = True,
        trainval_only: bool | None = None,
        normalize: bool = False,
        transform: Callable | None = None,
        ood: str | None = None,
    ):
        if task not in TASK_CONFIGS:
            raise ValueError(f"unknown task {task}; one of {list(TASK_CONFIGS)}")
        self.task, self.root, self.tier = task, pathlib.Path(root), tier
        idx = _load_index(self.root, tier)
        idx = idx[idx.config.isin(TASK_CONFIGS[task])]
        if tier is not None:
            idx = idx[idx.tier == tier]
        if qc_pass_only and "qc_pass" in idx:
            idx = idx[idx.qc_pass]
        if split is not None:
            splits = [split] if isinstance(split, str) else list(split)
            idx = idx[idx.split.isin(splits)]
        if trainval_only is None:
            trainval_only = bool(split in ("train", "val"))
        if trainval_only and "qc_trainval" in idx:
            idx = idx[idx.qc_trainval]
        if ood is not None:
            idx = idx[idx[ood]]
        if subset is not None and f"subset_{subset}" in idx:
            idx = idx[idx[f"subset_{subset}"]]
        self.index = idx.reset_index(drop=True)
        self.transform = transform
        self.normalize = normalize
        self._files: dict[str, h5py.File] = {}
        self.stats = None
        if normalize:
            self.stats = load_norm_stats(self.root, tier)

    def __len__(self) -> int:
        return len(self.index)

    MAX_OPEN_FILES = 16  # 2026-09-24: an unbounded per-process cache of 500 open shards grew to 50 GB of host memory
    # (HDF5 metadata caches) in a 6-worker DataLoader over the full S training set; keep a small LRU instead

    def _file(self, path: str) -> h5py.File:
        f = self._files.get(path)
        if f is None:
            if len(self._files) >= self.MAX_OPEN_FILES:
                oldest = next(iter(self._files))
                try:
                    self._files.pop(oldest).close()
                except Exception:  # noqa: BLE001
                    pass
            f = h5py.File(path, "r")
            self._files[path] = f
        else:  # refresh LRU order
            self._files.pop(path)
            self._files[path] = f
        return f

    def __getstate__(self):
        d = self.__dict__.copy()
        d["_files"] = {}
        return d

    def __getitem__(self, i: int) -> dict:
        r = self.index.iloc[i]
        gs = self._file(r.path)[r.sample_id]
        gc = gs["configs"][r.config]
        R = gs["inputs"]["resistance"][...]
        nd = gs["inputs"]["nodata_mask"][...].astype(np.float32)
        out = {
            "sample_id": r.sample_id,
            "config": r.config,
            "resistance": R[None],
            "log_resistance": np.log(R)[None].astype(np.float32),
            "nodata": nd[None],
            "meta": json.loads(gs.attrs["meta"]),
        }
        if "covariates" in gs["inputs"]:
            out["covariates"] = gs["inputs"]["covariates"][...]
        o = gc["outputs"]
        if self.task in ("T1", "T1W", "T1R", "T2"):
            focal = gc["inputs"]["focal_mask"][...]
            out["focal"] = focal[None]
            oh = np.zeros((K_MAX, *focal.shape), np.float32)
            for k in range(1, K_MAX + 1):
                oh[k - 1] = focal == k
            out["focal_onehot"] = oh
            out["focal_table"] = np.array(
                [[t["label"], t["row"], t["col"]] for t in json.loads(gc.attrs["focal_table"])],
                dtype=np.int32,
            ).reshape(-1, 3)
            out["cum_current"] = o["cum_current"][...][None]
            reff = o["reff"][...]
            K = reff.shape[0]
            padded = np.full((K_MAX, K_MAX), np.nan)
            padded[:K, :K] = reff
            out["reff"], out["reff_mask"] = padded, ~np.isnan(padded)
            if "pairwise_current" in o:
                out["pairwise_current"] = o["pairwise_current"][...]
                out["voltage"] = o["voltage"][...]
                out["pair_index"] = o["pair_index"][...]
        elif self.task == "T3":
            out["source_strength"] = gc["inputs"]["source_strength"][...][None]
            out["ground"] = gc["inputs"]["ground"][...].astype(np.float32)[None]
            out["current"] = o["current"][...][None]
            out["voltage"] = o["voltage"][...][None]
        else:
            out["source_strength"] = gc["inputs"]["source_strength"][...][None]
            for k in ("cum_current", "flow_potential", "normalized"):
                out[k] = o[k][...][None]
        if self.normalize and self.stats:
            s = self.stats["log_resistance"]
            out["log_resistance"] = ((out["log_resistance"] - s["mean"]) / s["std"]).astype(
                np.float32
            )
        if self.transform:
            out = self.transform(out)
        return out

    def torch(self):
        """Wrap as a torch.utils.data.Dataset converting arrays to tensors (meta/ids kept as python objects)."""
        import torch

        parent = self

        class _Torch(torch.utils.data.Dataset):
            def __len__(self):
                return len(parent)

            def __getitem__(self, i):
                d = parent[i]
                return {
                    k: (
                        torch.from_numpy(np.ascontiguousarray(v))
                        if isinstance(v, np.ndarray)
                        else v
                    )
                    for k, v in d.items()
                }

        return _Torch()


def log_targets(x: np.ndarray) -> np.ndarray:
    """Helper transform for current maps: log10(C + ε·max C), ε = 1e-6 (see ampscape.metrics.transforms)."""
    from ampscape.metrics.transforms import log10_eps

    return log10_eps(x)


def log1p_targets(
    x: np.ndarray,
) -> np.ndarray:  # kept for backwards compatibility of early notebooks
    return np.log1p(np.maximum(x, 0.0))


def compute_norm_stats(
    root: str | pathlib.Path,
    tier: str | None = "S",
    task: str = "T1",
    out: str | pathlib.Path | None = None,
) -> dict:
    """Train-only input statistics (log-resistance mean/std over valid pixels, per-channel covariate stats)."""
    ds = AmpScapeDataset(task, split="train", tier=tier, root=root, normalize=False)
    s = n = 0.0
    s2 = 0.0
    cov_s = cov_s2 = cov_n = None
    for i in range(len(ds)):
        d = ds[i]
        valid = d["nodata"][0] == 0
        v = d["log_resistance"][0][valid].astype(np.float64)
        s += v.sum()
        s2 += (v**2).sum()
        n += v.size
        if "covariates" in d:
            c = d["covariates"].astype(np.float64)
            c = np.where(c == -9999.0, np.nan, c)
            if cov_s is None:
                cov_s = np.zeros(c.shape[0])
                cov_s2 = np.zeros(c.shape[0])
                cov_n = np.zeros(c.shape[0])
            cov_s += np.nansum(c, axis=(1, 2))
            cov_s2 += np.nansum(c**2, axis=(1, 2))
            cov_n += np.sum(~np.isnan(c), axis=(1, 2))
    mean = s / max(n, 1)
    std = float(np.sqrt(max(s2 / max(n, 1) - mean**2, 1e-12)))
    from ampscape.metrics.transforms import EPS

    stats = {
        "tier": tier,
        "task": task,
        "n_train_items": len(ds),
        "log_resistance": {"mean": float(mean), "std": std, "n_pixels": int(n)},
        "target_transform": {"name": "log10_eps", "eps": EPS, "formula": "log10(C + eps * max(C))"},
    }
    if cov_s is not None:
        cm = cov_s / np.maximum(cov_n, 1)
        stats["covariates"] = {
            "mean": cm.tolist(),
            "std": np.sqrt(np.maximum(cov_s2 / np.maximum(cov_n, 1) - cm**2, 1e-12)).tolist(),
        }
    out = pathlib.Path(out) if out else pathlib.Path(root) / "stats" / "norm_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(out.read_text()) if out.exists() else {}
    existing[f"{tier}"] = stats
    out.write_text(json.dumps(existing, indent=1))
    return stats


def load_norm_stats(root: str | pathlib.Path, tier: str | None) -> dict | None:
    p = pathlib.Path(root) / "stats" / "norm_stats.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return d.get(str(tier)) or next(iter(d.values()), None)


def load_from_hub(
    task: str,
    tier: str,
    split: str = "test_id",
    repo_id: str = "Xirro/AmpScape",
    cache_dir: str | None = None,
    revision: str | None = None,
    **kw,
) -> AmpScapeDataset:
    """Download only the shards of one (tier, task group) from the Hub and open them as a dataset."""
    from huggingface_hub import snapshot_download

    from ampscape.io.hf_layout import TASK_GROUPS

    group = {"T2": "T1"}.get(task, task)
    assert group in TASK_GROUPS, task
    local = snapshot_download(
        repo_id,
        repo_type="dataset",
        cache_dir=cache_dir,
        revision=revision,
        allow_patterns=[f"data/{tier}/{group}/*", f"index/{tier}.parquet", "splits/*", "stats/*"],
    )
    return AmpScapeDataset(task, split=split, tier=tier, root=local, **kw)
