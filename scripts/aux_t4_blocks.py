#!/usr/bin/env python
"""Auxiliary T4 block-size runs (review addendum WP1: block_size = 1 reference; WP2: block-size Pareto rows).

  select  --tier M --build data/v1/M --out aux/t4_bs1_reference/M --n-per-split 100 --splits test_id,test_ood,ood_region
  prepare --out aux/t4_bs1_reference/M --block 1 [--correct-artifacts 1] [--shard-size 12]
          -> aux build with inputs whose `omni_block_size` (and `omni_correct_artifacts`) attrs are overridden;
             solve with `python scripts/generate.py submit --build <out> --configs omniscape [--time ...]`
  compare --out aux/t4_bs1_reference/M --tier M
          -> production T4 map (Hub task-group file of the sample's production shard) vs the aux map:
             rel-L2, log10-ε MAE, top-1/5/10 IoU, pinch-point recall, Spearman, non-source rel-L2, solve times;
             writes <out>/index.parquet (keyed by sample_id) and <out>/summary.{json,md}
The selection is deterministic (manifest order within each split) and restricted to samples whose production shard
is already validated and uploaded, so re-running `select` later tops up splits that were not yet generated.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile

import h5py
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cmd_select(a):
    build = pathlib.Path(a.build)
    man = pd.read_parquet(build / "manifest.parquet")
    up = {int(p.stem.split("-")[1]) for p in (build / "shards").glob("shard-*.uploaded")}
    avail = man[man.shard.isin(up) & man.configs.str.contains("omniscape")]
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prev = (
        pd.read_parquet(out / "selection.parquet") if (out / "selection.parquet").exists() else None
    )
    rows = []
    for split in a.splits.split(","):
        have = prev[prev.split == split] if prev is not None else None
        n_have = 0 if have is None else len(have)
        cand = avail[avail.split == split]
        if prev is not None:
            cand = cand[~cand.sample_id.isin(prev.sample_id)]
        take = cand.sort_values(["shard", "sample_id"]).head(max(0, a.n_per_split - n_have))
        rows.append(take)
        print(f"{split}: {n_have} already, {len(take)} added ({len(cand)} available)")
    sel = pd.concat(([prev] if prev is not None else []) + rows, ignore_index=True)
    sel.to_parquet(out / "selection.parquet", index=False)
    print(f"selection: {len(sel)} samples ->", out / "selection.parquet")


def cmd_prepare(a):
    from ampscape.solve.manifest import from_frame
    from ampscape.solve.prepare import prepare_shard
    from ampscape.sources import SourceConfig

    out = pathlib.Path(a.out)
    sel = pd.read_parquet(out / "selection.parquet")
    src_build = (
        pathlib.Path(
            json.loads((out / "selection.parquet").with_name("source_build.json").read_text())[
                "build"
            ]
        )
        if (out / "source_build.json").exists()
        else None
    )
    cfg_src = json.loads((pathlib.Path(a.build) / "build.json").read_text())
    sel = sel.copy()
    sel["shard"] = np.arange(len(sel)) // a.shard_size
    sel["configs"] = json.dumps(["omniscape"])
    sel["cg_baseline"] = False
    sel.to_parquet(out / "manifest.parquet", index=False)
    cfg = dict(
        cfg_src,
        dataset_version=f"aux-block{a.block}-ca{a.correct_artifacts}",
        aux={
            "block_size": a.block,
            "correct_artifacts": a.correct_artifacts,
            "source_build": str(a.build),
        },
        shard_size=a.shard_size,
    )
    (out / "build.json").write_text(json.dumps(cfg, indent=1))
    scfg = SourceConfig.from_yaml(ROOT / cfg["source_config"])
    for sh in sorted(sel.shard.unique()):
        specs = from_frame(sel[sel.shard == sh])
        p = out / "inputs" / f"shard-{sh:05d}.inputs.h5"
        prepare_shard(specs, str(p), scfg, pilot_root=str(ROOT / cfg["pilot"]), overwrite=True)
        with h5py.File(p, "a") as f:
            for sid in f["samples"]:
                f["samples"][sid].attrs["omni_block_size"] = int(a.block)
                f["samples"][sid].attrs["omni_correct_artifacts"] = int(a.correct_artifacts)
        print(
            f"shard {sh}: {len(specs)} inputs, block {a.block}, correct_artifacts {a.correct_artifacts}"
        )


def _production_maps(
    tier: str, shard_name: str, cache: pathlib.Path, repo: str
) -> dict[str, tuple[np.ndarray, float, int, int]]:
    """{sample_id: (cum_current, solve_time_s, block, radius)} from the Hub T4 task-group file of a production shard."""
    from huggingface_hub import hf_hub_download

    p = hf_hub_download(
        repo, f"data/{tier}/T4/{shard_name}", repo_type="dataset", cache_dir=str(cache)
    )
    out = {}
    with h5py.File(p, "r") as f:
        for sid in f:
            g = f[sid]["configs"]["omniscape"]
            st = json.loads(g["outputs"].attrs["solver_stats"])
            sp = st.get("solver_params", {})
            out[sid] = (
                g["outputs"]["cum_current"][...],
                float(st["wall_s"]),
                int(sp.get("block_size", 0)),
                int(sp.get("radius", 0)),
            )
    return out


def cmd_compare(a):
    from ampscape.metrics import domain, nonsource, pixel

    out = pathlib.Path(a.out)
    sel = pd.read_parquet(out / "manifest.parquet")
    cfg = json.loads((out / "build.json").read_text())
    src_build = pathlib.Path(cfg["aux"]["source_build"])
    prod_man = (
        pd.read_parquet(src_build / "manifest.parquet", columns=["sample_id", "shard"])
        .set_index("sample_id")
        .shard.to_dict()
    )
    cache = pathlib.Path(tempfile.mkdtemp(prefix="aux_cmp_", dir=str(out)))
    rows = []
    try:
        by_shard: dict[str, list[str]] = {}
        for sid in sel.sample_id:
            by_shard.setdefault(f"shard-{int(prod_man[sid]):05d}.h5", []).append(sid)
        aux_maps = {}
        for o in sorted((out / "outputs").glob("shard-*.outputs.h5")):
            with h5py.File(o, "r") as f:
                for sid in f["samples"]:
                    g = f["samples"][sid]
                    if "outputs" in g and "omniscape" in g["outputs"]:
                        st = json.loads(g["outputs"]["omniscape"].attrs["stats"])
                        aux_maps[sid] = (
                            g["outputs"]["omniscape"]["cum_current"][...],
                            float(st["wall_s"]),
                        )
        for shard_name, sids in sorted(by_shard.items()):
            prod = _production_maps(a.tier, shard_name, cache, a.repo)
            ip = None
            for sid in sids:
                if sid not in aux_maps or sid not in prod:
                    continue
                t_prod, tp, bp, rp = prod[sid]
                t_aux, ta = aux_maps[sid]
                # inputs (nodata + source strength) from the aux inputs file
                sh = int(sel[sel.sample_id == sid].shard.iloc[0])
                with h5py.File(out / "inputs" / f"shard-{sh:05d}.inputs.h5", "r") as fi:
                    g = fi["samples"][sid]
                    nd = g["inputs"]["nodata_mask"][...] > 0
                    S = g["configs"]["omniscape"]["source_strength"][...]
                m = ~nd
                # reference = the aux map (block 1 when this is the bs1 reference); "prediction" = the production map
                pix = pixel.all_pixel(t_prod, t_aux, m)
                dom = domain.all_domain(t_prod, t_aux, m)
                ns = nonsource.all_nonsource(
                    t_prod, t_aux, nonsource.nonsource_mask("omniscape", m, source_strength=S), m
                )
                r = sel[sel.sample_id == sid].iloc[0]
                rows.append(
                    {
                        "sample_id": sid,
                        "split": r.split,
                        "family": r.family,
                        "generator": r.generator,
                        "contrast": r.contrast,
                        "prod_block": bp,
                        "prod_radius": rp,
                        "aux_block": cfg["aux"]["block_size"],
                        "aux_correct_artifacts": cfg["aux"]["correct_artifacts"],
                        "prod_solve_s": tp,
                        "aux_solve_s": ta,
                        "rel_l2": pix["rel_l2"],
                        "mae_log10eps": pix["mae_log10eps"],
                        "top1_iou": dom["top1_iou"],
                        "top5_iou": dom["top5_iou"],
                        "top10_iou": dom["top10_iou"],
                        "pinch_recall": dom["pinch_recall"],
                        "spearman": dom["spearman"],
                        "ns_rel_l2": ns["ns_rel_l2"],
                        "ns_top5_iou": ns["ns_top5_iou"],
                        "max_diff_over_max": float(
                            np.nanmax(np.abs(t_prod[m] - t_aux[m]))
                            / max(np.nanmax(t_aux[m]), 1e-30)
                        ),
                    }
                )
    finally:
        shutil.rmtree(cache, ignore_errors=True)
    df = pd.DataFrame(rows)
    df.to_parquet(out / "index.parquet", index=False)
    keys = [
        "rel_l2",
        "mae_log10eps",
        "top1_iou",
        "top5_iou",
        "top10_iou",
        "pinch_recall",
        "spearman",
        "ns_rel_l2",
        "ns_top5_iou",
        "max_diff_over_max",
    ]
    summ = df.groupby("split")[keys].agg(["mean", "median", "max"]).round(4)
    times = df.groupby("split")[["prod_solve_s", "aux_solve_s"]].median().round(1)
    lines = [
        f"# {out.name}: production T4 (block {df.prod_block.iloc[0] if len(df) else '?'}) vs aux block {cfg['aux']['block_size']} "
        f"(correct_artifacts={cfg['aux']['correct_artifacts']}) — tier {a.tier}, {len(df)} samples",
        "",
        "| split | n | "
        + " | ".join(f"{k} mean / median / max" for k in keys)
        + " | prod s | aux s |",
        "|---|---|" + "---|" * len(keys) + "---|---|",
    ]
    for split, g in df.groupby("split"):
        cells = [f"{g[k].mean():.4f} / {g[k].median():.4f} / {g[k].max():.4f}" for k in keys]
        lines.append(
            f"| {split} | {len(g)} | "
            + " | ".join(cells)
            + f" | {g.prod_solve_s.median():.0f} | {g.aux_solve_s.median():.0f} |"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    (out / "summary.json").write_text(
        json.dumps(
            {
                "n": len(df),
                "per_split": {
                    s: {
                        k: {
                            "mean": float(g[k].mean()),
                            "median": float(g[k].median()),
                            "max": float(g[k].max()),
                        }
                        for k in keys
                    }
                    | {
                        "prod_solve_s_median": float(g.prod_solve_s.median()),
                        "aux_solve_s_median": float(g.aux_solve_s.median()),
                    }
                    for s, g in df.groupby("split")
                },
            },
            indent=1,
        )
    )
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--tier", required=True)
    s.add_argument("--build", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--n-per-split", type=int, default=100)
    s.add_argument("--splits", default="test_id,test_ood,ood_region")
    s.set_defaults(fn=cmd_select)
    p = sub.add_parser("prepare")
    p.add_argument("--out", required=True)
    p.add_argument("--build", required=True)
    p.add_argument("--block", type=int, required=True)
    p.add_argument("--correct-artifacts", type=int, default=1)
    p.add_argument("--shard-size", type=int, default=12)
    p.set_defaults(fn=cmd_prepare)
    c = sub.add_parser("compare")
    c.add_argument("--out", required=True)
    c.add_argument("--tier", required=True)
    c.add_argument("--repo", default="Xirro/AmpScape")
    c.set_defaults(fn=cmd_compare)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
