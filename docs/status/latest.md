# Status — 2026-10-16 02:00Z: leaderboard live, median rel-L2 in every main table, paper/draft.md assembled, verification pass complete (docs/verification_report.md)

## Owner requests of 2026-10-15, both done
1. **Leaderboard pushed** to `Xirro/AmpScape` under `aux/leaderboard/` (results.jsonl + README; official baselines as
   the first entries: in-tier S/M/L, zero-shot XL/XXL, T4 block-1 rows at M and L); the submission format is on the
   dataset card; `docs/submission.md` names the live location.
2. **Median rel-L2** next to the mean in every main results table (baselines, OOD, scale transfer, T4 Pareto, tuning
   effect, all-splits table), with one note in the metrics section.
3. **`paper/draft.md` exists** (commit 0a1d0d0, refined since): outline order, refreshed results and discussion with
   the tuned configurations, the per-task selection rule, the GNN L result, MgNO rows, the acceleration table and the
   derivation appendix; appendix with the full tables, fidelity, precision pass, licences, CLI and dataset statistics.
   Every number carries a source tag and `scripts/verify/check_draft_numbers.py` finds all 1,508 numeric tokens in
   their files. Main text ≈ 5,800 words plus six tables — above the 9-page target; a final cut is the next pass.

## Verification pass (owner request, as a reviewer: GitHub and Hub only) — `docs/verification_report.md`
| item | result |
|---|---|
| 1 fresh clone at `v1.0.2` on a compute node, lockfile env, `lite` loader, tests, `evaluate.py` on a published baseline | PASS (8/8 metrics match at printed precision; 198 tests pass); also at `main` (440 tests; whole `lite` = 517 shards / 25 GB). Undocumented: `uv` bootstrap, HF read token (private dataset), ssh clone |
| 2 regenerate every table/figure from the Hub only | PASS — byte-identical after publishing the acceleration evaluations that had never been pushed |
| 3 every number in the draft traced to its source file | PASS — 1,508 tokens, 0 untraceable |
| 4 card / Croissant / CITATION vs the index | PASS — 97/97 after fixes (Croissant date, `aux/` size, viewer-config note, Hub revisions stated) |
| 5 full Hub audit | tiers S, XXL, XL clean; M and L: first pass flagged 19 / 12 shards, all Hub CDN transfer errors with every sha256 matching, re-audit with the xet backend disabled clean → all five tiers PASS (3,067 shards, 14,798 files, 0 discrepancies). `aux/`: 9,443 files / 605 GB — two defective prediction files found and repaired (one had wrong size metadata on complete content, one was corrupt and was regenerated on a GPU; metrics unchanged); root cause fixed in the offloader |

Fixes committed: `load_from_hub` downloads only the subset's shards (it fetched the whole tier × group before: 30 GB
for "lite S/T1" at the tag, 1.9 GB now; test); acceleration evaluations published and in the offloader include list;
offloader ships only in-tier predictions with the whole-run push (test); Croissant `datePublished` = UTC tag date;
card statements corrected and re-pushed; stale push records and a stale doc copy refreshed; derivation appendix
updated to the current numbers; final GPU total 701.5 GPU-h / 773 jobs in `docs/tables/gpu_usage.md`.

## Owner decisions needed
- **Code tag for the paper** (`v1.0.2` predates the baseline scripts and the T4 reference branch; proposal `v1.1.0-paper`).
- **Reviewer access**: when the Hub repository becomes public; until then the README should say a read token is needed.
- **Draft length**: cut from ≈ 5,800 to ≈ 4,800 words of main text (candidates: Section 2, 4.1, 7.2 prose, Table 5 rows).

## Operations
No training queued; GPU use for the verification 1.0 GPU-h (two regeneration legs). Scratch ≈ 230 GB with XL/T4 and
XXL/T1 staged (evictable). Offloader loop and keepalive running. GitHub main = origin.
