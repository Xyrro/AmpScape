"""Merge an inputs shard and its Julia outputs into the final AmpScape HDF5 shard + index rows.

Final layout follows docs/task_specification.md §4: one group per sample::

    /<sample_id>/inputs/{resistance, nodata_mask, covariates?}
    /<sample_id>/configs/<cname>/inputs/{focal_mask | source_strength [+ ground]}, focal_table (JSON attr)
    /<sample_id>/configs/<cname>/outputs/{...solver outputs...}   (raw, never post-processed)
    /<sample_id> attrs: meta (JSON) with every field of §4.3

A configuration is a *task instance*: points → T1 + T2, wall_to_wall_* → T1W, regions → T1(R),
advanced → T3, omniscape → T4. The Parquet index has one row per (sample, config) with QC.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess

import h5py
import numpy as np
import pandas as pd

from ampscape.solve.qc import qc_advanced, qc_omniscape, qc_pairwise, qc_pass

KIND_TASK = {
    "points": "T1,T2",
    "wall_to_wall": "T1W",
    "regions": "T1R",
    "advanced": "T3",
    "omniscape": "T4",
}
GZIP = {"compression": "gzip", "compression_opts": 4, "shuffle": True}


def skipped_column(meta: dict) -> str:
    """Index column: 'config (task: reason); ...' for planned configurations undefined on this landscape ('' if none)."""
    sk = meta.get("skipped_configs") or []
    reasons = meta.get("skipped_reasons") or {}
    if not sk:
        return ""
    from ampscape.solve.prepare import skip_reason

    return "; ".join(f"{c} ({reasons.get(c) or skip_reason(c, True)})" for c in sk)


def git_tag() -> str:
    """Exact tag on HEAD (e.g. v1.0-pipeline), else AMPSCAPE_PIPELINE_TAG, else ""."""
    import os
    import subprocess

    try:
        t = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            cwd=pathlib.Path(__file__).resolve().parents[2],
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        t = ""
    return t or os.environ.get("AMPSCAPE_PIPELINE_TAG", "")


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _copy(src: h5py.Group, dst: h5py.Group, name: str):
    d = src[name]
    out = dst.create_dataset(name, data=d[...], chunks=True, **GZIP)
    for k, v in d.attrs.items():
        out.attrs[k] = v
    return out


def finalize_shard(
    inputs_h5: str,
    outputs_h5: str,
    final_h5: str,
    dataset_version: str,
    solver_preset: dict,
    r_max_lookup: dict | None = None,
) -> pd.DataFrame:
    """Write the final shard and return the index rows (one per sample × config)."""
    rows = []
    sha = git_sha()
    tag = git_tag()
    created = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    pathlib.Path(final_h5).parent.mkdir(parents=True, exist_ok=True)
    with (
        h5py.File(inputs_h5, "r") as fi,
        h5py.File(outputs_h5, "r") as fo,
        h5py.File(final_h5, "w") as ff,
    ):
        ff.attrs["dataset_version"] = dataset_version
        ff.attrs["pipeline_git_sha"] = sha
        ff.attrs["pipeline_tag"] = tag
        ff.attrs["created_at"] = created
        ff.attrs["schema_version"] = "0.1"
        for sid in fi["samples"]:
            gi = fi["samples"][sid]
            meta = json.loads(gi.attrs["meta"])
            if sid not in fo["samples"] or "complete" not in fo["samples"][sid].attrs:
                continue
            go = fo["samples"][sid]["outputs"]
            R = gi["inputs"]["resistance"][...]
            nd = gi["inputs"]["nodata_mask"][...] > 0
            gs = ff.create_group(sid)
            gin = gs.create_group("inputs")
            for name in gi["inputs"]:
                _copy(gi["inputs"], gin, name)
            gcfg = gs.create_group("configs")
            sample_flags: list[str] = []
            r_max = meta.get("r_max") or (
                meta.get("contrast") if meta["family"] == "synthetic" else None
            )
            for cname in gi["configs"]:
                if cname not in go:
                    continue
                kind = gi["configs"][cname].attrs["kind"]
                gc = gcfg.create_group(cname)
                gc.attrs["kind"] = kind
                gc.attrs["task_ids"] = KIND_TASK[kind]
                gci = gc.create_group("inputs")
                for name in gi["configs"][cname]:
                    _copy(gi["configs"][cname], gci, name)
                cm = meta["configs"].get(cname, {})
                gc.attrs["focal_table"] = json.dumps(cm.get("focal_table", []))
                gc.attrs["source_meta"] = json.dumps(cm.get("meta", {}), default=float)
                gco = gc.create_group("outputs")
                out = {k: go[cname][k][...] for k in go[cname]}
                out["stats"] = go[cname].attrs["stats"]
                for k, v in out.items():
                    if k == "stats":
                        continue
                    if k == "reff":
                        gco.create_dataset(k, data=v.astype(np.float64), **GZIP)
                    elif v.dtype.kind == "f":
                        gco.create_dataset(k, data=v.astype(np.float32), chunks=True, **GZIP)
                    else:
                        gco.create_dataset(k, data=v, **GZIP)
                stats = json.loads(out["stats"])
                gco.attrs["solver_stats"] = out["stats"]
                if kind in ("points", "wall_to_wall", "regions"):
                    focal = gi["configs"][cname]["focal_mask"][...]
                    q = qc_pairwise(R, nd, focal, out, r_max)
                elif kind == "advanced":
                    q = qc_advanced(
                        R,
                        nd,
                        gi["configs"][cname]["source_strength"][...],
                        gi["configs"][cname]["ground"][...],
                        out,
                    )
                else:
                    q = qc_omniscape(R, nd, out)
                ok_all, ok_trainval = qc_pass(q["qc_flags"])
                gco.attrs["qc_flags"] = json.dumps(q["qc_flags"])
                gco.attrs["qc_pass"] = bool(ok_all)
                sample_flags += q["qc_flags"]
                k_focal = int(len(cm.get("focal_table", []))) if kind != "advanced" else 0
                rows.append(
                    {
                        "sample_id": sid,
                        "config": cname,
                        "kind": kind,
                        "task_ids": KIND_TASK[kind],
                        "family": meta["family"],
                        "tier": meta["tier"],
                        "H": meta["H"],
                        "W": meta["W"],
                        "generator": meta.get("generator"),
                        "resistance_table_id": meta.get("resistance_table_id"),
                        "tile_id": meta.get("tile_id"),
                        "biome_num": meta.get("biome_num"),
                        "realm": meta.get("realm"),
                        "contrast": meta.get("contrast"),
                        "hard_case": (meta.get("generator_params") or {}).get("hard_case"),
                        "design": (meta.get("generator_params") or {}).get("design"),
                        "lat": meta.get("lat"),
                        "lon": meta.get("lon"),
                        "pixel_m": meta.get("pixel_size_m"),
                        "K": k_focal,
                        "placement": cm.get("meta", {}).get("placement"),
                        "seed": meta["seed"],
                        "solver": q["solver"],
                        "converged": q["converged"],
                        "solve_time_s": q["solve_time_s"],
                        "maxrss_mb": q["maxrss_mb"],
                        "residual_rel": q["residual_rel"],
                        "residual_rel_f32": q.get("residual_rel_f32"),
                        "conservation_err": q["conservation_err"],
                        "edge_ratio": q.get("edge_ratio"),
                        "qc_flags": ",".join(q["qc_flags"]),
                        "qc_pass": ok_all,
                        "qc_trainval": ok_trainval,
                        "skipped_configs": skipped_column(meta),
                        "shard": pathlib.Path(final_h5).name,
                        "dataset_version": dataset_version,
                        "pipeline_git_sha": sha,
                        "pipeline_tag": tag,
                        "created_at": created,
                    }
                )
            meta.update(
                {
                    "solver_name": "Circuitscape.jl/Omniscape.jl",
                    "solver_versions": {
                        "julia": stats.get("julia_version"),
                        "circuitscape": stats.get("circuitscape_version"),
                        "omniscape": stats.get("omniscape_version"),
                    },
                    "solver_preset": solver_preset,
                    "qc_flags": sorted(set(sample_flags)),
                    "created_at": created,
                    "pipeline_git_sha": sha,
                    "pipeline_tag": tag,
                    "dataset_version": dataset_version,
                }
            )
            gs.attrs["meta"] = json.dumps(meta, default=float)
    return pd.DataFrame(rows)


def index_rows_from_final(final_h5: str, shard_name: str | None = None) -> pd.DataFrame:
    """Rebuild the index rows of a finalized shard (or one of its HF task-group files) from the file itself.

    Used when a shard's per-shard index parquet is missing (e.g. its write failed on a full disk after the shard
    had been validated and uploaded). QC values are recomputed from the stored arrays and solver stats with the same
    functions finalize uses, so the rows are identical to a fresh finalize except `created_at`.
    """
    rows = []
    with h5py.File(final_h5, "r") as ff:
        shard = shard_name or pathlib.Path(final_h5).name
        dv, sha, tag = (
            str(ff.attrs.get(k, ""))
            for k in ("dataset_version", "pipeline_git_sha", "pipeline_tag")
        )
        created = str(ff.attrs.get("created_at", ""))
        for sid in ff:
            gs = ff[sid]
            meta = json.loads(gs.attrs["meta"])
            R = gs["inputs"]["resistance"][...]
            nd = gs["inputs"]["nodata_mask"][...] > 0
            r_max = meta.get("r_max") or (
                meta.get("contrast") if meta["family"] == "synthetic" else None
            )
            for cname in gs["configs"]:
                gc = gs["configs"][cname]
                kind = gc.attrs["kind"]
                gco = gc["outputs"]
                out = {k: gco[k][...] for k in gco}
                out["stats"] = gco.attrs["solver_stats"]
                cm = {
                    "focal_table": json.loads(gc.attrs.get("focal_table", "[]")),
                    "meta": json.loads(gc.attrs.get("source_meta", "{}")),
                }
                if kind in ("points", "wall_to_wall", "regions"):
                    q = qc_pairwise(R, nd, gc["inputs"]["focal_mask"][...], out, r_max)
                elif kind == "advanced":
                    q = qc_advanced(
                        R,
                        nd,
                        gc["inputs"]["source_strength"][...],
                        gc["inputs"]["ground"][...],
                        out,
                    )
                else:
                    q = qc_omniscape(R, nd, out)
                ok_all, ok_trainval = qc_pass(q["qc_flags"])
                k_focal = int(len(cm.get("focal_table", []))) if kind != "advanced" else 0
                rows.append(
                    {
                        "sample_id": sid,
                        "config": cname,
                        "kind": kind,
                        "task_ids": KIND_TASK[kind],
                        "family": meta["family"],
                        "tier": meta["tier"],
                        "H": meta["H"],
                        "W": meta["W"],
                        "generator": meta.get("generator"),
                        "resistance_table_id": meta.get("resistance_table_id"),
                        "tile_id": meta.get("tile_id"),
                        "biome_num": meta.get("biome_num"),
                        "realm": meta.get("realm"),
                        "contrast": meta.get("contrast"),
                        "hard_case": (meta.get("generator_params") or {}).get("hard_case"),
                        "design": (meta.get("generator_params") or {}).get("design"),
                        "lat": meta.get("lat"),
                        "lon": meta.get("lon"),
                        "pixel_m": meta.get("pixel_size_m"),
                        "K": k_focal,
                        "placement": cm.get("meta", {}).get("placement"),
                        "seed": meta["seed"],
                        "solver": q["solver"],
                        "converged": q["converged"],
                        "solve_time_s": q["solve_time_s"],
                        "maxrss_mb": q["maxrss_mb"],
                        "residual_rel": q["residual_rel"],
                        "residual_rel_f32": q.get("residual_rel_f32"),
                        "conservation_err": q["conservation_err"],
                        "edge_ratio": q.get("edge_ratio"),
                        "qc_flags": ",".join(q["qc_flags"]),
                        "qc_pass": ok_all,
                        "qc_trainval": ok_trainval,
                        "skipped_configs": skipped_column(meta),
                        "shard": shard,
                        "dataset_version": dv,
                        "pipeline_git_sha": sha,
                        "pipeline_tag": tag,
                        "created_at": created,
                    }
                )
    return pd.DataFrame(rows)
