#!/usr/bin/env python
"""Review round 2, point 4: fetch a deterministic test_id subset of T1 (points) and T3 (advanced) shards per tier from the
Hub into a local HF-layout root, and write (a) a manifest for the Julia truncated-PCG script and (b) one tiny
"finalized build" directory per tier (index.parquet + shards/) for scripts/baseline_coarsen.py.

  python scripts/review/fetch_subset.py --root aux/review_round2/cheap_baselines --n S=40,M=30,L=16
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = "Xirro/AmpScape"
GROUP = {"points": "T1", "advanced": "T3"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="aux/review_round2/cheap_baselines")
    ap.add_argument("--n", default="S=40,M=30,L=16")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from huggingface_hub import hf_hub_download

    root = ROOT / a.root
    want = {k: int(v) for k, v in (x.split("=") for x in a.n.split(","))}
    manifest = []
    for tier, n in want.items():
        idx = pd.read_parquet(ROOT / "data" / "hf" / "AmpScape" / "index" / f"{tier}.parquet")
        rows = []
        for config, group in GROUP.items():
            sub = idx[(idx.config == config) & (idx.split == "test_id") & idx.qc_pass].sort_values("hf_path")
            got = 0
            for path, g in sub.groupby("hf_path", sort=True):
                if got >= n:
                    break
                sids = sorted(g.sample_id.tolist())[: n - got]
                local = root / "hf" / path
                if not local.exists():
                    hf_hub_download(REPO, path, repo_type="dataset", local_dir=str(root / "hf"))
                manifest.append({"tier": tier, "task": "T3" if config == "advanced" else "T1V", "config": config,
                                 "shard": str(local), "sids": sids})
                for sid in sids:
                    rows.append({"sample_id": sid, "shard": f"{group}_{pathlib.Path(path).name}", "split": "test_id",
                                 "qc_pass": True, "tier": tier, "config": config})
                got += len(sids)
                print(f"{tier} {config}: {path} -> {len(sids)} samples (total {got})", flush=True)
        build = root / f"build_{tier}"
        (build / "shards").mkdir(parents=True, exist_ok=True)
        for m in [m for m in manifest if m["tier"] == tier]:
            link = build / "shards" / f"{GROUP[m['config']]}_{pathlib.Path(m['shard']).name}"
            if not link.exists():
                link.symlink_to(pathlib.Path(m["shard"]).resolve())
        pd.DataFrame(rows).to_parquet(build / "index.parquet", index=False)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {root / 'manifest.json'} ({sum(len(m['sids']) for m in manifest)} samples)")


if __name__ == "__main__":
    main()
