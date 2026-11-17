#!/usr/bin/env python
"""Review round 3, point 5: decision-level evaluation of the many-query demonstration (Section 8 of the paper).

  predict  (GPU)  the official demo model (runs/full/unet_T4_L_s1) on the 160 maps of the demo (20 held-out real L tiles
                  x 8 resistance tables) -> aux/review_round3/decision/maps.h5 (solver and model map per tile x table).
                  The five v1.0 tables are read from the Hub T4 files at revision v1.0 (as in the demo), the three extra
                  random tables from aux/wp7.
  analyze  (CPU)  (a) persistent pinch points: precision and recall of the surrogate route against the solver route over
                  the decision parameters (persistence fraction, top-percent defining a pinch point, matching tolerance);
                  (b) a precision-recall curve from ranking the surrogate's candidates by their persistence;
                  (c) verification budget: a hybrid route that solves m of the 8 tables exactly (m = 0..8) and uses the
                  surrogate for the rest, tables chosen by the surrogate's own effect ranking (most influential first),
                  with the precision/recall/IoU it reaches and its cost in solver maps.
                  -> docs/tables/review_round3_decision.{md,json}
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
WP7 = ROOT / "aux" / "wp7"
OUT = ROOT / "aux" / "review_round3" / "decision"
TABLES = ["generic_hm", "large_mammal", "amphibian", "forest_bird", "random_lm", "random_lm2", "random_lm3", "random_lm4"]
REF_TABLE = "generic_hm"


def demo_items():
    """(tile, table, d, wall_s) for the 160 demo maps."""
    from huggingface_hub import hf_hub_download

    from ampscape.data.dataset import AmpScapeDataset
    from ampscape.io.pagecache import drop_file_cache

    sel = pd.read_parquet(WP7 / "selection.parquet")
    tiles = set(sel.tile_id)
    v1 = pd.read_parquet(WP7 / "v1_samples.parquet")
    v1 = v1[v1.tile_id.isin(tiles)]
    for rel, g in v1.groupby("hf_path"):
        p = hf_hub_download("Xirro/AmpScape", rel, repo_type="dataset", revision="v1.0", cache_dir=str(ROOT / "data" / "hfcache_r3"))
        with h5py.File(p, "r") as f:
            for _, r in g.iterrows():
                gs = f[r.sample_id]
                R = gs["inputs"]["resistance"][...]
                nd = gs["inputs"]["nodata_mask"][...].astype(np.float32)
                gc = gs["configs"]["omniscape"]
                d = {"sample_id": r.sample_id, "config": "omniscape", "resistance": R[None], "log_resistance": np.log(R)[None].astype(np.float32),
                     "nodata": nd[None], "source_strength": gc["inputs"]["source_strength"][...][None],
                     "cum_current": gc["outputs"]["cum_current"][...][None]}
                st = json.loads(gc["outputs"].attrs["solver_stats"])
                yield r.tile_id, r.resistance_table_id, d, float(st.get("wall_s", np.nan))
        drop_file_cache(p)
    ds = AmpScapeDataset("T4", split=None, tier="L", root=WP7, qc_pass_only=False)
    for i in range(len(ds)):
        r = ds.index.iloc[i]
        d = ds[i]
        tile, table = d["meta"].get("tile_id"), d["meta"].get("resistance_table_id")
        if tile not in tiles:
            continue
        g = ds._file(r.path)[r.sample_id]["configs"][r.config]["outputs"]
        st = json.loads(g.attrs.get("solver_stats", g.attrs.get("stats", "{}")))
        yield tile, table, d, float(st.get("wall_s", np.nan))


def cmd_predict(a):
    import torch
    from wp7_demo import load_model

    from ampscape.models.common import inverse_target, make_inputs

    run = ROOT / a.run
    model, cfg = load_model(run)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    stats = {"log_resistance": cfg["norm_stats"]}
    extra = tuple(cfg.get("extra_channels", []))
    OUT.mkdir(parents=True, exist_ok=True)
    bf16 = device.type == "cuda" and not a.fp32
    name = f"maps_{'bf16' if bf16 else 'fp32'}.h5"
    n = 0
    t_model = 0.0
    with h5py.File(OUT / name, "w") as fo:
        fo.attrs["run"] = run.name
        fo.attrs["precision"] = "bf16 autocast" if bf16 else "fp32"
        fo.attrs["device"] = torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu"
        for tile, table, d, wall in demo_items():
            x = torch.from_numpy(make_inputs(d, "T4", stats, extra))[None].to(device)
            if device.type == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=bf16):
                y = model(x).float()
            if device.type == "cuda":
                torch.cuda.synchronize()
            t_model += time.perf_counter() - t0
            y = y[0, 0].cpu().numpy()
            m = d["nodata"][0] == 0
            pred = np.where(m, inverse_target(y), 0.0).astype(np.float32)
            g = fo.require_group(tile).create_group(table)
            g.create_dataset("solver", data=d["cum_current"][0].astype(np.float32), compression="gzip", compression_opts=4)
            g.create_dataset("model", data=pred, compression="gzip", compression_opts=4)
            g.create_dataset("mask", data=m.astype(np.uint8), compression="gzip", compression_opts=4)
            g.attrs["solver_wall_s"] = wall
            n += 1
        fo.attrs["model_seconds_total"] = t_model
    print(f"wrote {n} maps -> {OUT / name}; model time {t_model:.2f} s ({t_model / max(n, 1) * 1000:.1f} ms per map, batch 1, first call included)")


# ---------------------------------------------------------------------------------------------------------------
def pinch_votes(maps: dict, m: np.ndarray, top: float, radius: int = 3) -> np.ndarray:
    """Per pixel: number of tables in which a pinch point (local max in the top-`top` %) lies within `radius` px."""
    from scipy import ndimage

    from ampscape.metrics.domain import pinch_points

    votes = np.zeros(m.shape, np.int32)
    for a_ in maps.values():
        pp = pinch_points(a_, m, top, 3)
        votes += ndimage.maximum_filter(pp.astype(np.uint8), size=2 * radius + 1, mode="constant")
    return votes


def pr(pred_pts: np.ndarray, true_pts: np.ndarray, tol: int) -> tuple[float, float, int, int]:
    """Precision / recall of point sets with a matching tolerance of `tol` px (the demo's definition)."""
    from scipy import ndimage

    size = 2 * tol + 1
    near_t = ndimage.maximum_filter(true_pts.astype(np.uint8), size=size, mode="constant") > 0
    near_p = ndimage.maximum_filter(pred_pts.astype(np.uint8), size=size, mode="constant") > 0
    prec = float(np.logical_and(pred_pts, near_t).sum() / max(pred_pts.sum(), 1)) if pred_pts.any() else float("nan")
    rec = float(np.logical_and(true_pts, near_p).sum() / max(true_pts.sum(), 1)) if true_pts.any() else float("nan")
    return prec, rec, int(pred_pts.sum()), int(true_pts.sum())


def cmd_analyze(a):
    from ampscape.metrics.domain import top_q_mask
    from ampscape.metrics.pixel import rel_l2

    tiles = {}
    with h5py.File(OUT / a.maps, "r") as f:
        run = f.attrs["run"]
        prec_mode = f.attrs.get("precision", "fp32 (CPU)")
        t_inf = float(f.attrs.get("model_seconds_total", float("nan")))
        dev = f.attrs.get("device", "cpu")
        for tile in f:
            S, M, wall = {}, {}, {}
            for table in f[tile]:
                g = f[tile][table]
                S[table], M[table] = g["solver"][...], g["model"][...]
                wall[table] = float(g.attrs["solver_wall_s"])
                mask = g["mask"][...] > 0
            tiles[tile] = (S, M, mask, wall)
    n_t = len(TABLES)
    # (a) sweep over decision parameters ------------------------------------------------------------------------
    sweep = []
    for top in (1.0, 2.0, 5.0, 10.0):
        vS, vM = {}, {}
        for tile, (S, M, m, _) in tiles.items():
            vS[tile], vM[tile] = pinch_votes(S, m, top), pinch_votes(M, m, top)
        for frac in (0.25, 0.375, 0.5, 0.625, 0.75, 1.0):
            need = int(np.ceil(frac * n_t))
            for tol in (1, 3, 5):
                per = [pr(vM[t] >= need, vS[t] >= need, tol) for t in tiles]
                sweep.append({"top_percent": top, "persistence": frac, "tables_needed": need, "tolerance_px": tol,
                              "precision": float(np.nanmean([p[0] for p in per])), "recall": float(np.nanmean([p[1] for p in per])),
                              "n_model": float(np.mean([p[2] for p in per])), "n_solver": float(np.mean([p[3] for p in per])),
                              "tiles_with_points": int(sum(p[3] > 0 for p in per))})
    sw = pd.DataFrame(sweep)
    # (b) ranking the surrogate's candidates by persistence (demo setting: top 5 %, tolerance 3 px, truth = >= 50 %)
    curve = []
    vS5 = {t: pinch_votes(S, m, 5.0) for t, (S, M, m, _) in tiles.items()}
    vM5 = {t: pinch_votes(M, m, 5.0) for t, (S, M, m, _) in tiles.items()}
    truth_need = int(np.ceil(0.5 * n_t))
    for k in range(1, n_t + 1):
        per = [pr(vM5[t] >= k, vS5[t] >= truth_need, 3) for t in tiles]
        curve.append({"model_tables_needed": k, "precision": float(np.nanmean([p[0] for p in per])),
                      "recall": float(np.nanmean([p[1] for p in per])), "n_model": float(np.mean([p[2] for p in per]))})
    # (c) verification budget: solve m tables exactly, surrogate for the rest ------------------------------------
    budget = []
    for mm in range(0, n_t + 1):
        precs, recs, cores, cost = [], [], [], []
        for tile, (S, M, m, wall) in tiles.items():
            eff = {t: rel_l2(M[t], M[REF_TABLE], m) for t in TABLES if t != REF_TABLE}
            order = [REF_TABLE] + sorted(eff, key=eff.get, reverse=True)   # surrogate's own ranking, reference first
            exact = set(order[:mm])
            H = {t: (S[t] if t in exact else M[t]) for t in TABLES}
            p, r, _, _ = pr(pinch_votes(H, m, 5.0) >= truth_need, vS5[tile] >= truth_need, 3)
            precs.append(p)
            recs.append(r)
            cS = np.sum([top_q_mask(S[t], m, 5.0) for t in TABLES], axis=0) >= int(np.ceil(0.75 * n_t))
            cH = np.sum([top_q_mask(H[t], m, 5.0) for t in TABLES], axis=0) >= int(np.ceil(0.75 * n_t))
            u = np.logical_or(cS, cH).sum()
            cores.append(float(np.logical_and(cS, cH).sum() / u) if u else float("nan"))
            cost.append(sum(wall[t] for t in exact))
        budget.append({"tables_solved": mm, "precision": float(np.nanmean(precs)), "recall": float(np.nanmean(recs)),
                       "core_iou": float(np.nanmean(cores)), "solver_cpu_h_per_tile": float(np.mean(cost)) / 3600})
    res = {"run": run, "inference": prec_mode, "device": dev, "inference_seconds_160_maps": t_inf, "n_tiles": len(tiles), "sweep": sweep, "ranking_curve": curve, "budget": budget,
           "notes": "pinch point = local maximum (min distance 3 px) in the top-q % of a map; persistent = present (within "
                    "3 px) in >= the given share of the 8 tables; precision/recall per tile, averaged over tiles."}
    out = ROOT / "docs" / "tables" / f"review_round3_decision_{a.tag}"
    out.with_suffix(".json").write_text(json.dumps(res, indent=1))
    demo = sw[(sw.top_percent == 5.0) & (sw.persistence == 0.5) & (sw.tolerance_px == 3)].iloc[0]
    lines = [f"# Review round 3 — decision-level evaluation of the many-query demonstration ({len(tiles)} real L tiles x {n_t} tables, `{run}`, inference {prec_mode})", "",
             f"Check: the demo setting (top 5 %, >= 50 % of tables, 3 px) gives precision {demo.precision:.3f}, recall {demo.recall:.3f} "
             f"(paper: 0.657 / 0.941). Inference of the 160 maps: {t_inf:.2f} s on {dev} (batch 1, first call included). "
             "Generated by `scripts/review/r3_decision.py`.", "",
             "## (a) Persistent pinch points over the decision parameters (surrogate vs solver route)", "",
             "| top % | persistence | tolerance px | precision | recall | points / tile (surrogate) | points / tile (solver) |",
             "|---|---|---|---|---|---|---|"]
    for r in sweep:
        lines.append(f"| {r['top_percent']:g} | {r['persistence']:g} | {r['tolerance_px']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['n_model']:.0f} | {r['n_solver']:.0f} |")
    lines += ["", "## (b) Ranking the surrogate's candidates by persistence (truth: >= 50 % of solver tables; top 5 %, 3 px)", "",
              "| surrogate tables needed | precision | recall | candidates / tile |", "|---|---|---|---|"]
    for r in curve:
        lines.append(f"| >= {r['model_tables_needed']} of {n_t} | {r['precision']:.3f} | {r['recall']:.3f} | {r['n_model']:.1f} |")
    lines += ["", "## (c) Verification budget: m of 8 tables solved exactly (surrogate's ranking, reference table first)", "",
              "| tables solved | precision | recall | consensus-core IoU | solver CPU-h per tile |", "|---|---|---|---|---|"]
    for r in budget:
        lines.append(f"| {r['tables_solved']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['core_iou']:.3f} | {r['solver_cpu_h_per_tile']:.2f} |")
    out.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("predict")
    p.add_argument("--run", default="runs/full/unet_T4_L_s1")
    p.add_argument("--fp32", action="store_true", help="disable bf16 autocast on GPU (the demo used bf16)")
    p.set_defaults(fn=cmd_predict)
    q = sub.add_parser("analyze")
    q.add_argument("--maps", default="maps_bf16.h5")
    q.add_argument("--tag", default="bf16")
    q.set_defaults(fn=cmd_analyze)
    a = ap.parse_args()
    t0 = time.time()
    a.fn(a)
    print(f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
