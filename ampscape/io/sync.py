"""Streaming shard sync: validate → upload → checksum-verify → delete locally (owner decision E).

Storage (≈ 810 GB for v1.0) is the binding constraint, so finished shards must leave scratch as they
complete. This module is the single place that talks to the Hugging Face Hub. **Nothing here pushes
unless `--push` is given**; the default is a dry run that reports what would happen. Pushes are gated
by the owner (CLAUDE.md), and the target repo is `HF_ORG/AmpScape` (private).

State per shard, next to the file:
    shard-NNNNN.h5            final shard (written by finalize)
    shard-NNNNN.ok            written after the validator passes (JSON report)
    shard-NNNNN.uploaded      written after the remote sha256 matched (JSON: repo, path, commit, sha256)
Only shards with `.ok` are uploaded; only shards with `.uploaded` are deleted locally; the Parquet
index rows and quicklooks stay on scratch.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib

from ampscape.io.schema import validate_shard

REPO_LAYOUT = "data/{tier}/{task_group}/{name}"
SUBSET_CORE_SHARDS = {
    "S": 100,
    "M": 100,
    "L": 250,
}  # core ≈ 20k S + 10k M + 5k L landscapes (≈ 50 GB)   # HF layout: any tier / task group downloadable alone


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_path(shard: pathlib.Path, tier: str, task_group: str = "all") -> str:
    return REPO_LAYOUT.format(tier=tier, task_group=task_group, name=shard.name)


def expected_samples(build: pathlib.Path) -> dict[str, int]:
    """Samples per shard from the manifest (shard name -> count); {} if there is no manifest."""
    mp = build / "manifest.parquet"
    if not mp.exists():
        return {}
    import pandas as pd

    m = pd.read_parquet(mp, columns=["shard"])
    return {f"shard-{int(k):05d}": int(v) for k, v in m.groupby("shard").size().items()}


def tiles_root_of(build: pathlib.Path) -> str | None:
    bj = build / "build.json"
    return json.loads(bj.read_text()).get("pilot") if bj.exists() else None


def planned_configs(build: pathlib.Path) -> dict[str, dict[str, set[str]]]:
    """shard name -> {sample_id: set(planned configs)} from the manifest."""
    mp = build / "manifest.parquet"
    if not mp.exists():
        return {}
    import pandas as pd

    m = pd.read_parquet(mp, columns=["shard", "sample_id", "configs"])
    out: dict[str, dict[str, set[str]]] = {}
    for r in m.itertuples():
        out.setdefault(f"shard-{int(r.shard):05d}", {})[r.sample_id] = set(json.loads(r.configs))
    return out


def integrity_check(
    final_h5: pathlib.Path, planned: dict[str, set[str]], tiles_root: str | None = None
) -> list[str]:
    """Owner requirement (2026-09-16): a shard is complete only if its sample ids are exactly the planned set and every
    sample holds every planned configuration except those prepare recorded as undefined (`skipped_configs`)."""
    import h5py

    errors: list[str] = []
    with h5py.File(final_h5, "r") as f:
        ids = set(f.keys())
        if ids != set(planned):
            errors.append(
                f"sample ids differ from the plan: {len(ids - set(planned))} unexpected, {len(set(planned) - ids)} missing"
            )
        for sid in sorted(ids & set(planned)):
            meta = json.loads(f[sid].attrs["meta"])
            present = set(f[sid]["configs"].keys())
            if "skipped_configs" in meta:
                skipped = set(meta["skipped_configs"])
            elif (
                planned[sid] - present
            ):  # legacy meta: re-derive which planned configurations are undefined
                from ampscape.solve.prepare import derive_skipped_configs

                skipped = derive_skipped_configs(meta, planned[sid], tiles_root)
            else:
                skipped = set()
            want = planned[sid] - skipped
            if present != want:
                errors.append(
                    f"{sid}: configs present {sorted(present)} != planned {sorted(want)} (skipped {sorted(skipped)})"
                )
    return errors


def validate(
    shard: pathlib.Path,
    expected: dict[str, int] | None = None,
    planned: dict[str, dict[str, set[str]]] | None = None,
) -> bool:
    """Schema validation plus (2026-09-16) the sample count of the manifest: a shard truncated by a full disk can be
    schema-valid with fewer samples (tier S shard 104 reached the Hub with 5 of 200)."""
    ok = shard.with_suffix(".ok")
    if ok.exists():
        if expected and shard.stem in expected:
            n = json.loads(ok.read_text()).get("n_samples")
            if n != expected[shard.stem]:
                ok.unlink()
                shard.with_suffix(".invalid").write_text(
                    f"sample count {n} != manifest {expected[shard.stem]}"
                )
                return False
        return True
    rep = validate_shard(str(shard))
    if rep.ok and expected and shard.stem in expected and rep.n_samples != expected[shard.stem]:
        shard.with_suffix(".invalid").write_text(
            f"sample count {rep.n_samples} != manifest {expected[shard.stem]}"
        )
        return False
    if rep.ok and planned and shard.stem in planned:
        errs = integrity_check(shard, planned[shard.stem], tiles_root_of(shard.parents[1]))
        if errs:
            shard.with_suffix(".invalid").write_text("\n".join(errs))
            return False
    if rep.ok:
        ok.write_text(
            json.dumps(
                {
                    "validated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                    "n_samples": rep.n_samples,
                    "n_configs": rep.n_configs,
                    "sha256": sha256(shard),
                }
            )
        )
        return True
    shard.with_suffix(".invalid").write_text("\n".join(rep.errors))
    return False


def remote_sha256(api, repo_id: str, path_in_repo: str) -> str | None:
    """sha256 of the LFS/Xet object at `path_in_repo` as reported by the Hub (None if absent)."""
    info = api.get_paths_info(repo_id, [path_in_repo], repo_type="dataset", expand=True)
    for it in info:
        lfs = getattr(it, "lfs", None)
        if lfs and getattr(lfs, "sha256", None):
            return lfs.sha256
    return None


def upload_and_verify(
    shard: pathlib.Path, repo_id: str, path_in_repo: str, push: bool, max_retries: int = 3
) -> dict:
    marker = shard.with_suffix(".uploaded")
    if marker.exists():
        return json.loads(marker.read_text())
    local = json.loads(shard.with_suffix(".ok").read_text())["sha256"]
    if not push:
        return {
            "dry_run": True,
            "repo": repo_id,
            "path": path_in_repo,
            "sha256": local,
            "bytes": shard.stat().st_size,
        }
    from huggingface_hub import HfApi

    api = HfApi()
    for attempt in range(1, max_retries + 1):
        res = api.upload_file(
            path_or_fileobj=str(shard),
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"add {path_in_repo}",
        )
        remote = remote_sha256(api, repo_id, path_in_repo)
        if remote == local:
            rec = {
                "repo": repo_id,
                "path": path_in_repo,
                "sha256": local,
                "commit": getattr(res, "oid", None),
                "uploaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                "attempt": attempt,
            }
            marker.write_text(json.dumps(rec))
            return rec
    raise RuntimeError(f"checksum mismatch after {max_retries} uploads: {shard}")


def delete_local(shard: pathlib.Path, push: bool) -> bool:
    if not shard.with_suffix(".uploaded").exists() or not push:
        return False
    shard.unlink()
    return True


def upload_parts_one_commit(
    parts: dict[str, pathlib.Path], staging: pathlib.Path, repo_id: str
) -> dict[str, dict]:
    """Upload the task-group files of ONE shard in ONE Hub commit, then verify every file's sha256 on the Hub.
    Returns {group: record}; raises RuntimeError on any mismatch (the caller counts the attempt)."""
    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi()
    ops, rels, shas = [], {}, {}
    for grp, part in sorted(parts.items()):
        rel = str(part.relative_to(staging))
        rels[grp], shas[grp] = rel, sha256(part)
        ops.append(CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(part)))
    res = api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        operations=ops,
        commit_message=f"add {pathlib.Path(rels[next(iter(rels))]).name} ({len(ops)} task groups)",
    )
    out = {}
    for grp, rel in rels.items():
        remote = remote_sha256(api, repo_id, rel)
        if remote != shas[grp]:
            raise RuntimeError(f"checksum mismatch on the Hub for {rel}")
        out[grp] = {
            "repo": repo_id,
            "path": rel,
            "sha256": shas[grp],
            "bytes": parts[grp].stat().st_size,
            "commit": getattr(res, "oid", None),
            "uploaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        }
    return out


def sync_live(
    build: pathlib.Path,
    repo_id: str,
    tier: str,
    staging: pathlib.Path,
    push: bool = True,
    delete: bool = True,
    max_failures: int = 2,
) -> list[dict]:
    """v1.0 streaming mode (owner checklist e, revised 2026-09-16): one shard at a time —
    validate (schema) → split into the task-group files in a per-shard temporary staging dir → upload all parts in
    ONE commit → verify each part's sha256 on the Hub → `.uploaded` marker (with bytes) → delete the final shard, the
    raw inputs/outputs and the temporary dir. The temporary dir is removed in every case (also on failure), so a full
    disk cannot leave partial files behind. Every failed cycle on a shard is counted in `.upload_attempts`; after
    `max_failures` consecutive failures the shard gets `.upload_failed` and is skipped (stop rule)."""
    import shutil

    from ampscape.io.hf_layout import split_shard_by_task_group

    out = []
    expected = expected_samples(build)
    planned = planned_configs(build)
    for sh in sorted((build / "shards").glob("shard-*.h5")):
        rec: dict = {"shard": sh.name, "bytes": sh.stat().st_size}
        if sh.with_suffix(".uploaded").exists():
            rec["status"] = "already"
            out.append(rec)
            continue
        if sh.with_suffix(".upload_failed").exists():
            rec["status"] = "failed_twice"
            out.append(rec)
            continue
        try:
            valid = validate(sh, expected, planned)
        except Exception as e:  # unreadable / truncated final
            sh.with_suffix(".invalid").write_text(f"unreadable: {e}")
            valid = False
        if not valid:
            rec["status"] = "invalid"
            out.append(rec)
            continue
        tmp = staging / "tmp" / sh.stem
        attempts_f = sh.with_suffix(".upload_attempts")
        attempts = (
            json.loads(attempts_f.read_text())
            if attempts_f.exists()
            else {"failures": 0, "log": []}
        )
        try:
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True, exist_ok=True)
            parts = split_shard_by_task_group(sh, tmp, tier)
            if not push:
                rec["status"] = "dry_run"
                rec["parts"] = {g: str(p.relative_to(tmp)) for g, p in parts.items()}
                out.append(rec)
                continue
            recs = upload_parts_one_commit(parts, tmp, repo_id)
        except Exception as e:  # disk full, network, checksum mismatch, ...
            attempts["failures"] += 1
            attempts["log"].append(
                {"at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "error": str(e)[:300]}
            )
            attempts_f.write_text(json.dumps(attempts))
            rec["status"] = "upload_error"
            rec["error"] = str(e)[:200]
            if attempts["failures"] >= max_failures:
                sh.with_suffix(".upload_failed").write_text(json.dumps(attempts))
                rec["status"] = "upload_failed"
            out.append(rec)
            continue
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        sh.with_suffix(".uploaded").write_text(
            json.dumps(
                {
                    "parts": recs,
                    "bytes_final": sh.stat().st_size,
                    "uploaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                }
            )
        )
        attempts_f.unlink(missing_ok=True)
        rec["status"] = "uploaded"
        if delete:
            sh.unlink()
            for f in (
                build / "inputs" / f"{sh.stem}.inputs.h5",
                build / "outputs" / f"{sh.stem}.outputs.h5",
            ):
                f.unlink(missing_ok=True)
            rec["status"] = "uploaded+deleted"
        out.append(rec)
    return out


def hub_gb(repo_id: str, prefix: str = "data/") -> float:
    """GB of files under `prefix` in the dataset repo, from the Hub's own file listing."""
    from huggingface_hub import HfApi

    tot = 0
    for it in HfApi().list_repo_tree(repo_id, repo_type="dataset", recursive=True):
        if it.path.startswith(prefix) and getattr(it, "size", None):
            tot += it.size
    return tot / 1e9


