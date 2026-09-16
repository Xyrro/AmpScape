#!/usr/bin/env python
"""Freeze the v1.0 macro-cell split assignment (dataset plan §5): one seeded train/val/test_id label per cell of the
equal-width 20° grid, stratified by the cell's dominant RESOLVE realm (from the v1.0 S candidate points), written to
configs/splits/cell_assignment_v1.json and used by every split computation from then on.

Why: `assign_blocks` cuts the hash-sorted cells of each stratum by the split fractions, so the label of a cell depended
on which cells happened to hold tiles (tier by tier, subset by subset). Freezing the full-grid assignment makes the
split a pure function of (cell, seed) as the plan promised.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ampscape.splits.spatial import BlockGrid, assign_blocks  # noqa: E402


def main():
    cfg = yaml.safe_load(open(ROOT / "configs/datasets/v1_0.yaml"))["splits"]
    grid = BlockGrid(float(cfg["spatial_block"]["band_deg"]), equal_width=True)
    pts = pd.read_parquet(ROOT / "data/tiles/v1/specs/S/candidates.parquet")
    pts["block"] = [grid.block_id(a, b) for a, b in zip(pts.lat, pts.lon, strict=True)]
    realm = pts.groupby("block").REALM.agg(lambda x: x.mode().iloc[0]).to_dict()
    cells = [f"b{b:03d}_{j:03d}" for b in range(grid.n_bands()) for j in range(grid.n_lon(b))]
    land = [c for c in cells if c in realm]  # cells with land candidates
    fractions = {k: cfg[k] for k in ("train", "val", "test_id")}
    assign = assign_blocks(land, int(cfg["seed"]), fractions, realm)
    out = {
        "seed": int(cfg["seed"]),
        "band_deg": grid.size_deg,
        "n_cells_total": len(cells),
        "n_land_cells": len(land),
        "fractions": fractions,
        "strata": "dominant RESOLVE realm of the v1.0 S candidate points per cell",
        "source": "data/tiles/v1/specs/S/candidates.parquet (seed 202609061, 60 000 uniform land points)",
        "assignment": assign,
        "realm": realm,
    }
    p = ROOT / "configs/splits/cell_assignment_v1.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, sort_keys=True))
    from collections import Counter

    print(f"{len(land)} land cells of {len(cells)}:", Counter(assign.values()), "->", p)


if __name__ == "__main__":
    main()
