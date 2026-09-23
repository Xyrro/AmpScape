#!/usr/bin/env python
"""Post-run precision pass (owner 2026-09-21; docs/post_run_resolve_plan.md §6).

Re-solves selected index rows of a tier in place on the Hub: every `solver = cg+amg` row, every row whose Kirchhoff
residual is above the target, and every row whose residual was never measured (mode a: points and regions; mode b:
regions only). Per row the Julia core (`julia/AmpScapeSolve.jl/scripts/resolve_rows.jl`) solves each pair with
CHOLMOD on the reduced system + iterative refinement, verifies the true residual, recomputes currents / Reff and
records provenance (`solver_original`, `resolved_post_run`, `residual_per_pair`) in `solver_stats`.

  select  --tier L --work work/precision/L [--mode a|b] [--target 1e-9]
  submit  --tier L --work work/precision/L [--per-task 4] [--mem 8G] [--time 04:00:00] [--shards a-b]
  run     --tier L --work work/precision/L --shard 123           (one Slurm task: download, re-solve, rebuild index rows)
  upload  --tier L --work work/precision/L                       (login node: one commit per shard, sha256 verified, local copies deleted)
  status  --tier L --work work/precision/L
  publish --tier L                                               (index/<tier>.parquet + split lists; run once at the end of the pass)
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ampscape.io.hf_layout import CONFIG_TO_GROUP  # noqa: E402
from ampscape.io.sync import remote_sha256, sha256  # noqa: E402

REPO = f"{os.environ.get('HF_ORG', 'Xirro')}/AmpScape"
JULIA = "julia --project=julia/AmpScapeSolve.jl julia/AmpScapeSolve.jl/scripts/resolve_rows.jl"
SB = ["sbatch", "--parsable", "-A", "coc", "-q", "coc-ice", "-p", "coc-cpu", "-N1", "-n1"]
PAIR_CONFIGS = ("points", "wall_to_wall_NS", "wall_to_wall_EW", "regions", "advanced")


def shard_no(x) -> int:
    """'shard-00012.h5' / 'shard-00012' / 12 -> 12 (the per-shard index rows carry the file name)."""
    m = re.search(r"(\d+)", str(x))
    return int(m.group(1)) if m else int(x)


def tier_index(tier: str) -> pd.DataFrame:
    files = sorted(glob.glob(f"data/v1/{tier}/index/shard-*.parquet"))
    if not files:
        raise SystemExit(f"no per-shard index rows under data/v1/{tier}/index")
    idx = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    idx["shard_no"] = idx.shard.map(shard_no)
    return idx


def cmd_select(a):
    idx = tier_index(a.tier)
    # T4 rows are re-run whole (Omniscape with the solve rescue) only when QC failed (incident (i)); pairwise/advanced
    # rows follow the residual rules below
    idx = idx[
        idx.config.isin(PAIR_CONFIGS) | ((idx.config == "omniscape") & ~idx.qc_pass.astype(bool))
    ]
    unmeasured = idx.residual_rel.isna() & (
        idx.config.isin(["points", "regions"]) if a.mode == "a" else (idx.config == "regions")
    )
    failed = ~idx.qc_pass.astype(
        bool
    )  # not_converged / all_zero / residual_high rows: re-solved directly
    sel = idx[(idx.solver == "cg+amg") | (idx.residual_rel > a.target) | unmeasured | failed].copy()
    sel["reason"] = np.select(
        [~sel.qc_pass.astype(bool), sel.solver == "cg+amg", sel.residual_rel > a.target],
        ["qc_failed", "fallback", "above_target"],
        "unmeasured",
    )
    work = pathlib.Path(a.work)
    (work / "rows").mkdir(parents=True, exist_ok=True)
    for sh, g in sel.groupby("shard_no"):
        rows = [
            {"sample_id": r.sample_id, "config": r.config, "reason": r.reason}
            for r in g.itertuples()
        ]
        (work / "rows" / f"shard-{int(sh):05d}.json").write_text(json.dumps(rows))
    summary = {
        "tier": a.tier,
        "mode": a.mode,
        "target": a.target,
        "rows": int(len(sel)),
        "samples": int(sel.sample_id.nunique()),
        "shards": int(sel.shard_no.nunique()),
        "by_reason": sel.reason.value_counts().to_dict(),
        "by_config": sel.config.value_counts().to_dict(),
        "selected_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    (work / "selection.json").write_text(json.dumps(summary, indent=1))
    sel.to_parquet(work / "selection.parquet", index=False)
    print(json.dumps(summary))


def download(tier: str, grp: str, shard: str, dest: pathlib.Path) -> pathlib.Path:
    from huggingface_hub import hf_hub_download

    rel = f"data/{tier}/{grp}/{shard}.h5"
    cache = dest / ".hfcache"
    p = hf_hub_download(REPO, rel, repo_type="dataset", cache_dir=str(cache))
    out = dest / "data" / tier / grp / f"{shard}.h5"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, out)  # a real file (the cache holds symlinks) that Julia can open r+
    shutil.rmtree(cache, ignore_errors=True)
    return out


def rebuild_rows(h5: pathlib.Path, shard: str, touched: set[tuple[str, str]]) -> pd.DataFrame:
    """Index rows for the touched (sample, config) of one task-group file, via the finalize QC (same rules as production)."""
    import h5py

    from ampscape.solve.finalize import index_rows_from_final

    df = index_rows_from_final(str(h5), shard)
    df = df[[(s, c) in touched for s, c in zip(df.sample_id, df.config)]].copy()
    orig, flags = [], []
    with h5py.File(h5, "r") as f:
        for r in df.itertuples():
            st = json.loads(f[r.sample_id]["configs"][r.config]["outputs"].attrs["solver_stats"])
            orig.append(st.get("solver_original"))
            fl = [x for x in str(r.qc_flags).split(",") if x] if isinstance(r.qc_flags, str) else []
            if "resolved_post_run" not in fl:
                fl.append("resolved_post_run")
            flags.append(",".join(fl))
    df["solver_original"] = orig
    df["qc_flags"] = flags
    return df


def cmd_run(a):
    work = pathlib.Path(a.work)
    shard = f"shard-{a.shard:05d}"
    rows = json.loads((work / "rows" / f"{shard}.json").read_text())
    by_grp: dict[str, list[dict]] = {}
    for r in rows:
        by_grp.setdefault(CONFIG_TO_GROUP[r["config"]], []).append(r)
    files_dir = work / "files" / shard
    files_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "shard": shard,
        "tier": a.tier,
        "groups": {},
        "started": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    new_rows = []
    for grp, grows in sorted(by_grp.items()):
        h5 = download(a.tier, grp, shard, files_dir)
        rows_json = files_dir / f"{grp}.rows.json"
        rows_json.write_text(json.dumps(grows))
        rep = files_dir / f"{grp}.report.json"
        log = files_dir / f"{grp}.log"
        cmd = f"{JULIA} {h5} {rows_json} {rep} --target {a.target} --qc-tol {a.qc_tol}"
        with open(log, "w") as lf:
            rc = subprocess.run(
                cmd, shell=True, stdout=lf, stderr=subprocess.STDOUT, cwd=str(ROOT)
            ).returncode
        if rc != 0 or not rep.exists():
            result["groups"][grp] = {"status": "julia_failed", "rc": rc}
            (work / "failed").mkdir(exist_ok=True)
            (work / "failed" / f"{shard}.json").write_text(json.dumps(result, indent=1))
            raise SystemExit(f"{shard}/{grp}: julia failed rc={rc}, see {log}")
        report = json.loads(rep.read_text())
        touched = {
            (r["sample_id"], r["config"])
            for r in report["rows"]
            if r["status"] in ("ok", "residual_high")
        }
        errors = [r for r in report["rows"] if r["status"] not in ("ok", "residual_high")]
        new_rows.append(rebuild_rows(h5, shard, touched))
        result["groups"][grp] = {
            "path": f"data/{a.tier}/{grp}/{shard}.h5",
            "local": str(h5),
            "sha256": sha256(h5),
            "bytes": h5.stat().st_size,
            "n_rows": len(report["rows"]),
            "n_ok": sum(r["status"] == "ok" for r in report["rows"]),
            "n_residual_high": sum(r["status"] == "residual_high" for r in report["rows"]),
            "errors": errors,
            "time_s": report["time_s"],
        }
    upd = pd.concat(new_rows, ignore_index=True) if new_rows else pd.DataFrame()
    (work / "index").mkdir(exist_ok=True)
    old = pd.read_parquet(f"data/v1/{a.tier}/index/{shard}.parquet")
    if "solver_original" not in old:
        old["solver_original"] = None
    key = set(zip(upd.sample_id, upd.config))
    keep = old[[(s, c) not in key for s, c in zip(old.sample_id, old.config)]]
    merged = pd.concat([keep, upd[[c for c in old.columns if c in upd.columns]]], ignore_index=True)
    merged.to_parquet(work / "index" / f"{shard}.parquet", index=False)
    result["finished"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    result["n_index_rows_updated"] = int(len(upd))
    (work / "done").mkdir(exist_ok=True)
    (work / "done" / f"{shard}.json").write_text(json.dumps(result, indent=1, default=str))
    print(
        json.dumps({k: v for k, v in result.items() if k != "groups"}),
        {g: (v.get("n_ok"), v.get("n_residual_high")) for g, v in result["groups"].items()},
    )


def cmd_submit(a):
    """Work-queue submission (2026-09-22: the QoS allows 50 queued jobs per user): --workers long-lived tasks each claim
    shards from the list atomically (mkdir of work/claims/<shard>) and stop when less than --reserve-h of walltime is
    left; stale claims (no done marker) are cleared at every submission so interrupted shards are redone whole."""
    work = pathlib.Path(a.work)
    shards = sorted(int(p.stem.split("-")[1]) for p in (work / "rows").glob("shard-*.json"))
    if a.shards:
        lo, hi = (int(x) for x in a.shards.split("-"))
        shards = [s for s in shards if lo <= s <= hi]
    if a.only:  # exactly these shards (e.g. failed ones); their failed markers are cleared, other claims untouched
        want = {int(x) for x in a.only.split(",")}
        shards = [s for s in shards if s in want]
        for s in shards:
            (work / "failed" / f"shard-{s:05d}.json").unlink(missing_ok=True)
    shards = [s for s in shards if not (work / "done" / f"shard-{s:05d}.json").exists()]
    if not shards:
        print("nothing to submit")
        return
    claims = work / "claims"
    claims.mkdir(exist_ok=True)
    for s in (
        shards
    ):  # clear stale claims of shards without a done marker (a previous worker hit the walltime)
        c = claims / f"shard-{s:05d}"
        if c.exists():
            shutil.rmtree(c, ignore_errors=True)
    (work / "lists").mkdir(exist_ok=True)
    lst = work / "lists" / f"submit_{dt.datetime.now(dt.UTC):%Y%m%dT%H%M%S}.txt"
    lst.write_text("\n".join(str(s) for s in shards) + "\n")
    n_tasks = min(a.workers, len(shards))
    (work / "logs").mkdir(exist_ok=True)
    hh, mm, ss = (int(x) for x in a.time.split(":"))
    budget_s = hh * 3600 + mm * 60 + ss - int(a.reserve_h * 3600)
    wrap = (
        f"source scripts/env.sh; export JULIA_DEPOT_PATH=$AMPSCAPE_SCRATCH/julia_depot JULIA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1; "
        f"module load julia/1.11.3 2>/dev/null; t0=$(date +%s); "
        f"for s in $(cat {lst}); do "
        f'  [ $(( $(date +%s) - t0 )) -gt {budget_s} ] && {{ echo "worker stops: walltime reserve reached"; break; }}; '
        f"  n=$(printf shard-%05d $s); [ -f {work}/done/$n.json ] && continue; "
        f"  mkdir {claims}/$n 2>/dev/null || continue; "
        f"  python scripts/precision_pass.py run --tier {a.tier} --work {work} --shard $s --target {a.target} --qc-tol {a.qc_tol} 2>&1 | grep -v Warning | tail -3; "
        f'done; echo "worker done $(date -u +%FT%TZ)"'
    )
    cmd = SB + [
        "-c1",
        f"--mem={a.mem}",
        "-t",
        a.time,
        "-J",
        f"precision-{a.tier}",
        "-o",
        f"{work}/logs/%A_%a.out",
        f"--array=0-{n_tasks - 1}",
        "--wrap",
        wrap,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stdout.strip() or ("ERROR " + r.stderr.strip()[:200])
    print(f"submitted {len(shards)} shards to {n_tasks} worker tasks: job {out}")


def cmd_upload(a):
    """Upload finished shards in batches of --batch-shards per commit (the Hub allows 128 commits per hour; 2026-09-22
    the one-commit-per-shard version hit that limit), verify every file's sha256, then update the per-shard records."""
    import time

    from huggingface_hub import CommitOperationAdd, HfApi

    work = pathlib.Path(a.work)
    api = HfApi()
    done = sorted((work / "done").glob("shard-*.json"))
    pending = [d for d in done if not (work / "uploaded" / f"{d.stem}.json").exists()]
    n = 0
    for i in range(0, len(pending), a.batch_shards):
        batch = pending[i : i + a.batch_shards]
        ops, expect = [], {}  # expect[shard] = {grp: g}
        for d in batch:
            shard = d.stem
            res = json.loads(d.read_text())
            expect[shard] = {}
            for grp, g in res["groups"].items():
                local = pathlib.Path(g["local"])
                if not local.exists():
                    raise SystemExit(f"{shard}/{grp}: local file missing; re-run")
                if sha256(local) != g["sha256"]:
                    raise SystemExit(f"{shard}/{grp}: local file changed since the run; re-run")
                ops.append(CommitOperationAdd(path_in_repo=g["path"], path_or_fileobj=str(local)))
                expect[shard][grp] = g
        commit = None
        for attempt in range(6):
            try:
                commit = api.create_commit(
                    REPO,
                    operations=ops,
                    repo_type="dataset",
                    commit_message=f"precision pass: {a.tier} {batch[0].stem}..{batch[-1].stem} ({len(ops)} files re-solved)",
                )
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                wait = 900 if "429" in msg or "rate limit" in msg.lower() else 60 * (attempt + 1)
                print(
                    f"commit failed (attempt {attempt + 1}): {msg[:160]} — waiting {wait} s",
                    flush=True,
                )
                time.sleep(wait)
        if commit is None:
            raise SystemExit("commit failed six times — stop")
        for shard, groups in expect.items():
            for grp, g in groups.items():
                remote = remote_sha256(api, REPO, g["path"])
                if remote != g["sha256"]:
                    raise SystemExit(
                        f"{shard}/{grp}: sha256 mismatch on the Hub after upload — stop"
                    )
        for shard, groups in expect.items():
            # local upload record (audit_tier compares the Hub sha256 with it) and the scratch index rows
            rec_f = pathlib.Path(f"data/v1/{a.tier}/shards/{shard}.uploaded")
            rec = json.loads(rec_f.read_text()) if rec_f.exists() else {"parts": {}}
            for grp, g in groups.items():
                rec["parts"][grp] = {
                    "repo": REPO,
                    "path": g["path"],
                    "sha256": g["sha256"],
                    "bytes": g["bytes"],
                    "commit": getattr(commit, "oid", None),
                    "uploaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                    "precision_pass": True,
                }
            rec_f.write_text(json.dumps(rec))
            shutil.copyfile(
                work / "index" / f"{shard}.parquet", f"data/v1/{a.tier}/index/{shard}.parquet"
            )
            (work / "uploaded").mkdir(exist_ok=True)
            (work / "uploaded" / f"{shard}.json").write_text(
                json.dumps({"commit": getattr(commit, "oid", None), "groups": list(groups)})
            )
            (work / "reports" / shard).mkdir(
                parents=True, exist_ok=True
            )  # keep the per-row reports for the tier summary
            for rep in (work / "files" / shard).glob("*.report.json"):
                shutil.copyfile(rep, work / "reports" / shard / rep.name)
            shutil.rmtree(work / "files" / shard, ignore_errors=True)
            n += 1
        print(
            f"batch of {len(batch)} shard(s) ({len(ops)} files) uploaded and verified", flush=True
        )
    print(f"uploaded {n} shard(s); pending {len(pending) - n}")


