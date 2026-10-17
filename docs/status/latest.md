# Status — 2026-10-17 04:40Z: paper print-legibility pass complete (every page re-checked at print size)

## Done (owner request 2026-10-16/17: "recheck the paper carefully, i found many bugs, especially in the images …
make sure there's nothing like this anymore … also check for every parts of the paper at the end … pictures in part D
they combined together, it's too small to read")
1. **Figures** — every figure is now drawn at the width it is printed (`FULLW = 5.5` in, `HALFW = 2.64` in), so the
   font sizes in `scripts/paper_figures.py` are the font sizes on paper (the first PDF scaled 7-inch figures by 0.79
   and Figures 2/3 to 60 % / 50 %). Figure 2 re-laid out as a 3 × 10 grid (tiers as columns), Figure 3 as one row per
   task with in-distribution and OOD side by side, Figures 5/6 as native half-width designs. Every overlap found in the
   page-by-page audit removed (Figure 1 text block, Figure 4 legend and log ticks, Figure 5 annotations, OOD tier
   letters, curve titles, fidelity/WP7 titles and axis labels, precision legends). **Appendix D statistics redrawn**
   as four separate full-width figures in the paper style instead of four shrunk PNG copies.
2. **Tables** — headers printed raw LaTeX (`\rightarrow`, `\Delta`, `test\_id`) → math-aware escaper; Table 5 was
   empty → fixed `md_rows`; five wide tables were `\resizebox`-shrunk to ≈ 5 pt → slimmer columns at `\scriptsize`,
   no scaling, no overfull box; Table 1 `²`/`·` glyphs; `--` flags keep their double hyphens.
3. **Bibliography** — author lists were split at commas (`McRae and B. H.`), titles lower-cased (`julia`, `jax`),
   arXiv ids inside titles, unprintable dashes → all repaired (`references.bib`).
4. **Checklist / end matter** — hard-coded appendix letters had drifted (licences cited as Appendix I) → `\ref`s;
   `placeins` float barriers so no figure precedes its section heading; data-scaling figure next to its table.
5. **Verification** — `main.pdf` rebuilt (27 pages; 9 content pages, references from page 10); build log: 0 overfull
   boxes, 0 missing characters; `check_draft_numbers.py --tex`: 2,131 numeric tokens, 0 untraceable, 0 untagged;
   `tests/test_no_pattern_kills.py` passes; all 27 pages rendered and inspected (text, tables, figures, references,
   checklist). Details: `docs/paper_tex_changes.md` ("Print-legibility pass").

## Open for the owner
- Nine pages with no slack (unchanged).
- Scratch deletion: the inventory and recommendations from 2026-10-16 are waiting for your choice of rows; nothing
  has been deleted.
- Screenshot paths you pasted are on your Mac; attach them or `scp` to `work/screenshots/` if any bug is still open.
- Appendix float pages (Table 8 alone on p. 16, Figure 9 alone on p. 19) are LaTeX float pages, not defects; say so if
  you want them packed differently.

## Operations
GPU use for this step: none. Login-node work: figure regeneration (≈ 4 min, 1.2 GB peak) and Tectonic builds.
Offloader loop and keepalive running. GitHub main = origin after this push.
