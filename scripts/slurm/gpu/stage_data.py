#!/usr/bin/env python
"""Stage one (tier, task group) of Xirro/AmpScape from the Hub into the scratch cache for training (login node only —
compute nodes must not download), and compute the train-only normalisation statistics the trainer needs.

  python scripts/slurm/gpu/stage_data.py stage --tier S --group T1 [--cache data/hfcache]
  python scripts/slurm/gpu/stage_data.py stats --tier S --group T1        # under Slurm: stats/norm_stats.json[<tier>]
  python scripts/slurm/gpu/stage_data.py evict --tier S --group T1        # removes data/hfcache/data/S/T1 (re-downloadable)
  python scripts/slurm/gpu/stage_data.py status

Layout: data/hfcache/{data/<tier>/<group>/shard-*.h5, index/<tier>.parquet, splits/**, stats/norm_stats_<tier>.json};
AmpScapeDataset(root=data/hfcache, tier=<tier>) reads it directly (Hub layout). Sizes on the Hub (GB): S T1 32 / T3 25 /
T4 30; M 57 / 43 / 54; L 84 / 64 / 82; XL 61 / 47 / 61.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
REPO = "Xirro/AmpScape"
REVISION = "v1.0.2"  # data files identical to v1.0; index/splits carry the 1.0.2 split correction


def gb(path: pathlib.Path) -> float:
    out = subprocess.run(["du", "-sb", str(path)], capture_output=True, text=True).stdout
    return int(out.split()[0]) / 1e9 if out else 0.0


def cmd_stage(a):
    """Per-file download with 1–2 workers, DONTNEED on every completed file and a 5-s sweeper thread over the
    group / download-temp / xet-cache directories (login-node 4 GB memory cgroup, 2026-10-13: snapshot_download with
    8 workers filled the slice with clean pages faster than any post-group drop and was OOM-killed at 20–25 % of
    L/T1 and M/T4). Resumable: files already complete in the cache (metadata match) are skipped by hf_hub_download.
    `--max-files N` stages the first N shards only (memory test); no staged marker is written then."""
    import os
    from concurrent.futures import ThreadPoolExecutor

    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import HfApi, RepoFile, hf_hub_download

    from ampscape.io.pagecache import CacheSweeper, cgroup_memory, drop_file_cache

    cache = pathlib.Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    t0 = dt.datetime.now(dt.UTC)
    api = HfApi()
    group_rel = f"data/{a.tier}/{a.group}"

    def listing(path: str, recursive: bool = False) -> list[str]:
        return sorted(
            f.path
            for f in api.list_repo_tree(
                REPO, path, recursive=recursive, revision=REVISION, repo_type="dataset"
            )
            if isinstance(f, RepoFile)
        )

    shards = listing(group_rel)
    if a.max_files:
        shards = shards[: a.max_files]
    todo = [f"index/{a.tier}.parquet", *listing("splits", recursive=True), *shards]
    hf_home = pathlib.Path(os.environ.get("HF_HOME", str(pathlib.Path.home() / ".cache/huggingface")))
    tmp = cache / ".cache" / "huggingface" / "download"
    sweep_roots = [
        cache / group_rel,
        tmp / group_rel,
        cache / "index",
        tmp / "index",
        cache / "splits",
        tmp / "splits",
        hf_home / "xet",
    ]
    print(
        f"stage {a.tier}/{a.group}: {len(shards)} shards + {len(todo) - len(shards)} index/split files, "
        f"{a.workers} workers, sweep every {a.sweep_s} s; memory.current {cgroup_memory().get('current', 0) / 2**30:.2f} GiB",
        flush=True,
    )

    def fetch(rel: str) -> int:
        for attempt in range(4):
            try:
                p = hf_hub_download(
                    REPO, rel, repo_type="dataset", revision=REVISION, local_dir=str(cache)
                )
                drop_file_cache(p, fsync=True)  # dirty pages flushed, then dropped — the cgroup never sees them
                return os.path.getsize(p)
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    raise
                print(f"  retry {attempt + 1} {rel}: {str(e)[:160]}", flush=True)
                time.sleep(15 * (attempt + 1))
        return 0

    done_b = 0
    with CacheSweeper(sweep_roots, interval=a.sweep_s) as sw, ThreadPoolExecutor(a.workers) as ex:
        for i, b in enumerate(ex.map(fetch, todo), 1):
            done_b += b
            if i % 25 == 0 or i == len(todo):
                m = cgroup_memory()
                print(
                    f"  {i}/{len(todo)} files, {done_b / 1e9:.1f} GB; memory.current {m.get('current', 0) / 2**30:.2f} GiB "
                    f"(file {m.get('file', 0) / 2**30:.2f}); sweeps {sw.stats['sweeps']}, max sweep {sw.stats['max_sweep_s']} s",
                    flush=True,
                )
    n = len(list((cache / "data" / a.tier / a.group).glob("shard-*.h5")))
    size = gb(cache / "data" / a.tier / a.group)
    rec = {
        "tier": a.tier,
        "group": a.group,
        "files": n,
        "gb": round(size, 1),
        "staged_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "minutes": round((dt.datetime.now(dt.UTC) - t0).total_seconds() / 60, 1),
        "downloaded_gb": round(done_b / 1e9, 1),
        "peak_mem_gib": round(sw.stats["peak_mem"] / 2**30, 2),
        "sweeps": sw.stats["sweeps"],
        "max_sweep_s": sw.stats["max_sweep_s"],
    }
    stats_f = cache / "stats" / "norm_stats.json"
    have = json.loads(stats_f.read_text()) if stats_f.exists() else {}
    rec["norm_stats_ready"] = a.tier in have
    if a.max_files:
        rec["partial"] = True  # memory test: no staged marker
    else:
        (cache / "staged").mkdir(exist_ok=True)
        (cache / "staged" / f"{a.tier}_{a.group}.json").write_text(json.dumps(rec))
    print(json.dumps(rec))


def cmd_stats(a):
    """Train-only normalisation statistics for one tier (reads every train item once: run under Slurm, not on the
    login node): stats/norm_stats.json keyed by tier, which AmpScapeDataset(root=cache, tier=...) loads."""
    from ampscape.data.dataset import compute_norm_stats

    cache = pathlib.Path(a.cache)
    st = compute_norm_stats(cache, a.tier, task=a.group)
    print(
        json.dumps(
            {
                "tier": a.tier,
                "n_train_items": st["n_train_items"],
                "log_resistance": st["log_resistance"],
            }
        )
    )


def cmd_evict(a):
    cache = pathlib.Path(a.cache)
    target = cache / "data" / a.tier / a.group
    print(f"evicting {target} ({gb(target):.1f} GB; re-downloadable from {REPO}@{REVISION})")
    shutil.rmtree(target, ignore_errors=True)
    (cache / "staged" / f"{a.tier}_{a.group}.json").unlink(missing_ok=True)


def cmd_status(a):
    cache = pathlib.Path(a.cache)
    tot = 0.0
    for p in sorted((cache / "staged").glob("*.json")) if (cache / "staged").exists() else []:
        r = json.loads(p.read_text())
        tot += r["gb"]
        print(
            f"{r['tier']}/{r['group']}: {r['files']} files, {r['gb']} GB (staged {r['staged_at']})"
        )
    print(f"total staged {tot:.1f} GB; cache dir {gb(cache):.1f} GB")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (
        ("stage", cmd_stage),
        ("stats", cmd_stats),
        ("evict", cmd_evict),
        ("status", cmd_status),
    ):
        p = sub.add_parser(name)
        p.add_argument("--cache", default="data/hfcache")
        if name != "status":
            p.add_argument("--tier", required=True)
            p.add_argument("--group", required=True)
        if name == "stage":
            p.add_argument("--workers", type=int, default=2, help="download threads (1–2: memory cgroup)")
            p.add_argument("--sweep-s", type=float, default=5.0, help="page-cache sweeper interval")
            p.add_argument("--max-files", type=int, default=0, help="stage only the first N shards (test; no marker)")
        p.set_defaults(func=fn)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
