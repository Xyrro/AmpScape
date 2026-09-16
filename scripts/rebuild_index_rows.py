#!/usr/bin/env python
"""Rebuild a shard's index rows from its task-group files on the Hub (for shards uploaded before their index row
parquet could be written).  python scripts/rebuild_index_rows.py --build data/v1/S --tier S --shard 104"""

from __future__ import annotations

import argparse
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", required=True)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--repo", default="Xirro/AmpScape")
    a = ap.parse_args()
    from huggingface_hub import hf_hub_download

    from ampscape.io.hf_layout import TASK_GROUPS
    from ampscape.solve.finalize import index_rows_from_final

    name = f"shard-{a.shard:05d}.h5"
    frames = []
    for grp in TASK_GROUPS:
        try:
            p = hf_hub_download(a.repo, f"data/{a.tier}/{grp}/{name}", repo_type="dataset")
        except Exception:  # noqa: BLE001 - group absent for this shard
            continue
        frames.append(index_rows_from_final(p, name))
    idx = pd.concat(frames, ignore_index=True).drop_duplicates(["sample_id", "config"])
    out = pathlib.Path(a.build) / "index" / f"shard-{a.shard:05d}.parquet"
    idx.to_parquet(out, index=False)
    print(f"{name}: {idx.sample_id.nunique()} samples, {len(idx)} rows -> {out}")


if __name__ == "__main__":
    main()
