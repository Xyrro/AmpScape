#!/usr/bin/env python
"""Review round 3: T4 evaluations on auxiliary builds that are read directly (inputs/ + outputs/, no finalize).

  models    --tier S --rules default,uniform,random_field,habitat_core [--root aux/review_round3/source_ood]
            Point 1 (independent source rules): every official T4 run at the tier (5 models x 3 seeds) predicts each
            rule's landscapes twice — with the rule's true source raster, and with the production source raster of the
            same landscape swapped in (the `default` build). If a model reads its source channel, the swap must hurt.
            Also scored: the production-rule solver map used as the prediction for the new rule ("unchanged").
            -> <root>/models_<tier>.parquet (one row per run x rule x landscape x input)
  heuristic --fit aux/t4_bs1_reference/M_bs1:ood_region --eval S=aux/review_round3/source_ood/S_default:test_id,...
            Point 2b (a solver-free T4 baseline): the radius law C ~ k * r * mean_r(s) * (g / mean_r(g))^beta,
            mean_r = disc mean over the Omniscape radius r (FFT convolution over valid pixels), g = 1/R. Two rows:
            `radius law` (k = 2/3, beta = 0: no parameters) and `radius law + conductance` (k, beta fitted once on the
            fit build and reused at every tier). -> aux/review_round3/heuristic/heuristic.parquet
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import h5py
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
MODELS = ["unet", "fno", "vit", "gnn", "mgno"]
RADIUS = {"S": 16, "M": 32, "L": 64, "XL": 128, "XXL": 256}


def read_build(build: pathlib.Path, split: str | None = None):
    """Yield (sample_id, d) with d = dataset-like item: resistance, log_resistance, nodata, source_strength, cum_current."""
    sel = None
    for name in ("manifest.parquet", "selection.parquet"):
        if (build / name).exists():
            sel = pd.read_parquet(build / name)
            break
    keep = set(sel.sample_id[sel.split == split]) if (split and sel is not None and "split" in sel) else None
    split_of = dict(zip(sel.sample_id, sel.split, strict=True)) if (sel is not None and "split" in sel) else {}
    outs = {}
    for o in sorted((build / "outputs").glob("shard-*.outputs.h5")):
        with h5py.File(o, "r") as f:
            for sid in f["samples"]:
                g = f["samples"][sid]
                if "complete" in g.attrs and "outputs" in g and "omniscape" in g["outputs"]:
                    outs[sid] = o
    seen = set()  # a sample can sit in two input files (L_bs1: shards 0-4 were first prepared 12 per shard)
    for i in sorted((build / "inputs").glob("shard-*.inputs.h5")):
        with h5py.File(i, "r") as fi:
            for sid in fi["samples"]:
                if sid not in outs or sid in seen or (keep is not None and sid not in keep) or (split_of and sid not in split_of):
                    continue
                seen.add(sid)
                g = fi["samples"][sid]
                R = g["inputs"]["resistance"][...].astype(np.float32)
                nd = g["inputs"]["nodata_mask"][...].astype(np.float32)
                s = g["configs"]["omniscape"]["source_strength"][...].astype(np.float32)
                with h5py.File(outs[sid], "r") as fo:
                    go = fo["samples"][sid]["outputs"]["omniscape"]
                    C = go["cum_current"][...].astype(np.float32)
                    wall = float(json.loads(go.attrs["stats"]).get("wall_s", np.nan))
                meta = json.loads(g.attrs["meta"]) if "meta" in g.attrs else {}
                yield sid, {
                    "sample_id": sid,
                    "config": "omniscape",
                    "resistance": R[None],
                    "log_resistance": np.log(np.where(nd > 0, 1.0, R))[None].astype(np.float32),
                    "nodata": nd[None],
                    "source_strength": s[None],
                    "cum_current": C[None],
                    "family": meta.get("family", meta.get("generator")),
                    "split": split_of.get(sid),
                    "solve_s": wall,
                }


def score(pred: np.ndarray, truth: np.ndarray, m: np.ndarray) -> dict:
    from ampscape.metrics.domain import spearman, top_q_iou
    from ampscape.metrics.pixel import mae_log, rel_l2

    return {
        "rel_l2": rel_l2(pred, truth, m),
        "mae_log10eps": mae_log(pred, truth, m),
        "top5_iou": top_q_iou(pred, truth, m, 5.0),
        "spearman": spearman(pred, truth, m),
    }


def official_runs(model: str, tier: str) -> list[pathlib.Path]:
    dec = json.loads((ROOT / "docs" / "tables" / "tuning_decisions.json").read_text())
    t2 = dec.get(f"{model}_T4_{tier}", {}).get("official", "base") == "t2"
    runs = [ROOT / "runs" / "full" / f"{model}_T4_{tier}_s{s}{'_t2' if t2 else ''}" for s in (1, 2, 3)]
    return [r for r in runs if (r / "best.pt").exists()]


class ListDS:
    def __init__(self, items):
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def run_models(tier: str, groups) -> list[dict]:
    """groups: [(group, input_tag, {sid: d}, source_override {sid: s} | None)]; every official T4 run at the tier
    (5 models x 3 seeds) predicts every group; one row per run x group x landscape."""
    import torch
    from train import Items, collate, forward  # scripts/train.py

    from ampscape.models import build_model
    from ampscape.models.common import inverse_target

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows = []
    for model in MODELS:
        for run in official_runs(model, tier):
            cfg = json.loads((run / "config.json").read_text())
            net = build_model(cfg["model"], cfg["input_channels"], **cfg["model_config"])
            net.load_state_dict(torch.load(run / "best.pt", map_location="cpu")["model"])
            net.to(device).eval()
            stats = {"log_resistance": cfg["norm_stats"]}
            extra = tuple(cfg.get("extra_channels", []))
            mc = cfg["model_config"]
            amp = cfg.get("amp", True) and cfg["model"] != "fno" and device.type == "cuda"
            t0 = time.time()
            for group, inp, data, override in groups:
                items = []
                for sid, d in data.items():
                    if override is not None:
                        if sid not in override:
                            continue
                        d = dict(d, source_strength=override[sid])
                    items.append(d)
                it = Items(ListDS(items), "T4", stats, cfg["model"] == "gnn", extra, bool(mc.get("multiscale", False)),
                           tier, cfg.get("target_norm", "abs"), "default", 1.0, int(mc.get("factor", 4)))
                dl = torch.utils.data.DataLoader(it, batch_size=4, shuffle=False, num_workers=2, collate_fn=collate)
                with torch.no_grad():
                    for batch in dl:
                        if device.type == "cuda":
                            torch.cuda.synchronize()
                        t1 = time.perf_counter()
                        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=amp):
                            y = forward(net, cfg["model"], batch, device).float()
                        if device.type == "cuda":
                            torch.cuda.synchronize()
                        dt = (time.perf_counter() - t1) / y.shape[0]
                        y = y.cpu().numpy()
                        for i, sid in enumerate(batch["sample_id"]):
                            d = data[sid]
                            m = d["nodata"][0] == 0
                            pred = np.where(m, inverse_target(y[i, 0], batch["scale"][i]), 0.0)
                            rows.append({"run": run.name, "model": model, "seed": int(cfg["seed"]), "rule": group, "input": inp,
                                         "sample_id": sid, "family": d["family"], "time_s": dt, **score(pred, d["cum_current"][0], m)})
            print(f"{run.name}: {time.time() - t0:.0f} s", flush=True)
            del net
            if device.type == "cuda":
                torch.cuda.empty_cache()
    return rows


def cmd_models(a):
    root = pathlib.Path(a.root)
    rules = a.rules.split(",")
    data = {r: dict(read_build(root / f"{a.tier}_{r}")) for r in rules + (["default"] if "default" not in rules else [])}
    prod_src = {sid: d["source_strength"] for sid, d in data["default"].items()}
    prod_map = {sid: d["cum_current"][0] for sid, d in data["default"].items()}
    print({r: len(v) for r, v in data.items()}, flush=True)
    rows = []
    # solver-side reference rows: the production-rule map as the prediction for the new rule
    for r in rules:
        for sid, d in data[r].items():
            if sid in prod_map:
                m = d["nodata"][0] == 0
                rows.append({"run": "production-rule map", "model": "unchanged", "seed": 0, "rule": r, "input": "-",
                             "sample_id": sid, "family": d["family"], **score(prod_map[sid], d["cum_current"][0], m)})

    rows += run_models(a.tier, [(r, inp, data[r], (prod_src if inp == "production" else None))
                                for r in rules for inp in ("true", "production") if not (inp == "production" and r == "default")])
    df = pd.DataFrame(rows)
    import torch

    df["inference"] = "bf16 autocast (GPU; FNO fp32)" if torch.cuda.is_available() else "fp32 (CPU)"
    df.to_parquet(root / f"models_{a.tier}.parquet", index=False)
    print(df.groupby(["model", "rule", "input"]).rel_l2.mean().unstack(["input"]).round(3).to_string())


# ---------------------------------------------------------------------------------------------------------------
def disc_mean(a: np.ndarray, w: np.ndarray, r: int) -> np.ndarray:
    """Mean of `a` over valid pixels (weight w in {0,1}) within a disc of radius r, by FFT convolution."""
    from scipy.signal import fftconvolve

    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    k = ((yy**2 + xx**2) <= r * r).astype(np.float64)
    num = fftconvolve(a * w, k, mode="same")
    den = fftconvolve(w, k, mode="same")
    return np.where(den > 0.5, num / np.maximum(den, 1e-9), 0.0)


def heuristic_parts(d: dict, tier: str):
    r = RADIUS[tier]
    m = d["nodata"][0] == 0
    w = m.astype(np.float64)
    s = d["source_strength"][0].astype(np.float64)
    g = np.where(m, 1.0 / np.maximum(d["resistance"][0].astype(np.float64), 1e-12), 0.0)
    sbar = disc_mean(s, w, r)
    gbar = disc_mean(g, w, r)
    ratio = np.where((gbar > 0) & m, g / np.maximum(gbar, 1e-30), 0.0)
    return r, m, sbar, ratio


def cmd_heuristic(a):
    from ampscape.metrics.pixel import rel_l2

    def parse(spec):
        tier_build, _, split = spec.partition(":")
        return tier_build, split or None

    # fit k, beta on the fit build (rel-L2 is scale-sensitive, so k is the per-beta least-squares optimum on the pooled
    # fit set and beta is chosen on the mean per-landscape rel-L2)
    fb, fsplit = parse(a.fit)
    ftier = a.fit_tier
    fit = [(heuristic_parts(d, ftier), d["cum_current"][0]) for _, d in read_build(pathlib.Path(fb), fsplit)]
    print(f"fit set: {len(fit)} landscapes ({fb}:{fsplit}, tier {ftier})", flush=True)
    best = None
    for beta in a.betas:
        num = den = 0.0
        for (r, m, sbar, ratio), C in fit:
            base = r * sbar * ratio**beta
            num += float((base[m] * C[m]).sum())
            den += float((base[m] ** 2).sum())
        k = num / den
        err = float(np.mean([rel_l2(k * r * sbar * ratio**beta, C, m) for (r, m, sbar, ratio), C in fit]))
        print(f"beta {beta}: k {k:.4f}, fit rel-L2 {err:.4f}", flush=True)
        if best is None or err < best[2]:
            best = (beta, k, err)
    beta, k, _ = best
    variants = {"radius law (k=2/3, no fit)": (2.0 / 3.0, 0.0), f"radius law + conductance (k={k:.3f}, beta={beta})": (k, beta)}
    rows = []
    for spec in a.eval:
        tier, _, rest = spec.partition("=")
        b, split = parse(rest)
        for sid, d in read_build(pathlib.Path(b), split):
            t0 = time.perf_counter()
            r, m, sbar, ratio = heuristic_parts(d, tier)
            dt = time.perf_counter() - t0
            for name, (kk, bb) in variants.items():
                pred = np.where(m, kk * r * sbar * ratio**bb, 0.0)
                rows.append({"tier": tier, "build": b, "split": d["split"], "method": name, "sample_id": sid, "family": d["family"],
                             "time_s": dt, **score(pred, d["cum_current"][0], m)})
        print(f"{spec}: done", flush=True)
    out = ROOT / "aux" / "review_round3" / "heuristic"
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(out / "heuristic.parquet", index=False)
    (out / "fit.json").write_text(json.dumps({"fit": a.fit, "fit_tier": ftier, "beta": beta, "k": k, "n_fit": len(fit)}, indent=1))
    print(df.groupby(["tier", "method"])[["rel_l2", "mae_log10eps", "top5_iou", "spearman", "time_s"]].mean().round(4).to_string())


def cmd_reference(a):
    """Point 3a: the official T4 models, the production targets and the radius-law baseline against the exact block-1
    maps of the (enlarged) L reference set, per split. -> aux/review_round3/reference/reference_<tier>.parquet"""
    from huggingface_hub import hf_hub_download

    sel = pd.concat([pd.read_parquet(pathlib.Path(b) / ("manifest.parquet" if (pathlib.Path(b) / "manifest.parquet").exists() else "selection.parquet"))
                     .assign(build=b) for b in a.builds], ignore_index=True)
    split_of = dict(zip(sel.sample_id, sel.split, strict=True))
    build_of = dict(zip(sel.sample_id, sel.build, strict=True))
    data = {}
    for b in a.builds:
        data.update(dict(read_build(pathlib.Path(b))))
    print(f"{len(data)} landscapes with exact maps", flush=True)
    idx = pd.read_parquet(ROOT / "data" / "hf" / "AmpScape" / "index" / f"{a.tier}.parquet")
    hf = dict(zip(idx[idx.config == "omniscape"].sample_id, idx[idx.config == "omniscape"].hf_path, strict=True))
    rows = []
    fit = json.loads((ROOT / "aux" / "review_round3" / "heuristic" / "fit.json").read_text())
    for rel in sorted({hf[s] for s in data}):
        p = hf_hub_download("Xirro/AmpScape", rel, repo_type="dataset", cache_dir=str(ROOT / "data" / "hfcache_r3"))
        with h5py.File(p, "r") as f:
            for sid in [s for s in data if hf[s] == rel]:
                go = f[sid]["configs"]["omniscape"]["outputs"]
                d = data[sid]
                m = d["nodata"][0] == 0
                st = json.loads(go.attrs["solver_stats"])
                base = {"split": split_of[sid], "build": build_of[sid], "sample_id": sid, "family": d["family"], "seed": 0}
                rows.append({**base, "method": f"production (block {st['solver_params']['block_size']})", "time_s": float(st["wall_s"]),
                             **score(go["cum_current"][...], d["cum_current"][0], m)})
                rows.append({**base, "method": "exact (block 1)", "time_s": d["solve_s"], "rel_l2": 0.0})
                r, mm, sbar, ratio = heuristic_parts(d, a.tier)
                for name, (kk, bb) in {"radius law (k=2/3)": (2.0 / 3.0, 0.0), "radius law + conductance": (fit["k"], fit["beta"])}.items():
                    rows.append({**base, "method": name, "time_s": np.nan, **score(np.where(mm, kk * r * sbar * ratio**bb, 0.0), d["cum_current"][0], mm)})
    for r_ in run_models(a.tier, [("reference", "true", data, None)]):
        r_.update({"split": split_of[r_["sample_id"]], "build": build_of[r_["sample_id"]], "method": r_["model"]})
        rows.append(r_)
    out = ROOT / "aux" / "review_round3" / "reference"
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(out / f"reference_{a.tier}.parquet", index=False)
    print(df.groupby(["split", "method"]).rel_l2.agg(["mean", "count"]).round(4).to_string())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("models")
    m.add_argument("--tier", required=True)
    m.add_argument("--rules", default="default,uniform,random_field,habitat_core")
    m.add_argument("--root", default=str(ROOT / "aux" / "review_round3" / "source_ood"))
    m.set_defaults(fn=cmd_models)
    h = sub.add_parser("heuristic")
    h.add_argument("--fit", required=True, help="<build>[:split]")
    h.add_argument("--fit-tier", default="M")
    h.add_argument("--betas", type=float, nargs="+", default=[0.0, 0.25, 0.5, 0.75, 1.0])
    h.add_argument("--eval", nargs="+", required=True, help="<tier>=<build>[:split] ...")
    h.set_defaults(fn=cmd_heuristic)
    rf = sub.add_parser("reference")
    rf.add_argument("--tier", default="L")
    rf.add_argument("--builds", nargs="+", default=[str(ROOT / "aux/t4_bs1_reference/L_bs1"), str(ROOT / "aux/t4_bs1_reference/L_bs1_topup")])
    rf.set_defaults(fn=cmd_reference)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
