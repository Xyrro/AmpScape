#!/usr/bin/env python
"""Drop clean page cache for the scratch roots (login-node 4 GB memory cgroup; see ampscape/io/pagecache.py).

  python scripts/evict_cache.py                      # sweep data runs work aux .hf_cache logs; print memory before/after
  python scripts/evict_cache.py --if-above-gb 2.5    # only when the cgroup's memory.current exceeds 2.5 GB
  python scripts/evict_cache.py --roots runs/full --max-age-hours 6

Run by scripts/slurm/gpu/keepalive.sh every 10 minutes and whenever memory.current > 2.5 GB. Harmless anywhere else
(fadvise on an uncached file is a no-op); ≈ 2 min of mostly idle Lustre metadata time for the full sweep (82 k files).
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ampscape.io.pagecache import cgroup_memory, drop_tree_cache  # noqa: E402

DEFAULT_ROOTS = ["data", "runs", "work", "aux", ".hf_cache", "logs"]


def gb(x: int | None) -> str:
    return "n/a" if x is None else f"{x / 2**30:.2f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS, help="relative to the repo root")
    ap.add_argument("--min-size", type=int, default=0, help="skip files smaller than this (bytes)")
    ap.add_argument("--max-age-hours", type=float, default=None, help="only files modified within")
    ap.add_argument(
        "--if-above-gb",
        type=float,
        default=None,
        help="do nothing unless the cgroup memory.current exceeds this many GiB",
    )
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    before = cgroup_memory()
    if a.if_above_gb is not None and before.get("current", 0) <= a.if_above_gb * 2**30:
        if not a.quiet:
            print(f"memory.current {gb(before.get('current'))} GiB <= {a.if_above_gb}: nothing to do")
        return 0
    roots = [ROOT / r for r in a.roots if (ROOT / r).exists()]
    res = drop_tree_cache(
        roots,
        min_size=a.min_size,
        max_age_s=None if a.max_age_hours is None else a.max_age_hours * 3600,
    )
    after = cgroup_memory()
    print(
        f"{dt.datetime.now(dt.UTC).isoformat(timespec='seconds')} evict_cache: {res['files']} files, "
        f"{res['bytes'] / 1e9:.1f} GB advised in {res['seconds']} s; memory.current {gb(before.get('current'))} -> "
        f"{gb(after.get('current'))} GiB (file {gb(before.get('file'))} -> {gb(after.get('file'))}, "
        f"anon {gb(after.get('anon'))}, max {gb(after.get('max'))})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
