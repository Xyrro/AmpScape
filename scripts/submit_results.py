#!/usr/bin/env python
"""Benchmark submission path (docs/submission.md): validate a predictions directory against the index and the harness,
turn harness results into a leaderboard entry, append entries to the append-only leaderboard under aux/leaderboard/,
and seed the leaderboard with the official Phase 10-full baselines. Every number in an entry comes from a results file
(the harness `results.json`, or a run's `results.json` / `results_transfer.json`); nothing is recomputed here except
means / standard deviations over seeds.

  python scripts/submit_results.py validate --predictions <dir> --root <data root> --tier M --split test_id \\
      [--workers 8] [--t4-reference aux/t4_bs1_reference/M_bs1] [--no-eval]
  python scripts/submit_results.py make-entry --results <dir>/results.json --meta <dir>/meta.json \\
      [--seeds <results.json> ...] [--submitter NAME] [--t4-target production|block1_reference] --out entry.json
  python scripts/submit_results.py append --entry entry.json [entry2.json ...] [--leaderboard aux/leaderboard] [--push]
  python scripts/submit_results.py seed-baselines --runs runs/full [--leaderboard aux/leaderboard] [--push]

`--push` uploads results.jsonl + README.md through scripts/push_aux.py (login node only, maintainer only).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEADERBOARD_DIR = ROOT / "aux" / "leaderboard"
HUB_DEST = "aux/leaderboard"
REPO = "Xirro/AmpScape"

TASKS = ("T1", "T1W", "T1R", "T2", "T3", "T4")
TIERS = ("S", "M", "L", "XL", "XXL")
SPLITS = ("test_id", "test_ood", "ood_region", "test_ood_published")
T4_TARGETS = ("production", "block1_reference")
TIER_PX = {"S": 128, "M": 256, "L": 512, "XL": 1024, "XXL": 2048}
TASK_KIND = {
    "T1": "points",
    "T2": "points",
    "T1W": "wall_to_wall",
    "T1R": "regions",
    "T3": "advanced",
    "T4": "omniscape",
}
# datasets the harness needs per task (predictions.h5 layout: ampscape/eval/harness.py module docstring)
TASK_DATASETS = {
    "T1": ("cum_current",),
    "T1W": ("cum_current",),
    "T1R": ("cum_current",),
    "T2": ("reff",),
    "T3": ("current",),
    "T4": ("cum_current",),
}
KNOWN_DATASETS = {
    "cum_current",
    "voltage",
    "pairwise_current",
    "reff",
    "current",
    "flow_potential",
    "normalized",
}

# leaderboard metric columns -> key in the harness per-task aggregate
METRIC_KEYS = (
    "rel_l2",
    "mae_log10eps",
    "top5_iou",
    "pinch_recall",
    "spearman",
    "corridor_dice",
    "ssim",
    "speedup_median",
    "inference_time_s_median",
    "n",
)
HARNESS_KEY = {"corridor_dice": "corridor_dice_q10"}
AGGREGATED = ("speedup_median", "inference_time_s_median", "n")  # not averaged with ± std

META_REQUIRED = {
    "model": str,
    "task": str,
    "tier": str,
    "split": str,
    "seed": int,
    "params_M": (int, float),
    "train_data": str,
    "train_tiers": list,
    "hardware": str,
    "inference_batch": int,
    "code_url": str,
    "code_commit": str,
    "contact": str,
}

ENTRY_REQUIRED = (
    "submission_id",
    "timestamp",
    "submitter",
    "model",
    "task",
    "tier",
    "split",
    "metrics",
    "metrics_std",
    "params_M",
    "train_tiers",
    "zero_shot",
    "seeds",
    "notes",
)
ENTRY_OPTIONAL = ("t4_target", "hardware", "inference_batch", "code_url", "code_commit", "source")

MODEL_NAMES = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN"}
RUN_RE = re.compile(
    r"^(?P<model>[a-z0-9]+)_(?P<task>T\d[A-Z]?)_(?P<tier>S|M|L|XL|XXL)_s(?P<seed>\d+)$"
)
TAG_RE = re.compile(r"^[^_]+_(S|M|L|XL|XXL)_(test_id|test_ood|ood_region)$")
PUB_TAG_RE = re.compile(r"^published_(S|M|L|XL|XXL)_test_ood_published$")


# ------------------------------------------------------------------------------------------------- small helpers
def _finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _num_or_none(v):
    return float(v) if _finite(v) else None


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def parse_run_name(name: str) -> dict | None:
    """'unet_T1_L_s2' -> {model, task, tier, seed}; suffixed variants ('..._s1_scalenorm') -> None."""
    m = RUN_RE.match(name)
    return {**m.groupdict(), "seed": int(m.group("seed"))} if m else None


def parse_tag(tag: str) -> tuple[str, str] | None:
    """Evaluation group tag -> (tier, split); '<root>_<tier>_<split>' or 'published_<tier>_test_ood_published'."""
    m = TAG_RE.match(tag)
    if m:
        return m.group(1), m.group(2)
    m = PUB_TAG_RE.match(tag)
    if m:
        return m.group(1), "test_ood_published"
    return None


# ------------------------------------------------------------------------------------------------- entry schema
def validate_entry(entry: dict) -> list[str]:
    """Schema errors for one leaderboard entry (docs/submission.md §2); [] when valid."""
    errs: list[str] = []
    if not isinstance(entry, dict):
        return ["entry is not a JSON object"]
    for k in ENTRY_REQUIRED:
        if k not in entry:
            errs.append(f"missing field '{k}'")
    unknown = set(entry) - set(ENTRY_REQUIRED) - set(ENTRY_OPTIONAL)
    if unknown:
        errs.append(f"unknown fields {sorted(unknown)}")
    if errs:
        return errs
    sid = entry["submission_id"]
    if not isinstance(sid, str) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{2,127}$", sid):
        errs.append("submission_id must be 3-128 chars of [A-Za-z0-9._@+-]")
    try:
        dt.datetime.fromisoformat(str(entry["timestamp"]))
    except ValueError:
        errs.append("timestamp must be ISO-8601")
    for k in ("submitter", "model", "notes"):
        if not isinstance(entry[k], str) or (k != "notes" and not entry[k].strip()):
            errs.append(f"'{k}' must be a non-empty string")
    if entry["task"] not in TASKS:
        errs.append(f"task must be one of {TASKS}")
    if entry["tier"] not in TIERS:
        errs.append(f"tier must be one of {TIERS}")
    if entry["split"] not in SPLITS:
        errs.append(f"split must be one of {SPLITS}")
    m = entry["metrics"]
    if not isinstance(m, dict):
        errs.append("metrics must be an object")
    else:
        for k in METRIC_KEYS:
            if k not in m:
                errs.append(f"metrics.{k} missing (use null when not applicable)")
            elif k == "n":
                if not (isinstance(m[k], int) and not isinstance(m[k], bool) and m[k] > 0):
                    errs.append("metrics.n must be a positive integer")
            elif m[k] is not None and not _finite(m[k]):
                errs.append(f"metrics.{k} must be a finite number or null")
        if m.get("rel_l2") is None:
            errs.append("metrics.rel_l2 is required (leaderboard sort key)")
        if set(m) - set(METRIC_KEYS):
            errs.append(f"unknown metrics {sorted(set(m) - set(METRIC_KEYS))}")
    s = entry["metrics_std"]
    if s is not None:
        if not isinstance(s, dict):
            errs.append("metrics_std must be an object or null")
        else:
            for k, v in s.items():
                if k not in METRIC_KEYS or k in AGGREGATED:
                    errs.append(f"metrics_std.{k} is not an averaged metric")
                elif v is not None and not _finite(v):
                    errs.append(f"metrics_std.{k} must be a finite number or null")
    p = entry["params_M"]
    if p is not None and not (_finite(p) and p >= 0):
        errs.append("params_M must be a non-negative number or null")
    tt = entry["train_tiers"]
    if not isinstance(tt, list) or not tt or any(t not in TIERS for t in tt):
        errs.append(f"train_tiers must be a non-empty list of {TIERS}")
    if not isinstance(entry["zero_shot"], bool):
        errs.append("zero_shot must be a boolean")
    elif isinstance(tt, list) and tt and all(t in TIERS for t in tt):
        if entry["zero_shot"] != (entry["tier"] not in tt):
            errs.append(
                "zero_shot must be true exactly when the evaluated tier is not in train_tiers"
            )
    seeds = entry["seeds"]
    if (
        not isinstance(seeds, dict)
        or not isinstance(seeds.get("n"), int)
        or seeds["n"] < 1
        or not isinstance(seeds.get("values"), list)
        or len(seeds["values"]) != seeds["n"]
        or any(not isinstance(v, int) for v in seeds["values"])
    ):
        errs.append("seeds must be {'n': k, 'values': [k integers]}")
    elif seeds["n"] > 1 and s is None:
        errs.append("metrics_std is required when seeds.n > 1")
    elif seeds["n"] == 1 and s is not None:
        errs.append("metrics_std must be null when seeds.n == 1")
    t4t = entry.get("t4_target")
    if t4t is not None and t4t not in T4_TARGETS:
        errs.append(f"t4_target must be one of {T4_TARGETS} or null")
    if entry["task"] == "T4" and t4t is None:
        errs.append("t4_target is required for T4 entries")
    if entry["task"] != "T4" and t4t is not None:
        errs.append("t4_target applies to T4 only")
    ib = entry.get("inference_batch")
    if ib is not None:
        if not isinstance(ib, int) or ib < 1:
            errs.append("inference_batch must be a positive integer")
        elif entry["tier"] in ("XL", "XXL") and ib != 1:
            errs.append("inference_batch must be 1 at XL and XXL (docs/submission.md)")
    return errs


def aggregate_seeds(per_seed: list[dict]) -> tuple[dict, dict | None]:
    """Mean over seeds of every METRIC_KEYS value; sample std (ddof=1, as in the paper tables) when > 1 seed.
    speedup_median / inference_time_s_median are means of the per-seed medians; n is the first seed's n."""
    if not per_seed:
        raise ValueError("no seed results")
    metrics: dict = {}
    std: dict | None = {} if len(per_seed) > 1 else None
    for k in METRIC_KEYS:
        vals = [m.get(k) for m in per_seed]
        if k == "n":
            metrics[k] = vals[0]
            continue
        nums = [v for v in vals if _finite(v)]
        if not nums:
            metrics[k] = None
            if std is not None and k not in AGGREGATED:
                std[k] = None
            continue
        mean = sum(nums) / len(nums)
        metrics[k] = mean
        if std is not None and k not in AGGREGATED:
            std[k] = (
                math.sqrt(sum((v - mean) ** 2 for v in nums) / (len(nums) - 1))
                if len(nums) > 1
                else None
            )
    return metrics, std


