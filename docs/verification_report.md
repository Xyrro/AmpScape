# Verification pass before the paper (owner request 2026-10-15; run 2026-10-15/16)

Scope (owner): "Treat it as a reviewer would: nothing from this working tree, only GitHub and the Hub." Every check below
reads the GitHub repository (`Xyrro/AmpScape`, tag `v1.0.2` or `main` at the commit named) and the Hub dataset
(`Xirro/AmpScape`); the working tree supplied only the HF read token and the Slurm job scripts under `scripts/verify/`.
Logs: `work/verify/` (untracked, scratch); JSON results named per item.

| item | result | fixes applied |
|---|---|---|
| 1. Fresh clone at the tagged release on a compute node, lockfile env, `lite` loader, tests, `evaluate.py` on a published baseline | **PASS** at `v1.0.2` (8/8 metrics match `docs/tables/baselines_full.md` at the printed precision; 198 tests pass, 13 skipped) and at `main` (440 pass, 14 skipped); three steps need undocumented knowledge (below) | loader downloaded the whole tier × task group regardless of `subset` (30 GB for "lite S/T1" at the tag) → fixed on `main` (1.9 GB) with a test; README quickstart sizes corrected |
| 2. Regenerate every paper table and figure from Hub-published results only, diff against the committed versions | **PASS** — every table and figure byte-identical after one fix | the acceleration evaluations (`eval_accel_*`) of the 12 voltage-head runs had never been published → pushed, added to the offloader's include list |
| 3. Cross-check every number in `paper/draft.md` against its tagged source file | **PASS** — 1,508 numeric tokens, 0 untraceable, 0 untagged (`scripts/verify/check_draft_numbers.py`) | 29 initial mismatches fixed in the draft (rounded or derived values replaced by the source values or tagged `[derived]`) |
| 4. Dataset card, Croissant and CITATION.cff against the index | **PASS** — 97/97 checks after fixes (`scripts/verify/audit_metadata.py`) | `croissant.json` `datePublished` 2026-09-25 (local date) → 2026-09-26 (UTC date of the tag; re-validated, 0 errors / 0 warnings, uploaded); card: `aux/` size 20.5 GB was the v1.0 figure (605 GB today) → dated statement; viewer-config comment corrected; Hub revisions stated (`v1.0`, `v1.0.2`; `v1.0.1` is a GitHub tag only) |
| 5. Full Hub audit, five tiers and `aux/` | tiers S, XXL **PASS** (0 discrepancies); M, L, XL: running (12-h jobs, results appended below when done); `aux/`: 9,443 files / 605 GB listed, 8,243 covered by sha256 push records (5 stale records refreshed), 1,066 unrecorded files hashed from their local sources (0 mismatches), 128 files without local source downloaded and verified (second pass running); **one integrity defect found** (below) | stale push records of `aux/test_ood_published/index*` refreshed; stale Hub copy of `generation_postmortem.md` re-pushed; the defective file is being regenerated |

## 1. Reviewer path on a compute node (`scripts/verify/fresh_clone_verify.sbatch`)

Job 6286607 (tag `v1.0.2`, 18 min on a `coc-cpu` node, 48 GB RAM, node-local disk) and job 6286685 (`main` at
6ff0bf2; a second `main` run with the whole `lite` subset is 6286935). Steps and outcomes:

1. `git clone git@github.com:Xyrro/AmpScape.git && git checkout v1.0.2` — ok. **Undocumented:** the README shows the
   https URL, which requires the repository to be public; the clone used ssh.
2. Fresh environment: `uv python install 3.11 && uv sync --extra dev` (documented) — ok, torch imports.
   **Undocumented:** how to obtain `uv` itself (the job bootstrapped it with `python3 -m venv … && pip install uv`).
3. **Undocumented:** the dataset is private, so a reviewer needs an HF read token (`HF_HOME/token`); nothing in the
   README says so.
4. `uv run pytest -q tests`: `v1.0.2` 198 passed / 13 skipped (skips need pilot tiles, smoke shards, network);
   `main` 440 passed / 14 skipped.
