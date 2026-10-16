# Status — 2026-10-16 03:20Z: style memo written, paper rewritten as a NeurIPS 2026 LaTeX submission (9 content pages), PDF built

## Done (owner request 2026-10-16)
1. **Literature pass on form** — `docs/paper_style_memo.md`: PDEBench, The Well, PGLearn, OGB, EngiBench (NeurIPS 2025
   D&B) and Bubbleformer (NeurIPS 2025 spotlight; track label not shown publicly), the NeurIPS checklist, the 2026
   formatting instructions and the Evaluations & Datasets call. Structural counts (words, sections, figures, tables,
   sentence length) parsed from the arXiv HTML; first page / Figure 1 patterns, data overview, tasks, baselines,
   results, table style, tone, appendix contents and the 16 checklist items.
2. **LaTeX submission** — `paper/neurips/main.tex` with `neurips_2026.sty` (revision 2026-01-29, `eandd` track
   option, submission mode), built with Tectonic 0.17.0 → **`paper/neurips/main.pdf`** (28 pages: 9 content pages,
   references from page 10, appendices A–I, checklist). Markdown draft retired to `paper/draft_md_archive.md`.
3. **Figures** — seven main-text figures and the appendix set, all from `scripts/paper_figures.py --tex`
   (`scripts/paper_figdata.py` extracts the raster arrays from the Hub once); tables from
   `scripts/paper_tables_tex.py`. Every number traceable: `check_draft_numbers.py --tex` → 2,000 tokens, 0 untraceable.
4. **Change summary** — `docs/paper_tex_changes.md` (one page).

## Open for the owner
- Nine pages with no slack; Figures 2 and 3 are printed at 60 % / 50 % width.
- Camera-ready needs the `final` option, author block and a code tag (see `docs/verification_report.md`).

## Operations
GPU use for this step: none. Scratch ≈ 230 GB (XL/T4, XXL/T1 staged; `paper/figdata/` 455 MB, git-ignored).
Offloader loop and keepalive running. GitHub main = origin after this push.