def cmd_status(a):
    work = pathlib.Path(a.work)
    rows = len(list((work / "rows").glob("*.json")))
    done = list((work / "done").glob("*.json"))
    up = len(list((work / "uploaded").glob("*.json"))) if (work / "uploaded").exists() else 0
    failed = len(list((work / "failed").glob("*.json"))) if (work / "failed").exists() else 0
    agg = {"ok": 0, "residual_high": 0, "errors": 0, "time_s": 0.0}
    res_after = []
    for d in done:
        r = json.loads(d.read_text())
        for g in r["groups"].values():
            agg["ok"] += g.get("n_ok", 0)
            agg["residual_high"] += g.get("n_residual_high", 0)
            agg["errors"] += len(g.get("errors", []))
            agg["time_s"] += g.get("time_s", 0)
        for rep in (
            list((work / "reports" / d.stem).glob("*.report.json"))
            if (work / "reports" / d.stem).exists()
            else (work / "files" / d.stem).glob("*.report.json")
            if (work / "files" / d.stem).exists()
            else []
        ):
            res_after += [
                x["residual_after"]
                for x in json.loads(rep.read_text())["rows"]
                if "residual_after" in x
            ]
    res_after = [x for x in res_after if isinstance(x, (int, float)) and x == x]
    q = np.quantile(res_after, [0.5, 0.9, 0.99, 1.0]) if res_after else []
    print(
        json.dumps(
            {
                "tier": a.tier,
                "shards_selected": rows,
                "shards_done": len(done),
                "shards_uploaded": up,
                "shards_failed": failed,
                **agg,
                "cpu_h": round(agg["time_s"] / 3600, 1),
                "residual_after_quantiles(p50,p90,p99,max)": [f"{v:.1e}" for v in q],
            }
        )
    )


