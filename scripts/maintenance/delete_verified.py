"""Delete local files listed in a restore manifest, but only after re-checking each one (owner 2026-11-14).

1. Restore test: one entry per group is downloaded from the Hub at its pinned commit into temp and its hash checked;
   if any group fails, nothing is deleted.
2. Each local file is hashed again and deleted only if it still equals the manifest hash; any other file is kept and
   reported. Writes a JSON report. Run as a Slurm CPU job.

    python scripts/maintenance/delete_verified.py --manifest docs/maintenance/restore_manifest_2026-11-14.jsonl \
        --report work/delete_check/delete_2026-11-14.json [--dry-run]
"""

import argparse
import json
import os
import pathlib
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from restore_from_hub import ROOT, expected, fetch, file_hash, load  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--groups", nargs="*", help="limit to these manifest groups")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true", help="hash and report, delete nothing")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    rows = load(a.manifest, a.groups, None)
    # 1. restore test, one (smallest) entry per group
    first = {}
    for r in rows:
        if r["group"] not in first or r["size"] < first[r["group"]]["size"]:
            first[r["group"]] = r
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        for g, r in sorted(first.items()):
            dest = pathlib.Path(tmp) / "restored" / g
            fetch(r, dest, pathlib.Path(tmp) / "dl")  # raises on any mismatch: nothing deleted
            print(f"restore test {g}: {r['hub_path']} ok ({r['size'] / 1e6:.1f} MB)", flush=True)

    # 2. re-hash and delete
    def one(r: dict) -> tuple[str, dict]:
        p = ROOT / r["local"]
        if not p.exists():
            return "absent", r
        if p.stat().st_size != r["size"] or file_hash(p, r) != expected(r):
            return "kept_changed", r
        if not a.dry_run:
            p.unlink()
        return "deleted", r

    out = {"deleted": [], "absent": [], "kept_changed": []}
    with ThreadPoolExecutor(a.workers) as ex:
        for i, (status, r) in enumerate(ex.map(one, rows), 1):
            out[status].append(r["local"])
            if status == "kept_changed":
                print(f"KEPT (changed since verification): {r['local']}", flush=True)
            if i % 500 == 0:
                print(f"{i}/{len(rows)}", flush=True)
    size = {r["local"]: r["size"] for r in rows}
    summary = {k: [len(v), round(sum(size[x] for x in v) / 1e9, 2)] for k, v in out.items()}
    rep = {"manifest": a.manifest, "dry_run": a.dry_run, "restore_test": sorted(first), "summary": summary, **out}
    pathlib.Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps({"dry_run": a.dry_run, "summary": summary}))
    sys.exit(1 if out["kept_changed"] else 0)


if __name__ == "__main__":
    main()