def harness_metrics(results: dict, task: str, t4_target: str = "production") -> dict:
    """METRIC_KEYS from a harness results.json (per_task[task][metric] = {mean, median, n}, speedup = {...}).
    `t4_target='block1_reference'`: mean of the per-sample rows the harness scored against the exact block-1 map
    (`t4_target == 'block1_reference'`), n = their count — raises if there are none."""
    agg = results.get("per_task", {}).get(task)
    if not agg:
        raise ValueError(f"results.json has no per_task entry for {task}")
    if t4_target == "block1_reference":
        rows = [
            r
            for r in results.get("per_sample", [])
            if r.get("task") == task and r.get("t4_target") == "block1_reference"
        ]
        if not rows:
            raise ValueError("no per-sample rows scored against the block-1 reference (t4_target)")

        def mean(key):
            v = [r[key] for r in rows if _finite(r.get(key))]
            return sum(v) / len(v) if v else None

        def median(key):
            v = sorted(r[key] for r in rows if _finite(r.get(key)))
            if not v:
                return None
            mid = len(v) // 2
            return v[mid] if len(v) % 2 else 0.5 * (v[mid - 1] + v[mid])

        out = {k: mean(HARNESS_KEY.get(k, k)) for k in METRIC_KEYS if k not in AGGREGATED}
        out["speedup_median"] = median("speedup")
        out["inference_time_s_median"] = median("inference_time_s")
        out["n"] = len(rows)
        return out
    out = {}
    for k in METRIC_KEYS:
        if k in AGGREGATED:
            continue
        v = agg.get(HARNESS_KEY.get(k, k))
        out[k] = _num_or_none(v.get("mean")) if isinstance(v, dict) else _num_or_none(v)
    out["speedup_median"] = _num_or_none((agg.get("speedup") or {}).get("speedup_median"))
    it = agg.get("inference_time_s")
    out["inference_time_s_median"] = (
        _num_or_none(it.get("median")) if isinstance(it, dict) else None
    )
    n = agg.get("rel_l2", {}).get("n") if isinstance(agg.get("rel_l2"), dict) else None
    out["n"] = int(n) if n else int(results.get("n_rows", 0))
    return out


