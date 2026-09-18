"""Evaluation harness (brief §11): predictions directory + split → metrics JSON + Markdown table.

Predictions format (documented, framework-agnostic)
---------------------------------------------------
``<pred_dir>/predictions.h5``  one group per sample, one subgroup per configuration::

    /<sample_id>/<config>/cum_current      float32 (H,W)      T1, T1W, T1R, T4
    /<sample_id>/<config>/voltage          float32 (H,W) or (P,H,W)   optional (T1 first pair, T3) -> Kirchhoff + acceleration
    /<sample_id>/<config>/pairwise_current float32 (P,H,W)    optional
    /<sample_id>/<config>/reff             float64 (K,K)      T2 (points/regions/wall_to_wall)
    /<sample_id>/<config>/current          float32 (H,W)      T3
    /<sample_id>/<config>/flow_potential, normalized          T4 optional
    attrs on the config group: inference_time_s (float, per configuration, wall clock incl. any preprocessing)

``<pred_dir>/meta.json``: {"model": str, "task": str, "tier": str, "split": str, "notes": str, "seed": int, ...}

Targets come from a build root (``index.parquet`` + ``shards/*.h5``) or an HF-layout root. Metrics are
computed per (sample, config) and aggregated per task with mean, median and count; the JSON keeps the
per-sample rows. Determinism: samples are processed in sorted order and no randomness is used.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

import h5py
import numpy as np
import pandas as pd

from ampscape.data.dataset import _load_index
from ampscape.metrics import domain, efficiency, nonsource, physics, pixel, reff

KIND_TASK = {
    "points": "T1",
    "wall_to_wall": "T1W",
    "regions": "T1R",
    "advanced": "T3",
    "omniscape": "T4",
}


def _mask(nodata: np.ndarray, focal: np.ndarray | None, kind: str) -> np.ndarray:
    m = nodata == 0
    if kind == "wall_to_wall" and focal is not None:
        m &= focal == 0  # strip pixels carry the injected current by convention; excluded
    return m


def load_t4_reference(ref_dir: str | pathlib.Path | None) -> dict[str, np.ndarray]:
    """{sample_id: block-1 cum_current} from an aux block-1 reference build (docs/t4_fidelity.md); {} if None."""
    if not ref_dir:
        return {}
    import h5py

    out: dict[str, np.ndarray] = {}
    for o in sorted((pathlib.Path(ref_dir) / "outputs").glob("shard-*.outputs.h5")):
        with h5py.File(o, "r") as f:
            for sid in f["samples"]:
                g = f["samples"][sid]
                if "outputs" in g and "omniscape" in g["outputs"]:
                    out[sid] = g["outputs"]["omniscape"]["cum_current"][...]
    return out


def evaluate_sample(
    kind: str,
    gs: h5py.Group,
    gc: h5py.Group,
    gp: h5py.Group,
    R: np.ndarray,
    nd: np.ndarray,
    t4_reference: dict | None = None,
    sid: str | None = None,
) -> dict:
    out: dict = {}
    o = gc["outputs"]
    focal = gc["inputs"]["focal_mask"][...] if "focal_mask" in gc["inputs"] else None
    m = _mask(nd, focal, kind)
    if kind in ("points", "wall_to_wall", "regions"):
        if "cum_current" in gp:
            p, t = gp["cum_current"][...], o["cum_current"][...]
            if kind == "omniscape" and t4_reference and sid in t4_reference:
                # official T4 surface at M/L (owner decision 2026-09-18): primary metrics against the exact block-1 map,
                # the block-centred production target becomes the secondary `bc_*` set
                t_bc, t = t, t4_reference[sid]
                for k, v in pixel.all_pixel(p, t_bc, m).items():
                    out[f"bc_{k}"] = v
                for k, v in domain.all_domain(p, t_bc, m).items():
                    out[f"bc_{k}"] = v
                out["t4_target"] = "block1_reference"
            out.update(pixel.all_pixel(p, t, m))
            out.update(domain.all_domain(p, t, m))
            out.update(
                nonsource.all_nonsource(p, t, nonsource.nonsource_mask(kind, m, focal=focal), m)
            )
            out.update({f"phys_{k}": v for k, v in physics.nonnegativity(p, m).items()})
            out["phys_throughput_err"] = physics.throughput_error(p, t, m)
            if (
                "pairwise_current" in gp
            ):  # per-pair maps: a unit source/ground pixel carries exactly 1 A
                pc = gp["pairwise_current"][...]
                pi = o["pair_index"][...]
                errs = [
                    physics.focal_current_error(
                        pc[q], np.where(np.isin(focal, pi[q]), focal, 0), None
                    )
                    for q in range(pc.shape[0])
                ]
                out["phys_focal_current_err"] = float(np.nanmean(errs))
            elif kind == "wall_to_wall":  # single pair: the cumulative map is the pair map
                out["phys_focal_current_err"] = physics.focal_current_error(p, focal, None)
        if "reff" in gp:
            out.update(reff.all_reff(gp["reff"][...], o["reff"][...]))
        if "voltage" in gp and "labels" in o:
            v = gp["voltage"][...]
            v0 = v[0] if v.ndim == 3 else v
            pi = o["pair_index"][...][0]
            src, gnd = focal == int(pi[1]), focal == int(pi[0])
            inj = np.zeros(R.shape)
            inj[src] = 1.0 / src.sum()
            out["phys_kirchhoff_residual"] = physics.kirchhoff_residual(
                R,
                nd,
                v0.astype(np.float64),
                inj,
                grounded=gnd,
                supernode=src if src.sum() > 1 else None,
            )
    elif kind == "advanced":
        if "current" in gp:
            p, t = gp["current"][...], o["current"][...]
            out.update(pixel.all_pixel(p, t, m))
            out.update(domain.all_domain(p, t, m))
            out.update(
                nonsource.all_nonsource(
                    p,
                    t,
                    nonsource.nonsource_mask(
                        kind,
                        m,
                        source_strength=gc["inputs"]["source_strength"][...],
                        ground=gc["inputs"]["ground"][...] if "ground" in gc["inputs"] else None,
                    ),
                    m,
                )
            )
            out.update({f"phys_{k}": v for k, v in physics.nonnegativity(p, m).items()})
            out["phys_throughput_err"] = physics.throughput_error(p, t, m)
        if "voltage" in gp:
            out["voltage_mae"] = pixel.mse(gp["voltage"][...], o["voltage"][...], m) ** 0.5
            out["phys_kirchhoff_residual"] = physics.kirchhoff_residual(
                R,
                nd,
                gp["voltage"][...].astype(np.float64),
                gc["inputs"]["source_strength"][...].astype(np.float64),
                grounded=gc["inputs"]["ground"][...] > 0,
            )
    elif kind == "omniscape":
        for k in ("cum_current", "normalized", "flow_potential"):
            if k in gp:
                p, t = gp[k][...], o[k][...]
                pre = "" if k == "cum_current" else f"{k}_"
                out.update({pre + kk: vv for kk, vv in pixel.all_pixel(p, t, m).items()})
                if k == "cum_current":
                    out.update(domain.all_domain(p, t, m))
                    out.update({f"phys_{kk}": vv for kk, vv in physics.nonnegativity(p, m).items()})
    out["inference_time_s"] = float(gp.attrs.get("inference_time_s", np.nan))
    return out


def evaluate(
    pred_dir: str | pathlib.Path,
    split: str | list[str],
    root: str | pathlib.Path,
    tier: str | None = "S",
    subset: str | None = None,
    out_dir: str | pathlib.Path | None = None,
    acceleration: bool = False,
    t4_reference: str | pathlib.Path | None = None,
) -> dict:
    pred_dir = pathlib.Path(pred_dir)
    meta = (
        json.loads((pred_dir / "meta.json").read_text())
        if (pred_dir / "meta.json").exists()
        else {}
    )
    idx = _load_index(pathlib.Path(root), tier)
    t4_ref = load_t4_reference(t4_reference)
    splits = [split] if isinstance(split, str) else list(split)
    idx = idx[idx.split.isin(splits) & idx.qc_pass]
    if subset and f"subset_{subset}" in idx:
        idx = idx[idx[f"subset_{subset}"]]
    rows = []
    with h5py.File(pred_dir / "predictions.h5", "r") as fp:
        for r in idx.sort_values(["sample_id", "config"]).itertuples():
            if r.sample_id not in fp or r.config not in fp[r.sample_id]:
                continue
            with h5py.File(r.path, "r") as f:
                gs = f[r.sample_id]
                gc = gs["configs"][r.config]
                R = gs["inputs"]["resistance"][...]
                nd = gs["inputs"]["nodata_mask"][...]
                m = evaluate_sample(
                    r.kind,
                    gs,
                    gc,
                    fp[r.sample_id][r.config],
                    R,
                    nd,
                    t4_reference=t4_ref,
                    sid=r.sample_id,
                )
            m.update(
                {
                    "sample_id": r.sample_id,
                    "config": r.config,
                    "kind": r.kind,
                    "task": KIND_TASK[r.kind],
                    "family": r.family,
                    "split": r.split,
                    "solve_time_s": r.solve_time_s,
                    "speedup": efficiency.speedup(r.solve_time_s, m["inference_time_s"]),
                }
            )
            for c in (
                "test_ood_region",
                "test_ood_scale",
                "test_ood_table",
                "test_ood_contrast",
                "test_ood_synth2real",
            ):
                if c in idx:
                    m[c] = bool(getattr(r, c))
            rows.append(m)
    df = pd.DataFrame(rows)
    result = {
        "model": meta.get("model", pred_dir.name),
        "meta": meta,
        "root": str(root),
        "tier": tier,
        "splits": splits,
        "subset": subset,
        "n_rows": int(len(df)),
        "evaluated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "per_task": {},
        "per_sample": df.to_dict("records"),
    }
    if len(df):
        num = [c for c in df.columns if df[c].dtype.kind == "f"]
        for task, g in df.groupby("task"):
            agg = {
                c: {
                    "mean": float(np.nanmean(g[c])),
                    "median": float(np.nanmedian(g[c])),
                    "n": int(g[c].notna().sum()),
                }
                for c in num
                if g[c].notna().any()
            }
            agg["speedup"] = efficiency.summarize_speedup(
                g.solve_time_s.tolist(), g.inference_time_s.tolist()
            )
            result["per_task"][task] = agg
    if acceleration:
        from ampscape.metrics.acceleration import run_warm_start_eval, summarize

        srcs = sorted(set(idx.path))
        recs = []
        for s in srcs:
            recs += run_warm_start_eval(
                s, pred_dir / "predictions.h5", pred_dir / f"warm_start_{pathlib.Path(s).stem}.json"
            )
        result["acceleration"] = {"summary": summarize(recs), "records": recs}
    if out_dir:
        out_dir = pathlib.Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "results.json").write_text(json.dumps(result, indent=1, default=float))
        (out_dir / "results.md").write_text(markdown_table(result))
    return result


PRIMARY = [
    "mae_log10eps",
    "ns_rel_l2",
    "ns_mae_log10eps",
    "ns_top5_iou",
    "rel_l2",
    "top5_iou",
    "pinch_recall",
    "spearman",
    "corridor_dice_q10",
    "reff_rel_error",
    "reff_spearman",
    "phys_kirchhoff_residual",
    "phys_focal_current_err",
    "phys_neg_fraction",
    "voltage_mae",
    "normalized_mae_log10eps",
]
SECONDARY = [
    "bc_mae_log10eps",
    "bc_rel_l2",
    "bc_top5_iou",
    "bc_pinch_recall",
    "ns_top1_iou",
    "ns_top10_iou",
    "ns_fraction",
    "ssim",
    "psnr_db",
    "mse",
    "top1_iou",
    "top10_iou",
    "reff_mae_log10",
    "reff_nn_agreement",
    "reff_symmetry",
    "phys_throughput_err",
]


def markdown_table(result: dict) -> str:
    lines = [
        f"# Evaluation: {result['model']}",
        "",
        f"root `{result['root']}`, tier {result['tier']}, splits {result['splits']}, subset {result['subset']}, {result['n_rows']} (sample, config) rows, {result['evaluated_at']}",
        "",
    ]
    for task, agg in result["per_task"].items():
        lines += [f"## {task}", "", "| metric | mean | median | n |", "|---|---|---|---|"]
        for k in PRIMARY + SECONDARY:
            if k in agg:
                v = agg[k]
                lines.append(
                    f"| {k}{' (secondary)' if k in SECONDARY else ''} | {v['mean']:.4g} | {v['median']:.4g} | {v['n']} |"
                )
        sp = agg.get("speedup", {})
        if sp.get("speedup_median") is not None and not np.isnan(sp.get("speedup_median", np.nan)):
            lines.append(
                f"| speed-up vs solver (median / geomean) | {sp['speedup_median']:.3g} | {sp['speedup_geomean']:.3g} | |"
            )
        lines.append("")
    if "acceleration" in result:
        s = result["acceleration"]["summary"]
        lines += [
            "## Solver acceleration (AMG-PCG warm start from predicted voltage)",
            "",
            f"systems {s.get('n_systems')}: iterations zero-start median {s.get('iters_zero_median')} → warm {s.get('iters_warm_median')} "
            f"(median reduction {s.get('iter_reduction_median', float('nan')):.1%}); time reduction median {s.get('time_reduction_median', float('nan')):.1%}; "
            f"warm-start residual median {s.get('residual_start_warm_median', float('nan')):.2e}",
            "",
        ]
    return "\n".join(lines)
