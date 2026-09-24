"""Physics-consistency checks (brief §11).

* ``kirchhoff_residual``: ‖L v − b‖/‖b‖ on the exact graph when a **voltage** map is predicted
  (same definition as the solver QC; collapsed rows for focal regions).
* ``focal_current_error``: for pairwise maps the node current at a unit source/ground equals the
  injected current (1 A per pair; a cumulative map over P pairs carries P at a node that is in every
  pair); reported as |predicted − expected| / expected at the focal pixels.
* ``nonnegativity``: fraction of valid pixels with negative predicted current and the most negative
  value relative to max (currents are non-negative by definition).
* ``throughput_error``: relative error of the sum of node currents over valid pixels (a scalar
  proxy for total flow when no voltage is predicted; documented as a proxy, not a conservation law).
"""

from __future__ import annotations

import numpy as np

from ampscape.solve.qc import kirchhoff_residual  # noqa: F401  (re-exported)


def nonnegativity(pred, mask=None) -> dict[str, float]:
    p = np.asarray(pred, dtype=np.float64).squeeze()
    m = np.ones(p.shape, bool) if mask is None else np.asarray(mask, bool).squeeze()
    v = p[m]
    mx = float(np.max(np.abs(v))) if v.size else 0.0
    return {
        "neg_fraction": float(np.mean(v < 0)) if v.size else 0.0,
        "neg_min_over_max": float(min(v.min(), 0.0) / mx) if mx > 0 else 0.0,
    }


def focal_current_error(pred, focal_mask, pair_index=None) -> float:
    """|c_pred − c_expected| / c_expected averaged over focal pixels; expected = number of pairs the label is in
    (1 for a single-pair map, K−1 for a cumulative map over all pairs of K point nodes)."""
    p = np.asarray(pred, dtype=np.float64).squeeze()
    f = np.asarray(focal_mask).squeeze()
    labels = [int(x) for x in np.unique(f) if x > 0]
    if not labels:
        return float("nan")
    errs = []
    for lab in labels:
        expected = (
            1.0
            if pair_index is None or len(pair_index) == 1
            else float(sum(1 for a, b in pair_index if lab in (a, b)))
        )
        at = p[f == lab]
        errs.append(np.abs(at.max() - expected) / expected)
    return float(np.mean(errs))


def throughput_error(pred, target, mask=None) -> float:
    p = np.asarray(pred, dtype=np.float64).squeeze()
    t = np.asarray(target, dtype=np.float64).squeeze()
    m = np.ones(t.shape, bool) if mask is None else np.asarray(mask, bool).squeeze()
    st = t[m].sum()
    return float(abs(p[m].sum() - st) / st) if st > 0 else float("nan")
