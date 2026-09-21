#!/usr/bin/env python
"""Full audit of one tier on the Hub against the plan (owner requirement, 2026-09-16).

For every shard of the manifest: (1) the five task-group files exist on the Hub and their LFS sha256 matches the local
`.uploaded` record; (2) each file is downloaded (one shard at a time, cache deleted afterwards) and the exact set of
sample UUIDs equals the planned assignment of that shard; (3) every sample holds every planned configuration except
the ones its meta records as undefined (`skipped_configs`); for legacy shards without that field the undefined
configurations are re-derived by regenerating the sources from the seed; (4) the per-shard index rows on scratch
agree with the file contents. Writes <build>/audit_<tier>.json and prints a summary; exit 1 on any discrepancy.

  python scripts/audit_tier.py --build data/v1/S --tier S [--shards 0-499] [--workers 4]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile
import threading

import h5py
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGEN_LOCK = threading.Lock()
sys.path.insert(0, str(ROOT))
from ampscape.io.hf_layout import CONFIG_TO_GROUP  # noqa: E402


def hub_files(repo: str, tier: str) -> dict[str, dict]:
    from huggingface_hub import HfApi

    out = {}
    for it in HfApi().list_repo_tree(
        repo, path_in_repo=f"data/{tier}", repo_type="dataset", recursive=True, expand=True
    ):
        lfs = getattr(it, "lfs", None)
        out[it.path] = {
            "size": getattr(it, "size", None),
            "sha256": getattr(lfs, "sha256", None) if lfs else None,
        }
    return out


def undefined_by_regeneration(
    meta: dict, planned: set[str], present: set[str], tiles_root: str | None
) -> set[str]:
    """Legacy samples (no `skipped_configs`): re-derive the undefined planned configurations exactly as prepare would."""
    from ampscape.solve.prepare import derive_skipped_configs

    # the synthetic generators drive NLMpy through NumPy's *global* RNG (seeded_global_rng), which is not thread-safe:
    # serialise regenerations across the audit's download threads or two samples corrupt each other's landscapes
    with REGEN_LOCK:
        return derive_skipped_configs(meta, planned, tiles_root)


def audit_shard(
    shard: int,
    tier: str,
    build: pathlib.Path,
    plan: pd.DataFrame,
    hub: dict,
    repo: str,
    tmp: pathlib.Path,
    tiles_root: str | None,
) -> dict:
    from huggingface_hub import hf_hub_download

    name = f"shard-{shard:05d}"
    rows = plan[plan.shard == shard]
    planned = {r.sample_id: set(json.loads(r.configs)) for r in rows.itertuples()}
    groups_needed = {
        CONFIG_TO_GROUP[c] for cs in planned.values() for c in cs if c in CONFIG_TO_GROUP
    }
    rep = {"shard": name, "n_planned": len(planned), "errors": [], "files": {}}
    marker = build / "shards" / f"{name}.uploaded"
    local = json.loads(marker.read_text()).get("parts", {}) if marker.exists() else {}
    present: dict[str, set[str]] = {}
    metas: dict[str, dict] = {}
    absent_groups: list[
        str
    ] = []  # judged after the skipped configs are known (a group whose every planned
    # config in this shard was legitimately skipped has no file — e.g. T1R when no sample has ≥ 2 habitat patches)
    for grp in sorted(groups_needed):
        rel = f"data/{tier}/{grp}/{name}.h5"
        if rel not in hub:
            absent_groups.append(grp)
            continue
        h = hub[rel]
        loc = local.get(grp, {}).get("sha256")
        rep["files"][rel] = {"hub_sha256": h["sha256"], "local_sha256": loc, "size": h["size"]}
        if loc and h["sha256"] != loc:
            rep["errors"].append(f"sha256 mismatch Hub vs local record: {rel}")
        if not loc:
            rep["errors"].append(f"no local upload record for {rel}")
        try:
            p = hf_hub_download(repo, rel, repo_type="dataset", cache_dir=str(tmp))
            with h5py.File(p, "r") as f:
                for sid in f:
                    present.setdefault(sid, set()).update(f[sid]["configs"].keys())
                    if sid not in metas:
                        metas[sid] = json.loads(f[sid].attrs["meta"])
        except Exception as e:  # noqa: BLE001
            rep["errors"].append(f"unreadable {rel}: {str(e)[:120]}")
    ids_hub, ids_plan = set(present), set(planned)
    if ids_hub != ids_plan:
        rep["errors"].append(
            f"sample ids: {len(ids_hub - ids_plan)} unexpected, {len(ids_plan - ids_hub)} missing"
        )
    n_regen = 0
    wanted_groups: set[str] = set()
    for sid in sorted(ids_hub & ids_plan):
        meta = metas[sid]
        if "skipped_configs" in meta:
            skipped = set(meta["skipped_configs"])
        else:
            missing = planned[sid] - present[sid]
            skipped = (
                undefined_by_regeneration(meta, planned[sid], present[sid], tiles_root)
                if missing
                else set()
            )
            n_regen += bool(missing)
        want = planned[sid] - skipped
        if present[sid] != want:
            rep["errors"].append(f"{sid}: configs {sorted(present[sid])} != planned {sorted(want)}")
        wanted_groups.update(CONFIG_TO_GROUP[c] for c in want if c in CONFIG_TO_GROUP)
    rep["n_regenerated_checks"] = n_regen
    for grp in absent_groups:
        if grp in wanted_groups or not (ids_hub & ids_plan):
            rep["errors"].append(f"missing on Hub: data/{tier}/{grp}/{name}.h5")
        else:
            rep.setdefault("absent_groups_all_skipped", []).append(grp)
    ip = build / "index" / f"{name}.parquet"
    if ip.exists():
        idx = pd.read_parquet(ip, columns=["sample_id", "config"])
        idx_cfg = idx.groupby("sample_id").config.apply(set).to_dict()
        if idx_cfg != present:
            rep["errors"].append("index rows on scratch differ from the Hub file contents")
    else:
        rep["errors"].append("no index rows on scratch")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", required=True)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--repo", default="Xirro/AmpScape")
    ap.add_argument("--shards", default=None)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    build = pathlib.Path(a.build)
    plan = pd.read_parquet(build / "manifest.parquet", columns=["shard", "sample_id", "configs"])
    shards = sorted(int(s) for s in plan.shard.unique())
    if a.shards:
        lo, hi = (int(x) for x in a.shards.split("-"))
        shards = [s for s in shards if lo <= s <= hi]
    hub = hub_files(a.repo, a.tier)
    tiles_root = json.loads((build / "build.json").read_text()).get("pilot")
    from joblib import Parallel, delayed

    def one(sh):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"audit_{sh}_", dir=str(build)))
        try:
            return audit_shard(sh, a.tier, build, plan, hub, a.repo, tmp, tiles_root)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    reps = Parallel(n_jobs=a.workers, prefer="threads")(delayed(one)(sh) for sh in shards)
    bad = [r for r in reps if r["errors"]]
    out = {
        "tier": a.tier,
        "n_shards": len(reps),
        "n_bad": len(bad),
        "bad": bad,
        "n_files": sum(len(r["files"]) for r in reps),
    }
    (build / f"audit_{a.tier}.json").write_text(json.dumps(out, indent=1))
    print(
        f"audit {a.tier}: {len(reps)} shards, {out['n_files']} Hub files, {len(bad)} shards with discrepancies"
    )
    for r in bad[:20]:
        print(" ", r["shard"], r["errors"][:3])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