def publish_index(
    build: pathlib.Path, repo_id: str, tier: str, staging: pathlib.Path, push: bool = True
) -> dict:
    """Upload the current per-tier index (from the finalized shards' index rows) and split lists to the Hub."""
    import pandas as pd

    from ampscape.io.hf_layout import CONFIG_TO_GROUP

    rows = sorted((build / "index").glob("shard-*.parquet"))
    if not rows:
        return {"status": "no index rows"}
    idx = pd.concat([pd.read_parquet(p) for p in rows], ignore_index=True)
    if "split" not in idx and (build / "index.parquet").exists():
        idx = pd.read_parquet(build / "index.parquet")
    if "split" not in idx:  # per-shard finalize rows carry no split: apply the v1.0 rule now
        from ampscape.splits.assign import add_splits

        idx = add_splits(idx, build)
    # per-sample skipped configurations with reasons (owner requirement 2026-09-16): rows written before the field existed
    # get it from the plan minus the configurations present, with the kind's documented reason (legitimate absences only —
    # the tier audit guarantees that every other planned configuration is present)
    from ampscape.solve.prepare import skip_reason

    planned = planned_configs(build)
    present = idx.groupby("sample_id").config.apply(set).to_dict()
    u = idx.drop_duplicates("sample_id").set_index("sample_id")
    shard_of = u.shard.str.replace(".h5", "", regex=False).to_dict()

    # `regions` is only planned where habitat information exists (real tiles; synthetic patch mosaics), so an
    # absent planned `regions` always means "no eligible habitat patches"
    def legacy_col(sid: str) -> str:
        want = planned.get(shard_of.get(sid, ""), {}).get(sid, set())
        return "; ".join(
            f"{c} ({skip_reason(c, True)})" for c in sorted(want - present.get(sid, set()))
        )

    if "skipped_configs" not in idx:
        idx["skipped_configs"] = ""
    idx["skipped_configs"] = idx["skipped_configs"].fillna("")
    need = idx.skipped_configs.eq("") & idx.sample_id.map(
        lambda sid: bool(
            planned.get(shard_of.get(sid, ""), {}).get(sid, set()) - present.get(sid, set())
        )
    )
    idx.loc[need, "skipped_configs"] = idx.loc[need, "sample_id"].map(legacy_col)
    idx["task_group"] = idx.config.map(CONFIG_TO_GROUP)
    idx["hf_path"] = [
        f"data/{tier}/{g}/{s}" for g, s in zip(idx.task_group, idx.shard, strict=True)
    ]
    # download subsets (plan §5.2, nested): mini = the first 3 shards of S (600 landscapes, all tasks, ≈ 0.4 GB);
    # core = the first SUBSET_CORE_SHARDS[tier] shards of S/M/L; full = everything
    shard_no = idx.shard.str.extract(r"(\d+)")[0].astype(int)
    idx["subset_mini"] = (tier == "S") & (shard_no < 3)
    idx["subset_core"] = idx["subset_mini"] | (shard_no < SUBSET_CORE_SHARDS.get(tier, 0))
    idx["subset_full"] = True
    (staging / "index").mkdir(parents=True, exist_ok=True)
    idx.to_parquet(staging / "index" / f"{tier}.parquet", index=False)
    for sub in ("mini", "core", "full"):
        part = idx[idx[f"subset_{sub}"]]
        if not len(part):
            continue
        d = staging / "splits" / sub
        d.mkdir(parents=True, exist_ok=True)
        for split, g in part.groupby("split"):
            g[["sample_id"]].drop_duplicates().to_parquet(d / f"{split}.parquet", index=False)
    if push:
        from huggingface_hub import HfApi

        HfApi().upload_folder(
            repo_id=repo_id,
            repo_type="dataset",
            folder_path=str(staging),
            allow_patterns=["index/*", "splits/**"],
            delete_patterns=[f"splits/*/{tier}_*"] if False else None,
            commit_message=f"index/{tier}: {idx.sample_id.nunique()} samples",
        )
    return {
        "status": "published" if push else "dry_run",
        "tier": tier,
        "samples": int(idx.sample_id.nunique()),
        "rows": len(idx),
    }


