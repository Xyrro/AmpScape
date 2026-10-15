#!/usr/bin/env python
"""Configuration selection per model × task × tier on validation loss (owner rule, 2026-10-15): the tier-tuned
configuration ('_t2' re-runs) is the official one for a (model, task, tier) only if its best validation loss, mean
over its seeds, is below the pre-tuning configuration's mean by more than the pre-tuning standard error
(std over seeds / sqrt(n_tuned)) — the seed-1 rule of scripts/tuning_select.py (candidate vs seed 1, margin = full
seed spread) applied to seed means. Test metrics are never read and a decision is never carried across tasks.
Where only the T1 tuning candidate exists (no re-runs yet), the seed-1 rule decides T1 alone.

  python scripts/tuning_decisions.py [--runs runs/full] [--out docs/tables/tuning_decisions.md]
                                     [--json docs/tables/tuning_decisions.json] [--winners docs/tables/tuning_full.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODELS = ("unet", "fno", "vit", "gnn")
TASKS = ("T1", "T3", "T4")
TIERS = ("S", "M", "L")
LABEL = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN"}


def best_val(run: pathlib.Path) -> float | None:
    p = run / "log.csv"
    if not p.exists():
        return None
    vals = [float(r["val_loss"]) for r in csv.DictReader(p.open()) if r.get("val_loss")]
    return min(vals) if vals else None


def decide(runs: pathlib.Path, winners: dict) -> dict:
    out = {}
    for tier in TIERS:
        for model in MODELS:
            w = winners.get(tier, {}).get(model, {})
            variant = w.get("variant") if w.get("changed") else None
            for task in TASKS:
                off = [v for s in (1, 2, 3) if (v := best_val(runs / f"{model}_{task}_{tier}_s{s}")) is not None]
                tun = [v for s in (1, 2, 3) if (v := best_val(runs / f"{model}_{task}_{tier}_s{s}_t2")) is not None]
                if not off:
                    continue
                mo = statistics.mean(off)
                sd = statistics.stdev(off) if len(off) > 1 else 0.0
                key = f"{model}_{task}_{tier}"
                if tun:
                    mt = statistics.mean(tun)
                    margin = sd / math.sqrt(len(tun))
                    official = "t2" if mt < mo - margin else "base"
                    out[key] = {
                        "model": model, "task": task, "tier": tier, "variant": variant,
                        "official": official, "n_official": len(off), "n_tuned": len(tun),
                        "val_official_mean": mo, "val_official_std": sd, "val_tuned_mean": mt, "margin": margin,
                        "delta_pct": (mt - mo) / mo * 100, "basis": f"{len(tun)} tuned seeds vs {len(off)} official, margin std/sqrt({len(tun)})",
                    }
                elif variant and task == "T1":
                    cand = best_val(runs / f"{model}_T1_{tier}_s1_tune_{variant}")
                    o1 = best_val(runs / f"{model}_T1_{tier}_s1")
                    if cand is None or o1 is None:
                        continue
                    official = "t2" if cand < o1 - sd else "base"
                    out[key] = {
                        "model": model, "task": task, "tier": tier, "variant": variant,
                        "official": official, "n_official": len(off), "n_tuned": 1,
                        "val_official_mean": o1, "val_official_std": sd, "val_tuned_mean": cand, "margin": sd,
                        "delta_pct": (cand - o1) / o1 * 100, "basis": "tuning candidate seed 1 vs official seed 1, margin std (no re-runs yet)",
                    }
                elif variant:
                    out[key] = {
                        "model": model, "task": task, "tier": tier, "variant": variant, "official": "base",
                        "n_official": len(off), "n_tuned": 0, "val_official_mean": mo, "val_official_std": sd,
                        "val_tuned_mean": None, "margin": None, "delta_pct": None,
                        "basis": "no tuned run for this task yet: pre-tuning configuration stays official",
                    }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/full")
    ap.add_argument("--winners", default="docs/tables/tuning_full.json")
    ap.add_argument("--out", default="docs/tables/tuning_decisions.md")
    ap.add_argument("--json", default="docs/tables/tuning_decisions.json")
    a = ap.parse_args()
    winners = json.loads((ROOT / a.winners).read_text()) if (ROOT / a.winners).exists() else {}
    dec = decide(ROOT / a.runs, winners)
    (ROOT / a.json).write_text(json.dumps(dec, indent=1))
    lines = [
        "# Official configuration per model × task × tier (selection on validation loss only; `scripts/tuning_decisions.py`)",
        "",
        "Rule (owner, 2026-10-15): the tier-tuned configuration is official for a (model, task, tier) only if its best "
        "validation loss (masked MSE, log target; mean over its seeds) is below the pre-tuning configuration's mean by "
        "more than the pre-tuning standard error (seed std / √n). Decisions are never carried across tasks and test "
        "metrics are never read. Where only the T1 tuning candidate exists, the seed-1 rule of `tuning_select.py` decides T1.",
        "",
        "| tier | task | model | tuned variant | official config | val loss pre-tuning (mean ± std) | val loss tuned (mean) | Δ | basis |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for k, r in sorted(dec.items(), key=lambda kv: (TIERS.index(kv[1]["tier"]), kv[1]["task"], kv[1]["model"])):
        mt = "–" if r["val_tuned_mean"] is None else f"{r['val_tuned_mean']:.4f}"
        d = "–" if r["delta_pct"] is None else f"{r['delta_pct']:+.1f} %"
        lines.append(
            f"| {r['tier']} | {r['task']} | {LABEL[r['model']]} | {r['variant'] or '–'} | "
            f"{'**tuned (' + str(r['variant']) + ')**' if r['official'] == 't2' else 'pre-tuning'} | "
            f"{r['val_official_mean']:.4f} ± {r['val_official_std']:.4f} | {mt} | {d} | {r['basis']} |"
        )
    (ROOT / a.out).write_text("\n".join(lines) + "\n")
    print(f"{a.out}: {len(dec)} decisions, tuned official for {sum(1 for r in dec.values() if r['official'] == 't2')}")


if __name__ == "__main__":
    main()
