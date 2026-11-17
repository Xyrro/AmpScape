# Offsite audit, 2026-11-16: what exists only on scratch

Owner, 2026-11-16: "check if there anything can not be reproducable and affects writing the paper? since [cluster] scratch
may be cleared after a certain time, we wanna make sure we saved everything. on github and hugging face".

## Method

`scripts/maintenance/audit_offsite.py` (Slurm job 7122941, 10 min on 8 cores; read-only) walked the scratch working copy.
It skipped git-tracked files (the working copy was clean and `main` was pushed) and the environments, Julia depot,
tools and download caches (rebuilt from `uv.lock`, `julia/AmpScapeSolve.jl/Manifest.toml`, `scripts/setup_gdal_env.sh`).
It hashed every other file and looked the content up anywhere in `Xirro/AmpScape` at `main` (24,155 files): sha256 for
LFS/xet files, the git blob sha1 otherwise. Report: `work/offsite_audit/report.json` on scratch (untracked).

| | files | GB |
|---|---|---|
| checked (untracked or ignored) | 50,616 | 42.95 |
| content on the Hub | 5,644 | 6.09 |
| **content neither in git nor on the Hub** | **44,972** | **36.86** |

## The paper itself is safe

- `paper/neurips/main.tex` compiles from git alone: all 39 `\input`/`\includegraphics` targets, `references.bib` and the
  style file are tracked.
- Every table's `% src:` file (`docs/tables/*.md`, `paper/tables/*.md`, `docs/dataset_card.md`, `docs/licenses.md`) is
  tracked, so every number in the paper is in git.
- The inputs of `scripts/paper_figures.py` are on the Hub: `aux/results/runs_full/<run>/{results*.json, log.csv,
  predictions/*/eval_*/results.json}` and `aux/wp7/demo_results.parquet`. After a purge they are fetched from there
  (not from scratch). Checkpoints, predictions and the dataset are on the Hub (cleanups of 2026-10-26 and 2026-11-14).
- `gnn_T4_L_s1` XXL evaluation: scratch holds a second GPU evaluation (14:33 UTC on 2026-10-04) of the one on the Hub
  (14:02); metrics differ in the fifth significant digit (rel-L2 0.748210 vs 0.748216). The paper's scale-transfer
  rows come from `results_transfer.json`, which is on the Hub, so no reported number depends on the scratch copy.

## Gaps closed in git (this audit)

Inputs of paper figures, tables or claims that were only on scratch, 4.5 MB in all (commit a7170f3):

| File | Why it was missing | Paper use |
|---|---|---|
| `docs/tables/review_round3_raw/*.parquet` (7) | `*.parquet` in `.gitignore`; the folder's JSON files were tracked | T4 Pareto heuristic (Fig. T4 error vs cost), source-OOD table, L reference subsets |
| `docs/tables/nodata_sample.parquet` | same | NoData figure (synthetic side) |
| `docs/provenance/tiles_v1.0.parquet` (from `data/tiles/v1.0/tiles.parquet`) | under `data/` | biome/realm table and NoData figure; the Hub index has no biome or QC columns |
| `docs/provenance/sources_manifest.json` (from `data/sources/manifest.json`) | under `data/` | full sha256 and URL of the 21 source downloads (`docs/licenses.md` lists 16-digit prefixes) |
| `docs/provenance/repro_{S,M}_compare.json` (from `data/repro/`) | under `data/` | evidence for "regeneration is bitwise reproducible on one CPU model" |

`.gitignore` now exempts `docs/tables/**/*.parquet` and `docs/provenance/*.parquet`.

## Proposed Hub upload (needs owner approval: Hub pushes are gated; the repo is public)

Raw records behind tables that are already in git. The tables survive a purge, but re-deriving them would need
recomputation (CPU solver builds, GPU inference) or would be impossible (precision-pass records, build logs). About
2.6 GB, under `aux/records/` (many-small-file folders as one tar each):

