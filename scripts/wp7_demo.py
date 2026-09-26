#!/usr/bin/env python
"""WP7 — downstream many-query demonstration (docs/REVIEW_ADDENDUM_2026-09.md §WP7).

On the 20 held-out real L tiles of aux/wp7, run the best T4 surrogate across all 8 resistance tables (5 v1.0 tables +
3 extra random draws) and compare the *conclusions* a user would draw from the model route with those from the exact
Omniscape route: (a) stability of the top-q % regions across tables (pairwise IoU matrices, consensus core), (b) the
ranking of tables by their effect relative to the reference table `generic_hm`, (c) persistence of pinch points across
tables; plus the total cost of both routes.

  python scripts/wp7_demo.py fetch                                  # login node: the v1.0 T4 shards of the 20 tiles → aux/wp7/v1
  python scripts/wp7_demo.py run --run runs/full/unet_T4_L_s1       # GPU job: aux/wp7/demo_results.parquet + demo_summary.md
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WP7 = ROOT / "aux" / "wp7"
REF_TABLE = "generic_hm"
TABLES = [
    "generic_hm",
    "large_mammal",
    "amphibian",
    "forest_bird",
    "random_lm",
    "random_lm2",
    "random_lm3",
    "random_lm4",
]


def cmd_fetch(a):
    from huggingface_hub import hf_hub_download

    v1 = pd.read_parquet(WP7 / "v1_samples.parquet")
    dest = WP7 / "v1"
    for rel in sorted(set(v1.hf_path)):
        out = dest / rel
        if out.exists():
            continue
        p = hf_hub_download(
            "Xirro/AmpScape",
            rel,
            repo_type="dataset",
            revision="v1.0",
            cache_dir=str(dest / ".cache"),
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pathlib.Path(p).read_bytes())
    idx = pd.read_parquet(ROOT / "data/hf/AmpScape/index/L.parquet")
    (dest / "index").mkdir(exist_ok=True)
    idx[idx.sample_id.isin(v1.sample_id)].to_parquet(dest / "index" / "L.parquet", index=False)
    print(
        f"fetched {len(set(v1.hf_path))} T4 shard files for {v1.sample_id.nunique()} v1.0 samples → {dest}"
    )


def load_model(run: pathlib.Path):
    import torch

    from ampscape.models import build_model

    cfg = json.loads((run / "config.json").read_text())
    model = build_model(cfg["model"], cfg["input_channels"], **cfg["model_config"])
    ck = torch.load(run / "best.pt", map_location="cpu")
    model.load_state_dict(ck["model"])
    return model.eval(), cfg


def items(sel_tiles: set[str]):
    """Yield (tile_id, table_id, dataset item, solver stats) for the 8 tables of each selected tile."""
    from ampscape.data.dataset import AmpScapeDataset

    for root, kw in ((WP7 / "v1", {}), (WP7, {})):
        ds = AmpScapeDataset("T4", split=None, tier="L", root=root, qc_pass_only=False, **kw)
        for i in range(len(ds)):
            r = ds.index.iloc[i]
            d = ds[i]
            tile = d["meta"].get("tile_id")
            if tile not in sel_tiles:
                continue
            table = d["meta"].get("resistance_table_id")
            g = ds._file(r.path)[r.sample_id]["configs"][r.config]["outputs"]
            st = json.loads(g.attrs.get("solver_stats", g.attrs.get("stats", "{}")))
            yield tile, table, d, st


def top_mask(a, m, q):
    from ampscape.metrics.domain import top_q_mask

    return top_q_mask(a, m, q)


def iou(x, y):
    u = np.logical_or(x, y).sum()
    return float(np.logical_and(x, y).sum() / u) if u else float("nan")


def persistent_pinch(maps: dict, m, frac=0.5, radius=3):
    """Pixels that are a pinch point (local maximum in the top-5 %) in ≥ frac of the tables (within `radius`)."""
    from scipy import ndimage

    from ampscape.metrics.domain import pinch_points

    votes = np.zeros(m.shape, np.int32)
    for a in maps.values():
        pp = pinch_points(a, m, 5.0, 3)
        votes += ndimage.maximum_filter(pp.astype(np.uint8), size=2 * radius + 1, mode="constant")
    return votes >= max(1, int(np.ceil(frac * len(maps))))


def cmd_run(a):
    import torch

    from ampscape.metrics.pixel import rel_l2
    from ampscape.models.common import inverse_target, make_inputs

    run = pathlib.Path(a.run)
    model, cfg = load_model(run)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    stats = {"log_resistance": cfg["norm_stats"]}
    extra = tuple(cfg.get("extra_channels", []))
    sel = pd.read_parquet(WP7 / "selection.parquet")
    per_tile: dict[str, dict] = {}
    t_model = 0.0
    t_solver = 0.0
    for tile, table, d, st in items(set(sel.tile_id)):
        x = torch.from_numpy(make_inputs(d, "T4", stats, extra))[None].to(device)
        if device.type == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        with (
            torch.no_grad(),
            torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"),
        ):
            y = model(x).float()[0, 0].cpu().numpy()
        if device.type == "cuda":
            torch.cuda.synchronize()
        t_model += time.perf_counter() - t0
        t_solver += float(st.get("wall_s", 0.0))
        pred = inverse_target(y)
        truth = d["cum_current"][0].astype(np.float32)
        m = d["nodata"][0] == 0
        pred[~m] = 0
        per_tile.setdefault(tile, {"solver": {}, "model": {}, "solver_s": 0.0})
        per_tile[tile]["solver"][table] = truth
        per_tile[tile]["model"][table] = pred
        per_tile[tile]["solver_s"] += float(st.get("wall_s", 0.0))
        per_tile[tile]["mask"] = m
    rows = []
    for tile, dd in per_tile.items():
        tables = [t for t in TABLES if t in dd["solver"] and t in dd["model"]]
        if len(tables) < 4 or REF_TABLE not in tables:
            continue
        m = dd["mask"]

        # (a) stability of the top-5 % regions across tables: pairwise IoU matrices for each route
        def pair_iou(maps):
            out = np.full((len(tables), len(tables)), np.nan)
            masks = {t: top_mask(maps[t], m, 5.0) for t in tables}
            for i, ti in enumerate(tables):
                for j, tj in enumerate(tables):
                    if j > i:
                        out[i, j] = out[j, i] = iou(masks[ti], masks[tj])
            return out, masks

        S_iou, S_masks = pair_iou(dd["solver"])
        M_iou, M_masks = pair_iou(dd["model"])
        tri = np.triu_indices(len(tables), 1)
        core_S = np.sum([S_masks[t] for t in tables], axis=0) >= int(np.ceil(0.75 * len(tables)))
        core_M = np.sum([M_masks[t] for t in tables], axis=0) >= int(np.ceil(0.75 * len(tables)))
        # (b) ranking of tables by effect (rel-L2 distance to the reference table's map)
        eff_S = {
            t: rel_l2(dd["solver"][t], dd["solver"][REF_TABLE], m) for t in tables if t != REF_TABLE
        }
        eff_M = {
            t: rel_l2(dd["model"][t], dd["model"][REF_TABLE], m) for t in tables if t != REF_TABLE
        }
        order_S = sorted(eff_S, key=eff_S.get, reverse=True)
        order_M = sorted(eff_M, key=eff_M.get, reverse=True)
        from scipy.stats import spearmanr

        rank_rho = float(
            spearmanr([eff_S[t] for t in order_S], [eff_M[t] for t in order_S]).statistic
        )
        # (c) persistent pinch points (in ≥ 50 % of the tables)
        pp_S = persistent_pinch(dd["solver"], m)
        pp_M = persistent_pinch(dd["model"], m)
        from scipy import ndimage

        near_M = ndimage.maximum_filter(pp_M.astype(np.uint8), size=7, mode="constant") > 0
        near_S = ndimage.maximum_filter(pp_S.astype(np.uint8), size=7, mode="constant") > 0
        # per-table accuracy of the model against the solver (context)
        acc = {t: rel_l2(dd["model"][t], dd["solver"][t], m) for t in tables}
        rows.append(
            {
                "tile_id": tile,
                "n_tables": len(tables),
                "stability_mean_iou_solver": float(np.nanmean(S_iou[tri])),
                "stability_mean_iou_model": float(np.nanmean(M_iou[tri])),
                "stability_matrix_abs_diff": float(np.nanmean(np.abs(S_iou[tri] - M_iou[tri]))),
                "core75_iou_model_vs_solver": iou(core_M, core_S),
                "core75_frac_solver": float(core_S[m].mean()),
                "ranking_spearman": rank_rho,
                "top1_table_agree": order_S[0] == order_M[0],
                "top3_tables_agree": len(set(order_S[:3]) & set(order_M[:3])) / 3,
                "most_influential_table_solver": order_S[0],
                "most_influential_table_model": order_M[0],
                "pinch_persistent_n_solver": int(pp_S.sum()),
                "pinch_persistent_recall": float(
                    np.logical_and(pp_S, near_M).sum() / max(pp_S.sum(), 1)
                ),
                "pinch_persistent_precision": float(
                    np.logical_and(pp_M, near_S).sum() / max(pp_M.sum(), 1)
                ),
                "model_rel_l2_mean": float(np.mean(list(acc.values()))),
                "model_rel_l2_max": float(np.max(list(acc.values()))),
                "solver_seconds": dd["solver_s"],
            }
        )
    df = pd.DataFrame(rows)
    df.to_parquet(WP7 / "demo_results.parquet", index=False)
    n_maps = sum(len(v["solver"]) for v in per_tile.values())
    lines = [
        f"# WP7 — many-query demonstration: {len(df)} held-out real L tiles × {df.n_tables.max()} resistance tables, model `{run.name}` ({cfg['model']}, {cfg['n_params'] / 1e6:.1f} M params)",
        "",
        "| conclusion | solver route | model route | agreement |",
        "|---|---|---|---|",
        f"| stability of the top-5 % regions across tables (mean pairwise IoU) | {df.stability_mean_iou_solver.mean():.3f} | {df.stability_mean_iou_model.mean():.3f} | mean abs. difference of the IoU matrices {df.stability_matrix_abs_diff.mean():.3f} |",
        f"| consensus core (top-5 % in ≥ 75 % of tables), fraction of valid pixels | {df.core75_frac_solver.mean():.4f} | — | IoU model-vs-solver core {df.core75_iou_model_vs_solver.mean():.3f} (median {df.core75_iou_model_vs_solver.median():.3f}) |",
        f"| ranking of tables by effect vs `{REF_TABLE}` | — | — | Spearman {df.ranking_spearman.mean():.3f}; same most-influential table in {df.top1_table_agree.mean():.0%} of tiles; top-3 overlap {df.top3_tables_agree.mean():.2f} |",
        f"| persistent pinch points (≥ 50 % of tables) | {df.pinch_persistent_n_solver.mean():.1f} per tile | — | recall {df.pinch_persistent_recall.mean():.3f}, precision {df.pinch_persistent_precision.mean():.3f} (3-px tolerance) |",
        f"| per-map accuracy (context) | — | rel-L2 vs solver mean {df.model_rel_l2_mean.mean():.3f}, worst table {df.model_rel_l2_max.mean():.3f} | |",
        f"| total cost for {n_maps} maps | {t_solver / 3600:.1f} CPU-h ({t_solver / n_maps:.0f} s per map, 1 core) | {t_model:.1f} s on one GPU ({t_model / n_maps * 1000:.0f} ms per map) + training once | ×{t_solver / max(t_model, 1e-9):.0f} |",
        "",
        "Per-tile rows: `aux/wp7/demo_results.parquet`. Tables: the four expert tables, the v1.0 per-tile `random_lm` draw and",
        "three extra random draws (`random_lm2..4`, aux/wp7). Solver times are the recorded Omniscape wall times (CHOLMOD, 1 core).",
    ]
    (WP7 / "demo_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch").set_defaults(func=cmd_fetch)
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.set_defaults(func=cmd_run)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
