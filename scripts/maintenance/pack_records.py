"""Pack the scratch-only raw records for the private backup repo Xirro/AmpScape-records (owner 2026-11-16: "if
possible, create a private repo"; nothing identifying goes to the public repo).

Takes the files the offsite audit found in neither git nor the Hub (`audit_offsite.py` report) that belong to the
groups below, hashes each one again and writes one .tar.gz per group (member names = paths relative to the scratch
working copy), a manifest (path, size, sha256, archive) and a README into --out. Upload with `scripts/push_aux.py
--repo Xirro/AmpScape-records --dest records`; restore with `restore_records.py`. Run as a Slurm CPU job.

    python scripts/maintenance/pack_records.py --report work/offsite_audit/report.json --out work/records_upload
"""

import argparse
import fnmatch
import hashlib
import json
import os
import pathlib
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ARCHIVES = {  # archive: globs over scratch-relative paths ("*" crosses "/")
    "review_round3": ["aux/review_round3/*"],
    "review_round2": ["aux/review_round2/*"],
    "aux_builds": ["aux/wp7/*", "aux/scale_probe/*", "aux/t4_bs1_reference/*", "aux/t4_blocksize_baselines/*",
                   "aux/leaderboard/*", "aux/t1_pair1/*"],
    "tiles_metadata": ["data/tiles/*.parquet", "data/tiles/*.json"],
    "data_v1_records": ["data/v1/*"],
    "precision_pass": ["work/precision/*"],
    "run_records": ["runs/full/*warm_start*", "runs/full/gnn_T4_L_s1/*/results.*"],
    "logs": ["logs/*"],
}
SKIP = ["data/v1/*corrupt*", "data/v1/*/corrupt/*", "*/quicklooks/*.png", "data/v1/*/datasets--Xirro--AmpScape/*",
        "*.uploaded", "*.ok", "*.done", "*/.offloaded*", "*.lock"]
README = """# AmpScape raw records (private backup)

Scratch-only raw records of the AmpScape project, backed up before a possible scratch purge (2026-11-16). They are not
part of the public dataset `Xirro/AmpScape`. Every table made from them is in the code repository.

- `records/<group>.tar.gz`: one archive per group; member names are paths relative to the working copy.
- `records/manifest.jsonl`: one line per file: `path`, `size`, `sha256`, `archive`.
- `records/summary.json`: files and bytes per archive.

Restore (from the code repository root): `python scripts/maintenance/restore_records.py --archives <group> ...`
(downloads, extracts only missing files, checks every sha256 against the manifest).

| Archive | Contents |
|---|---|
| review_round3 | review round 3: source-OOD solver builds, decision-analysis prediction maps, PCG all-pairs, heuristic, reference, logs |
| review_round2 | review round 2: coarsen-x4 builds and predictions, Omniscape thread timings, logs |
| aux_builds | WP7 tiles, splits and stats; scale-probe, T4 reference and block-size build manifests and solver logs |
| tiles_metadata | tile specs, candidates and tile tables of the v1 / v1.0 tile plans |
| data_v1_records | per-tier build records: per-shard build indexes, manifests, solve times, build.json, splits, task-log archives |
| precision_pass | post-run precision pass: per-shard rows, reports and selections |
| run_records | warm-start PCG per-system records; second GPU evaluation of gnn_T4_L_s1 at XXL |
| logs | generation, GPU-driver, sync and upload logs |
"""


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
        os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="work/offsite_audit/report.json")
    ap.add_argument("--out", default="work/records_upload")
    a = ap.parse_args()
    rep = json.loads((ROOT / a.report).read_text())
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    groups = {k: [] for k in ARCHIVES}
    for x in rep["nowhere"]:
        p = x["path"]
        if any(fnmatch.fnmatch(p, g) for g in SKIP):
            continue
        for name, globs in ARCHIVES.items():
            if any(fnmatch.fnmatch(p, g) for g in globs):
                groups[name].append(p)
                break
    rows, summary = [], {}
    for name, paths in groups.items():
        present = [p for p in sorted(paths) if (ROOT / p).is_file()]
        with tarfile.open(out / f"{name}.tar.gz", "w:gz", compresslevel=6) as t:
            for p in present:
                rows.append({"path": p, "size": (ROOT / p).stat().st_size, "sha256": sha256(ROOT / p),
                             "archive": f"{name}.tar.gz"})
                t.add(ROOT / p, arcname=p, recursive=False)
        summary[name] = {"files": len(present), "missing_since_audit": len(paths) - len(present),
                         "bytes": sum(r["size"] for r in rows if r["archive"] == f"{name}.tar.gz"),
                         "archive_bytes": (out / f"{name}.tar.gz").stat().st_size}
        print(name, summary[name], flush=True)
    (out / "manifest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    (out / "README.md").write_text(README)
    print(json.dumps({"files": len(rows), "gb": round(sum(r["size"] for r in rows) / 1e9, 3),
                      "archive_gb": round(sum(s["archive_bytes"] for s in summary.values()) / 1e9, 3)}))


if __name__ == "__main__":
    main()
