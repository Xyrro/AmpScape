#!/usr/bin/env python
"""WP2: T4 error-vs-cost table and Pareto figure per split — block-size rows (aux builds scored against the block-1
reference), the production target (block rule), and learned models (runs evaluated with --t4-reference), side by side.

  python scripts/t4_pareto.py --reference aux/t4_bs1_reference/M_bs1 --blocks aux/t4_blocksize_baselines/M_b3_ca0 ... \
      [--runs runs/dev/unet_T4 ...] --tier M --out docs/tables/t4_pareto_M.md --fig docs/figures/t4_pareto_M.png
Costs: block rows = median Omniscape solve time per landscape (single core); learned rows = median batch-amortised GPU
inference time per landscape (from the run's predictions eval). Errors against the exact block-1 map.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import pandas as pd

KEYS = ["rel_l2", "ns_rel_l2", "mae_log10eps", "top5_iou", "pinch_recall", "spearman"]


def block_rows(ref: pathlib.Path, blocks: list[pathlib.Path]) -> pd.DataFrame:
    rows = []
    idx = pd.read_parquet(ref / "index.parquet")  # production (block rule) vs block 1
    for split, g in idx.groupby("split"):
        rows.append(
            {
                "split": split,
                "method": f"production block {int(g.prod_block.iloc[0])} (correct_artifacts=1)",
                "n": len(g),
                "cost_s": g.prod_solve_s.median(),
                **{k: g[k].mean() for k in KEYS},
            }
        )
        rows.append(
            {
                "split": split,
                "method": "block 1 (exact, reference)",
                "n": len(g),
                "cost_s": g.aux_solve_s.median(),
                **{
                    k: (1.0 if k in ("top5_iou", "pinch_recall", "spearman") else 0.0) for k in KEYS
                },
            }
        )
    for b in blocks:
        p = b / "vs_bs1.parquet"
        if not p.exists():
            continue
        d = pd.read_parquet(p)
        for split, g in d.groupby("split"):
            rows.append(
                {
                    "split": split,
                    "method": f"block {int(g.block.iloc[0])} (correct_artifacts={int(g.correct_artifacts.iloc[0])})",
                    "n": len(g),
                    "cost_s": g.solve_s.median(),
                    **{k: g[k].mean() for k in KEYS},
                }
            )
    return pd.DataFrame(rows)


def model_rows(runs: list[pathlib.Path], tier: str) -> pd.DataFrame:
    rows = []
    for r in runs:
        res = json.loads((r / "results.json").read_text())
        for tag, e in res["eval"].items():
            if not tag.startswith(f"S_{tier}_") and not tag.startswith(f"{tier}_{tier}_"):
                continue
            split = tag.split("_", 2)[2]
            m = e.get("T4", {})
            if not m or m.get("rel_l2") is None:
                continue
            cost = None
            per = r / "predictions" / tag / f"eval_{split}" / "results.json"
            if per.exists():
                ps = json.loads(per.read_text())["per_sample"]
                ts = [x.get("inference_time_s") for x in ps if x.get("inference_time_s")]
                cost = float(pd.Series(ts).median()) if ts else None
            rows.append(
                {
                    "split": split,
                    "method": f"{r.name} (learned)",
                    "n": e.get("n_rows"),
                    "cost_s": cost,
                    **{k: m.get(k) for k in KEYS},
                }
            )
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--blocks", nargs="*", default=[])
    ap.add_argument("--runs", nargs="*", default=[])
    ap.add_argument("--tier", default="M")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fig", default=None)
    a = ap.parse_args()
    df = pd.concat(
        [
            block_rows(pathlib.Path(a.reference), [pathlib.Path(b) for b in a.blocks]),
            model_rows([pathlib.Path(r) for r in a.runs], a.tier),
        ],
        ignore_index=True,
    )
    lines = [
        f"# T4 error vs cost at tier {a.tier} (errors against the exact block-1 map on the reference subset)",
        "",
        "| split | method | n | cost s / landscape | rel_l2 | ns_rel_l2 | mae_log10eps | top5_iou | pinch_recall | spearman |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for split, g in df.groupby("split"):
        for r in g.sort_values("cost_s", ascending=False).itertuples():

            def f(v):
                return "–" if v is None or pd.isna(v) else f"{v:.4f}"

            lines.append(
                f"| {split} | {r.method} | {r.n} | {'–' if pd.isna(r.cost_s) else f'{r.cost_s:.3g}'} | "
                + " | ".join(f(getattr(r, k)) for k in KEYS)
                + " |"
            )
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if a.fig:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker

        splits = sorted(df.split.unique())
        fig, axes = plt.subplots(1, len(splits), figsize=(4.2 * len(splits), 3.6), squeeze=False)
        for ax, split in zip(axes[0], splits, strict=True):
            g = df[(df.split == split) & df.cost_s.notna()]
            for r in g.itertuples():
                ax.scatter(r.cost_s, r.rel_l2, s=40, marker="o" if "learned" in r.method else "s")
                ax.annotate(
                    r.method.replace(" (correct_artifacts=", " ca=").replace(")", ""),
                    (r.cost_s, r.rel_l2),
                    fontsize=6,
                    xytext=(3, 3),
                    textcoords="offset points",
                )
            ax.set_xscale("log")
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_xlabel("cost per landscape (s)")
            ax.set_ylabel("rel-L2 vs block-1 map")
            ax.set_title(split, fontsize=9)
        fig.tight_layout()
        fig.savefig(a.fig, dpi=120)
        print("figure ->", a.fig)


if __name__ == "__main__":
    main()
