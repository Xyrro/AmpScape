#!/usr/bin/env python
"""Verification item 3 (owner, 2026-10-15): every number in paper/draft.md must be traceable to the repository file
named in the square-bracket source tag that follows it.

Units: a table (its caption line carries the tags; every row is checked against them) or a prose segment (the text
between two tags belongs to the tag that closes it). A numeric token passes when the same digits occur in one of the
segment's source files (thousands separators and the sign are ignored; `0.041`, `167,020`, `1.23e+04`, `4.7 %`,
`2.9e-13` are matched as written). Exempt: bare reference numbers in brackets, section/figure/table/appendix numbers,
tiers and task names (T1, 128²), versions and dates, and integers below 20 (counts such as "three seeds", "K ∈ [2, 8]").

  python scripts/verify/check_draft_numbers.py --draft paper/draft.md [--root .] [--out work/verify/draft_numbers.json]
  (--root may point at a tagged checkout: every source path is read relative to it)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

TAG = re.compile(r"\[((?:[\w./-]+\.(?:md|json|py|yaml|cff))(?:\s*[;,]\s*[\w./-]+\.(?:md|json|py|yaml|cff))*|derived(?::[^\]]*)?)\]")
CITE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")
NUM = re.compile(r"(?<![\w.])[+-]?\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?(?![\w²³⁴⁵⁶⁷⁸⁹⁰¹])")
EXEMPT_BEFORE = re.compile(r"(Table|Figure|Section|Appendix|§|Sections|Tables|Figures|v|version|K ∈ \[|n ∈ \{|q ∈ \{|CC BY|CC0|Croissant|Python|Circuitscape\.jl|Omniscape\.jl)\s*$")


def numbers(text: str) -> list[str]:
    text = CITE.sub(" ", text)
    text = re.sub(r"\b(20\d\d-\d\d-\d\d|20\d\d|v?\d+\.\d+\.\d+|T\dV?[WR]?|[SMLX]{1,3}\b|\d+²)", " ", text)
    out = []
    for m in NUM.finditer(text):
        tok = m.group(0)
        before = text[max(0, m.start() - 12):m.start()]
        if EXEMPT_BEFORE.search(before):
            continue
        plain = tok.replace(",", "").lstrip("+-")
        if re.fullmatch(r"\d+", plain) and int(plain) < 20:
            continue
        if re.fullmatch(r"\d+\.\d", plain) and re.search(r"(Section|§|Appendix|Sections)\s*$", before):
            continue
        out.append(tok)
    return out


def norm(s: str) -> str:
    return s.replace(",", "").replace(" ", "").replace(" ", "")


def present(tok: str, texts: list[str]) -> bool:
    t = norm(tok).lstrip("+-")
    for body in texts:
        if t in body:
            return True
        # 4.7 % written as 4.7% or 0.0470; 1.23e+04 as 1.23e4
        if "e+" in t and t.replace("e+", "e") in body:
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", default="paper/draft.md")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    lines = pathlib.Path(a.draft).read_text().splitlines()
    cache: dict[str, str | None] = {}

    def load(path: str) -> str | None:
        if path not in cache:
            p = root / path
            cache[path] = norm(p.read_text()) if p.exists() else None
        return cache[path]

    checked = 0
    mismatches: list[dict] = []
    untagged: list[dict] = []
    missing_files: set[str] = set()
    table_sources: list[str] = []
    in_table = False
    in_refs = False
    for ln, line in enumerate(lines, 1):
        if line.startswith("## References"):
            in_refs = True
        elif line.startswith("#"):
            in_refs = False
        if in_refs or re.match(r"^\d+\. ", line):
            continue  # bibliography entries carry volume/page numbers, not results
        if line.startswith("|"):
            if not in_table:
                in_table = True
            if re.fullmatch(r"\|(\s*-+\s*\|)+", line.strip()):
                continue
            toks = numbers(line)
            if not toks:
                continue
            if not table_sources:
                untagged.append({"line": ln, "tokens": toks, "text": line[:80]})
                continue
            if any(src.startswith("derived") for src in table_sources):
                continue
            texts = [t for t in (load(s) for s in table_sources) if t]
            for tok in toks:
                checked += 1
                if not present(tok, texts):
                    mismatches.append({"line": ln, "token": tok, "sources": table_sources, "text": line[:100]})
            continue
        in_table = False
        if not line.strip() or line.startswith("#") or line.startswith("<!--"):
            if line.startswith("#"):
                m = TAG.search(line)  # a heading may carry the tag of the table(s) under it
                table_sources = [t.strip() for t in re.split(r"[;,]", m.group(1))] if m else []
            continue
        tags = list(TAG.finditer(line))
        if tags:
            table_sources = [s.strip() for s in re.split(r"[;,]", tags[-1].group(1))]
        pos = 0
        segments = []
        for m in tags:
            segments.append((line[pos:m.start()], [s.strip() for s in re.split(r"[;,]", m.group(1))]))
            pos = m.end()
        tail = line[pos:]
        if tail.strip():
            segments.append((tail, tags[-1].group(1).split(";") if tags else []))
        for text, sources in segments:
            toks = numbers(text)
            if not toks:
                continue
            sources = [s.strip() for s in sources]
            if not sources:
                untagged.append({"line": ln, "tokens": toks, "text": text.strip()[:100]})
                continue
            if any(src.startswith("derived") for src in sources):
                continue  # arithmetic on tagged numbers, marked [derived: ...]
            texts = []
            for s in sources:
                t = load(s)
                if t is None:
                    missing_files.add(s)
                else:
                    texts.append(t)
            for tok in toks:
                checked += 1
                if not present(tok, texts):
                    mismatches.append({"line": ln, "token": tok, "sources": sources, "text": text.strip()[:100]})
    out = {"draft": a.draft, "root": str(root), "checked": checked, "mismatches": mismatches, "untagged": untagged, "missing_source_files": sorted(missing_files)}
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"{checked} numeric tokens checked; {len(mismatches)} not found in their source files; {len(untagged)} untagged segments with numbers; {len(missing_files)} missing source files {sorted(missing_files)}")
    for m in mismatches:
        print(f"  L{m['line']}: {m['token']!r} not in {m['sources']} :: {m['text']}")
    for u in untagged:
        print(f"  L{u['line']}: untagged {u['tokens']} :: {u['text']}")


if __name__ == "__main__":
    main()
