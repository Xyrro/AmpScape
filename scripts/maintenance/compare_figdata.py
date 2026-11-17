"""Compare two paper/figdata directories array by array (owner 2026-10-26: figdata is deleted only if a rebuild from
the Hub reproduces it exactly). Exit 0 only when every .npz holds identical arrays and the manifests agree."""

import json
import pathlib
import sys

import numpy as np

a, b = map(pathlib.Path, sys.argv[1:3])
bad = []
names = sorted({p.name for p in a.iterdir()} | {p.name for p in b.iterdir()})
for n in names:
    pa, pb = a / n, b / n
    if not (pa.exists() and pb.exists()):
        bad.append(f"{n}: only in one directory")
    elif n.endswith(".npz"):
        za, zb = np.load(pa, allow_pickle=False), np.load(pb, allow_pickle=False)
        if set(za.files) != set(zb.files):
            bad.append(f"{n}: different keys")
        for k in set(za.files) & set(zb.files):
            if za[k].dtype != zb[k].dtype or not np.array_equal(za[k], zb[k], equal_nan=za[k].dtype.kind in "fc"):
                bad.append(f"{n}:{k} differs")
    elif n.endswith(".json"):
        ja, jb = json.loads(pa.read_text()), json.loads(pb.read_text())
        for j in (ja, jb):  # build timestamp and duration
            j.pop("_meta", None) if isinstance(j, dict) else None
        if ja != jb:
            bad.append(f"{n}: content differs")
    elif pa.read_bytes() != pb.read_bytes():
        bad.append(f"{n}: bytes differ")
print(f"{len(names)} files compared, {len(bad)} differences")
print("\n".join(bad))
sys.exit(1 if bad else 0)
