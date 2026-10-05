#!/usr/bin/env python
"""Build the driver plan for the post-tuning re-runs (item 2): for every model whose per-tier config changed
(`docs/tables/tuning_full.json`), three seeds on all its tasks at that tier with the new variant, plus — for L — the
zero-shot XL/XXL transfer legs and the seed-1 scale-aware variant with its transfers. Runs are named
`<model>_<task>_<tier>_s<seed>_t2` ("tier-tuned", second official configuration); the pre-tuning runs keep their names.

  python scripts/tuning_rerun_plan.py [--winners docs/tables/tuning_full.json] [--out docs/plans/phase14_plan.json]

Cost estimate: the tuning run's measured GPU-h for the chosen variant (T1 at that tier) × task factor
(T4 1.0, T3 1.0) — printed per tag and in total, to be recorded in DECISIONS.md before launch.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASKS = {
    "unet": ["T1", "T4", "T3"],
    "fno": ["T1", "T4", "T3"],
    "vit": ["T1", "T4"],
    "gnn": ["T1", "T4"],
}
DIST = {"fno": " --extra dist", "gnn": " --extra dist", "unet": "", "vit": ""}
XFER_EST = {"XL": 1.0, "XXL": 1.5}


def measured_gpu_h(run: pathlib.Path, default: float) -> float:
    p = run / "log.csv"
    if p.exists():
        d = pd.read_csv(p)
        if len(d) and "cum_gpu_h" in d:
            return float(d.cum_gpu_h.iloc[-1])
    return default


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--winners", default="docs/tables/tuning_full.json")
    ap.add_argument("--out", default="docs/plans/phase14_plan.json")
    a = ap.parse_args()
    w = json.loads((ROOT / a.winners).read_text())
    jobs: list[dict] = []

    def add(name, model, task, tier, seed, tag, extra, est_h, **kw):
        jobs.append(
            {
                "name": name,
                "model": model,
                "task": task,
                "tier": tier,
                "seed": seed,
                "tag": tag,
                "extra": extra,
                "est_h": round(est_h, 2),
                **kw,
            }
        )

    for tier in ("M", "L"):
        for model, info in w.get(tier, {}).items():
            if not info.get("changed"):
                continue
            var = info["variant"]
            base_h = measured_gpu_h(
                ROOT / "runs" / "full" / f"{model}_T1_{tier}_s1_tune_{var}", 3.0
            )
            for task in TASKS[model]:
                for seed in (1, 2, 3):
                    add(
                        f"{model}_{task}_{tier}_s{seed}_t2",
                        model,
                        task,
                        tier,
                        seed,
                        f"RERUN_{tier}",
                        f"--variant {var}{DIST[model]}",
                        base_h,
                    )
            if tier == "L":
                for task in ("T1", "T4"):
                    add(
                        f"{model}_{task}_L_s1_t2_scalenorm",
                        model,
                        task,
                        "L",
                        1,
                        "RERUN_SN",
                        f"--variant {var}{DIST[model]} --target-norm scale",
                        base_h,
                    )
    # transfers for every new L run (zero-shot) and the scale-aware variants
    for j in [x for x in jobs if x["tier"] == "L" and x["task"] in ("T1", "T4")]:
        for xt in ("XL", "XXL"):
            if xt == "XXL" and j["model"] == "vit":
                continue
            jobs.append(
                {
                    "name": f"xfer_{j['name']}_{xt}",
                    "model": j["model"],
                    "task": j["task"],
                    "tier": xt,
                    "seed": j["seed"],
                    "tag": "RERUN_XF",
                    "kind": "transfer",
                    "src": j["name"],
                    "extra": "",
                    "est_h": XFER_EST[xt] * (2.0 if j["model"] == "gnn" else 1.0),
                }
            )
    (ROOT / a.out).write_text(json.dumps(jobs, indent=1))
    by: dict = {}
    for j in jobs:
        by[j["tag"]] = by.get(j["tag"], 0.0) + j["est_h"]
    print(
        f"{len(jobs)} jobs, est {sum(by.values()):.0f} GPU-h:", {k: round(v) for k, v in by.items()}
    )


if __name__ == "__main__":
    main()
