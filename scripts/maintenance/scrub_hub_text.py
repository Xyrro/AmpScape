"""Stage cleaned copies of the public dataset's text files (owner 2026-11-16: no IDs or sensitive content in the public
repo; step 1 of the recommendation in docs/status: current files only, HDF5 files and history unchanged).

Downloads every text file of Xirro/AmpScape at REVISION (JSON, Markdown, CSV, logs, ...; no HDF5, checkpoints,
GeoTIFF, PNG or parquet) to node-local temp, applies the untracked rules of `scrub_identifiers.py`
(`work/identity_scrub.json`) and writes each changed file to --out/<Hub path>. A changed JSON file must parse and must
equal the original with the rules applied to every key and string value, so no number, list or structure changes.
Writes --out/../changes.jsonl (path, sha256 before/after, replacements). Read-only on the Hub; upload the staging
folder with `scripts/push_aux.py`. Run as a Slurm CPU job.

    python scripts/maintenance/scrub_hub_text.py --out work/hub_scrub/staging
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import tempfile

REPO = "Xirro/AmpScape"
ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP = ["*.h5", "*.pt", "*.tif", "*.tiff", "*.png", "*.parquet", "*.npz", "*.pdf"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", default="main")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules", default=str(ROOT / "work" / "identity_scrub.json"))
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import snapshot_download

    rules = [(re.compile(p, re.M), r) for p, r in json.loads(pathlib.Path(a.rules).read_text())]

    def scrub(s: str) -> tuple[str, int]:
        total = 0
        for rx, rep in rules:
            s, n = rx.subn(rep, s)
            total += n
        return s, total

    def scrub_obj(o):
        if isinstance(o, str):
            return scrub(o)[0]
        if isinstance(o, list):
            return [scrub_obj(x) for x in o]
        if isinstance(o, dict):
            return {scrub(k)[0]: scrub_obj(v) for k, v in o.items()}
        return o

    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    changes, n_text, bad = [], 0, []
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        snapshot_download(REPO, repo_type="dataset", revision=a.revision, local_dir=tmp, ignore_patterns=SKIP,
                          max_workers=8)
        for p in sorted(pathlib.Path(tmp).rglob("*")):
            if not p.is_file() or ".cache" in p.relative_to(tmp).parts:
                continue
            rel = p.relative_to(tmp).as_posix()
            raw = p.read_bytes()
            try:
                s = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            n_text += 1
            new, n = scrub(s)
            if not n:
                continue
            if rel.endswith(".json"):
                try:
                    if json.loads(new) != scrub_obj(json.loads(s)):
                        bad.append(rel)
                        continue
                except ValueError:
                    bad.append(rel)
                    continue
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(new, encoding="utf-8")
            changes.append({"path": rel, "replacements": n, "sha256_before": hashlib.sha256(raw).hexdigest(),
                            "sha256_after": hashlib.sha256(new.encode()).hexdigest()})
    (out.parent / "changes.jsonl").write_text("".join(json.dumps(c) + "\n" for c in changes))
    print(json.dumps({"text_files": n_text, "changed": len(changes), "replacements": sum(c["replacements"] for c in changes),
                      "staged_gb": round(sum((out / c["path"]).stat().st_size for c in changes) / 1e9, 3),
                      "rejected_json": bad}))


if __name__ == "__main__":
    main()