def acquire_lease(name: str, root: pathlib.Path, fresh_s: float = 1500.0) -> bool:
    """Cross-host single-instance lease in <root>/logs/lease_<name>.json ({host, pid, ts}). Returns True when this
    process may run: no lease, a stale lease (older than fresh_s), or a lease held by this very host:pid. A fresh lease
    held by another host:pid means another instance is active (e.g. started from a different login node, where pid
    locks cannot see this node's processes, 2026-09-19) — the caller must stand down."""
    import os
    import socket
    import time

    lf = root / "logs" / f"lease_{name}.json"
    me = {"host": socket.gethostname(), "pid": os.getpid()}
    try:
        cur = json.loads(lf.read_text())
    except Exception:  # noqa: BLE001
        cur = None
    if (
        cur
        and time.time() - cur.get("ts", 0) < fresh_s
        and (cur.get("host"), cur.get("owner"))
        != (me["host"], os.environ.get("AMPSCAPE_LEASE_OWNER", str(os.getppid())))
    ):
        return False
    lf.parent.mkdir(exist_ok=True)
    lf.write_text(
        json.dumps(
            {
                **me,
                "owner": os.environ.get("AMPSCAPE_LEASE_OWNER", str(os.getppid())),
                "ts": time.time(),
            }
        )
    )
    return True