def make_entry(
    results: dict,
    meta: dict,
    seed_results: list[dict] | None = None,
    submitter: str | None = None,
    submission_id: str | None = None,
    t4_target: str | None = None,
    timestamp: str | None = None,
) -> dict:
    """Leaderboard entry from a harness results.json + the submitter's meta.json (+ further seeds' results.json)."""
    missing = [k for k in META_REQUIRED if k not in meta]
    if missing:
        raise ValueError(f"meta.json is missing required fields {missing}")
    task, tier, split = meta["task"], meta["tier"], meta["split"]
    if task == "T4":
        t4_target = t4_target or "production"
    else:
        t4_target = None
    all_results = [results, *(seed_results or [])]
    per_seed = [harness_metrics(r, task, t4_target or "production") for r in all_results]
    metrics, std = aggregate_seeds(per_seed)
    seeds = [
        int((r.get("meta") or {}).get("seed", meta["seed"]) if i else meta["seed"])
        for i, r in enumerate(all_results)
    ]
    ts = timestamp or _now()
    submitter = submitter or meta.get("submitter") or meta["contact"]
    if not submission_id:
        h = hashlib.sha256(
            "|".join([submitter, meta["model"], task, tier, split, ts]).encode()
        ).hexdigest()[:10]
        submission_id = f"sub-{ts[:10].replace('-', '')}-{h}"
    train_tiers = list(meta["train_tiers"])
    entry = {
        "submission_id": submission_id,
        "timestamp": ts,
        "submitter": submitter,
        "model": meta["model"],
        "task": task,
        "tier": tier,
        "split": split,
        "metrics": metrics,
        "metrics_std": std,
        "params_M": float(meta["params_M"]),
        "train_tiers": train_tiers,
        "zero_shot": tier not in train_tiers,
        "seeds": {"n": len(seeds), "values": seeds},
        "notes": str(meta.get("notes", "")),
        "t4_target": t4_target,
        "hardware": meta["hardware"],
        "inference_batch": int(meta["inference_batch"]),
        "code_url": meta["code_url"],
        "code_commit": meta["code_commit"],
        "source": {
            "kind": "submission",
            "train_data": meta["train_data"],
            "contact": meta["contact"],
            "evaluated_at": [r.get("evaluated_at") for r in all_results],
        },
    }
    errs = validate_entry(entry)
    if errs:
        raise ValueError("entry does not validate: " + "; ".join(errs))
    return entry


