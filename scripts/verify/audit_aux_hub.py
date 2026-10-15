#!/usr/bin/env python
"""Verification (owner, 2026-10-15, item 5, aux/ part): every file under aux/ on the Hub against the local push
records (`<src>/.hub_pushed.json` written by scripts/push_aux.py after a sha256-verified upload).

For each Hub file: LFS sha256 and size from the repo tree (no download; the Hub stores the sha256 of every LFS
object and push_aux.py verified it at upload time) compared with the record of the same Hub path. Reports files on the
Hub without a record, records without a Hub file, and sha256/size mismatches; writes <out> as JSON and a summary.

  python scripts/verify/audit_aux_hub.py --out work/verify/audit_aux.json [--records <dir> ...]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import time

from huggingface_hub import HfApi

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD_ROOTS = ["aux", "runs/full", "runs/dev", "runs/tune", "data/dev", "data/builds", "data/predictions", "data/scale_probe"]


def local_records(roots: list[str]) -> dict[str, dict]:
    rec: dict[str, dict] = {}
    for r in roots:
        base = ROOT / r
        if not base.exists():
            continue
        for p in base.rglob(".hub_pushed.json"):
            try:
                d = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError) as e:
                print(f"unreadable record {p}: {e}")
                continue
            for rel, e in d.items():
                if isinstance(e, dict) and "path" in e:
                    rec[e["path"]] = {"sha256": e.get("sha256"), "bytes": e.get("bytes"), "record": str(p.relative_to(ROOT))}
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Xirro/AmpScape")
    ap.add_argument("--prefix", default="aux")
    ap.add_argument("--out", required=True)
    ap.add_argument("--records", nargs="*", default=RECORD_ROOTS)
    a = ap.parse_args()
    t0 = time.time()
    api = HfApi()
    hub: dict[str, dict] = {}
    for it in api.list_repo_tree(a.repo, repo_type="dataset", path_in_repo=a.prefix, recursive=True, expand=True):
        size = getattr(it, "size", None)
        if size is None:
            continue  # folder
        lfs = getattr(it, "lfs", None)
        sha = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None
        hub[it.path] = {"bytes": size, "sha256": sha, "lfs": lfs is not None}
    rec = local_records(a.records)
    missing_record = sorted(p for p in hub if p not in rec)
    missing_hub = sorted(p for p in rec if p.startswith(a.prefix + "/") and p not in hub)
    mismatch = []
    for p, h in hub.items():
        r = rec.get(p)
        if not r:
            continue
        if h["sha256"] and r["sha256"] and h["sha256"] != r["sha256"]:
            mismatch.append({"path": p, "hub_sha256": h["sha256"], "record_sha256": r["sha256"], "record": r["record"]})
        elif r["bytes"] is not None and h["bytes"] != r["bytes"]:
            mismatch.append({"path": p, "hub_bytes": h["bytes"], "record_bytes": r["bytes"], "record": r["record"]})
    per_top = collections.Counter()
    gb_top = collections.Counter()
    for p, h in hub.items():
        top = "/".join(p.split("/")[:2])
        per_top[top] += 1
        gb_top[top] += h["bytes"] / 1e9
    non_lfs = [p for p, h in hub.items() if not h["lfs"]]
    out = {
        "repo": a.repo,
        "prefix": a.prefix,
        "n_hub_files": len(hub),
        "gb_hub": round(sum(h["bytes"] for h in hub.values()) / 1e9, 2),
        "n_records": sum(1 for p in rec if p.startswith(a.prefix + "/")),
        "n_matched": len(hub) - len(missing_record),
        "n_sha_checked": sum(1 for p, h in hub.items() if p in rec and h["sha256"] and rec[p]["sha256"]),
        "n_non_lfs": len(non_lfs),
        "missing_record": missing_record,
        "missing_hub": missing_hub,
        "mismatch": mismatch,
        "per_folder": {k: {"files": per_top[k], "gb": round(gb_top[k], 2)} for k in sorted(per_top)},
        "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seconds": round(time.time() - t0),
    }
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(
        f"aux audit: {len(hub)} Hub files ({out['gb_hub']} GB), {out['n_matched']} with a local record, "
        f"{out['n_sha_checked']} sha256-checked, {len(mismatch)} mismatches, {len(missing_record)} without record, "
        f"{len(missing_hub)} records without Hub file; {out['seconds']} s"
    )
    for k, v in out["per_folder"].items():
        print(f"  {k}: {v['files']} files, {v['gb']} GB")
    for p in missing_record[:30]:
        print("  no record:", p)
    for m in mismatch[:30]:
        print("  mismatch:", m)


if __name__ == "__main__":
    main()
