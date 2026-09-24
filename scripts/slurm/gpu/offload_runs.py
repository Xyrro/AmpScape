#!/usr/bin/env python
"""Offload finished Phase 10-full runs to the Hub (aux/results/runs_full/<run>/) with sha256 verification, then remove the
local predictions and last.pt (2.6 GB per S run; the quota would fill within hours otherwise). results.json, config.json,
log.csv, best.pt and the T4-reference evaluation stay local. Login node only (Hub pushes).

  python scripts/slurm/gpu/offload_runs.py [--runs runs/full] [--loop 1800]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
INCLUDE = [
    "results.json",
    "config.json",
    "log.csv",
    "done.json",
    "best.pt",
    "predictions",
    "eval_t4_reference",
    "train.log",
]


def finished(run: pathlib.Path) -> bool:
    if not (run / "results.json").exists() or not (run / "done.json").exists():
        return False
    cfg = json.loads((run / "config.json").read_text())
    if (
        cfg["task"] == "T4"
        and cfg["tier"] in ("M", "L")
        and not (run / "eval_t4_reference").exists()
    ):
        return False  # the reference evaluation runs at the end of the job; wait for it
    return True


def offload(run: pathlib.Path) -> None:
    mark = run / ".offloaded"
    if mark.exists():
        return
    r = subprocess.run(
        [
            sys.executable,
            "scripts/push_aux.py",
            "--src",
            str(run),
            "--dest",
            f"aux/results/runs_full/{run.name}",
            "--include",
            *INCLUDE,
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if r.returncode != 0 or "MISMATCH" in r.stdout:
        print(f"{run.name}: push failed\n{r.stdout[-400:]}\n{r.stderr[-400:]}", flush=True)
        return
    rec = json.loads((run / ".hub_pushed.json").read_text())
    freed = 0
    for p in list((run / "predictions").rglob("*.h5")) + [run / "last.pt"]:
        rel = str(p.relative_to(run))
        if p.exists() and (rel in rec or p.name == "last.pt"):
            freed += p.stat().st_size
            p.unlink()
    mark.write_text(json.dumps({"freed_gb": round(freed / 1e9, 2), "files": len(rec)}))
    print(
        f"{run.name}: offloaded ({len(rec)} files on the Hub), freed {freed / 1e9:.1f} GB locally",
        flush=True,
    )


XFER_SPLITS = ("test_id", "test_ood", "ood_region")


def offload_transfer(run: pathlib.Path) -> None:
    """Scale-transfer outputs (transfer_eval.py) land in an already-offloaded run: push each completed tier's
    predictions + metrics + results_transfer.json to the same Hub folder and free the predictions locally."""
    p = run / "results_transfer.json"
    if not p.exists():
        return
    ev = json.loads(p.read_text()).get("eval", {})
    for tier in ("XL", "XXL"):
        mark = run / f".offloaded_transfer_{tier}"
        if mark.exists() or not all(f"hfcache_{tier}_{sp}" in ev for sp in XFER_SPLITS):
            continue
        include = ["results_transfer.json"] + [
            f"{sub}/hfcache_{tier}_{sp}"
            for sp in XFER_SPLITS
            for sub in ("predictions", "eval_transfer")
        ]
        r = subprocess.run(
            [
                sys.executable,
                "scripts/push_aux.py",
                "--src",
                str(run),
                "--dest",
                f"aux/results/runs_full/{run.name}",
                "--include",
                *include,
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        if r.returncode != 0 or "MISMATCH" in r.stdout:
            print(
                f"{run.name} transfer {tier}: push failed\n{r.stdout[-400:]}\n{r.stderr[-400:]}",
                flush=True,
            )
            continue
        rec = json.loads((run / ".hub_pushed.json").read_text())
        freed = 0
        for sp in XFER_SPLITS:
            for h5 in (run / "predictions" / f"hfcache_{tier}_{sp}").glob("*.h5"):
                if str(h5.relative_to(run)) in rec:
                    freed += h5.stat().st_size
                    h5.unlink()
        mark.write_text(json.dumps({"freed_gb": round(freed / 1e9, 2)}))
        print(
            f"{run.name} transfer {tier}: offloaded, freed {freed / 1e9:.1f} GB locally", flush=True
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/full")
    ap.add_argument("--loop", type=int, default=0, help="seconds between passes (0 = one pass)")
    a = ap.parse_args()
    while True:
        for run in sorted(pathlib.Path(a.runs).glob("*_T*")):
            if finished(run):
                try:
                    offload(run)
                    offload_transfer(run)
                except Exception as e:  # noqa: BLE001
                    print(f"{run.name}: {e!r}", flush=True)
        if not a.loop:
            break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