# ------------------------------------------------------------------------------------------------- leaderboard files
def load_entries(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{i}: {e}") from e
    return out


def append_entries(entries: list[dict], lb_dir: pathlib.Path) -> tuple[int, int]:
    """Validate, skip ids already present, append to results.jsonl, re-render README.md. Returns (added, skipped)."""
    lb_dir.mkdir(parents=True, exist_ok=True)
    jsonl = lb_dir / "results.jsonl"
    existing = load_entries(jsonl)
    have = {e["submission_id"] for e in existing}
    bad = {}
    for e in entries:
        errs = validate_entry(e)
        if errs:
            bad[e.get("submission_id", "?")] = errs
    if bad:
        raise ValueError("invalid entries: " + json.dumps(bad, indent=1))
    added, skipped = [], 0
    for e in entries:
        if e["submission_id"] in have:
            skipped += 1
            continue
        have.add(e["submission_id"])
        added.append(e)
    if added:
        with open(jsonl, "a") as f:
            for e in added:
                f.write(json.dumps(e, sort_keys=False) + "\n")
    (lb_dir / "README.md").write_text(render_readme(existing + added))
    return len(added), skipped


def _fmt(v, std=None, digits=3) -> str:
    if not _finite(v):
        return "–"
    s = f"{v:.{digits}f}" if (digits == 0 or abs(v) < 1e4) else f"{v:.3g}"
    if _finite(std):
        s += f" ± {std:.{digits}f}"
    return s


SPLIT_ORDER = {s: i for i, s in enumerate(SPLITS)}
TIER_ORDER = {t: i for i, t in enumerate(TIERS)}
TASK_ORDER = {t: i for i, t in enumerate(TASKS)}


def render_readme(entries: list[dict], generated: str | None = None) -> str:
    """One table per task × tier × split (× T4 target), rows sorted by rel_l2 ascending."""
    groups: dict[tuple, list[dict]] = {}
    for e in entries:
        groups.setdefault((e["task"], e["tier"], e["split"], e.get("t4_target")), []).append(e)
    lines = [
        "# AmpScape leaderboard",
        "",
        f"{len(entries)} entries, rendered {generated or _now()} by `scripts/submit_results.py` from `results.jsonl` "
        "(append-only; schema and submission procedure: `docs/submission.md` in the code repository).",
        "",
        "Rows are sorted by `rel_l2` (lower is better) within each task × tier × split; `± std` over seeds when a model "
        "was run with more than one seed; speed-up = solver wall time / inference time per configuration (median); "
        "inference time is the median per configuration in seconds. Zero-shot rows were trained at the listed tiers "
        "only and evaluated at a held-out scale. T4 tables at M and L name the target: `production` = the "
        "block-centred Omniscape target, `block1_reference` = the exact block-1 map on the reference subset "
        "(`aux/t4_bs1_reference/`).",
        "",
    ]
    for key in sorted(
        groups,
        key=lambda k: (
            TASK_ORDER.get(k[0], 99),
            TIER_ORDER.get(k[1], 99),
            SPLIT_ORDER.get(k[2], 99),
            str(k[3]),
        ),
    ):
        task, tier, split, t4t = key
        title = f"## {task} · {tier} · {split}" + (f" · target {t4t}" if t4t else "")
        lines += [
            title,
            "",
            "| # | model | submitter | zero-shot | train tiers | params (M) | seeds | rel_l2 | mae_log10eps | top5_iou "
            "| pinch_recall | spearman | corridor_dice | ssim | speed-up (median) | inference s (median) | n | date | id |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        rows = sorted(groups[key], key=lambda e: (e["metrics"]["rel_l2"], e["submission_id"]))
        for i, e in enumerate(rows, 1):
            m, s = e["metrics"], e.get("metrics_std") or {}
            lines.append(
                f"| {i} | {e['model']} | {e['submitter']} | {'yes' if e['zero_shot'] else 'no'} | "
                f"{'+'.join(e['train_tiers'])} | {_fmt(e['params_M'], digits=2)} | {e['seeds']['n']} | "
                + " | ".join(
                    _fmt(m.get(k), s.get(k))
                    for k in (
                        "rel_l2",
                        "mae_log10eps",
                        "top5_iou",
                        "pinch_recall",
                        "spearman",
                        "corridor_dice",
                        "ssim",
                    )
                )
                + f" | {_fmt(m.get('speedup_median'), digits=0)} | {_fmt(m.get('inference_time_s_median'), digits=4)} "
                f"| {m['n']} | {str(e['timestamp'])[:10]} | `{e['submission_id']}` |"
            )
        lines.append("")
    return "\n".join(lines)


def push_leaderboard(lb_dir: pathlib.Path) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "push_aux.py"),
        "--src",
        str(lb_dir),
        "--dest",
        HUB_DEST,
        "--include",
        "results.jsonl",
        "README.md",
        "--repo",
        REPO,
    ]
    print("push:", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=False).returncode


