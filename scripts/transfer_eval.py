#!/usr/bin/env python
"""Scale-transfer evaluation: a model trained at one tier (S/M/L) is evaluated at a held-out tier (XL, XXL).

The card defines XL and XXL as held-out-scale tiers for models trained at ≤ L (their v1.0 splits hold 228 / 0 train
landscapes), so the XL/XXL rows of the baselines table come from this script, not from training at XL.

  python scripts/transfer_eval.py --run runs/full/unet_T1_L_s1 --tier XL --splits test_id,test_ood,ood_region

Per split: predictions at batch 1 (predictions/<root>_<tier>_<split>/predictions.h5, same format as train.py), then
the harness metrics with --workers processes (eval_transfer/<tag>/results.json), summarised into
<run>/results_transfer.json (eval[tag] = per-task means, like results.json). Resumable: a split whose predictions and
metrics exist is skipped, so a job that hits the walltime continues in the next leg. Inputs are normalised with the
statistics of the training tier (config.json), as in training.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

import torch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from train import Items, collate, evaluate_group, predict  # noqa: E402

from ampscape.data.dataset import AmpScapeDataset, load_norm_stats  # noqa: E402
from ampscape.models import build_model  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--tier", required=True, help="evaluation tier (XL, XXL)")
    ap.add_argument("--splits", default="test_id,test_ood,ood_region")
    ap.add_argument("--root", default="data/hfcache")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "1")))
    ap.add_argument("--loader-workers", type=int, default=2)
    a = ap.parse_args()
    run = pathlib.Path(a.run)
    cfg = json.loads((run / "config.json").read_text())
    name, task = cfg["model"], cfg["task"]
    extra = tuple(cfg.get("extra_channels", []))
    multiscale = bool(cfg["model_config"].get("multiscale", False))
    graph = name == "gnn"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp = name != "fno"
    stats = load_norm_stats(cfg.get("root", a.root), cfg["tier"]) or load_norm_stats(
        a.root, cfg["tier"]
    )
    if stats is None:
        raise SystemExit(f"no normalisation statistics for the training tier {cfg['tier']}")
    model = build_model(name, cfg["input_channels"], **cfg["model_config"])
    model.load_state_dict(torch.load(run / "best.pt", map_location="cpu")["model"])
    model.to(device).eval()
    out_path = run / "results_transfer.json"
    summary = (
        json.loads(out_path.read_text())
        if out_path.exists()
        else {
            "source_run": run.name,
            "trained_tier": cfg["tier"],
            "model": name,
            "task": task,
            "eval": {},
        }
    )
    for split in [s.strip() for s in a.splits.split(",") if s.strip()]:
        tag = f"{pathlib.Path(a.root).name}_{a.tier}_{split}"
        pdir = run / "predictions" / tag
        edir = run / "eval_transfer" / tag
        if (edir / "results.json").exists() and tag in summary["eval"]:
            print(f"{tag}: done already", flush=True)
            continue
        ds = AmpScapeDataset(task, split, a.tier, a.root)
        if len(ds) == 0:
            print(f"{tag}: no samples", flush=True)
            continue
        pdir.mkdir(parents=True, exist_ok=True)
        if not (pdir / "predictions.h5").exists() or not (pdir / "meta.json").exists():
            dl = torch.utils.data.DataLoader(
                Items(ds, task, stats, graph, extra, multiscale),
                batch_size=1,
                shuffle=False,
                num_workers=a.loader_workers,
                collate_fn=collate,
            )
            t0 = dt.datetime.now(dt.UTC)
            n = predict(model, name, dl, device, task, pdir / "predictions.h5", amp)
            (pdir / "meta.json").write_text(
                json.dumps(
                    {
                        "model": f"{name}-{cfg.get('variant', 'base')}{'+' + '+'.join(extra) if extra else ''}_{task}_{cfg['tier']}→{a.tier}",
                        "task": task,
                        "tier": a.tier,
                        "split": split,
                        "seed": cfg.get("seed"),
                        "notes": f"scale transfer: trained at {cfg['tier']} (run {run.name}), evaluated at {a.tier}, batch 1",
                        "train_root": cfg.get("root", a.root),
                        "source_run": run.name,
                    },
                    indent=1,
                )
            )
            print(
                f"{tag}: {n} predictions in {(dt.datetime.now(dt.UTC) - t0).total_seconds() / 60:.1f} min",
                flush=True,
            )
        t0 = dt.datetime.now(dt.UTC)
        res = evaluate_group(pdir, [split], a.root, a.tier)
        # evaluate_group writes into pdir/eval_<split>; keep a copy under eval_transfer/<tag> (the offloader ships it)
        src = pdir / f"eval_{split}"
        edir.mkdir(parents=True, exist_ok=True)
        for f in src.glob("results.*"):
            (edir / f.name).write_bytes(f.read_bytes())
        summary["eval"][tag] = res
        summary["updated_at"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
        out_path.write_text(json.dumps(summary, indent=1, default=float))
        print(
            f"{tag}: metrics in {(dt.datetime.now(dt.UTC) - t0).total_seconds() / 60:.1f} min "
            f"({a.workers} workers): { ({t: round(d.get('rel_l2', float('nan')), 4) for t, d in res.items() if isinstance(d, dict)}) }",
            flush=True,
        )
    print("transfer evaluation complete", flush=True)


if __name__ == "__main__":
    main()
