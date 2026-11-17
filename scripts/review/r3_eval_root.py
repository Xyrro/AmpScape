#!/usr/bin/env python
"""Review round 3: a minimal harness root for the L T4 reference evaluation — index/L.parquet plus the production T4
shards that hold the test_id landscapes of the (enlarged) L block-1 reference, linked from the local Hub cache.
  python scripts/review/r3_eval_root.py --out work/r3_rootL
"""
import argparse
import os
import pathlib
import shutil

import pandas as pd
from huggingface_hub import hf_hub_download

ROOT = pathlib.Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(ROOT / "work" / "r3_rootL"))
ap.add_argument("--reference", default=str(ROOT / "aux" / "t4_bs1_reference" / "L_bs1"))
a = ap.parse_args()
out = pathlib.Path(a.out)
(out / "index").mkdir(parents=True, exist_ok=True)
idx = pd.read_parquet(ROOT / "data" / "hf" / "AmpScape" / "index" / "L.parquet")
shutil.copy2(ROOT / "data" / "hf" / "AmpScape" / "index" / "L.parquet", out / "index" / "L.parquet")
ref = pd.read_parquet(pathlib.Path(a.reference) / "manifest.parquet")
sids = set(ref.sample_id[ref.split == "test_id"])
paths = sorted(set(idx[idx.sample_id.isin(sids) & (idx.config == "omniscape")].hf_path))
for rel in paths:
    p = hf_hub_download("Xirro/AmpScape", rel, repo_type="dataset", cache_dir=str(ROOT / "data" / "hfcache_r3"))
    dst = out / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    os.symlink(os.path.realpath(p), dst)
print(f"{len(sids)} test_id reference landscapes in {len(paths)} T4 shards -> {out}")
