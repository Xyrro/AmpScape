#!/usr/bin/env python
"""Non-learned baseline: coarsen x f -> reference solve -> upsample, written in the predictions format.

python scripts/baseline_coarsen.py --root data/builds/mini --splits test_id,test_ood,ood_region --factor 4 --out data/predictions/coarsen4
Then: python scripts/evaluate.py --predictions data/predictions/coarsen4 --split test_id,test_ood,ood_region
The coarse solve runs through the Julia batch solver (run this on a compute node or via srun).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

import pandas as pd

from ampscape.models.coarsen import write_coarse_inputs, write_predictions

ROOT = pathlib.Path(__file__).resolve().parents[1]
JULIA_PKG = ROOT / "julia" / "AmpScapeSolve.jl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/builds/mini")
    ap.add_argument("--splits", default="test_id,test_ood,ood_region")
    ap.add_argument("--factor", type=int, default=4)
    ap.add_argument("--out", required=True)
    ap.add_argument("--omniscape-solver", default="cholmod")
    a = ap.parse_args()
    root, out = pathlib.Path(a.root), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    idx = pd.read_parquet(root / "index.parquet")
    idx = idx[idx.split.isin(a.splits.split(",")) & idx.qc_pass]
    pred = out / "predictions.h5"
    if pred.exists():
        pred.unlink()
    tmp = os.environ.get("TMPDIR", "/tmp")
    total = 0
    for shard, g in idx.groupby("shard"):
        final = root / "shards" / shard
        sids = sorted(g.sample_id.unique())
        cin = out / f"coarse_{shard.replace('.h5', '')}.inputs.h5"
        cout = out / f"coarse_{shard.replace('.h5', '')}.outputs.h5"
        times = write_coarse_inputs(str(final), str(cin), sids, a.factor)
        if cout.exists():
            cout.unlink()
        cmd = [
            "julia",
            f"--project={JULIA_PKG}",
            str(JULIA_PKG / "scripts" / "solve_shard.jl"),
            str(cin),
            str(cout),
            "--tmp",
            tmp,
            "--solver",
            "cholmod",
            "--fallback",
            "cg+amg",
            "--omniscape-solver",
            a.omniscape_solver,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-1500:])
            sys.exit(1)
        n = write_predictions(str(final), str(cout), str(pred), a.factor, times, append=True)
        total += n
        print(f"{shard}: {len(sids)} samples coarsened and solved, {n} written")
    (out / "meta.json").write_text(
        json.dumps(
            {
                "model": f"coarsen{a.factor}_solve_upsample",
                "task": "all",
                "tier": str(idx.tier.iloc[0]),
                "split": a.splits,
                "factor": a.factor,
                "notes": "non-learned baseline: geometric-mean coarsening, "
                "reference CHOLMOD solve on the coarse grid, bilinear upsampling; Reff taken from the coarse solve",
            },
            indent=1,
        )
    )
    print(f"wrote {pred} ({total} samples), meta.json")


if __name__ == "__main__":
    main()
