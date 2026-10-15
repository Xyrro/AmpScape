#!/usr/bin/env python
"""Verification (owner, 2026-10-15, item 2): mirror every *published* result file the table/figure generators read —
nothing from runs/ or aux/ of the working tree — into one directory laid out like the Hub, so the generators can be
run against it (`scripts/verify/regenerate_from_hub.sh`).

  python scripts/verify/mirror_hub_results.py --out work/verify/hub_mirror

Mirrored (metadata/metrics only, no predictions.h5 / checkpoints): aux/results/runs_full/** (results*.json,
eval_t4_reference, eval_transfer, eval_accel_*, config/log/done/requeues/REUSED_FROM), aux/results/predictions/**
(non-learned baselines), aux/t4_bs1_reference/*/index.parquet + summaries, aux/t4_blocksize_baselines/**/*.parquet,
aux/wp7/*.parquet.
"""
from __future__ import annotations

import argparse
import pathlib
import time

from huggingface_hub import snapshot_download

PATTERNS = [
    "aux/results/runs_full/**/*.json",
    "aux/results/runs_full/**/*.md",
    "aux/results/runs_full/**/*.csv",
    "aux/results/runs_full/**/*.log",
    "aux/results/runs_full/**/*.txt",
    "aux/results/predictions/**/*.json",
    "aux/results/predictions/**/*.md",
    "aux/t4_bs1_reference/**/*.parquet",
    "aux/t4_bs1_reference/**/*.md",
    "aux/t4_bs1_reference/**/*.json",
    "aux/t4_blocksize_baselines/**/*.parquet",
    "aux/t4_blocksize_baselines/**/*.md",
    "aux/t4_blocksize_baselines/**/*.json",
    "aux/wp7/*.parquet",
    "aux/wp7/*.md",
    "aux/wp7/*.json",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default="Xirro/AmpScape")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    local = snapshot_download(
        a.repo, repo_type="dataset", local_dir=str(out), allow_patterns=PATTERNS, max_workers=a.workers
    )
    files = [p for p in pathlib.Path(local).rglob("*") if p.is_file() and ".cache" not in p.parts]
    gb = sum(p.stat().st_size for p in files) / 1e9
    print(f"mirrored {len(files)} files, {gb:.2f} GB to {local} in {time.time() - t0:.0f} s")
    (out / "MIRROR.txt").write_text(
        f"repo={a.repo} files={len(files)} gb={gb:.2f} patterns={PATTERNS} finished={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
    )


if __name__ == "__main__":
    main()
