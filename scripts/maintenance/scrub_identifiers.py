"""Replace identifying strings in text files by neutral placeholders (owner 2026-11-16: no IDs or sensitive content in
the public repo).

The rules are an ordered JSON list of [regex, replacement] pairs in an untracked file (default
`work/identity_scrub.json`), so the identifiers themselves never enter git. Applies to the git-tracked text files of
--root (or every text file when --root is not a git work tree); binary files and files that are not UTF-8 are
skipped and listed. Prints the count per rule and per file. Standard library only.

    python scripts/maintenance/scrub_identifiers.py [--root DIR] [--rules work/identity_scrub.json] [--dry-run]
"""

import argparse
import collections
import json
import pathlib
import re
import subprocess


def text_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Tracked files when --root is the top of a git work tree; every file otherwise (a folder inside another
    repository's ignored area, such as an exported snapshot, has no tracked files of its own)."""
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode == 0 and pathlib.Path(top.stdout.strip()).resolve() == root:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True, check=True)
        return [root / f for f in r.stdout.split("\0") if f]
    return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--rules", default=str(pathlib.Path(__file__).resolve().parents[2] / "work" / "identity_scrub.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rules = [(re.compile(p, re.M), r) for p, r in json.loads(pathlib.Path(a.rules).read_text())]
    root = pathlib.Path(a.root).resolve()
    per_rule, per_file, skipped = collections.Counter(), collections.Counter(), []
    for p in text_files(root):
        if not p.is_file() or p.is_symlink():
            continue
        raw = p.read_bytes()
        if b"\0" in raw[:8192]:
            skipped.append(str(p.relative_to(root)))
            continue
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped.append(str(p.relative_to(root)))
            continue
        new = s
        for i, (rx, rep) in enumerate(rules):
            new, n = rx.subn(rep, new)
            if n:
                per_rule[i] += n
                per_file[str(p.relative_to(root))] += n
        if new != s and not a.dry_run:
            p.write_text(new, encoding="utf-8")
    for i in range(len(rules)):
        if per_rule[i]:
            print(f"rule {i:2d}: {per_rule[i]:5d} replacements")
    for f, n in sorted(per_file.items(), key=lambda kv: -kv[1]):
        print(f"{n:5d} {f}")
    print(f"{sum(per_file.values())} replacements in {len(per_file)} files ({'dry run' if a.dry_run else 'written'}); "
          f"{len(skipped)} binary or non-UTF-8 files skipped")


if __name__ == "__main__":
    main()
