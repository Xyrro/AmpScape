# Status — 2026-11-16: raw records backed up privately and verified; public repos hold no credentials but do hold identifiers

Owner: "do not have any credentials or id or any sensitive content in the public repo. yeah if possible, create a
private repo". Record: `docs/offsite_audit_2026-11-16.md`.

## Done
- **Private backup:** `Xirro/AmpScape-records` (Hub dataset, private). 25,271 scratch-only files (3.72 GB, including the
  optional solver logs) in eight archives (2.07 GB) plus a sha256 manifest, uploaded in commit `64bc96c`. Every
  archive was downloaded back and all 25,271 files matched (job 7124296). Restore with
  `scripts/maintenance/restore_records.py --archives <name>`. Nothing was added to the public repo.
- **Public repos scanned:** no tokens, keys, passwords or personal e-mail addresses in either; GitHub commits use the
  no-reply address; no identifiers in the 6,614 Hub commit messages.
- This session's own docs and scan scripts no longer name any identifier (patterns live in the untracked
  `work/identity_patterns.json`); `work/` is git-ignored.

## Identifiers already public (cleanup needs the owner's decision)
| Where | What |
|---|---|
| GitHub, ≈ 80 files (Slurm scripts, docs, status/decision logs, `CLAUDE.md`, `scripts/env.sh`) | cluster user ID, absolute scratch paths, institution, cluster, node and account names |
| GitHub `LICENSE`, `CITATION.cff`; Hub `README.md` (BibTeX) | owner's real name |
| Hub, 3,427 JSON files under `aux/results/` | absolute scratch paths with the user ID (`train_root`, `root`) |
| Hub, HDF5 `solver_stats` attribute (all 97 sampled shards / result files: presumably all 18,493 files, 1.77 TB) | compute-node hostname, which names the institution |
| Hub `aux/generation_postmortem.md` | institution, cluster, Slurm account |
| History of both repos | all of the above, in every earlier version |

## Options
- **A. Clean the current versions (recommended first step):** GitHub: scripts take paths and account from the
  environment or an untracked local config, docs use placeholders (normal commits). Hub: rewrite the path fields of the
  3,427 JSON files (≈ 3.3 GB re-upload, metrics unchanged) and the post-mortem. History still holds the old versions.
- **B. Remove from history as well:** make both current repos private (everything stays restorable with a token) and
  publish fresh public repos from the cleaned content. No force-push is needed, but the paper, Croissant and leaderboard
  URLs change. Squashing the Hub history in place instead would break the restore records' pinned commits and the
  `v1.0`/`v1.0.2` tags.
- **C. Shard hostnames:** rewrite `solver_stats` in all 18,493 HDF5 files (1.77 TB pass through compute nodes, batch by
  batch). This is a large job; I would estimate the cost before starting. Hostnames name the institution's cluster,
  not a person.
- **D. Real name:** keep it in `LICENSE`/`CITATION.cff`/card (normal for a release) or replace it with a placeholder
  during double-blind review.

## Recommendation (owner asked, 2026-11-16)
1. **A on both repos:** placeholders for the user ID, scratch paths, cluster and institution names in the current
   files. Hub: re-upload of the 3,427 JSON files (≈ 3.3 GB, numbers unchanged) and the post-mortem (Hub push: needs
   approval).
2. **D for the review period:** "Anonymous" in `LICENSE`, `CITATION.cff` and the dataset-card citation; the name returns
   at camera-ready.
3. **GitHub history:** make the current GitHub repo private and publish the cleaned code as a fresh public repo with one
   commit (code only, cheap, no force-push); links to it in the paper and card change.
4. **Leave the Hub history and the 1.8 TB of HDF5 files as they are.** A free account has 100 GB of private storage
   (huggingface.co/docs/hub/storage-limits), so the 1.8 TB dataset cannot simply go private. A squash would break
   the restore records and the `v1.0`/`v1.0.2` tags. Rewriting every file would only hide the institution, which the
   published paper names anyway. Residual: earlier card versions in the Hub history and the hostnames inside the
   HDF5 files still identify name and institution for someone who digs.
5. **Anonymity during review** is then decided by the review links (pending anonymised-link item): the paper currently
   links the Hub repo by name.

## Waiting on the owner
- Approve steps 1-3 of the recommendation (or choose otherwise among A/B/C/D).
- Other projects' caches (owner's call): `<other-project>/tmp/hf_cache` 4.0 GB, `<other-project>/data/pip-cache` 1.3 GB.
- Anonymised link for the double-blind submission; `neurips_2027.sty` swap when published.
