#!/usr/bin/env python
"""GPU-hour accounting for the Phase 10 dev runs and extrapolation to full v1.0 training.

  python scripts/gpu_budget.py --runs runs/dev --out docs/tables/gpu_budget.md

Per run: GPU-hours per epoch = mean epoch wall time (train + val pass) / 3600, from log.csv; total = training + evaluation
wall time. Extrapolation to v1.0 (three seeds, all training tiers): the per-sample time is assumed to scale with the
number of pixels (all four models are linear in pixels except the ViT's global attention, which is quadratic in tokens
and would need windowed attention at L and above — flagged), the number of training landscapes per tier comes from the
recommended ladder × the in-distribution train share measured on dev (0.61), and the number of epochs is the epoch at
which the dev run reached its best validation loss, scaled by (dev train size / v1.0 train size)^0.5 (larger sets need
fewer passes; conservative square-root rule, stated as an assumption).
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib

LADDER = {
    "S": 100_000,
    "M": 50_000,
    "L": 20_000,
    "XL": 4_000,
}  # recommended v1.0 landscapes per tier
TRAIN_SHARE = {
    "S": 0.61,
    "M": 0.72,
    "L": 0.61,
    "XL": 0.25 * 0.61,
}  # dev-measured train share (S, M); XL: 25 % train/val slice
PIXELS = {"S": 128**2, "M": 256**2, "L": 512**2, "XL": 1024**2}
SEEDS = 3
TASK_CONFIGS_PER_LANDSCAPE = {"T1": 1, "T3": 1, "T4": 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/dev")
    ap.add_argument("--out", default="docs/tables/gpu_budget.md")
    a = ap.parse_args()
    rows = []
    for d in sorted(pathlib.Path(a.runs).glob("*_T*")):
        if not (d / "results.json").exists():
            continue
        r = json.loads((d / "results.json").read_text())
        cfg, hist = r["config"], r["history"]
        if not hist:
            continue
        ep_s = sum(h["epoch_s"] for h in hist) / len(hist)
        best = min(hist, key=lambda h: h["val_loss"])
        n_train = hist[0]["n_train"]
        train_h = hist[-1]["cum_gpu_h"]
        rows.append(
            {
                "model": cfg["model"],
                "task": cfg["task"],
                "params_M": cfg["n_params"] / 1e6,
                "n_train": n_train,
                "epochs": len(hist),
                "best_epoch": best["epoch"],
                "epoch_s": ep_s,
                "gpu_h_per_epoch": ep_s / 3600,
                "train_gpu_h": train_h,
                "s_per_sample_epoch": ep_s / n_train,
                "best_val": best["val_loss"],
            }
        )
    lines = [
        "# GPU budget (Phase 10 dev runs, L40S, bf16 autocast except FNO)",
        "",
        "| model | task | params (M) | train items | epochs run | best epoch | s / epoch | GPU-h / epoch | training GPU-h |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['model']} | {r['task']} | {r['params_M']:.2f} | {r['n_train']} | {r['epochs']} | {r['best_epoch']} | {r['epoch_s']:.1f} | "
            f"{r['gpu_h_per_epoch']:.4f} | {r['train_gpu_h']:.3f} |"
        )
    total_dev = sum(r["train_gpu_h"] for r in rows)
    lines += [
        "",
        f"Dev training total: **{total_dev:.2f} GPU-h** ({len(rows)} runs); evaluation passes add a few minutes each.",
        "",
        "## Extrapolation to v1.0 (3 seeds; per model × task; assumptions in the script docstring)",
        "",
        "| model | task | s / sample-epoch at S | epochs assumed (S / M / L / XL) | S | M | L | XL | total GPU-h (3 seeds) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    grand = 0.0
    for r in rows:
        per = {}
        eps = {}
        for tier, n in LADDER.items():
            n_train = n * TRAIN_SHARE[tier]
            e = max(5, math.ceil(r["best_epoch"] * math.sqrt(r["n_train"] / max(n_train, 1))))
            e = max(e, 5)
            eps[tier] = e
            per[tier] = (
                n_train * e * r["s_per_sample_epoch"] * PIXELS[tier] / PIXELS["S"] / 3600 * SEEDS
            )
        tot = sum(per.values())
        grand += tot
        lines.append(
            f"| {r['model']} | {r['task']} | {r['s_per_sample_epoch'] * 1e3:.2f} ms | {eps['S']} / {eps['M']} / {eps['L']} / {eps['XL']} | "
            f"{per['S']:.0f} | {per['M']:.0f} | {per['L']:.0f} | {per['XL']:.0f} | **{tot:.0f}** |"
        )
    lines += [
        "",
        f"Grand total (square-root epoch rule): **{grand:.0f} GPU-h** (L40S-equivalent).",
        "",
        "## Conservative scenario: 30 epochs at every tier (or the dev best epoch if larger), 3 seeds",
        "",
        "| model | task | S | M | L | XL | total GPU-h |",
        "|---|---|---|---|---|---|---|",
    ]
    grand2 = 0.0
    for r in rows:
        per = {}
        for tier, n in LADDER.items():
            e = max(30, r["best_epoch"])
            per[tier] = (
                n
                * TRAIN_SHARE[tier]
                * e
                * r["s_per_sample_epoch"]
                * PIXELS[tier]
                / PIXELS["S"]
                / 3600
                * SEEDS
            )
        tot = sum(per.values())
        grand2 += tot
        lines.append(
            f"| {r['model']} | {r['task']} | {per['S']:.0f} | {per['M']:.0f} | {per['L']:.0f} | {per['XL']:.0f} | **{tot:.0f}** |"
        )
    lines += [
        "",
        f"Grand total (30-epoch rule): **{grand2:.0f} GPU-h**. Both scenarios exclude evaluation passes (a few minutes per run "
        "at S; XL/XXL inference is batch-1 and adds ~1 GPU-h per model), hyper-parameter search, and the physics-informed "
        "variant. Per-epoch times were measured with small datasets (1.8k items), where fixed per-step overheads dominate: "
        "the ms/sample figures are upper bounds for well-batched training at scale.",
        "",
        "ViT rows at L/XL assume windowed "
        "attention (global attention at 512² with patch 4 = 16 384 tokens is not feasible); GNN rows assume the same 12-hop "
        "depth (its receptive field, not its cost, is the limit at larger tiers).",
    ]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