5. Documented loader `load_from_hub("T1", "S", split="train", subset="lite")`: at `v1.0.2` it returned 6,050 train
   samples but **downloaded the entire S/T1 group (30 GB, 500 shards, 581 s)** — the `subset` argument only filtered the
   index after the download, so the README's "mini ≈ 0.6 GB" was not true of the download. Fixed on `main`
   (`ampscape/data/dataset.py`: the index names the subset's shards and only those are fetched; `tests/test_data_loader.py`):
   the same call now downloads 1.9 GB (40 shards) in 39 s. The whole-`lite` loop (S, M, L × five task groups) in job
   6286685 was cut short by a Hub CDN error (`504 Gateway Time-out` from the xet backend after 79 shards / 4.4 GB); it is
   re-run with the xet backend disabled in job 6286935.
6. `scripts/evaluate.py` at `v1.0.2` on the published predictions of `unet_T1_S_s1` (`aux/results/runs_full/unet_T1_S_s1/predictions/hfcache_S_test_id`, 274 MB) against the S/T1 group downloaded from the Hub: 9,850 rows in 434 s; every printed metric equals the `docs/tables/baselines_full.md` row of `origin/main` at three decimals (MAE 0.042, rel-L2 0.111, top-5 % IoU 0.857, pinch recall 0.914, Spearman 0.993, corridor Dice 0.938, SSIM 0.989, median speed-up 738.585). The evaluation code of `v1.0.2` therefore reproduces the paper's S rows; the later harness changes (T4 reference branch, packed loader) do not alter them.

Evaluation-code drift since `v1.0.2` (for the record): `ampscape/eval/harness.py` (+37 lines, T4 block-1 reference
branch), `ampscape/metrics/acceleration.py` (+7), `ampscape/data/dataset.py` (+28) and the new `ampscape/data/packed.py`.
The paper should cite a code tag that includes the baseline scripts; `v1.0.2` predates them (owner decision pending:
tag the paper commit).

## 2. Regeneration from the Hub only (`scripts/verify/mirror_hub_results.py`, worktree `work/verify/tree`)

Job 6286555 mirrored every result file the generators read — 4,634 files, 3.02 GB: `aux/results/runs_full/**`
(results, transfer results, T4 reference evaluations, configs, logs; no predictions or checkpoints),
`aux/results/predictions/**`, `aux/t4_bs1_reference/**`, `aux/t4_blocksize_baselines/**` and `aux/wp7/*.parquet`.
A clean worktree at `main` 6ff0bf2 had `runs/full`, `data/predictions` and `aux/` replaced by symlinks into the mirror
(two layout differences had to be mapped by hand: the Hub stores `aux/t4_bs1_reference/{M,L}` and
`aux/t4_blocksize_baselines/{M,L}/<build>` where the scripts expect `{M,L}_bs1` and `<tier>_<build>`), then
`tuning_select.py`, `tuning_decisions.py`, `paper_figures.py --skip-stats`, `tuning_effect.py` and
`acceleration_table.py` were run. Result: **every table and figure byte-identical** to the committed versions
(`docs/tables/*.md`, `paper/tables/*.md`, `paper/baselines.md`, `paper/figures/*.png`) except
`docs/tables/acceleration.md`, which came out empty because the `eval_accel_test_id/` and `eval_accel_test_ood/`
directories of the 12 voltage-head runs had never been pushed (the offloader's include list lacked them). Fix: pushed
(48 files), include list extended; after re-mirroring, `acceleration.md` is byte-identical too.

## 3. Numbers in `paper/draft.md` (`scripts/verify/check_draft_numbers.py`)

Every prose segment and every table row in the draft carries a source tag (`[path; path]`); the script extracts every
numeric token (exempting reference numbers, section/figure/table numbers, tiers, versions, dates and integers below 20)
and requires the same digits in one of the tagged files. Final run: 1,508 tokens checked, 0 not found, 0 untagged. The
29 initial failures were rounded values ("≈ 11,000×" for 11077×, "3.28 ms" for 0.00328 s), derived values
(0.463 − 0.458 = 0.005), a caption tag the parser could not read, and quotations from the related-work section without a
tag; each was replaced by the source value or tagged. Numbers that are arithmetic on tagged numbers (the predicted
1 − 64/128 = 0.50) carry `[derived: …]`.

## 4. Card, Croissant, CITATION.cff against the index (`scripts/verify/audit_metadata.py`, job 6286910)

From the Hub only (`index/<tier>.parquet`, `croissant.json`, `README.md`, the repository tree) and the GitHub-tracked
card and `CITATION.cff`: per-tier landscapes, configuration rows, synthetic/real split, QC-failing rows, GB on the Hub
and the totals all equal the card (174,400 / 920,372 / 25 / 1,157.4 GB); the per-tier split assignments equal the
union split lists after removing the 24 QC-failing landscapes; the subsets hold exactly 600 S (mini), 8,000 S + 2,400 M
+ 800 L (lite, 25.9 GB on the Hub, 517 files) and 20,000 S + 10,000 M + 5,000 L (core, 115.5 GB) landscapes; every
Croissant FileSet's `includes` pattern matches the Hub files and the index (25 tier × group sets, 3 subset sets, 5 index
sets); licence (CC BY 4.0) and version (1.0.2) agree across card, Croissant and CITATION. Fixed: Croissant
`datePublished` (2026-09-25 → 2026-09-26, the UTC date of the tag, matching card and CITATION), the card's `aux/` size
and viewer-config comment, and the statement of which revisions exist on the Hub. Final run 0 failing of 97.

## 5. Full Hub audit

**Tiers** (`scripts/audit_tier.py`, one 12-h job per tier, 4 workers; every shard downloaded, sha256 against the local
upload record, sample-id set against the plan, every planned configuration present, index rows against file contents):
S — 500 shards, 2,500 Hub files, 0 discrepancies (job 6286544); XXL — 400 shards, 1,708 Hub files, 0 discrepancies
(job 6286548); M, L, XL — jobs 6286545–6286547, results appended below. The previous audits (2026-09, `audit_<tier>_2026-09.json`) are kept beside the new ones.

**`aux/`** (`scripts/verify/audit_aux_hub.py`, `audit_aux_local_sha.py`, `audit_aux_download.py`): 9,443 files, 605.49 GB.
(a) 8,243 files have a sha256 push record; 3,294 of them carry an LFS sha256 on the Hub and all but 5 matched; the 5
(`aux/test_ood_published/index*.parquet`) matched the *current* local files, i.e. the records were stale, and were
refreshed by a no-op re-push. (b) 1,200 files had no record: 1,066 were hashed from their local sources with 0
mismatches (17 GB, `aux/t1_pair1`, `aux/dev/S`, block-size tables, docs copies); 128 have no local source any more
(the `aux/dev` builds were deleted after upload; two prediction files) and were downloaded and hashed in a second pass
(job 6286934, results below); 6 small non-LFS Markdown copies were compared byte-wise — `aux/generation_postmortem.md`
was stale (9,584 vs 9,697 bytes) and was re-pushed.
(c) **Integrity defect:** `aux/results/runs_full/gnn_T1_L_s3_t2/predictions/hfcache_XXL_test_id/predictions.h5` — the
Hub lists 854,407,780 bytes while the download yields 931,457,226 bytes ("file size mismatch"), and no push record
exists: the local file (931,457,226 bytes) was deleted for scratch quota at 16:47Z before the offloader's 16:54Z push
of that split's metrics, so the Hub copy is a partial earlier upload. The metrics of that split (`results_transfer.json`,
`eval_transfer/`) were computed from the complete local file and are unaffected. Fix in progress: the XXL test_id
predictions of `gnn_T1_L_s3_t2` are regenerated with `scripts/transfer_eval.py` (≈ 0.5 GPU-h) and re-pushed with a
record; the regenerated metrics must equal the published ones. `aux/results/runs_full/gnn_T4_L_s2/predictions/hfcache_XL_test_id/predictions.h5` is the second unrecorded prediction file and is verified in the same pass.

## Findings that need an owner decision

1. **Code tag for the paper.** `v1.0.2` reproduces the S rows but predates the baseline scripts, the T4 reference
   branch and the leaderboard tooling; the paper should cite a tag at the paper commit (proposal: `v1.1.0-paper`).
2. **Private dataset, ssh clone, `uv` bootstrap** are the three steps a reviewer cannot take from the README alone; the
   README gains a "Reviewer access" paragraph once the owner decides when the Hub repository becomes public.
3. **Hub layout of the aux evaluation sets** differs from the local names the scripts expect
   (`aux/t4_bs1_reference/M` vs `M_bs1`, `aux/t4_blocksize_baselines/M/M_b7_ca1` vs `M_b7_ca1`); either the scripts
   accept both or `docs/aux_layout.md` documents the mapping (done in this report; code unchanged).
