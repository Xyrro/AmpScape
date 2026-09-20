#!/usr/bin/env python
"""Autonomous v1.0 tier driver (owner instruction 2026-09-16): M → L → XL → XXL in waves per the runbook, without
waiting for the owner; reports at tier boundaries; stops on the stop rule, scratch > 250 GB, or a dead sync supervisor.

Runs detached on the login node (setsid nohup …); idempotent (state in logs/driver_state.json, pid lock); one cycle
every CYCLE seconds. Everything heavy (plan, prepare, solve, finalize) is a Slurm job; the driver only submits, checks
markers and starts the per-tier sync supervisor. Alerts are written to logs/ALERT.txt (and the driver exits);
tier-boundary reports to logs/tier_boundary_<tier>.txt and docs/status/generation_log.md.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path("/storage/ice1/1/8/yxiao413/EcoFlowBench")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
LOGS = ROOT / "logs"
STATE = LOGS / "driver_state.json"
CYCLE = 600
SCRATCH_ALERT_GB = 250.0
SCRATCH_SUBMIT_GB = 200.0
# tier, landscapes, shard size, wave (shards), max concurrent jobs, extra plan args
TIERS = [
    ("M", 50000, 100, 80, 80, []),
    ("L", 20000, 20, 100, 100, []),
    ("XL", 4000, 6, 100, 100, []),
    ("XXL", 400, 1, 64, 64, ["--n-tiles", "38"]),
]
SB = ["sbatch", "--parsable", "-A", "coc", "-q", "coc-ice", "-p", "coc-cpu", "-N1", "-n1"]


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def log(msg: str) -> None:
    with open(LOGS / "driver.log", "a") as f:
        f.write(f"{now()} {msg}\n")


def sh(cmd: list[str], **kw) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout.strip()


def scratch_gb() -> float:
    out = sh(["lfs", "quota", "-u", os.environ.get("USER", "yxiao413"), "/storage/ice1"])
    for line in out.splitlines():
        if "/storage/ice1" in line:
            v = line.split()[1].rstrip("*")
            return (
                float(v) / 1e6
                if v.isdigit()
                else float(v.rstrip("G"))
                if v.endswith("G")
                else float(v) / 1e6
            )
    return 0.0


def data_gb() -> float:
    return int(sh(["du", "-sb", str(ROOT / "data")]).split()[0]) / 1e9


def build(tier: str) -> pathlib.Path:
    return ROOT / "data" / "v1" / tier


def counts(tier: str) -> dict:
    b = build(tier)
    sh_dir = b / "shards"
    n_shards = 0
    if (b / "manifest.parquet").exists():
        import pandas as pd

        n_shards = int(pd.read_parquet(b / "manifest.parquet", columns=["shard"]).shard.nunique())
    return {
        "shards": n_shards,
        "inputs": len(list((b / "inputs").glob("*.h5"))) if (b / "inputs").exists() else 0,
        "outputs": len(list((b / "outputs").glob("*.h5"))) if (b / "outputs").exists() else 0,
        "finals": len(list(sh_dir.glob("shard-*.h5"))) if sh_dir.exists() else 0,
        "ok": len(list(sh_dir.glob("shard-*.ok"))) if sh_dir.exists() else 0,
        "uploaded": len(list(sh_dir.glob("shard-*.uploaded"))) if sh_dir.exists() else 0,
        "failed": len(list(sh_dir.glob("shard-*.upload_failed"))) if sh_dir.exists() else 0,
        "invalid": len(list(sh_dir.glob("shard-*.invalid"))) if sh_dir.exists() else 0,
    }


def qc_fail_rate(tier: str) -> float:
    import pandas as pd

    rows = sorted((build(tier) / "index").glob("shard-*.parquet"))
    if not rows:
        return 0.0
    idx = pd.concat([pd.read_parquet(p, columns=["qc_pass"]) for p in rows], ignore_index=True)
    return float(1 - idx.qc_pass.mean()) if len(idx) else 0.0


def sync_alive(tier: str) -> bool:
    """A sync loop for the tier is alive if its cross-host lease (written by every sync cycle) is fresh — on any login
    node — or, failing that, if the local pid file points to a live process (2026-09-19: pid files are host-local)."""
    lf = LOGS / f"lease_sync_{tier}.json"
    try:
        d = json.loads(lf.read_text())
        if (
            time.time() - float(d.get("ts", 0)) < 7200
        ):  # a sync cycle = 15 min sleep + up to ~15 min of uploads
            return True
    except Exception:  # noqa: BLE001
        pass
    pf = LOGS / f"sync_{tier}.pid"
    if not pf.exists():
        return False
    try:
        os.kill(int(pf.read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def start_sync(tier: str) -> None:
    subprocess.Popen(
        ["setsid", "nohup", str(ROOT / "scripts/slurm/v1/sync_loop.sh"), f"data/v1/{tier}", tier],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(5)


def jobs_named(name: str) -> int:
    """Queued/running jobs whose name is exactly `name` (2026-09-19: a prefix match counted the aux array
    `ampscape-L_bs1` as tier-L work and stalled the L waves)."""
    out = sh(["squeue", "-u", os.environ.get("USER", "yxiao413"), "-h", "-o", "%j"])
    return sum(1 for j in out.splitlines() if j.strip() == name)


def alert(reason: str, state: dict) -> None:
    (LOGS / "ALERT.txt").write_text(f"{now()} {reason}\n{json.dumps(state, indent=1)}\n")
    log(f"ALERT: {reason}")
    raise SystemExit(2)


def audit_clean(tier: str, st: dict) -> bool:
    """True when <build>/audit_<tier>.json exists, is newer than the last upload marker, and reports no discrepancy.
    Otherwise submits the audit job (once) and returns False; a dirty audit raises an alert (repair, never drop)."""
    b = build(tier)
    aj = b / f"audit_{tier}.json"
    marks = list((b / "shards").glob("shard-*.uploaded"))
    latest_upload = max((m.stat().st_mtime for m in marks), default=0.0)
    if aj.exists() and aj.stat().st_mtime > latest_upload:
        d = json.loads(aj.read_text())
        if d.get("n_bad", 1) == 0 and d.get("n_shards") == counts(tier)["shards"]:
            return True
        alert(
            f"{tier}: audit found {d.get('n_bad')} shard(s) with discrepancies — repair required",
            st,
        )
    ts = st["tiers"].setdefault(tier, {})
    job = ts.get("audit_job")
    if job and sh(["squeue", "-h", "-j", job]):
        return False  # audit running
    jid = sh(
        SB
        + [
            "-c4",
            "--mem=24G",
            "-t",
            "12:00:00",
            "-J",
            f"audit-{tier}",
            "-o",
            f"data/v1/logs/audit_{tier}_%j.out",
            "--wrap",
            f"source scripts/env.sh; python scripts/audit_tier.py --build data/v1/{tier} --tier {tier} --workers 4",
        ]
    )
    if jid.isdigit():
        ts["audit_job"] = jid
        log(f"{tier}: audit job {jid} submitted")
    return False


def boundary_report(tier: str, state: dict) -> None:
    c = counts(tier)
    rep = sh(
        [
            sys.executable,
            "scripts/generation_log.py",
            "--builds",
            f"data/v1/{tier}",
            "--since",
            "2026-09-15",
        ]
    )
    t0 = state["tiers"][tier].get("first_upload_at")
    rate = ""
    if t0:
        hours = max(
            (dt.datetime.now(dt.UTC) - dt.datetime.fromisoformat(t0)).total_seconds() / 3600, 0.01
        )
        rate = f"{c['uploaded'] / hours:.0f} shards/h"
    txt = f"TIER {tier} COMPLETE {now()}\n{json.dumps(c)}\nQC fail rate {qc_fail_rate(tier):.3%}\nupload rate {rate}\n{rep}\n"
    (LOGS / f"tier_boundary_{tier}.txt").write_text(txt)
    log(f"tier {tier} complete")


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"tiers": {}, "current": None}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=1))


def run_tier(
    tier: str, n: int, shard_size: int, wave: int, maxc: int, extra: list[str], st: dict
) -> bool:
    """One cycle of work on a tier; returns True when the tier is complete (all shards uploaded)."""
    ts = st["tiers"].setdefault(
        tier, {"submitted_upto": -1, "prepared_upto": -1, "prepare_job": None, "started": now()}
    )
    b = build(tier)
    if not (b / "manifest.parquet").exists():
        # planning is a 20–40 min single-core job (tens of thousands of landscapes are sampled): run it under Slurm,
        # not on the shared login node, and come back next cycle
        pj = ts.get("plan_job")
        if pj and sh(["squeue", "-h", "-j", pj]):
            return False
        if pj and not (b / "manifest.parquet").exists():
            alert(f"{tier}: planning job {pj} ended without a manifest", st)
        b.mkdir(parents=True, exist_ok=True)
        cmd = (
            f"source scripts/env.sh; python scripts/plan_v1.py --tier {tier} --n {n} --out {b} --shard-size {shard_size} "
            f"--tiles data/tiles/v1.0 --dataset-version 1.0.0 {' '.join(extra)}"
        )
        jid = sh(
            SB
            + [
                "-c1",
                "--mem=16G",
                "-t",
                "04:00:00",
                "-J",
                f"plan-{tier}",
                "-o",
                f"data/v1/logs/plan_{tier}_%j.out",
                "--wrap",
                cmd,
            ]
        )
        if jid.isdigit():
            ts["plan_job"] = jid
            log(f"{tier}: planning job {jid} submitted")
        return False
    c = counts(tier)
    n_shards = c["shards"]
    if c["uploaded"] >= n_shards and n_shards > 0:
        return audit_clean(tier, st)  # complete only when the full Hub-vs-plan audit passes
    # stop rule checks for this tier
    if c["failed"]:
        alert(f"{tier}: {c['failed']} shard(s) failed to upload twice", st)
    if c["ok"] and qc_fail_rate(tier) > 0.01:
        alert(f"{tier}: QC failure rate {qc_fail_rate(tier):.2%} > 1 %", st)
    if c["invalid"]:
        alert(
            f"{tier}: {c['invalid']} shard(s) marked .invalid — repair required (never dropped)", st
        )
    # shards solved (completion marker) but never finalized (a finalize step that died): run finalize for them
    # only markers older than 30 min with no array task of the tier running count as stale: the array task writes the
    # marker and then finalizes itself, and a second finalize on the same shard corrupts the final (tier-M shard 434)
    stale = [
        o
        for o in (b / "outputs").glob("shard-*.outputs.h5.done")
        if not (b / "shards" / (o.name.split(".")[0] + ".h5")).exists()
        and not (b / "shards" / (o.name.split(".")[0] + ".uploaded")).exists()
        and time.time() - o.stat().st_mtime > 1800
    ]
    if stale and jobs_named(f"ampscape-{tier}") > 0:
        stale = []
    if (
        stale
        and not ts.get("refinalize_job")
        or (
            ts.get("refinalize_job")
            and not sh(["squeue", "-h", "-j", ts["refinalize_job"]])
            and stale
        )
    ):
        ids = " ".join(o.name.split(".")[0].split("-")[1].lstrip("0") or "0" for o in stale[:50])
        jid = sh(
            SB
            + [
                "-c1",
                "--mem=8G",
                "-t",
                "04:00:00",
                "-J",
                f"refin-{tier}",
                "-o",
                f"data/v1/logs/refin_{tier}_%j.out",
                "--wrap",
                f"source scripts/env.sh; for s in {ids}; do python scripts/generate.py finalize --build data/v1/{tier} --shard $s --quicklooks 2>&1 | grep -v Warning | tail -1; done",
            ]
        )
        if jid.isdigit():
            ts["refinalize_job"] = jid
            log(f"{tier}: re-finalize job {jid} for {len(stale)} solved-but-unfinalized shard(s)")
    # prepare the next wave (one prepare job at a time, ahead of submission)
    nxt_lo = ts["prepared_upto"] + 1
    # prepare at most ONE wave beyond the last submitted wave (inputs are scratch; L/XL inputs are large)
    if (
        nxt_lo < n_shards
        and ts.get("prepare_job") is None
        and nxt_lo <= ts["submitted_upto"] + wave + 1
    ):
        nxt_hi = min(nxt_lo + wave - 1, n_shards - 1)
        jid = sh(
            SB
            + [
                "-c1",
                "--mem=12G",
                "-t",
                "06:00:00",
                "-J",
                f"prep-{tier}",
                "-o",
                f"data/v1/logs/prep_{tier}_%j.out",
                "scripts/slurm/v1/prepare_shards.sh",
                f"data/v1/{tier}",
                str(nxt_lo),
                str(nxt_hi),
            ]
        )
        if jid.isdigit():
            ts["prepare_job"] = {"id": jid, "lo": nxt_lo, "hi": nxt_hi}
            log(f"{tier}: prepare {nxt_lo}-{nxt_hi} job {jid}")
    if ts.get("prepare_job"):
        pj = ts["prepare_job"]
        if not sh(["squeue", "-h", "-j", pj["id"]]):
            have = all(
                (b / "inputs" / f"shard-{s:05d}.inputs.h5").exists()
                for s in range(pj["lo"], pj["hi"] + 1)
            )
            if have:
                ts["prepared_upto"] = pj["hi"]
                ts["prepare_job"] = None
                log(f"{tier}: prepared through {pj['hi']}")
            else:
                alert(
                    f"{tier}: prepare job {pj['id']} ended without all inputs {pj['lo']}-{pj['hi']}",
                    st,
                )
    # submit the next wave when the previous wave's backlog is below one wave and scratch allows it
    sub_lo = ts["submitted_upto"] + 1
    if sub_lo < n_shards and ts["prepared_upto"] >= sub_lo:
        sub_hi = min(sub_lo + wave - 1, ts["prepared_upto"], n_shards - 1)
        backlog = (ts["submitted_upto"] + 1) - c["uploaded"]
        if (
            backlog < wave
            and data_gb() < SCRATCH_SUBMIT_GB
            and jobs_named(f"ampscape-{tier}") <= wave // 4
        ):  # stragglers of the previous wave may still run
            out = sh(
                [
                    sys.executable,
                    "scripts/generate.py",
                    "submit",
                    "--build",
                    f"data/v1/{tier}",
                    "--shards",
                    f"{sub_lo}-{sub_hi}",
                    "--max-concurrent",
                    str(maxc),
                    "--skip-precompile",
                ]
            )
            if "Submitted batch job" in out:
                ts["submitted_upto"] = sub_hi
                log(f"{tier}: submitted wave {sub_lo}-{sub_hi}: {out.splitlines()[-1]}")
                if not sync_alive(tier):
                    start_sync(tier)
                    log(f"{tier}: sync supervisor started")
            elif "nothing to submit" in out:
                ts["submitted_upto"] = sub_hi
            else:
                log(f"{tier}: submit refused: {out[-300:]}")
    # shards of *earlier* waves that ended without a completion marker (node failure, walltime): resubmit once — also
    # while a later wave runs; `generate.py submit` skips shards that still have a queued/running task
    if ts["submitted_upto"] >= 0:
        upto = (
            ts["submitted_upto"] + 1
        )  # every submitted shard; `submit` skips those with a queued/running task
        missing = [
            s
            for s in range(0, upto)
            if not any(
                (b / d / f"shard-{s:05d}{suf}").exists()
                for d, suf in (
                    ("shards", ".h5"),
                    ("shards", ".uploaded"),
                    (
                        "outputs",
                        ".outputs.h5.done",
                    ),  # a partial outputs file (walltime) does not count
                )
            )
        ]
        # shards with a queued/running task are in progress, not missing (2026-09-19: a running wave was counted as
        # missing three times and raised a false alert)
        q = sh(["squeue", "-u", os.environ.get("USER", "yxiao413"), "-h", "-o", "%j|%K"])
        active: set[int] = set()
        for line in q.splitlines():
            name, _, tid = line.partition("|")
            tid = tid.strip()
            if name != f"ampscape-{tier}":
                continue
            if tid.isdigit():
                active.add(int(tid))
            else:
                for part in tid.strip("[]").split("%")[0].split(","):
                    if "-" in part:
                        lo, hi = part.split("-")
                        if lo.isdigit() and hi.isdigit():
                            active.update(range(int(lo), int(hi) + 1))
                    elif part.isdigit():
                        active.add(int(part))
        missing = [s for s in missing if s not in active]
        if missing:
            key = tuple(missing)
            n_prev = ts.get("resubmit_rounds", {}).get(str(key), 0)
            if n_prev >= 3:
                alert(f"{tier}: shards {missing[:10]} still missing after 3 resubmissions", st)
            ts.setdefault("resubmit_rounds", {})[str(key)] = n_prev + 1
            out = sh(
                [
                    sys.executable,
                    "scripts/generate.py",
                    "submit",
                    "--build",
                    f"data/v1/{tier}",
                    "--shards",
                    f"{min(missing)}-{max(missing)}",
                    "--max-concurrent",
                    str(maxc),
                    "--skip-precompile",
                ]
            )
            ts["resubmitted"] = list(key)
            log(
                f"{tier}: resubmitted missing shards {missing[:10]}…: {out.splitlines()[-1] if out else ''}"
            )
    if c["uploaded"] and not ts.get("first_upload_at"):
        ts["first_upload_at"] = now()
    if ts["submitted_upto"] >= 0 and not sync_alive(tier):
        alert(f"{tier}: sync supervisor is not running", st)
    return False


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    pidf = LOGS / "driver.pid"
    if pidf.exists():
        try:
            os.kill(int(pidf.read_text()), 0)
            print("driver already running")
            return
        except (OSError, ValueError):
            pass
    pidf.write_text(str(os.getpid()))
    log(f"driver started pid {os.getpid()}")
    try:
        while True:
            st = load_state()
            from ampscape.io.sync import acquire_lease

            os.environ["AMPSCAPE_LEASE_OWNER"] = str(os.getpid())
            if not acquire_lease("driver", ROOT, fresh_s=1500.0):
                log("another driver instance holds the lease (other host) — exiting")
                return
            if (LOGS / "ALERT.txt").exists():
                log("ALERT present; driver idle")
                return
            g = scratch_gb()
            if g > SCRATCH_ALERT_GB:
                alert(f"scratch {g:.0f} GB > {SCRATCH_ALERT_GB:.0f} GB", st)
            # tier S must be fully on the Hub first
            cs = counts("S")
            if cs["uploaded"] < cs["shards"] or not audit_clean("S", st):
                if cs["failed"]:
                    alert(f"S: {cs['failed']} shard(s) failed to upload twice", st)
                if not sync_alive("S"):
                    alert("S: sync supervisor is not running", st)
                log(f"S: {cs['uploaded']}/{cs['shards']} uploaded; waiting")
            else:
                if "S" not in st["tiers"]:
                    st["tiers"]["S"] = {"first_upload_at": "2026-09-16T06:52:00+00:00"}
                    boundary_report("S", st)
                    save_state(st)
                for tier, n, ssz, wave, maxc, extra in TIERS:
                    if st["tiers"].get(tier, {}).get("complete"):
                        continue
                    done = run_tier(tier, n, ssz, wave, maxc, extra, st)
                    save_state(st)
                    if done:
                        st["tiers"][tier]["complete"] = now()
                        boundary_report(tier, st)
                        save_state(st)
                        continue
                    break  # work on one tier at a time
                else:
                    log("all tiers complete")
                    (LOGS / "tier_boundary_ALL.txt").write_text(f"ALL TIERS COMPLETE {now()}\n")
                    return
            save_state(st)
            time.sleep(CYCLE)
    finally:
        pidf.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
