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
import matplotlib.lines  # noqa: E402
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
HEUR = ROOT / "aux" / "review_round3" / "heuristic" / "heuristic.parquet"


def t4_pareto(out: pathlib.Path) -> None:
    for tier in ("M", "L"):
        ref = ROOT / "aux" / "t4_bs1_reference" / f"{tier}_bs1"
        blocks = sorted(b for b in glob.glob(str(ROOT / "aux" / "t4_blocksize_baselines" / f"{tier}_*")) if not b.endswith("_topup"))  # top-up builds are merged into their parent (2026-10-22)
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
                *(["--heuristic", str(HEUR)] if HEUR.exists() else []),
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


def full_precision(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Replace the 3-decimal per-seed metrics read from docs/tables/baselines_full.md by the full-precision values in
    each run's results.json (`eval[<root>_<tier>_<split>][<task>][<metric>]`); averaging rounded seeds shifted two
    Table 2 cells by 0.001 (review round 3, 2026-10-20). Rows without a results file keep their table value."""
    df = df.copy()
    for i, r in df.iterrows():
        rj = ROOT / "runs" / "full" / str(r["model"]) / "results.json"
        if not rj.exists():
            continue
        ev = json.loads(rj.read_text()).get("eval", {})
        split = str(r["split"]).replace("published S", "test_ood_published")
        tag = next((k for k in ev if k.endswith(f"_{r['tier']}_{split}")), None)
        vals = ev.get(tag, {}).get(r["task"], {}) if tag else {}
        for m in metrics:
            key = {"corridor_dice": "corridor_dice_q10"}.get(m, m)
            if m in df.columns and isinstance(vals.get(key), (int, float)):
                df.at[i, m] = float(vals[key])
    return df


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
    learned = prefer_tuned(df[df.seed.notna() & (df.suffix == "") & df.tier.isin(["S", "M", "L"])])  # in-tier training runs only (the XL-trained U-Net is quoted from baselines_full.md)
    metrics = ["rel_l2", "mae_log10eps", "top5_iou", "pinch_recall", "spearman"]
    learned = full_precision(learned, metrics)
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
    df = prefer_tuned(df[df.seed.notna() & (df.suffix == "") & df.tier.isin(["S", "M", "L"])].copy())  # in-tier training runs only
    df["split"] = df.split.replace({"published S": "published"})
    splits = ["test_id", "test_ood", "ood_region", "published"]
    df = df[df.split.isin(splits)]
    df = full_precision(df.assign(split=df.split.replace({"published": "published S"})), ["rel_l2", "spearman", "top5_iou", "pinch_recall"]).assign(split=df.split)
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
    # official configuration only (the tier-tuned run where it is official; before 2026-10-20 both were pooled)
    learned = prefer_tuned(df[df.seed.notna() & (df.suffix == "")])
    metrics = [
        "rel_l2",
        "mae_log10eps",
        "top5_iou",
        "pinch_recall",
        "spearman",
        "corridor_dice",
        "ssim",
    ]
    learned = full_precision(learned, metrics)
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
FULLW = 5.5  # NeurIPS text width in inches: full-width figures are drawn at this width so fonts print at their size
HALFW = 2.64  # 0.48 * text width (two figures side by side)
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


def _log_ticks(ax, subs=(1.0, 2.0, 3.0, 5.0)):
    """Plain decimal labels on a log axis that spans less than two decades (no '6 × 10^-1' labels)."""
    ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=subs, numticks=12))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())


def _npz(name: str) -> dict | None:
    p = FIGDATA / f"{name}.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _short(name: str) -> str:
    return str(name).replace("_", " ").replace("nan", "")


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
        W, H = FULLW, 2.15
        fig = plt.figure(figsize=(W, H))
        side = 0.74 / W  # panel width in figure fraction (0.74 in)
        ph = 0.74 / H
        y0 = 1.0 - 0.085 - ph  # top row of panels
        gap = 0.08 / W  # between panels of one group
        agap = 0.2 / W  # where an arrow sits
        box_w = 1.05 / W
        x_start = 0.01
        c0 = x_start
        c1 = c0 + side + agap
        c2 = c1 + side + agap
        c3 = c2 + box_w + agap
        cols = [c0, c1, c2, c3, c3 + side + gap, c3 + 2 * (side + gap)]

        def panel(x, y, img, cmap, title, w=side, h=ph):
            ax = fig.add_axes([x, y, w, h])
            _imshow(ax, img, cmap)
            ax.set_title(title, fontsize=7, pad=2)
            return ax

        if cov is not None and len(cov) >= 2:
            hh = ph / 2 - 0.04  # two half-height panels with room for the lower one's title
            panel(cols[0], y0 + ph - hh, cov[0], "Greens", (names[0] if names else "covariate 1")[:14], h=hh)
            panel(cols[0], y0, cov[min(1, len(cov) - 1)], "terrain", (names[1] if len(names) > 1 else "covariate 2")[:14], h=hh)
            fig.text(cols[0] + side / 2, y0 - 0.04, "covariate layers", ha="center", fontsize=7)
        else:
            ax = fig.add_axes([cols[0], y0, side, ph]); ax.axis("off")
            ax.text(0.5, 0.5, "synthetic\ngenerator", ha="center", va="center", fontsize=7.5)
        panel(cols[1], y0, np.where(nd, np.nan, np.log10(d["points__resistance"])), "viridis", "resistance $\\log_{10} R$")
        fig.text(cols[1] + side / 2, y0 - 0.04, "resistance table", ha="center", fontsize=7)
        ax = fig.add_axes([cols[2], y0, box_w, ph]); ax.axis("off")
        ax.text(0.5, 0.5, "reference solvers\nCircuitscape.jl 5.17.1\nOmniscape.jl 0.6.2\nCHOLMOD, float64\nresidual per row", ha="center", va="center", fontsize=6.8,
                bbox=dict(boxstyle="round,pad=0.4", fc="#f4f4f4", ec="#888", lw=0.8))
        ax = panel(cols[3], y0, _log_current(d["points__out_cum_current"], nd), "magma", "T1 pairwise")
        focal = d.get("points__in_focal_mask")
        if focal is not None:
            yy, xx = np.nonzero(focal > 0)
            ax.scatter(xx, yy, s=6, c="cyan", marker="s", linewidths=0)
        if "advanced__out_current" in d:
            panel(cols[4], y0, _log_current(d["advanced__out_current"], nd), "magma", "T3 advanced")
        panel(cols[5], y0, _log_current(d["omniscape__out_cum_current"], nd), "magma", "T4 omnidirectional")
        fig.text((cols[3] + cols[5] + side) / 2, y0 - 0.04, "exact targets (float32 maps, float64 effective resistances)", ha="center", fontsize=7)
        ym = y0 + ph / 2
        ins = 0.03 / W  # arrows start and end clear of the panel edges
        for x0, x1 in ((cols[0] + side + ins, cols[1] - ins), (cols[1] + side + ins, cols[2] - ins), (cols[2] + box_w + ins, cols[3] - ins)):
            fig.patches.append(matplotlib.patches.FancyArrowPatch((x0, ym), (x1, ym), transform=fig.transFigure, arrowstyle="-|>", mutation_scale=7, color="#444", lw=0.9, shrinkA=0, shrinkB=0))
        yb, hb = 0.0, y0 - 0.12
        for x0, w, txt in ((0.01, 0.32, "Tiers\nS 128$^2$ at 100 m · M 256$^2$ at 100 m\nL 512$^2$ at 200 m · XL 1024$^2$ at 500 m\nXXL 2048$^2$ at 1 km\n174,400 landscapes · 920,372 rows\n1,157 GB on the Hub"),
                           (0.35, 0.33, "Tasks\nT1 pairwise current map\nT2 effective resistances\nT1W wall-to-wall strips · T1R regions\nT3 advanced mode (sources → grounds)\nT4 Omniscape omnidirectional current"),
                           (0.70, 0.30, "Splits and metrics\nsplit by macro-cell and seed family\nOOD: region · table · contrast ·\nscale (XL, XXL) · published surfaces\nmetrics: pixel · ranking ·\nnon-source · physics · speed-up")):
            ax = fig.add_axes([x0, yb, w, hb]); ax.axis("off")
            head, body = txt.split("\n", 1)
            ax.text(0.0, 1.0, head, ha="left", va="top", fontsize=8, fontweight="bold")
            ax.text(0.0, 0.8, body, ha="left", va="top", fontsize=6.8, linespacing=1.3)
        _save(fig, "fig1_overview")


def fig_gallery() -> None:
    """Figure 2: synthetic and real landscapes with their T1 and T4 targets at every tier (columns = tiers)."""
    import json as _json

    man = _json.loads((FIGDATA / "manifest.json").read_text()) if (FIGDATA / "manifest.json").exists() else {}
    tiers = [t for t in TIER_ORDER if (FIGDATA / f"gallery_{t}_synthetic.npz").exists() and (FIGDATA / f"gallery_{t}_real.npz").exists()]
    if not tiers:
        log("paper fig2: figdata missing — skipped")
        return
    n = len(tiers)
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(3, 2 * n + 1, figsize=(FULLW, 1.85), gridspec_kw=dict(wspace=0.1, hspace=0.06, width_ratios=[1] * n + [0.3] + [1] * n))
        for ax in axes[:, n]:
            ax.axis("off")
        rows = (("$\\log_{10} R$", "viridis"), ("T1\ncurrent", "magma"), ("T4\ncurrent", "magma"))
        for j, fam in enumerate(("synthetic", "real")):
            for i, tier in enumerate(tiers):
                c = i + j * (n + 1)
                d = _npz(f"gallery_{tier}_{fam}")
                nd = d["points__nodata"].astype(bool)
                _imshow(axes[0, c], np.where(nd, np.nan, np.log10(d["points__resistance"])), "viridis")
                _imshow(axes[1, c], _log_current(d["points__out_cum_current"], nd), "magma")
                _imshow(axes[2, c], _log_current(d["omniscape__out_cum_current"], nd), "magma")
                m = man.get(f"gallery_{tier}_{fam}", {})
                lab = _short(m.get("generator", "") if fam == "synthetic" else m.get("table", ""))
                axes[0, c].set_title(f"{tier}\n{d['points__resistance'].shape[0]}$^2$", fontsize=6.5, pad=2, linespacing=1.0)
            x_mid = (axes[0, j * (n + 1)].get_position().x0 + axes[0, j * (n + 1) + n - 1].get_position().x1) / 2
            fig.text(x_mid, 1.0, f"{fam} landscapes", ha="center", va="bottom", fontsize=8, fontweight="bold")
        for i, (lab, _) in enumerate(rows):
            axes[i, 0].set_ylabel(lab, fontsize=6.5, labelpad=2)
        _save(fig, "fig2_gallery")


def fig_qualitative() -> None:
    """Figure 3: input, exact target, best-model prediction and error map for T1 and T4 at L, in-distribution and OOD
    side by side (one row per task, a shared error colour scale per row)."""
    import json as _json

    man = _json.loads((FIGDATA / "manifest.json").read_text()) if (FIGDATA / "manifest.json").exists() else {}
    cases = [c for c in ("id", "ood") if (FIGDATA / f"qual_L_{c}.npz").exists()]
    if not cases:
        log("paper fig3: figdata missing — skipped")
        return
    nc = len(cases)
    with plt.rc_context(PAPER_STYLE):
        ratios = ([1, 1, 1, 1] + [0.18]) * nc
        ratios = ratios[:-1] + [0.08]  # last column: colour bar
        fig, axes = plt.subplots(2, len(ratios), figsize=(FULLW, 1.75), gridspec_kw=dict(wspace=0.06, hspace=0.08, width_ratios=ratios))
        for i, task in enumerate(("T1", "T4")):
            cfg = "points" if task == "T1" else "omniscape"
            data = {c: _npz(f"qual_L_{c}") for c in cases}
            lims = []
            for c in cases:
                d = data[c]
                nd = d[f"{cfg}__nodata"].astype(bool)
                err = _log_current(d[f"{cfg}__pred_cum_current"], nd) - _log_current(d[f"{cfg}__out_cum_current"], nd)
                lims.append(np.nanpercentile(np.abs(err), 99))
            lim = max(lims)
            im = None
            for k, c in enumerate(cases):
                d = data[c]
                nd = d[f"{cfg}__nodata"].astype(bool)
                tgt = _log_current(d[f"{cfg}__out_cum_current"], nd)
                prd = _log_current(d[f"{cfg}__pred_cum_current"], nd)
                vmin, vmax = np.nanpercentile(tgt, 1), np.nanmax(tgt)
                c0 = k * 5
                _imshow(axes[i, c0], np.where(nd, np.nan, np.log10(d[f"{cfg}__resistance"])), "viridis")
                if task == "T1" and f"{cfg}__in_focal_mask" in d:
                    yy, xx = np.nonzero(d[f"{cfg}__in_focal_mask"] > 0)
                    axes[i, c0].scatter(xx, yy, s=7, c="cyan", marker="s", linewidths=0)
                _imshow(axes[i, c0 + 1], tgt, "magma", vmin, vmax)
                _imshow(axes[i, c0 + 2], prd, "magma", vmin, vmax)
                im = _imshow(axes[i, c0 + 3], prd - tgt, "RdBu_r", -lim, lim)
                if k < nc - 1:
                    axes[i, c0 + 4].axis("off")
            cb = fig.colorbar(im, cax=axes[i, -1])
            cb.ax.tick_params(labelsize=5.5, pad=1)
            cb.set_label("error (log$_{10}$)", fontsize=6)
            run = (man.get("qual_L_id", {}).get("runs") or {}).get(task, "")
            model = MODEL_LABEL.get(run.split("_")[0], run.split("_")[0]) if run else ""
            axes[i, 0].set_ylabel(f"{task} · {model}", fontsize=7)
        titles = ("input", "target", "prediction", "error")
        for k, c in enumerate(cases):
            for j, t in enumerate(titles):
                axes[0, k * 5 + j].set_title(t, pad=2, fontsize=6.5)
            m = man.get(f"qual_L_{c}", {})
            head = "in-distribution (test_id)" if c == "id" else f"OOD: held-out {_short(m.get('table', ''))} table (test_ood)"
            x_mid = (axes[0, k * 5].get_position().x0 + axes[0, k * 5 + 3].get_position().x1) / 2
            fig.text(x_mid, 1.0, head, ha="center", va="bottom", fontsize=7.5, fontweight="bold")
        _save(fig, "fig3_qualitative")


def fig_error_vs_tier_tex() -> None:
    """Figure 4: rel-L2 on test_id versus tier per task and model (mean ± std over seeds)."""
    rows = _md_rows(ROOT / "paper" / "tables" / "baselines_sml.md")
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        tasks = ["T1", "T3", "T4"]
        fig, axes = plt.subplots(1, 3, figsize=(FULLW, 1.65), gridspec_kw=dict(wspace=0.35))
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
                ax.errorbar(x, y, yerr=e, marker="o", ms=3.5, capsize=2, lw=1.2, color=MODEL_COLOR[base], label=lab)
            ax.set_xticks([0, 1, 2])
            ax.set_xticklabels(["S\n128²", "M\n256²", "L\n512²"])
            ax.set_yscale("log")
            _log_ticks(ax)
            ax.set_title(task + {"T1": " pairwise current", "T3": " advanced mode", "T4": " omnidirectional"}[task])
            ax.grid(alpha=0.3, which="both", lw=0.5)
            if ax is axes[0]:
                ax.set_ylabel("relative L2 on test_id")
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, frameon=False, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.1), columnspacing=1.2)
        _save(fig, "fig4_error_vs_tier")


def fig_pareto_L_tex() -> None:
    """Figure 5 (half width): T4 error against the exact block-1 map versus cost per landscape at L."""
    rows = [r for r in _md_rows(ROOT / "paper" / "tables" / "t4_pareto_L.md") if r["split"] == "test_id"]
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, ax = plt.subplots(figsize=(HALFW, 2.35))
        seen = set()
        solver_pts = []
        for r in rows:
            cost = r["cost s / landscape"].replace("–", "")
            if not cost:
                continue
            c, y = float(cost), float(r["rel_l2"])
            m = r["method"]
            if "no solver" in m:  # review round 3: solver-free radius-law baseline (plot the fitted variant only)
                if "conductance" in m:
                    ax.scatter(c, y, s=30, marker="D", color="#8c564b", zorder=3, label="radius-law heuristic (CPU)")
                    ax.annotate("radius law", (c, y), textcoords="offset points", xytext=(0, 5), ha="center", va="bottom", fontsize=6, color="#8c564b")
                continue
            if "learned" in m:
                base = m.split("_")[0]
                sa = "scalenorm" in m
                lab = MODEL_LABEL.get(base, base)
                ax.scatter(c, y, s=30, marker="^" if sa else "o", facecolor="w" if sa else MODEL_COLOR.get(base, "k"),
                           edgecolor=MODEL_COLOR.get(base, "k"), lw=1.0, zorder=3, label=lab if (lab not in seen and not sa) else None)
                if not sa:
                    seen.add(lab)
            else:
                yy = max(y, 2e-3)
                blk = re.search(r"block (\d+)", m)
                lab = f"block {blk.group(1)}" if blk else m
                if "exact" in m:
                    lab = "block 1, exact\n(plotted at 0.002)"
                elif "production" in m:
                    lab += " (production)"
                elif "correct_artifacts=0" in m:
                    lab += ", no corr."
                solver_pts.append((c, yy, lab))
                ax.scatter(c, yy, s=26, marker="s", color="#555", zorder=3, label="Omniscape solver" if "Omniscape solver" not in seen else None)
                seen.add("Omniscape solver")
        for c, yy, lab in solver_pts:
            if "exact" in lab:
                kw = dict(xytext=(0, 5), ha="center", va="bottom")
            elif lab == "block 3":
                kw = dict(xytext=(0, -5), ha="center", va="top")
            elif "no corr" in lab:
                kw = dict(xytext=(0, 5), ha="center", va="bottom")
            else:
                kw = dict(xytext=(-5, 0), ha="right", va="center")
            ax.annotate(lab, (c, yy), textcoords="offset points", fontsize=6, color="#333", **kw)
        ax.scatter([], [], marker="^", facecolor="w", edgecolor="k", s=30, lw=1.0, label="open: scale-aware target")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("cost per landscape (s): solver one CPU core, learned one GPU", fontsize=7)
        ax.set_ylabel("rel-L2 vs exact block-1 map", fontsize=7.5)
        ax.tick_params(labelsize=7)
        ax.set_ylim(1.2e-3, 0.5)
        ax.set_xlim(1e-3, 8e4)
        ax.grid(alpha=0.3, which="both", lw=0.5)
        ax.legend(frameon=False, fontsize=6.3, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, handletextpad=0.3, columnspacing=1.0)
        _save(fig, "fig5_pareto_L")


def fig_scale_transfer_tex() -> None:
    """Figure 6: L-trained models at L, XL and XXL (test_id), zero-shot versus the scale-aware target."""
    rows = [r for r in _md_rows(ROOT / "paper" / "tables" / "scale_transfer.md") if r["split"] == "test_id"]
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(FULLW, 1.85), gridspec_kw=dict(wspace=0.3))
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
            _log_ticks(ax, subs=(1.0, 2.0, 3.0, 5.0) if task == "T4" else (1.0, 2.0, 5.0))
            ax.set_title({"T4": "T4 omnidirectional current", "T1": "T1 pairwise current"}[task])
            ax.grid(alpha=0.3, which="both", lw=0.5)
            if task == "T4":
                ax.axhline(0.5, color="#999", lw=0.7, ls=":")
                ax.axhline(0.75, color="#999", lw=0.7, ls=":")
                ax.text(0.08, 0.77, "1 − r$_L$/r$_{XXL}$ = 0.75", fontsize=6.5, color="#666", va="bottom")
                ax.text(0.08, 0.515, "1 − r$_L$/r$_{XL}$ = 0.50", fontsize=6.5, color="#666", va="bottom")
        axes[0].set_ylabel("relative L2 on test_id")
        h, l = axes[1].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.16), columnspacing=1.0, handlelength=1.6)
        _save(fig, "fig6_scale_transfer")


def _ood_panel(ax, sub, ratios, tier_y=1.5):
    x = np.arange(len(sub))
    w = 0.27
    for k, (col, lab, color) in enumerate(ratios):
        vals = [float(r[col]) if r[col] not in ("–", "") else np.nan for r in sub]
        ax.bar(x + (k - 1) * w, vals, width=w, color=color, label=lab, lw=0)
    ax.axhline(1.0, color="k", lw=0.7, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels([r["model"] for r in sub], fontsize=6.5, rotation=60, ha="right", rotation_mode="anchor")
    for tier in TIER_ORDER:
        idx = [k for k, r in enumerate(sub) if r["tier"] == tier]
        if idx:
            ax.text(np.mean(idx), tier_y, tier, ha="center", va="center", fontsize=7.5, fontweight="bold", color="#333")
            if idx[0] > 0:
                ax.axvline(idx[0] - 0.5, color="#bbb", lw=0.5)
    ax.grid(alpha=0.3, axis="y", lw=0.5)
    ax.set_ylim(0.5, 1.6)
    ax.set_xlim(-0.6, len(sub) - 0.4)


def fig_ood_tex(tasks=("T1", "T4"), name="fig7_ood", stacked=True) -> None:
    """Figure 7: rel-L2 on each OOD split relative to test_id, per task, tier and model. stacked=True draws the
    half-width main figure (one panel per task, one above the other); stacked=False the full-width appendix row."""
    rows = _md_rows(ROOT / "paper" / "tables" / "ood_degradation.md")
    if not rows:
        return
    inv = {v: k for k, v in MODEL_LABEL.items()}
    ratios = [("test_ood / id", "held-out table + contrast", "#d62728"), ("ood_region / id", "held-out region", "#1f77b4"), ("published / id", "published surfaces (S)", "#2ca02c")]
    subs = {}
    for task in tasks:
        sub = [r for r in rows if r["task"] == task and r["model"] != "MgNO"]
        subs[task] = sorted(sub, key=lambda r: (TIER_ORDER.index(r["tier"]), MODEL_ORDER.index(inv[r["model"]])))
    with plt.rc_context(PAPER_STYLE):
        if stacked:
            fig, axes = plt.subplots(len(tasks), 1, figsize=(HALFW, 1.15 * len(tasks) + 0.45), gridspec_kw=dict(hspace=0.12), sharex=True)
            axes = np.atleast_1d(axes)
            for ax, task in zip(axes, tasks, strict=False):
                _ood_panel(ax, subs[task], ratios)
                ax.set_ylabel(f"{task}: ratio to test_id", fontsize=7)
            for ax in axes[:-1]:
                ax.tick_params(axis="x", length=0)
            h, l = axes[0].get_legend_handles_labels()
            fig.legend(h, l, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.55, 1.07), fontsize=6.5, columnspacing=0.8, handlelength=1.2)
        else:
            widths = [max(len(subs[t]), 1) for t in tasks]
            fig, axes = plt.subplots(1, len(tasks), figsize=(FULLW, 2.3), gridspec_kw=dict(wspace=0.08, width_ratios=widths), sharey=True)
            axes = np.atleast_1d(axes)
            for ax, task in zip(axes, tasks, strict=False):
                _ood_panel(ax, subs[task], ratios)
                ax.set_title(task, loc="left", fontsize=8.5)
            axes[0].set_ylabel("rel-L2 ratio to test_id")
            h, l = axes[0].get_legend_handles_labels()
            fig.legend(h, l, frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.07))
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
        fig, axes = plt.subplots(nrow, ncol, figsize=(FULLW, 1.05 * nrow + 0.35), gridspec_kw=dict(wspace=0.45, hspace=0.7))
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
                ax.set_ylim(lo * 0.5, min(hi * 1.5, 10.0))  # exploded MgNO seeds leave the frame instead of flattening the others
            ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(numticks=4))
            seeds = len(groups[key])
            ax.set_title(f"{MODEL_LABEL[base]} · {task} · {tier}", fontsize=6.8, pad=2)
            ax.tick_params(labelsize=5.8, pad=1.5)
            ax.grid(alpha=0.25, which="both", lw=0.4)
        for ax in axes[len(keys):]:
            ax.axis("off")
        fig.text(0.5, 0.0, "epoch — solid: validation loss (masked MSE, log target); dotted: training loss; one line per seed (MgNO: diverged seeds included)", ha="center", va="bottom", fontsize=7)
        _save(fig, "figA_training_curves")


def figA_data_scaling() -> None:
    rows = _md_rows(ROOT / "paper" / "tables" / "wp4_data_scaling.md")
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, ax = plt.subplots(figsize=(3.4, 2.1))
        for base, ls in (("unet", "-"), ("fno", "--")):
            lab = MODEL_LABEL[base]
            for regime, mk, name in (("ep30", "o", "fixed epochs (30)"), ("steps", "s", "fixed steps")):
                g = [r for r in rows if r["model"] == lab and r["regime"] in (regime, "full")]
                g = sorted(g, key=lambda r: int(r["n train"].replace(",", "")))
                ax.plot([int(r["n train"].replace(",", "")) for r in g], [float(r["rel-L2"]) for r in g], marker=mk, ms=3.5, ls=ls, lw=1.1, color=MODEL_COLOR[base], mfc=MODEL_COLOR[base] if regime == "ep30" else "w", label=f"{lab}, {name}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        _log_ticks(ax)
        ax.set_xlabel("training landscapes (tier S, T1)")
        ax.set_ylabel("relative L2 on test_id")
        ax.grid(alpha=0.3, which="both", lw=0.5)
        ax.legend(frameon=False, fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, columnspacing=1.0)
        _save(fig, "figA_data_scaling")


def figA_fidelity() -> None:
    """Appendix: per-landscape deviation of the production T4 target from the exact block-1 map (reference subsets)."""
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(FULLW, 2.05), gridspec_kw=dict(wspace=0.4))
        for ax, tier in zip(axes[:2], ("M", "L"), strict=False):
            p = ROOT / "aux" / "t4_bs1_reference" / f"{tier}_bs1" / "index.parquet"
            if not p.exists():
                ax.axis("off")
                continue
            d = pd.read_parquet(p)
            bins = np.linspace(0, max(0.1, float(d.rel_l2.quantile(0.995))), 30)
            for fam, col in (("synthetic", "#ff7f0e"), ("real", "#1f77b4")):
                g = d[d.family == fam]
                ax.hist(g.rel_l2.clip(upper=bins[-1]), bins=bins, alpha=0.65, color=col, label=f"{fam} ({len(g)})")
            ax.axvline(d.rel_l2.mean(), color="k", lw=0.8, ls="--")
            ax.axvline(0.05, color="#d62728", lw=0.7, ls=":")
            ax.set_title(f"{tier}: block {int(d.prod_block.iloc[0])} vs 1 (n = {len(d)})", fontsize=8, pad=15)
            ax.set_xlabel("rel-L2, production vs exact")
            ax.set_ylabel("landscapes")
            ax.legend(frameon=False, fontsize=6, loc="lower center", bbox_to_anchor=(0.5, 0.99), ncol=2, columnspacing=0.6, handlelength=1.0, handletextpad=0.4, borderaxespad=0.0)
            ax.grid(alpha=0.3, lw=0.5)
        ax = axes[2]
        for tier, col in (("M", "#1f77b4"), ("L", "#d62728")):
            p = ROOT / "aux" / "t4_bs1_reference" / f"{tier}_bs1" / "index.parquet"
            if p.exists():
                d = pd.read_parquet(p)
                ax.scatter(d.prod_solve_s, d.aux_solve_s, s=6, alpha=0.5, color=col, label=f"{tier}: {float((d.aux_solve_s / d.prod_solve_s).median()):.1f}× median", lw=0)
        lim = [10, 3e4]
        ax.plot(lim, lim, "k--", lw=0.6)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("production solve (s)")
        ax.set_ylabel("block-1 solve (s)")
        ax.set_title("exact reference: cost", fontsize=8, pad=15)
        ax.legend(frameon=False, fontsize=6, loc="lower center", bbox_to_anchor=(0.5, 0.99), ncol=2, handlelength=1.0, columnspacing=0.6, handletextpad=0.4, borderaxespad=0.0, markerscale=1.5)
        ax.grid(alpha=0.3, which="both", lw=0.5)
        _save(fig, "figA_fidelity")


def figA_precision() -> None:
    """Appendix: the post-run precision pass per tier (docs/tables/precision_pass.md)."""
    rows = [r for r in _md_rows(ROOT / "docs" / "tables" / "precision_pass.md") if r["tier"].strip("*") in TIER_ORDER]
    if not rows:
        return
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(FULLW, 2.0), gridspec_kw=dict(wspace=0.4))
        x = np.arange(len(rows))
        ax = axes[0]
        q = {k: [] for k in ("p50", "p90", "p99", "max")}
        for r in rows:
            vals = [float(v) for v in r["residual after: p50 / p90 / p99 / max"].split("/")]
            for k, v in zip(q, vals, strict=False):
                q[k].append(v)
        for k, mk in zip(q, ("o", "s", "^", "x"), strict=False):
            ax.plot(x, q[k], marker=mk, ms=4, lw=0.8, label=k)
        ax.axhline(1e-6, color="#d62728", lw=0.8, ls=":", label="QC threshold $10^{-6}$")
        ax.axhline(1e-9, color="#777", lw=0.8, ls=":", label="target $10^{-9}$")
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([r["tier"].strip("*") for r in rows])
        ax.set_ylabel("relative Kirchhoff residual after the pass")
        ax.legend(frameon=False, fontsize=6.5, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), columnspacing=1.0, handlelength=1.6)
        ax.grid(alpha=0.3, which="both", lw=0.5)
        ax = axes[1]
        n = [int(r["rows re-solved"].replace(",", "").replace("*", "")) for r in rows]
        f = [int(r["rows > 1e-6 (flagged, excluded from splits)"].replace(",", "").replace("*", "")) for r in rows]
        ax.bar(x - 0.2, n, width=0.4, color="#1f77b4", label="rows re-solved (left axis)", lw=0)
        ax2 = ax.twinx()
        ax2.bar(x + 0.2, f, width=0.4, color="#d62728", label="rows flagged > 10$^{-6}$ (right axis)", lw=0)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([r["tier"].strip("*") for r in rows])
        ax.set_ylabel("rows re-solved")
        ax2.set_ylabel("rows flagged", color="#d62728")
        ax2.spines["right"].set_visible(True)
        ax2.set_ylim(0, max(f) * 1.6)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=6.5, ncol=1, loc="lower center", bbox_to_anchor=(0.5, 1.0))
        ax.grid(alpha=0.3, axis="y", lw=0.5)
        _save(fig, "figA_precision")


def figA_wp7() -> None:
    src = ROOT / "aux" / "wp7" / "demo_results.parquet"
    if not src.exists():
        return
    d = pd.read_parquet(src)
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(FULLW, 2.0), gridspec_kw=dict(wspace=0.45))
        ax = axes[0]
        ax.scatter(d.stability_mean_iou_solver, d.stability_mean_iou_model, s=16, color="#1f77b4", lw=0)
        lim = [0, max(d.stability_mean_iou_solver.max(), d.stability_mean_iou_model.max()) * 1.05]
        ax.plot(lim, lim, "k--", lw=0.7)
        ax.set_xlabel("solver route: mean pairwise\ntop-5 % IoU across tables")
        ax.set_ylabel("surrogate route")
        ax.set_title("stability of\npriority areas", fontsize=8)
        ax = axes[1]
        ax.hist(d.core75_iou_model_vs_solver, bins=10, color="#2ca02c", alpha=0.85)
        ax.set_xlabel("IoU of consensus cores,\nsurrogate vs solver")
        ax.set_ylabel("tiles")
        ax.set_title(f"consensus core\n(median IoU {d.core75_iou_model_vs_solver.median():.2f})", fontsize=8)
        ax = axes[2]
        ax.scatter(d.pinch_persistent_recall, d.pinch_persistent_precision, s=16, color="#d62728", lw=0)
        ax.set_xlabel("persistent pinch-point recall")
        ax.set_ylabel("precision")
        ax.set_title("persistent\npinch points", fontsize=8)
        for a in axes:
            a.grid(alpha=0.3, lw=0.5)
        _save(fig, "figA_wp7")


def figA_stats() -> None:
    """Appendix: dataset statistics in the paper style (the Markdown versions are docs/figures/dataset_stats_*.png):
    contrast and NoData per tier and family, biome and realm coverage, solve time per configuration, storage."""
    idx_dir = ROOT / "data" / "hf" / "AmpScape" / "index"
    tiles_f = ROOT / "data" / "tiles" / "v1.0" / "tiles.parquet"
    counts_f = ROOT / "docs" / "tables" / "final_counts.json"
    if not (idx_dir.exists() and tiles_f.exists() and counts_f.exists()):
        log("paper figA_stats: index / tiles / counts missing — skipped")
        return
    cols = ["sample_id", "config", "family", "contrast", "tile_id", "realm", "solve_time_s"]
    idx = pd.concat([pd.read_parquet(idx_dir / f"{t}.parquet", columns=cols).assign(tier=t) for t in TIER_ORDER], ignore_index=True)
    samples = idx.drop_duplicates("sample_id")
    tiles = pd.read_parquet(tiles_f, columns=["tile_id", "biome_name", "qc_frac_unusable"])
    counts = json.loads(counts_f.read_text())
    tier_color = dict(zip(TIER_ORDER, ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"], strict=False))
    with plt.rc_context(PAPER_STYLE):
        # (a) contrast per tier and family, NoData fraction
        fig, axes = plt.subplots(1, 3, figsize=(FULLW, 1.9), gridspec_kw=dict(wspace=0.45))
        for fam, ax in (("synthetic", axes[0]), ("real", axes[1])):
            sub = samples[samples.family == fam]
            for t in TIER_ORDER:
                c = sub[sub.tier == t].contrast.dropna()
                if len(c):
                    ax.hist(np.log10(c), bins=40, histtype="step", lw=1.0, color=tier_color[t], label=f"{t} (n = {len(c):,})")
            ax.set_xlabel("log$_{10}$ contrast")
            ax.set_ylabel("landscapes")
            ax.set_title(f"{fam} landscapes")
            if fam == "synthetic":
                ax.set_xlim(0.5, 6.5)
                h_t, l_t = ax.get_legend_handles_labels()
                fig.legend(h_t, [l.split(" (")[0] for l in l_t], frameon=False, fontsize=6.5, ncol=5, loc="upper center", bbox_to_anchor=(0.36, 1.24), title="tier", title_fontsize=6.5, columnspacing=1.0)
            ax.grid(alpha=0.3, lw=0.5)
        ax = axes[2]
        real = samples[samples.family == "real"].merge(tiles, on="tile_id", how="left")
        nd_f = ROOT / "docs" / "tables" / "nodata_sample.parquet"
        ax.hist(real.qc_frac_unusable.dropna(), bins=40, histtype="step", lw=1.0, color="#1f77b4", label=f"real tiles ({int(real.qc_frac_unusable.notna().sum()):,})")
        if nd_f.exists():
            nd = pd.read_parquet(nd_f)
            syn = nd[nd.family == "synthetic"]
            ax.hist(syn.nodata_frac_measured, bins=40, histtype="step", lw=1.0, color="#ff7f0e", label=f"synthetic sample ({len(syn):,})")
        ax.set_yscale("log")
        ax.set_xlabel("NoData fraction of the raster")
        ax.set_ylabel("landscapes")
        ax.set_title("NoData fraction")
        ax.legend(frameon=False, fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.12), ncol=2, handlelength=1.0, columnspacing=0.8)
        ax.grid(alpha=0.3, lw=0.5)
        _save(fig, "figA_stats_contrast")

        # (b) biome and realm coverage of the real landscapes, stacked by tier
        fig, axes = plt.subplots(1, 2, figsize=(FULLW, 2.9), gridspec_kw=dict(wspace=0.75, width_ratios=[1.35, 1]))
        for ax, key, title in ((axes[0], "biome_name", "biome (RESOLVE Ecoregions 2017)"), (axes[1], "realm", "biogeographic realm")):
            tab = real.groupby([key, "tier"]).size().unstack(fill_value=0).reindex(columns=TIER_ORDER, fill_value=0)
            tab = tab.loc[tab.sum(axis=1).sort_values(ascending=True).index]
            left = np.zeros(len(tab))
            for t in TIER_ORDER:
                ax.barh(np.arange(len(tab)), tab[t].values, left=left, color=tier_color[t], label=t, height=0.75, lw=0)
                left += tab[t].values
            ax.set_yticks(np.arange(len(tab)))
            ax.set_yticklabels([str(b).replace("Tropical & Subtropical", "Trop. & Subtrop.")[:44] for b in tab.index], fontsize=6.5)
            ax.set_xlabel("real landscapes")
            ax.set_title(title)
            ax.grid(alpha=0.3, axis="x", lw=0.5)
        axes[1].legend(frameon=False, fontsize=6.5, title="tier", title_fontsize=6.5, loc="center left", bbox_to_anchor=(1.02, 0.5))
        _save(fig, "figA_stats_biome_realm")

        # (c) solve time per configuration and tier
        configs = ["points", "wall_to_wall_NS", "wall_to_wall_EW", "regions", "advanced", "omniscape"]
        short = {"points": "points", "wall_to_wall_NS": "w2w NS", "wall_to_wall_EW": "w2w EW", "regions": "regions", "advanced": "advanced", "omniscape": "omniscape"}
        fig, axes = plt.subplots(1, 5, figsize=(FULLW, 2.1), gridspec_kw=dict(wspace=0.55))
        for ax, t in zip(axes, TIER_ORDER, strict=False):
            sub = idx[idx.tier == t]
            data = [np.log10(sub[sub.config == c].solve_time_s.clip(lower=1e-2).dropna().values) for c in configs]
            present = [(short[c], d) for c, d in zip(configs, data, strict=False) if len(d)]
            bp = ax.boxplot([d for _, d in present], showfliers=False, widths=0.6, patch_artist=True,
                            medianprops=dict(color="k", lw=0.9), boxprops=dict(lw=0.6, facecolor=tier_color[t], alpha=0.55), whiskerprops=dict(lw=0.6), capprops=dict(lw=0.6))
            ax.set_xticks(np.arange(1, len(present) + 1))
            ax.set_xticklabels([n for n, _ in present], rotation=60, ha="right", rotation_mode="anchor", fontsize=6)
            ax.tick_params(axis="y", labelsize=6)
            ax.set_title(f"tier {t}")
            ax.grid(alpha=0.3, axis="y", lw=0.5)
            if ax is axes[0]:
                ax.set_ylabel("log$_{10}$ solve time (s)")
        _save(fig, "figA_stats_solve_times")

        # (d) storage per tier and task group
        gb = counts["per_tier_group_gb"]
        groups = ["T1", "T1W", "T1R", "T3", "T4"]
        mat = np.array([[gb.get(f"{t}/{g}", 0.0) for g in groups] for t in TIER_ORDER])
        fig, ax = plt.subplots(figsize=(3.4, 2.3))
        bottom = np.zeros(len(TIER_ORDER))
        for j, g in enumerate(groups):
            ax.bar(TIER_ORDER, mat[:, j], bottom=bottom, label=g, lw=0)
            bottom += mat[:, j]
        for i, t in enumerate(TIER_ORDER):
            ax.text(i, bottom[i] + 4, f"{bottom[i]:.0f}", ha="center", va="bottom", fontsize=6.5)
        ax.set_ylabel("GB on the Hub")
        ax.set_ylim(0, bottom.max() * 1.12)
        ax.legend(frameon=False, fontsize=6.5, ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.0), columnspacing=1.2, handlelength=1.2)
        ax.set_title(f"storage by tier and task group ({counts['total_data_gb']:,.0f} GB)", pad=16)
        ax.grid(alpha=0.3, axis="y", lw=0.5)
        _save(fig, "figA_stats_storage")


def tex_figures(only: set[str] | None = None) -> None:
    """All figures of the LaTeX paper (paper/neurips/figures/)."""
    fns = [fig_overview, fig_gallery, fig_qualitative, fig_error_vs_tier_tex, fig_pareto_L_tex, fig_scale_transfer_tex,
           fig_ood_tex, lambda: fig_ood_tex(("T1", "T3", "T4"), "figA_ood_all", stacked=False),
           figA_training_curves, figA_data_scaling, figA_fidelity, figA_precision, figA_wp7, figA_stats, figA_cheap_baselines]
    for fn in fns:
        name = getattr(fn, "__name__", "fig_ood_all")
        if only and not any(o in name for o in only):
            continue
        try:
            fn()
        except Exception as e:  # noqa: BLE001 — one broken panel must not stop the rest
            log(f"paper figure {name} FAILED: {e!r}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default="paper")
    ap.add_argument(
        "--skip-stats", action="store_true", help="skip F1 (reads the full indexes; slow)"
    )
    ap.add_argument("--tex", action="store_true", help="also draw the LaTeX paper's figures into paper/neurips/figures/")
    ap.add_argument("--only", nargs="*", help="with --tex: draw only the figures whose function name contains one of these strings")
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
        tex_figures(set(a.only) if a.only else None)
    log("done")



def figA_cheap_baselines() -> None:
    """Appendix (review rounds 2-3): error versus cost on T1 (all pairs) and T3 on the same test_id landscapes and the
    same targets — truncated AMG-PCG after k iterations (one CPU core; mean solid, median dashed), coarsen-x4 (one
    core) and the learned models (GPU inference per landscape; mean filled, median hollow)."""
    p = ROOT / "docs" / "tables" / "review_round3_pcg.json"
    if not p.exists():
        return
    d = json.loads(p.read_text())
    tier_color = {"S": "#1f77b4", "M": "#ff7f0e", "L": "#2ca02c"}
    floor = 1e-4
    with plt.rc_context(PAPER_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(FULLW, 2.4), gridspec_kw=dict(wspace=0.3))
        for ax, task in zip(axes, ("T1", "T3"), strict=True):
            for tier in ("S", "M", "L"):
                rows = d.get(task, {}).get(tier, [])
                pcg = [r for r in rows if r["method"].startswith("PCG k=")]
                pcg.sort(key=lambda r: int(r["method"].split("=")[1]))
                for stat, ls in (("rel_l2_mean", "-"), ("rel_l2_median", "--")):
                    xs = [r["cost_s"] for r in pcg]
                    ys = [max(r[stat], floor) for r in pcg]
                    ax.plot(xs, ys, ls, color=tier_color[tier], lw=1.0 if ls == "-" else 0.8, marker="." if ls == "-" else None, ms=3.5)
                for r in pcg:
                    k = int(r["method"].split("=")[1])
                    if k in (2, 8):
                        ax.annotate(f"k={k}", (r["cost_s"], max(r["rel_l2_mean"], floor)), textcoords="offset points", xytext=(4, 0), fontsize=5.5, color=tier_color[tier], va="center")
                for r in rows:
                    if r["method"] == "coarsen x4":
                        ax.scatter([r["cost_s"]], [max(r["rel_l2_mean"], floor)], marker="s", s=24, facecolor="w", edgecolor=tier_color[tier], lw=1.1, zorder=3)
                    base = {"U-Net": "unet", "FNO": "fno", "ViT": "vit", "GNN": "gnn", "MgNO": "mgno"}.get(r["method"])
                    if base and np.isfinite(r.get("gpu_s", np.nan)):
                        ax.scatter([r["gpu_s"]], [r["rel_l2_mean"]], marker="^", s=26, color=MODEL_COLOR[base], edgecolor=tier_color[tier], lw=0.8, zorder=4)
                        ax.scatter([r["gpu_s"]], [r["rel_l2_median"]], marker="^", s=22, facecolor="w", edgecolor=MODEL_COLOR[base], lw=0.8, zorder=4)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_ylim(5e-5, 3)
            ax.set_xlabel("cost per landscape (s)")
            ax.set_title({"T1": "T1 pairwise (cumulative over all pairs)", "T3": "T3 advanced mode"}[task], fontsize=7.5)
            ax.grid(alpha=0.3, which="both", lw=0.5)
        axes[0].set_ylabel("rel-L2 on test_id subset")
        L2D = matplotlib.lines.Line2D
        h = [L2D([], [], color=tier_color[t], lw=1.0) for t in ("S", "M", "L")]
        lab = [f"PCG, {t}" for t in ("S", "M", "L")]
        h += [L2D([], [], color="0.3", lw=1.0, marker="."), L2D([], [], color="0.3", lw=0.8, ls="--"),
              L2D([], [], marker="s", ls="", mfc="w", mec="0.3", ms=4)]
        lab += ["mean", "median", "coarsen ×4 (mean)"]
        for base in ("unet", "fno", "vit", "gnn", "mgno"):
            h.append(L2D([], [], marker="^", ls="", color=MODEL_COLOR[base], ms=5))
            lab.append(f"{MODEL_LABEL[base]} (GPU)")
        fig.legend(h, lab, frameon=False, loc="upper center", ncol=6, bbox_to_anchor=(0.5, 1.16), fontsize=6, columnspacing=0.8, handlelength=1.6)
        _save(fig, "figA_cheap_baselines")

if __name__ == "__main__":
    main()
