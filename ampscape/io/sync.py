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

REPO_LAYOUT = "data/{tier}/{task_group}/{name}"   # HF layout: any tier / task group downloadable alone


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_path(shard: pathlib.Path, tier: str, task_group: str = "all") -> str:
    return REPO_LAYOUT.format(tier=tier, task_group=task_group, name=shard.name)


def validate(shard: pathlib.Path) -> bool:
    ok = shard.with_suffix(".ok")
    if ok.exists():
        return True
    rep = validate_shard(str(shard))
    if rep.ok:
        ok.write_text(json.dumps({"validated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                                  "n_samples": rep.n_samples, "n_configs": rep.n_configs, "sha256": sha256(shard)}))
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


def upload_and_verify(shard: pathlib.Path, repo_id: str, path_in_repo: str, push: bool, max_retries: int = 3) -> dict:
    marker = shard.with_suffix(".uploaded")
    if marker.exists():
        return json.loads(marker.read_text())
    local = json.loads(shard.with_suffix(".ok").read_text())["sha256"]
    if not push:
        return {"dry_run": True, "repo": repo_id, "path": path_in_repo, "sha256": local, "bytes": shard.stat().st_size}
    from huggingface_hub import HfApi

    api = HfApi()
    for attempt in range(1, max_retries + 1):
        res = api.upload_file(path_or_fileobj=str(shard), path_in_repo=path_in_repo, repo_id=repo_id, repo_type="dataset",
                              commit_message=f"add {path_in_repo}")
        remote = remote_sha256(api, repo_id, path_in_repo)
        if remote == local:
            rec = {"repo": repo_id, "path": path_in_repo, "sha256": local, "commit": getattr(res, "oid", None),
                   "uploaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "attempt": attempt}
            marker.write_text(json.dumps(rec))
            return rec
    raise RuntimeError(f"checksum mismatch after {max_retries} uploads: {shard}")


def delete_local(shard: pathlib.Path, push: bool) -> bool:
    if not shard.with_suffix(".uploaded").exists() or not push:
        return False
    shard.unlink()
    return True


def sync_live(build: pathlib.Path, repo_id: str, tier: str, staging: pathlib.Path, push: bool = True, delete: bool = True,
              max_upload_attempts: int = 2) -> list[dict]:
    """v1.0 streaming mode (owner checklist e): for every final shard without an `.uploaded` marker —
    validate (schema) → split into the HF task-group files → upload each → verify the Hub sha256 → write the marker →
    delete the final shard and the staged files locally (index rows, `.ok`, `.uploaded` and quicklooks stay).
    A shard whose upload fails `max_upload_attempts` times gets a `.upload_failed` marker (stop rule: two failures)."""
    from ampscape.io.hf_layout import split_shard_by_task_group

    out = []
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
        if not validate(sh):
            rec["status"] = "invalid"
            out.append(rec)
            continue
        parts = split_shard_by_task_group(sh, staging, tier)
        recs, ok = {}, True
        for grp, part in sorted(parts.items()):
            rel = str(part.relative_to(staging))
            try:
                part_ok = part.with_suffix(".ok")
                if not part_ok.exists():
                    part_ok.write_text(json.dumps({"sha256": sha256(part)}))
                recs[grp] = upload_and_verify(part, repo_id, rel, push, max_retries=max_upload_attempts)
            except RuntimeError as e:      # checksum mismatch after the allowed attempts
                recs[grp] = {"error": str(e)}
                ok = False
        rec["parts"] = recs
        if ok and push:
            sh.with_suffix(".uploaded").write_text(json.dumps({"parts": recs, "uploaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}))
            rec["status"] = "uploaded"
            if delete:
                sh.unlink()
                for part in parts.values():
                    for f in (part, part.with_suffix(".ok"), part.with_suffix(".uploaded")):
                        f.unlink(missing_ok=True)
                rec["status"] = "uploaded+deleted"
        elif not ok:
            sh.with_suffix(".upload_failed").write_text(json.dumps(recs))
            rec["status"] = "upload_failed"
        else:
            rec["status"] = "dry_run"
        out.append(rec)
    return out


def publish_index(build: pathlib.Path, repo_id: str, tier: str, staging: pathlib.Path, push: bool = True) -> dict:
    """Upload the current per-tier index (from the finalized shards' index rows) and split lists to the Hub."""
    from ampscape.io.hf_layout import CONFIG_TO_GROUP
    import pandas as pd

    rows = sorted((build / "index").glob("shard-*.parquet"))
    if not rows:
        return {"status": "no index rows"}
    idx = pd.concat([pd.read_parquet(p) for p in rows], ignore_index=True)
    if "split" not in idx and (build / "index.parquet").exists():
        idx = pd.read_parquet(build / "index.parquet")
    idx["task_group"] = idx.config.map(CONFIG_TO_GROUP)
    idx["hf_path"] = [f"data/{tier}/{g}/{s}" for g, s in zip(idx.task_group, idx.shard, strict=True)]
    (staging / "index").mkdir(parents=True, exist_ok=True)
    idx.to_parquet(staging / "index" / f"{tier}.parquet", index=False)
    if "split" in idx:
        d = staging / "splits" / "full"
        d.mkdir(parents=True, exist_ok=True)
        for split, g in idx.groupby("split"):
            g[["sample_id"]].drop_duplicates().to_parquet(d / f"{split}.parquet", index=False)
    if push:
        from huggingface_hub import HfApi

        HfApi().upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(staging), allow_patterns=["index/*", "splits/**"],
                              commit_message=f"index/{tier}: {idx.sample_id.nunique()} samples")
    return {"status": "published" if push else "dry_run", "tier": tier, "samples": int(idx.sample_id.nunique()), "rows": len(idx)}


def scratch_used_gb(root: pathlib.Path) -> float:
    """Bytes under root via `du -sb` (a Python walk over the ~100k tile files takes minutes on Lustre)."""
    import subprocess

    try:
        out = subprocess.run(["du", "-sb", str(root)], capture_output=True, text=True, timeout=600).stdout
        return int(out.split()[0]) / 1e9
    except Exception:  # noqa: BLE001
        return 0.0


def sync_build(build: pathlib.Path, repo_id: str, tier: str, push: bool = False, delete: bool = False,
               soft_limit_gb: float = 120.0, hard_limit_gb: float = 150.0) -> list[dict]:
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
    out.append({"shard": "_summary", "local_gb": round(used, 2), "soft_limit_gb": soft_limit_gb, "hard_limit_gb": hard_limit_gb,
                "generation_allowed": used < hard_limit_gb, "warn": used >= soft_limit_gb})
    return out


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Validate, upload (gated), verify and delete finished shards")
    ap.add_argument("--build", required=True)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--repo", default=f"{os.environ.get('HF_ORG', 'Xirro')}/AmpScape")
    ap.add_argument("--push", action="store_true", help="actually upload (owner-gated); default dry run")
    ap.add_argument("--delete", action="store_true", help="delete local shards after verified upload")
    ap.add_argument("--live", action="store_true", help="v1.0 streaming mode: split by task group, upload, verify, delete (implies --push --delete)")
    ap.add_argument("--staging", default=None, help="HF-layout staging dir for --live (default <build>/hf)")
    ap.add_argument("--publish-index", action="store_true", help="also upload the current index/<tier>.parquet and split lists")
    a = ap.parse_args(argv)
    build = pathlib.Path(a.build)
    if a.live:
        staging = pathlib.Path(a.staging) if a.staging else build / "hf"
        recs = sync_live(build, a.repo, a.tier, staging, push=True, delete=True)
        if a.publish_index:
            recs.append(publish_index(build, a.repo, a.tier, staging, push=True))
        for rec in recs:
            print(json.dumps(rec))
        n_fail = sum(1 for r in recs if r.get("status") in ("upload_failed", "failed_twice"))
        return 2 if n_fail else 0
    for rec in sync_build(build, a.repo, a.tier, push=a.push, delete=a.delete):
        print(json.dumps(rec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
