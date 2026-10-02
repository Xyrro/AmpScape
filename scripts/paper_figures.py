#!/usr/bin/env python
"""Regenerate every paper figure and table from the committed result files (Phase 12, brief §14: one script).

  python scripts/paper_figures.py [--out paper] [--skip-stats]

Outputs (all under paper/):
  figures/dataset_stats_*.png            F1  dataset statistics (delegates to scripts/dataset_stats_figures.py)
  figures/t4_pareto_{M,L}.png, tables/t4_pareto_{M,L}.md
                                         F2  T4 error vs cost (solver block sizes + learned models vs the exact block-1 map)
  figures/error_vs_tier.png, tables/baselines_sml.md
                                         F3  rel-L2 vs tier per model and task, mean ± std over seeds (test_id)
  figures/scale_transfer.png, tables/scale_transfer.md
                                         F4  L-trained models evaluated at L / XL / XXL (zero-shot; scale-aware variants when present)
  figures/wp7_agreement.png, tables/wp7_per_tile.md
                                         F5  many-query demonstration: surrogate vs solver conclusions per tile
Every number comes from docs/tables/*.md, runs/full/*/results*.json or aux/wp7/demo_results.parquet; the script
never recomputes metrics. Missing inputs are reported and skipped, never fabricated.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
TIER_ORDER = ["S", "M", "L", "XL", "XXL"]
MODEL_LABEL = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN"}


def log(msg: str) -> None:
    print(msg, flush=True)


# ----------------------------------------------------------------------------------------------------------------- F1
def dataset_stats(out: pathlib.Path) -> None:
    fig_dir = out / "figures"
    r = subprocess.run(
        [
            sys.executable,
            "scripts/dataset_stats_figures.py",
            "--out",
            str(fig_dir),
            "--table",
            str(out / "tables" / "dataset_statistics.md"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        log(f"F1 dataset statistics: FAILED\n{r.stderr[-600:]}")
    else:
        log(
            "F1 dataset statistics: "
            + ", ".join(p.name for p in sorted(fig_dir.glob("dataset_stats_*.png")))
        )


# ----------------------------------------------------------------------------------------------------------------- F2
def t4_pareto(out: pathlib.Path) -> None:
    for tier in ("M", "L"):
        ref = ROOT / "aux" / "t4_bs1_reference" / f"{tier}_bs1"
        blocks = sorted(glob.glob(str(ROOT / "aux" / "t4_blocksize_baselines" / f"{tier}_*")))
        runs = sorted(
            p
            for p in glob.glob(str(ROOT / "runs" / "full" / f"*_T4_{tier}_s*"))
            if (pathlib.Path(p) / "eval_t4_reference" / "results.json").exists()
        )
        if not ref.exists():
            log(f"F2 T4 Pareto {tier}: reference {ref} missing — skipped")
            continue
        r = subprocess.run(
            [
                sys.executable,
                "scripts/t4_pareto.py",
                "--reference",
                str(ref),
                "--blocks",
                *blocks,
                "--runs",
                *runs,
                "--tier",
                tier,
                "--out",
                str(out / "tables" / f"t4_pareto_{tier}.md"),
                "--fig",
                str(out / "figures" / f"t4_pareto_{tier}.png"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            log(f"F2 T4 Pareto {tier}: FAILED\n{r.stderr[-600:]}")
        else:
            log(f"F2 T4 Pareto {tier}: {len(blocks)} block builds, {len(runs)} learned runs")


# ----------------------------------------------------------------------------------------------------------------- F3
def read_markdown_table(path: pathlib.Path) -> pd.DataFrame:
    rows, header = [], None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    df = pd.DataFrame(rows)
    for c in df.columns:
        if c in ("task", "tier", "split", "model"):
            continue
        df[c] = pd.to_numeric(df[c].replace({"–": np.nan, "": np.nan}), errors="coerce")
    return df


def split_run_name(model: str) -> tuple[str, str, str, int | None, str]:
    """'unet_T1_M_s2[_suffix]' -> (base 'unet', task, tier, seed, suffix); non-learned rows -> (model, '', '', None, '')."""
    m = re.match(r"^(unet|fno|vit|gnn)_(T\w+)_(S|M|L|XL|XXL)_s(\d+)(?:_(.+))?$", model)
    if not m:
        return model, "", "", None, ""
    return m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5) or ""


def error_vs_tier(out: pathlib.Path) -> None:
    src = ROOT / "docs" / "tables" / "baselines_full.md"
    if not src.exists():
        log("F3 error vs tier: docs/tables/baselines_full.md missing — skipped")
        return
    df = read_markdown_table(src)
    df = df[df.split == "test_id"].copy()
    parsed = df.model.apply(split_run_name)
    df["base"] = [p[0] for p in parsed]
    df["seed"] = [p[3] for p in parsed]
    df["suffix"] = [p[4] for p in parsed]
    learned = df[df.seed.notna() & (df.suffix == "")]
    metrics = ["rel_l2", "mae_log10eps", "top5_iou", "pinch_recall", "spearman"]
    agg = (
        learned.groupby(["task", "tier", "base"])[metrics + ["speed-up (median)", "train GPU-h"]]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    # table: mean ± std over seeds
    lines = [
        "# Learned baselines on test_id, mean ± std over seeds (from docs/tables/baselines_full.md)",
        "",
        "| task | tier | model | seeds | rel-L2 | MAE log10 | top-5 % IoU | pinch recall | Spearman | speed-up (median) | train GPU-h |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in agg.sort_values(["task", "tier", "base"]).iterrows():
        n = int(r[("rel_l2", "count")])

        def ms(k, r=r, n=n):
            m, s = r[(k, "mean")], r[(k, "std")]
            return f"{m:.3f} ± {s:.3f}" if n > 1 and np.isfinite(s) else f"{m:.3f}"

        lines.append(
            f"| {r['task'].iloc[0] if hasattr(r['task'], 'iloc') else r['task']} | {r['tier'].iloc[0] if hasattr(r['tier'], 'iloc') else r['tier']} | "
            f"{MODEL_LABEL.get(r['base'].iloc[0] if hasattr(r['base'], 'iloc') else r['base'], r['base'])} | {n} | {ms('rel_l2')} | {ms('mae_log10eps')} | "
            f"{ms('top5_iou')} | {ms('pinch_recall')} | {ms('spearman')} | {r[('speed-up (median)', 'mean')]:.0f} | "
            f"{r[('train GPU-h', 'mean')]:.2f} |"
        )
    (out / "tables" / "baselines_sml.md").write_text("\n".join(lines) + "\n")
    # figure: rel-L2 vs tier, one panel per task
    tasks = [t for t in ("T1", "T3", "T4") if t in set(learned.task)]
    fig, axes = plt.subplots(1, len(tasks), figsize=(4.2 * len(tasks), 3.6), sharey=False)
    axes = np.atleast_1d(axes)
    for ax, task in zip(axes, tasks, strict=False):
        sub = agg[agg.task == task]
        for base in ("unet", "fno", "vit", "gnn"):
            g = sub[sub.base == base]
            if not len(g):
                continue
            tiers = [t for t in TIER_ORDER if t in set(g.tier)]
            x = [TIER_ORDER.index(t) for t in tiers]
            y = [float(g[g.tier == t][("rel_l2", "mean")].iloc[0]) for t in tiers]
            e = [float(np.nan_to_num(g[g.tier == t][("rel_l2", "std")].iloc[0])) for t in tiers]
            ax.errorbar(x, y, yerr=e, marker="o", capsize=3, label=MODEL_LABEL[base])
        present = [t for t in TIER_ORDER if t in set(sub.tier)]
        ax.set_xticks([TIER_ORDER.index(t) for t in present])
        ax.set_xticklabels(present)
        ax.set_title(f"{task}: rel-L2 on test_id (mean ± std over seeds)")
        ax.set_xlabel("tier")
        ax.set_ylabel("relative L2")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "figures" / "error_vs_tier.png", dpi=150)
    plt.close(fig)
    log(f"F3 error vs tier: {len(agg)} (task, tier, model) rows")


# ----------------------------------------------------------------------------------------------------------------- F4
def scale_transfer(out: pathlib.Path) -> None:
    rows = []
    for p in sorted(glob.glob(str(ROOT / "runs" / "full" / "*_L_s*" / "results_transfer.json"))):
        run = pathlib.Path(p).parent
        base, task, tier, seed, suffix = split_run_name(run.name)
        if seed is None:
            continue
        ev = json.loads(pathlib.Path(p).read_text())["eval"]
        for tag, v in ev.items():
            m = re.match(r"^[^_]+_(XL|XXL)_(test_id|test_ood|ood_region)$", tag)
            if not m or task not in v:
                continue
            d = v[task]
            rows.append(
                {
                    "model": base,
                    "task": task,
                    "variant": "scale-aware" if suffix == "scalenorm" else "zero-shot",
                    "seed": seed,
                    "eval_tier": m.group(1),
                    "split": m.group(2),
                    "rel_l2": d.get("rel_l2"),
                    "spearman": d.get("spearman"),
                    "top5_iou": d.get("top5_iou"),
                    "throughput_err": d.get("phys_throughput_err"),
                    "n": v.get("n_rows"),
                }
            )
        # the L row of the same run (its own tier) for reference
        rj = run / "results.json"
        if rj.exists():
            r = json.loads(rj.read_text())
            for tag, v in r["eval"].items():
                m = re.match(r"^[^_]+_L_(test_id|test_ood|ood_region)$", tag)
                if m and task in v:
                    d = v[task]
                    rows.append(
                        {
                            "model": base,
                            "task": task,
                            "variant": "scale-aware" if suffix == "scalenorm" else "zero-shot",
                            "seed": seed,
                            "eval_tier": "L",
                            "split": m.group(1),
                            "rel_l2": d.get("rel_l2"),
                            "spearman": d.get("spearman"),
                            "top5_iou": d.get("top5_iou"),
                            "throughput_err": d.get("phys_throughput_err"),
                            "n": v.get("n_rows"),
                        }
                    )
    if not rows:
        log("F4 scale transfer: no results_transfer.json found — skipped")
        return
    df = pd.DataFrame(rows)
    agg = (
        df.groupby(["task", "model", "variant", "eval_tier", "split"])[
            ["rel_l2", "spearman", "top5_iou", "throughput_err"]
        ]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    lines = [
        "# Scale transfer: models trained at L evaluated at L, XL and XXL (from runs/full/*/results_transfer.json; "
        "L rows from results.json). Mean ± std over seeds; zero-shot = official config; scale-aware = --target-norm scale.",
        "",
        "| task | model | variant | eval tier | split | seeds | rel-L2 | Spearman | top-5 % IoU | throughput err |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    order = {"L": 0, "XL": 1, "XXL": 2}
    agg["o"] = agg["eval_tier"].map(order)
    for _, r in agg.sort_values(["task", "model", "variant", "o", "split"]).iterrows():
        n = int(r[("rel_l2", "count")])

        def ms(k, r=r, n=n):
            m, s = r[(k, "mean")], r[(k, "std")]
            if not np.isfinite(m):
                return "–"
            return f"{m:.3f} ± {s:.3f}" if n > 1 and np.isfinite(s) else f"{m:.3f}"

        lines.append(
            f"| {r['task'].iloc[0]} | {MODEL_LABEL.get(r['model'].iloc[0], r['model'].iloc[0])} | {r['variant'].iloc[0]} | "
            f"{r['eval_tier'].iloc[0]} | {r['split'].iloc[0]} | {n} | {ms('rel_l2')} | {ms('spearman')} | {ms('top5_iou')} | {ms('throughput_err')} |"
        )
    (out / "tables" / "scale_transfer.md").write_text("\n".join(lines) + "\n")
    # figure: test_id rel-L2 at L / XL / XXL per model, panels per task, zero-shot solid vs scale-aware hatched
    tasks = sorted(set(df.task))
    fig, axes = plt.subplots(1, len(tasks), figsize=(4.6 * len(tasks), 3.6))
    axes = np.atleast_1d(axes)
    for ax, task in zip(axes, tasks, strict=False):
        sub = agg[(agg.task == task) & (agg.split == "test_id")]
        models = [m for m in ("unet", "fno", "vit", "gnn") if m in set(sub.model)]
        variants = [v for v in ("zero-shot", "scale-aware") if v in set(sub.variant)]
        width = 0.8 / (len(models) * max(len(variants), 1))
        for i, model in enumerate(models):
            for j, variant in enumerate(variants):
                g = sub[(sub.model == model) & (sub.variant == variant)]
                xs, ys, es = [], [], []
                for t in ("L", "XL", "XXL"):
                    gg = g[g.eval_tier == t]
                    if len(gg):
                        xs.append(
                            order[t]
                            + (i * len(variants) + j - (len(models) * len(variants) - 1) / 2)
                            * width
                        )
                        ys.append(float(gg[("rel_l2", "mean")].iloc[0]))
                        es.append(float(np.nan_to_num(gg[("rel_l2", "std")].iloc[0])))
                if xs:
                    ax.bar(
                        xs,
                        ys,
                        width=width,
                        yerr=es,
                        capsize=2,
                        label=f"{MODEL_LABEL[model]} ({variant})",
                        hatch="//" if variant == "scale-aware" else None,
                        alpha=0.9,
                    )
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["L (trained)", "XL", "XXL"])
        vals = sub[("rel_l2", "mean")].astype(float)
        if len(vals) and np.nanmax(vals) / max(np.nanmin(vals), 1e-9) > 8:
            ax.set_yscale("log")
        ax.set_ylabel("relative L2 (test_id)")
        ax.set_title(f"{task}: trained at L, evaluated across scales")
        ax.grid(alpha=0.3, axis="y")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "figures" / "scale_transfer.png", dpi=150)
    plt.close(fig)
    log(
        f"F4 scale transfer: {len(df)} rows from {df.groupby(['model', 'task', 'variant', 'seed']).ngroups} runs"
    )


# ----------------------------------------------------------------------------------------------------------------- F5
def wp7(out: pathlib.Path) -> None:
    src = ROOT / "aux" / "wp7" / "demo_results.parquet"
    if not src.exists():
        log("F5 WP7: aux/wp7/demo_results.parquet missing — skipped")
        return
    d = pd.read_parquet(src)
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    ax = axes[0]
    ax.scatter(d.stability_mean_iou_solver, d.stability_mean_iou_model, s=28)
    lim = [0, max(d.stability_mean_iou_solver.max(), d.stability_mean_iou_model.max()) * 1.05]
    ax.plot(lim, lim, "k--", lw=0.8)
    ax.set_xlabel("solver: mean pairwise top-5 % IoU across tables")
    ax.set_ylabel("surrogate")
    ax.set_title("Stability of priority areas (per tile)")
    ax = axes[1]
    ax.hist(d.core75_iou_model_vs_solver, bins=10, color="tab:green", alpha=0.8)
    ax.set_xlabel("IoU of consensus cores (surrogate vs solver)")
    ax.set_title(f"Consensus core agreement (median {d.core75_iou_model_vs_solver.median():.2f})")
    ax = axes[2]
    ax.scatter(d.pinch_persistent_recall, d.pinch_persistent_precision, s=28, color="tab:red")
    ax.set_xlabel("persistent pinch-point recall")
    ax.set_ylabel("precision")
    ax.set_title(
        f"Persistent pinch points (ranking Spearman {d.ranking_spearman.mean():.3f}, top-1 table agrees {int(d.top1_table_agree.sum())}/{len(d)})"
    )
    for a in axes:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "figures" / "wp7_agreement.png", dpi=150)
    plt.close(fig)
    cols = [
        "tile_id",
        "stability_mean_iou_solver",
        "stability_mean_iou_model",
        "core75_iou_model_vs_solver",
        "ranking_spearman",
        "top1_table_agree",
        "pinch_persistent_recall",
        "pinch_persistent_precision",
        "model_rel_l2_mean",
    ]
    lines = [
        "# WP7 per-tile results (aux/wp7/demo_results.parquet)",
        "",
        "| " + " | ".join(cols) + " |",
        "|" + "---|" * len(cols),
    ]
    for _, r in d[cols].iterrows():
        lines.append(
            "| "
            + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r.values)
            + " |"
        )
    (out / "tables" / "wp7_per_tile.md").write_text("\n".join(lines) + "\n")
    log(f"F5 WP7: {len(d)} tiles")


def refresh_baselines_table() -> None:
    """docs/tables/baselines_full.md from runs/full (scripts/collect_baselines.py) so F3 reads current results."""
    r = subprocess.run(
        [
            sys.executable,
            "scripts/collect_baselines.py",
            "--runs",
            "runs/full",
            "--out",
            "docs/tables/baselines_full.md",
            "--title",
            "Phase 10-full learned baselines (running table, regenerated by scripts/paper_figures.py)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    log(
        "F0 baselines table: " + ("refreshed" if r.returncode == 0 else f"FAILED {r.stderr[-300:]}")
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default="paper")
    ap.add_argument(
        "--skip-stats", action="store_true", help="skip F1 (reads the full indexes; slow)"
    )
    a = ap.parse_args()
    out = ROOT / a.out
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    if (ROOT / "runs" / "full").exists():
        refresh_baselines_table()
    if not a.skip_stats:
        dataset_stats(out)
    t4_pareto(out)
    error_vs_tier(out)
    scale_transfer(out)
    wp7(out)
    log("done")


if __name__ == "__main__":
    main()
