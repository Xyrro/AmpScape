"""Find files on scratch that are neither in git nor on the Hub (owner 2026-11-16: scratch may be purged, so everything
the paper needs must live on GitHub or the Hub).

Walks the working copy and skips git-tracked files (GitHub holds them once main is pushed) and the environments, the
Julia depot and download caches (rebuilt from uv.lock, Manifest.toml and the Hub). Every other file is hashed and looked
up by content anywhere in the Hub repo at REVISION: sha256 for LFS/xet files, the git blob sha1 otherwise. Writes a JSON
report with per-directory totals and every file found nowhere off scratch. Read-only; run as a Slurm CPU job.

    python scripts/maintenance/audit_offsite.py --out work/offsite_audit/report.json
"""

import argparse
import collections
import json
import os
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from verify_against_hub import REPO, hashes  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP_TOP = {
    ".git",
    "envs",
    "julia_depot",
    "tools",
}  # rebuilt from uv.lock / Manifest.toml / install scripts
SKIP_ANY = {
    ".uv_cache",
    ".pip_cache",
    ".hf_cache",
    ".cache",
    ".conda_pkgs",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".ipynb_checkpoints",
}


def walk() -> tuple[list[pathlib.Path], list[str]]:
    files, links = [], []
    for d, dirs, names in os.walk(ROOT):
        rel = pathlib.Path(d).relative_to(ROOT)
        dirs[:] = [
            x
            for x in dirs
            if x not in SKIP_ANY and not (rel == pathlib.Path(".") and x in SKIP_TOP)
        ]
        for n in names:
            p = pathlib.Path(d) / n
            if p.is_symlink():
                links.append(p.relative_to(ROOT).as_posix())
            elif p.is_file():
                files.append(p)
    return files, links


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", default="main")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    from huggingface_hub import HfApi

    on_hub = {}
    for e in HfApi().list_repo_tree(REPO, recursive=True, repo_type="dataset", revision=a.revision):
        if hasattr(e, "blob_id"):
            on_hub[e.lfs.sha256 if e.lfs else e.blob_id] = e.path
    print(f"hub files at {a.revision}: {len(on_hub)}", flush=True)
    tracked = set(
        subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True, text=True
        ).stdout.split("\0")
    )
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.splitlines()
    files, links = walk()
    files = [p for p in files if p.relative_to(ROOT).as_posix() not in tracked]
    print(f"untracked or ignored files to check: {len(files)}", flush=True)

    def one(p: pathlib.Path) -> tuple[str, int, str | None, float]:
        st = p.stat()
        s256, s1 = hashes(p)
        return (
            p.relative_to(ROOT).as_posix(),
            st.st_size,
            on_hub.get(s256) or on_hub.get(s1),
            st.st_mtime,
        )

    by_dir = collections.defaultdict(
        lambda: {"files": 0, "bytes": 0, "nowhere": 0, "nowhere_bytes": 0}
    )
    nowhere, matched = [], {}
    with ThreadPoolExecutor(a.workers) as ex:
        for i, (rel, size, hp, mtime) in enumerate(ex.map(one, files), 1):
            parts = rel.split("/")[:-1] or ["."]  # folders only, down to three levels
            for k in {"/".join(parts[:n]) for n in (1, 2, 3) if n <= len(parts)}:
                by_dir[k]["files"] += 1
                by_dir[k]["bytes"] += size
                if hp is None:
                    by_dir[k]["nowhere"] += 1
                    by_dir[k]["nowhere_bytes"] += size
            if hp is None:
                nowhere.append({"path": rel, "size": size, "mtime": round(mtime)})
            else:
                matched[rel] = hp
            if i % 5000 == 0:
                print(f"{i}/{len(files)}", flush=True)
    rep = {
        "revision": a.revision,
        "hub_files": len(on_hub),
        "tracked_modified": dirty,
        "symlinks": links,
        "checked": len(files),
        "bytes": sum(d["bytes"] for k, d in by_dir.items() if "/" not in k),
        "by_dir": dict(sorted(by_dir.items())),
        "nowhere": sorted(nowhere, key=lambda r: r["path"]),
        "on_hub": matched,
    }
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(rep, indent=1))
    print(
        json.dumps(
            {
                "checked": len(files),
                "nowhere": len(nowhere),
                "nowhere_gb": round(sum(r["size"] for r in nowhere) / 1e9, 3),
                "tracked_modified": len(dirty),
            }
        )
    )


if __name__ == "__main__":
    main()