| Scratch | GB | What |
|---|---|---|
| `aux/review_round3/` | 1.41 | review round 3: source-OOD solver builds (0.63), decision-analysis prediction maps (0.77), PCG all-pairs, heuristic, reference, logs |
| `aux/review_round2/` (not-yet-uploaded part) | 0.11 | coarsen-×4 builds and predictions (the result JSONs are in git) |
| `aux/wp7`, `aux/scale_probe`, `aux/t4_*` non-log files | 0.16 | the 120 WP7 resistance tiles, WP7 splits/stats, top-up build manifests |
| `data/tiles/` metadata | 0.04 | tile specs, candidates, `tiles.parquet`, `resistance.parquet` of the v1/v1.0 tile plans |
| `data/v1/` build records | 0.57 | per-shard build indexes, manifests, `solve_times.parquet`, `build.json`, split files, task-log archives |
| `work/precision/` | 0.16 | precision-pass per-shard rows and reports (19,354 files) |
| `runs/full/*_voltage/**/warm_start*.json`, `gnn_T4_L_s1` XXL re-evaluation | 0.01 | per-system records behind the acceleration table; second GNN evaluation |
| `logs/` | 0.15 | generation and GPU driver logs, upload logs |

Optional, +1.1 GB: the Julia solver logs of the T4 reference and block-size builds (`aux/t4_*/*/logs/*.out`) and the
scale probe.

## Not saved, and why

| Scratch | GB | Reason |
|---|---|---|
| `data/sources/` | 20.42 | public downloads; URL and sha256 of each are now in `docs/provenance/sources_manifest.json` |
| `work/probe/` | 4.83 | two 2-epoch FNO timing probes; timings recorded in `docs/scratch_cleanup_2026-10-26.md` |
| quicklook PNGs | 1.83 | regenerated from the shards (`ampscape.solve.quicklook.shard_quicklooks`) |
| `runs/full/gnn_T4_L_s1/predictions/hfcache_XXL_test_id/predictions.h5` | 1.34 | GPU re-run of the predictions on the Hub; see above |
| smoke, calibration and verification runs, `aux/diag` | 1.24 | development checks, not reported |
| `data/repro/` rebuilt shards | 1.19 | the reproducibility rebuild itself; its comparison is in git |
| `data/v1` corrupt XXL outputs | 0.97 | failed attempts, replaced by re-solves |
| `data/hf/` and `data/v1/*/datasets--*` | 0.61 | pre-release upload staging and download-cache copies of S shards since replaced on the Hub (the staged shard checked is in none of `v1.0`, `v1.0.2`, `main`) |
| `data/builds/mini` inputs/outputs | 0.30 | merged into the mini shards on the Hub (`aux/mini`) |
| `data/tiles` rasters | 0.25 | re-extracted by `scripts/extract_tiles.py` from the tile specs (in the proposed upload) and the source layers |
| superseded evaluations and backups (`*prodtarget_wrong*`, `work/*backup*`, `work/*before*`) | 0.11 | replaced by the published versions |
| `work/lit/`, `work/release_1_0_2/`, `work/verify/`, other small `work/` notes | 0.03 | saved web pages of cited papers (the bibliography is in git), release staging and verification copies of published files |

## Is a public upload safe? (owner question, 2026-11-16)

`scripts/maintenance/scan_sensitive.py` (Slurm job 7123936, read-only) scanned the 25,271 candidate files: raw bytes,
every member of the tar archives, parquet string columns, HDF5 attributes and small string datasets. For comparison
it also scanned the 5,521 text, JSON and parquet files on scratch whose content is already public on the Hub.

| Pattern | Candidates (+ optional solver logs) | Already public on the Hub |
|---|---|---|
| HF / GitHub / AWS tokens, private keys, password or API-key words | 0 | 0 |
| e-mail addresses, owner's name | 0 | 0 |
| cluster user ID | 2,127 (+429) | 3,425 |
| scratch or home paths | 1,312 (+429) | 2,896 |
| institution domain in node hostnames | 1,374 (+429) | 1 (the generation post-mortem names institution and cluster) |
| compute-node names | 2,198 (+429) | 0 |
| Slurm account/QoS names | 2,113 (+429) | 1 |

