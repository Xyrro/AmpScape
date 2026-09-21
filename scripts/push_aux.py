#!/usr/bin/env python
"""Push an auxiliary build / result directory to the Hub under aux/ (owner 2026-09-21: evaluation sets and results
must never be scratch-only). Files are uploaded in commits of ≤ --commit-gb, every LFS file's sha256 is verified on the
Hub, and the record is kept in <src>/.hub_pushed.json so a re-run only pushes new or changed files. Nothing is deleted.

  python scripts/push_aux.py --src data/dev/S --dest aux/dev/S --include 'shards/*.h5' 'index/*.parquet' index.parquet \\
      'manifest*.parquet' build.json 'splits/*' 'stats/*'
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time

from ampscape.io.sync import remote_sha256, sha256


def collect(src: pathlib.Path, patterns: list[str]) -> list[pathlib.Path]:
    out: set[pathlib.Path] = set()
    for pat in patterns:
        for p in src.glob(pat):
            if p.is_file():
                out.add(p)
            elif p.is_dir():
                out.update(q for q in p.rglob("*") if q.is_file())
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dest", required=True, help="path prefix in the repo, e.g. aux/dev/S")
    ap.add_argument(
        "--include", nargs="+", required=True, help="globs relative to --src (dirs are recursed)"
    )
    ap.add_argument("--repo", default="Xirro/AmpScape")
    ap.add_argument("--commit-gb", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    from huggingface_hub import CommitOperationAdd, HfApi

    src = pathlib.Path(a.src)
    rec_f = src / ".hub_pushed.json"
    rec = json.loads(rec_f.read_text()) if rec_f.exists() else {}
    files = collect(src, a.include)
    todo = []
    for p in files:
        rel = str(p.relative_to(src))
        h = sha256(p)
        if rec.get(rel, {}).get("sha256") == h:
            continue
        todo.append((p, rel, h))
    tot = sum(p.stat().st_size for p, _, _ in todo)
    print(
        f"{a.src} -> {a.dest}: {len(files)} files, {len(todo)} to push ({tot / 1e9:.2f} GB)",
        flush=True,
    )
    if a.dry_run or not todo:
        return 0
    api = HfApi()
    batch, size = [], 0
    batches = []
    for item in todo:
        batch.append(item)
        size += item[0].stat().st_size
        if size >= a.commit_gb * 1e9:
            batches.append(batch)
            batch, size = [], 0
    if batch:
        batches.append(batch)
    for i, b in enumerate(batches, 1):
        ops = [
            CommitOperationAdd(path_in_repo=f"{a.dest}/{rel}", path_or_fileobj=str(p))
            for p, rel, _ in b
        ]
        for attempt in range(4):
            try:
                res = api.create_commit(
                    a.repo,
                    operations=ops,
                    repo_type="dataset",
                    commit_message=f"aux: {a.dest} ({len(b)} files, batch {i}/{len(batches)})",
                )
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    raise
                print(f"  retry {attempt + 1}: {str(e)[:200]}", flush=True)
                time.sleep(30 * (attempt + 1))
        bad = 0
        for p, rel, h in b:
            remote = remote_sha256(api, a.repo, f"{a.dest}/{rel}")
            if (
                remote is None
            ):  # small non-LFS file: the Hub keeps it as a regular blob; re-download and compare
                from huggingface_hub import hf_hub_download

                local = hf_hub_download(a.repo, f"{a.dest}/{rel}", repo_type="dataset")
                remote = sha256(pathlib.Path(local))
            if remote != h:
                bad += 1
                print(f"  MISMATCH {rel}", flush=True)
                continue
            rec[rel] = {
                "sha256": h,
                "bytes": p.stat().st_size,
                "path": f"{a.dest}/{rel}",
                "commit": getattr(res, "oid", None),
                "pushed_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            }
        rec_f.write_text(json.dumps(rec, indent=1))
        print(
            f"  batch {i}/{len(batches)}: {len(b)} files, {sum(p.stat().st_size for p, _, _ in b) / 1e9:.2f} GB, {bad} mismatches",
            flush=True,
        )
        if bad:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
