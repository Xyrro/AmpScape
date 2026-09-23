#!/usr/bin/env python
"""Per-tier summary of the post-run precision pass from the local index rows (docs/tables/precision_pass.md).

python scripts/precision_summary.py [--tiers S,M,L,XL,XXL] [--out docs/tables/precision_pass.md]
"""

from __future__ import annotations

import argparse
import glob
import pathlib

import numpy as np
import pandas as pd


def tier_rows(tier: str) -> pd.DataFrame:
    files = sorted(glob.glob(f"data/v1/{tier}/index/shard-*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def fmt(x: float) -> str:
    return "—" if x is None or not np.isfinite(x) else f"{x:.1e}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="S,M,L,XL,XXL")
    ap.add_argument("--out", default="docs/tables/precision_pass.md")
    a = ap.parse_args()
    lines = [
        "# Post-run precision pass — per-tier summary (from the index; every T1/T1W/T1R/T3 row carries its true Kirchhoff residual)",
        "",
        "| tier | rows re-solved | of which `cg+amg` (now `cholmod`) | residual after: p50 / p90 / p99 / max | rows > 1e-9 (floor, recorded) | rows > 1e-6 (flagged, excluded from splits) | non-T4 rows unmeasured | non-T4 rows QC-fail (all) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    tot = {"rows": 0, "cg": 0, "gt9": 0, "gt6": 0, "unm": 0, "fail": 0}
    for t in a.tiers.split(","):
        idx = tier_rows(t)
        u = idx[idx.qc_flags.astype(str).str.contains("resolved_post_run")]
        r = u.residual_rel.dropna()
        nt = idx[idx.config != "omniscape"]
        cg = int((u.get("solver_original", pd.Series(dtype=object)) == "cg+amg").sum())
        row = {
            "rows": len(u),
            "cg": cg,
            "gt9": int((r > 1e-9).sum()),
            "gt6": int((r > 1e-6).sum()),
            "unm": int(nt.residual_rel.isna().sum()),
            "fail": int((~nt.qc_pass.astype(bool)).sum()),
        }
        for k in tot:
            tot[k] += row[k]
        q = [r.quantile(p) for p in (0.5, 0.9, 0.99)] + [r.max()] if len(r) else [np.nan] * 4
        lines.append(
            f"| {t} | {row['rows']:,} | {cg} | {' / '.join(fmt(v) for v in q)} | {row['gt9']:,} | {row['gt6']} | {row['unm']} | {row['fail']} |"
        )
    lines.append(
        f"| **total** | **{tot['rows']:,}** | {tot['cg']} | | {tot['gt9']:,} | {tot['gt6']} | {tot['unm']} | {tot['fail']} |"
    )
    lines += [
        "",
        "Rows above 1e-6 after CHOLMOD + up to three refinement steps (and LDLᵀ / AMG-PCG as last resorts) are all synthetic",
        "landscapes at contrast ≥ 10⁴; they carry `residual_high`, `qc_pass = false`, and their samples are excluded from the",
        "split lists (the rows stay in the index with their achieved residual). Provenance per re-solved row:",
        "`qc_flags` contains `resolved_post_run`, `solver_original` holds the production solver when it changed, and",
        "`solver_stats.resolved_post_run` (per-pair residuals, methods, refinement steps, consistency with the replaced maps).",
    ]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
