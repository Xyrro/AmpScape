#!/usr/bin/env python
"""Evaluation groups are keyed '<root dir name>_<tier>_<split>'. Legs that read their data from the node's local
copy (train_full.sbatch LOCALDATA=1, 2026-10-13) used root dirs named '<tier>_<group>', so their predictions and
results.json keys came out as e.g. 'M_T4_M_test_id' instead of the canonical 'hfcache_M_test_id' (which the tables,
the T4 reference evaluation and the offloader paths expect). Rename them in place; idempotent.

  python scripts/fix_local_root_tags.py [--runs runs/full] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess

PAT = re.compile(r"^(?P<root>.+)_(?P<tier>S|M|L|XL|XXL)_(?P<split>test_id|test_ood|ood_region|train|val)$")


def fix_run(run: pathlib.Path, dry: bool = False) -> list[tuple[str, str]]:
    renames = []
    pred = run / "predictions"
    if pred.exists():
        for d in sorted(pred.iterdir()):
            m = PAT.match(d.name)
            if not m or m.group("root") == "hfcache":
                continue
            new = f"hfcache_{m.group('tier')}_{m.group('split')}"
            if (pred / new).exists():
                raise RuntimeError(f"{run.name}: both {d.name} and {new} exist")
            renames.append((d.name, new))
            if not dry:
                d.rename(pred / new)
    if not renames:
        return []
    for jf in list(run.glob("*.json")) + list(run.glob("predictions/*/*.json")) + list(run.glob("predictions/*/*/*.json")):
        if jf.name.startswith("."):
            continue
        txt = jf.read_text()
        new_txt = txt
        for old, new in renames:
            new_txt = new_txt.replace(f'"{old}"', f'"{new}"').replace(f"/{old}/", f"/{new}/").replace(f"/{old}\"", f"/{new}\"")
        if new_txt != txt and not dry:
            jf.write_text(new_txt)
    return renames


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/full")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    live = {
        n[len("phase10-") :]
        for n in subprocess.run(
            ["squeue", "-u", os.environ.get("USER", ""), "-h", "-o", "%j"], capture_output=True, text=True
        ).stdout.split()
        if n.startswith("phase10-")
    }  # a leg still writing predictions must not have its directory renamed under it (00:04Z)
    for run in sorted(pathlib.Path(a.runs).iterdir()):
        if not run.is_dir() or (run / ".offloaded").exists() or run.name in live:
            continue
        r = fix_run(run, a.dry_run)
        if r:
            print(f"{run.name}: {', '.join(f'{o} -> {n}' for o, n in r)}{' (dry run)' if a.dry_run else ''}")


if __name__ == "__main__":
    main()
