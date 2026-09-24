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

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
REPO = "Xirro/AmpScape"
REVISION = "v1.0"


def gb(path: pathlib.Path) -> float:
    out = subprocess.run(["du", "-sb", str(path)], capture_output=True, text=True).stdout
    return int(out.split()[0]) / 1e9 if out else 0.0


def cmd_stage(a):
    from huggingface_hub import snapshot_download

    cache = pathlib.Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    t0 = dt.datetime.now(dt.UTC)
    snapshot_download(
        REPO,
        repo_type="dataset",
        revision=REVISION,
        local_dir=str(cache),
        allow_patterns=[
            f"data/{a.tier}/{a.group}/*",
            f"index/{a.tier}.parquet",
            "splits/**",
        ],
        max_workers=8,
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
    }
    stats_f = cache / "stats" / "norm_stats.json"
    have = json.loads(stats_f.read_text()) if stats_f.exists() else {}
    rec["norm_stats_ready"] = a.tier in have
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
        p.set_defaults(func=fn)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
