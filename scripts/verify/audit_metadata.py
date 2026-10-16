#!/usr/bin/env python
"""Verification (owner, 2026-10-15, item 4): the dataset card, croissant.json and CITATION.cff against the published
index — counts, sizes, splits, subsets, licence, versions. Reads only the Hub (index/<tier>.parquet, croissant.json,
README.md, the repo tree) and GitHub-tracked files passed on the command line (card, CITATION.cff).

  python scripts/verify/audit_metadata.py --work work/verify/meta --card docs/dataset_card.md --cff CITATION.cff \
      --out work/verify/audit_metadata.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re

import pandas as pd
import yaml
from huggingface_hub import HfApi, hf_hub_download

TIERS = ["S", "M", "L", "XL", "XXL"]


def card_counts(card: str) -> dict:
    """The 'Final counts' table: tier -> (landscapes, rows, synthetic, real, GB, qc_fail)."""
    out = {}
    sec = card.split("## Final counts")[1].split("\n## ")[0]
    for line in sec.splitlines():
        m = re.match(r"\|\s*\**(\w+)\**\s*\|\s*\**([\d,]+)\**\s*\|\s*\**([\d,]+)\**\s*\|\s*([\d, /]*)\|\s*\**([\d.]+)\**\s*\|\s*(\d+)", line)
        if m:
            tier, land, rows, synreal, gb, qc = m.groups()
            sr = [int(x.replace(",", "").strip()) for x in synreal.split("/")] if "/" in synreal else [None, None]
            out[tier] = {"landscapes": int(land.replace(",", "")), "rows": int(rows.replace(",", "")), "synthetic": sr[0], "real": sr[1], "gb": float(gb), "qc_fail": int(qc)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Xirro/AmpScape")
    ap.add_argument("--work", required=True)
    ap.add_argument("--card", required=True)
    ap.add_argument("--cff", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    work = pathlib.Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    findings: list[dict] = []

    def check(item: str, ok: bool, detail: str) -> None:
        findings.append({"item": item, "ok": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + item + ": " + detail)

    # --- Hub tree: sizes per tier / top folder
    sizes = collections.Counter()
    files = collections.Counter()
    hub_files: dict[str, int] = {}
    for it in api.list_repo_tree(a.repo, repo_type="dataset", recursive=True):
        size = getattr(it, "size", None)
        if size is None:
            continue
        hub_files[it.path] = size
        parts = it.path.split("/")
        top = "/".join(parts[:2]) if parts[0] in ("data", "aux") else parts[0]
        sizes[top] += size
        files[top] += 1
    # --- index per tier
    idx = {}
    for t in TIERS:
        p = hf_hub_download(a.repo, f"index/{t}.parquet", repo_type="dataset", local_dir=str(work))
        idx[t] = pd.read_parquet(p)
    card = pathlib.Path(a.card).read_text()
    cc = card_counts(card)
    hub_readme = pathlib.Path(hf_hub_download(a.repo, "README.md", repo_type="dataset", local_dir=str(work))).read_text()
    check("card == Hub README", hub_readme == card, "identical" if hub_readme == card else "differs")
    tot = {"landscapes": 0, "rows": 0, "gb": 0.0, "qc_fail": 0}
    for t in TIERS:
        d = idx[t]
        land = d.sample_id.nunique()
        rows = len(d)
        real = d[d.family.eq("real") | d.tile_id.notna()].sample_id.nunique() if "tile_id" in d else None
        syn = land - real
        qc_fail = int((~d.qc_pass.astype(bool)).sum())
        gb = sizes[f"data/{t}"] / 1e9
        c = cc.get(t, {})
        tot["landscapes"] += land
        tot["rows"] += rows
        tot["gb"] += gb
        tot["qc_fail"] += qc_fail
        for k, v in (("landscapes", land), ("rows", rows), ("synthetic", syn), ("real", real), ("qc_fail", qc_fail)):
            check(f"{t} {k}", c.get(k) == v, f"index {v} vs card {c.get(k)}")
        check(f"{t} GB", c.get("gb") is not None and abs(c["gb"] - gb) < 0.15, f"Hub {gb:.1f} vs card {c.get('gb')}")
        # splits: index split column vs splits/full/<split>.parquet lists
        for sp in ("train", "val", "test_id", "test_ood"):
            try:
                lp = hf_hub_download(a.repo, f"splits/full/{sp}.parquet", repo_type="dataset", local_dir=str(work))
                ids = set(pd.read_parquet(lp).iloc[:, 0])
            except Exception as e:  # noqa: BLE001
                check(f"{t} split list {sp}", False, f"unreadable: {e}")
                continue
            failing = set(d[~d.qc_pass.astype(bool)].sample_id)  # a landscape with any failing row is excluded whole
            mine = set(d[d.split == sp].sample_id) - failing
            check(f"{t} split {sp} == splits/full/{sp} ∩ tier", mine == (ids & set(d.sample_id)), f"{len(mine)} index ids (QC-failing landscapes removed), {len(mine - ids)} not in the list, {len((ids & set(d.sample_id)) - mine)} listed but not in the index split")
    c = cc.get("total", {})
    for k in ("landscapes", "rows", "qc_fail"):
        check(f"total {k}", c.get(k) == tot[k], f"index {tot[k]} vs card {c.get(k)}")
    check("total GB", c.get("gb") is not None and abs(c["gb"] - tot["gb"]) < 0.5, f"Hub {tot['gb']:.1f} vs card {c.get('gb')}")
    # subsets: landscapes per tier and size on the Hub (shards referenced by hf_path)
    sub_counts = {}
    for sub in ("mini", "lite", "core"):
        per = {}
        gb = 0.0
        nfiles = set()
        for t in TIERS:
            d = idx[t]
            col = f"subset_{sub}"
            if col not in d:
                continue
            s = d[d[col].astype(bool)]
            per[t] = int(s.sample_id.nunique())
            for hp in set(s.hf_path):
                if hp in hub_files:
                    nfiles.add(hp)
                    gb += hub_files[hp] / 1e9
        sub_counts[sub] = {"per_tier": per, "gb": round(gb, 1), "files": len(nfiles)}
    exp = {"mini": ({"S": 600}, 0.6), "lite": ({"S": 8000, "M": 2400, "L": 800}, 26.0), "core": ({"S": 20000, "M": 10000, "L": 5000}, 115.5)}
    for sub, (per, gb) in exp.items():
        got = sub_counts[sub]
        check(f"subset {sub} landscapes", {k: v for k, v in got["per_tier"].items() if v} == per, f"index {got['per_tier']} vs card {per}")
        check(f"subset {sub} GB", abs(got["gb"] - gb) <= max(0.15, 0.05 * gb), f"Hub {got['gb']} GB ({got['files']} files) vs card ≈ {gb}")
    aux_gb = sum(v for k, v in sizes.items() if k.startswith("aux")) / 1e9
    m = re.search(r"under `aux/` \(([\d.]+) GB", card)
    check("aux GB", m is not None and abs(float(m.group(1)) - aux_gb) < 1.0, f"Hub {aux_gb:.1f} vs card {m.group(1) if m else None}")
    # --- croissant
    cj = json.loads(pathlib.Path(hf_hub_download(a.repo, "croissant.json", repo_type="dataset", local_dir=str(work))).read_text())
    cff = yaml.safe_load(pathlib.Path(a.cff).read_text())
    fm = yaml.safe_load(card.split("---")[1])
    ver_card = re.findall(r"\*\*v(\d+\.\d+(?:\.\d+)?)\*\* \((\d{4}-\d\d-\d\d)\)", card)
    latest_card = ver_card[-1] if ver_card else (None, None)
    check("croissant version == latest card version", cj.get("version") == latest_card[0], f"croissant {cj.get('version')} vs card {latest_card}")
    check("croissant datePublished == card date of that version", cj.get("datePublished") == latest_card[1], f"croissant {cj.get('datePublished')} vs card {latest_card[1]}")
    check("CITATION.cff version", str(cff.get("version")) == latest_card[0], f"cff {cff.get('version')} vs card {latest_card[0]}")
    check("CITATION.cff date-released", str(cff.get("date-released")) == latest_card[1], f"cff {cff.get('date-released')} vs card {latest_card[1]}")
    check("licence consistent", "by/4.0" in str(cj.get("license")) and fm.get("license") == "cc-by-4.0" and cff.get("license") == "CC-BY-4.0", f"croissant {cj.get('license')}, card {fm.get('license')}, cff {cff.get('license')}")
    check("CITATION.cff url == Hub repo", cff.get("url", "").endswith(a.repo), cff.get("url"))
    dist = {d["@id"]: d for d in cj.get("distribution", [])}
    expected_sets = {f"shards-{t}-{g}" for t in TIERS for g in ("T1", "T1W", "T1R", "T3", "T4")}
    check("croissant FileSets per tier × group", expected_sets <= set(dist), f"{len(expected_sets & set(dist))}/{len(expected_sets)} present; extra {sorted(set(dist) - expected_sets)}")
    for t in TIERS:
        for g in ("T1", "T1W", "T1R", "T3", "T4"):
            d = dist.get(f"shards-{t}-{g}", {})
            inc = d.get("includes")
            n_hub = sum(1 for p in hub_files if p.startswith(f"data/{t}/{g}/"))
            n_idx = idx[t][idx[t].task_group.eq(g)].hf_path.nunique() if "task_group" in idx[t] else None
            check(f"croissant {t}/{g} includes", inc == f"data/{t}/{g}/*.h5" and n_hub == n_idx, f"includes {inc}; Hub files {n_hub}, index files {n_idx}")
    rs = {r["@id"]: r for r in cj.get("recordSet", [])}
    idx_fields = {f["@id"].split("/")[-1] for r in rs.values() if r["@id"].startswith("index") for f in r.get("field", [])}
    cols = set(idx["S"].columns)
    check("croissant index recordSet fields ⊂ index columns", idx_fields <= cols, f"{len(idx_fields)} fields; not in index: {sorted(idx_fields - cols)}")
    check("croissant subset FileSets", {"subset-mini", "subset-lite", "subset-core"} <= set(dist) or any("lite" in k for k in dist), f"subset entries: {sorted(k for k in dist if 'subset' in k or 'lite' in k or 'mini' in k)}")
    check("card front matter configs", fm.get("configs") not in ([], None), f"configs = {fm.get('configs')!r} (viewer configs; HDF5 shards are not viewer-loadable, so an empty list is expected but the comment claims push_to_hub.py fills it)")
    out = {"findings": findings, "subsets": sub_counts, "sizes_gb": {k: round(v / 1e9, 2) for k, v in sizes.items()}, "files": dict(files), "n_fail": sum(1 for f in findings if not f["ok"])}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"{out['n_fail']} failing of {len(findings)} checks -> {a.out}")


if __name__ == "__main__":
    main()
