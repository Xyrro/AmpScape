"""Restore files deleted in a scratch cleanup from the Hub, byte for byte (owner 2026-11-14).

Reads a restore manifest (`build_delete_manifest.py`): each entry names the local path, the Hub path with identical
bytes, the pinned Hub commit and the hash. Each file is downloaded to node-local temp, its hash checked, then moved to
the local path. Run as a Slurm CPU job (compute nodes reach the Hub; keeps the login-node memory cgroup clear).

    python scripts/maintenance/restore_from_hub.py --manifest docs/maintenance/restore_manifest_2026-11-14.jsonl \
        --groups best_pt bs1_reference [--only 'runs/full/unet_T4_L_*'] [--dry-run]
"""

import argparse
import fnmatch
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

REPO = "Xirro/AmpScape"
ROOT = pathlib.Path(__file__).resolve().parents[2]


def file_hash(path: pathlib.Path, entry: dict) -> str:
    """The hash kind the manifest entry carries (sha256 for LFS/xet files, git blob sha1 otherwise)."""
    h = hashlib.sha256() if "sha256" in entry else hashlib.sha1(b"blob %d\0" % path.stat().st_size)
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
        os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return h.hexdigest()


def expected(entry: dict) -> str:
    return entry.get("sha256") or entry["git_sha1"]


def fetch(entry: dict, dest: pathlib.Path, tmp: pathlib.Path) -> None:
    """Download the entry's Hub file at its pinned commit, verify, and move it to dest."""
    from huggingface_hub import hf_hub_download

    p = pathlib.Path(hf_hub_download(REPO, entry["hub_path"], repo_type="dataset", revision=entry["revision"],
                                     local_dir=str(tmp)))
    got = file_hash(p, entry)
    if got != expected(entry):
        p.unlink(missing_ok=True)
        raise RuntimeError(f"hash mismatch after download: {entry['hub_path']} ({got} != {expected(entry)})")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(p), str(dest))


def load(manifest: str, groups: list[str] | None, only: str | None) -> list[dict]:
    rows = [json.loads(line) for line in (ROOT / manifest).read_text().splitlines() if line.strip()]
    if groups:
        rows = [r for r in rows if r["group"] in groups]
    if only:
        rows = [r for r in rows if fnmatch.fnmatch(r["local"], only)]
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--groups", nargs="*")
    ap.add_argument("--only", help="glob over the local paths")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    rows = load(a.manifest, a.groups, a.only)
    todo = [r for r in rows if not (ROOT / r["local"]).exists()]
    print(f"{len(rows)} entries selected, {len(todo)} missing locally, {sum(r['size'] for r in todo) / 1e9:.2f} GB")
    if a.dry_run:
        return
    failed = 0
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        for r in todo:
            try:
                fetch(r, ROOT / r["local"], pathlib.Path(tmp))
            except Exception as e:  # noqa: BLE001 — report every failure, keep going
                failed += 1
                print(f"FAILED {r['local']}: {e}", flush=True)
    print(f"restored {len(todo) - failed} of {len(todo)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
