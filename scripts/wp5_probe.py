#!/usr/bin/env python
"""WP5 resolution-vs-size probe set (docs/addendum_WP5_report.md §3), stored under aux/scale_probe/, never in v1.0.

Design (2 × 2 per real tile, fixed T4 window of 12.8 km):  cell A = 256² @ 100 m (central crop of C),
cell B = 256² @ 200 m (central crop of the L-native tile), cell C = 512² @ 100 m (new extraction around the L centre),
cell D = 512² @ 200 m (the L-native tile).  Synthetic seeds are regenerated at 256² and 512² (size axis only).
Radius 128 px / block 11 at 100 m, 64 px / block 5 at 200 m (both 12.8 km); table large_mammal.

  select   --out aux/scale_probe --n-real 60 --n-syn 60          # 30 test_id + 30 ood_region L tiles; 60 synthetic seeds
  extract  --out aux/scale_probe [--workers 4]                    # cell C: 512² @ 100 m stacks (Slurm)
  build    --out aux/scale_probe                                  # probe tile root: A/B/C/D rasters + tiles/resistance parquet
  plan     --out aux/scale_probe [--shard-size 8]                 # manifest + inputs with per-sample radius/block attrs
Then: generate.py submit --build aux/scale_probe/probe_L ...; finalize; evaluate per cell with --root aux/scale_probe/build.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CELLS = {
    "A": (256, 100.0, 128, 11),
    "B": (256, 200.0, 64, 5),
    "C": (512, 100.0, 128, 11),
    "D": (512, 200.0, 64, 5),
}
SYN_SEED0 = 900_000_000  # disjoint from every v1.0 tier stream (S 1e8 … XXL 5e8)


def cmd_select(a):
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = pd.read_parquet(ROOT / "data/v1/L/manifest.parquet")
    real = m[(m.family == "real") & (m.table_id == "large_mammal")].drop_duplicates("tile_id")
    tiles = pd.read_parquet(ROOT / "data/tiles/v1.0/tiles.parquet").set_index("tile_id")
    rows = []
    for split in ("test_id", "ood_region"):
        pick = real[real.split == split].sort_values("tile_id").head(a.n_real // 2)
        for r in pick.itertuples():
            t = tiles.loc[r.tile_id]
            rows.append(
                {
                    "source_tile": r.tile_id,
                    "split": split,
                    "lat": float(t.lat),
                    "lon": float(t.lon),
                    "realm": t.realm,
                    "biome_num": int(t.biome_num),
                }
            )
    sel = pd.DataFrame(rows)
    sel.to_parquet(out / "selection_real.parquet", index=False)
    syn = pd.DataFrame({"seed": [SYN_SEED0 + i for i in range(a.n_syn)]})
    syn.to_parquet(out / "selection_syn.parquet", index=False)
    print(f"real: {sel.split.value_counts().to_dict()} | synthetic seeds: {len(syn)}")


def cmd_extract(a):
    from joblib import Parallel, delayed

    from ampscape.landscapes import real

    out = pathlib.Path(a.out)
    sel = pd.read_parquet(out / "selection_real.parquet")
    sources = real.local_sources_from_dir(str(ROOT / "data/sources"))
    (out / "tiles" / "C").mkdir(parents=True, exist_ok=True)
    versions = {
        "note": "WP5 probe extraction, same reader as data/tiles/v1.0",
        "extracted_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }

    def one(r):
        tid = f"P_{r.source_tile}_C"
        p = out / "tiles" / "C" / f"{tid}.tif"
        if p.exists():
            return {"tile_id": tid, "ok": True, "cached": True}
        spec = real.TileSpec(
            tile_id=tid,
            lat=r.lat,
            lon=r.lon,
            tier="L",
            size=512,
            pixel_m=100.0,
            stratum={"realm": r.realm, "biome_num": r.biome_num},
        )
        ch, grid, qc = real.extract_tile(spec, sources)
        if qc["accept"]:
            real.write_tile(str(p), ch, grid, spec, qc, versions)
        return {
            "tile_id": tid,
            "ok": bool(qc["accept"]),
            "unusable": qc["frac_unusable"],
            "dem_nan_land": qc.get("frac_dem_nan_land"),
        }

    res = Parallel(n_jobs=a.workers, prefer="threads")(delayed(one)(r) for r in sel.itertuples())
    pd.DataFrame(res).to_parquet(out / "extract_C.parquet", index=False)
    print(f"extracted C: {sum(r['ok'] for r in res)} ok of {len(res)}")


def _write_raster(path: pathlib.Path, R: np.ndarray, nd: np.ndarray, profile: dict, tags: dict):
    import rasterio

    path.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(
        profile,
        count=2,
        dtype="float32",
        nodata=None,
        compress="deflate",
        predictor=2,
        height=R.shape[0],
        width=R.shape[1],
    )
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(R.astype(np.float32), 1)
        dst.write(nd.astype(np.float32), 2)
        dst.update_tags(**tags)


def cmd_build(a):
    import rasterio
    from rasterio.windows import Window

    from ampscape.landscapes.real import read_tile
    from ampscape.resistance import apply_table, load_tables

    out = pathlib.Path(a.out)
    sel = pd.read_parquet(out / "selection_real.parquet")
    v1 = ROOT / "data/tiles/v1.0"
    v1t = pd.read_parquet(v1 / "tiles.parquet").set_index("tile_id")
    table = load_tables(ROOT / "configs/resistance_tables")["large_mammal"]
    tile_rows, res_rows = [], []
    for r in sel.itertuples():
        srcs = {
            "D": v1 / v1t.loc[r.source_tile, "path"],
            "C": out / "tiles" / "C" / f"P_{r.source_tile}_C.tif",
        }
        if not srcs["C"].exists():
            continue
        for cell, (size, pm, radius, block) in CELLS.items():
            base = "C" if pm == 100.0 else "D"
            cov, tags = read_tile(str(srcs[base]))
            with rasterio.open(srcs[base]) as s:
                prof = s.profile
                tr = s.transform
            if size == 256:  # central crop
                o = 128
                cov = {k: v[o : o + 256, o : o + 256] for k, v in cov.items()}
                tr = tr * rasterio.Affine.translation(o, o)
            R, nd, stats = apply_table(table, cov)
            tid = f"P_{r.source_tile}_{cell}"
            p = out / "resistance" / "large_mammal" / f"{tid}.tif"
            _write_raster(
                p,
                R,
                nd,
                dict(prof, transform=tr),
                {
                    "tile_id": tid,
                    "table_id": "large_mammal",
                    "table_version": table.version,
                    "table_sha256": table.sha256 or "",
                    "r_max": table.r_max,
                    "probe_cell": cell,
                    "source_tile": r.source_tile,
                },
            )
            # a covariate tile per cell (prepare reads landcover from it for T1R)
            tp = out / "tiles" / cell / f"{tid}.tif"
            tp.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(srcs[base]) as s:
                if size == 256:
                    data = s.read(window=Window(128, 128, 256, 256))
                else:
                    data = s.read()
                pr = dict(s.profile, height=size, width=size, transform=tr)
                with rasterio.open(tp, "w", **pr) as d:
                    d.write(data)
                    d.update_tags(**{k: v for k, v in s.tags().items()})
                    d.update_tags(tile_id=tid, probe_cell=cell, source_tile=r.source_tile)
                    for i in range(1, s.count + 1):
                        d.set_band_description(i, s.descriptions[i - 1] or "")
            tile_rows.append(
                {
                    "tile_id": tid,
                    "lat": r.lat,
                    "lon": r.lon,
                    "tier": "L",
                    "size": size,
                    "pixel_m": pm,
                    "epsg": int(v1t.loc[r.source_tile, "epsg"]),
                    "qc_accept": True,
                    "biome_num": r.biome_num,
                    "biome_name": "",
                    "realm": r.realm,
                    "ghm_tercile": int(v1t.loc[r.source_tile, "ghm_tercile"]),
                    "stratum": str(v1t.loc[r.source_tile, "stratum"]),
                    "path": str(tp.relative_to(out)),
                    "probe_cell": cell,
                    "source_tile": r.source_tile,
                    "split": r.split,
                    "radius": radius,
                    "block": block,
                }
            )
            res_rows.append(
                {
                    "tile_id": tid,
                    "table_id": "large_mammal",
                    "table_version": table.version,
                    "table_sha256": table.sha256,
                    "path": str(p.relative_to(out)),
                    **stats,
                    "created_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                }
            )
    pd.DataFrame(tile_rows).to_parquet(out / "tiles.parquet", index=False)
    pd.DataFrame(res_rows).to_parquet(out / "resistance.parquet", index=False)
    print(
        f"probe tile root: {len(tile_rows)} cell tiles ({len(tile_rows) // 4} source tiles × 4 cells)"
    )


def cmd_plan(a):
    import h5py

    from ampscape.solve.manifest import DEFAULT_CONFIGS, SampleSpec, sample_uuid, to_frame
    from ampscape.solve.prepare import prepare_shard
    from ampscape.sources import SourceConfig

    out = pathlib.Path(a.out)
    build = out / "probe_L"
    build.mkdir(parents=True, exist_ok=True)
    tiles = pd.read_parquet(out / "tiles.parquet")
    syn = pd.read_parquet(out / "selection_syn.parquet")
    specs, meta_rows = [], []
    for r in tiles.itertuples():
        sid = sample_uuid("ampscape-scale-probe", "real", f"{r.tile_id}:large_mammal")
        specs.append(
            SampleSpec(
                sid,
                "ampscape-scale-probe",
                "real",
                "L",
                int(r.size),
                float(r.pixel_m),
                int(sample_uuid("p", "s", r.tile_id)[:8], 16) % (2**31 - 1),
                json.dumps(list(DEFAULT_CONFIGS)),
                tile_id=r.tile_id,
                table_id="large_mammal",
                split=r.split,
                cg_baseline=False,
                extra=json.dumps(
                    {
                        "probe_cell": r.probe_cell,
                        "source_tile": r.source_tile,
                        "radius": int(r.radius),
                        "block": int(r.block),
                    }
                ),
            )
        )
        meta_rows.append(
            {
                "sample_id": sid,
                "probe_cell": r.probe_cell,
                "source_tile": r.source_tile,
                "family": "real",
                "split": r.split,
                "size": r.size,
                "pixel_m": r.pixel_m,
            }
        )
    for s in syn.seed:
        for cell, size in (("S256", 256), ("S512", 512)):
            sid = sample_uuid("ampscape-scale-probe", "synthetic", f"{cell}:{int(s)}")
            radius, block = (
                (128, 11) if size == 512 else (64, 5)
            )  # fixed 12.8 km at a nominal 100 m (512²) vs 200 m (256²)
            specs.append(
                SampleSpec(
                    sid,
                    "ampscape-scale-probe",
                    "synthetic",
                    "L",
                    size,
                    100.0 if size == 512 else 200.0,
                    int(s),
                    json.dumps(list(DEFAULT_CONFIGS)),
                    split="test_id",
                    cg_baseline=False,
                    extra=json.dumps(
                        {"design": "v1", "probe_cell": cell, "radius": radius, "block": block}
                    ),
                )
            )
            meta_rows.append(
                {
                    "sample_id": sid,
                    "probe_cell": cell,
                    "source_tile": None,
                    "family": "synthetic",
                    "split": "test_id",
                    "size": size,
                    "pixel_m": 100.0 if size == 512 else 200.0,
                }
            )
    for i, sp in enumerate(specs):
        sp.shard = i // a.shard_size
    df = to_frame(specs)
    df.to_parquet(build / "manifest.parquet", index=False)
    pd.DataFrame(meta_rows).to_parquet(out / "probe_index.parquet", index=False)
    cfg = {
        "dataset_id": "ampscape-scale-probe",
        "tier": "L",
        "shard_size": a.shard_size,
        "pilot": str(out.resolve().relative_to(ROOT.resolve())),
        "published": None,
        "source_config": "configs/tasks/sources_default.yaml",
        "solver_preset": "configs/solver/circuitscape_reference.yaml",
        "dataset_version": "aux-scale-probe",
        "n_synthetic": int(len(syn) * 2),
        "n_real": int(len(tiles)),
        "seed0": SYN_SEED0,
    }
    (build / "build.json").write_text(json.dumps(cfg, indent=1))
    scfg = SourceConfig.from_yaml(ROOT / cfg["source_config"])
    for sh in sorted(df.shard.unique()):
        p = build / "inputs" / f"shard-{sh:05d}.inputs.h5"
        sub = [s for s in specs if s.shard == sh]
        prepare_shard(sub, str(p), scfg, pilot_root=str(out), overwrite=True)
        with h5py.File(p, "a") as f:
            for s in sub:
                ex = json.loads(s.extra)
                f["samples"][s.sample_id].attrs["omni_radius"] = int(ex["radius"])
                f["samples"][s.sample_id].attrs["omni_block_size"] = int(ex["block"])
        print(f"shard {sh}: {len(sub)} inputs")
    print(f"planned {len(df)} probe samples in {df.shard.nunique()} shards -> {build}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--out", required=True)
    s.add_argument("--n-real", type=int, default=60)
    s.add_argument("--n-syn", type=int, default=60)
    s.set_defaults(fn=cmd_select)
    e = sub.add_parser("extract")
    e.add_argument("--out", required=True)
    e.add_argument("--workers", type=int, default=4)
    e.set_defaults(fn=cmd_extract)
    b = sub.add_parser("build")
    b.add_argument("--out", required=True)
    b.set_defaults(fn=cmd_build)
    p = sub.add_parser("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--shard-size", type=int, default=8)
    p.set_defaults(fn=cmd_plan)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
