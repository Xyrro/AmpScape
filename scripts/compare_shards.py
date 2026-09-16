#!/usr/bin/env python
"""Bitwise comparison of two shard sets (freeze checklist b): every dataset must be byte-identical; attributes are
compared after dropping run-specific provenance (created_at, pipeline_git_sha/tag, hostname, timings, memory).
  python scripts/compare_shards.py --a data/dev/S/shards --b data/repro/S/shards --out data/repro/S_compare.json
"""

from __future__ import annotations

import argparse
import json
import pathlib

import h5py
import numpy as np

VOLATILE = {
    "created_at",
    "pipeline_git_sha",
    "pipeline_tag",
    "hostname",
    "wall_s",
    "maxrss_mb",
    "started_utc",
    "time_to_1e-06",
    "time_to_2e-12",
    "n_threads",
    "blas_threads",
}


def strip(obj):
    if isinstance(obj, dict):
        return {k: strip(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [strip(v) for v in obj]
    return obj


def norm_attr(v):
    if isinstance(v, (bytes, np.bytes_)):
        v = v.decode()
    if isinstance(v, str) and v[:1] in "{[":
        try:
            return strip(json.loads(v))
        except json.JSONDecodeError:
            return v
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, np.generic):
        return v.item()
    return v


def compare(fa: h5py.File, fb: h5py.File, rep: dict, path: str = "/") -> None:
    ga, gb = fa[path], fb[path]
    for k in set(ga.attrs) | set(gb.attrs):
        if k in VOLATILE:
            continue
        if norm_attr(ga.attrs.get(k)) != norm_attr(gb.attrs.get(k)):
            rep["attr_diffs"].append(f"{path}@{k}")
    ka, kb = set(ga.keys()), set(gb.keys())
    for k in ka ^ kb:
        rep["missing"].append(f"{path}{k}")
    for k in sorted(ka & kb):
        pa, pb = ga[k], gb[k]
        if isinstance(pa, h5py.Dataset):
            rep["n_datasets"] += 1
            if (
                pa.shape != pb.shape
                or pa.dtype != pb.dtype
                or not np.array_equal(pa[...], pb[...], equal_nan=True)
            ):
                rep["dataset_diffs"].append(f"{path}{k}")
                if pa.shape == pb.shape and pa.dtype.kind == "f":
                    a, b = pa[...].astype(np.float64), pb[...].astype(np.float64)
                    rep["max_rel_diff"] = max(
                        rep["max_rel_diff"],
                        float(np.nanmax(np.abs(a - b)) / (np.nanmax(np.abs(a)) + 1e-30)),
                    )
        else:
            compare(fa, fb, rep, f"{path}{k}/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for pb in sorted(pathlib.Path(a.b).glob("shard-*.h5")):
        pa = pathlib.Path(a.a) / pb.name
        rep = {
            "n_datasets": 0,
            "dataset_diffs": [],
            "attr_diffs": [],
            "missing": [],
            "max_rel_diff": 0.0,
        }
        with h5py.File(pa, "r") as fa, h5py.File(pb, "r") as fb:
            compare(fa, fb, rep)
        rep["bitwise_identical"] = not (rep["dataset_diffs"] or rep["missing"])
        rep["identical_incl_attrs"] = rep["bitwise_identical"] and not rep["attr_diffs"]
        out[pb.name] = rep
        print(
            pb.name,
            "datasets",
            rep["n_datasets"],
            "| bitwise identical:",
            rep["bitwise_identical"],
            "| attr diffs:",
            len(rep["attr_diffs"]),
            "| dataset diffs:",
            len(rep["dataset_diffs"]),
            "| max rel diff:",
            rep["max_rel_diff"],
        )
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
