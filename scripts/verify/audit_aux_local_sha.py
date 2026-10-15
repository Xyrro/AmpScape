#!/usr/bin/env python
"""Verification item 5 (aux/), second pass: for every Hub file under aux/ that has no push record
(audit_aux_hub.py `missing_record`), hash the local source file and compare with the Hub's LFS sha256.

  python scripts/verify/audit_aux_local_sha.py --audit work/verify/audit_aux.json --out work/verify/audit_aux_sha.json

Local source per Hub prefix (docs/aux_layout.md): aux/dev/<tier> ← data/dev/<tier>; aux/results/runs_full/<run> ←
runs/full/<run>; aux/t1_pair1, aux/t4_* ← same path; the Markdown/PNG copies at the top of aux/ ← docs/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time

from huggingface_hub import HfApi

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAP = {
    "aux/dev/": "data/dev/",
    "aux/results/runs_full/": "runs/full/",
    "aux/results/runs_dev/": "runs/dev/",
    "aux/results/runs_tune/": "runs/tune/",
    "aux/results/predictions/": "data/predictions/",
    "aux/mini/": "data/builds/mini/",
    "aux/test_ood_published/": "data/builds/published/",
    "aux/README.md": "docs/aux_layout.md",
    "aux/dataset_statistics.md": "docs/tables/dataset_statistics.md",
    "aux/generation_postmortem.md": "docs/generation_postmortem.md",
    "aux/precision_pass.md": "docs/tables/precision_pass.md",
    "aux/figures/": "docs/figures/",
}


def local_path(hub_path: str) -> pathlib.Path | None:
    for pre, loc in MAP.items():
        if hub_path == pre:
            return ROOT / loc
        if pre.endswith("/") and hub_path.startswith(pre):
            return ROOT / loc / hub_path[len(pre):]
    p = ROOT / hub_path
    return p if p.exists() else None


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default="Xirro/AmpScape")
    a = ap.parse_args()
    aud = json.loads(pathlib.Path(a.audit).read_text())
    todo = aud["missing_record"]
    api = HfApi()
    hub = {}
    for it in api.list_repo_tree(a.repo, repo_type="dataset", path_in_repo="aux", recursive=True, expand=True):
        if getattr(it, "size", None) is None:
            continue
        lfs = getattr(it, "lfs", None)
        hub[it.path] = {"bytes": it.size, "sha256": (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None}
    t0 = time.time()
    res = {"match": [], "mismatch": [], "no_local": [], "no_hub_sha": []}
    gb = 0.0
    for hp in todo:
        lp = local_path(hp)
        h = hub.get(hp, {})
        if lp is None or not lp.exists():
            res["no_local"].append(hp)
            continue
        if not h.get("sha256"):
            # small non-LFS file: compare bytes only after downloading would be needed; compare size
            res["no_hub_sha"].append({"path": hp, "local_bytes": lp.stat().st_size, "hub_bytes": h.get("bytes")})
            continue
        s = sha256(lp)
        gb += lp.stat().st_size / 1e9
        (res["match"] if s == h["sha256"] else res["mismatch"]).append({"path": hp, "local": str(lp.relative_to(ROOT)), "local_sha256": s, "hub_sha256": h["sha256"]} if s != h["sha256"] else hp)
    out = {"n_todo": len(todo), "n_match": len(res["match"]), "n_mismatch": len(res["mismatch"]), "n_no_local": len(res["no_local"]), "n_no_hub_sha": len(res["no_hub_sha"]), "gb_hashed": round(gb, 2), "seconds": round(time.time() - t0), **res}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"local-sha pass: {out['n_todo']} unrecorded Hub files; {out['n_match']} match, {out['n_mismatch']} mismatch, {out['n_no_local']} without local source, {out['n_no_hub_sha']} non-LFS (size compared only); {out['gb_hashed']} GB hashed in {out['seconds']} s")
    for m in res["mismatch"][:40]:
        print("  mismatch:", m["path"], "local", m["local"])
    for m in res["no_hub_sha"][:20]:
        print("  non-LFS:", m)
    for p in res["no_local"][:20]:
        print("  no local source:", p)


if __name__ == "__main__":
    main()
