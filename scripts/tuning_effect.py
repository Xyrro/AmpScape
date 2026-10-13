#!/usr/bin/env python
"""What the per-tier tuning pass changed (phase 13/14/15): the official pre-tuning runs versus the tier-tuned re-runs
('_t2') of the same model / task / tier, mean over seeds per split, from docs/tables/baselines_full.md.

  python scripts/tuning_effect.py [--table docs/tables/baselines_full.md] [--out docs/tables/tuning_effect.md]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("paper_figures", ROOT / "scripts" / "paper_figures.py")
pf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pf)

METRICS = ["rel_l2", "mae_log10eps", "top5_iou", "pinch_recall", "spearman"]
LOWER_IS_BETTER = {"rel_l2", "mae_log10eps"}
SPLITS = ["test_id", "test_ood", "ood_region"]


def load(table: pathlib.Path):
    df = pf.read_markdown_table(table)
    parsed = df.model.apply(pf.split_run_name)
    df["base"] = [p[0] for p in parsed]
    df["seed"] = [p[3] for p in parsed]
    df["suffix"] = [p[4] for p in parsed]
    df["tuned"] = df.model.str.contains(r"_t2(?:$|_)", regex=True)
    return df[df.seed.notna() & (df.suffix == "") & df.split.isin(SPLITS)].copy()


def fmt(m: float, s: float, n: int) -> str:
    if not np.isfinite(m):
        return "–"
    return f"{m:.3f} ± {s:.3f}" if n > 1 and np.isfinite(s) else f"{m:.3f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="docs/tables/baselines_full.md")
    ap.add_argument("--tuning", default="docs/tables/tuning_full.json")
    ap.add_argument("--out", default="docs/tables/tuning_effect.md")
    a = ap.parse_args()
    df = load(ROOT / a.table)
    tuned_keys = sorted({(r.task, r.tier, r.base) for r in df[df.tuned].itertuples()})
    lines = [
        "# Effect of the per-tier tuning pass — pre-tuning official runs vs tier-tuned re-runs (`_t2`)",
        "",
        f"Source: `{a.table}` (mean ± std over seeds; Δ = tuned − official, relative; lower rel-L2 / MAE is better). "
        "Rows exist only where tier-tuned re-runs finished; model/tier pairs whose tuning candidates did not beat the "
        "official seed-1 validation loss by more than the official seed spread keep the pre-tuning runs "
        "(`docs/tables/tuning_full.md`).",
        "",
    ]
    tp = ROOT / a.tuning
    if tp.exists():
        tj = json.loads(tp.read_text())  # {tier: {model: {variant, changed, official_variant, official_best_val, candidates}}}
        lines += [
            "## Configuration changes (selection on validation loss, T1 seed 1; `scripts/tuning_select.py`)",
            "",
            "| tier | model | official | chosen | best val loss official → chosen | decision |",
            "|---|---|---|---|---|---|",
        ]
        for tier, models in tj.items():
            for base, r in models.items():
                cand = r.get("candidates", {})
                lines.append(
                    f"| {tier} | {pf.MODEL_LABEL.get(base, base)} | {r.get('official_variant', '–')} | {r.get('variant', '–')} | "
                    f"{r.get('official_best_val', float('nan')):.4f} → {cand.get(r.get('variant'), float('nan')):.4f} "
                    f"(seed spread ± {r.get('official_seed_std', float('nan')):.4f}) | "
                    f"{'config changes' if r.get('changed') else 'official kept'} |"
                )
        lines.append("")
    lines += ["## Per split, mean over seeds", "",
              "| task | tier | model | split | seeds (official / tuned) | rel-L2 official → tuned (Δ) | MAE log10 official → tuned (Δ) | top-5 % IoU | pinch recall | Spearman | params (M) | train GPU-h |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for task, tier, base in tuned_keys:
        for split in SPLITS:
            sub = df[(df.task == task) & (df.tier == tier) & (df.base == base) & (df.split == split)]
            off, tun = sub[~sub.tuned], sub[sub.tuned]
            if off.empty and tun.empty:
                continue

            def cell(k: str, delta: bool = False) -> str:
                mo, so, no = off[k].mean(), off[k].std(), len(off)
                mt, st, nt = tun[k].mean(), tun[k].std(), len(tun)
                s = f"{fmt(mo, so, no)} → {fmt(mt, st, nt)}"
                if delta and np.isfinite(mo) and np.isfinite(mt) and mo:
                    s += f" ({(mt - mo) / abs(mo) * 100:+.1f} %)"
                return s

            lines.append(
                f"| {task} | {tier} | {pf.MODEL_LABEL.get(base, base)} | {split} | {len(off)} / {len(tun)} | "
                f"{cell('rel_l2', True)} | {cell('mae_log10eps', True)} | {cell('top5_iou')} | {cell('pinch_recall')} | "
                f"{cell('spearman')} | {off['params (M)'].mean():.1f} → {tun['params (M)'].mean():.1f} | "
                f"{off['train GPU-h'].mean():.2f} → {tun['train GPU-h'].mean():.2f} |"
            )
    (ROOT / a.out).write_text("\n".join(lines) + "\n")
    print(f"{a.out}: {len(tuned_keys)} tuned (task, tier, model) groups")


if __name__ == "__main__":
    main()
