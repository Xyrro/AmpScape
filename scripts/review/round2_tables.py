#!/usr/bin/env python
"""Review round 2 result tables (docs/tables/review_round2_*.md + .json) from aux/review_round2/:
  omniscape_threads/threads_<n>.json  -> solver wall time per landscape vs Julia threads (M, L), like-for-like speed-ups
                                         of the T4 surrogates and the break-even number of maps including training
  cheap_baselines/pcg.json            -> truncated AMG-PCG on T3 and the first T1 pair: error vs cost per k
  cheap_baselines/coarsen4_<tier>.json -> coarsen-x4-solve-upsample on T1 and T3
Learned-model reference numbers come from docs/tables/baselines_full.md (rel-L2, inference time) and
paper/tables/t4_pareto_{M,L}.md (T4 cost per landscape) and are quoted, not recomputed.
  python scripts/review/round2_tables.py
"""
from __future__ import annotations

import json
import pathlib
import re

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
AUX = ROOT / "aux" / "review_round2"
OUT = ROOT / "docs" / "tables"
LABEL = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN", "mgno": "MgNO"}


def md_rows(path: pathlib.Path) -> list[dict]:
    rows, header = [], None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def learned_reference() -> pd.DataFrame:
    """Official runs on test_id (seed mean): rel-L2, inference and solver seconds per landscape, training GPU-h.
    Official configuration per (model, task, tier) from docs/tables/tuning_decisions.json ('t2' = tuned re-run)."""
    dec = json.loads((ROOT / "docs" / "tables" / "tuning_decisions.json").read_text())
    rows = []
    for d in sorted((ROOT / "runs" / "full").iterdir()):
        m = re.match(r"^(unet|fno|vit|gnn|mgno)_(T1|T3|T4)_(S|M|L)_s(\d)(_t2)?$", d.name)
        if not m or not (d / "results.json").exists():
            continue
        base, task, tier, seed, t2 = m.groups()
        official = dec.get(f"{base}_{task}_{tier}", {}).get("official", "base")
        if (official == "t2") != bool(t2):
            continue
        r = json.loads((d / "results.json").read_text())
        e = r.get("eval", {}).get(f"hfcache_{tier}_test_id", {}).get(task, {})
        if not e:
            continue
        hist = r.get("history", [])
        gpu_h = hist[-1].get("cum_gpu_h") if hist and isinstance(hist[-1], dict) else None
        rows.append({"task": task, "tier": tier, "model": LABEL[base], "base": base, "seed": int(seed), "rel_l2": e.get("rel_l2"),
                     "inference_s": e.get("inference_time_s"), "solver_s": e.get("solve_time_s"), "train_gpu_h": gpu_h})
    return pd.DataFrame(rows)