# ------------------------------------------------------------------------------------------------- validate
def check_meta(meta: dict, tier: str, split: str) -> list[str]:
    errs = []
    for k, typ in META_REQUIRED.items():
        if k not in meta:
            errs.append(f"meta.json: missing '{k}'")
        elif not isinstance(meta[k], typ) or isinstance(meta[k], bool):
            errs.append(f"meta.json: '{k}' must be {typ}")
    if errs:
        return errs
    if meta["task"] not in TASKS:
        errs.append(f"meta.json: task must be one of {TASKS}")
    if meta["tier"] != tier:
        errs.append(f"meta.json: tier {meta['tier']!r} != --tier {tier!r}")
    if meta["split"] != split:
        errs.append(f"meta.json: split {meta['split']!r} != --split {split!r}")
    if split not in SPLITS:
        errs.append(f"split must be one of {SPLITS}")
    if any(t not in TIERS for t in meta["train_tiers"]) or not meta["train_tiers"]:
        errs.append(f"meta.json: train_tiers must be a non-empty list of {TIERS}")
    if tier in ("XL", "XXL") and meta["inference_batch"] != 1:
        errs.append("meta.json: inference_batch must be 1 at XL and XXL")
    if meta["inference_batch"] < 1:
        errs.append("meta.json: inference_batch must be >= 1")
    for k in ("model", "train_data", "hardware", "code_url", "code_commit", "contact"):
        if not meta[k].strip():
            errs.append(f"meta.json: '{k}' is empty")
    return errs


def check_predictions(
    pred_dir: pathlib.Path, root: pathlib.Path, tier: str, split: str, task: str
) -> dict:
    """Coverage against the index (all qc_pass rows of the split's task kind, no extras), datasets, dtypes,
    shapes, finiteness and the inference_time_s attribute. Returns {'errors': [...], 'n_expected': .., ...}."""
    import h5py
    import numpy as np

    from ampscape.data.dataset import _load_index

    idx = _load_index(root, tier)
    kind = TASK_KIND[task]
    sel = idx[(idx.split == split) & idx.qc_pass & (idx.kind == kind)]
    expected = {(r.sample_id, r.config): r for r in sel.itertuples(index=False)}
    exp_sids = {s for s, _ in expected}
    errs: list[str] = []
    n_checked = 0
    with h5py.File(pred_dir / "predictions.h5", "r") as fp:
        have = set(fp.keys())
        missing = sorted(exp_sids - have)
        extra = sorted(have - exp_sids)
        errs += [f"missing sample {s}" for s in missing[:20]]
        if len(missing) > 20:
            errs.append(f"... {len(missing)} samples missing in total")
        errs += [
            f"extra sample {s} (not a qc_pass {kind} row of split {split})" for s in extra[:20]
        ]
        if len(extra) > 20:
            errs.append(f"... {len(extra)} extra samples in total")
        for (sid, cfg), row in sorted(expected.items()):
            if sid not in fp:
                continue
            if cfg not in fp[sid]:
                errs.append(f"{sid}: missing config group {cfg}")
                continue
            g = fp[sid][cfg]
            H, W = int(row.H), int(row.W)  # per-row raster size from the index (tier size: TIER_PX)
            for name in TASK_DATASETS[task]:
                if name not in g:
                    errs.append(f"{sid}/{cfg}: missing dataset {name}")
            for name in g:
                if name not in KNOWN_DATASETS:
                    errs.append(f"{sid}/{cfg}: unknown dataset {name}")
                    continue
                d = g[name]
                if name == "reff":
                    K = int(row.K)
                    if d.shape != (K, K):
                        errs.append(f"{sid}/{cfg}/reff: shape {d.shape} != ({K}, {K})")
                    if d.dtype != np.float64:
                        errs.append(f"{sid}/{cfg}/reff: dtype {d.dtype} != float64")
                else:
                    ok = d.shape == (H, W) or (
                        name in ("voltage", "pairwise_current")
                        and d.ndim == 3
                        and d.shape[1:] == (H, W)
                    )
                    if not ok:
                        errs.append(f"{sid}/{cfg}/{name}: shape {d.shape} != ({H}, {W})")
                    if d.dtype != np.float32:
                        errs.append(f"{sid}/{cfg}/{name}: dtype {d.dtype} != float32")
                if not np.isfinite(d[...]).all():
                    errs.append(f"{sid}/{cfg}/{name}: contains NaN or Inf")
            t = g.attrs.get("inference_time_s")
            if t is None or not np.isfinite(float(t)) or float(t) <= 0:
                errs.append(f"{sid}/{cfg}: attr inference_time_s missing, non-finite or <= 0")
            n_checked += 1
            if len(errs) > 200:
                errs.append("... more than 200 problems, stopping")
                break
    return {
        "errors": errs,
        "n_expected": len(expected),
        "n_samples_expected": len(exp_sids),
        "n_checked": n_checked,
        "n_missing": len(missing),
        "n_extra": len(extra),
    }


