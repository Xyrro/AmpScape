#!/usr/bin/env python
"""Collect Phase 10 results (runs/dev/*/results.json + the coarsen baseline evals) into one Markdown table.

python scripts/collect_baselines.py --runs runs/dev --coarsen data/predictions/dev_coarsen4 --out docs/tables/baselines_dev.md
"""

from __future__ import annotations

import argparse
import json
import pathlib

KEYS = [
    "mae_log10eps",
    "rel_l2",
    "top5_iou",
    "pinch_recall",
    "spearman",
    "corridor_dice_q10",
    "ssim",
]
GROUPS = [
    ("S_S_test_id", "test_id"),
    ("S_S_test_ood", "test_ood"),
    ("S_S_ood_region", "ood_region"),
    ("published_S_test_ood_published", "published S"),
    ("published_XXL_test_ood_published", "published XXL"),
]


def fmt(v):
    return "–" if v is None else f"{v:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/dev")
    ap.add_argument("--coarsen", default="data/predictions/dev_coarsen4")
    ap.add_argument("--out", default="docs/tables/baselines_dev.md")
    a = ap.parse_args()
    rows = []
    for d in sorted(pathlib.Path(a.runs).glob("*_T*")):
        p = d / "results.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        cfg = r["config"]
        for tag, name in GROUPS:
            e = r["eval"].get(tag)
            if not e:
                continue
            t = cfg["task"]
            m = e.get(t, {})
            sp = (m.get("speedup") or {}).get("speedup_median")
            rows.append(
                {
                    "model": d.name,
                    "task": t,
                    "split": name,
                    "n": e.get("n_rows"),
                    **{k: m.get(k) for k in KEYS},
                    "speedup": sp,
                    "params_M": cfg["n_params"] / 1e6,
                    "epochs": len(r["history"]),
                    "gpu_h": (r["history"][-1]["cum_gpu_h"] if r["history"] else None),
                }
            )
    cz = pathlib.Path(a.coarsen)
    for split in ("test_id", "test_ood", "ood_region"):
        p = cz / f"eval_{split}" / "results.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        for t, agg in r["per_task"].items():
            if t not in ("T1", "T3", "T4"):
                continue
            rows.append(
                {
                    "model": "coarsen4 (non-learned)",
                    "task": t,
                    "split": split,
                    "n": agg.get("mae_log10eps", {}).get("n"),
                    **{k: agg.get(k, {}).get("mean") for k in KEYS},
                    "speedup": (agg.get("speedup") or {}).get("speedup_median"),
                    "params_M": None,
                    "epochs": None,
                    "gpu_h": None,
                }
            )
    lines = [
        "# Learned baselines on the dev subset (tier S, single seed) vs the coarsen-×4 baseline",
        "",
        "| task | split | model | n | mae_log10eps | rel_l2 | top5_iou | pinch_recall | spearman | corridor_dice | ssim | speed-up (median) | params (M) | epochs | train GPU-h |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    order = {"test_id": 0, "test_ood": 1, "ood_region": 2, "published S": 3, "published XXL": 4}
    for r in sorted(rows, key=lambda r: (r["task"], order[r["split"]], r["model"])):
        lines.append(
            f"| {r['task']} | {r['split']} | {r['model']} | {r['n']} | "
            + " | ".join(fmt(r[k]) for k in KEYS)
            + f" | {fmt(r['speedup'])} | {fmt(r['params_M'])} | {r['epochs'] or '–'} | {fmt(r['gpu_h'])} |"
        )
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
