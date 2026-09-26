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
    try:
        cfg = json.loads((run / "config.json").read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"{run.name}: config.json unreadable ({e}); skipped", flush=True)
        return False
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
    """Scale-transfer outputs (transfer_eval.py) land in an already-offloaded run: push each finished split's
    predictions (if kept) + metrics + results_transfer.json to the same Hub folder and free the predictions locally.
    Per split, not per tier (2026-09-25: waiting for all three splits let ≈ 80 GB of XL predictions pile up)."""
    p = run / "results_transfer.json"
    if not p.exists():
        return
    try:
        ev = json.loads(p.read_text()).get("eval", {})
    except json.JSONDecodeError as e:
        print(f"{run.name}: results_transfer.json unreadable ({e}); skipped", flush=True)
        return
    for tag in sorted(ev):
        mark = run / f".offloaded_transfer_{tag}"
        if mark.exists() or not (run / "eval_transfer" / tag / "results.json").exists():
            continue
        include = ["results_transfer.json", f"eval_transfer/{tag}", f"predictions/{tag}"]
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
                f"{run.name} transfer {tag}: push failed\n{r.stdout[-400:]}\n{r.stderr[-400:]}",
                flush=True,
            )
            continue
        try:
            rec = json.loads((run / ".hub_pushed.json").read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"{run.name}: .hub_pushed.json unreadable ({e}); predictions kept", flush=True)
            continue
        freed = 0
        for h5 in (run / "predictions" / tag).glob("*.h5"):
            if str(h5.relative_to(run)) in rec:
                freed += h5.stat().st_size
                h5.unlink()
        mark.write_text(json.dumps({"freed_gb": round(freed / 1e9, 2)}))
        print(
            f"{run.name} transfer {tag}: offloaded, freed {freed / 1e9:.1f} GB locally", flush=True
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