def cmd_validate(a) -> int:
    pred_dir = pathlib.Path(a.predictions)
    meta_p = pred_dir / "meta.json"
    if not meta_p.exists():
        print(f"ERROR: {meta_p} missing")
        return 1
    if not (pred_dir / "predictions.h5").exists():
        print(f"ERROR: {pred_dir / 'predictions.h5'} missing")
        return 1
    meta = json.loads(meta_p.read_text())
    errs = check_meta(meta, a.tier, a.split)
    if errs:
        print("\n".join(errs))
        return 1
    task = meta["task"]
    print(
        f"meta.json ok: {meta['model']} {task} {a.tier} {a.split} seed {meta['seed']}", flush=True
    )
    rep = check_predictions(pred_dir, pathlib.Path(a.root), a.tier, a.split, task)
    print(
        f"index: {rep['n_expected']} (sample, config) rows / {rep['n_samples_expected']} samples expected; "
        f"{rep['n_checked']} checked, {rep['n_missing']} missing, {rep['n_extra']} extra, {len(rep['errors'])} problems",
        flush=True,
    )
    if rep["errors"]:
        print("\n".join(rep["errors"]))
        return 1
    if a.no_eval:
        print("structure ok (--no-eval: metrics not computed)")
        return 0
    from ampscape.eval.harness import PRIMARY, evaluate

    r = evaluate(
        pred_dir,
        a.split,
        a.root,
        a.tier,
        None,
        pred_dir,
        t4_reference=a.t4_reference,
        workers=a.workers,
    )
    print(f"{r['n_rows']} rows evaluated -> {pred_dir / 'results.json'}, results.md")
    for t, agg in r["per_task"].items():
        print(f"  {t}:")
        for k in PRIMARY:
            if k in agg:
                v = agg[k]
                print(f"    {k:<24} mean {v['mean']:.4g}  median {v['median']:.4g}  n {v['n']}")
        sp = agg.get("speedup") or {}
        if _finite(sp.get("speedup_median")):
            print(f"    {'speedup_median':<24} {sp['speedup_median']:.4g}")
    if task not in r["per_task"]:
        print(f"ERROR: no {task} rows were evaluated")
        return 1
    return 0


# ------------------------------------------------------------------------------------------------- make-entry / append
def cmd_make_entry(a) -> int:
    results = json.loads(pathlib.Path(a.results).read_text())
    meta = json.loads(pathlib.Path(a.meta).read_text())
    seeds = [json.loads(pathlib.Path(p).read_text()) for p in (a.seeds or [])]
    entry = make_entry(
        results,
        meta,
        seeds,
        submitter=a.submitter,
        submission_id=a.id,
        t4_target=a.t4_target,
    )
    pathlib.Path(a.out).write_text(json.dumps(entry, indent=1) + "\n")
    print(
        f"{a.out}: {entry['submission_id']} {entry['model']} {entry['task']} {entry['tier']} {entry['split']}"
    )
    print(json.dumps(entry["metrics"], indent=1))
    return 0


def cmd_append(a) -> int:
    entries = []
    for p in a.entry:
        e = json.loads(pathlib.Path(p).read_text())
        entries += e if isinstance(e, list) else [e]
    lb = pathlib.Path(a.leaderboard)
    added, skipped = append_entries(entries, lb)
    print(f"{lb}: {added} appended, {skipped} already present -> results.jsonl, README.md")
    return push_leaderboard(lb) if a.push else 0


# ------------------------------------------------------------------------------------------------- seed-baselines
def _load_json(p: pathlib.Path) -> dict | None:
    return json.loads(p.read_text()) if p.exists() else None


def summary_metrics(group: dict, task: str, per_split: dict | None) -> dict:
    """METRIC_KEYS from one eval group of a run's results.json / results_transfer.json (`eval[tag]` = per-task
    means + speedup + n_rows); the median inference time comes from the per-split harness file when present."""
    m = group.get(task) or {}
    out = {
        k: _num_or_none(m.get(HARNESS_KEY.get(k, k))) for k in METRIC_KEYS if k not in AGGREGATED
    }
    out["speedup_median"] = _num_or_none((m.get("speedup") or {}).get("speedup_median"))
    out["inference_time_s_median"] = None
    if per_split:
        it = per_split.get("per_task", {}).get(task, {}).get("inference_time_s")
        if isinstance(it, dict):
            out["inference_time_s_median"] = _num_or_none(it.get("median"))
    out["n"] = int(group.get("n_rows") or 0)
    return out


def _baseline_entry(
    sid: str,
    model: str,
    task: str,
    tier: str,
    split: str,
    per_seed: list[dict],
    seeds: list[int],
    cfgs: list[dict],
    train_tier: str,
    inference_batch: int,
    runs: list[str],
    notes: str,
    t4_target: str | None,
    timestamp: str,
) -> dict:
    metrics, std = aggregate_seeds(per_seed)
    params = [c.get("n_params") for c in cfgs if _finite(c.get("n_params"))]
    devices = sorted({c.get("device", "") for c in cfgs if c.get("device")})
    return {
        "submission_id": sid,
        "timestamp": timestamp,
        "submitter": "AmpScape maintainers (official baseline)",
        "model": model,
        "task": task,
        "tier": tier,
        "split": split,
        "metrics": metrics,
        "metrics_std": std,
        "params_M": (sum(params) / len(params) / 1e6) if params else None,
        "train_tiers": [train_tier],
        "zero_shot": tier != train_tier,
        "seeds": {"n": len(seeds), "values": seeds},
        "notes": notes,
        "t4_target": t4_target,
        "hardware": ", ".join(devices) or "unknown",
        "inference_batch": inference_batch,
        "code_url": "https://github.com/xyrro/EcoFlowBench",
        "code_commit": ",".join(sorted({c.get("git", "") for c in cfgs if c.get("git")})),
        "source": {"kind": "official_baseline", "runs": runs},
    }


