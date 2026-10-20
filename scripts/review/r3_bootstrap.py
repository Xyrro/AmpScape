#!/usr/bin/env python
"""Review round 3, point 3b: bootstrap confidence intervals for the headline rel-L2 numbers, by stratum.

For every official run group (model x task x tier, three seeds, the configuration in docs/tables/tuning_decisions.json)
the per-landscape rel-L2 of each seed is read from the harness results (`per_sample`). The reported value is the
seed mean of the per-seed means (the headline statistic of Table 2); its 95 % interval resamples landscapes
(B = 2000, the same resample for every seed, percentile interval). Strata: test_id (all / synthetic / real),
test_ood (held-out contrast 10^6 / held-out table) and test_ood_published (S). For each task x tier x stratum the
best model is compared with the runner-up by a paired bootstrap over the landscapes both were scored on
(P = share of resamples in which the order flips).

  python scripts/review/r3_bootstrap.py   -> docs/tables/review_round3_bootstrap.{md,json}
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs" / "full"
B = 2000
MODELS = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN", "mgno": "MgNO"}
TASKS = ["T1", "T3", "T4"]
TIERS = ["S", "M", "L"]
DEC = json.loads((ROOT / "docs" / "tables" / "tuning_decisions.json").read_text())


def official_runs(model: str, task: str, tier: str) -> list[pathlib.Path]:
    t2 = DEC.get(f"{model}_{task}_{tier}", {}).get("official", "base") == "t2"
    out = []
    for s in (1, 2, 3):
        d = RUNS / f"{model}_{task}_{tier}_s{s}{'_t2' if t2 else ''}"
        if (d / "results.json").exists():
            out.append(d)
    return out


def per_sample(run: pathlib.Path, split: str) -> pd.DataFrame | None:
    hits = sorted(run.glob(f"predictions/*_{split}/eval_{split}/results.json"))
    if not hits:
        return None
    r = json.loads(hits[0].read_text())
    df = pd.DataFrame(r["per_sample"])
    return df[np.isfinite(df.rel_l2)][["sample_id", "rel_l2", "family"] + [c for c in df.columns if c.startswith("test_ood_")]]


STRATA = {
    "test_id": ("test_id", None),
    "test_id synthetic": ("test_id", lambda d: d.family == "synthetic"),
    "test_id real": ("test_id", lambda d: d.family == "real"),
    "test_ood contrast 1e6": ("test_ood", lambda d: d.get("test_ood_contrast", False) == True),  # noqa: E712
    "test_ood held-out table": ("test_ood", lambda d: d.get("test_ood_table", False) == True),  # noqa: E712
    "published (S)": ("test_ood_published", None),
}


def matrix(runs: list[pathlib.Path], split: str, filt) -> pd.DataFrame | None:
    """landscapes x seeds rel-L2 matrix on the landscapes every seed was scored on."""
    cols = []
    for r in runs:
        d = per_sample(r, split)
        if d is None:
            return None
        if filt is not None:
            d = d[filt(d)]
        cols.append(d.groupby("sample_id").rel_l2.mean().rename(r.name))
    if not cols:
        return None
    m = pd.concat(cols, axis=1, join="inner")
    return m if len(m) else None


def boot(m: pd.DataFrame, rng: np.random.Generator) -> tuple[float, float, float, np.ndarray]:
    a = m.to_numpy()
    est = float(a.mean(axis=0).mean())
    idx = rng.integers(0, len(a), size=(B, len(a)))
    bs = a[idx].mean(axis=1).mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return est, float(lo), float(hi), idx


def main() -> None:
    rng = np.random.default_rng(20261019)
    rows, flips = [], []
    for task in TASKS:
        for tier in TIERS:
            for sname, (split, filt) in STRATA.items():
                if split == "test_ood_published" and tier != "S":
                    continue
                mats = {}
                for mk, mname in MODELS.items():
                    runs = official_runs(mk, task, tier)
                    if len(runs) < 3:
                        continue
                    m = matrix(runs, split, filt)
                    if m is None or len(m) < 5:
                        continue
                    est, lo, hi, _ = boot(m, rng)
                    mats[mname] = m
                    rows.append({"task": task, "tier": tier, "stratum": sname, "model": mname, "n": len(m),
                                 "rel_l2": est, "ci_lo": lo, "ci_hi": hi})
                ranked = sorted((k for k in mats if k != "MgNO"), key=lambda k: mats[k].to_numpy().mean())
                if len(ranked) >= 2:
                    a, b = mats[ranked[0]].mean(axis=1), mats[ranked[1]].mean(axis=1)
                    common = a.index.intersection(b.index)
                    da = (a[common] - b[common]).to_numpy()
                    idx = rng.integers(0, len(da), size=(B, len(da)))
                    p_flip = float((da[idx].mean(axis=1) >= 0).mean())
                    flips.append({"task": task, "tier": tier, "stratum": sname, "best": ranked[0], "runner_up": ranked[1],
                                  "n_common": len(common), "diff": float(da.mean()), "p_order_flips": p_flip})
    df = pd.DataFrame(rows)
    out = ROOT / "docs" / "tables" / "review_round3_bootstrap"
    out.with_suffix(".json").write_text(json.dumps({"B": B, "rows": rows, "ranking": flips}, indent=1))
    lines = ["# Review round 3 — bootstrap 95 % intervals for rel-L2 (official runs, three seeds)", "",
             f"Seed mean of per-seed mean rel-L2; percentile interval over B = {B} landscape resamples (same resample for every seed). "
             "Source: `per_sample` of each run's harness results. Generated by `scripts/review/r3_bootstrap.py`.", ""]
    for task in TASKS:
        lines += [f"## {task}", "", "| tier | stratum | " + " | ".join(MODELS.values()) + " |", "|---|---|" + "---|" * len(MODELS)]
        for (tier, sname), g in df[df.task == task].groupby(["tier", "stratum"], sort=False):
            cells = []
            for mname in MODELS.values():
                r = g[g.model == mname]
                cells.append("—" if r.empty else f"{r.rel_l2.iloc[0]:.3f} [{r.ci_lo.iloc[0]:.3f}, {r.ci_hi.iloc[0]:.3f}] (n {r.n.iloc[0]})")
            lines.append(f"| {tier} | {sname} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Is the best model's lead resolved? (paired bootstrap, MgNO excluded as in Table 2)", "",
              "| task | tier | stratum | best | runner-up | n | mean diff | P(order flips) |", "|---|---|---|---|---|---|---|---|"]
    for r in flips:
        lines.append(f"| {r['task']} | {r['tier']} | {r['stratum']} | {r['best']} | {r['runner_up']} | {r['n_common']} | {r['diff']:+.4f} | {r['p_order_flips']:.3f} |")
    # stratum ratios relative to test_id (MgNO excluded, as in Table 2), cited in the OOD paragraph of the paper
    pv = df[df.model != "MgNO"].pivot_table(index=["task", "tier", "model"], columns="stratum", values="rel_l2")
    nn = df.pivot_table(index=["tier"], columns="stratum", values="n", aggfunc="first")
    lines += ["", "## Stratum ratios relative to test_id (official runs, MgNO excluded)", "", "| stratum | all tasks: min | max | T4: min | max |", "|---|---|---|---|---|"]
    for st in ("test_id synthetic", "test_id real", "test_ood contrast 1e6", "test_ood held-out table", "published (S)"):
        rr = (pv[st] / pv["test_id"]).dropna()
        r4 = rr[rr.index.get_level_values(0) == "T4"]
        lines.append(f"| {st} | {rr.min():.2f} | {rr.max():.2f} | {r4.min():.2f} | {r4.max():.2f} |")
    lines += ["", "Share of the held-out-table part in test_ood (landscapes): " + ", ".join(
        f"{t} {nn.loc[t, 'test_ood held-out table'] / (nn.loc[t, 'test_ood held-out table'] + nn.loc[t, 'test_ood contrast 1e6']) * 100:.0f} %" for t in TIERS)]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))
    print(f"... {len(rows)} rows, {len(flips)} ranking comparisons -> {out}.md/.json")


if __name__ == "__main__":
    sys.exit(main())
