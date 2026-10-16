#!/usr/bin/env python
"""Verification item 5 (aux/), third pass: Hub files under aux/ that have neither a push record nor a local source
(audit_aux_local_sha.py `no_local`) and the small non-LFS files are downloaded to a scratch directory, hashed against
the Hub's LFS sha256 (transfer integrity), opened (HDF5: group count; parquet: row count) and, for aux/dev/<tier>,
checked against their own index (every indexed sample present in its shard). Non-LFS Markdown copies are compared
byte-wise with the repository file they mirror.

  python scripts/verify/audit_aux_download.py --sha work/verify/audit_aux_sha.json --out work/verify/audit_aux_dl.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import tempfile
import time

from huggingface_hub import HfApi, hf_hub_download

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC_COPIES = {
    "aux/README.md": "docs/aux_layout.md",
    "aux/dataset_statistics.md": "docs/tables/dataset_statistics.md",
    "aux/generation_postmortem.md": "docs/generation_postmortem.md",
    "aux/precision_pass.md": "docs/tables/precision_pass.md",
    "aux/t1_pair1/README.md": "aux/t1_pair1/README.md",
    "aux/t4_bs1_reference/README.md": None,
}


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default="Xirro/AmpScape")
    a = ap.parse_args()
    prev = json.loads(pathlib.Path(a.sha).read_text())
    todo = list(prev["no_local"]) + [m["path"] for m in prev["no_hub_sha"]]
    api = HfApi()
    hub = {}
    for it in api.list_repo_tree(a.repo, repo_type="dataset", path_in_repo="aux", recursive=True, expand=True):
        if getattr(it, "size", None) is None:
            continue
        lfs = getattr(it, "lfs", None)
        hub[it.path] = {"bytes": it.size, "sha256": (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None}
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aux_audit_", dir=os.environ.get("TMPDIR", "/tmp")))
    t0 = time.time()
    res = {"ok": [], "bad": [], "doc_copy_stale": [], "doc_copy_same": []}
    gb = 0.0
    dev_index: dict[str, set] = {}
    for hp in sorted(todo):
        h = hub.get(hp)
        if not h:
            res["bad"].append({"path": hp, "why": "not on the Hub any more"})
            continue
        lp = pathlib.Path(hf_hub_download(a.repo, hp, repo_type="dataset", local_dir=str(tmp)))
        gb += lp.stat().st_size / 1e9
        entry = {"path": hp, "bytes": lp.stat().st_size}
        if h["sha256"]:
            entry["sha_ok"] = sha256(lp) == h["sha256"]
        else:
            entry["sha_ok"] = lp.stat().st_size == h["bytes"]
        if hp.endswith(".h5"):
            import h5py

            try:
                with h5py.File(lp, "r") as f:
                    entry["groups"] = len(f.keys())
                    entry["opens"] = True
                    if "/aux/dev/" in "/" + hp:
                        tier = hp.split("/")[2]
                        dev_index.setdefault(tier, set()).update(f.keys())
            except Exception as e:  # noqa: BLE001
                entry["opens"] = False
                entry["error"] = repr(e)
        elif hp.endswith(".parquet"):
            import pandas as pd

            try:
                entry["rows"] = int(len(pd.read_parquet(lp)))
                entry["opens"] = True
            except Exception as e:  # noqa: BLE001
                entry["opens"] = False
                entry["error"] = repr(e)
        if hp in DOC_COPIES and DOC_COPIES[hp]:
            src = ROOT / DOC_COPIES[hp]
            same = src.exists() and src.read_bytes() == lp.read_bytes()
            (res["doc_copy_same"] if same else res["doc_copy_stale"]).append({"hub": hp, "repo": DOC_COPIES[hp], "same": same})
        (res["ok"] if entry.get("sha_ok") and entry.get("opens", True) else res["bad"]).append(entry)
        lp.unlink(missing_ok=True)
    # aux/dev: every sample of the tier index must be in a shard we opened (when the index was among the downloads)
    dev_checks = {}
    for tier, ids in dev_index.items():
        idx_path = tmp / "aux" / "dev" / tier / "index.parquet"
        try:
            import pandas as pd

            p = hf_hub_download(a.repo, f"aux/dev/{tier}/index.parquet", repo_type="dataset", local_dir=str(tmp))
            idx = pd.read_parquet(p)
            missing = set(idx.sample_id) - ids
            dev_checks[tier] = {"index_samples": int(idx.sample_id.nunique()), "shard_groups": len(ids), "missing_from_shards": len(missing)}
        except Exception as e:  # noqa: BLE001
            dev_checks[tier] = {"error": repr(e)}
    out = {"n_todo": len(todo), "n_ok": len(res["ok"]), "n_bad": len(res["bad"]), "gb_downloaded": round(gb, 2), "seconds": round(time.time() - t0), "dev_checks": dev_checks, **res}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"download pass: {len(todo)} files, {out['n_ok']} ok, {out['n_bad']} bad, {out['gb_downloaded']} GB in {out['seconds']} s; dev checks {dev_checks}")
    for b in res["bad"][:20]:
        print("  bad:", b)
    for d in res["doc_copy_stale"]:
        print("  stale doc copy:", d)
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
