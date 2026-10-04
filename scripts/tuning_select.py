#!/usr/bin/env python
"""Per-tier tuning pass (item 2, docs/tuning_plan_full.md): selection table on VAL ONLY.

  python scripts/tuning_select.py [--runs runs/full] [--out docs/tables/tuning_full.md] [--json docs/tables/tuning_full.json]

Candidates at tier T ∈ {M, L}: the official seed-1 run `<model>_T1_<T>_s1` (variant = OFFICIAL) and every
`<model>_T1_<T>_s1_tune_<variant>` run. Criterion: best (minimum) validation loss over epochs (masked MSE in the
log-target space, log.csv `val_loss`), i.e. the quantity early stopping monitors; test splits are never read.
Rule: a candidate replaces the official config only if its best val loss is lower than the official seed-1 value by
more than the seed spread of the official config (std of the best val loss over the three official seeds); ties
keep the official config. Output: Markdown table + JSON {tier: {model: {"variant": ..., "changed": bool}}}.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ampscape.models import OFFICIAL  # noqa: E402


def best_val(run: pathlib.Path) -> tuple[float | None, int | None, float | None]:
    p = run / "log.csv"
    if not p.exists():
        return None, None, None
    d = pd.read_csv(p)
    if not len(d) or "val_loss" not in d:
        return None, None, None
    i = int(d.val_loss.idxmin())
    gpu_h = float(d.cum_gpu_h.iloc[-1]) if "cum_gpu_h" in d else None
    return float(d.val_loss.iloc[i]), int(d.epoch.iloc[i]), gpu_h


def n_params(run: pathlib.Path) -> float | None:
    p = run / "config.json"
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("n_params", None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/full")
    ap.add_argument("--out", default="docs/tables/tuning_full.md")
    ap.add_argument("--json", default="docs/tables/tuning_full.json")
    a = ap.parse_args()
    runs = ROOT / a.runs
    lines = [
        "# Per-tier tuning pass at M and L — selection on val only (T1, seed 1; `scripts/tuning_select.py`)",
        "",
        "Criterion: best validation loss over epochs (masked MSE, log target). A candidate replaces the official",
        "config only if it beats the official seed-1 value by more than the official config's seed spread",
        "(std of best val loss over seeds 1–3). Test splits are not used.",
        "",
        "| tier | model | variant | best val loss | epoch | params (M) | train GPU-h | vs official | decision |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    winners: dict = {}
    for tier in ("M", "L"):
        winners[tier] = {}
        for model in ("unet", "fno", "vit", "gnn"):
            off_var = OFFICIAL[model][0]
            seeds = []
            for s in (1, 2, 3):
                v, _, _ = best_val(runs / f"{model}_T1_{tier}_s{s}")
                if v is not None:
                    seeds.append(v)
            if not seeds:
                continue
            off_v = seeds[0]
            spread = float(np.std(seeds, ddof=1)) if len(seeds) > 1 else 0.0
            cands = [(off_var, runs / f"{model}_T1_{tier}_s1")]
            for p in sorted(runs.glob(f"{model}_T1_{tier}_s1_tune_*")):
                cands.append((re.sub(r"^.*_tune_", "", p.name), p))
            rows = []
            for var, p in cands:
                v, ep, gh = best_val(p)
                if v is None:
                    rows.append((var, None, None, n_params(p), gh))
                    continue
                rows.append((var, v, ep, n_params(p), gh))
            best = min((r for r in rows if r[1] is not None), key=lambda r: r[1])
            changed = best[0] != off_var and (off_v - best[1]) > spread
            chosen = best[0] if changed else off_var
            winners[tier][model] = {
                "variant": chosen,
                "changed": bool(changed),
                "official_variant": off_var,
                "official_best_val": off_v,
                "official_seed_std": spread,
                "candidates": {r[0]: r[1] for r in rows},
            }
            for var, v, ep, npar, gh in rows:
                tag = "official" if var == off_var else ""
                rel = "" if v is None or var == off_var else f"{(v - off_v) / off_v * 100:+.1f} %"
                dec = ("**chosen**" if var == chosen else "") if v is not None else "missing"
                lines.append(
                    f"| {tier} | {model} | {var} {tag} | {v:.4f} | {ep} | {npar / 1e6:.1f} | {gh:.2f} | {rel} | {dec} |"
                    if v is not None
                    else f"| {tier} | {model} | {var} {tag} | – | – | {(npar or 0) / 1e6:.1f} | – | | missing |"
                )
            lines.append(
                f"| {tier} | {model} | (official seed spread) | ± {spread:.4f} | | | | | {'config changes' if changed else 'official kept'} |"
            )
    (ROOT / a.out).write_text("\n".join(lines) + "\n")
    (ROOT / a.json).write_text(json.dumps(winners, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
