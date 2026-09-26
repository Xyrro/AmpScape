#!/usr/bin/env python
"""Re-aggregate stored scale-transfer metrics on the current split membership (v1.0.2: the XL test_id split shrank
from 3,118 to 2,335 landscapes; the per-sample metrics of the transfer legs cover the old superset, so no
prediction has to be recomputed).

  python scripts/reaggregate_transfer.py [--runs runs/full] [--root data/hfcache] [--tier XL]

Rewrites <run>/eval_transfer/<tag>/results.json (per_sample filtered, per_task re-aggregated, `reaggregated` note)
and the tag's summary in <run>/results_transfer.json, and clears the offload marker of the tag so the offloader
pushes the new files.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ampscape.data.dataset import _load_index  # noqa: E402
from ampscape.metrics import efficiency  # noqa: E402


def aggregate(df: pd.DataFrame) -> dict:
    per_task = {}
    if not len(df):
        return per_task
    num = [c for c in df.columns if df[c].dtype.kind == "f"]
    for task, g in df.groupby("task"):
        agg = {
            c: {
                "mean": float(np.nanmean(g[c])),
                "median": float(np.nanmedian(g[c])),
                "n": int(g[c].notna().sum()),
            }
            for c in num
            if g[c].notna().any()
        }
        agg["speedup"] = efficiency.summarize_speedup(
            g.solve_time_s.tolist(), g.inference_time_s.tolist()
        )
        per_task[task] = agg
    return per_task


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/full")
    ap.add_argument("--root", default="data/hfcache")
    ap.add_argument("--tier", default="XL")
    a = ap.parse_args()
    idx = _load_index(pathlib.Path(a.root), a.tier)
    members = {s: set(idx.loc[idx.split == s, "sample_id"]) for s in idx.split.unique()}
    n_runs = 0
    for run in sorted(pathlib.Path(a.runs).glob("*_L_s*")):
        p = run / "results_transfer.json"
        if not p.exists():
            continue
        summary = json.loads(p.read_text())
        changed = False
        for tag in list(summary["eval"]):
            if f"_{a.tier}_" not in tag:
                continue
            split = tag.split(f"_{a.tier}_", 1)[1]
            rp = run / "eval_transfer" / tag / "results.json"
            if not rp.exists():
                continue
            r = json.loads(rp.read_text())
            df = pd.DataFrame(r["per_sample"])
            before = len(df)
            df = df[df.sample_id.isin(members.get(split, set()))]
            if len(df) == before and r.get("reaggregated"):
                continue
            r["per_sample"] = df.to_dict("records")
            r["per_task"] = aggregate(df)
            r["n_rows"] = int(len(df))
            r["reaggregated"] = {
                "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                "reason": "v1.0.2 split lists (XL amendment C3 corrected)",
                "rows_before": before,
            }
            rp.write_text(json.dumps(r, indent=1, default=float))
            summary["eval"][tag] = {
                t: {k: v.get("mean") for k, v in agg.items() if isinstance(v, dict) and "mean" in v}
                | {"speedup": agg.get("speedup")}
                for t, agg in r["per_task"].items()
            } | {"n_rows": r["n_rows"]}
            (run / f".offloaded_transfer_{tag}").unlink(missing_ok=True)
            changed = True
            print(f"{run.name} {tag}: {before} -> {len(df)} rows")
        if changed:
            summary["updated_at"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(summary, indent=1, default=float))
            tmp.replace(p)
            n_runs += 1
    print(f"re-aggregated {n_runs} runs")


if __name__ == "__main__":
    main()
