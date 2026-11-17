"""Owner 2026-11-16: is the proposed aux/records/ upload safe for the public Hub? Read-only scan of the candidate files
(and, for comparison, of scratch files already public on the Hub) for credentials, e-mail addresses and identifying
strings: raw bytes of text/tif/other files, every member of tar archives, string columns of parquet files, HDF5
attributes and small string datasets. Reads the audit_offsite.py report; run as a Slurm CPU job from the repo root:

    python scripts/maintenance/scan_sensitive.py   # -> work/offsite_audit/sensitive_scan.json
"""
import collections
import fnmatch
import getpass
import json
import os
import pathlib
import re
import tarfile
from multiprocessing import Pool

import h5py
import pandas as pd

UPLOAD = ["aux/review_round3/*", "aux/review_round2/*", "aux/wp7/*", "aux/scale_probe/*", "aux/t4_bs1_reference/*",
          "aux/t4_blocksize_baselines/*", "aux/leaderboard/*", "aux/t1_pair1/*", "data/tiles/*.parquet", "data/tiles/*.json",
          "data/v1/*", "work/precision/*", "runs/full/*warm_start*", "runs/full/gnn_T4_L_s1/*/results.*", "logs/*"]
SKIP = ["data/v1/*corrupt*", "data/v1/*/corrupt/*", "*/quicklooks/*.png", "data/v1/*/datasets--Xirro--AmpScape/*",
        "*.uploaded", "*.ok", "*.done", "*/.offloaded*", "*.lock"]
PAT = {
    "hf_token": rb"hf_[A-Za-z0-9]{30,}", "github_token": rb"(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})",
    "private_key": rb"-----BEGIN [A-Z ]*PRIVATE KEY", "aws_key": rb"AKIA[0-9A-Z]{16}",
    "secret_word": rb"(?i)(password|passwd|api[_-]?key|secret[_-]?key|access[_-]?token|bearer [a-z0-9])",
    "email": rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.(com|edu|org|net|io|ai)\b",
    # identity patterns are never committed (owner 2026-11-16: no IDs in the public repo): the user ID and the home
    # and scratch prefixes come from the environment, everything else (institution, cluster, node names, accounts,
    # personal names) from the untracked IDENTITY_FILE as {"name": "regex", ...}
    "user_id": re.escape(getpass.getuser()).encode(),
    "home_or_scratch_path": "|".join(re.escape(str(pathlib.Path(p).parent)) for p in
                                     (os.path.expanduser("~"), os.environ.get("AMPSCAPE_SCRATCH", "/nonexistent/x"))
                                     ).encode(),
}
IDENTITY_FILE = pathlib.Path(__file__).resolve().parents[2] / "work" / "identity_patterns.json"
if IDENTITY_FILE.exists():
    PAT.update({k: v.encode() for k, v in json.loads(IDENTITY_FILE.read_text()).items()})


def scan(buf: bytes, where: str, found: dict):
    for k, p in PAT.items():
        if k in found:
            continue
        m = re.search(p, buf)
        if m:
            s = buf[max(0, m.start() - 40): m.end() + 40].decode("latin-1").replace("\n", " ")
            if k in ("hf_token", "github_token", "private_key", "aws_key"):
                s = re.sub(r"(hf_|gh[pousr]_|github_pat_|AKIA)[A-Za-z0-9_]{4}[A-Za-z0-9_]+", r"\1****(masked)", s)
            found[k] = f"{where}: ...{s}..."


def strings_h5(f):
    out = []
    def visit(name, obj):
        for a, v in obj.attrs.items():
            out.append(f"{name}@{a}={v!r}"[:2000])
        if isinstance(obj, h5py.Dataset) and obj.dtype.kind in "SOU" and obj.size < 10000:
            out.append(repr(obj[()])[:20000])
    f.visititems(visit)
    for a, v in f.attrs.items():
        out.append(f"/@{a}={v!r}"[:2000])
    return "\n".join(out).encode()


def scan_file(args):
    rel, group = args
    found, err = {}, None
    p = pathlib.Path(rel)
    name = p.name
    try:
        if name.endswith((".tar.gz", ".tgz", ".tar")):
            with tarfile.open(p) as t:
                for m in t:
                    scan(m.name.encode(), f"{rel}:{m.name}", found)
                    if m.isfile():
                        scan(t.extractfile(m).read(), f"{rel}:{m.name}", found)
        elif name.endswith(".parquet"):
            df = pd.read_parquet(p)
            parts = [" ".join(map(str, df.columns))]
            for c in df.columns:
                if df[c].dtype == object:
                    parts.append("\n".join(map(str, df[c].dropna().astype(str).unique()[:200000])))
            scan("\n".join(parts).encode(), rel, found)
        elif ".h5" in name:
            with h5py.File(p, "r") as f:
                scan(strings_h5(f), rel, found)
        else:
            scan(p.read_bytes(), rel, found)
    except Exception as e:  # noqa: BLE001
        err = f"{rel}: {type(e).__name__}: {e}"[:300]
    return group, found, err

def tally(jobs: list[tuple[str, str]], n_proc: int) -> tuple[dict, dict, list]:
    """Scan (path, group) pairs in parallel: per pattern, files with a hit per group, a few examples, errors."""
    hits = {k: collections.Counter() for k in PAT}
    ex = {k: [] for k in PAT}
    errors = []
    with Pool(n_proc) as pool:
        for i, (group, found, err) in enumerate(pool.imap_unordered(scan_file, jobs, chunksize=16), 1):
            for k, e in found.items():
                hits[k][group] += 1
                if sum(1 for x in ex[k] if x.startswith(group)) < 4:
                    ex[k].append(f"{group} | {e}")
            if err:
                errors.append(err)
            if i % 5000 == 0:
                print(i, flush=True)
    return {k: dict(v) for k, v in hits.items()}, ex, errors


def main() -> None:
    R = json.load(open("work/offsite_audit/report.json"))
    up = [x["path"] for x in R["nowhere"] if any(fnmatch.fnmatch(x["path"], g) for g in UPLOAD)
          and not any(fnmatch.fnmatch(x["path"], g) for g in SKIP)]
    pub = [f for f in R["on_hub"] if f.endswith((".json", ".md", ".log", ".csv", ".txt", ".out", ".parquet"))]
    print(f"upload candidates: {len(up)} files; already-public comparison set: {len(pub)} files", flush=True)
    jobs = [(rel, "optional_solver_logs" if fnmatch.fnmatch(rel, "aux/t4_*/*/logs/*")
             or fnmatch.fnmatch(rel, "aux/scale_probe/*/logs/*") else "upload") for rel in up]
    jobs += [(rel, "already_public") for rel in pub]
    hits, ex, errors = tally(jobs, int(os.environ.get("SLURM_CPUS_PER_TASK", "4")))
    res = {"n_upload": len(up), "n_public_compared": len(pub), "hits": hits, "examples": ex, "errors": errors[:50],
           "n_errors": len(errors)}
    pathlib.Path("work/offsite_audit/sensitive_scan.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(hits, indent=0))
    print("errors", len(errors))


if __name__ == "__main__":
    main()
