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
  figures/wp4_data_scaling.png, tables/wp4_data_scaling.md
                                         F6  WP4 data-scaling ablation at S (fixed-epoch vs fixed-step)
  figures/ood_degradation.png, tables/ood_degradation.md
                                         F7  per-OOD-split degradation at the training tier (ratios to test_id)
  baselines.md, dataset_statistics.md     F8  brief §14 deliverables: all-split baselines table (mean ± std); dataset statistics table
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
import matplotlib.patches  # noqa: E402
import matplotlib.ticker  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
TIER_ORDER = ["S", "M", "L", "XL", "XXL"]
MODEL_LABEL = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN", "mgno": "MgNO"}


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
            str(out / "dataset_statistics.md"),  # brief §14 deliverable name
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
        # per (model, task, tier) the official configuration's runs (tuning_decisions.json): the tier-tuned re-run
        # ('_t2' after the seed) or the pre-tuning run of the same seed (2026-10-14/15)
        names = {pathlib.Path(p).name for p in runs}

        def keep(p: str) -> bool:
            n = pathlib.Path(p).name
            base = n.split("_")[0]
            t2_official = official_config(base, "T4", tier) == "t2"
            if "_t2" in n:
                return t2_official
            return not (t2_official and re.sub(r"(_s\d+)", r"\1_t2", n, count=1) in names)

        runs = [p for p in runs if keep(p)]
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
    """'unet_T1_M_s2[_suffix]' -> (base 'unet', task, tier, seed, suffix); non-learned rows -> (model, '', '', None, '').
    The suffix 't2' (tier-tuned official configuration, item 2 of 2026-10-05) is reported as suffix '' with the
    run marked tuned; callers that prefer tuned rows use `prefer_tuned`."""
    m = re.match(r"^(unet|fno|vit|gnn|mgno)_(T\w+)_(S|M|L|XL|XXL)_s(\d+)(?:_(.+))?$", model)
    if not m:
        return model, "", "", None, ""
    suffix = m.group(5) or ""
    if suffix == "t2":
        suffix = ""
    elif suffix.startswith("t2_"):
        suffix = suffix[3:]  # '_t2_scalenorm': the tier-tuned scale-aware variant (2026-10-14)
    return m.group(1), m.group(2), m.group(3), int(m.group(4)), suffix


def official_config(base: str, task: str, tier: str) -> str:
    """'t2' when the tier-tuned configuration is the official one for (model, task, tier), else 'base' — from
    docs/tables/tuning_decisions.json (scripts/tuning_decisions.py: selection per model × task × tier on validation
    loss, owner rule 2026-10-15). Without a decision the pre-tuning run is official."""
    global _DECISIONS
    if _DECISIONS is None:
        f = ROOT / "docs" / "tables" / "tuning_decisions.json"
        _DECISIONS = json.loads(f.read_text()) if f.exists() else {}
    return _DECISIONS.get(f"{base}_{task}_{tier}", {}).get("official", "base")


_DECISIONS = None


