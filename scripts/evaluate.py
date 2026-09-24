#!/usr/bin/env python
"""python scripts/evaluate.py --predictions <dir> --split test_id [--root data/builds/mini --tier S --subset mini --out <dir> --acceleration]

Writes <out>/results.json and <out>/results.md (default out = <predictions>/eval_<split>). Format: ampscape/eval/harness.py.
"""

from __future__ import annotations

import argparse
import os
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
    ap.add_argument(
        "--t4-reference",
        default=None,
        help="aux block-1 reference build (docs/t4_fidelity.md): T4 primary metrics against exact targets, production as bc_*",
    )
    ap.add_argument(
        "--t4-blocks",
        nargs="*",
        default=None,
        help="aux block-size builds scored against the reference (vs_bs1.parquet): printed beside the model (WP2)",
    )
    ap.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("SLURM_CPUS_PER_TASK", "1")),
        help="metric processes (default: the job's cores)",
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
        t4_blocks=a.t4_blocks,
        workers=a.workers,
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
