#!/usr/bin/env python
"""WP7 (many-query demonstration) — the solver side, on CPU while the GPU baselines train.

Selects 20 held-out real L tiles (split test_id, every table's T4 row QC-pass in v1.0), adds three extra random
resistance tables per tile (`random_lm2..4`, seeded like the v1.0 `random_lm` draw), and builds `aux/wp7/` so that the
Omniscape (T4) targets of the extra draws can be solved with the production pipeline (the five v1.0 tables of these
tiles already have exact T4 targets on the Hub). The demo then compares, per tile across the 8 tables, the conclusions
drawn from the best T4 surrogate with those from the solver (docs/REVIEW_ADDENDUM_2026-09.md §WP7).

  python scripts/wp7_prepare.py select   [--n 20]              # writes aux/wp7/selection.parquet
  python scripts/wp7_prepare.py build                          # tiles root aux/wp7/tiles + extra random rasters + manifest
  # then, under Slurm: generate.py prepare / submit --configs omniscape on aux/wp7 (see docs/phase10_full_schedule.md)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "aux" / "wp7"
TILES_V1 = ROOT / "data" / "tiles" / "v1.0"
EXTRA_TABLES = ["random_lm2", "random_lm3", "random_lm4"]


def extra_seed(table_id: str, tile_id: str) -> int:
    return int(hashlib.sha1(f"{table_id}|{tile_id}".encode()).hexdigest()[:8], 16) % (2**31 - 1)


def cmd_select(a):
    idx = pd.read_parquet(ROOT / "data" / "hf" / "AmpScape" / "index" / "L.parquet")
    t4 = idx[(idx.config == "omniscape") & (idx.family == "real") & (idx.split == "test_id")]
    ok = t4.groupby("tile_id").agg(
        n=("sample_id", "size"),
        qc=("qc_pass", "all"),
        realm=("realm", "first"),
        biome=("biome_num", "first"),
    )
    ok = ok[(ok.n == 5) & ok.qc].reset_index()
    # round-robin over realms for spread, deterministic order
    ok = ok.sort_values(["realm", "tile_id"]).reset_index(drop=True)
    picked, k = [], 0
    realms = list(ok.realm.unique())
    while len(picked) < a.n and k < len(ok):
        for r in realms:
            cand = ok[(ok.realm == r) & (~ok.tile_id.isin(picked))]
            if len(cand):
                picked.append(cand.tile_id.iloc[0])
            if len(picked) >= a.n:
                break
        k += 1
    sel = ok[ok.tile_id.isin(picked)].copy()
    samples = t4[t4.tile_id.isin(picked)][
        ["sample_id", "tile_id", "resistance_table_id", "hf_path", "qc_pass"]
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    sel.to_parquet(OUT / "selection.parquet", index=False)
    samples.to_parquet(OUT / "v1_samples.parquet", index=False)
    print(
        f"{len(sel)} tiles: realms {sel.realm.value_counts().to_dict()}; {len(samples)} existing v1.0 T4 samples"
    )


def cmd_build(a):
    import rasterio

    from ampscape.landscapes.real import read_tile
    from ampscape.resistance import apply_table, load_tables, perturb_table
    from ampscape.solve.manifest import SampleSpec, sample_uuid, to_frame
    from ampscape.solve.plan_v1 import TIER_PIXEL_M, TIER_SIZES, stable_seed

    sel = pd.read_parquet(OUT / "selection.parquet")
    tiles = pd.read_parquet(TILES_V1 / "tiles.parquet")
    tiles = tiles[tiles.tile_id.isin(sel.tile_id)].reset_index(drop=True)
    res = pd.read_parquet(TILES_V1 / "resistance.parquet")
    res = res[res.tile_id.isin(sel.tile_id)].reset_index(drop=True)
    troot = OUT / "tiles"
    troot.mkdir(parents=True, exist_ok=True)
    for p in list(tiles.path) + list(
        res.path
    ):  # tile covariates + the five v1.0 rasters (paths relative to the root)
        dst = troot / p
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(TILES_V1 / p, dst)
    tiles.to_parquet(troot / "tiles.parquet", index=False)
    tables = {
        k: v
        for k, v in load_tables(ROOT / "configs/resistance_tables").items()
        if not k.startswith("random")
    }
    rows = list(res.to_dict("records"))
    for _, row in tiles.iterrows():
        cov, _ = read_tile(str(troot / row.path))
        with rasterio.open(troot / row.path) as src:
            profile = src.profile
        for tid in EXTRA_TABLES:
            seed = extra_seed(tid, row.tile_id)
            t = perturb_table(tables["large_mammal"], seed=seed, log_sd=0.5, table_id=tid)
            r, nd, stats = apply_table(t, cov)
            p = troot / "resistance" / tid / f"{row.tile_id}.tif"
            p.parent.mkdir(parents=True, exist_ok=True)
            prof = dict(
                profile, count=2, dtype="float32", nodata=None, compress="deflate", predictor=2
            )
            with rasterio.open(p, "w", **prof) as dst:
                dst.write(r, 1)
                dst.write(nd.astype(np.float32), 2)
                dst.update_tags(
                    tile_id=row.tile_id,
                    table_id=tid,
                    table_version=t.version,
                    table_sha256=t.sha256 or "",
                    r_max=t.r_max,
                    random=json.dumps(t.random),
                )
            rows.append(
                {
                    "tile_id": row.tile_id,
                    "table_id": tid,
                    "table_version": t.version,
                    "table_sha256": t.sha256,
                    "random_seed": seed,
                    "path": str(p.relative_to(troot)),
                    **stats,
                    "created_utc": pd.Timestamp.utcnow().isoformat(),
                }
            )
    pd.DataFrame(rows).to_parquet(troot / "resistance.parquet", index=False)
    # manifest: the extra draws only (T4 config), 4 landscapes per shard
    specs, j = [], 0
    for tile in sorted(sel.tile_id):
        for tid in EXTRA_TABLES:
            specs.append(
                SampleSpec(
                    sample_uuid("wp7", "real", f"L:{tile}:{tid}"),
                    "wp7",
                    "real",
                    "L",
                    TIER_SIZES["L"],
                    TIER_PIXEL_M["L"],
                    stable_seed(f"{tile}|{tid}"),
                    json.dumps(["omniscape"]),
                    tile_id=tile,
                    table_id=tid,
                    shard=j // 4,
                    extra=json.dumps({"design": "wp7", "wp7": "extra random table"}),
                )
            )
            j += 1
    df = to_frame(specs)
    df["split"] = "test_id"
    df["cg_baseline"] = False
    df.to_parquet(OUT / "manifest.parquet", index=False)
    base = json.loads((ROOT / "data/v1/L/build.json").read_text())
    base.update(
        {
            "dataset_id": "wp7",
            "design": "wp7-many-tables",
            "n": len(df),
            "n_synthetic": 0,
            "n_real": len(df),
            "n_tiles": int(sel.tile_id.nunique()),
            "shard_size": 4,
            "pilot": str(troot.relative_to(ROOT)),
            "dataset_version": "1.0.0-wp7",
        }
    )
    (OUT / "build.json").write_text(json.dumps(base, indent=1))
    print(
        f"wp7 build: {len(df)} extra-draw landscapes in {df.shard.nunique()} shards; tiles root {troot} ({len(rows)} rasters)"
    )


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--n", type=int, default=20)
    s.set_defaults(func=cmd_select)
    b = sub.add_parser("build")
    b.set_defaults(func=cmd_build)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
