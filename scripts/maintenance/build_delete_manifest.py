"""Build the restore manifest for the 2026-11-14 scratch cleanup (owner: delete only what is fully reproducible).

Every entry maps a local file to a Hub path holding byte-identical content, pinned to one Hub commit, with the Hub's
hash. Inputs are the read-only verification reports of `verify_against_hub.py` (work/delete_check/r2/): files those
reports flagged are left out. Login node (Hub listing only, no hashing).

    python scripts/maintenance/build_delete_manifest.py --reports work/delete_check/r2 \
        --revision aa2bc2f546bffe56f1584326ed3840e5a3fb0649 --out docs/maintenance/restore_manifest_2026-11-14.jsonl
"""

import argparse
import json
import pathlib

REPO = "Xirro/AmpScape"
ROOT = pathlib.Path(__file__).resolve().parents[2]

# group: (local root, globs, Hub prefix, path-matched report) — the local relative path equals the Hub relative path
BY_PATH = {
    "best_pt": ("runs/full", ["*/best.pt"], "aux/results/runs_full", "best_pt.json"),
    "t1_pair1": ("aux/t1_pair1", ["**/*.h5"], "aux/t1_pair1", "t1_pair1.json"),
    "runs_tune": ("runs/tune", ["**/*.h5", "**/*.pt"], "aux/results/runs_tune", "runs_tune.json"),
    "runs_dev": ("runs/dev", ["**/*.h5", "**/*.pt"], "aux/results/runs_dev", "runs_dev.json"),
    "predictions": ("data/predictions", ["**/*.h5"], "aux/results/predictions", "predictions.json"),
    "runs_full_h5": ("runs/full", ["**/*.h5"], "aux/results/runs_full", "runs_full_h5.json"),
}
# group: (content-matched report, Hub prefix) — the report records the Hub path of each local file
BY_CONTENT = {
    "bs1_reference": ("bs1_content.json", "aux/t4_bs1_reference"),
    "blocksize": ("blocksize_content.json", "aux/t4_blocksize_baselines"),
    "scale_probe_h5": ("scale_probe_h5_content.json", "aux/scale_probe"),
    "scale_probe_tif": ("scale_probe_tif_content.json", "aux/scale_probe"),
    "wp7_h5": ("wp7_h5_content.json", "aux/wp7"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="work/delete_check/r2")
    ap.add_argument("--revision", required=True, help="Hub commit the reports were checked against")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from huggingface_hub import HfApi

    api = HfApi()
    rep_dir = ROOT / a.reports
    listing = {}

    def hub(prefix: str) -> dict:
        if prefix not in listing:
            listing[prefix] = {
                e.path: e
                for e in api.list_repo_tree(REPO, path_in_repo=prefix, recursive=True, repo_type="dataset",
                                            revision=a.revision)
                if hasattr(e, "blob_id")
            }
        return listing[prefix]

    def entry(group: str, local: pathlib.Path, e) -> dict:
        d = {"group": group, "local": local.relative_to(ROOT).as_posix(), "hub_path": e.path, "revision": a.revision,
             "size": e.size}
        d.update({"sha256": e.lfs.sha256} if e.lfs else {"git_sha1": e.blob_id})
        assert local.stat().st_size == e.size, f"size changed since verification: {local}"
        return d

    out, counts = [], {}
    for group, (root, globs, prefix, report) in BY_PATH.items():
        flagged = {p["path"] for p in json.loads((rep_dir / report).read_text())["problems"]}
        h = hub(prefix)
        files = sorted({p for g in globs for p in (ROOT / root).glob(g) if p.is_file()})
        for p in files:
            hp = f"{prefix}/{p.relative_to(ROOT / root).as_posix()}"
            if hp in flagged or hp not in h:
                continue
            out.append(entry(group, p, h[hp]))
    for group, (report, prefix) in BY_CONTENT.items():
        r = json.loads((rep_dir / report).read_text())
        h = hub(prefix)
        for rel, hp in sorted(r["hub_path"].items()):
            out.append(entry(group, ROOT / r["local"] / rel, h[hp]))
    for d in out:
        counts[d["group"]] = counts.get(d["group"], [0, 0])
        counts[d["group"]][0] += 1
        counts[d["group"]][1] += d["size"]
    assert len({d["local"] for d in out}) == len(out), "a local file appears twice"
    path = ROOT / a.out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(d) + "\n" for d in out))
    for g, (n, b) in counts.items():
        print(f"{g:16s} {n:5d} files {b / 1e9:7.2f} GB")
    print(f"{'total':16s} {len(out):5d} files {sum(d['size'] for d in out) / 1e9:7.2f} GB -> {a.out}")


if __name__ == "__main__":
    main()
