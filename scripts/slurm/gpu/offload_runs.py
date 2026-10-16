#!/usr/bin/env python
"""Offload finished Phase 10-full runs to the Hub (aux/results/runs_full/<run>/) with sha256 verification, then remove the
local predictions and last.pt (2.6 GB per S run; the quota would fill within hours otherwise). results.json, config.json,
log.csv, best.pt and the T4-reference evaluation stay local. Login node only (Hub pushes).

  python scripts/slurm/gpu/offload_runs.py [--runs runs/full] [--loop 1800]
"""

from __future__ import annotations

import argparse
import hashlib
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
    "eval_accel_test_id",  # 2026-10-15 verification: the acceleration evaluations of the voltage heads were never
    "eval_accel_test_ood",  # published (docs/tables/acceleration.md could not be regenerated from the Hub)
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
    if cfg.get("target_kind") == "voltage" and not all(
        (run / f"eval_accel_{sp}" / "results.json").exists() for sp in ("test_id", "test_ood")
    ):
        return (
            False  # warm-start evaluations (driver backfill, CPU) read the local predictions first
        )
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

REFERENCE = "eval_t4_reference/results.json"


def reference_stale(run: pathlib.Path) -> bool:
    """An offloaded T4 run whose local exact-reference evaluation differs from the one pushed (2026-10-13: the
    reference evaluation of 28 M/L T4 runs was recomputed after their offload — the old one is kept as
    eval_t4_reference_prodtarget_wrong/ — and the `.offloaded` mark made the offloader skip them, so the Hub kept
    the superseded results.json/results.md)."""
    ref = run / REFERENCE
    if not (run / ".offloaded").exists() or not ref.exists():
        return False
    try:
        rec = json.loads((run / ".hub_pushed.json").read_text())
    except (OSError, json.JSONDecodeError):
        return True
    return rec.get(REFERENCE, {}).get("sha256") != hashlib.sha256(ref.read_bytes()).hexdigest()


def repush_reference(run: pathlib.Path) -> None:
    """Push a recomputed eval_t4_reference/ of an already offloaded run (push_aux.py uploads only the files whose
    sha256 changed, so the Hub copy is replaced in place and .hub_pushed.json records the new hash)."""
    if not reference_stale(run):
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
            "eval_t4_reference",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if r.returncode != 0 or "MISMATCH" in r.stdout or reference_stale(run):
        print(f"{run.name}: eval_t4_reference re-push failed\n{r.stdout[-400:]}\n{r.stderr[-400:]}", flush=True)
        return
    print(f"{run.name}: recomputed eval_t4_reference re-pushed (Hub copy replaced)", flush=True)


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
                    repush_reference(run)
                except Exception as e:  # noqa: BLE001
                    print(f"{run.name}: {e!r}", flush=True)
        if not a.loop:
            break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
