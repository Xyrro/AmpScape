"""Solver-acceleration metric: CG iterations and wall time to the reference tolerance when the
AMG-preconditioned CG is warm-started from a *predicted voltage map* versus from zero.

The computation runs in Julia (`scripts/warm_start_eval.jl`, same `cg_baseline` as the stored
zero-start baselines) so that preconditioner, tolerance and matrix are identical to the reference.
"""

from __future__ import annotations

import json
import pathlib
import subprocess

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
JULIA_PKG = ROOT / "julia" / "AmpScapeSolve.jl"


def run_warm_start_eval(
    source_h5: str | pathlib.Path,
    predictions_h5: str | pathlib.Path,
    out_json: str | pathlib.Path,
    rtol: float = 1e-6,
) -> list[dict]:
    cmd = [
        "julia",
        f"--project={JULIA_PKG}",
        str(JULIA_PKG / "scripts" / "warm_start_eval.jl"),
        str(source_h5),
        str(predictions_h5),
        str(out_json),
        str(rtol),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    return json.loads(pathlib.Path(out_json).read_text())


def summarize(records: list[dict]) -> dict[str, float]:
    if not records:
        return {"n_systems": 0}
    iz = np.array([r["iters_zero"] for r in records], float)
    iw = np.array([r["iters_warm"] for r in records], float)
    tz = np.array([r["time_zero_s"] for r in records], float)
    tw = np.array([r["time_warm_s"] for r in records], float)
    return {
        "n_systems": len(records),
        "iters_zero_median": float(np.median(iz)),
        "iters_warm_median": float(np.median(iw)),
        "iter_reduction_median": float(np.median(1 - iw / np.maximum(iz, 1))),
        "time_zero_median_s": float(np.median(tz)),
        "time_warm_median_s": float(np.median(tw)),
        "time_reduction_median": float(np.median(1 - tw / np.maximum(tz, 1e-12))),
        "residual_start_warm_median": float(np.median([r["residual_start_warm"] for r in records])),
        "converged_warm_fraction": float(np.mean([r["converged_warm"] for r in records])),
    }
