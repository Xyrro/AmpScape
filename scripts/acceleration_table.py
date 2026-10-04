#!/usr/bin/env python
"""Solver-acceleration results (item 1): AMG-PCG iterations and wall time to rtol 1e-6 warm-started from the
predicted voltage versus from zero, per voltage-head run and split (from `evaluate.py --acceleration` outputs).

  python scripts/acceleration_table.py [--runs runs/full] [--out docs/tables/acceleration.md]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/full")
    ap.add_argument("--out", default="docs/tables/acceleration.md")
    a = ap.parse_args()
    lines = [
        "# Solver acceleration: AMG-PCG warm-started from the predicted voltage vs zero start (rtol 1e-6)",
        "",
        "Voltage heads: official U-Net / FNO configurations trained to predict the voltage map (T3 advanced mode;",
        "T1V = first pair of each T1 landscape, point source/ground, pre-solved) — seed 1. Medians over systems;",
        "'reduction' = median of 1 − warm/zero per system; residual_start = relative residual of the warm start",
        "(zero start = 1). CPU, Julia, same preconditioner/matrix/tolerance as the stored baselines.",
        "",
        "| task | tier | model | split | systems | iters zero → warm | iter reduction | time zero → warm (ms) | time reduction | warm-start residual | converged |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    n = 0
    for run in sorted((ROOT / a.runs).glob("*_voltage")):
        m = re.match(r"^(unet|fno|vit|gnn|mgno)_(T3|T1V)_(S|M|L)_s(\d+)_voltage$", run.name)
        if not m:
            continue
        for ev in sorted(run.glob("eval_accel_*/results.json")):
            r = json.loads(ev.read_text())
            s = r.get("acceleration", {}).get("summary", {})
            if not s or not s.get("n_systems"):
                continue
            split = ev.parent.name.replace("eval_accel_", "")
            lines.append(
                f"| {m.group(2)} | {m.group(3)} | {m.group(1)} | {split} | {s['n_systems']} | "
                f"{s['iters_zero_median']:.0f} → {s['iters_warm_median']:.0f} | {s['iter_reduction_median'] * 100:+.1f} % | "
                f"{s['time_zero_median_s'] * 1e3:.1f} → {s['time_warm_median_s'] * 1e3:.1f} | {s['time_reduction_median'] * 100:+.1f} % | "
                f"{s['residual_start_warm_median']:.3g} | {s['converged_warm_fraction'] * 100:.1f} % |"
            )
            n += 1
    (ROOT / a.out).write_text("\n".join(lines) + "\n")
    print(f"{n} rows -> {a.out}")


if __name__ == "__main__":
    main()
