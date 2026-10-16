#!/usr/bin/env python
"""Verification item 5: fetch a Hub file whose LFS size metadata disagrees with its content (huggingface_hub refuses
it: "Consistency check failed"), by a plain streamed GET of the resolve URL, then validate the HDF5 content (opens,
group count against the index's expected sample count) and hash it, so the owner can decide whether to re-upload.

  python scripts/verify/fetch_inconsistent.py --path aux/results/runs_full/<run>/predictions/<tag>/predictions.h5 \
      --expect-groups 275 --out work/verify/fix/
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import time

import h5py
import requests
from huggingface_hub import get_token, hf_hub_url


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Xirro/AmpScape")
    ap.add_argument("--path", required=True)
    ap.add_argument("--expect-groups", type=int, default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    url = hf_hub_url(a.repo, a.path, repo_type="dataset")
    dest = pathlib.Path(a.out) / a.path
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    h = hashlib.sha256()
    n = 0
    with requests.get(url, headers={"Authorization": f"Bearer {get_token()}"}, stream=True, allow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        declared = r.headers.get("Content-Length")
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(1 << 24):
                fh.write(chunk)
                h.update(chunk)
                n += len(chunk)
    print(f"{a.path}: {n} bytes in {time.time() - t0:.0f} s (Content-Length {declared}); sha256 {h.hexdigest()}")
    try:
        with h5py.File(dest, "r") as f:
            keys = list(f.keys())
            print(f"  HDF5 opens: {len(keys)} top-level groups; expected {a.expect_groups}")
            ok = a.expect_groups is None or len(keys) == a.expect_groups
            # every group must hold the config subgroup with a cum_current dataset
            bad = 0
            for k in keys:
                g = f[k]
                if not any("cum_current" in g[c] for c in g.keys()):
                    bad += 1
            print(f"  groups without cum_current: {bad}")
            print("RESULT:", "COMPLETE" if ok and bad == 0 else "INCOMPLETE")
    except Exception as e:  # noqa: BLE001
        print("  HDF5 does not open:", repr(e))
        print("RESULT: CORRUPT")


if __name__ == "__main__":
    main()
