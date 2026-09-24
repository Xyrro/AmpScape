#!/usr/bin/env python
"""Collect Phase 10 results (runs/dev/*/results.json + the coarsen baseline evals) into one Markdown table.

python scripts/collect_baselines.py --runs runs/dev --coarsen data/predictions/dev_coarsen4 --out docs/tables/baselines_dev.md
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re

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
TIERS = ("S", "M", "L", "XL", "XXL")


def parse_group(tag: str) -> tuple[str, str] | None:
    """('tier', 'split') for an evaluation group key '<root>_<tier>_<split>' (root may contain no '_'; the full runs
    use root 'hfcache'); published groups map to 'published <tier>'."""
    for t, name in GROUPS:
        if tag == t:
            return (
                "S" if name.startswith("published S") else "XXL" if "XXL" in name else "S",
                name,
            )
    m = re.match(r"^[^_]+_(S|M|L|XL|XXL)_(test_id|test_ood|ood_region|train|val)$", tag)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^published_(S|M|L|XL|XXL)_test_ood_published$", tag)
    if m:
        return m.group(1), f"published {m.group(1)}"
    return None


def fmt(v):
    return "–" if v is None else f"{v:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/dev")
    ap.add_argument("--coarsen", default="data/predictions/dev_coarsen4")
    ap.add_argument("--out", default="docs/tables/baselines_dev.md")
    ap.add_argument(
        "--title",
        default="Learned baselines on the dev subset (tier S, single seed) vs the coarsen-×4 baseline",
    )
    a = ap.parse_args()
    rows = []
    for d in sorted(pathlib.Path(a.runs).glob("*_T*")):
        p = d / "results.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        cfg = r["config"]
        for tag, e in r["eval"].items():
            parsed = parse_group(tag)
            if not e or parsed is None:
                continue
            tier, name = parsed
            t = cfg["task"]
            m = e.get(t, {})
            sp = (m.get("speedup") or {}).get("speedup_median")
            rows.append(
                {
                    "model": d.name,
                    "task": t,
                    "tier": tier,
                    "split": name,
                    "n": e.get("n_rows"),
                    **{k: m.get(k) for k in KEYS},
                    "speedup": sp,
                    "params_M": cfg["n_params"] / 1e6,
                    "epochs": len(r["history"]),
                    "gpu_h": (r["history"][-1]["cum_gpu_h"] if r["history"] else None),
                }
            )
    # scale transfer (Phase 10-full §5): L-trained runs evaluated at XL / XXL — one row per (run, tier, split)
    for d in sorted(pathlib.Path(a.runs).glob("*_T*")):
        p = d / "results_transfer.json"
        if not p.exists() or not (d / "results.json").exists():
            continue
        rt = json.loads(p.read_text())
        r = json.loads((d / "results.json").read_text())
        cfg = r["config"]
        for tag, e in rt.get("eval", {}).items():
            parsed = parse_group(tag)
            if not e or parsed is None:
                continue
            tier, name = parsed
            t = cfg["task"]
            m = e.get(t, {})
            sp = (m.get("speedup") or {}).get("speedup_median")
            rows.append(
                {
                    "model": f"{d.name} → {tier}",
                    "task": t,
                    "tier": tier,
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
    for split in ("test_id", "test_ood", "ood_region") if cz.exists() else []:
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
                    "tier": "S",
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
        f"# {a.title}",
        "",
        "| task | tier | split | model | n | mae_log10eps | rel_l2 | top5_iou | pinch_recall | spearman | corridor_dice | ssim | speed-up (median) | params (M) | epochs | train GPU-h |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    order = {"test_id": 0, "test_ood": 1, "ood_region": 2, "train": 5, "val": 6}
    torder = {t: i for i, t in enumerate(TIERS)}
    for r in sorted(
        rows,
        key=lambda r: (
            r["task"],
            torder.get(r["tier"], 9),
            order.get(r["split"], 3 if r["split"].startswith("published") else 8),
            r["model"],
        ),
    ):
        lines.append(
            f"| {r['task']} | {r['tier']} | {r['split']} | {r['model']} | {r['n']} | "
            + " | ".join(fmt(r[k]) for k in KEYS)
            + f" | {fmt(r['speedup'])} | {fmt(r['params_M'])} | {r['epochs'] or '–'} | {fmt(r['gpu_h'])} |"
        )
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
