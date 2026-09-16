#!/usr/bin/env python
"""Confirm that re-uploaded shards replaced their Hub copies: same path, a newer commit, a different sha256 than the
previous version of the same path (from the repo history), and only one current object per path.
  python scripts/confirm_replaced.py --tier S --shards data/v1/S/short_shards.json"""

from __future__ import annotations

import argparse
import json
import pathlib

from huggingface_hub import HfApi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True)
    ap.add_argument("--shards", required=True, help="JSON list of [shard, ...] rows or ints")
    ap.add_argument("--repo", default="Xirro/AmpScape")
    a = ap.parse_args()
    api = HfApi()
    shards = [
        int(x[0] if isinstance(x, list) else x)
        for x in json.loads(pathlib.Path(a.shards).read_text())
    ]
    commits = api.list_repo_commits(a.repo, repo_type="dataset")  # newest first
    out, bad = {}, []
    for sh in shards:
        name = f"shard-{sh:05d}.h5"
        touching = [c for c in commits if name in (c.title or "")]
        if len(touching) < 2:
            bad.append((sh, f"only {len(touching)} commit(s) touch {name}"))
            continue
        newest, previous = touching[0], touching[1]
        paths = [f"data/{a.tier}/{g}/{name}" for g in ("T1", "T1W", "T1R", "T3", "T4")]
        cur = {
            i.path: getattr(getattr(i, "lfs", None), "sha256", None)
            for i in api.get_paths_info(a.repo, paths, repo_type="dataset", expand=True)
        }
        old = {
            i.path: getattr(getattr(i, "lfs", None), "sha256", None)
            for i in api.get_paths_info(
                a.repo, paths, repo_type="dataset", expand=True, revision=previous.commit_id
            )
        }
        same = [p for p in cur if cur[p] and cur[p] == old.get(p)]
        out[sh] = {
            "newest_commit": newest.commit_id[:8],
            "previous_commit": previous.commit_id[:8],
            "n_files": len(cur),
            "unchanged_files": same,
        }
        if same:
            bad.append((sh, f"{len(same)} file(s) have the same sha256 as before the re-upload"))
    print(
        json.dumps(
            {"checked": len(shards), "replaced": len(shards) - len(bad), "problems": bad}, indent=1
        )
    )
    pathlib.Path(f"data/v1/{a.tier}/replaced_check.json").write_text(
        json.dumps({"per_shard": out, "problems": bad}, indent=1)
    )


if __name__ == "__main__":
    main()
