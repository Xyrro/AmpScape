#!/usr/bin/env python
"""Review round 3: build Omniscape (T4) solver inputs from the production Hub files, so that auxiliary solves use the
exact landscapes of the benchmark (the real-tile resistance rasters are no longer on scratch).

  select --tier S --out <build> --quota test_id:synthetic=100,test_id:real=100
         -> <build>/selection.parquet (deterministic: index order of the Hub T4 rows, QC-pass only)
  build  --tier S --out <build> [--sel <selection.parquet>] [--block 1] [--rule default|uniform|random_field|habitat_core]
         [--shard-size 10]
         -> <build>/{manifest.parquet, build.json, inputs/shard-XXXXX.inputs.h5}; shards whose outputs exist are kept
Then solve with scripts/review/r3_solve.sbatch (generate.py solve --configs omniscape, one shard per array task).

Source rules (point 1 of review round 3: does a T4 model use its source channel?). The production rule is
`default`: suitability (1/R) above its 0.5 quantile on the largest valid component, rescaled to max 1. The others
keep the landscape and the Omniscape geometry and change only the source raster:
  uniform       s = 1 on the largest valid component (every pixel a source)
  random_field  Gaussian random field independent of R (length scale 16 px x tier scale, seeded by sample id),
                kept above its median on the component and shifted to start at 0, rescaled to max 1
  habitat_core  (1/R)^2 above its 0.8 quantile on the component, rescaled to max 1 (sparser, sharper habitat)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import h5py
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
REPO = "Xirro/AmpScape"
CACHE = ROOT / "data" / "hfcache_r3"
TIER_SCALE = {"S": 1, "M": 2, "L": 4, "XL": 8, "XXL": 16}
RULES = ("default", "uniform", "random_field", "habitat_core")


def hub_index(tier: str) -> pd.DataFrame:
    idx = pd.read_parquet(ROOT / "data" / "hf" / "AmpScape" / "index" / f"{tier}.parquet")
    return idx[(idx.config == "omniscape") & idx.qc_pass].reset_index(drop=True)


def cmd_select(a):
    idx = hub_index(a.tier)
    rows = []
    for item in a.quota.split(","):
        key, n = item.split("=")
        split, fam = key.split(":")
        c = idx[(idx.split == split) & (idx.family == fam)]
        rows.append(c.head(int(n)))
        print(f"{split}/{fam}: {min(int(n), len(c))} of {len(c)}")
    sel = pd.concat(rows, ignore_index=True)[["sample_id", "split", "family", "generator", "contrast", "hf_path"]]
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sel.to_parquet(out / "selection.parquet", index=False)
    print(f"selection: {len(sel)} -> {out / 'selection.parquet'}")


def _largest_component(R: np.ndarray, nd: np.ndarray) -> np.ndarray:
    from ampscape.sources.generators import _largest_component_mask

    comp, _ = _largest_component_mask(R, nd)
    return comp


def source_for_rule(rule: str, R: np.ndarray, nd: np.ndarray, s_prod: np.ndarray, sid: str, tier: str) -> np.ndarray:
    if rule == "default":
        return s_prod.astype(np.float32)
    comp = _largest_component(R, nd)
    if rule == "uniform":
        s = comp.astype(np.float64)
    elif rule == "random_field":
        from ampscape.landscapes.synthetic import gaussian_random_field

        seed = int(hashlib.sha1(f"r3-random_field|{sid}".encode()).hexdigest()[:8], 16)
        f = gaussian_random_field(R.shape, 16.0 * TIER_SCALE[tier], np.random.default_rng(seed)).astype(np.float64)
        thr = float(np.median(f[comp]))
        s = np.where(comp & (f >= thr), f - thr, 0.0)
    elif rule == "habitat_core":
        q = np.where(comp, (1.0 / np.asarray(R, np.float64)) ** 2, 0.0)
        thr = float(np.quantile(q[comp], 0.8))
        s = np.where(comp & (q >= thr), q, 0.0)
    else:
        raise ValueError(rule)
    if s.max() <= 0:
        s = comp.astype(np.float64)
    return (s / s.max()).astype(np.float32)


def cmd_build(a):
    from huggingface_hub import hf_hub_download

    from ampscape.io.pagecache import drop_file_cache
    from ampscape.solve.prepare import omni_params

    out = pathlib.Path(a.out)
    sel = pd.read_parquet(a.sel or out / "selection.parquet").reset_index(drop=True)
    sel["shard"] = np.arange(len(sel)) // a.shard_size
    sel["configs"] = json.dumps(["omniscape"])
    sel["tier"] = a.tier
    sel["rule"] = a.rule
    radius, prod_block = omni_params(a.tier)
    block = a.block or prod_block
    (out / "inputs").mkdir(parents=True, exist_ok=True)
    sel.to_parquet(out / "manifest.parquet", index=False)
    (out / "build.json").write_text(
        json.dumps(
            {
                "dataset_id": "ampscape-v1.0",
                "tier": a.tier,
                "solver_preset": "configs/solver/circuitscape_reference.yaml",
                "dataset_version": f"aux-r3-{a.rule}-block{block}",
                "aux": {"source": "hub", "rule": a.rule, "block_size": block, "radius": radius,
                        "production_block": prod_block, "correct_artifacts": int(a.correct_artifacts)},
                "shard_size": a.shard_size,
            },
            indent=1,
        )
    )
    for sh, g in sel.groupby("shard"):
        p = out / "inputs" / f"shard-{sh:05d}.inputs.h5"
        if (out / "outputs" / f"shard-{sh:05d}.outputs.h5").exists() and p.exists():
            continue
        with h5py.File(p, "w") as fo:
            gs = fo.create_group("samples")
            for hf_path, gg in g.groupby("hf_path", sort=False):
                src = hf_hub_download(REPO, hf_path, repo_type="dataset", cache_dir=str(CACHE))
                with h5py.File(src, "r") as fi:
                    for sid in gg.sample_id:
                        gi = fi[sid]
                        R = gi["inputs"]["resistance"][...]
                        nd = gi["inputs"]["nodata_mask"][...]
                        sp = gi["configs"]["omniscape"]["inputs"]["source_strength"][...]
                        stats = json.loads(gi["configs"]["omniscape"]["outputs"].attrs["solver_stats"])
                        pp = stats.get("solver_params", {})
                        assert int(pp.get("radius", radius)) == radius, (sid, pp)
                        s = source_for_rule(a.rule, R, nd > 0, sp, sid, a.tier)
                        g2 = gs.create_group(sid)
                        g2.attrs["tier"] = a.tier
                        g2.attrs["omni_radius"] = radius
                        g2.attrs["omni_block_size"] = int(block)
                        g2.attrs["omni_correct_artifacts"] = int(a.correct_artifacts)
                        g2.attrs["cg_baseline"] = 0
                        meta = json.loads(gi.attrs["meta"])
                        meta["r3"] = {"rule": a.rule, "block_size": int(block), "production_block": int(pp.get("block_size", prod_block)),
                                      "hf_path": hf_path, "n_source_pixels": int((s > 0).sum())}
                        g2.attrs["meta"] = json.dumps(meta, default=float)
                        ins = g2.create_group("inputs")
                        ins.create_dataset("resistance", data=R.astype(np.float32), compression="gzip", compression_opts=4)
                        ins.create_dataset("nodata_mask", data=nd.astype(np.uint8), compression="gzip", compression_opts=4)
                        gc = g2.create_group("configs").create_group("omniscape")
                        gc.attrs["kind"] = "omniscape"
                        gc.attrs["source_threshold"] = 0.0
                        gc.create_dataset("source_strength", data=s, compression="gzip", compression_opts=4)
                drop_file_cache(src)
        drop_file_cache(p, fsync=True)
        print(f"shard {sh}: {len(g)} samples, rule {a.rule}, block {block}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--tier", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--quota", required=True)
    s.set_defaults(fn=cmd_select)
    b = sub.add_parser("build")
    b.add_argument("--tier", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--sel", default=None)
    b.add_argument("--block", type=int, default=None, help="Omniscape block size (default: production)")
    b.add_argument("--rule", default="default", choices=RULES)
    b.add_argument("--shard-size", type=int, default=10)
    b.add_argument("--correct-artifacts", type=int, default=1, help="Omniscape artefact correction (1 = production)")
    b.set_defaults(fn=cmd_build)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
