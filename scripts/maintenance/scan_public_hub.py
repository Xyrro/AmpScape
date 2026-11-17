"""Scan the public dataset repo Xirro/AmpScape for credentials and identifying content (owner 2026-11-16: "do not have
any credentials or id or any sensitive content in the public repo").

Downloads every file at REVISION except the HDF5 shards and checkpoints (JSON, Markdown, logs, CSV, parquet, GeoTIFF,
PNG, ...) to node-local temp, plus the smallest HDF5 file of every folder group (attributes and small string datasets
are scanned), and scans all of them with the patterns of `scan_sensitive.py`. Also scans every commit title and message.
Writes a JSON report with per-pattern counts by top-level folder and examples. Read-only. Run as a Slurm CPU job.

    python scripts/maintenance/scan_public_hub.py --out work/offsite_audit/public_hub_scan.json
"""

import argparse
import collections
import json
import os
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scan_sensitive import PAT, tally  # noqa: E402

REPO = "Xirro/AmpScape"


def group_of(path: str) -> str:
    """Folder group for HDF5 sampling: data/<tier>/<task>; aux/results/<kind>; aux/<name>; run names dropped."""
    parts = path.split("/")
    if parts[0] == "data":
        return "/".join(parts[:3])
    if parts[:2] == ["aux", "results"]:
        return "/".join(parts[:3]) + "/*/" + parts[-1]
    return "/".join(parts[:2])


def top_of(path: str) -> str:
    parts = path.split("/")
    return (
        "/".join(parts[:3])
        if parts[0] == "aux" and len(parts) > 3
        else "/".join(parts[:2])
        if len(parts) > 1
        else parts[0]
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", default="main")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download

    api = HfApi()
    files = [
        e
        for e in api.list_repo_tree(REPO, recursive=True, repo_type="dataset", revision=a.revision)
        if hasattr(e, "blob_id")
    ]
    small = [e.path for e in files if not e.path.endswith((".h5", ".pt"))]
    h5 = {}
    for e in files:
        if e.path.endswith(".h5"):
            g = group_of(e.path)
            if g not in h5 or e.size < h5[g].size:
                h5[g] = e
    print(
        f"{len(files)} files; downloading {len(small)} non-HDF5 files and {len(h5)} HDF5 samples "
        f"({sum(e.size for e in h5.values()) / 1e9:.1f} GB)",
        flush=True,
    )
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        snapshot_download(
            REPO,
            repo_type="dataset",
            revision=a.revision,
            local_dir=tmp,
            ignore_patterns=["*.h5", "*.pt"],
            max_workers=8,
        )
        for e in h5.values():
            hf_hub_download(REPO, e.path, repo_type="dataset", revision=a.revision, local_dir=tmp)
        local = small + [e.path for e in h5.values()]
        missing = [p for p in local if not (pathlib.Path(tmp) / p).is_file()]
        print(f"downloaded; missing {len(missing)}", flush=True)
        cwd = os.getcwd()
        os.chdir(tmp)  # scan_file takes paths relative to the working directory
        try:
            jobs = [(p, top_of(p)) for p in local]
            hits, ex, errors = tally(jobs, int(os.environ.get("SLURM_CPUS_PER_TASK", "4")))
        finally:
            os.chdir(cwd)
    commit_hits = collections.Counter()
    commit_ex = collections.defaultdict(list)
    commits = api.list_repo_commits(REPO, repo_type="dataset", revision=a.revision)
    for c in commits:
        text = f"{c.title}\n{c.message or ''}".encode()
        for k, p in PAT.items():
            m = re.search(p, text)
            if m:
                commit_hits[k] += 1
                if len(commit_ex[k]) < 4:
                    commit_ex[k].append(
                        f"{c.commit_id[:8]}: {text[max(0, m.start() - 40) : m.end() + 40].decode()}"
                    )
    rep = {
        "revision": a.revision,
        "files": len(files),
        "scanned_non_h5": len(small),
        "h5_samples": {g: e.path for g, e in sorted(h5.items())},
        "hits_by_folder": hits,
        "examples": ex,
        "errors": errors[:50],
        "n_errors": len(errors),
        "missing_downloads": missing,
        "commits": len(commits),
        "commit_hits": dict(commit_hits),
        "commit_examples": dict(commit_ex),
    }
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: sum(v.values()) for k, v in hits.items()}), "commits:", dict(commit_hits))


if __name__ == "__main__":
    main()
