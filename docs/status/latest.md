# Status — 2026-11-17: public repositories cleaned (steps 1-3); name kept; steps 4-5 proposed

Owner: "ok then do the step 1-3. how should we do with 4 and 5?" and "for step 2, you can still use my name".
Record: `docs/offsite_audit_2026-11-16.md`.

## Done
- **GitHub, current files:** site settings (Slurm account, QoS, partitions, GPU pools, quota tool, scratch file system)
  moved to git-ignored `scripts/env.local.sh` / `configs/cluster/local.yaml` (`ampscape/cluster.py`, `ampscape_sbatch`);
  docs, logs and raw tables use placeholders (`scrub_identifiers.py`, rules git-ignored). Full test suite on the
  cluster through `ampscape_sbatch`: 746 passed, 6 skipped.
- **GitHub, history:** old repository private as `Xyrro/AmpScape-history`; the public `Xyrro/AmpScape` (same URL) holds
  one cleaned snapshot per release tag (`v1.0-pipeline`, `v1.0`, `v1.0.1`, `v1.0.2`) and the current tree. All five
  commits scanned: no identifiers. Both clones follow the new history (`history` remote for the old one).
- **Name:** kept as author credit in `LICENSE`, `CITATION.cff` and the dataset card (owner decision).
- **Hub, current files:** 3,427 result JSON files and the post-mortem cleaned (paths only, metrics unchanged), four
  commits, every file checked. New scan: no credentials, user ID, paths, cluster or account names in any text file.
- Future result files record relative data roots (`ampscape.cluster.portable_path`).

## What remains public (by decision)
- Compute-node hostnames (university domain) inside the HDF5 `solver_stats` attributes of the dataset files.
- Earlier versions of files in the Hub history (old result JSON with absolute paths).
- The owner's name as author credit.

## Proposal for step 4 (Hub history, HDF5 hostnames)
- Leave both. Rewriting the 1.8 TB of HDF5 files would only hide the university, which the published paper names; a
  history squash would break the restore records and the `v1.0`/`v1.0.2` tags; the free plan cannot make 1.8 TB private.
- Small forward fix (needs a go): the Julia solver records the CPU model instead of the hostname, so any future build
  carries no host names (the CPU model is what the reproducibility statement relies on).

## Proposal for step 5 (review anonymity)
- When the NeurIPS 2027 call is out, check whether the track is double-blind and how reviewers must get the data.
- If double-blind: the submitted PDF links anonymous copies instead of `Xirro/AmpScape` and the GitHub repo: the code
  through an anonymising mirror of the public repo, the data through a reviewer copy under an anonymous Hub account
  (the lite/mini subsets, harness and Croissant file, with the hostname attribute removed from those few files);
  real links return at camera-ready. Check the PDF metadata at the same time.

## Waiting on the owner
- Go / no-go on the solver hostname change (step 4) and on preparing the reviewer copy when the call is out (step 5).
- Other projects' caches (owner's call); `neurips_2027.sty` swap when published.
- Scratch-only temporary copies that can go when convenient: `work/records_upload` (2.1 GB, in the private repo) and
  `work/hub_scrub/staging` (3.3 GB, now on the Hub).
