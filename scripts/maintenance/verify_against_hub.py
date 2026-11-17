"""Verify local copies against the Hub before deleting them (owner 2026-10-26: delete only what is reproducible).

For every local file under LOCAL_DIR, look up REPO_PREFIX/<relative path> on the Hub at REVISION and compare the content
hash: sha256 for LFS/xet files, the git blob sha1 for regular files. Writes a JSON report; exit 0 only when every file
matches.

    python scripts/maintenance/verify_against_hub.py --local data/hfcache/data/XL/T4 --prefix data/XL/T4 \
        --revision v1.0.2 --out work/delete_check/XL_T4.json
    python scripts/maintenance/verify_against_hub.py --local runs/full --prefix aux/results/runs_full \
        --include '*/best.pt' --out work/delete_check/best_pt.json   # only files matching the glob
    python scripts/maintenance/verify_against_hub.py --local aux/t4_bs1_reference --prefix aux/t4_bs1_reference \
        --include '**/*.h5' --by-content --out work/delete_check/bs1.json
        # match by content anywhere under --prefix (renamed or merged builds); the report records the Hub path of each
"""

import argparse
import hashlib
import json
import os
import pathlib
import sys

REPO = "Xirro/AmpScape"


def hashes(path: pathlib.Path) -> tuple[str, str]:
    sha256, sha1 = hashlib.sha256(), hashlib.sha1()
    sha1.update(b"blob %d\0" % path.stat().st_size)
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            sha256.update(chunk)
            sha1.update(chunk)
        os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return sha256.hexdigest(), sha1.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", required=True)
    ap.add_argument("--prefix", required=True, help="path in the Hub repo that corresponds to --local")
    ap.add_argument("--revision", default="main")
    ap.add_argument("--out", required=True)
    ap.add_argument("--include", default="*", help="glob relative to --local; only matching files are checked")
    ap.add_argument("--by-content", action="store_true", help="match each file by hash anywhere under --prefix")
    a = ap.parse_args()
    from huggingface_hub import HfApi

    hub, by_hash = {}, {}
    for e in HfApi().list_repo_tree(REPO, path_in_repo=a.prefix, recursive=True, repo_type="dataset", revision=a.revision):
        if hasattr(e, "blob_id"):
            hub[e.path] = (e.lfs.sha256 if e.lfs else None, e.blob_id, e.size)
            by_hash[e.lfs.sha256 if e.lfs else e.blob_id] = e.path
    local = pathlib.Path(a.local)
    files = sorted(p for p in local.glob(a.include) if p.is_file()) if a.include != "*" else sorted(
        p for p in local.rglob("*") if p.is_file())
    ok, bad, where = 0, [], {}
    for p in files:
        rp = f"{a.prefix}/{p.relative_to(local).as_posix()}"
        if a.by_content:
            s256, s1 = hashes(p)
            hp = by_hash.get(s256) or by_hash.get(s1)
            if hp is None:
                bad.append({"path": rp, "problem": "content not on Hub"})
            else:
                ok += 1
                where[p.relative_to(local).as_posix()] = hp
            continue
        if rp not in hub:
            bad.append({"path": rp, "problem": "missing on Hub"})
            continue
        lfs256, blob, size = hub[rp]
        s256, s1 = hashes(p)
        if (lfs256 and s256 != lfs256) or (not lfs256 and s1 != blob) or p.stat().st_size != size:
            bad.append({"path": rp, "problem": "hash or size mismatch"})
        else:
            ok += 1
    rep = {"local": a.local, "prefix": a.prefix, "revision": a.revision, "files": len(files), "matched": ok,
           "bytes": sum(p.stat().st_size for p in files), "problems": bad}
    if a.by_content:
        rep["hub_path"] = where  # local relative path -> Hub path holding identical bytes
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k not in ("problems", "hub_path")}), f"problems={len(bad)}")
    sys.exit(0 if not bad and files else 1)


if __name__ == "__main__":
    main()
