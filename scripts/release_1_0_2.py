#!/usr/bin/env python
"""v1.0.2 metadata release (owner approval 2026-09-26): two split fixes, data revision unchanged.

1. XL amendment C3 corrected. C3 (25 % of XL landscapes train/val) was applied by hashing `block_id`, which only
   real tiles have; synthetic landscapes hashed the literal "None" (≥ share) and were all moved to test_id
   (XL train 228 / val 0). Corrected rule: real tiles keep the macro-cell rule (unchanged, 228 train) and val is
   drawn among the kept cells at the base val ratio; synthetic landscapes keep their base train/val label with a
   per-seed-family share chosen so that XL train+val ≈ 25 % of the 4,000 landscapes. Everything else (holdouts,
   flags, XXL test-only) is untouched; new train/val rows get test_ood_scale = False and qc_trainval from qc.
2. Split lists rebuilt as cross-tier unions. `publish_index` wrote `splits/<subset>/<split>.parquet` per tier and
   each tier's upload overwrote the previous one (the v1.0 Hub lists held a single tier). The lists are now the
   union over the five tier indexes (mini/lite/core/full membership from the subset columns; QC-failing samples
   excluded as before).

  python scripts/release_1_0_2.py plan                       # dry run: counts, writes work/release_1_0_2/{index,splits}
  python scripts/release_1_0_2.py publish                    # upload index/XL.parquet + splits/** to the Hub, refresh local caches
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ampscape.splits.assign import DEFAULT_CFG, stable_unit  # noqa: E402
from ampscape.splits.spatial import synthetic_split  # noqa: E402

REPO = "Xirro/AmpScape"
TIERS = ["S", "M", "L", "XL", "XXL"]
SPLITS = ["train", "val", "test_id", "test_ood", "ood_region"]
WORK = ROOT / "work" / "release_1_0_2"
CACHE = ROOT / "data" / "hfcache"


def hub_index(tier: str) -> pd.DataFrame:
    from huggingface_hub import hf_hub_download

    return pd.read_parquet(hf_hub_download(REPO, f"index/{tier}.parquet", repo_type="dataset"))


def fix_xl(idx: pd.DataFrame, share_total: float = 0.25) -> tuple[pd.DataFrame, dict]:
    cfg = yaml.safe_load(open(DEFAULT_CFG))
    sp = cfg["splits"]
    seed = int(sp["seed"])
    fr = {k: sp[k] for k in ("train", "val", "test_id")}
    df = idx.copy()
    L = df.drop_duplicates("sample_id").set_index("sample_id")
    n_xl = len(L)
    target = int(round(share_total * n_xl))
    # real tiles: keep the C3 macro-cell rule; val among the kept cells at the base ratio (a second salt)
    real_tv = L[(L.family == "real") & L.split.isin(["train", "val"])]
    val_ratio = fr["val"] / (fr["train"] + fr["val"])
    real_val = {
        sid
        for sid, r in real_tv.iterrows()
        if stable_unit(f"{r.block_id}|{seed}|xlval") < val_ratio
    }
    n_real = len(real_tv)
    # synthetic: candidates = base train/val that C3 moved to test_id (holdouts were applied before C3, so a
    # synthetic test_id row whose base label is train/val is exactly a C3-moved row)
    syn = L[L.family == "synthetic"]
    base = {sid: synthetic_split(int(r.seed), seed, fr) for sid, r in syn.iterrows()}
    cand = [
        sid for sid, b in base.items() if b in ("train", "val") and L.loc[sid, "split"] == "test_id"
    ]
    need = max(target - n_real, 0)
    share = min(need / max(len(cand), 1), 1.0)
    keep = {sid for sid in cand if stable_unit(f"{int(L.loc[sid, 'seed'])}|{seed}|xl") < share}
    new_split = {}
    for sid in keep:
        new_split[sid] = base[sid]
    for sid in real_val:
        new_split[sid] = "val"
    moved = df.sample_id.isin(new_split)
    df.loc[moved, "split"] = df.loc[moved, "sample_id"].map(new_split)
    df.loc[moved, "test_ood_scale"] = False
    if "qc_trainval" in df:
        df["qc_trainval"] = df.qc_pass.astype(bool) & df.split.isin(["train", "val"])
    L2 = df.drop_duplicates("sample_id")
    rep = {
        "xl_landscapes": n_xl,
        "target_trainval": target,
        "real_trainval_kept": n_real,
        "real_val_new": len(real_val),
        "synthetic_candidates": len(cand),
        "synthetic_share": round(share, 4),
        "synthetic_moved_to_trainval": len(keep),
        "before": idx.drop_duplicates("sample_id").split.value_counts().to_dict(),
        "after": L2.split.value_counts().to_dict(),
        "after_by_family": {f: g.split.value_counts().to_dict() for f, g in L2.groupby("family")},
    }
    return df, rep


def build_split_lists(indexes: dict[str, pd.DataFrame], out: pathlib.Path) -> dict:
    counts: dict = {}
    for sub in ("mini", "lite", "core", "full"):
        parts = []
        for idx in indexes.values():
            col = f"subset_{sub}"
            if col not in idx:
                continue
            part = idx[idx[col].astype(bool)]
            bad = (
                set(part.loc[~part.qc_pass.astype(bool), "sample_id"])
                if "qc_pass" in part
                else set()
            )
            parts.append(part[~part.sample_id.isin(bad)][["sample_id", "split"]])
        if not parts:
            continue
        allp = pd.concat(parts, ignore_index=True).drop_duplicates("sample_id")
        d = out / "splits" / sub
        d.mkdir(parents=True, exist_ok=True)
        counts[sub] = {}
        for split, g in allp.groupby("split"):
            g[["sample_id"]].to_parquet(d / f"{split}.parquet", index=False)
            counts[sub][split] = int(len(g))
    return counts


def cmd_plan(a):
    indexes = {t: hub_index(t) for t in TIERS}
    xl_new, rep = fix_xl(indexes["XL"], a.share)
    indexes["XL"] = xl_new
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "index").mkdir(parents=True)
    xl_new.to_parquet(WORK / "index" / "XL.parquet", index=False)
    counts = build_split_lists(indexes, WORK)
    rep["split_lists"] = counts
    (WORK / "report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


def cmd_publish(a):
    from huggingface_hub import HfApi

    if not (WORK / "report.json").exists():
        raise SystemExit("run `plan` first")
    api = HfApi()
    api.upload_folder(
        repo_id=REPO,
        repo_type="dataset",
        folder_path=str(WORK),
        allow_patterns=["index/XL.parquet", "splits/**"],
        commit_message="v1.0.2 (metadata): XL amendment C3 corrected (synthetic train/val restored); split lists rebuilt as cross-tier unions",
    )
    # refresh local caches that carry the index / lists
    for dst in (CACHE, ROOT / "data" / "hf" / "AmpScape"):
        if not dst.exists():
            continue
        (dst / "index").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WORK / "index" / "XL.parquet", dst / "index" / "XL.parquet")
        if (dst / "splits").exists():
            shutil.rmtree(dst / "splits")
        shutil.copytree(WORK / "splits", dst / "splits")
        print("refreshed", dst)
    print("published")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument(
        "--share", type=float, default=0.25, help="XL train+val share of all XL landscapes"
    )
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("publish")
    p.set_defaults(func=cmd_publish)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
