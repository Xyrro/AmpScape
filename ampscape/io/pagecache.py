"""Drop clean page cache for files this process has written or read (login-node memory hygiene).

PACE-ICE login nodes put each user in a 4 GB memory cgroup (`user-<uid>.slice`, `memory.max`). The kernel is supposed
to reclaim clean file pages before invoking the OOM killer, but on 2026-10-10 the cgroup sat at ≈ 3.85 GB of file cache
from our scratch (Lustre) I/O, `memory.reclaim` is not writable by the user, and processes in the slice were SIGKILLed
(the driver's Hub staging subprocesses in a loop, then the owner's tmux attach and SSH session). `posix_fadvise(...,
POSIX_FADV_DONTNEED)` over data/, runs/, work/ and .hf_cache cleared it. Rule since then: every file a login-node
daemon writes (fsync first) or reads is advised DONTNEED right after use, and `scripts/evict_cache.py` sweeps the
scratch roots periodically from the keepalive. Compute nodes are unaffected (their jobs run in Slurm cgroups).
"""

from __future__ import annotations

import os
import pathlib
import time
from collections.abc import Iterable

SKIP_DIRS = frozenset({".git", "__pycache__", ".venv", "julia_depot", "tools", "node_modules"})


def drop_file_cache(path: str | os.PathLike, *, fsync: bool = False) -> int:
    """Advise the kernel that this file's pages are not needed (whole file). With `fsync=True` the file's dirty pages
    are flushed first (a file we just wrote: dirty pages cannot be dropped). Returns the file size in bytes, or 0 when
    the file could not be opened / advised (never raises: this is hygiene, not correctness)."""
    try:
        fd = os.open(os.fspath(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return 0
    try:
        if fsync:
            try:
                os.fsync(fd)
            except OSError:
                pass
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        return os.fstat(fd).st_size
    except OSError:
        return 0
    finally:
        os.close(fd)


def drop_files_cache(paths: Iterable[str | os.PathLike], *, fsync: bool = False) -> int:
    return sum(drop_file_cache(p, fsync=fsync) for p in paths)


def drop_tree_cache(
    roots: Iterable[str | os.PathLike],
    *,
    min_size: int = 0,
    max_age_s: float | None = None,
    fsync: bool = False,
    skip_dirs: frozenset[str] = SKIP_DIRS,
) -> dict:
    """Walk `roots` (regular files only, symlinks not followed) and advise DONTNEED on each file; returns
    {"files": n_advised, "bytes": total_size, "seconds": wall}. `max_age_s` restricts the sweep to files modified
    within that window (a stat per file either way)."""
    t0 = time.monotonic()
    now = time.time()
    n = 0
    total = 0

    def walk(d: str) -> None:
        nonlocal n, total
        try:
            it = os.scandir(d)
        except OSError:
            return
        with it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        if e.name not in skip_dirs:
                            walk(e.path)
                    elif e.is_file(follow_symlinks=False):
                        if min_size or max_age_s is not None:
                            st = e.stat(follow_symlinks=False)
                            if st.st_size < min_size:
                                continue
                            if max_age_s is not None and now - st.st_mtime > max_age_s:
                                continue
                        b = drop_file_cache(e.path, fsync=fsync)
                        if b:
                            n += 1
                            total += b
                except OSError:
                    continue

    for r in roots:
        walk(os.fspath(r))
    return {"files": n, "bytes": total, "seconds": round(time.monotonic() - t0, 1)}


def cgroup_dir() -> pathlib.Path | None:
    """The user slice of this process' cgroup v2 path (the level that carries the 4 GB `memory.max` on PACE login
    nodes), or the leaf cgroup when no `user-<uid>.slice` component exists; None off cgroup v2."""
    try:
        line = pathlib.Path("/proc/self/cgroup").read_text().strip().splitlines()[-1]
    except (OSError, IndexError):
        return None
    rel = line.split("::", 1)[-1].strip("/")
    parts = rel.split("/") if rel else []
    for i, p in enumerate(parts):
        if p.startswith("user-") and p.endswith(".slice"):
            parts = parts[: i + 1]
            break
    d = pathlib.Path("/sys/fs/cgroup", *parts)
    return d if (d / "memory.current").exists() else None


def cgroup_memory() -> dict:
    """{"current", "max", "file", "anon"} in bytes (missing keys when unreadable; `max` may be None = unlimited)."""
    d = cgroup_dir()
    out: dict = {}
    if d is None:
        return out
    try:
        out["current"] = int((d / "memory.current").read_text())
        mx = (d / "memory.max").read_text().strip()
        out["max"] = None if mx == "max" else int(mx)
        for line in (d / "memory.stat").read_text().splitlines():
            k, _, v = line.partition(" ")
            if k in ("file", "anon"):
                out[k] = int(v)
    except (OSError, ValueError):
        pass
    return out
