#!/usr/bin/env python
"""Extract the small arrays the paper's qualitative figures need (overview, data gallery, prediction panels) into
paper/figdata/*.npz plus a manifest, so that scripts/paper_figures.py never touches shards or prediction files.

  python scripts/paper_figdata.py --out paper/figdata [--tmp /tmp/ampscape_figdata]

Sources (recorded per item in paper/figdata/manifest.json):
  * S tier: the local mini build (data/builds/mini, all configurations per shard; one synthetic and one real sample).
  * M, L, XL tiers: one synthetic and one real `test_id` landscape each; their T1 (`points`) and T4 (`omniscape`)
    shards are fetched from the Hub (`hf_path` of the published index) unless staged under data/hfcache.
  * XXL: both groups are read from data/hfcache when staged, otherwise fetched.
  * Qualitative panels at L: one in-distribution real `test_id` landscape and one `test_ood` landscape built with the
    held-out `forest_bird` table; predictions of the official T1 model (fno_T1_L_s1_t2, FNO w48) and T4 model
    (unet_T4_L_s1) are read from their published predictions.h5 (aux/results/runs_full/<run>/predictions/<tag>/).
Run as a Slurm CPU job (≈ 6 GB of Hub downloads to node-local disk).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time

import h5py
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = "Xirro/AmpScape"
T1_RUN, T4_RUN = "fno_T1_L_s1_t2", "unet_T4_L_s1"


def hub_file(path: str, tmp: pathlib.Path) -> pathlib.Path:
    local = ROOT / "data" / "hfcache" / path
    if local.exists():
        return local
    from huggingface_hub import hf_hub_download

    return pathlib.Path(hf_hub_download(REPO, path, repo_type="dataset", local_dir=str(tmp)))


def read_sample(h5path: pathlib.Path, sid: str, config: str) -> dict:
    out = {}
    with h5py.File(h5path, "r") as f:
        g = f[sid]
        out["resistance"] = g["inputs"]["resistance"][...].astype(np.float32)
        out["nodata"] = g["inputs"]["nodata_mask"][...].astype(np.uint8)
        if "covariates" in g["inputs"]:
            out["covariates"] = g["inputs"]["covariates"][...].astype(np.float32)
            ch = g["inputs"]["covariates"].attrs.get("channels", [])
            out["covariate_names"] = np.array([str(x) for x in ch])
        c = g["configs"][config]
        for k in ("focal_mask", "source_strength", "ground"):
            if k in c["inputs"]:
                out[f"in_{k}"] = c["inputs"][k][...]
        for k in ("cum_current", "current", "voltage", "flow_potential"):
            if k in c["outputs"]:
                out[f"out_{k}"] = c["outputs"][k][...].astype(np.float32)
        attrs = {k: (v.tolist() if hasattr(v, "tolist") else str(v)) for k, v in g.attrs.items()}
        out["attrs"] = np.array(json.dumps(attrs)[:4000])
    return out


def pick(idx: pd.DataFrame, family: str, split: str = "test_id", table: str | None = None) -> str:
    """One landscape with both `points` and `omniscape` rows passing QC; real: median contrast; synthetic: a fractal
    or GRF landscape at contrast 1000 when present. Deterministic (sorted ids)."""
    d = idx[(idx.family == family) & (idx.split == split) & idx.qc_pass.astype(bool)]
    if table:
        d = d[d.resistance_table_id == table]
    both = d.groupby("sample_id").config.apply(set)
    ids = [s for s, cs in both.items() if {"points", "omniscape"} <= cs]
    d = d[d.sample_id.isin(ids) & (d.config == "points")].sort_values("sample_id")
    if family == "synthetic":
        pref = d[d.generator.astype(str).str.contains("fractal|grf", regex=True) & (d.contrast.round() == 1000)]
        d = pref if len(pref) else d
        return d.sample_id.iloc[len(d) // 3]
    d = d.assign(dc=(d.contrast - d.contrast.median()).abs()).sort_values(["dc", "sample_id"])
    return d.sample_id.iloc[0]


def meta_row(r: pd.Series) -> dict:
    return {
        "generator": str(r.generator),
        "table": str(r.resistance_table_id),
        "contrast": float(r.contrast),
        "biome_num": float(r.biome_num) if pd.notna(r.biome_num) else None,
        "realm": str(r.realm) if "realm" in r else None,
        "pixel_m": float(r.pixel_m) if "pixel_m" in r else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="paper/figdata")
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp") + "/ampscape_figdata")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(a.tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    t0 = time.time()

    # ---- S: the mini build (synthetic + real); the real sample also serves the overview figure
    mini = ROOT / "data" / "builds" / "mini"
    midx = pd.read_parquet(mini / "index.parquet")
    for fam in ("synthetic", "real"):
        split = "test_id" if ((midx.family == fam) & (midx.split == "test_id")).any() else "train"
        sid = pick(midx, fam, split=split)
        row = midx[(midx.sample_id == sid) & (midx.config == "points")].iloc[0]
        shard = mini / "shards" / row.shard
        d = {}
        for cfg in ("points", "omniscape", "advanced"):
            if ((midx.sample_id == sid) & (midx.config == cfg)).any():
                for k, v in read_sample(shard, sid, cfg).items():
                    d[f"{cfg}__{k}"] = v
        np.savez_compressed(out / f"gallery_S_{fam}.npz", **d)
        manifest[f"gallery_S_{fam}"] = {"sample_id": sid, "tier": "S", "family": fam, "split": split, **meta_row(row),
                                        "source": f"data/builds/mini/shards/{row.shard} (aux/mini on the Hub)"}
        print("S", fam, sid, "covariates" if "points__covariates" in d else "no covariates", flush=True)

    # ---- M, L, XL, XXL from the published index
    cols = ["sample_id", "config", "family", "generator", "resistance_table_id", "contrast", "biome_num", "realm",
            "split", "test_ood_table", "qc_pass", "hf_path", "task_group", "pixel_m"]
    for tier in ("M", "L", "XL", "XXL"):
        idx = pd.read_parquet(ROOT / "data" / "hfcache" / "index" / f"{tier}.parquet", columns=cols)
        for fam in ("synthetic", "real"):
            sid = pick(idx, fam)
            rows = idx[(idx.sample_id == sid) & idx.config.isin(["points", "omniscape"])]
            d = {}
            for _, r in rows.iterrows():
                p = hub_file(r.hf_path, tmp)
                for k, v in read_sample(p, sid, r.config).items():
                    d[f"{r.config}__{k}"] = v
            np.savez_compressed(out / f"gallery_{tier}_{fam}.npz", **d)
            manifest[f"gallery_{tier}_{fam}"] = {"sample_id": sid, "tier": tier, "family": fam, "split": "test_id",
                                                 **meta_row(rows.iloc[0]), "source": sorted(set(rows.hf_path))}
            print(tier, fam, sid, f"{time.time() - t0:.0f} s", flush=True)

    # ---- qualitative panels at L: ID (real test_id) and OOD (forest_bird table, test_ood)
    idx = pd.read_parquet(ROOT / "data" / "hfcache" / "index" / "L.parquet", columns=cols)
    cases = {"id": ("test_id", pick(idx, "real", "test_id")), "ood": ("test_ood", pick(idx, "real", "test_ood", table="forest_bird"))}
    preds: dict[tuple, pathlib.Path] = {}
    for case, (split, sid) in cases.items():
        rows = idx[(idx.sample_id == sid) & idx.config.isin(["points", "omniscape"])]
        d = {}
        for _, r in rows.iterrows():
            p = hub_file(r.hf_path, tmp)
            for k, v in read_sample(p, sid, r.config).items():
                d[f"{r.config}__{k}"] = v
        srcs = sorted(set(rows.hf_path))
        for run, cfg in ((T1_RUN, "points"), (T4_RUN, "omniscape")):
            tag = f"hfcache_L_{split}"
            hub_path = f"aux/results/runs_full/{run}/predictions/{tag}/predictions.h5"
            if (run, tag) not in preds:
                from huggingface_hub import hf_hub_download

                preds[(run, tag)] = pathlib.Path(hf_hub_download(REPO, hub_path, repo_type="dataset", local_dir=str(tmp)))
            with h5py.File(preds[(run, tag)], "r") as f:
                g = f[sid][cfg]
                d[f"{cfg}__pred_cum_current"] = g["cum_current"][...].astype(np.float32)
                d[f"{cfg}__pred_inference_time_s"] = np.float32(g.attrs.get("inference_time_s", np.nan))
            srcs.append(hub_path)
        np.savez_compressed(out / f"qual_L_{case}.npz", **d)
        manifest[f"qual_L_{case}"] = {"sample_id": sid, "tier": "L", "split": split, "family": str(rows.iloc[0].family),
                                      **meta_row(rows.iloc[0]), "runs": {"T1": T1_RUN, "T4": T4_RUN}, "source": srcs}
        print("qual", case, sid, f"{time.time() - t0:.0f} s", flush=True)
    manifest["_meta"] = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "repo": REPO,
                         "seconds": round(time.time() - t0)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("done", sorted(p.name for p in out.glob("*.npz")))


if __name__ == "__main__":
    main()
