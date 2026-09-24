#!/usr/bin/env python
"""Tile the published resistance surfaces into data/tiles/published/{tier}/*.tif + published_tiles.parquet.

python scripts/tile_published.py --out data/tiles/published --max-per-source 30 [--tiers S] [--include-xxl]
"""

from __future__ import annotations

import argparse
import json
import pathlib

import pandas as pd

from ampscape.landscapes.published import (
    SOURCES,
    extract_published_tile,
    nearest_tier,
    tile_centres,
    tile_id,
    write_tile,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/tiles/published")
    ap.add_argument("--max-per-source", type=int, default=30)
    ap.add_argument("--max-xxl", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20260913)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    rows = []
    for src in SOURCES:
        import rasterio

        with rasterio.open(src.path) as ds:
            native = float(ds.res[0])
        tier = nearest_tier(native)
        cap = a.max_xxl if tier == "XXL" else a.max_per_source
        n_ok = 0
        for lat, lon in tile_centres(src, tier, max_tiles=None, seed=a.seed):
            if n_ok >= cap:
                break
            res = extract_published_tile(src, lat, lon, tier)
            if res is None:
                continue
            R, nd, grid, prov = res
            tid = tile_id(src, tier, lat, lon)
            p = out / "tiles" / tier / f"{tid}.tif"
            sha = write_tile(str(p), R, nd, grid, prov)
            rows.append(
                {
                    "tile_id": tid,
                    "source_id": src.source_id,
                    "tier": tier,
                    "size": R.shape[0],
                    "pixel_m": prov["pixel_size_m"],
                    "lat": lat,
                    "lon": lon,
                    "epsg": grid.epsg,
                    "path": str(p.relative_to(out)),
                    "sha256": sha,
                    "provenance": json.dumps(prov),
                    "doi": src.doi,
                    "license": src.license,
                    "r_min": prov["r_min"],
                    "r_max": prov["r_max"],
                    "nodata_frac": prov["nodata_frac"],
                }
            )
            n_ok += 1
        print(f"{src.source_id}: native {native} m -> tier {tier}: {n_ok} tiles")
    df = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "published_tiles.parquet", index=False)
    print(
        df.groupby(["source_id", "tier"])
        .agg(n=("tile_id", "size"), r_max=("r_max", "max"), nodata=("nodata_frac", "mean"))
        .to_string()
    )


if __name__ == "__main__":
    main()
