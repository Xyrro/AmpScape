#!/usr/bin/env python
"""Phase 10-full GPU driver (owner 2026-09-24: full baselines on ICE, no external allocation, 20 GPU-hour gate lifted).

Keeps ≤ MAX_GPU jobs of the plan queued/running on coc-gpu (L40S), in priority order — headline first (U-Net and FNO on
T1 and T4 across tiers, seed 1), then the remaining model × task pairs (seed 1), then seeds 2–3, then WP4 (data-scaling
at S), GNN last — staging the (tier, task-group) data each job needs from the Hub on the login node (this process),
computing the tier's normalisation statistics under Slurm, and evicting staged groups nobody pending needs when
scratch is short. Every training job is `scripts/slurm/gpu/train_full.sbatch` (resumable across the 16-h walltime,
evaluation included). State: logs/gpu_driver_state.json; log: logs/gpu_driver.log; alerts: logs/GPU_ALERT.txt.

  setsid nohup python scripts/slurm/gpu/gpu_driver.py >/dev/null 2>&1 < /dev/null &
  python scripts/slurm/gpu/gpu_driver.py --plan          # print the plan and estimated GPU-hours, no submission
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
LOGS = ROOT / "logs"
CACHE = ROOT / "data" / "hfcache"
RUNS = ROOT / "runs" / "full"
STATE = LOGS / "gpu_driver_state.json"

MAX_GPU = 18  # concurrent jobs of ours on coc-gpu (16 healthy L40S + A100 spill-over; 1 920 GPU-run-minutes per user)
MAX_QUEUED_TOTAL = 45  # QoS MaxSubmitPU = 50
SCRATCH_LIMIT_GB = 275.0  # 2026-09-24 09:50Z: 265 → 275 (offloader every 10 min keeps runs/full small; quota 300). total quota guard (300 GB): base ≈ 117 GB, so ≈ 150 GB of staged groups at most
LOOKAHEAD = 12  # pending jobs whose data is staged ahead
EVICT_LOOKAHEAD = 12  # a staged group is evictable when none of the next N pending jobs (nor a running job) needs it
GROUP_GB = {
    ("S", "T1"): 32,
    ("S", "T3"): 25,
    ("S", "T4"): 30,
    ("M", "T1"): 57,
    ("M", "T3"): 43,
    ("M", "T4"): 54,
    ("L", "T1"): 84,
    ("L", "T3"): 64,
    ("L", "T4"): 82,
    ("XL", "T1"): 61,
    ("XL", "T3"): 47,
    ("XL", "T4"): 61,
}
GRES = "gpu:l40s:1"
GRES_ALT = "gpu:a100:1"  # used when ≥ ALT_AFTER of our jobs are already pending on L40S
ALT_AFTER = 4
PARTITION = "coc-gpu"
WALL = "02:00:00"  # 2026-09-24: QoS MaxTRESRunMinsPU gres/gpu=1920 → short jobs + self re-queue give ≈ 16 concurrent GPUs
TIERS = ["S", "M", "L", "XL"]
GROUP = {"T1": "T1", "T3": "T3", "T4": "T4"}
# per-tier resources: (batch, cpus, mem)
RES = {
    "S": {"batch": 16, "cpus": 6, "mem": "64G"},
    "M": {"batch": 8, "cpus": 6, "mem": "96G"},
    "L": {"batch": 4, "cpus": 8, "mem": "128G"},
    "XL": {"batch": 2, "cpus": 8, "mem": "160G"},
}
GNN_BATCH = {"S": 8, "M": 4, "L": 1, "XL": 1}
# GPU-hours per run from docs/tables/gpu_budget.md (30-epoch scenario, per seed)
EST = {
    ("fno", "T1"): {"S": 1.0, "M": 2.3, "L": 3.3, "XL": 0.7},
    ("fno", "T3"): {"S": 1.3, "M": 3.7, "L": 4.7, "XL": 1.0},
    ("fno", "T4"): {"S": 2.0, "M": 4.7, "L": 6.0, "XL": 1.3},
    ("gnn", "T1"): {"S": 8.3, "M": 19.7, "L": 26.7, "XL": 5.3},
    ("gnn", "T4"): {"S": 21.0, "M": 49.7, "L": 67.3, "XL": 13.3},
    ("unet", "T1"): {"S": 3.3, "M": 8.0, "L": 11.0, "XL": 2.3},
    ("unet", "T3"): {"S": 2.3, "M": 5.3, "L": 7.0, "XL": 1.3},
    ("unet", "T4"): {"S": 1.3, "M": 3.0, "L": 4.0, "XL": 0.7},
    ("vit", "T1"): {"S": 1.7, "M": 4.0, "L": 5.7, "XL": 1.0},
    ("vit", "T4"): {"S": 1.0, "M": 2.0, "L": 2.7, "XL": 0.7},
}


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def log(msg: str) -> None:
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "gpu_driver.log", "a") as f:
        f.write(f"{now()} {msg}\n")


def sh(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def plan() -> list[dict]:
    """Priority-ordered job list. Each job: model, task, tier, seed, tag (P1..P4/WP4), extra args."""
    jobs: list[dict] = []

    def add(model, task, tier, seed, tag, **kw):
        name = f"{model}_{task}_{tier}_s{seed}" + (f"_{kw['suffix']}" if kw.get("suffix") else "")
        jobs.append(
            {
                "name": name,
                "model": model,
                "task": task,
                "tier": tier,
                "seed": seed,
                "tag": tag,
                **kw,
            }
        )

    # tier-major inside a priority (docs/phase10_full_schedule.md §2): the small tiers report first and the staged
    # groups are used up tier by tier — model-major order made the driver wait for L/T1 while M/T4 was still pending
    for tier in TIERS:  # P1: headline, seed 1
        for model in ("unet", "fno"):
            for task in ("T1", "T4"):
                add(model, task, tier, 1, "P1")
    for tier in TIERS:  # P2
        for model, task in (("unet", "T3"), ("fno", "T3"), ("vit", "T1"), ("vit", "T4")):
            add(model, task, tier, 1, "P2")
    for tier in TIERS:  # P3: seeds 2 and 3, tier-major
        for seed in (2, 3):
            for model, task in (
                ("unet", "T1"),
                ("unet", "T4"),
                ("fno", "T1"),
                ("fno", "T4"),
                ("unet", "T3"),
                ("fno", "T3"),
                ("vit", "T1"),
                ("vit", "T4"),
            ):
                add(model, task, tier, seed, "P3")
    # WP4: data-scaling ablation at S, U-Net and FNO on T1, seed 1, fixed-epoch (30) and fixed-step (30 epochs of the
    # full set ≈ 118k steps at batch 16) variants; the full-size run is the P1 job itself
    for model in ("unet", "fno"):
        for n in (1000, 5000, 20000):
            add(model, "T1", "S", 1, "WP4", suffix=f"n{n}_ep30", maxtrain=n, epochs=30)
            steps_full = 30 * 63303 // 16
            ep = max(30, min(2000, steps_full // max(n // 16, 1)))
            add(model, "T1", "S", 1, "WP4", suffix=f"n{n}_steps", maxtrain=n, epochs=ep)
    for seed in (1, 2, 3):  # P4: GNN last
        for task in ("T1", "T4"):
            for tier in TIERS:
                add("gnn", task, tier, seed, "P4")
    return jobs


def est_hours(j: dict) -> float:
    base = EST[(j["model"], j["task"])][j["tier"]]
    if j.get("maxtrain"):
        frac = j["maxtrain"] / 63303
        return base * frac * (j.get("epochs", 30) / 30)
    return base


def load_state() -> dict:
    return (
        json.loads(STATE.read_text())
        if STATE.exists()
        else {"submitted": {}, "staged": [], "stats_jobs": {}}
    )


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=1))


def our_jobs() -> dict[str, str]:
    """{job name: state} for our phase10 jobs (queued/running) — names are phase10-<run name>."""
    out = {}
    for line in sh(
        ["squeue", "-u", os.environ.get("USER", "yxiao413"), "-h", "-o", "%j|%t"]
    ).splitlines():
        name, _, state = line.partition("|")
        if name.startswith("phase10-"):
            out[name[len("phase10-") :]] = state
    return out


def n_queued_total() -> int:
    return len(
        sh(["squeue", "-u", os.environ.get("USER", "yxiao413"), "-h", "-o", "%i"]).splitlines()
    )


def quota_gb() -> float:
    for line in sh(["pace-quota"]).splitlines():
        if line.startswith("Scratch:"):
            return float(line.split()[1])
    return 0.0


def staged(tier: str, group: str) -> bool:
    return (CACHE / "staged" / f"{tier}_{group}.json").exists()


def stats_ready(tier: str) -> bool:
    p = CACHE / "stats" / "norm_stats.json"
    return p.exists() and tier in json.loads(p.read_text())


def stage(tier: str, group: str) -> None:
    log(f"staging {tier}/{group} from the Hub (login node)")
    r = subprocess.run(
        [
            sys.executable,
            "scripts/slurm/gpu/stage_data.py",
            "stage",
            "--tier",
            tier,
            "--group",
            group,
        ],
        capture_output=True,
        text=True,
    )
    log(
        f"staged {tier}/{group}: {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]}"
    )


def submit_stats(tier: str, group: str, st: dict) -> None:
    key = tier
    job = st["stats_jobs"].get(key)
    if job and sh(["squeue", "-h", "-j", job]):
        return
    jid = sh(
        [
            "sbatch",
            "--parsable",
            "-A",
            "coc",
            "-q",
            "coc-ice",
            "-p",
            "coc-cpu",
            "-N1",
            "-n1",
            "-c2",
            "--mem=16G",
            "-t",
            "04:00:00",
            "-J",
            f"phase10-stats-{tier}",
            "-o",
            f"logs/gpu_stats_{tier}_%j.out",
            "--wrap",
            f"source scripts/env.sh; python scripts/slurm/gpu/stage_data.py stats --tier {tier} --group {group}",
        ]
    )
    if jid.isdigit():
        st["stats_jobs"][key] = jid
        log(f"norm stats job for {tier}: {jid}")


def submit(j: dict, st: dict) -> None:
    out = RUNS / j["name"]
    out.mkdir(parents=True, exist_ok=True)
    res = dict(RES[j["tier"]])
    batch = GNN_BATCH[j["tier"]] if j["model"] == "gnn" else res["batch"]
    prev = st["submitted"].get(j["name"], {})
    if prev.get(
        "oom"
    ):  # a previous attempt was killed for host memory: double it (node limit 191 GB)
        res["mem"] = f"{min(int(res['mem'].rstrip('G')) * 2 ** prev['oom'], 180)}G"
    # GPU type: keep the L40S pool (16 healthy GPUs) as the default and spill to A100 (8 GPUs) only while ≥ ALT_AFTER
    # of our jobs are pending on L40S and fewer than 4 are pending on A100
    pend = sh(
        ["squeue", "-u", os.environ.get("USER", "yxiao413"), "-h", "-t", "PD", "-o", "%j|%b"]
    ).splitlines()
    pd_l40s = sum(1 for x in pend if x.startswith("phase10-") and "l40s" in x)
    pd_a100 = sum(1 for x in pend if x.startswith("phase10-") and "a100" in x)
    gres = GRES_ALT if (pd_l40s >= ALT_AFTER and pd_a100 < 4) else GRES
    export = (
        f"ALL,MODEL={j['model']},TASK={j['task']},TIER={j['tier']},SEED={j['seed']},OUT={out},ROOT={CACHE},"
        f"EPOCHS={j.get('epochs', 30)},BATCH={batch},PATIENCE=8,WORKERS={res['cpus']},MAXTRAIN={j.get('maxtrain', '')},"
        f"EXTRA=,MEM={res['mem']},GRES={gres},WALL={WALL}"
    )
    bad = (
        LOGS / "gpu_bad_nodes.txt"
    )  # nodes that threw CUDA/ECC errors (smoke test 2026-09-24): never schedule there
    exclude = (
        ["--exclude=" + ",".join(bad.read_text().split())]
        if bad.exists() and bad.read_text().split()
        else []
    )
    jid = sh(
        [
            "sbatch",
            "--parsable",
            *exclude,
            "-A",
            "coc",
            "-q",
            "coc-ice",
            "-p",
            PARTITION,
            "-N1",
            "-n1",
            f"-c{res['cpus']}",
            f"--mem={res['mem']}",
            f"--gres={gres}",
            "-t",
            WALL,
            "-J",
            f"phase10-{j['name']}",
            "-o",
            f"{out}/slurm_%j.out",
            "--export",
            export,
            "scripts/slurm/gpu/train_full.sbatch",
        ]
    )
    if jid.isdigit():
        st["submitted"][j["name"]] = {
            "job": jid,
            "at": now(),
            "tag": j["tag"],
            "est_h": est_hours(j),
            "mem": res["mem"],
            "oom": prev.get("oom", 0),
        }
        log(f"submitted {j['tag']} {j['name']} (est {est_hours(j):.1f} GPU-h): job {jid}")
    else:
        log(f"submit failed for {j['name']}: {jid[-200:]}")


def note_oom(jobs: list[dict], st: dict) -> None:
    """A run whose last Slurm job ended OUT_OF_MEMORY gets double host memory at its next submission."""
    for j in jobs:
        rec = st["submitted"].get(j["name"])
        if not rec or rec.get("oom_checked") == rec["job"]:
            continue
        state = (
            sh(["sacct", "-j", rec["job"], "-X", "-o", "State", "-P", "-n"]).strip().splitlines()
        )
        if not state or state[0].startswith(("RUNNING", "PENDING", "COMPLETING")):
            continue
        if state[0].startswith("OUT_OF_MEMORY"):
            rec["oom"] = rec.get("oom", 0) + 1
            log(
                f"{j['name']}: job {rec['job']} OUT_OF_MEMORY at {rec.get('mem')} — next submission doubles host memory"
            )
        rec["oom_checked"] = rec["job"]


def note_bad_nodes(jobs: list[dict]) -> None:
    """A run whose last Slurm log ends in a CUDA/ECC error marks its node as bad (the job is re-submitted elsewhere)."""
    bad = LOGS / "gpu_bad_nodes.txt"
    known = set(bad.read_text().split()) if bad.exists() else set()
    for j in jobs:
        outs = sorted((RUNS / j["name"]).glob("slurm_*.out"), key=lambda p: p.stat().st_mtime)
        if not outs or (RUNS / j["name"] / "done.json").exists():
            continue
        txt = outs[-1].read_text()[-4000:]
        if "ECC error" in txt or "CUDA error" in txt:
            for line in outs[-1].read_text().splitlines():
                if line.startswith("host="):
                    node = line.split()[0].split("=")[1].split(".")[0]
                    if node not in known:
                        known.add(node)
                        log(f"node {node} marked bad ({outs[-1].name}: CUDA/ECC error)")
    if known:
        bad.write_text("\n".join(sorted(known)) + "\n")


def done(j: dict) -> bool:
    return (RUNS / j["name"] / "done.json").exists() and (
        RUNS / j["name"] / "results.json"
    ).exists()


def alert(msg: str) -> None:
    (LOGS / "GPU_ALERT.txt").write_text(f"{now()} {msg}\n")
    log("ALERT: " + msg)


def cycle(jobs: list[dict], st: dict) -> None:
    note_bad_nodes(jobs)
    note_oom(jobs, st)
    active = our_jobs()
    running = {n for n, s in active.items() if not n.startswith("stats-")}
    pending = [j for j in jobs if not done(j) and j["name"] not in running]
    # staging: data of the next pending jobs, in priority order, only when the group fits under the quota guard
    # (2026-09-24: an unguarded staging chain hit the 300 GB quota); groups no pending job needs are evicted first
    needed = []
    for j in pending[:LOOKAHEAD]:
        key = (j["tier"], GROUP[j["task"]])
        if key not in needed:
            needed.append(key)
    # staging in strict priority order: the data of the highest-priority pending jobs comes first; when it does not fit,
    # evict staged groups that no RUNNING job uses, those whose next pending use is furthest down the list first
    # (re-staging a group takes ≈ 3 min at the measured 8–10 GB/min). 2026-09-24: the S groups were pinning 87 GB and
    # blocking the headline M/L runs.
    running_jobs = [j for j in jobs if j["name"] in running]
    running_groups = {(jj["tier"], GROUP[jj["task"]]) for jj in running_jobs}
    first_use = {}
    for k, jj in enumerate(pending):
        first_use.setdefault((jj["tier"], GROUP[jj["task"]]), k)
    # draining: when the highest-priority unstaged group does not fit because RUNNING jobs pin the groups that would
    # be evicted, those groups stop receiving new jobs (their later seeds wait) so the pin dissolves as the running
    # legs finish; otherwise the P3 S seeds kept the S groups pinned indefinitely (2026-09-24 08:20Z).
    draining: set[tuple[str, str]] = set()

    freed = [
        0.0
    ]  # GB evicted this cycle: pace-quota lags a few minutes behind deletions (09:59Z: read 271 after
    # evicting 30 GB), so the fit test uses quota_gb() - freed

    def evict_until(size: float, target_use: int) -> None:
        # never evict a group whose next pending use comes before the target's (10:18Z: the driver staged M/T4 and
        # evicted it seconds later to make room for L/T1)
        cands = []
        for p_ in sorted((CACHE / "staged").glob("*.json")) if (CACHE / "staged").exists() else []:
            t_, g_ = p_.stem.split("_", 1)
            if (t_, g_) in running_groups or first_use.get((t_, g_), 10**6) <= target_use:
                continue
            cands.append((first_use.get((t_, g_), 10**6), t_, g_))
        for _, t_, g_ in sorted(cands, reverse=True):
            if quota_gb() - freed[0] + size <= SCRATCH_LIMIT_GB:
                return
            subprocess.run(
                [
                    sys.executable,
                    "scripts/slurm/gpu/stage_data.py",
                    "evict",
                    "--tier",
                    t_,
                    "--group",
                    g_,
                ],
                capture_output=True,
            )
            freed[0] += GROUP_GB.get((t_, g_), 60.0)
            log(
                f"evicted {t_}/{g_} to make room (next use at pending position {first_use.get((t_, g_), 'none')})"
            )

    for tier, group in needed:
        if staged(tier, group):
            if not stats_ready(tier):
                submit_stats(tier, group, st)
            continue
        size = GROUP_GB.get((tier, group), 60.0)
        if quota_gb() - freed[0] + size > SCRATCH_LIMIT_GB:
            evict_until(size, first_use.get((tier, group), 10**6))
            if quota_gb() - freed[0] + size > SCRATCH_LIMIT_GB:
                # mark the pinned groups (furthest next use first) that would free enough space as draining
                need = quota_gb() - freed[0] + size - SCRATCH_LIMIT_GB
                # small tiers first (their legs end within 2 h; an M/L group stays pinned for hours), then the
                # group whose next pending use is furthest away
                pinned = sorted(
                    (TIERS.index(g_[0]), -first_use.get(g_, 10**6), g_)
                    for g_ in running_groups
                    if g_ != (tier, group)
                )
                for _, _, g_ in pinned:
                    if need <= 0:
                        break
                    draining.add(g_)
                    need -= GROUP_GB.get(g_, 60.0)
                log(
                    f"scratch {quota_gb() - freed[0]:.0f} GB: {tier}/{group} ({size:.0f} GB) does not fit under {SCRATCH_LIMIT_GB:.0f} GB even after evictions; draining {sorted(draining)}"
                )
                break  # strict priority: do not stage a later group before this one
        stage(tier, group)
        if staged(tier, group):
            freed[0] -= size
        if staged(tier, group) and not stats_ready(tier):
            submit_stats(tier, group, st)
    # submission in priority order
    slots = MAX_GPU - len(running)
    for j in pending:
        if slots <= 0 or n_queued_total() >= MAX_QUEUED_TOTAL:
            break
        key = (j["tier"], GROUP[j["task"]])
        if j["tag"] == "P4" and any(
            jj["tag"] != "P4" for jj in pending if jj["name"] not in running
        ):
            continue  # GNN strictly last: never ahead of a P1–P3/WP4 job that is only waiting for its data
        if not (staged(*key) and stats_ready(j["tier"])):
            continue
        if key in draining and not (RUNS / j["name"] / "done.json").exists():
            continue  # its group is about to be evicted for a higher-priority group (evaluation-only legs still go)
        if (RUNS / j["name"] / "paused.json").exists():
            continue  # the job re-queues itself with --resume
        submit(j, st)
        slots -= 1
    save_state(st)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    jobs = plan()
    if a.plan:
        tot = 0.0
        by = {}
        for j in jobs:
            h = est_hours(j)
            tot += h
            by[j["tag"]] = by.get(j["tag"], 0) + h
        print(
            f"{len(jobs)} jobs, est {tot:.0f} GPU-h (per tag: {json.dumps({k: round(v) for k, v in by.items()})})"
        )
        for j in jobs[:20]:
            print(" ", j["tag"], j["name"], f"{est_hours(j):.1f} h")
        return
    from ampscape.io.sync import acquire_lease

    if not acquire_lease("gpu_driver", ROOT):
        print("another gpu_driver holds the lease")
        return
    log(
        f"gpu driver started pid {os.getpid()}: {len(jobs)} jobs, est {sum(est_hours(j) for j in jobs):.0f} GPU-h"
    )
    st = load_state()
    while True:
        try:
            if (LOGS / "GPU_ALERT.txt").exists():
                log("alert present; idle")
            else:
                cycle(jobs, st)
                if all(done(j) for j in jobs):
                    log("all jobs done")
                    break
        except Exception as e:  # noqa: BLE001
            log(f"cycle error: {e!r}")
        acquire_lease("gpu_driver", ROOT)
        if a.once:
            break
        time.sleep(600)


if __name__ == "__main__":
    main()