Hits are Slurm job headers (`User ID`, `Account`, `QOS`, `Nodes`) and `host=` / `build=` lines in the logs. Licences add
no restriction: the candidates hold only derived rasters, metadata and model outputs, the same kinds the public
dataset already redistributes (`docs/licenses.md`), and no source files.

Conclusion: nothing secret; nothing that identifies the owner that is not already public (user ID, institution,
cluster and account are already named on the Hub and in the public GitHub repo). The upload would add many more
identifying lines, which matters only for double-blind anonymity. Anything pushed to the main repo stays in its
history, and that history cannot be rewritten without breaking the commit pinned by the 2026-11-14 restore manifest.
Recommended: a separate **private** Hub dataset repo for these records (a backup, not a publication), which can later
be made public or deleted as a whole.

## Private backup done (owner: "if possible, create a private repo", 2026-11-16)

- Repo `Xirro/AmpScape-records` (Hub dataset, **private**, created 2026-11-16). Nothing went to the public repo.
- `scripts/maintenance/pack_records.py` (Slurm job 7124174) packed 25,271 files (3.72 GB: the recommended set and the
  optional solver logs) into eight archives (2.07 GB), with `records/manifest.jsonl` (path, size, sha256, archive).
- `scripts/push_aux.py --repo Xirro/AmpScape-records --dest records` uploaded 11 files in one commit (`64bc96c`); every
  file's sha256 on the Hub equals the local one.
- `scripts/maintenance/restore_records.py --all --verify-only` (Slurm job 7124296) downloaded every archive back,
  extracted it and matched all 25,271 files against the manifest: **all verified**.
- Restore: `python scripts/maintenance/restore_records.py --archives <name> [--only '<glob>']` writes only missing files.
- The packed copies stay in `work/records_upload/` on scratch (2.1 GB, scratch-only duplicates).

## Public repos: credentials and identifying content (owner: "do not have any credentials or id or any sensitive content in the public repo", 2026-11-16)

GitHub (`git grep` over the tree and `git log -G` over all history; commit identities) and the Hub
(`scripts/maintenance/scan_public_hub.py`, Slurm job 7124205: all 6,087 non-HDF5 files at `main`, the smallest HDF5
file of each of 97 folder groups, all 6,614 commit messages). Identity patterns are built at run time and from the
untracked `work/identity_patterns.json`; they are not written here.

| | GitHub (tree now) | Hub (`main`) |
|---|---|---|
| tokens, keys, passwords | 0 (history too) | 0 |
| personal e-mail addresses | 0; commits use the GitHub no-reply address | 0 |
| commit messages with identifiers | — | 0 of 6,614 |
| cluster user ID, absolute scratch/home paths | 56 files (Slurm scripts, docs, status logs, `CLAUDE.md`, `scripts/env.sh`) | 3,427 JSON files under `aux/results/` (`train_root`/`root` paths) |
| institution, cluster, node names, Slurm account | ≈ 40 files | 61 of 97 HDF5 samples: every sampled dataset shard and result file carries the node hostname in `solver_stats` (written by `AmpScapeSolve.jl`), so presumably all 18,493 HDF5 files (1.77 TB); `aux/generation_postmortem.md` |
| owner's real name | `LICENSE`, `CITATION.cff` | `README.md` (BibTeX author) |

Both repos keep every earlier version in their history. Removing the content from history means rewriting it: for
GitHub a force-push (not allowed without the owner) or a new repo; for the Hub a history squash. A squash would
also remove the commits that the 2026-10-26 and 2026-11-14 restore records pin, and the `v1.0`/`v1.0.2` tags. The
cleanup options and their costs are listed in `docs/status/latest.md`; the owner decides.

This session's own additions were scrubbed: the audit tables above and the status lines name no identifiers, and the
scan scripts no longer contain identity patterns. They remain in the history of commits `c7b11dc`–`04e9d7f`, like the
earlier ones.