def prefer_tuned(df: pd.DataFrame) -> pd.DataFrame:
    """Among rows of one (task, tier, split, base, seed) keep the run of the official configuration for that
    (model, task, tier): the tier-tuned run ('_t2') where `official_config` says so, else the pre-tuning run;
    adds a boolean column `tuned`."""
    df = df.copy()
    df["tuned"] = df.model.str.contains(r"_t2(?:$|_)", regex=True)
    off_t2 = df.apply(lambda r: official_config(r["base"], r["task"], r["tier"]) == "t2", axis=1)
    key = ["task", "tier", "split", "base", "seed"]
    has_t2 = df[df.tuned].groupby(key).size().index
    drop = df.index[((~df.tuned) & off_t2 & df.set_index(key).index.isin(has_t2)) | (df.tuned & ~off_t2)]
    return df.drop(drop)


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
    learned = prefer_tuned(df[df.seed.notna() & (df.suffix == "")])
    metrics = ["rel_l2", "mae_log10eps", "top5_iou", "pinch_recall", "spearman"]
    agg = (
        learned.groupby(["task", "tier", "base"])[metrics + ["speed-up (median)", "train GPU-h"]]
        .agg(["mean", "std", "count", "median"])
        .reset_index()
    )
    # table: mean ± std over seeds, plus the median over seeds of rel-L2 (owner, 2026-10-15: at L the seed
    # disagreement on rel-L2 makes the mean outlier-driven)
    lines = [
        "# Learned baselines on test_id, mean ± std over seeds (from docs/tables/baselines_full.md); rel-L2 median = median over seeds",
        "",
        "| task | tier | model | seeds | rel-L2 | rel-L2 median | MAE log10 | top-5 % IoU | pinch recall | Spearman | speed-up (median) | train GPU-h |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in agg.sort_values(["task", "tier", "base"]).iterrows():
        n = int(r[("rel_l2", "count")])

        def ms(k, r=r, n=n):
            m, s = r[(k, "mean")], r[(k, "std")]
            return f"{m:.3f} ± {s:.3f}" if n > 1 and np.isfinite(s) else f"{m:.3f}"

        lines.append(
            f"| {r['task'].iloc[0] if hasattr(r['task'], 'iloc') else r['task']} | {r['tier'].iloc[0] if hasattr(r['tier'], 'iloc') else r['tier']} | "
            f"{MODEL_LABEL.get(r['base'].iloc[0] if hasattr(r['base'], 'iloc') else r['base'], r['base'])} | {n} | {ms('rel_l2')} | {r[('rel_l2', 'median')]:.3f} | {ms('mae_log10eps')} | "
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
        for base in ("unet", "fno", "vit", "gnn", "mgno"):
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
        if "_t2" not in run.name:
            t2 = run.parent / f"{base}_{task}_{tier}_s{seed}_t2{'_' + suffix if suffix else ''}"
            if (t2 / "results_transfer.json").exists() and official_config(base, task, tier) == "t2":
                continue  # the tier-tuned counterpart is the official L model (also for scale-aware)
        elif official_config(base, task, tier) != "t2":
            continue  # tuned run of a (model, task, tier) whose official configuration is the pre-tuning one
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
        .agg(["mean", "std", "count", "median"])
        .reset_index()
    )
    lines = [
        "# Scale transfer: models trained at L evaluated at L, XL and XXL (from runs/full/*/results_transfer.json; "
        "L rows from results.json). Mean ± std over seeds, rel-L2 also as the median over seeds; zero-shot = official config; scale-aware = --target-norm scale.",
        "",
        "| task | model | variant | eval tier | split | seeds | rel-L2 | rel-L2 median | Spearman | top-5 % IoU | throughput err |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
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
            f"{r['eval_tier'].iloc[0]} | {r['split'].iloc[0]} | {n} | {ms('rel_l2')} | {r[('rel_l2', 'median')]:.3f} | {ms('spearman')} | {ms('top5_iou')} | {ms('throughput_err')} |"
        )
    (out / "tables" / "scale_transfer.md").write_text("\n".join(lines) + "\n")
    # figure: test_id rel-L2 at L / XL / XXL per model, panels per task, zero-shot solid vs scale-aware hatched
    tasks = sorted(set(df.task))
    fig, axes = plt.subplots(1, len(tasks), figsize=(4.6 * len(tasks), 3.6))
    axes = np.atleast_1d(axes)
    for ax, task in zip(axes, tasks, strict=False):
        sub = agg[(agg.task == task) & (agg.split == "test_id")]
        models = [m for m in ("unet", "fno", "vit", "gnn", "mgno") if m in set(sub.model)]
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


# ----------------------------------------------------------------------------------------------------------------- F6
def wp4_data_scaling(out: pathlib.Path) -> None:
    """WP4: rel-L2 on test_id vs number of training landscapes at S (U-Net, FNO; fixed-epoch and fixed-step)."""
    src = ROOT / "docs" / "tables" / "baselines_full.md"
    if not src.exists():
        return
    df = read_markdown_table(src)
    df = df[(df.split == "test_id") & (df.tier == "S") & (df.task == "T1")].copy()
    rows = []
    for _, r in df.iterrows():
        m = re.match(r"^(unet|fno)_T1_S_s1(?:_n(\d+)_(ep30|steps))?$", r.model)
        if not m:
            continue
        n = int(m.group(2)) if m.group(2) else None
        rows.append(
            {
                "model": m.group(1),
                "n_train": n,
                "regime": m.group(3) or "full",
                "rel_l2": r.rel_l2,
                "mae": r.mae_log10eps,
                "top5_iou": r.top5_iou,
                "epochs": r.epochs,
                "gpu_h": r["train GPU-h"],
            }
        )
    if not rows:
        log("F6 WP4: no rows — skipped")
        return
    d = pd.DataFrame(rows)
    full_n = 61577  # S train landscapes with QC pass (train split of the S index; docs/tables/final_counts.json: 63,303 train samples)
    d.loc[d.regime == "full", "n_train"] = full_n
    lines = [
        "# WP4 data-scaling ablation at S, task T1, seed 1 (from docs/tables/baselines_full.md)",
        "",
        "fixed-epoch = 30 epochs on the subset; fixed-step ≈ the full run's optimisation steps; full = the official run (all train landscapes).",
        "",
        "| model | n train | regime | rel-L2 | MAE log10 | top-5 % IoU | epochs | train GPU-h |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, r in d.sort_values(["model", "n_train", "regime"]).iterrows():
        lines.append(
            f"| {MODEL_LABEL[r.model]} | {int(r.n_train):,} | {r.regime} | {r.rel_l2:.3f} | {r.mae:.3f} | {r.top5_iou:.3f} | {int(r.epochs)} | {r.gpu_h:.2f} |"
        )
    (out / "tables" / "wp4_data_scaling.md").write_text("\n".join(lines) + "\n")
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    for model, ls in (("unet", "-"), ("fno", "--")):
        for regime, mk in (("ep30", "o"), ("steps", "s")):
            g = d[(d.model == model) & (d.regime.isin([regime, "full"]))].sort_values("n_train")
            if len(g):
                ax.plot(
                    g.n_train,
                    g.rel_l2,
                    marker=mk,
                    linestyle=ls,
                    label=f"{MODEL_LABEL[model]} ({'fixed epochs' if regime == 'ep30' else 'fixed steps'})",
                )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("training landscapes (tier S)")
    ax.set_ylabel("relative L2 on test_id (T1)")
    ax.set_title("WP4: data scaling at S")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "figures" / "wp4_data_scaling.png", dpi=150)
    plt.close(fig)
    log(f"F6 WP4: {len(d)} rows")


# ----------------------------------------------------------------------------------------------------------------- F7
def ood_degradation(out: pathlib.Path) -> None:
    """Per-OOD-split degradation at the training tier: rel-L2 on test_ood / ood_region / published tiles relative to
    test_id, official runs, mean over seeds (brief §14 ood_analysis)."""
    src = ROOT / "docs" / "tables" / "baselines_full.md"
    if not src.exists():
        return
    df = read_markdown_table(src)
    parsed = df.model.apply(split_run_name)
    df["base"] = [p[0] for p in parsed]
    df["seed"] = [p[3] for p in parsed]
    df["suffix"] = [p[4] for p in parsed]
    df = prefer_tuned(df[df.seed.notna() & (df.suffix == "")].copy())
    df["split"] = df.split.replace({"published S": "published"})
    splits = ["test_id", "test_ood", "ood_region", "published"]
    df = df[df.split.isin(splits)]
    g = df.groupby(["task", "tier", "base", "split"])[
        ["rel_l2", "spearman", "top5_iou", "pinch_recall"]
    ].mean()
    med = df.groupby(["task", "tier", "base", "split"])["rel_l2"].median().unstack("split")
    wide = g["rel_l2"].unstack("split")
    for sp_ in splits:
        if sp_ not in wide:
            wide[sp_] = np.nan
        wide[f"{sp_} median"] = med[sp_] if sp_ in med else np.nan
    wide["test_ood/test_id"] = wide["test_ood"] / wide["test_id"]
    wide["ood_region/test_id"] = wide["ood_region"] / wide["test_id"]
    wide["published/test_id"] = wide["published"] / wide["test_id"]
    wide = wide.reset_index()
    lines = [
        "# OOD degradation at the training tier (rel-L2, official configs, mean over seeds with the median over seeds in brackets; from docs/tables/baselines_full.md)",
        "",
        "test_ood = held-out resistance table (forest_bird) + held-out contrast (10⁶); ood_region = held-out biomes/realm; "
        "published = real tiles with published resistance surfaces (S only). Ratios > 1 mean degradation relative to test_id.",
        "",
        "| task | tier | model | test_id [median] | test_ood [median] | ood_region [median] | published [median] | test_ood / id | ood_region / id | published / id |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    def f(v):
        return "–" if not np.isfinite(v) else f"{v:.3f}"

    order = {t: i for i, t in enumerate(TIER_ORDER)}
    wide["o"] = wide.tier.map(order)
    for _, r in wide.sort_values(["task", "o", "base"]).iterrows():
        def fm(sp_, r=r):
            return "–" if not np.isfinite(r[sp_]) else f"{r[sp_]:.3f} [{r[f'{sp_} median']:.3f}]"

        lines.append(
            f"| {r.task} | {r.tier} | {MODEL_LABEL.get(r.base, r.base)} | {fm('test_id')} | {fm('test_ood')} | {fm('ood_region')} | "
            f"{fm('published')} | {f(r['test_ood/test_id'])} | {f(r['ood_region/test_id'])} | {f(r['published/test_id'])} |"
        )
    (out / "tables" / "ood_degradation.md").write_text("\n".join(lines) + "\n")
    tasks = [t for t in ("T1", "T3", "T4") if t in set(wide.task)]
    fig, axes = plt.subplots(1, len(tasks), figsize=(4.6 * len(tasks), 3.8), sharey=True)
    axes = np.atleast_1d(axes)
    ratios = [
        ("test_ood/test_id", "held-out table + contrast"),
        ("ood_region/test_id", "held-out region"),
        ("published/test_id", "published tiles (S)"),
    ]
    for ax, task in zip(axes, tasks, strict=False):
        sub = wide[wide.task == task].sort_values(["o", "base"])
        labels = [f"{r.tier}\n{MODEL_LABEL.get(r.base, r.base)}" for _, r in sub.iterrows()]
        x = np.arange(len(sub))
        w = 0.27
        for k, (col, lab) in enumerate(ratios):
            ax.bar(x + (k - 1) * w, sub[col].values, width=w, label=lab)
        ax.axhline(1.0, color="k", lw=0.8, ls="--")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_title(f"{task}: rel-L2 relative to test_id")
        ax.grid(alpha=0.3, axis="y")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("rel-L2(split) / rel-L2(test_id)")
    fig.tight_layout()
    fig.savefig(out / "figures" / "ood_degradation.png", dpi=150)
    plt.close(fig)
    log(f"F7 OOD degradation: {len(wide)} (task, tier, model) rows")


# ----------------------------------------------------------------------------------------------------------------- F8
def baselines_all_splits(out: pathlib.Path) -> None:
    """paper/baselines.md (brief §14): every task / tier / model / split, mean ± std over seeds, official configs."""
    src = ROOT / "docs" / "tables" / "baselines_full.md"
    if not src.exists():
        return
    df = read_markdown_table(src)
    parsed = df.model.apply(split_run_name)
    df["base"] = [p[0] for p in parsed]
    df["seed"] = [p[3] for p in parsed]
    df["suffix"] = [p[4] for p in parsed]
    learned = df[df.seed.notna() & (df.suffix == "")]
    metrics = [
        "rel_l2",
        "mae_log10eps",
        "top5_iou",
        "pinch_recall",
        "spearman",
        "corridor_dice",
        "ssim",
    ]
    agg = (
        learned.groupby(["task", "tier", "split", "base"])[metrics + ["speed-up (median)"]]
        .agg(["mean", "std", "count", "median"])
        .reset_index()
    )
    order = {t: i for i, t in enumerate(TIER_ORDER)}
    sp_order = {"test_id": 0, "test_ood": 1, "ood_region": 2, "published S": 3}
    agg["o"] = agg["tier"].map(order)
    agg["so"] = agg["split"].map(sp_order).fillna(9)
    lines = [
        "# Learned baselines — all evaluation splits, mean ± std over seeds, rel-L2 also as the median over seeds (official configs; from docs/tables/baselines_full.md)",
        "",
        "Non-learned baselines (coarsen ×4, Omniscape block sizes) are in docs/tables/baselines_full.md and paper/tables/t4_pareto_{M,L}.md.",
        "",
        "| task | tier | split | model | seeds | rel-L2 | rel-L2 median | MAE log10 | top-5 % IoU | pinch recall | Spearman | corridor dice | SSIM | speed-up (median) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in agg.sort_values(["task", "o", "so", "base"]).iterrows():
        n = int(r[("rel_l2", "count")])

        def ms(k, r=r, n=n):
            m, s_ = r[(k, "mean")], r[(k, "std")]
            if not np.isfinite(m):
                return "–"
            return f"{m:.3f} ± {s_:.3f}" if n > 1 and np.isfinite(s_) else f"{m:.3f}"

        lines.append(
            f"| {r['task'].iloc[0]} | {r['tier'].iloc[0]} | {r['split'].iloc[0]} | {MODEL_LABEL.get(r['base'].iloc[0], r['base'].iloc[0])} | {n} | "
            f"{ms('rel_l2')} | {r[('rel_l2', 'median')]:.3f} | {ms('mae_log10eps')} | {ms('top5_iou')} | {ms('pinch_recall')} | {ms('spearman')} | "
            f"{ms('corridor_dice')} | {ms('ssim')} | {r[('speed-up (median)', 'mean')]:.0f} |"
        )
    (out / "baselines.md").write_text("\n".join(lines) + "\n")
    log(f"F8 baselines (all splits): {len(agg)} rows -> paper/baselines.md")


# ============================================================================================ paper (LaTeX) figures
# 2026-10-16: the NeurIPS submission's figures. One style for every panel; vector PDF (+ PNG preview) written to
# paper/neurips/figures/. Raster panels (overview, gallery, qualitative) read the small arrays extracted by
# scripts/paper_figdata.py (paper/figdata/*.npz, manifest.json names every source file); numeric panels read the same
# regenerated tables as the Markdown figures above.
PAPER_STYLE = {
    "font.size": 8,
    "axes.titlesize": 8.5,
    "axes.labelsize": 8,
    "legend.fontsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 120,
    "savefig.dpi": 200,
    "pdf.fonttype": 42,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
}
MODEL_COLOR = {"unet": "#1f77b4", "fno": "#d62728", "vit": "#2ca02c", "gnn": "#9467bd", "mgno": "#ff7f0e"}
MODEL_ORDER = ["unet", "fno", "vit", "gnn", "mgno"]
TEX_FIG = ROOT / "paper" / "neurips" / "figures"
FIGDATA = ROOT / "paper" / "figdata"


def _save(fig, name: str) -> None:
    TEX_FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(TEX_FIG / f"{name}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(TEX_FIG / f"{name}.png", bbox_inches="tight", pad_inches=0.02, dpi=170)
    plt.close(fig)
    log(f"paper figure {name}.pdf")


def _log_current(c: np.ndarray, nodata: np.ndarray | None = None) -> np.ndarray:
    """log10(C + 1e-6 · max C), NoData masked — the metric space of the paper."""
    c = np.asarray(c, dtype=np.float64)
    m = np.nanmax(c) if np.isfinite(c).any() else 1.0
    out = np.log10(np.clip(c, 0, None) + 1e-6 * max(m, 1e-30))
    if nodata is not None:
        out = np.where(nodata.astype(bool), np.nan, out)
    return out


def _parse_ms(s) -> tuple[float, float]:
    """'0.114 ± 0.007' -> (0.114, 0.007); '0.220' -> (0.220, nan)."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return np.nan, np.nan
    txt = str(s).replace("−", "-")
    m = re.match(r"\s*([-+]?[\d.]+(?:e[-+]?\d+)?)(?:\s*±\s*([\d.]+))?", txt)
    if not m:
        return np.nan, np.nan
    return float(m.group(1)), float(m.group(2)) if m.group(2) else np.nan


def _md_rows(path: pathlib.Path) -> list[dict]:
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
    return rows


def _imshow(ax, img, cmap, vmin=None, vmax=None, title=None):
    cm = plt.get_cmap(cmap).copy()
    cm.set_bad("#e6e6e6")
    im = ax.imshow(img, cmap=cm, vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if title:
        ax.set_title(title, pad=2)
    return im


def _npz(name: str) -> dict | None:
    p = FIGDATA / f"{name}.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def fig_overview() -> None:
    """Figure 1: covariates -> resistance -> reference solvers -> targets, with the tiers and the task menu."""
    d = _npz("gallery_S_real") or _npz("gallery_S_synthetic")
    if d is None:
        log("paper fig1: figdata missing — skipped")
        return
    nd = d["points__nodata"].astype(bool)
    cov = d.get("points__covariates")
    raw = d.get("points__covariate_names", [])
    names = [str(x) for x in raw] if cov is not None else []
    if len(names) == 1 and "," in names[0]:
        names = [x.strip() for x in names[0].split(",")]
    if cov is not None and (len(names) != len(cov) or any(len(n) <= 2 for n in names)):
        names = ["land cover", "elevation", "slope", "distance to road", "distance to river", "human modification"][: len(cov)]
    with plt.rc_context(PAPER_STYLE):
        W, H = 7.0, 2.3
        fig = plt.figure(figsize=(W, H))
        side = 1.0 / W  # one-inch panels in figure fraction
        ph = 1.0 / H
        y0 = 1.0 - 0.09 - ph  # top row of panels
        cols = [0.01, 0.01 + side + 0.03, 0.01 + 2 * (side + 0.03), 0.01 + 2 * (side + 0.03) + 0.21, 0.01 + 3 * (side + 0.03) + 0.21, 0.01 + 4 * (side + 0.03) + 0.21]

        def panel(x, y, img, cmap, title, w=side, h=ph):
            ax = fig.add_axes([x, y, w, h])
            _imshow(ax, img, cmap)
            ax.set_title(title, fontsize=6.5, pad=1.5)
            return ax

        # covariates: two half-height stacks
        if cov is not None and len(cov) >= 2:
            panel(cols[0], y0 + ph / 2 + 0.01, cov[0], "Greens", (names[0] if names else "covariate 1")[:16], h=ph / 2 - 0.01)
            panel(cols[0], y0, cov[min(1, len(cov) - 1)], "terrain", (names[1] if len(names) > 1 else "covariate 2")[:16], h=ph / 2 - 0.01)
            fig.text(cols[0] + side / 2, y0 - 0.035, "open covariate layers", ha="center", fontsize=6.5)
        else:
            ax = fig.add_axes([cols[0], y0, side, ph]); ax.axis("off")
            ax.text(0.5, 0.5, "synthetic\ngenerator", ha="center", va="center", fontsize=7)
        panel(cols[1], y0, np.where(nd, np.nan, np.log10(d["points__resistance"])), "viridis", "resistance $\\log_{10} R$")
        fig.text(cols[1] + side / 2, y0 - 0.035, "resistance table", ha="center", fontsize=6.5)
        ax = fig.add_axes([cols[2], y0, 0.19, ph]); ax.axis("off")
        ax.text(0.5, 0.5, "reference solvers\nCircuitscape.jl 5.17.1\nOmniscape.jl 0.6.2\nCHOLMOD, double precision\nresidual recorded per row", ha="center", va="center", fontsize=6.3,
                bbox=dict(boxstyle="round,pad=0.5", fc="#f4f4f4", ec="#888", lw=0.8))
        ax = panel(cols[3], y0, _log_current(d["points__out_cum_current"], nd), "magma", "T1 pairwise current")
        focal = d.get("points__in_focal_mask")
        if focal is not None:
            yy, xx = np.nonzero(focal > 0)
            ax.scatter(xx, yy, s=5, c="cyan", marker="s", linewidths=0)
        if "advanced__out_current" in d:
            panel(cols[4], y0, _log_current(d["advanced__out_current"], nd), "magma", "T3 advanced current")
        panel(cols[5], y0, _log_current(d["omniscape__out_cum_current"], nd), "magma", "T4 omnidirectional current")
        fig.text((cols[3] + cols[5] + side) / 2, y0 - 0.035, "exact targets (float32 maps, float64 effective resistances)", ha="center", fontsize=6.5)
        ym = y0 + ph / 2
        for x0, x1 in ((cols[0] + side + 0.003, cols[1] - 0.003), (cols[1] + side + 0.003, cols[2] - 0.003), (cols[2] + 0.19 + 0.003, cols[3] - 0.003)):
            fig.patches.append(matplotlib.patches.FancyArrowPatch((x0, ym), (x1, ym), transform=fig.transFigure, arrowstyle="-|>", mutation_scale=8, color="#444", lw=0.9))
        # bottom block: three readable columns (tiers | tasks | splits and metrics)
        yb, hb = 0.0, y0 - 0.12
        for x0, w, txt in ((0.01, 0.30, "Tiers\nS 128$^2$ at 100 m · M 256$^2$ at 100 m\nL 512$^2$ at 200 m · XL 1024$^2$ at 500 m\nXXL 2048$^2$ at 1 km\n174,400 landscapes · 920,372 rows · 1,157 GB"),
                           (0.33, 0.36, "Tasks\nT1 pairwise current map, T2 effective resistances\nT1W wall-to-wall strips · T1R habitat regions\nT3 advanced mode (sources → grounds)\nT4 Omniscape cumulative current"),
                           (0.71, 0.29, "Splits and metrics\ntrain / val / test_id by macro-cell and seed family\nOOD: region, table, contrast, scale (XL, XXL),\nsynthetic→real, published surfaces\npixel · ranking · non-source · physics · speed-up")):
            ax = fig.add_axes([x0, yb, w, hb]); ax.axis("off")
            head, body = txt.split("\n", 1)
            ax.text(0.0, 1.0, head, ha="left", va="top", fontsize=8, fontweight="bold")
            ax.text(0.0, 0.76, body, ha="left", va="top", fontsize=7.4, linespacing=1.3)
        _save(fig, "fig1_overview")


def fig_gallery() -> None:
    """Figure 2: synthetic and real landscapes with their T1 and T4 targets at every tier."""
    import json as _json

    man = _json.loads((FIGDATA / "manifest.json").read_text()) if (FIGDATA / "manifest.json").exists() else {}
    tiers = [t for t in TIER_ORDER if (FIGDATA / f"gallery_{t}_synthetic.npz").exists() and (FIGDATA / f"gallery_{t}_real.npz").exists()]
    if not tiers:
        log("paper fig2: figdata missing — skipped")
        return
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(len(tiers), 6, figsize=(6.2, 1.0 * len(tiers) + 0.2), gridspec_kw=dict(wspace=0.05, hspace=0.08))
        axes = np.atleast_2d(axes)
        cols = ["synthetic: resistance", "T1 current", "T4 current", "real: resistance", "T1 current", "T4 current"]
        for i, tier in enumerate(tiers):
            for j, fam in enumerate(("synthetic", "real")):
                d = _npz(f"gallery_{tier}_{fam}")
                nd = d["points__nodata"].astype(bool)
                _imshow(axes[i, 3 * j], np.where(nd, np.nan, np.log10(d["points__resistance"])), "viridis")
                _imshow(axes[i, 3 * j + 1], _log_current(d["points__out_cum_current"], nd), "magma")
                _imshow(axes[i, 3 * j + 2], _log_current(d["omniscape__out_cum_current"], nd), "magma")
                m = man.get(f"gallery_{tier}_{fam}", {})
                lab = (m.get("generator", "") if fam == "synthetic" else m.get("table", "")) or ""
                axes[i, 3 * j].text(0.02, 0.98, lab, transform=axes[i, 3 * j].transAxes, ha="left", va="top", fontsize=5.5, color="w", bbox=dict(fc="k", alpha=0.45, pad=1.0, lw=0))
            axes[i, 0].set_ylabel(f"{tier}", rotation=0, labelpad=12, va="center")
        for j, c in enumerate(cols):
            axes[0, j].set_title(c, pad=2)
        _save(fig, "fig2_gallery")


def fig_qualitative() -> None:
    """Figure 3: input, exact target, best-model prediction and error map for T1 and T4 at L, in-distribution and OOD."""
    import json as _json

    man = _json.loads((FIGDATA / "manifest.json").read_text()) if (FIGDATA / "manifest.json").exists() else {}
    cases = [c for c in ("id", "ood") if (FIGDATA / f"qual_L_{c}.npz").exists()]
    if not cases:
        log("paper fig3: figdata missing — skipped")
        return
    with plt.rc_context(PAPER_STYLE):
        rows = [(c, t) for t in ("T1", "T4") for c in cases]
        fig, axes = plt.subplots(len(rows), 4, figsize=(5.6, 1.38 * len(rows) + 0.15), gridspec_kw=dict(wspace=0.05, hspace=0.12))
        axes = np.atleast_2d(axes)
        for i, (case, task) in enumerate(rows):
            d = _npz(f"qual_L_{case}")
            cfg = "points" if task == "T1" else "omniscape"
            nd = d[f"{cfg}__nodata"].astype(bool)
            tgt = _log_current(d[f"{cfg}__out_cum_current"], nd)
            prd = _log_current(d[f"{cfg}__pred_cum_current"], nd)
            vmin, vmax = np.nanpercentile(tgt, 1), np.nanmax(tgt)
            _imshow(axes[i, 0], np.where(nd, np.nan, np.log10(d[f"{cfg}__resistance"])), "viridis")
            if task == "T1" and f"{cfg}__in_focal_mask" in d:
                yy, xx = np.nonzero(d[f"{cfg}__in_focal_mask"] > 0)
                axes[i, 0].scatter(xx, yy, s=6, c="cyan", marker="s", linewidths=0)
            _imshow(axes[i, 1], tgt, "magma", vmin, vmax)
            _imshow(axes[i, 2], prd, "magma", vmin, vmax)
            err = prd - tgt
            lim = np.nanpercentile(np.abs(err), 99)
            im = _imshow(axes[i, 3], err, "RdBu_r", -lim, lim)
            cb = fig.colorbar(im, ax=axes[i, 3], fraction=0.046, pad=0.02)
            cb.ax.tick_params(labelsize=5.5)
            m = man.get(f"qual_L_{case}", {})
            run = (m.get("runs") or {}).get(task, "")
            model = MODEL_LABEL.get(run.split("_")[0], run.split("_")[0]) if run else ""
            lab = f"{task} · {model}\n{'in-distribution' if case == 'id' else 'OOD: ' + str(m.get('table', '')) + ' table'}"
            axes[i, 0].set_ylabel(lab, fontsize=6.5)
        for j, c in enumerate(("input $\\log_{10} R$ (cyan: focal nodes)", "exact target", "prediction", "error, log$_{10}$ pred − log$_{10}$ target")):
            axes[0, j].set_title(c, pad=2, fontsize=7)
        _save(fig, "fig3_qualitative")


def fig_error_vs_tier_tex() -> None:
    """Figure 4: rel-L2 on test_id versus tier per task and model (mean ± std over seeds)."""
    rows = _md_rows(ROOT / "paper" / "tables" / "baselines_sml.md")
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        tasks = ["T1", "T3", "T4"]
        fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.0), gridspec_kw=dict(wspace=0.3))
        for ax, task in zip(axes, tasks, strict=False):
            for base in MODEL_ORDER:
                lab = MODEL_LABEL[base]
                g = [r for r in rows if r["task"] == task and r["model"] == lab]
                if not g:
                    continue
                g = sorted(g, key=lambda r: TIER_ORDER.index(r["tier"]))
                x = [TIER_ORDER.index(r["tier"]) for r in g]
                ms = [_parse_ms(r["rel-L2"]) for r in g]
                y = [m for m, _ in ms]
                e = [0 if np.isnan(s) else s for _, s in ms]
                ax.errorbar(x, y, yerr=e, marker="o", ms=3.5, capsize=2, lw=1.2, color=MODEL_COLOR[base], label=lab + (" (1 seed)" if base == "mgno" else ""))
            ax.set_xticks([0, 1, 2])
            ax.set_xticklabels(["S\n128²", "M\n256²", "L\n512²"])
            ax.set_yscale("log")
            ax.set_title(task + {"T1": " pairwise current", "T3": " advanced mode", "T4": " omnidirectional"}[task])
            ax.grid(alpha=0.3, which="both", lw=0.5)
            if ax is axes[0]:
                ax.set_ylabel("relative L2 on test_id")
        h, l = axes[0].get_legend_handles_labels()
        axes[1].legend(h, l, frameon=False, loc="lower right")
        _save(fig, "fig4_error_vs_tier")


def fig_pareto_L_tex() -> None:
    """Figure 5: T4 error against the exact block-1 map versus cost per landscape at L (test_id reference subset)."""
    rows = [r for r in _md_rows(ROOT / "paper" / "tables" / "t4_pareto_L.md") if r["split"] == "test_id"]
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, ax = plt.subplots(figsize=(3.4, 2.75))
        seen = set()
        for r in rows:
            cost = r["cost s / landscape"].replace("–", "")
            if not cost:
                continue
            c, y = float(cost), float(r["rel_l2"])
            m = r["method"]
            if "learned" in m:
                base = m.split("_")[0]
                sa = "scalenorm" in m
                lab = MODEL_LABEL.get(base, base) + (" (scale-aware target)" if sa else "")
                ax.scatter(c, y, s=36, marker="^" if sa else "o", facecolor=MODEL_COLOR.get(base, "k") if not sa else "w",
                           edgecolor=MODEL_COLOR.get(base, "k"), lw=1.0, zorder=3, label=lab if lab not in seen else None)
                seen.add(lab)
            else:
                yy = max(y, 2e-3)
                lab = m.replace(" (correct_artifacts=1)", "").replace(" (correct_artifacts=0)", ", no artefact correction").replace("(exact, reference)", "(exact; plotted at 0.002)")
                ax.scatter(c, yy, s=30, marker="s", color="#555", zorder=3, label="Omniscape solver" if "Omniscape solver" not in seen else None)
                seen.add("Omniscape solver")
                ax.annotate(lab, (c, yy), textcoords="offset points", xytext=(0, 6), fontsize=6.5, ha="center")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("cost per landscape (s)\nsolver: one CPU core · learned: one GPU", fontsize=7.5)
        ax.set_ylabel("rel-L2 vs exact block-1 map", fontsize=7.5)
        ax.tick_params(labelsize=7)
        ax.set_ylim(1.5e-3, 0.4)
        ax.set_xlim(1e-3, 5e4)
        ax.grid(alpha=0.3, which="both", lw=0.5)
        ax.legend(frameon=False, fontsize=6.5, loc="lower left", ncol=1)
        _save(fig, "fig5_pareto_L")


def fig_scale_transfer_tex() -> None:
    """Figure 6: L-trained models at L, XL and XXL (test_id), zero-shot versus the scale-aware target."""
    rows = [r for r in _md_rows(ROOT / "paper" / "tables" / "scale_transfer.md") if r["split"] == "test_id"]
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.05), gridspec_kw=dict(wspace=0.28))
        for ax, task in zip(axes, ("T4", "T1"), strict=False):
            for base in MODEL_ORDER:
                lab = MODEL_LABEL[base]
                for variant, ls, mk in (("zero-shot", "-", "o"), ("scale-aware", "--", "^")):
                    g = [r for r in rows if r["task"] == task and r["model"] == lab and r["variant"] == variant]
                    if not g:
                        continue
                    g = sorted(g, key=lambda r: ["L", "XL", "XXL"].index(r["eval tier"]))
                    x = [["L", "XL", "XXL"].index(r["eval tier"]) for r in g]
                    ms = [_parse_ms(r["rel-L2"]) for r in g]
                    ax.errorbar(x, [m for m, _ in ms], yerr=[0 if np.isnan(s) else s for _, s in ms], ls=ls, marker=mk, ms=3.5, lw=1.1, capsize=2, color=MODEL_COLOR[base], mfc=MODEL_COLOR[base] if variant == "zero-shot" else "w", label=f"{lab} {variant}")
            ax.set_xticks([0, 1, 2])
            ax.set_xticklabels(["L (trained)\n512²", "XL\n1024²", "XXL\n2048²"])
            ax.set_yscale("log")
            ax.set_title({"T4": "T4 omnidirectional current", "T1": "T1 pairwise current"}[task])
            ax.grid(alpha=0.3, which="both", lw=0.5)
            if task == "T4":
                ax.axhline(0.5, color="#999", lw=0.7, ls=":")
                ax.axhline(0.75, color="#999", lw=0.7, ls=":")
                ax.text(0.02, 0.765, "1 − r$_L$/r$_{XXL}$ = 0.75", fontsize=6, color="#666", va="bottom")
                ax.text(0.02, 0.51, "1 − r$_L$/r$_{XL}$ = 0.50", fontsize=6, color="#666", va="bottom")
        axes[0].set_ylabel("relative L2 on test_id")
        h, l = axes[1].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.12))
        _save(fig, "fig6_scale_transfer")


def fig_ood_tex(tasks=("T1", "T4"), name="fig7_ood", stacked=True) -> None:
    """Figure 7: rel-L2 on each OOD split relative to test_id, per task, tier and model (stacked panels for the
    half-width main figure; the three-task row version is the appendix figure)."""
    rows = _md_rows(ROOT / "paper" / "tables" / "ood_degradation.md")
    if not rows:
        return
    inv = {v: k for k, v in MODEL_LABEL.items()}
    with plt.rc_context(PAPER_STYLE):
        if stacked:  # half-width main figure: the tasks side by side, compact
            fig, axes = plt.subplots(1, len(tasks), figsize=(3.4, 2.1), gridspec_kw=dict(wspace=0.08), sharey=True)
        else:
            fig, axes = plt.subplots(1, len(tasks), figsize=(7.0, 2.3), gridspec_kw=dict(wspace=0.08, width_ratios=[5, 2.4, 5][: len(tasks)]), sharey=True)
        axes = np.atleast_1d(axes)
        ratios = [("test_ood / id", "held-out table + contrast", "#d62728"), ("ood_region / id", "held-out region", "#1f77b4"), ("published / id", "published surfaces (S)", "#2ca02c")]
        for ax, task in zip(axes, tasks, strict=False):
            sub = [r for r in rows if r["task"] == task and r["model"] != "MgNO"]
            sub = sorted(sub, key=lambda r: (TIER_ORDER.index(r["tier"]), MODEL_ORDER.index(inv[r["model"]])))
            x = np.arange(len(sub))
            w = 0.27
            for k, (col, lab, color) in enumerate(ratios):
                vals = [float(r[col]) if r[col] not in ("–", "") else np.nan for r in sub]
                ax.bar(x + (k - 1) * w, vals, width=w, color=color, label=lab, lw=0)
            ax.axhline(1.0, color="k", lw=0.7, ls="--")
            ax.set_xticks(x)
            ax.set_xticklabels([r["model"] for r in sub], fontsize=5.5, rotation=60, ha="right")
            for tier in TIER_ORDER:
                idx = [k for k, r in enumerate(sub) if r["tier"] == tier]
                if idx:
                    ax.text(np.mean(idx), 1.56, tier, ha="center", va="top", fontsize=7, fontweight="bold")
                    if idx[0] > 0:
                        ax.axvline(idx[0] - 0.5, color="#bbb", lw=0.5)
            ax.set_title(task, pad=10, loc="left")
            ax.grid(alpha=0.3, axis="y", lw=0.5)
            ax.set_ylim(0.5, 1.6)
            if ax is axes[0]:
                ax.set_ylabel("rel-L2 ratio to test_id", fontsize=6.5)
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, frameon=False, loc="upper center", ncol=3 if not stacked else 1, bbox_to_anchor=(0.5, 1.06 if not stacked else 1.16), fontsize=6)
        _save(fig, name)


def figA_training_curves() -> None:
    """Appendix: training and validation loss per epoch for every official run, seeds overlaid."""
    import json as _json

    dec_f = ROOT / "docs" / "tables" / "tuning_decisions.json"
    decisions = _json.loads(dec_f.read_text()) if dec_f.exists() else {}
    runs = ROOT / "runs" / "full"
    if not runs.exists():
        return
    groups: dict[tuple, list[pathlib.Path]] = {}
    for d in sorted(runs.iterdir()):
        m = re.match(r"^(unet|fno|vit|gnn|mgno)_(T1|T3|T4)_(S|M|L)_s(\d)(_t2)?$", d.name)
        if not m or not (d / "log.csv").exists():
            continue
        base, task, tier, _seed, t2 = m.groups()
        official = decisions.get(f"{base}_{task}_{tier}", {}).get("official", "base")
        if (official == "t2") != bool(t2):
            continue
        groups.setdefault((task, tier, base), []).append(d)
    keys = sorted(groups, key=lambda k: (["T1", "T3", "T4"].index(k[0]), TIER_ORDER.index(k[1]), MODEL_ORDER.index(k[2])))
    if not keys:
        return
    ncol = 6
    nrow = int(np.ceil(len(keys) / ncol))
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(nrow, ncol, figsize=(7.0, 1.35 * nrow + 0.3), gridspec_kw=dict(wspace=0.35, hspace=0.6))
        axes = np.atleast_2d(axes).ravel()
        for ax, key in zip(axes, keys, strict=False):
            task, tier, base = key
            lo, hi = np.inf, 0.0
            for d in groups[key]:
                lg = pd.read_csv(d / "log.csv")
                ax.plot(lg.epoch, lg.val_loss, color=MODEL_COLOR[base], lw=0.9, alpha=0.9)
                ax.plot(lg.epoch, lg.train_loss, color=MODEL_COLOR[base], lw=0.7, ls=":", alpha=0.7)
                v = lg.val_loss[np.isfinite(lg.val_loss) & (lg.val_loss > 0)]
                if len(v):
                    lo, hi = min(lo, float(v.min())), max(hi, float(v.max()))
            ax.set_yscale("log")
            if np.isfinite(lo) and hi > 0:
                ax.set_ylim(lo * 0.5, hi * 1.5)
            ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(numticks=4))
            ax.set_title(f"{MODEL_LABEL[base]} {task} {tier} ({len(groups[key])} seed{'s' if len(groups[key]) > 1 else ''})", fontsize=6.5, pad=2)
            ax.tick_params(labelsize=5.5)
            ax.grid(alpha=0.25, which="both", lw=0.4)
        for ax in axes[len(keys):]:
            ax.axis("off")
        fig.text(0.5, 0.005, "epoch — solid: validation loss (masked MSE, log target); dotted: training loss", ha="center", fontsize=7)
        _save(fig, "figA_training_curves")


def figA_data_scaling() -> None:
    rows = _md_rows(ROOT / "paper" / "tables" / "wp4_data_scaling.md")
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, ax = plt.subplots(figsize=(3.4, 2.5))
        for base, ls in (("unet", "-"), ("fno", "--")):
            lab = MODEL_LABEL[base]
            for regime, mk, name in (("ep30", "o", "fixed epochs (30)"), ("steps", "s", "fixed steps")):
                g = [r for r in rows if r["model"] == lab and r["regime"] in (regime, "full")]
                g = sorted(g, key=lambda r: int(r["n train"].replace(",", "")))
                ax.plot([int(r["n train"].replace(",", "")) for r in g], [float(r["rel-L2"]) for r in g], marker=mk, ms=3.5, ls=ls, lw=1.1, color=MODEL_COLOR[base], mfc=MODEL_COLOR[base] if regime == "ep30" else "w", label=f"{lab}, {name}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("training landscapes (tier S, T1)")
        ax.set_ylabel("relative L2 on test_id")
        ax.grid(alpha=0.3, which="both", lw=0.5)
        ax.legend(frameon=False, fontsize=6)
        _save(fig, "figA_data_scaling")


def figA_fidelity() -> None:
    """Appendix: per-landscape deviation of the production T4 target from the exact block-1 map (reference subsets)."""
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.2), gridspec_kw=dict(wspace=0.32))
        for ax, tier in zip(axes[:2], ("M", "L"), strict=False):
            p = ROOT / "aux" / "t4_bs1_reference" / f"{tier}_bs1" / "index.parquet"
            if not p.exists():
                ax.axis("off")
                continue
            d = pd.read_parquet(p)
            bins = np.linspace(0, max(0.1, float(d.rel_l2.quantile(0.995))), 30)
            for fam, col in (("synthetic", "#ff7f0e"), ("real", "#1f77b4")):
                g = d[d.family == fam]
                ax.hist(g.rel_l2.clip(upper=bins[-1]), bins=bins, alpha=0.65, color=col, label=f"{fam} (n = {len(g)})")
            ax.axvline(d.rel_l2.mean(), color="k", lw=0.8, ls="--")
            ax.axvline(0.05, color="#d62728", lw=0.7, ls=":")
            ax.set_title(f"{tier}: block {int(d.prod_block.iloc[0])} vs block 1, n = {len(d)}")
            ax.set_xlabel("rel-L2 of the production target")
            ax.set_ylabel("landscapes")
            ax.legend(frameon=False, fontsize=6)
            ax.grid(alpha=0.3, lw=0.5)
        ax = axes[2]
        for tier, col in (("M", "#1f77b4"), ("L", "#d62728")):
            p = ROOT / "aux" / "t4_bs1_reference" / f"{tier}_bs1" / "index.parquet"
            if p.exists():
                d = pd.read_parquet(p)
                ax.scatter(d.prod_solve_s, d.aux_solve_s, s=6, alpha=0.5, color=col, label=f"{tier} (median ratio {float((d.aux_solve_s / d.prod_solve_s).median()):.1f}×)", lw=0)
        lim = [10, 3e4]
        ax.plot(lim, lim, "k--", lw=0.6)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("production solve (s)")
        ax.set_ylabel("block-1 solve (s)")
        ax.set_title("cost of the exact reference")
        ax.set_title("exact reference: cost", fontsize=8)
        ax.legend(frameon=False, fontsize=6)
        ax.grid(alpha=0.3, which="both", lw=0.5)
        _save(fig, "figA_fidelity")


def figA_precision() -> None:
    """Appendix: the post-run precision pass per tier (docs/tables/precision_pass.md)."""
    rows = [r for r in _md_rows(ROOT / "docs" / "tables" / "precision_pass.md") if r["tier"].strip("*") in TIER_ORDER]
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.2), gridspec_kw=dict(wspace=0.3))
        x = np.arange(len(rows))
        ax = axes[0]
        q = {k: [] for k in ("p50", "p90", "p99", "max")}
        for r in rows:
            vals = [float(v) for v in r["residual after: p50 / p90 / p99 / max"].split("/")]
            for k, v in zip(q, vals, strict=False):
                q[k].append(v)
        for k, mk in zip(q, ("o", "s", "^", "x"), strict=False):
            ax.plot(x, q[k], marker=mk, ms=4, lw=0.8, label=k)
        ax.axhline(1e-6, color="#d62728", lw=0.7, ls=":")
        ax.text(len(rows) - 0.9, 1.3e-6, "QC threshold", fontsize=6, color="#d62728")
        ax.axhline(1e-9, color="#999", lw=0.7, ls=":")
        ax.text(len(rows) - 0.9, 1.3e-9, "target", fontsize=6, color="#666")
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([r["tier"] for r in rows])
        ax.set_ylabel("relative Kirchhoff residual after the pass")
        ax.legend(frameon=False, fontsize=6, ncol=2)
        ax.grid(alpha=0.3, which="both", lw=0.5)
        ax = axes[1]
        n = [int(r["rows re-solved"].replace(",", "")) for r in rows]
        f = [int(r["rows > 1e-6 (flagged, excluded from splits)"].replace(",", "")) for r in rows]
        ax.bar(x - 0.2, n, width=0.4, color="#1f77b4", label="rows re-solved", lw=0)
        ax2 = ax.twinx()
        ax2.bar(x + 0.2, f, width=0.4, color="#d62728", label="rows flagged (> 1e-6)", lw=0)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([r["tier"] for r in rows])
        ax.set_ylabel("rows re-solved")
        ax2.set_ylabel("rows flagged", color="#d62728")
        ax2.spines["right"].set_visible(True)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=6, loc="lower left")
        ax.grid(alpha=0.3, axis="y", lw=0.5)
        _save(fig, "figA_precision")


def figA_wp7() -> None:
    src = ROOT / "aux" / "wp7" / "demo_results.parquet"
    if not src.exists():
        return
    d = pd.read_parquet(src)
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.2), gridspec_kw=dict(wspace=0.35))
        ax = axes[0]
        ax.scatter(d.stability_mean_iou_solver, d.stability_mean_iou_model, s=16, color="#1f77b4", lw=0)
        lim = [0, max(d.stability_mean_iou_solver.max(), d.stability_mean_iou_model.max()) * 1.05]
        ax.plot(lim, lim, "k--", lw=0.7)
        ax.set_xlabel("solver: mean pairwise top-5 % IoU across tables")
        ax.set_ylabel("surrogate")
        ax.set_title("stability of priority areas (per tile)")
        ax = axes[1]
        ax.hist(d.core75_iou_model_vs_solver, bins=10, color="#2ca02c", alpha=0.85)
        ax.set_xlabel("IoU of consensus cores, surrogate vs solver")
        ax.set_title(f"consensus core (median {d.core75_iou_model_vs_solver.median():.2f})")
        ax = axes[2]
        ax.scatter(d.pinch_persistent_recall, d.pinch_persistent_precision, s=16, color="#d62728", lw=0)
        ax.set_xlabel("persistent pinch-point recall")
        ax.set_ylabel("precision")
        ax.set_title("persistent pinch points (per tile)")
        for a in axes:
            a.grid(alpha=0.3, lw=0.5)
        _save(fig, "figA_wp7")


def tex_figures() -> None:
    """All figures of the LaTeX paper (paper/neurips/figures/)."""
    import shutil

    for fn in (fig_overview, fig_gallery, fig_qualitative, fig_error_vs_tier_tex, fig_pareto_L_tex, fig_scale_transfer_tex,
               fig_ood_tex, lambda: fig_ood_tex(("T1", "T3", "T4"), "figA_ood_all", stacked=False),
               figA_training_curves, figA_data_scaling, figA_fidelity, figA_precision, figA_wp7):
        try:
            fn()
        except Exception as e:  # noqa: BLE001 — one broken panel must not stop the rest
            log(f"paper figure {getattr(fn, '__name__', 'lambda')} FAILED: {e!r}")
    for name in ("contrast", "biome_realm", "nodata", "solve_times", "storage"):
        src = ROOT / "docs" / "figures" / f"dataset_stats_{name}.png"
        if src.exists():
            TEX_FIG.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, TEX_FIG / f"figA_stats_{name}.png")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default="paper")
    ap.add_argument(
        "--skip-stats", action="store_true", help="skip F1 (reads the full indexes; slow)"
    )
    ap.add_argument("--tex", action="store_true", help="also draw the LaTeX paper's figures into paper/neurips/figures/")
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
    wp4_data_scaling(out)
    ood_degradation(out)
    baselines_all_splits(out)
    if a.tex:
        tex_figures()
    log("done")


if __name__ == "__main__":
    main()
