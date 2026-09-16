"""Download-subset membership (dataset plan §5.2): mini ⊂ core ⊂ full, fixed by seed and nested."""

from __future__ import annotations

import hashlib

import pandas as pd

SUBSET_ORDER = ["mini", "core", "full"]


def _u(sample_id: str, seed: int) -> float:
    return int(hashlib.sha256(f"{seed}|subset|{sample_id}".encode()).hexdigest()[:8], 16) / 2**32


def assign_subsets(index: pd.DataFrame, targets: dict[str, int | None], seed: int = 20260906) -> dict[str, set[str]]:
    """Return {subset: sample ids}. ``targets`` = landscapes per subset (None = everything).

    Selection is stratified by (tier, family, split) with a deterministic per-sample hash, and nested:
    the mini ids are a subset of core, core of full. Every split present in the index keeps at least
    one sample in every subset, so each subset is usable for train/val/test on its own.
    """
    s = index.drop_duplicates("sample_id")[["sample_id", "tier", "family", "split"]].copy()
    s["u"] = [_u(i, seed) for i in s.sample_id]
    s = s.sort_values("u")
    out: dict[str, set[str]] = {}
    prev: set[str] = set()
    for name in SUBSET_ORDER:
        target = targets.get(name)
        if target is None or target >= len(s):
            chosen = set(s.sample_id)
        else:
            frac = target / len(s)
            chosen = set(prev)
            for _, g in s.groupby(["tier", "family", "split"]):
                need = max(1, int(round(len(g) * frac))) - len(chosen & set(g.sample_id))
                if need > 0:
                    chosen |= set(g[~g.sample_id.isin(chosen)].sample_id.head(need))
        out[name] = chosen | prev
        prev = out[name]
    return out