def cmd_publish(a):
    from ampscape.io.sync import publish_index

    build = pathlib.Path(f"data/v1/{a.tier}")
    print(publish_index(build, REPO, a.tier, build / "hf", push=True))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (
        ("select", cmd_select),
        ("submit", cmd_submit),
        ("run", cmd_run),
        ("upload", cmd_upload),
        ("status", cmd_status),
        ("publish", cmd_publish),
    ):
        p = sub.add_parser(name)
        p.add_argument("--tier", required=True)
        p.add_argument("--work", default=None)
        p.add_argument("--target", type=float, default=1e-9)
        p.add_argument("--qc-tol", type=float, default=1e-6)
        if name == "select":
            p.add_argument("--mode", choices=["a", "b"], default="a")
        if name == "run":
            p.add_argument("--shard", type=int, required=True)
        if name == "upload":
            p.add_argument("--batch-shards", type=int, default=20)
        if name == "submit":
            p.add_argument("--workers", type=int, default=45)
            p.add_argument("--mem", default="8G")
            p.add_argument("--time", default="18:00:00")
            p.add_argument(
                "--reserve-h",
                type=float,
                default=5.0,
                help="stop claiming when less walltime than this is left",
            )
            p.add_argument("--shards", default=None)
            p.add_argument(
                "--only",
                default=None,
                help="comma-separated shard numbers to (re)run, e.g. failed ones",
            )
        p.set_defaults(func=fn)
    a = ap.parse_args()
    if a.work is None:
        a.work = f"work/precision/{a.tier}"
    a.func(a)


if __name__ == "__main__":
    main()
