#!/usr/bin/env python
"""Score a coarsen-x4 predictions.h5 against the targets in the fetched Hub shards with the harness's pixel metrics.

  python scripts/review/score_coarsen.py --pred <out>/predictions.h5 --manifest <root>/manifest.json --out <json>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import h5py
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ampscape.metrics.pixel import mae_log, rel_l2  # noqa: E402

TARGET = {"points": "cum_current", "advanced": "current"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    man = json.loads(pathlib.Path(a.manifest).read_text())
    recs = []
    with h5py.File(a.pred, "r") as fp:
        for m in man:
            with h5py.File(m["shard"], "r") as fs:
                for sid in m["sids"]:
                    if sid not in fp or m["config"] not in fp[sid]:
                        continue
                    gp = fp[sid][m["config"]]
                    pred = gp[TARGET[m["config"]]][...]
                    tgt = fs[sid]["configs"][m["config"]]["outputs"][TARGET[m["config"]]][...]
                    nd = fs[sid]["inputs"]["nodata_mask"][...].astype(bool)
                    mask = ~nd
                    if m["config"] == "points":  # harness: focal pixels are scored too; strips only for T1W
                        pass
                    t = gp.attrs.get("inference_time_s", np.nan)
                    recs.append({"tier": m["tier"], "task": m["task"].replace("T1V", "T1"), "sample_id": sid,
                                 "rel_l2": rel_l2(pred, tgt, mask), "mae_log": mae_log(pred, tgt, mask),
                                 "inference_time_s": float(t)})
    pathlib.Path(a.out).write_text(json.dumps(recs, indent=1))
    print(f"wrote {a.out} ({len(recs)} samples)")


if __name__ == "__main__":
    main()
