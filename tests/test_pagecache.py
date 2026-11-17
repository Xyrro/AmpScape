"""Login-node page-cache hygiene: the sweeper runs during a transfer, drops files it finds, and stops cleanly."""

from __future__ import annotations

import os
import time

from ampscape.io.pagecache import CacheSweeper, drop_file_cache, drop_tree_cache


def test_drop_file_cache_returns_size(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(os.urandom(1 << 16))
    assert drop_file_cache(p, fsync=True) == 1 << 16
    assert drop_file_cache(tmp_path / "missing") == 0


def test_sweeper_runs_while_transfer_in_flight(tmp_path):
    d = tmp_path / "group"
    d.mkdir()
    with CacheSweeper([d, tmp_path / "absent"], interval=0.2) as sw:
        for i in range(3):
            (d / f"shard-{i}.h5").write_bytes(b"x" * 4096)
            time.sleep(0.3)
        mid = sw.stats["sweeps"]
    assert mid >= 2, sw.stats  # sweeps happened during the "download"
    assert sw.stats["sweeps"] == mid + 1  # the final fsync sweep on exit
    assert sw.stats["files"] >= 3 and sw.stats["bytes"] >= 3 * 4096
    assert not sw._thread.is_alive()


def test_tree_sweep_respects_max_age(tmp_path):
    old = tmp_path / "old.bin"
    old.write_bytes(b"o" * 100)
    os.utime(old, (time.time() - 3600, time.time() - 3600))
    new = tmp_path / "new.bin"
    new.write_bytes(b"n" * 100)
    r = drop_tree_cache([tmp_path], max_age_s=600)
    assert r["files"] == 1 and r["bytes"] == 100
