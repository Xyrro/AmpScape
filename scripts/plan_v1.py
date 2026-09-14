#!/usr/bin/env python
"""Plan a v1.0-prefix build for one tier (dev / core subsets; ampscape.solve.plan_v1).

  python scripts/plan_v1.py --tier S --n 3000 --out data/dev/S --tiles data/tiles/v1 --shard-size 100 --dataset-version 1.0.0-dev
Then: generate.py prepare / submit / finalize --build data/dev/S (same driver as the mini).
"""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tiles", default="data/tiles/v1")
    ap.add_argument("--shard-size", type=int, default=100)
    ap.add_argument("--dataset-version", default="1.0.0-dev")
    ap.add_argument("--source-config", default="configs/tasks/sources_default.yaml")
    ap.add_argument("--solver-preset", default="configs/solver/circuitscape_reference.yaml")
    a = ap.parse_args()
    from ampscape.solve.plan_v1 import V1_DATASET_ID, plan_v1, split_counts

    build = pathlib.Path(a.out)
    build.mkdir(parents=True, exist_ok=True)
    df = plan_v1(a.tier, a.n, str(ROOT / a.tiles), a.shard_size)
    df.to_parquet(build / "manifest.parquet", index=False)
    n_syn, n_tiles = split_counts(a.n)
    cfg = {"dataset_id": V1_DATASET_ID, "design": "v1.0-prefix", "tier": a.tier, "n": a.n, "n_synthetic": n_syn, "n_real": n_tiles * 5,
           "n_tiles": n_tiles, "shard_size": a.shard_size, "pilot": a.tiles, "published": None, "source_config": a.source_config,
           "solver_preset": a.solver_preset, "dataset_version": a.dataset_version, "seed0": None}
    (build / "build.json").write_text(json.dumps(cfg, indent=1))
    print(f"planned {len(df)} samples ({n_syn} synthetic + {n_tiles} tiles × 5) in {df.shard.nunique()} shards -> {build}")
    print("splits:", df.split.value_counts().to_dict(), "| cg_baseline on", int(df.cg_baseline.sum()))
    ex = df[df.family == "synthetic"].extra.apply(lambda x: json.loads(x).get("hard_case"))
    print("generators:", df[df.family == "synthetic"].generator.value_counts().to_dict())
    print("hard cases:", ex.value_counts(dropna=False).to_dict())
    print("tables:", df[df.family == "real"].table_id.value_counts().to_dict())
    print("regions configs:", int(df.configs.str.contains("regions").sum()))


if __name__ == "__main__":
    main()