def seed_baselines(
    runs_dir: pathlib.Path, timestamp: str | None = None
) -> tuple[list[dict], list[str]]:
    """Entries for every official run group `<model>_<task>_<tier>_s<seed>` under runs_dir with results.json:
    in-tier rows (zero_shot False), scale-transfer rows from results_transfer.json (XL/XXL, zero_shot True,
    model '<model> (trained at <tier>)'), and T4 block-1 reference rows from eval_t4_reference/results.json when
    that file holds rows scored against the reference. Returns (entries, warnings)."""
    ts = timestamp or _now()
    groups: dict[tuple[str, str, str], list[tuple[int, pathlib.Path]]] = {}
    warnings: list[str] = []
    for d in sorted(runs_dir.iterdir()):
        if not d.is_dir():
            continue
        p = parse_run_name(d.name)
        tuned = False
        if p is None and d.name.endswith(
            "_t2"
        ):  # tier-tuned official configuration (item 2, 2026-10-05)
            p = parse_run_name(d.name[:-3])
            tuned = p is not None
        if p is None:
            if re.match(r"^[a-z0-9]+_T\d[A-Z]?_(S|M|L|XL|XXL)_s\d+_", d.name):
                warnings.append(f"skipped variant run {d.name}")
            continue
        if not (d / "results.json").exists():
            warnings.append(f"skipped {d.name}: no results.json")
            continue
        groups.setdefault((p["model"], p["task"], p["tier"]), []).append((p["seed"], d, tuned))
    entries: list[dict] = []
    for (model, task, tier), seed_runs3 in sorted(groups.items()):
        # one run per seed: the tier-tuned run replaces the pre-tuning one when both exist
        by_seed: dict[int, tuple[int, pathlib.Path]] = {}
        for sd, d, _tuned in sorted(seed_runs3, key=lambda x: (x[0], x[2])):
            by_seed[sd] = (sd, d)
        seed_runs = sorted(by_seed.values())
        name = MODEL_NAMES.get(model, model)
        results = [(s, d, json.loads((d / "results.json").read_text())) for s, d in seed_runs]
        cfgs = [r["config"] for _, _, r in results]
        if any(c.get("task") != task or c.get("tier") != tier for c in cfgs):
            warnings.append(
                f"{model}_{task}_{tier}: config task/tier disagree with the run name; skipped"
            )
            continue
        gpu_h = [r["history"][-1].get("cum_gpu_h") for _, _, r in results if r.get("history")]
        epochs = [len(r.get("history") or []) for _, _, r in results]
        variant = sorted({c.get("variant", "") for c in cfgs})
        extra = sorted({"+".join(c.get("extra_channels") or []) for c in cfgs})
        base_note = (
            f"official Phase 10-full baseline (scripts/train.py); variant {'/'.join(variant)}"
            + (f", extra channels {'/'.join(x for x in extra if x)}" if any(extra) else "")
            + f"; epochs {'/'.join(map(str, epochs))}"
            + (
                f"; train GPU-h {sum(gpu_h) / len(gpu_h):.2f} mean"
                if gpu_h and all(_finite(g) for g in gpu_h)
                else ""
            )
            + "; metrics are the harness means per seed, averaged over seeds (± sample std)"
        )
        t4_target = "production" if task == "T4" else None
        # in-tier rows
        tags = sorted({t for _, _, r in results for t in r.get("eval", {})})
        for tag in tags:
            parsed = parse_tag(tag)
            if parsed is None:
                warnings.append(f"{model}_{task}_{tier}: unrecognised eval tag {tag}; skipped")
                continue
            etier, split = parsed
            if etier != tier:
                warnings.append(
                    f"{model}_{task}_{tier}: eval tag {tag} is at another tier; skipped"
                )
                continue
            per_seed, seeds, runs, batches = [], [], [], set()
            for s, d, r in results:
                g = r.get("eval", {}).get(tag)
                if not g or not g.get(task):
                    continue
                per_split = _load_json(d / "predictions" / tag / f"eval_{split}" / "results.json")
                per_seed.append(summary_metrics(g, task, per_split))
                seeds.append(s)
                runs.append(d.name)
                batches.add(int(r["config"].get("batch", 0)))
            if not per_seed:
                continue
            ns = {m["n"] for m in per_seed}
            if len(ns) > 1:
                warnings.append(
                    f"{model}_{task}_{tier} {split}: n differs across seeds {sorted(ns)}; first kept"
                )
            entries.append(
                _baseline_entry(
                    f"baseline-{model}_{task}_{tier}-{split}",
                    name,
                    task,
                    tier,
                    split,
                    per_seed,
                    seeds,
                    [r["config"] for s, _, r in results if s in seeds],
                    tier,
                    1 if tier in ("XL", "XXL") else (max(batches) if batches else 1),
                    runs,
                    base_note,
                    t4_target,
                    ts,
                )
            )
        # scale-transfer rows (results_transfer.json: model trained at `tier`, evaluated at XL / XXL, batch 1)
        xfers = [(s, d, _load_json(d / "results_transfer.json")) for s, d in seed_runs]
        xtags = sorted({t for _, _, rt in xfers if rt for t in rt.get("eval", {})})
        for tag in xtags:
            parsed = parse_tag(tag)
            if parsed is None:
                warnings.append(f"{model}_{task}_{tier}: unrecognised transfer tag {tag}; skipped")
                continue
            etier, split = parsed
            if etier == tier:
                warnings.append(f"{model}_{task}_{tier}: transfer tag {tag} is in-tier; skipped")
                continue
            per_seed, seeds, runs = [], [], []
            for s, d, rt in xfers:
                g = (rt or {}).get("eval", {}).get(tag)
                if not g or not g.get(task):
                    continue
                per_split = _load_json(d / "eval_transfer" / tag / "results.json")
                per_seed.append(summary_metrics(g, task, per_split))
                seeds.append(s)
                runs.append(d.name)
            if not per_seed:
                continue
            ns = {m["n"] for m in per_seed}
            if len(ns) > 1:
                warnings.append(
                    f"{model}_{task}_{tier}->{etier} {split}: n differs across seeds {sorted(ns)}; first kept"
                )
            entries.append(
                _baseline_entry(
                    f"baseline-{model}_{task}_{tier}-xfer-{etier}-{split}",
                    f"{name} (trained at {tier})",
                    task,
                    etier,
                    split,
                    per_seed,
                    seeds,
                    [r["config"] for s, _, r in results if s in seeds],
                    tier,
                    1,
                    runs,
                    f"zero-shot scale transfer (scripts/transfer_eval.py) of the {tier}-trained run to {etier}, batch 1; "
                    + base_note,
                    "production" if task == "T4" else None,
                    ts,
                )
            )
        # T4 at M / L against the exact block-1 reference (eval_t4_reference/results.json, --t4-reference)
        if task == "T4" and tier in ("M", "L"):
            per_seed, seeds, runs, splits = [], [], [], set()
            for s, d, _ in results:
                rr = _load_json(d / "eval_t4_reference" / "results.json")
                if not rr:
                    continue
                try:
                    per_seed.append(harness_metrics(rr, task, "block1_reference"))
                except ValueError:
                    warnings.append(
                        f"{d.name}/eval_t4_reference/results.json holds no rows scored against the block-1 reference "
                        "(no per-sample t4_target); block-1 row not seeded"
                    )
                    continue
                seeds.append(s)
                runs.append(d.name)
                splits.update(rr.get("splits", []))
            if per_seed and len(splits) == 1:
                split = splits.pop()
                entries.append(
                    _baseline_entry(
                        f"baseline-{model}_{task}_{tier}-{split}-block1",
                        name,
                        task,
                        tier,
                        split,
                        per_seed,
                        seeds,
                        [r["config"] for s, _, r in results if s in seeds],
                        tier,
                        max(int(c.get("batch", 1)) for c in cfgs),
                        runs,
                        "T4 scored against the exact block-1 Omniscape map on the reference subset "
                        "(aux/t4_bs1_reference); " + base_note,
                        "block1_reference",
                        ts,
                    )
                )
    return entries, warnings


