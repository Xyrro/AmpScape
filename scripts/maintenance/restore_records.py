"""Restore (or verify) the raw records backed up in the private repo Xirro/AmpScape-records (`pack_records.py`).

Downloads `records/manifest.jsonl` and the requested archives to temp, extracts them and checks every file's sha256
against the manifest. A restore writes only files missing from the working copy (existing ones are compared and
reported); `--verify-only` extracts everything to temp and writes nothing. Needs a token that can read the private
repo. Run as a Slurm CPU job.

    python scripts/maintenance/restore_records.py --archives review_round3 logs [--only 'aux/review_round3/source_ood/*']
    python scripts/maintenance/restore_records.py --all --verify-only
"""

import argparse
import fnmatch
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tarfile
import tempfile

REPO = "Xirro/AmpScape-records"
ROOT = pathlib.Path(__file__).resolve().parents[2]


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
        os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archives", nargs="*", default=[], help="archive names without .tar.gz")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", help="glob over the restored paths")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--revision", default="main")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import hf_hub_download

    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        tmp = pathlib.Path(tmp)

        def get(f: str) -> pathlib.Path:
            return pathlib.Path(hf_hub_download(REPO, f"records/{f}", repo_type="dataset", revision=a.revision,
                                                local_dir=str(tmp / "dl")))

        man = [json.loads(line) for line in get("manifest.jsonl").read_text().splitlines() if line.strip()]
        names = sorted({r["archive"][: -len(".tar.gz")] for r in man}) if a.all else a.archives
        bad = 0
        for name in names:
            rows = {r["path"]: r for r in man if r["archive"] == f"{name}.tar.gz"
                    and (not a.only or fnmatch.fnmatch(r["path"], a.only))}
            arc = get(f"{name}.tar.gz")
            ex = tmp / "x" / name
            with tarfile.open(arc) as t:
                members = [m for m in t.getmembers() if m.name in rows]
                t.extractall(ex, members=members, filter="data")
            arc.unlink()
            counts = {"verified": 0, "restored": 0, "present_identical": 0, "present_different": 0}
            for path, r in rows.items():
                p = ex / path
                if not p.is_file() or p.stat().st_size != r["size"] or sha256(p) != r["sha256"]:
                    bad += 1
                    print(f"BAD {name}: {path}", flush=True)
                    continue
                counts["verified"] += 1
                if a.verify_only:
                    continue
                dest = ROOT / path
                if dest.exists():
                    counts["present_identical" if sha256(dest) == r["sha256"] else "present_different"] += 1
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(p), str(dest))
                    counts["restored"] += 1
            shutil.rmtree(ex)
            print(f"{name}: {len(rows)} files in manifest, {counts}", flush=True)
    print("all files verified" if not bad else f"{bad} files FAILED verification")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
