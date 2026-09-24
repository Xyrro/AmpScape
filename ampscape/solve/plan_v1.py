"""v1.0 planner (configs/datasets/v1_0.yaml, dataset plan §2–§5): deterministic per-tier streams so that any
subset built from the first n landscapes of a tier (dev, core) is a true prefix of v1.0 and stays valid as
long as the pipeline is frozen.

Streams per tier
  synthetic  seed = TIER_SEED_BASE[tier] + i, landscape from :func:`sample_landscape_v1` (v1.0 generator mix +
             hard-case stratum); split by seed family; `regions` (T1R) added on patch-mosaic landscapes (C5).
  real       accepted tiles of `<tiles_root>/tiles.parquet` in extraction order (the sampler's stratified
             round-robin order, prefix-extracted with `extract_tiles.py --first-accepted`), each × the five
             tables (4 expert + the per-tile `random_lm`); source seed = sha1(tile_id | table_id).
The first n landscapes of a tier = the first round(0.6 n) synthetic seeds + the first n_tiles = (n − n_syn) / 5
tiles × 5 tables. Sample ids are UUID5 of (dataset_id, family, key) and therefore identical in v1.0.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib

import pandas as pd

from ampscape.solve.manifest import (
    DEFAULT_CONFIGS,
    TIER_PIXEL_M,
    TIER_SIZES,
    SampleSpec,
    sample_uuid,
)

TIER_SEED_BASE = {
    "S": 100_000_000,
    "M": 200_000_000,
    "L": 300_000_000,
    "XL": 400_000_000,
    "XXL": 500_000_000,
}
V1_TABLES = ["generic_hm", "large_mammal", "amphibian", "forest_bird", "random_lm"]
V1_DATASET_ID = "ampscape-v1.0"
SYNTHETIC_SHARE = 0.6


def stable_seed(key: str) -> int:
    return int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) % (2**31 - 1)


def split_counts(
    n: int, synthetic_share: float = SYNTHETIC_SHARE, n_tables: int = len(V1_TABLES)
) -> tuple[int, int]:
    """(n_synthetic, n_tiles) with n_synthetic + n_tiles * n_tables == n when n * (1 - share) is a multiple of n_tables."""
    n_tiles = int(math.ceil(n * (1.0 - synthetic_share) / n_tables))
    return n - n_tiles * n_tables, n_tiles


def plan_v1_synthetic(
    tier: str,
    n: int,
    shard_size: int,
    shard0: int = 0,
    dataset_id: str = V1_DATASET_ID,
    configs=DEFAULT_CONFIGS,
) -> list[SampleSpec]:
    from ampscape.landscapes.synthetic import sample_landscape_v1

    size = TIER_SIZES[tier]
    out = []
    for i in range(n):
        seed = TIER_SEED_BASE[tier] + i
        ls = sample_landscape_v1(seed, (size, size))
        cfgs = list(configs) + (
            ["regions"] if "patch_mosaic" in ls.params and "regions" not in configs else []
        )
        out.append(
            SampleSpec(
                sample_uuid(dataset_id, "synthetic", f"{tier}:{seed}"),
                dataset_id,
                "synthetic",
                tier,
                size,
                TIER_PIXEL_M[tier],
                seed,
                json.dumps(cfgs),
                generator=ls.generator,
                contrast=ls.contrast,
                shard=shard0 + i // shard_size,
                extra=json.dumps({"design": "v1", "hard_case": ls.params.get("hard_case")}),
            )
        )
    return out


def plan_v1_real(
    tier: str,
    n_tiles: int,
    tiles_root: str | pathlib.Path,
    shard_size: int,
    shard0: int = 0,
    dataset_id: str = V1_DATASET_ID,
    configs=DEFAULT_CONFIGS,
    tables=V1_TABLES,
) -> list[SampleSpec]:
    root = pathlib.Path(tiles_root)
    tiles = pd.read_parquet(root / "tiles.parquet")
    tiles = tiles[(tiles.tier == tier) & tiles.qc_accept]  # extraction (= stream) order
    res = pd.read_parquet(root / "resistance.parquet")
    have = set(zip(res.tile_id, res.table_id, strict=True))
    if len(tiles) < n_tiles:
        raise SystemExit(f"{len(tiles)} accepted {tier} tiles in {root}, need {n_tiles}")
    out = []
    j = 0
    for tile in tiles.tile_id.iloc[:n_tiles]:
        for table in tables:
            if (tile, table) not in have:
                raise SystemExit(f"resistance raster missing for {tile} × {table}")
            cfgs = list(configs) + (
                ["regions"] if "regions" not in configs else []
            )  # prepare skips tiles without patches
            out.append(
                SampleSpec(
                    sample_uuid(dataset_id, "real", f"{tier}:{tile}:{table}"),
                    dataset_id,
                    "real",
                    tier,
                    TIER_SIZES[tier],
                    TIER_PIXEL_M[tier],
                    stable_seed(f"{tile}|{table}"),
                    json.dumps(cfgs),
                    tile_id=tile,
                    table_id=table,
                    shard=shard0 + j // shard_size,
                    extra=json.dumps({"design": "v1"}),
                )
            )
            j += 1
    return out


def plan_v1(
    tier: str,
    n: int,
    tiles_root: str | pathlib.Path,
    shard_size: int,
    dataset_id: str = V1_DATASET_ID,
    n_tiles: int | None = None,
) -> pd.DataFrame:
    from ampscape.solve.manifest import assign_plan_splits, to_frame

    n_syn, n_tiles = split_counts(n) if n_tiles is None else (n - n_tiles * len(V1_TABLES), n_tiles)
    specs = plan_v1_synthetic(tier, n_syn, shard_size, 0, dataset_id)
    shard0 = (len(specs) + shard_size - 1) // shard_size
    specs += plan_v1_real(tier, n_tiles, tiles_root, shard_size, shard0, dataset_id)
    df = assign_plan_splits(to_frame(specs), str(tiles_root))
    return df
