#!/usr/bin/env python
"""Append the daily v1.0 generation summary to docs/status/generation_log.md (runbook item f).

  python scripts/generation_log.py --builds data/v1/S data/v1/M ... [--since 2026-09-15]
Per tier: shards planned / solved / finalized / uploaded, QC failure rate (index rows), GB verified on the Hub
(.uploaded markers), local GB; plus core-hours used (sacct, all ampscape-* jobs since --since) and the stop-rule status.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]


def tier_summary(build: pathlib.Path) -> dict:
    man = pd.read_parquet(build / "manifest.parquet")
    n_shards = man.shard.nunique()
    up_names = {p.stem for p in (build / "shards").glob("shard-*.uploaded")}
    solved = len({p.stem.replace(".outputs", "") for p in (build / "outputs").glob("shard-*.outputs.h5")} | up_names
                 | {p.stem for p in (build / "shards").glob("shard-*.h5")} | {p.stem for p in (build / "shards").glob("shard-*.ok")})
    finals = list((build / "shards").glob("shard-*.h5"))
    ok = list((build / "shards").glob("shard-*.ok"))
    up = list((build / "shards").glob("shard-*.uploaded"))
    failed = list((build / "shards").glob("shard-*.upload_failed"))
    invalid = list((build / "shards").glob("shard-*.invalid"))
    rows = sorted((build / "index").glob("shard-*.parquet"))
    idx = pd.concat([pd.read_parquet(p) for p in rows], ignore_index=True) if rows else pd.DataFrame()
    qc_fail = float(1 - idx.qc_pass.mean()) if len(idx) else float("nan")
    gb_hub = 0.0
    for m in up:
        d = json.loads(m.read_text())
        gb_hub += sum(p.get("bytes", 0) for p in d.get("parts", {}).values()) / 1e9 if "parts" in d else 0.0
    try:
        from ampscape.io.sync import hub_gb
        gb_hub = hub_gb(f"{__import__('os').environ.get('HF_ORG', 'Xirro')}/AmpScape", prefix=f"data/{man.tier.iloc[0]}/")
    except Exception:  # noqa: BLE001 - offline: keep the marker-based estimate
        pass
    gb_local = sum(p.stat().st_size for p in finals) / 1e9
    return {"tier": str(man.tier.iloc[0]), "shards": n_shards, "solved": solved, "finalized": len(ok), "uploaded": len(up),
            "upload_failed": len(failed), "invalid": len(invalid), "qc_fail_rate": qc_fail, "rows": len(idx),
            "gb_hub": gb_hub, "gb_local": gb_local}


def core_hours(since: str) -> float:
    r = subprocess.run(["sacct", "-S", since, "-u", "yxiao413", "-o", "JobName,ElapsedRaw,AllocCPUS", "-P", "-n"], capture_output=True, text=True).stdout
    tot = 0.0
    for line in r.splitlines():
        parts = line.split("|")
        if len(parts) >= 3 and parts[0].startswith("ampscape-") and parts[1].isdigit():
            tot += int(parts[1]) * int(parts[2] or 1) / 3600
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--builds", nargs="+", required=True)
    ap.add_argument("--since", default="2026-09-15")
    ap.add_argument("--log", default=str(ROOT / "docs/status/generation_log.md"))
    a = ap.parse_args()
    now = dt.datetime.now(dt.UTC).isoformat(timespec="minutes")
    rows = [tier_summary(pathlib.Path(b)) for b in a.builds if (pathlib.Path(b) / "manifest.parquet").exists()]
    ch = core_hours(a.since)
    stop = [f"{r['tier']}: QC fail {r['qc_fail_rate']:.2%}" for r in rows if r["qc_fail_rate"] > 0.01] + \
           [f"{r['tier']}: {r['upload_failed']} shard(s) failed to upload twice" for r in rows if r["upload_failed"]]
    lines = [f"## {now}", "", "| tier | shards | solved | finalized | uploaded | upload failed | invalid | QC fail | GB on Hub | GB local |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['tier']} | {r['shards']} | {r['solved']} | {r['finalized']} | {r['uploaded']} | {r['upload_failed']} | {r['invalid']} | "
                     f"{r['qc_fail_rate']:.3%} | {r['gb_hub']:.1f} | {r['gb_local']:.1f} |")
    lines += ["", f"Core-hours used since {a.since} (ampscape-* jobs): **{ch:.0f}**. Stop rule: "
              + ("**TRIGGERED — pause and report:** " + "; ".join(stop) if stop else "not triggered."), ""]
    p = pathlib.Path(a.log)
    p.write_text((p.read_text() if p.exists() else "# v1.0 generation log\n\n") + "\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
