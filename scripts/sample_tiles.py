#!/usr/bin/env python
"""Stratified sampling of real-tile centres (brief §4.2).

Draws uniform-on-sphere land points, joins RESOLVE biome/realm, samples gHM, assigns gHM
terciles, and balances across biome × realm × tercile strata. Writes:
  <out>/candidates.parquet   all attributed candidates (for resampling rejected tiles)
  <out>/tile_specs.json      the selected tiles + a reserve list, plus tercile edges and seed

Usage (login node, needs data/sources unzipped):
  python scripts/sample_tiles.py --out data/tiles/pilot --n 50 --reserve 100 --seed 20260905 \
      --realms Nearctic Neotropic Afrotropic Australasia Oceania Palearctic --grip-regions 1 2 3 5 7
"""

from __future__ import annotations

import argparse
import json
import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd

from ampscape.landscapes import sampling


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="data/sources")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--reserve", type=int, default=100)
    ap.add_argument("--candidates", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=20260905)
    ap.add_argument("--realms", nargs="*", default=None)
    ap.add_argument(
        "--grip-regions",
        nargs="*",
        type=int,
        default=None,
        help="only keep candidates whose GRIP4 region file is downloaded",
    )
    ap.add_argument("--min-biomes", type=int, default=5)
    ap.add_argument("--tier", default="S")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--pixel-m", type=float, default=100.0)
    ap.add_argument(
        "--grid-fit",
        action="store_true",
        help="drop candidates whose tile straddles two split macro-cells (v1.0 rule)",
    )
    ap.add_argument("--band-deg", type=float, default=20.0)
    ap.add_argument(
        "--strict-cells",
        default=None,
        help="frozen cell assignment JSON: keep only candidates whose whole footprint lies in test_id cells "
        "(snapping into the interior box of the candidate's own test cell); test_ood_scale_strict",
    )
    args = ap.parse_args()

    src = pathlib.Path(args.sources)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    eco = gpd.read_file(src / "Ecoregions2017" / "Ecoregions2017.shp")
    pts = sampling.sample_land_points(eco, args.candidates, rng)
    if args.realms:
        pts = pts[pts["REALM"].isin(args.realms)].reset_index(drop=True)
    ghm_path = next((src / "gHM").rglob("gHM.tif"))
    pts["ghm"] = sampling.sample_ghm(str(ghm_path), pts["lat"].to_numpy(), pts["lon"].to_numpy())
    pts = pts[np.isfinite(pts["ghm"])].reset_index(drop=True)
    terc, edges = sampling.assign_terciles(pts["ghm"].to_numpy())
    pts["ghm_tercile"] = terc
    pts["grip_region"] = [
        sampling.grip_region(r, la, lo)
        for r, la, lo in zip(pts["REALM"], pts["lat"], pts["lon"], strict=True)
    ]
    if args.grip_regions:
        pts = pts[pts["grip_region"].isin(args.grip_regions)].reset_index(drop=True)
    if args.grid_fit:
        # v1.0 rule (dataset plan §5 iv): a tile must sit inside one split macro-cell. Candidates that straddle are
        # snapped to the nearest centre of the cell's interior box (matters for XL/XXL, whose footprints are a
        # large fraction of a cell), re-attributed (ecoregion, gHM) at the new centre, and dropped if that fails.
        from shapely.geometry import Point

        from ampscape.splits.spatial import BlockGrid

        grid = BlockGrid(args.band_deg, equal_width=True)
        half = args.size * args.pixel_m / 2.0
        lat2, lon2, moved = [], [], []
        for la, lo in zip(pts["lat"], pts["lon"], strict=True):
            la, lo = float(la), float(lo)
            if grid.fits(la, lo, half):
                lat2.append(la)
                lon2.append(lo)
                moved.append(False)
                continue
            box = grid.interior_bounds(grid.block_id(la, lo), half)
            if box is None:
                lat2.append(np.nan)
                lon2.append(np.nan)
                moved.append(True)
                continue
            la2, lo2 = min(max(la, box[0]), box[1]), min(max(lo, box[2]), box[3])
            ok = grid.fits(la2, lo2, half)
            lat2.append(la2 if ok else np.nan)
            lon2.append(lo2 if ok else np.nan)
            moved.append(True)
        moved = np.array(moved)
        pts["lat"], pts["lon"] = lat2, lon2
        pts = pts[np.isfinite(pts["lat"])].reset_index(drop=True)
        moved = moved[np.isfinite(np.array(lat2))]
        if moved.any():
            mv = pts[moved].copy()
            mv = gpd.GeoDataFrame(
                mv[["lat", "lon", "ghm"]],
                geometry=[Point(x, y) for x, y in zip(mv["lon"], mv["lat"], strict=True)],
                crs="EPSG:4326",
            )
            keep_cols = ["ECO_ID", "ECO_NAME", "BIOME_NUM", "BIOME_NAME", "REALM", "geometry"]
            ecoj = eco[keep_cols]
            ecoj = ecoj[
                (ecoj["REALM"] != "Antarctica")
                & (ecoj["BIOME_NUM"] != 98)
                & (ecoj["BIOME_NUM"] != 99)
            ]
            rej = gpd.sjoin(mv, ecoj, how="inner", predicate="within")
            rej = rej[~rej.index.duplicated()]
            rej["ghm"] = sampling.sample_ghm(
                str(ghm_path), rej["lat"].to_numpy(), rej["lon"].to_numpy()
            )
            rej = rej[np.isfinite(rej["ghm"])]
            pts = pd.concat(
                [pts[~moved], rej.drop(columns=["index_right"], errors="ignore")], ignore_index=True
            )
            pts["ghm_tercile"] = sampling.assign_terciles(pts["ghm"].to_numpy(), edges)[0]
            pts["grip_region"] = [
                sampling.grip_region(r, la, lo)
                for r, la, lo in zip(pts["REALM"], pts["lat"], pts["lon"], strict=True)
            ]
            if args.grip_regions:
                pts = pts[pts["grip_region"].isin(args.grip_regions)].reset_index(drop=True)
        print(
            f"grid-fit: {int((~moved).sum())} candidates fit as drawn, {int(moved.sum())} snapped into a cell's interior box "
            f"and re-attributed, {len(pts)} kept"
        )

    if args.strict_cells:
        from ampscape.splits.spatial import BlockGrid

        assign = json.loads(pathlib.Path(args.strict_cells).read_text())["assignment"]
        grid = BlockGrid(args.band_deg, equal_width=True)
        half = args.size * args.pixel_m / 2.0
        keep_lat, keep_lon, keep = [], [], []
        for la, lo in zip(pts["lat"], pts["lon"], strict=True):
            la, lo = float(la), float(lo)
            blocks = grid.footprint_blocks(la, lo, half)
            if all(assign.get(b) == "test_id" for b in blocks):
                keep_lat.append(la)
                keep_lon.append(lo)
                keep.append(True)
                continue
            own = grid.block_id(la, lo)
            box = grid.interior_bounds(own, half) if assign.get(own) == "test_id" else None
            if box is not None:
                la2, lo2 = min(max(la, box[0]), box[1]), min(max(lo, box[2]), box[3])
                if all(assign.get(b) == "test_id" for b in grid.footprint_blocks(la2, lo2, half)):
                    keep_lat.append(la2)
                    keep_lon.append(lo2)
                    keep.append(True)
                    continue
            keep_lat.append(la)
            keep_lon.append(lo)
            keep.append(False)
        pts["lat"], pts["lon"] = keep_lat, keep_lon
        pts = pts[np.array(keep)].reset_index(drop=True)
        print(
            f"strict-cells: {len(pts)} candidates fit entirely inside test_id cells "
            f"(cells: {sorted({grid.block_id(a, b) for a, b in zip(pts['lat'], pts['lon'], strict=True)})})"
        )
    cands = [
        sampling.Candidate(
            float(r.lat),
            float(r.lon),
            int(r.BIOME_NUM),
            str(r.BIOME_NAME),
            str(r.REALM),
            int(r.ECO_ID),
            str(r.ECO_NAME),
            float(r.ghm),
            int(r.ghm_tercile),
            None if r.grip_region is None or np.isnan(r.grip_region) else int(r.grip_region),
        )
        for r in pts.itertuples()
    ]
    chosen = sampling.balance_strata(cands, args.n + args.reserve, rng, min_biomes=args.min_biomes)
    selected, reserve = chosen[: args.n], chosen[args.n :]

    def spec(i: int, c: sampling.Candidate) -> dict:
        return {
            "tile_id": f"{args.tier}_{c.realm[:3].lower()}_b{c.biome_num:02d}_{i:04d}",
            "lat": c.lat,
            "lon": c.lon,
            "tier": args.tier,
            "size": args.size,
            "pixel_m": args.pixel_m,
            "stratum": c.to_dict(),
        }

    specs = {
        "seed": args.seed,
        "grid_fit": bool(args.grid_fit),
        "strict_cells": args.strict_cells,
        "ghm_tercile_edges": edges,
        "n_candidates_attributed": len(cands),
        "selected": [spec(i, c) for i, c in enumerate(selected)],
        "reserve": [spec(1000 + i, c) for i, c in enumerate(reserve)],
    }
    (out / "tile_specs.json").write_text(json.dumps(specs, indent=1))
    pts.drop(columns="geometry").to_parquet(out / "candidates.parquet", index=False)
    from collections import Counter

    print(f"candidates attributed: {len(cands)}; selected {len(selected)} + reserve {len(reserve)}")
    print("tercile edges:", edges)
    print("biomes:", sorted(Counter(c.biome_name for c in selected).items()))
    print("realms:", sorted(Counter(c.realm for c in selected).items()))
    print("terciles:", sorted(Counter(c.ghm_tercile for c in selected).items()))
    print("strata:", len({c.stratum for c in selected}))


if __name__ == "__main__":
    main()
