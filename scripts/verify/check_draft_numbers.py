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


TEX_STRIP = re.compile(r"\\(cite[pt]?|ref|label|eqref|includegraphics|input|vspace|hspace|setlength|caption|label|url|href|footnotemark|bibliography|bibliographystyle|usepackage|documentclass|newcommand|renewcommand|begin|end)\*?(\[[^\]]*\])?(\{[^{}]*\})+")
LEN = re.compile(r"-?\d+(\.\d+)?\s*(\\(line|text|column)width|pt|cm|mm|em|ex|in)\b")


def tex_to_units(text: str) -> list[tuple[int, str, list[str]]]:
    """(line, cleaned text, sources) per paragraph of a .tex file. Source tags are `% src: a; b` comment lines inside
    the paragraph (or at its end); table .tex files are checked separately through their own `% src:` header."""
    units = []
    buf, srcs, start = [], [], 1
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw
        m = re.match(r"\s*%\s*src:\s*(.+)$", line)
        if m:
            srcs += [x.strip() for x in re.split(r"[;,]", m.group(1)) if x.strip()]
            continue
        if "%" in line:
            line = re.sub(r"(?<!\\)%.*$", "", line)
        if not line.strip():
            if buf:
                units.append((start, "\n".join(buf), srcs))
            buf, srcs = [], []
            start = ln + 1
            continue
        if not buf:
            start = ln
        buf.append(line)
    if buf:
        units.append((start, "\n".join(buf), srcs))
    out = []
    for start, body, srcs in units:
        body = LEN.sub(" ", body)
        body = TEX_STRIP.sub(" ", body)
        body = re.sub(r"\\[a-zA-Z@]+\*?", " ", body)  # remaining commands
        body = body.replace("$", " ").replace("~", " ")
        out.append((start, body, srcs))
    return out


def check_tex(path: pathlib.Path, root: pathlib.Path) -> dict:
    checked, mismatches, untagged = 0, [], []
    cache: dict[str, str | None] = {}

    def load(p: str) -> str | None:
        if p not in cache:
            f = root / p
            cache[p] = norm(f.read_text()) if f.exists() else None
        return cache[p]

    text = path.read_text()
    if "\\begin{document}" in text:
        text = text.split("\\begin{document}", 1)[1]  # the preamble holds lengths and colour mixes, not results
    for start, body, srcs in tex_to_units(text):
        if re.match(r"\s*\\(section|subsection|paragraph|maketitle|tableofcontents|appendix|newpage|clearpage)", body.strip()) and not srcs:
            toks = numbers(re.sub(r"\\(section|subsection|paragraph)\*?\{[^}]*\}", " ", body))
        else:
            toks = numbers(body)
        if not toks:
            continue
        if any(s.startswith("derived") for s in srcs):
            continue
        if not srcs:
            untagged.append({"file": str(path), "line": start, "tokens": toks, "text": body.strip()[:100]})
            continue
        texts = [t for t in (load(s) for s in srcs) if t]
        for tok in toks:
            checked += 1
            if not present(tok, texts):
                mismatches.append({"file": str(path), "line": start, "token": tok, "sources": srcs, "text": body.strip()[:100]})
    return {"checked": checked, "mismatches": mismatches, "untagged": untagged}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", default="paper/draft.md")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tex", nargs="*", default=None, help="LaTeX files (paragraphs tagged with '%% src:' comments) instead of the Markdown draft")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    if a.tex is not None:
        tot = {"checked": 0, "mismatches": [], "untagged": []}
        for f in a.tex:
            r = check_tex(pathlib.Path(f), root)
            for k in tot:
                tot[k] = tot[k] + r[k] if isinstance(tot[k], list) else tot[k] + r[k]
        if a.out:
            pathlib.Path(a.out).write_text(json.dumps(tot, indent=1))
        print(f"{tot['checked']} numeric tokens checked in {len(a.tex)} LaTeX files; {len(tot['mismatches'])} not found in their source files; {len(tot['untagged'])} untagged paragraphs with numbers")
        for m in tot["mismatches"]:
            print(f"  {m['file']}:L{m['line']}: {m['token']!r} not in {m['sources']} :: {m['text']}")
        for u in tot["untagged"]:
            print(f"  {u['file']}:L{u['line']}: untagged {u['tokens']} :: {u['text']}")
        return
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