def cmd_seed_baselines(a) -> int:
    entries, warnings = seed_baselines(pathlib.Path(a.runs))
    for w in warnings:
        print("WARNING:", w)
    bad = {e["submission_id"]: validate_entry(e) for e in entries if validate_entry(e)}
    if bad:
        print("entries that do not fit the schema:", json.dumps(bad, indent=1))
        return 1
    lb = pathlib.Path(a.leaderboard)
    added, skipped = append_entries(entries, lb)
    kinds = {}
    for e in entries:
        kinds[e["source"]["kind"] + ("/zero-shot" if e["zero_shot"] else "")] = (
            kinds.get(e["source"]["kind"] + ("/zero-shot" if e["zero_shot"] else ""), 0) + 1
        )
    print(
        f"{len(entries)} baseline entries built {kinds}; {added} appended, {skipped} already present -> {lb}"
    )
    return push_leaderboard(lb) if a.push else 0


# ------------------------------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="check a predictions directory and run the harness")
    v.add_argument("--predictions", required=True, help="directory with predictions.h5 + meta.json")
    v.add_argument(
        "--root", required=True, help="data root (HF layout with index/<tier>.parquet, or a build)"
    )
    v.add_argument("--tier", required=True, choices=TIERS)
    v.add_argument("--split", required=True, choices=SPLITS)
    v.add_argument("--workers", type=int, default=1, help="harness metric processes")
    v.add_argument(
        "--t4-reference", default=None, help="aux block-1 reference build for T4 at M / L"
    )
    v.add_argument("--no-eval", action="store_true", help="structural checks only")
    v.set_defaults(fn=cmd_validate)

    m = sub.add_parser("make-entry", help="leaderboard entry from harness results.json + meta.json")
    m.add_argument("--results", required=True)
    m.add_argument("--meta", required=True)
    m.add_argument("--seeds", nargs="*", default=None, help="results.json of further seeds")
    m.add_argument("--submitter", default=None, help="defaults to meta.submitter or meta.contact")
    m.add_argument("--id", default=None, help="submission id (default: generated)")
    m.add_argument("--t4-target", choices=T4_TARGETS, default=None)
    m.add_argument("--out", required=True)
    m.set_defaults(fn=cmd_make_entry)

    p = sub.add_parser("append", help="validate entries and append them to the local leaderboard")
    p.add_argument("--entry", nargs="+", required=True)
    p.add_argument("--leaderboard", default=str(LEADERBOARD_DIR))
    p.add_argument(
        "--push", action="store_true", help="upload via scripts/push_aux.py (login node)"
    )
    p.set_defaults(fn=cmd_append)

    s = sub.add_parser("seed-baselines", help="entries for the official runs under --runs")
    s.add_argument("--runs", default="runs/full")
    s.add_argument("--leaderboard", default=str(LEADERBOARD_DIR))
    s.add_argument("--push", action="store_true")
    s.set_defaults(fn=cmd_seed_baselines)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
