#!/usr/bin/env python
"""v1.0 real-tile stream (dataset plan §2.1, §5): stratified, grid-fitting tile centres per tier from the v1.0 seeds,
prefix extraction, and the five resistance rasters per tile (4 expert tables + a per-tile `random_lm`).

Steps (login node; extraction is network-bound):
  sample   python scripts/build_v1_tiles.py sample  --out data/tiles/v1 --tiers S M XXL
  extract  python scripts/build_v1_tiles.py extract --out data/tiles/v1 --tier S --first-accepted 240
  resist   python scripts/build_v1_tiles.py resist  --out data/tiles/v1
  parents  python scripts/build_v1_tiles.py parents --out data/tiles/v1        # provisional XXL assignment regions
The selected lists are the full v1.0 tile counts (S 8 000, M 4 000, L 1 600, XL 320, XXL 32) so that every later
extraction of more tiles continues the same stream.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
V1_SPLIT_SEED = 20260906
TIER_TILE_SEED = {t: V1_SPLIT_SEED * 10 + k for k, t in enumerate(["S", "M", "L", "XL", "XXL", "XXL_strict"], start=1)}
V1_TILES = {"S": 8000, "M": 4000, "L": 1600, "XL": 320, "XXL": 32, "XXL_strict": 6}
TIER_GEOM = {"S": (128, 100.0), "M": (256, 100.0), "L": (512, 200.0), "XL": (1024, 500.0), "XXL": (2048, 1000.0), "XXL_strict": (2048, 1000.0)}
CANDIDATES = {"S": 60000, "M": 30000, "L": 15000, "XL": 6000, "XXL": 3000, "XXL_strict": 20000}


def cmd_sample(a):
    for tier in a.tiers:
        size, pm = TIER_GEOM[tier]
        out = pathlib.Path(a.out) / "specs" / tier
        if (out / "tile_specs.json").exists() and not a.force:
            print(f"{tier}: specs exist, skipping")
            continue
        strict = tier == "XXL_strict"
        cmd = [sys.executable, str(ROOT / "scripts/sample_tiles.py"), "--out", str(out), "--n", str(V1_TILES[tier]), "--reserve", "6" if strict else "0",
               "--candidates", str(CANDIDATES[tier]), "--seed", str(TIER_TILE_SEED[tier]), "--tier", "XXL" if strict else tier, "--size", str(size),
               "--pixel-m", str(pm), "--min-biomes", "1" if strict else ("3" if tier == "XXL" else "5")]
        if strict:
            cmd += ["--strict-cells", str(ROOT / "configs/splits/cell_assignment_v1.json")]   # test_ood_scale_strict
        elif tier != "XXL":
            cmd.append("--grid-fit")      # XXL tiles are test-only and not cell-fitted (owner decision 2026-09-14)
        print(" ".join(cmd))
        subprocess.run(cmd, check=True)


def cmd_extract(a):
    cmd = [sys.executable, str(ROOT / "scripts/extract_tiles.py"), "--specs", str(pathlib.Path(a.out) / "specs" / a.tier), "--out", a.out,
           "--workers", str(a.workers), "--first-accepted", str(a.first_accepted), "--per-specs-manifest"]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def tile_random_seed(tile_id: str) -> int:
    return int(hashlib.sha1(f"random_lm|{tile_id}".encode()).hexdigest()[:8], 16) % (2**31 - 1)


def cmd_resist(a):
    import numpy as np
    import pandas as pd
    import rasterio

    from ampscape.landscapes.real import read_tile
    from ampscape.resistance import apply_table, load_tables, perturb_table

    tables = {k: v for k, v in load_tables(ROOT / "configs/resistance_tables").items() if not k.startswith("random")}
    out = pathlib.Path(a.out)
    tiles = pd.read_parquet(out / "tiles.parquet")
    tiles = tiles[tiles.qc_accept].reset_index(drop=True)
    rp = out / "resistance.parquet"
    done = pd.read_parquet(rp) if rp.exists() else pd.DataFrame()
    have = set(zip(done.tile_id, done.table_id, strict=True)) if len(done) else set()
    rows = list(done.to_dict("records")) if len(done) else []
    n_new = 0
    for _, row in tiles.iterrows():
        todo = {tid: t for tid, t in tables.items() if (row.tile_id, tid) not in have}
        if (row.tile_id, "random_lm") not in have:
            seed = tile_random_seed(row.tile_id)
            todo["random_lm"] = perturb_table(tables["large_mammal"], seed=seed, log_sd=0.5, table_id="random_lm")
        if not todo:
            continue
        cov, _ = read_tile(str(out / row.path))
        with rasterio.open(out / row.path) as src:
            profile = src.profile
        for tid, t in todo.items():
            r, nd, stats = apply_table(t, cov)
            p = out / "resistance" / tid / f"{row.tile_id}.tif"
            p.parent.mkdir(parents=True, exist_ok=True)
            prof = dict(profile, count=2, dtype="float32", nodata=None, compress="deflate", predictor=2)
            tags = dict(tile_id=row.tile_id, table_id=tid, table_version=t.version, table_sha256=t.sha256 or "", r_max=t.r_max)
            if tid == "random_lm":
                tags["random"] = json.dumps(t.random)
            with rasterio.open(p, "w", **prof) as dst:
                dst.write(r, 1)
                dst.write(nd.astype(np.float32), 2)
                dst.set_band_description(1, "resistance")
                dst.set_band_description(2, "nodata_mask")
                dst.update_tags(**tags)
            rows.append({"tile_id": row.tile_id, "table_id": tid, "table_version": t.version, "table_sha256": t.sha256,
                         "random_seed": t.random["seed"] if tid == "random_lm" else None, "path": str(p.relative_to(out)), **stats,
                         "created_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")})
            n_new += 1
    pd.DataFrame(rows).to_parquet(rp, index=False)
    print(f"resistance rasters: {n_new} new, {len(rows)} total ({len(tiles)} tiles × 5 tables)")


def cmd_merge(a):
    """Merge the per-tier manifests (tiles_<tier>.parquet) into tiles.parquet (accepted order preserved per tier)."""
    import pandas as pd

    out = pathlib.Path(a.out)
    parts = sorted(out.glob("tiles_*.parquet"))
    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    if "strict" not in df:
        df["strict"] = False
    df["strict"] = df["strict"].fillna(False).astype(bool)
    df.to_parquet(out / "tiles.parquet", index=False)
    acc = df[df.qc_accept]
    print(f"merged {len(parts)} manifests: {len(df)} rows, {len(acc)} accepted;", acc.groupby("tier").size().to_dict(), "| strict:", int(acc.strict.sum()))


def cmd_parents(a):
    import pandas as pd

    specs = json.loads((pathlib.Path(a.out) / "specs" / "XXL" / "tile_specs.json").read_text())
    sel = specs["selected"][: V1_TILES["XXL"]]
    df = pd.DataFrame([{"tile_id": s["tile_id"], "tier": "XXL", "lat": s["lat"], "lon": s["lon"], "size": s["size"], "pixel_m": s["pixel_m"],
                        "realm": s["stratum"]["realm"], "biome_num": s["stratum"]["biome_num"], "biome_name": s["stratum"]["biome_name"]}
                       for s in sel])
    df.to_parquet(pathlib.Path(a.out) / "parents.parquet", index=False)
    print(f"{len(df)} provisional XXL parents written (assignment regions frozen for every tier)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--out", required=True); s.add_argument("--tiers", nargs="+", default=["S", "M", "XXL"]); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_sample)
    e = sub.add_parser("extract"); e.add_argument("--out", required=True); e.add_argument("--tier", required=True); e.add_argument("--first-accepted", type=int, required=True); e.add_argument("--workers", type=int, default=4); e.set_defaults(fn=cmd_extract)
    r = sub.add_parser("resist"); r.add_argument("--out", required=True); r.set_defaults(fn=cmd_resist)
    mg = sub.add_parser("merge"); mg.add_argument("--out", required=True); mg.set_defaults(fn=cmd_merge)
    p = sub.add_parser("parents"); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_parents)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