def threads_table() -> tuple[list[str], dict]:
    recs = []
    for p in sorted((AUX / "omniscape_threads").glob("threads_*.json")):
        recs += json.loads(p.read_text())
    if not recs:
        return [], {}
    d = pd.DataFrame(recs)
    out = {"per_solve": recs}
    lines = ["# Omniscape wall time versus Julia threads (review round 2, point 1)", "",
             "Production T4 configuration per tier (radius / block: M 32 / 3, L 64 / 5; artefact correction on; CHOLMOD window solver) on the",
             "first landscapes of the `test_id` reference subsets, `parallelize = true` with the given number of Julia threads on one",
             "CPU node; 1 thread = the production setting (`parallelize = false`). Same landscapes at every thread count.",
             f"Host: {d.host.iloc[0]}.", "",
             "| tier | threads | n landscapes | wall s per landscape (median) | mean | speed-up vs 1 thread | parallel efficiency |",
             "|---|---|---|---|---|---|---|"]
    summ = {}
    for tier in ("M", "L"):
        base = d[(d.tier == tier) & (d.threads == 1)]
        if base.empty:
            continue
        for nt, g in d[d.tier == tier].groupby("threads"):
            common = set(base.sample_id) & set(g.sample_id)
            b = base[base.sample_id.isin(common)].wall_s.median()
            w = g[g.sample_id.isin(common)].wall_s.median()
            summ[(tier, int(nt))] = {"n": len(common), "median_s": float(w), "mean_s": float(g[g.sample_id.isin(common)].wall_s.mean()), "speedup": float(b / w), "efficiency": float(b / w / nt)}
            lines.append(f"| {tier} | {int(nt)} | {len(common)} | {w:.1f} | {g[g.sample_id.isin(common)].wall_s.mean():.1f} | {b / w:.2f}× | {b / w / nt:.2f} |")
    out["summary"] = {f"{t}_{n}": v for (t, n), v in summ.items()}
    # like-for-like speed-ups and break-even for the T4 surrogates at M and L
    lines += ["", "## Like-for-like speed-up of the T4 surrogates and break-even number of maps", "",
              "Inference cost per landscape and training cost of the official runs from `paper/tables/t4_pareto_{M,L}.md` and",
              "`docs/tables/baselines_full.md` (seed mean); solver cost per landscape from this timing (median). Break-even = maps after",
              "which training once plus inference costs less GPU/CPU wall time than the solver: N ≥ T_train / (t_solver − t_inference).",
              "The GPU-hour and the CPU-node-hour are not priced equally; the table reports wall time only.", "",
              "| tier | model | rel-L2 vs exact map | inference s / map (GPU) | train GPU-h | solver s / map, 1 thread | speed-up, 1 thread | solver s / map, max threads | speed-up, max threads | break-even maps (1 thread) | break-even maps (max threads) |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    ref = learned_reference()
    be = {}
    for tier in ("M", "L"):
        pr = [r for r in md_rows(ROOT / "paper" / "tables" / f"t4_pareto_{tier}.md") if r["split"] == "test_id"]
        nts = sorted(n for (t, n) in summ if t == tier)
        if not nts:
            continue
        t1 = summ[(tier, 1)]["median_s"]; nmax = nts[-1]; tmax = summ[(tier, nmax)]["median_s"]
        for r in pr:
            m = re.match(r"^(unet|fno|vit|gnn|mgno)_T4_\w+?(?: \(tuned\))?(?:_s\d+)?(?:_t2)?(_scalenorm)? \(learned, (\d) seeds?\)$", r["method"])
            if not m or m.group(1) not in ("unet", "fno") or m.group(2) or "scalenorm" in r["method"]:
                continue
            base = m.group(1)
            cost = float(r["cost s / landscape"])
            g = ref[(ref.task == "T4") & (ref.tier == tier) & (ref.base == base)]
            gpu_h = float(g.train_gpu_h.astype(float).mean()) if len(g) else float("nan")
            n1 = gpu_h * 3600 / (t1 - cost); nm = gpu_h * 3600 / (tmax - cost)
            be[f"{tier}_{base}"] = {"rel_l2": float(r["rel_l2"]), "inference_s": cost, "train_gpu_h": gpu_h, "solver_1": t1, "speedup_1": t1 / cost, "solver_max": tmax, "threads_max": nmax, "speedup_max": tmax / cost, "break_even_1": n1, "break_even_max": nm}
            lines.append(f"| {tier} | {LABEL[base]} | {float(r['rel_l2']):.4f} | {cost:.5f} | {gpu_h:.2f} | {t1:.0f} | {t1 / cost:,.0f}× | {tmax:.1f} ({nmax} threads) | {tmax / cost:,.0f}× | {n1:,.0f} | {nm:,.0f} |")
    out["break_even"] = be
    return lines, out


def pcg_table() -> tuple[list[str], dict]:
    p = AUX / "cheap_baselines" / "pcg.json"
    if not p.exists():
        return [], {}
    recs = json.loads(p.read_text())
    ref = learned_reference()
    lines = ["# Truncated AMG-PCG and coarsen-×4 baselines on T3 and the first T1 pair (review round 2, point 4)", "",
             "AMG-preconditioned CG from zero on the exact graph (Circuitscape's cg+amg preconditioner), stopped after k iterations; the",
             "current map is Circuitscape's node current of the truncated voltage. T3: exact `current` target of the shard; T1V: the",
             "first pair of each T1 landscape against a PCG solution at relative residual 1e-12. rel-L2 on raw currents and MAE in",
             "log10-ε space, NoData masked, median over the `test_id` subset (first shards in Hub order); cost = AMG setup + k",
             "iterations on one CPU core, median seconds. Learned rows: the official runs' test_id rel-L2 (seed mean over the whole split)",
             "and inference seconds per landscape (GPU, batch-amortised) from `docs/tables/baselines_full.md`.", ""]
    summ = {}
    for task in ("T3", "T1V"):
        lines += [f"## {task}", "", "| tier | n | k | cost s / landscape (1 core) | rel-L2 median | MAE log10 median | iterations to 1e-6 (median) | time to 1e-6 (median s) |", "|---|---|---|---|---|---|---|---|"]
        for tier in ("S", "M", "L"):
            g = [r for r in recs if r["tier"] == tier and r["task"] == task]
            if not g:
                continue
            ks = sorted({d["k"] for r in g for d in r["k"]})
            it6 = float(np.median([r["converged_1e-6"]["iters"] for r in g])); t6 = float(np.median([r["t_setup_s"] + r["converged_1e-6"]["t_solve_s"] for r in g]))
            for k in ks:
                vals = [(d["t_solve_s"] + r["t_setup_s"], d["rel_l2"], d["mae_log"]) for r in g for d in r["k"] if d["k"] == k and d["rel_l2"] is not None]
                if not vals:
                    continue
                c, rl, ma = (float(np.median([v[i] for v in vals])) for i in range(3))
                summ[f"{task}_{tier}_k{k}"] = {"n": len(g), "cost_s": c, "rel_l2": rl, "mae_log": ma}
                lines.append(f"| {tier} | {len(g)} | {k} | {c:.4f} | {rl:.4f} | {ma:.4f} | {it6:.0f} | {t6:.3f} |")
            summ[f"{task}_{tier}_conv"] = {"iters": it6, "time_s": t6, "rel_l2": float(np.median([r["converged_1e-6"]["rel_l2"] for r in g]))}
            lines.append(f"| {tier} | {len(g)} | to 1e-6 | {t6:.4f} | {summ[f'{task}_{tier}_conv']['rel_l2']:.4f} | – | {it6:.0f} | {t6:.3f} |")
        lines.append("")
    # coarsen
    lines += ["## Coarsen-×4, reference solve on the coarse grid, bilinear upsampling (same subsets)", "",
              "| tier | task | n | cost s / landscape (1 core) | rel-L2 median | MAE log10 median |", "|---|---|---|---|---|---|"]
    for tier in ("S", "M", "L"):
        p = AUX / "cheap_baselines" / f"coarsen4_{tier}.json"
        if not p.exists():
            continue
        c = pd.DataFrame(json.loads(p.read_text()))
        for task, g in c.groupby("task"):
            summ[f"coarsen4_{task}_{tier}"] = {"n": len(g), "cost_s": float(g.inference_time_s.median()), "rel_l2": float(g.rel_l2.median()), "mae_log": float(g.mae_log.median())}
            lines.append(f"| {tier} | {task} | {len(g)} | {g.inference_time_s.median():.4f} | {g.rel_l2.median():.4f} | {g.mae_log.median():.4f} |")
    # learned reference rows
    lines += ["", "## Learned models on the whole test_id split (reference, from docs/tables/baselines_full.md)", "",
              "| tier | task | model | rel-L2 (seed mean) | inference s / landscape | solver s / landscape |", "|---|---|---|---|---|---|"]
    for task in ("T3", "T1"):
        for tier in ("S", "M", "L"):
            g = ref[(ref.task == task) & (ref.tier == tier)]
            for model, gm in g.groupby("model"):
                rl, inf, sol = float(gm.rel_l2.mean()), float(gm.inference_s.mean()), float(gm.solver_s.mean())
                summ[f"learned_{task}_{tier}_{model}"] = {"rel_l2": rl, "inference_s": inf, "solver_s": sol, "seeds": int(len(gm))}
                lines.append(f"| {tier} | {task} | {model} | {rl:.3f} | {inf:.5f} | {sol:.2f} |")
    return lines, summ


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tl, tj = threads_table()
    if tl:
        (OUT / "review_round2_threads.md").write_text("\n".join(tl) + "\n")
        (OUT / "review_round2_threads.json").write_text(json.dumps(tj, indent=1))
        print("wrote docs/tables/review_round2_threads.md")
    pl, pj = pcg_table()
    if pl:
        (OUT / "review_round2_cheap.md").write_text("\n".join(pl) + "\n")
        (OUT / "review_round2_cheap.json").write_text(json.dumps(pj, indent=1))
        print("wrote docs/tables/review_round2_cheap.md")


if __name__ == "__main__":
    main()
