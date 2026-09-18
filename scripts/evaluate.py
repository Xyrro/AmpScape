#!/usr/bin/env python
"""python scripts/evaluate.py --predictions <dir> --split test_id [--root data/builds/mini --tier S --subset mini --out <dir> --acceleration]

Writes <out>/results.json and <out>/results.md (default out = <predictions>/eval_<split>). Format: ampscape/eval/harness.py.
"""

from __future__ import annotations

import argparse
import pathlib

from ampscape.eval import evaluate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--split", required=True, help="split name or comma-separated list")
    ap.add_argument("--root", default="data/builds/mini")
    ap.add_argument("--tier", default="S")
    ap.add_argument("--subset", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--acceleration",
        action="store_true",
        help="run the Julia warm-start evaluation on predicted voltages",
    )
    a = ap.parse_args()
    splits = a.split.split(",")
    out = a.out or str(pathlib.Path(a.predictions) / f"eval_{'+'.join(splits)}")
    r = evaluate(
        a.predictions,
        splits,
        a.root,
        a.tier,
        a.subset,
        out,
        acceleration=a.acceleration,
        t4_reference=a.t4_reference,
    )
    print(f"{r['n_rows']} rows -> {out}/results.json, results.md")
    for task, agg in r["per_task"].items():
        keys = [
            k
            for k in ("mae_log10eps", "rel_l2", "top5_iou", "reff_rel_error", "spearman")
            if k in agg
        ]
        print(" ", task, {k: round(agg[k]["mean"], 4) for k in keys})


if __name__ == "__main__":
    main()
