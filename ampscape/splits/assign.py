"""Attach split and OOD columns to a build index (dataset plan §4–5).

Real samples: spatial macro-cell assignment shared across tiers (``spatial.assign_tiles``) using the
tile centres from the sample metadata; synthetic samples: seed family. Held-out tables / contrasts are
demoted from train/val to ``test_ood``. Writes ``splits/<split>.parquet`` (sample ids) next to the index.
"""

from __future__ import annotations

import json
import pathlib

import pandas as pd
import yaml

from ampscape.splits.spatial import (
    BlockGrid,
    apply_tile_holdouts,
    region_holdouts,
    apply_holdouts,
    assign_tiles,
    ood_flags,
    synthetic_split,
)

DEFAULT_CFG = pathlib.Path(__file__).resolve().parents[2] / "configs" / "datasets" / "v1_0.yaml"


def stable_unit(key: str) -> float:
    """Deterministic pseudo-uniform in [0, 1) from a string (sha1; Python's hash() is salted per process)."""
    import hashlib

    return int(hashlib.sha1(key.encode()).hexdigest()[:12], 16) / float(16 ** 12)


def add_splits(index: pd.DataFrame, build: pathlib.Path, cfg_path: pathlib.Path = DEFAULT_CFG) -> pd.DataFrame:
    cfg = yaml.safe_load(open(cfg_path))
    sp = cfg["splits"]
    sb = sp["spatial_block"]
    grid = BlockGrid(float(sb.get("band_deg", sb.get("size_deg", 20.0))), equal_width=(sb.get("grid", "equal_width") == "equal_width"))
    seed = int(sp["seed"])
    fractions = {k: sp[k] for k in ("train", "val", "test_id")}
    df = index.copy()
    # real tiles: one row per tile with centre and size
    real = df[df.family == "real"].drop_duplicates("sample_id")
    if len(real):
        tiles = pd.DataFrame({"tile_id": real.tile_id, "tier": real.tier, "lat": real.lat, "lon": real.lon, "size": real.H,
                              "pixel_m": real.pixel_m, "realm": real.realm, "biome_num": real.biome_num}).drop_duplicates("tile_id")
        from ampscape.solve.manifest import load_parents

        bj = pathlib.Path(build) / "build.json"
        tiles_root = json.loads(bj.read_text()).get("pilot") if bj.exists() else None
        tiles = pd.concat([tiles, load_parents(tiles_root)], ignore_index=True)
        ood_blocks, ood_tiles = region_holdouts(tiles, grid, cfg["ood"]["test_ood_region"])
        t = apply_tile_holdouts(assign_tiles(tiles, grid, seed, ood_blocks=ood_blocks, fractions=fractions), ood_tiles)
        tile_split = dict(zip(t.tile_id, t.split, strict=True))
        tile_block = dict(zip(t.tile_id, t.block_id, strict=True))
    else:
        tile_split, tile_block = {}, {}
    splits, blocks = [], []
    for r in df.itertuples():
        if r.family == "real":
            splits.append(tile_split.get(r.tile_id, "excluded"))
            blocks.append(tile_block.get(r.tile_id))
        elif r.family == "published":
            splits.append("test_ood_published")
            blocks.append(None)
        else:
            splits.append(synthetic_split(int(r.seed), seed, fractions))
            blocks.append(None)
    df["split"] = splits
    df["block_id"] = blocks
    flags = [ood_flags(row, cfg) for row in df.to_dict("records")]
    for k in flags[0]:
        df[k] = [f[k] for f in flags]
    df["split"] = [s if s == "test_ood_published" else apply_holdouts(s, f) for s, f in zip(df.split, flags, strict=True)]
    df["test_ood_published"] = df.split == "test_ood_published"
    # XL: only a share of macro-cells are train/val (amendment C3) — applied by block hash
    xl_share = float(sp.get("xl_trainval_share", 0.25))
    df.loc[(df.tier == "XL") & df.split.isin(["train", "val"]) & (df.block_id.apply(lambda b: stable_unit(f"{b}|{seed}") >= xl_share)), "split"] = "test_id"
    df.loc[(df.tier == "XXL") & df.split.isin(["train", "val"]), "split"] = "test_id"
    df["qc_trainval"] = df.qc_trainval & df.split.isin(["train", "val"])
    out = pathlib.Path(build) / "splits"
    out.mkdir(exist_ok=True)
    for name, g in df.groupby("split"):
        g[["sample_id"]].drop_duplicates().to_parquet(out / f"{name}.parquet", index=False)
    (out / "README.json").write_text(json.dumps({"seed": seed, "block_size_deg": grid.size_deg, "fractions": fractions,
                                                 "counts": df.groupby("split").sample_id.nunique().to_dict()}, indent=1))
    return df