def scratch_used_gb(root: pathlib.Path) -> float:
    """Bytes under root via `du -sb` (a Python walk over the ~100k tile files takes minutes on Lustre)."""
    import subprocess

    try:
        out = subprocess.run(
            ["du", "-sb", str(root)], capture_output=True, text=True, timeout=600
        ).stdout
        return int(out.split()[0]) / 1e9
    except Exception:  # noqa: BLE001
        return 0.0


def sync_build(
    build: pathlib.Path,
    repo_id: str,
    tier: str,
    push: bool = False,
    delete: bool = False,
    soft_limit_gb: float = 120.0,
    hard_limit_gb: float = 150.0,
) -> list[dict]:
    """One pass over a build's final shards. Returns per-shard records."""
    shards = sorted((build / "shards").glob("shard-*.h5"))
    used = sum(p.stat().st_size for p in shards) / 1e9
    out = []
    for sh in shards:
        rec: dict = {"shard": sh.name, "bytes": sh.stat().st_size}
        if not validate(sh):
            rec["status"] = "invalid"
            out.append(rec)
            continue
        rec.update(upload_and_verify(sh, repo_id, repo_path(sh, tier), push))
        rec["status"] = "uploaded" if sh.with_suffix(".uploaded").exists() else "dry_run"
        if delete and delete_local(sh, push):
            rec["status"] = "uploaded+deleted"
        out.append(rec)
    out.append(
        {
            "shard": "_summary",
            "local_gb": round(used, 2),
            "soft_limit_gb": soft_limit_gb,
            "hard_limit_gb": hard_limit_gb,
            "generation_allowed": used < hard_limit_gb,
            "warn": used >= soft_limit_gb,
        }
    )
    return out


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Validate, upload (gated), verify and delete finished shards"
    )
    ap.add_argument("--build", required=True)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--repo", default=f"{os.environ.get('HF_ORG', 'Xirro')}/AmpScape")
    ap.add_argument(
        "--push", action="store_true", help="actually upload (owner-gated); default dry run"
    )
    ap.add_argument(
        "--delete", action="store_true", help="delete local shards after verified upload"
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="v1.0 streaming mode: split by task group, upload, verify, delete (implies --push --delete)",
    )
    ap.add_argument(
        "--staging", default=None, help="HF-layout staging dir for --live (default <build>/hf)"
    )
    ap.add_argument(
        "--publish-index",
        action="store_true",
        help="also upload the current index/<tier>.parquet and split lists",
    )
    a = ap.parse_args(argv)
    build = pathlib.Path(a.build)
    if a.live:
        root = pathlib.Path(__file__).resolve().parents[2]
        if not acquire_lease(f"sync_{a.tier}", root):
            print(
                json.dumps(
                    {
                        "summary": True,
                        "skipped": "another sync instance holds the lease (other host/pid)",
                    }
                )
            )
            return 0
        staging = pathlib.Path(a.staging) if a.staging else build / "hf"
        recs = sync_live(build, a.repo, a.tier, staging, push=True, delete=True)
        if a.publish_index:
            recs.append(publish_index(build, a.repo, a.tier, staging, push=True))
        for rec in recs:
            print(json.dumps(rec))
        n_fail = sum(1 for r in recs if r.get("status") in ("upload_failed", "failed_twice"))
        n_new = sum(1 for r in recs if r.get("status", "").startswith("uploaded"))
        print(json.dumps({"summary": True, "uploaded_this_cycle": n_new, "failed_twice": n_fail}))
        return 2 if n_fail else 0
    for rec in sync_build(build, a.repo, a.tier, push=a.push, delete=a.delete):
        print(json.dumps(rec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
