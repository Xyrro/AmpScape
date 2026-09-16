"""Efficiency: speed-up of a surrogate's inference over the recorded reference-solver time."""

from __future__ import annotations

import numpy as np


def speedup(solve_time_s: float, inference_time_s: float) -> float:
    return (
        float(solve_time_s / inference_time_s)
        if inference_time_s and inference_time_s > 0
        else float("nan")
    )


def summarize_speedup(solve_times: list[float], inference_times: list[float]) -> dict[str, float]:
    s = np.asarray(solve_times, float)
    i = np.asarray(inference_times, float)
    ok = (i > 0) & np.isfinite(s)
    if not ok.any():
        return {
            "speedup_median": float("nan"),
            "speedup_geomean": float("nan"),
            "solver_time_total_s": float(np.nansum(s)),
            "inference_time_total_s": float(np.nansum(i)),
        }
    r = s[ok] / i[ok]
    return {
        "speedup_median": float(np.median(r)),
        "speedup_geomean": float(np.exp(np.mean(np.log(r)))),
        "solver_time_total_s": float(np.nansum(s)),
        "inference_time_total_s": float(np.nansum(i)),
    }
