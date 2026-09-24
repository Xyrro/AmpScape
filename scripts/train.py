#!/usr/bin/env python
"""Train one learned baseline on one task and evaluate it through the harness (brief §12, Phase 10).

  python scripts/train.py --model unet --task T1 --tier S --root data/dev/S --out runs/dev/unet_T1 \
      --epochs 30 --time-budget-min 60 --eval-splits test_id,test_ood,ood_region --published-root data/builds/published

Shared by every model: inputs from ampscape.models.common.make_inputs (standardised log-resistance with train-only
stats, NoData mask, task source channels), targets log10(C + ε·max C), masked MSE, AdamW + cosine schedule, early
stopping on the validation loss, fixed seed. Writes: config.json, log.csv (per epoch: losses, time, GPU-hours),
best.pt, predictions/<group>/predictions.h5 + eval results (results.json / results.md), results.json (summary).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pathlib
import subprocess
import sys
import time

import h5py
import numpy as np
import torch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ampscape.data.dataset import AmpScapeDataset, compute_norm_stats, load_norm_stats  # noqa: E402
from ampscape.models import MODEL_CONFIGS, MODEL_VARIANTS, OFFICIAL, build_model  # noqa: E402
from ampscape.models.common import (  # noqa: E402
    TASK_CHANNELS,
    TASK_TARGET,
    coarse_graph,
    grid_graph,
    inverse_target,
    make_inputs,
    make_target,
    masked_mse,
    n_channels,
)

DEFAULT_LR = {"unet": 1e-3, "fno": 1e-3, "vit": 3e-4, "gnn": 1e-3}


class Items(torch.utils.data.Dataset):
    def __init__(
        self,
        ds: AmpScapeDataset,
        task: str,
        stats: dict,
        graph: bool,
        extra: tuple[str, ...] = (),
        multiscale: bool = False,
    ):
        self.ds, self.task, self.stats, self.graph, self.extra, self.multiscale = (
            ds,
            task,
            stats,
            graph,
            extra,
            multiscale,
        )

    def __len__(self):
        return len(self.ds)

    def __getitem__(self, i):
        d = self.ds[i]
        x = make_inputs(d, self.task, self.stats, self.extra)
        y, m = make_target(d, self.task)
        out = {"x": x, "y": y, "mask": m, "sample_id": d["sample_id"], "config": d["config"]}
        if self.graph:
            idx, ei, w = grid_graph(d["resistance"][0], d["nodata"][0] > 0)
            out.update({"node_index": idx, "edge_index": ei, "edge_weight": w})
            if self.multiscale:
                idx_c, ei_c, w_c, f2c = coarse_graph(d["resistance"][0], d["nodata"][0] > 0)
                out.update(
                    {
                        "coarse_edge_index": ei_c,
                        "coarse_edge_weight": w_c,
                        "fine_to_coarse": f2c,
                        "n_coarse": int((idx_c >= 0).sum()),
                    }
                )
        return out


def collate(batch):
    out = {k: torch.from_numpy(np.stack([b[k] for b in batch])) for k in ("x", "y", "mask")}
    out["sample_id"] = [b["sample_id"] for b in batch]
    out["config"] = [b["config"] for b in batch]
    if "node_index" in batch[0]:
        idxs, eis, ws, off = [], [], [], 0
        for b in batch:
            idx = b["node_index"].copy()
            n = int((idx >= 0).sum())
            idx[idx >= 0] += off
            idxs.append(idx)
            eis.append(b["edge_index"] + off)
            ws.append(b["edge_weight"])
            off += n
        out["node_index"] = torch.from_numpy(np.stack(idxs))
        out["edge_index"] = torch.from_numpy(np.concatenate(eis, axis=1))
        out["edge_weight"] = torch.from_numpy(np.concatenate(ws))
        if "coarse_edge_index" in batch[0]:
            ceis, cws, f2cs, offc = [], [], [], 0
            for b in batch:
                ceis.append(b["coarse_edge_index"] + offc)
                cws.append(b["coarse_edge_weight"])
                f2c = b["fine_to_coarse"].copy()
                f2c[f2c >= 0] += offc
                f2cs.append(f2c)
                offc += b["n_coarse"]
            out["coarse_edge_index"] = torch.from_numpy(np.concatenate(ceis, axis=1))
            out["coarse_edge_weight"] = torch.from_numpy(np.concatenate(cws))
            out["fine_to_coarse"] = torch.from_numpy(np.concatenate(f2cs))
            out["n_coarse"] = offc
    return out


def forward(model, name, batch, device):
    x = batch["x"].to(device, non_blocking=True)
    if name == "gnn":
        if "coarse_edge_index" in batch:
            return model(
                x,
                batch["node_index"].to(device),
                batch["edge_index"].to(device),
                batch["edge_weight"].to(device),
                batch["coarse_edge_index"].to(device),
                batch["coarse_edge_weight"].to(device),
                batch["fine_to_coarse"].to(device),
                batch["n_coarse"],
            )
        return model(
            x,
            batch["node_index"].to(device),
            batch["edge_index"].to(device),
            batch["edge_weight"].to(device),
        )
    return model(x)


def run_epoch(model, name, loader, device, opt=None, sched=None, amp=True, clip=1.0):
    train = opt is not None
    model.train(train)
    tot, n = 0.0, 0
    for batch in loader:
        y, m = batch["y"].to(device), batch["mask"].to(device)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=amp and device.type == "cuda"):
            pred = forward(model, name, batch, device)
        loss = masked_mse(pred.float(), y, m)
        if train:
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
            opt.step()
            if sched is not None:
                sched.step()
        tot += float(loss.detach()) * y.shape[0]
        n += y.shape[0]
    return tot / max(n, 1)


@torch.no_grad()
def predict(model, name, loader, device, task, out_h5, amp=True):
    """Write predictions.h5 in the documented format with per-sample inference time (GPU-synchronised)."""
    model.eval()
    key = TASK_TARGET[task]
    n = 0
    with h5py.File(out_h5, "w") as f:
        for batch in loader:
            if device.type == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            with torch.autocast(
                "cuda", dtype=torch.bfloat16, enabled=amp and device.type == "cuda"
            ):
                pred = forward(model, name, batch, device).float()
            if device.type == "cuda":
                torch.cuda.synchronize()
            dt = (time.perf_counter() - t0) / pred.shape[0]
            pred = pred.cpu().numpy()
            for i, (sid, cfg) in enumerate(zip(batch["sample_id"], batch["config"], strict=True)):
                c = inverse_target(pred[i, 0])
                c[batch["mask"][i, 0].numpy() == 0] = np.where(
                    batch["x"][i, 1].numpy() > 0, np.nan, c
                )[batch["mask"][i, 0].numpy() == 0]
                g = f.require_group(sid).require_group(cfg)
                g.create_dataset(
                    key,
                    data=np.nan_to_num(c, nan=0.0).astype(np.float32),
                    compression="gzip",
                    compression_opts=4,
                )
                g.attrs["inference_time_s"] = dt
                n += 1
    return n


def evaluate_group(
    pred_dir: pathlib.Path, splits: list[str], root: str, tier: str | None, acceleration=False
) -> dict:
    from ampscape.eval.harness import evaluate

    r = evaluate(
        pred_dir,
        splits,
        root,
        tier,
        None,
        pred_dir / ("eval_" + "+".join(splits)),
        acceleration=acceleration,
        workers=int(os.environ.get("SLURM_CPUS_PER_TASK", "1")),
    )
    return {
        t: {k: v.get("mean") for k, v in agg.items() if isinstance(v, dict) and "mean" in v}
        | {"speedup": agg.get("speedup")}
        for t, agg in r["per_task"].items()
    } | {"n_rows": r["n_rows"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(MODEL_CONFIGS))
    ap.add_argument("--task", required=True, choices=list(TASK_CHANNELS))
    ap.add_argument("--tier", default="S")
    ap.add_argument("--root", default="data/dev/S")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--time-budget-min", type=float, default=60.0)
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument(
        "--max-train", type=int, default=None, help="subsample the training set (smoke tests)"
    )
    ap.add_argument("--eval-splits", default="test_id,test_ood,ood_region")
    ap.add_argument("--published-root", default="data/builds/published")
    ap.add_argument(
        "--published-tiers", default="S", help="comma list; XXL only for fully convolutional models"
    )
    ap.add_argument("--no-amp", action="store_true")
    ap.add_argument(
        "--resume", action="store_true", help="continue from <out>/last.pt if present (2026-09-24)"
    )
    ap.add_argument(
        "--eval-reserve-min",
        type=float,
        default=60.0,
        help="with --pause-exit: defer the evaluation to a fresh leg when fewer minutes than this remain",
    )
    ap.add_argument(
        "--pause-exit",
        action="store_true",
        help="if the time budget stops training before it finishes, write paused.json and exit without evaluating "
        "(the Slurm wrapper re-queues the job with --resume)",
    )
    ap.add_argument("--eval-only", default=None, help="checkpoint path; skip training")
    ap.add_argument(
        "--variant",
        default="official",
        help="key of ampscape.models.MODEL_VARIANTS[model] (default: the frozen official config)",
    )
    ap.add_argument(
        "--extra",
        default="official",
        help="comma list of extra input channels (dist); 'official' = the frozen default, '' = none",
    )
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    (out / "predictions").mkdir(parents=True, exist_ok=True)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp = (not a.no_amp) and a.model != "fno"  # complex FFT weights are not autocast-safe
    lr = a.lr or DEFAULT_LR[a.model]
    graph = a.model == "gnn"
    if a.variant == "official":
        a.variant = OFFICIAL[a.model][0]
    extra = (
        OFFICIAL[a.model][1] if a.extra == "official" else tuple(e for e in a.extra.split(",") if e)
    )
    mcfg = dict(MODEL_VARIANTS[a.model][a.variant])
    multiscale = bool(mcfg.get("multiscale", False))
    in_ch = n_channels(a.task, extra)

    stats = load_norm_stats(a.root, a.tier) or compute_norm_stats(a.root, a.tier, a.task)
    cfg = {
        "model": a.model,
        "task": a.task,
        "tier": a.tier,
        "root": a.root,
        "model_config": mcfg,
        "variant": a.variant,
        "extra_channels": list(extra),
        "lr": lr,
        "batch": a.batch,
        "epochs": a.epochs,
        "weight_decay": a.weight_decay,
        "seed": a.seed,
        "amp": amp,
        "patience": a.patience,
        "time_budget_min": a.time_budget_min,
        "input_channels": in_ch,
        "target": f"log10({TASK_TARGET[a.task]} + eps*max)",
        "norm_stats": stats["log_resistance"],
        "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        "git": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
    }
    model = build_model(a.model, in_ch, **mcfg).to(device)
    cfg["n_params"] = sum(p.numel() for p in model.parameters())
    (out / "config.json").write_text(json.dumps(cfg, indent=1))

    history = []
    if a.eval_only:
        model.load_state_dict(torch.load(a.eval_only, map_location=device)["model"])
    else:
        tr = AmpScapeDataset(a.task, "train", a.tier, a.root)
        if a.max_train:
            tr.index = tr.index.iloc[: a.max_train].reset_index(drop=True)
        va = AmpScapeDataset(a.task, "val", a.tier, a.root)
        dl_tr = torch.utils.data.DataLoader(
            Items(tr, a.task, stats, graph, extra, multiscale),
            batch_size=a.batch,
            shuffle=True,
            num_workers=a.workers,
            collate_fn=collate,
            pin_memory=True,
            drop_last=True,
            persistent_workers=a.workers > 0,
        )
        dl_va = torch.utils.data.DataLoader(
            Items(va, a.task, stats, graph, extra, multiscale),
            batch_size=a.batch,
            shuffle=False,
            num_workers=a.workers,
            collate_fn=collate,
        )
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=a.weight_decay)
        steps = a.epochs * max(len(dl_tr), 1)
        sched = torch.optim.lr_scheduler.LambdaLR(
            opt, lambda s: 0.5 * (1 + math.cos(math.pi * min(s / max(steps, 1), 1.0)))
        )
        best, bad, t_start = float("inf"), 0, time.time()
        # 2026-09-24 (Phase 10-full on ICE, 16-h walltime): resumable training — `last.pt` holds model, optimiser,
        # scheduler, epoch, best/bad counters, history and the GPU-hours already spent; `--resume` continues from it and
        # `done.json` marks a finished run (patience or epochs), so a wrapper can re-queue until done
        start_ep, spent_h = 1, 0.0
        last = out / "last.pt"
        if a.resume and last.exists():
            ck = torch.load(last, map_location=device)
            model.load_state_dict(ck["model"])
            opt.load_state_dict(ck["opt"])
            sched.load_state_dict(ck["sched"])
            history = ck["history"]
            best, bad, start_ep, spent_h = ck["best"], ck["bad"], ck["epoch"] + 1, ck["gpu_h"]
            print(
                f"resumed from epoch {ck['epoch']} ({spent_h:.2f} GPU-h so far, best val {best:.4f})",
                flush=True,
            )
        with open(out / "log.csv", "a" if (a.resume and start_ep > 1) else "w", newline="") as fh:
            w = csv.writer(fh)
            if start_ep == 1:
                w.writerow(
                    ["epoch", "train_loss", "val_loss", "lr", "epoch_s", "cum_gpu_h", "n_train"]
                )
            finished = False
            ep, cum = start_ep - 1, spent_h
            if start_ep > a.epochs:
                finished = True
            for ep in range(start_ep, a.epochs + 1):
                t0 = time.time()
                tl = run_epoch(model, a.model, dl_tr, device, opt, sched, amp)
                vl = run_epoch(model, a.model, dl_va, device, amp=amp)
                dt = time.time() - t0
                cum = spent_h + (time.time() - t_start) / 3600
                row = [
                    ep,
                    round(tl, 5),
                    round(vl, 5),
                    opt.param_groups[0]["lr"],
                    round(dt, 1),
                    round(cum, 4),
                    len(tr),
                ]
                w.writerow(row)
                fh.flush()
                history.append(
                    dict(
                        zip(
                            [
                                "epoch",
                                "train_loss",
                                "val_loss",
                                "lr",
                                "epoch_s",
                                "cum_gpu_h",
                                "n_train",
                            ],
                            row,
                            strict=True,
                        )
                    )
                )
                print(
                    f"epoch {ep}: train {tl:.4f} val {vl:.4f} ({dt:.0f} s, {cum:.2f} GPU-h)",
                    flush=True,
                )
                if vl < best:
                    best, bad = vl, 0
                    torch.save(
                        {"model": model.state_dict(), "config": cfg, "epoch": ep, "val_loss": vl},
                        out / "best.pt",
                    )
                else:
                    bad += 1
                torch.save(
                    {
                        "model": model.state_dict(),
                        "opt": opt.state_dict(),
                        "sched": sched.state_dict(),
                        "epoch": ep,
                        "best": best,
                        "bad": bad,
                        "history": history,
                        "gpu_h": cum,
                    },
                    out / "last.pt.tmp",
                )
                (out / "last.pt.tmp").replace(last)
                if bad >= a.patience or ep == a.epochs:
                    finished = True
                    print(f"stop at epoch {ep} ({'patience' if bad >= a.patience else 'epochs'})")
                    break
                if (time.time() - t_start) / 60 > a.time_budget_min:
                    print(f"pause at epoch {ep} (time budget; resume with --resume)")
                    break
            if (
                not finished and a.pause_exit
            ):  # time budget hit: let the wrapper re-queue with --resume, no evaluation yet
                (out / "paused.json").write_text(
                    json.dumps(
                        {"epoch": ep, "gpu_h": cum, "job": os.environ.get("SLURM_JOB_ID", "")}
                    )
                )
                print("PAUSED_FOR_RESUME", flush=True)
                return
            (out / "paused.json").unlink(missing_ok=True)
            (out / "done.json").write_text(
                json.dumps({"epoch": ep, "best_val": best, "gpu_h": cum, "finished": finished})
            )
            # 2026-09-24: the evaluation needs a full leg of its own when little budget is left (an FNO M leg was
            # killed by the walltime mid-evaluation); the wrapper re-queues and the next leg evaluates immediately
            left_min = a.time_budget_min - (time.time() - t_start) / 60
            if a.pause_exit and left_min < a.eval_reserve_min:
                (out / "paused.json").write_text(
                    json.dumps(
                        {
                            "epoch": ep,
                            "gpu_h": cum,
                            "job": os.environ.get("SLURM_JOB_ID", ""),
                            "reason": "evaluation deferred",
                        }
                    )
                )
                print(
                    f"training finished; {left_min:.0f} min left < {a.eval_reserve_min} min — evaluation deferred to the next leg",
                    flush=True,
                )
                print("PAUSED_FOR_RESUME", flush=True)
                return
        model.load_state_dict(torch.load(out / "best.pt", map_location=device)["model"])

    # ---- evaluation through the harness ----
    summary = {"config": cfg, "history": history, "eval": {}}
    groups = [(a.root, a.tier, s.strip()) for s in a.eval_splits.split(",") if s.strip()]
    if a.published_root and pathlib.Path(a.published_root).exists():
        groups += [
            (a.published_root, t.strip(), "test_ood_published")
            for t in a.published_tiers.split(",")
            if t.strip()
        ]
    for root, tier, split in groups:
        ds = AmpScapeDataset(a.task, split, tier, root)
        if len(ds) == 0:
            continue
        bs = 1 if tier in ("XL", "XXL") else a.batch
        dl = torch.utils.data.DataLoader(
            Items(ds, a.task, stats, graph, extra, multiscale),
            batch_size=bs,
            shuffle=False,
            num_workers=min(a.workers, 2),
            collate_fn=collate,
        )
        tag = f"{pathlib.Path(root).name}_{tier}_{split}"
        pdir = out / "predictions" / tag
        pdir.mkdir(parents=True, exist_ok=True)
        n = predict(model, a.model, dl, device, a.task, pdir / "predictions.h5", amp)
        (pdir / "meta.json").write_text(
            json.dumps(
                {
                    "model": f"{a.model}-{a.variant}{'+' + '+'.join(extra) if extra else ''}_{a.task}_{a.tier}",
                    "task": a.task,
                    "tier": tier,
                    "split": split,
                    "seed": a.seed,
                    "notes": "learned baseline, Phase 10",
                    "train_root": a.root,
                },
                indent=1,
            )
        )
        summary["eval"][tag] = evaluate_group(pdir, [split], root, tier)
        print(
            f"{tag}: {n} predictions ->",
            {
                t: {
                    k: round(v, 4)
                    for k, v in d.items()
                    if k in ("mae_log10eps", "rel_l2", "top5_iou") and v is not None
                }
                for t, d in summary["eval"][tag].items()
                if isinstance(d, dict)
            },
            flush=True,
        )
    (out / "results.json").write_text(json.dumps(summary, indent=1, default=float))
    print("done ->", out)


if __name__ == "__main__":
    main()
