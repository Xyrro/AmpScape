"""For files of the 2026-10-15 verification mirror that differ from the Hub's main, confirm the exact local bytes exist
at the last Hub commit before the mirror was taken (owner 2026-10-26: delete only what is reproducible)."""

import hashlib
import json
import pathlib
import sys

from huggingface_hub import HfApi

REPO = "Xirro/AmpScape"
rep = json.load(open("work/delete_check/hub_mirror.json"))
paths = [p["path"] for p in rep["problems"]]
api = HfApi()
commits = api.list_repo_commits(REPO, repo_type="dataset")
cut = "2026-10-15T23:35:44"
rev = next(c for c in commits if c.created_at.strftime("%Y-%m-%dT%H:%M:%S") <= cut)  # newest first
info = {}
for d in sorted({str(pathlib.PurePosixPath(p).parent) for p in paths}):
    for e in api.list_repo_tree(REPO, path_in_repo=d, repo_type="dataset", revision=rev.commit_id):
        if hasattr(e, "blob_id"):
            info[e.path] = e
ok, bad = 0, []
for p in paths:
    b = pathlib.Path("work/verify/hub_mirror") / p
    data = b.read_bytes()
    e = info.get(p)
    if e is None:
        bad.append((p, "missing at revision"))
    elif (e.lfs and hashlib.sha256(data).hexdigest() == e.lfs.sha256) or (
        not e.lfs and hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == e.blob_id):
        ok += 1
    else:
        bad.append((p, "differs at revision"))
out = {"revision": rev.commit_id, "revision_time": rev.created_at.isoformat(), "checked": len(paths), "matched": ok,
       "problems": bad}
json.dump(out, open("work/delete_check/hub_mirror_history.json", "w"), indent=1)
print({k: v for k, v in out.items() if k != "problems"}, bad[:5])
sys.exit(1 if bad else 0)
