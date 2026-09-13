"""Tiling of published resistance surfaces for the `test_ood_published` evaluation set (dataset plan §5.4).

Rule (owner, 2026-09-13): resistance is used *as given*, resampled to the nearest AmpScape tier whose
pixel size is ≥ the source resolution (never upsampled): 10–20 m sources → tier S (100 m) [and M],
1 km sources → tier XXL (1 km, no resampling). Aggregation is the **geometric mean of resistance**
over the target pixel footprint (the mean of log R), the neutral choice for a multiplicative quantity;
NoData if more than half the footprint is NoData. Values are then rescaled to R ≥ 1 by dividing by the
source minimum when that minimum is < 1 (documented per source; all three sources already have min = 1).
Provenance (source DOI, licence, CRS, native resolution, rule, min/max) is recorded per tile.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
from dataclasses import dataclass

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds

from ampscape.landscapes.real import make_grid

TIER_PIXEL = {"S": 100.0, "M": 100.0, "L": 200.0, "XL": 500.0, "XXL": 1000.0}
TIER_SIZE = {"S": 128, "M": 256, "L": 512, "XL": 1024, "XXL": 2048}


@dataclass
class PublishedSource:
    source_id: str
    path: str
    doi: str
    license: str
    citation: str
    crs_override: str | None = None       # e.g. EPSG:32604 for the gallinule ASCII grids (no CRS in file)
    nodata_override: float | None = None


SOURCES = [
    PublishedSource("eurac_alps", "data/sources/published/Landscape_Permeability.tif", "10.5281/zenodo.6602481", "CC BY 4.0",
                    "Marsoner, Simion, Giombini, Egarter Vigl (Eurac Research) 2022, Zenodo 10.5281/zenodo.6602481"),
    PublishedSource("raccoon_europe", "data/sources/published/output maps/raccoon - resistance.tif", "10.6084/m9.figshare.27311484.v1", "CC BY 4.0",
                    "figshare 10.6084/m9.figshare.27311484.v1 (Crossing borders: range expansion of the Northern raccoon in Europe)"),
    PublishedSource("hawaiian_gallinule", "data/sources/published/f_wet_negbin.txt", "10.5061/dryad.p90b87p", "CC0 1.0",
                    "Dryad 10.5061/dryad.p90b87p (van Rees et al., Ecol. Evol. 2018, 10.1002/ece3.4296); layer f_wet_negbin",
                    crs_override="EPSG:32604", nodata_override=-9999.0),
]


def nearest_tier(native_res_m: float) -> str:
    for t in ("S", "M", "L", "XL", "XXL"):
        if TIER_PIXEL[t] >= native_res_m - 1e-6:
            return t
    return "XXL"


def _open(src: PublishedSource):
    ds = rasterio.open(src.path)
    crs = rasterio.crs.CRS.from_string(src.crs_override) if src.crs_override else ds.crs
    nodata = src.nodata_override if src.nodata_override is not None else ds.nodata
    return ds, crs, nodata


def tile_centres(src: PublishedSource, tier: str, max_tiles: int | None = None, seed: int = 0) -> list[tuple[float, float]]:
    """Regular grid of non-overlapping tile centres over the source extent (lat, lon), shuffled deterministically."""
    ds, crs, _ = _open(src)
    size_m = TIER_SIZE[tier] * TIER_PIXEL[tier]
    xmin, ymin, xmax, ymax = ds.bounds
    xs = np.arange(xmin + size_m / 2, xmax - size_m / 2 + 1e-6, size_m)
    ys = np.arange(ymin + size_m / 2, ymax - size_m / 2 + 1e-6, size_m)
    from pyproj import Transformer

    tr = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    pts = []
    for y in ys:
        for x in xs:
            lon, lat = tr.transform(x, y)
            pts.append((float(lat), float(lon)))
    ds.close()
    rng = np.random.default_rng(seed)
    rng.shuffle(pts)
    return pts[:max_tiles] if max_tiles else pts


def extract_published_tile(src: PublishedSource, lat: float, lon: float, tier: str, max_nodata_frac: float = 0.10):
    """Resistance tile (float32, R ≥ 1, 1.0 at NoData), NoData mask, grid, provenance dict; None if too much NoData."""
    ds, crs, nodata = _open(src)
    grid = make_grid(lat, lon, TIER_SIZE[tier], TIER_PIXEL[tier])
    native = float(ds.res[0])
    xmin, ymin, xmax, ymax = transform_bounds(grid.crs, crs, *grid.bounds, densify_pts=21)
    win = ds.window(xmin - 2 * native, ymin - 2 * native, xmax + 2 * native, ymax + 2 * native).round_offsets().round_lengths()
    data = ds.read(1, window=win, boundless=True, fill_value=nodata if nodata is not None else np.nan).astype(np.float64)
    src_tf = ds.window_transform(win)
    valid = np.isfinite(data) & ((data != nodata) if nodata is not None else True) & (data > 0)
    logr = np.where(valid, np.log(np.maximum(data, 1e-12)), 0.0)
    # geometric mean of R = exp(area mean of log R); track the valid fraction with a second reprojection
    dst_log = np.full(grid.shape, np.nan, dtype=np.float64)
    dst_val = np.zeros(grid.shape, dtype=np.float64)
    resamp = Resampling.average if native < TIER_PIXEL[tier] - 1e-6 else Resampling.nearest
    reproject(logr, dst_log, src_transform=src_tf, src_crs=crs, dst_transform=grid.transform, dst_crs=grid.crs,
              src_nodata=None, dst_nodata=np.nan, resampling=resamp)
    reproject(valid.astype(np.float64), dst_val, src_transform=src_tf, src_crs=crs, dst_transform=grid.transform, dst_crs=grid.crs,
              src_nodata=None, dst_nodata=0.0, resampling=resamp)
    ds.close()
    nd = ~(np.isfinite(dst_log) & (dst_val >= 0.5))
    if nd.mean() > max_nodata_frac:
        return None
    # mean of log over the valid part of the footprint: divide the masked average by the valid fraction
    R = np.exp(np.where(nd, 0.0, dst_log / np.maximum(dst_val, 1e-9))).astype(np.float32)
    rmin = float(R[~nd].min())
    scale = 1.0
    if rmin < 1.0:
        scale = 1.0 / rmin
        R = R * scale
    R[nd] = 1.0
    R = np.maximum(R, 1.0).astype(np.float32)
    prov = {"source_id": src.source_id, "doi": src.doi, "license": src.license, "citation": src.citation, "source_file": src.path,
            "source_crs": crs.to_string(), "native_res_m": native, "tier": tier, "pixel_size_m": TIER_PIXEL[tier],
            "resampling": "geometric mean of R (area mean of log R)" if resamp == Resampling.average else "none (native resolution)",
            "rescale_factor": scale, "r_min": float(R[~nd].min()), "r_max": float(R[~nd].max()), "nodata_frac": float(nd.mean()),
            "epsg": grid.epsg, "transform": list(grid.transform)[:6], "lat": lat, "lon": lon}
    return R, nd, grid, prov


def tile_id(src: PublishedSource, tier: str, lat: float, lon: float) -> str:
    h = hashlib.sha1(f"{src.source_id}|{tier}|{lat:.5f}|{lon:.5f}".encode()).hexdigest()[:8]
    return f"pub_{src.source_id}_{tier}_{h}"


def write_tile(path: str, R: np.ndarray, nd: np.ndarray, grid, prov: dict) -> str:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=grid.size, width=grid.size, count=2, dtype="float32", crs=grid.crs,
                       transform=grid.transform, compress="deflate", tiled=True) as dst:
        dst.write(R, 1)
        dst.write(nd.astype(np.float32), 2)
        dst.set_band_description(1, "resistance")
        dst.set_band_description(2, "nodata")
        dst.update_tags(provenance=json.dumps(prov))
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["SOURCES", "PublishedSource", "nearest_tier", "tile_centres", "extract_published_tile", "tile_id", "write_tile", "math"]
