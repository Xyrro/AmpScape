# Scratch cleanup, 2026-10-26

Owner approval (2026-10-26): "you can delete the safe ones, but make sure they can 100 percent reproducable anytime
when i need them". Scratch went from 296.8 GB to 191.7 GB of the 300 GB quota. Every deleted item was first shown to
be recoverable byte for byte (or rebuilt and compared). The check reports are in `work/delete_check/` (not tracked).

## Deleted and how each was checked

| Item | Size | Check before deletion | Result |
|---|---|---|---|
| `data/hfcache/data/XL/T4` (staged group) | 60.9 GB | sha256 of every shard against the Hub LFS hash at tag `v1.0.2` (Slurm job 6601100, `scripts/maintenance/verify_against_hub.py`) | 667 of 667 identical |
| `data/hfcache/data/XXL/T1` (staged group) | 21.4 GB | same | 400 of 400 identical |
| `data/hfcache/data/XXL/T4` (staged group) | 22.2 GB | same | 400 of 400 identical |
| `work/verify/hub_mirror` (2026-10-15 mirror of `aux/` results) | 3.1 GB | sha256 / git blob sha1 of every file against the Hub at `main`; files that differ checked at the last commit before the mirror (`scripts/maintenance/verify_mirror_history.py`) | 4,617 identical at `main`; the other 65 (L block-size and L reference results replaced on 2026-10-22) identical at commit `01c5afa0a2027687566277e098c9d34b21b617b0` |
| `.hf_cache/hub`, `.hf_cache/hub_test`, `.hf_cache/xet` (download cache) | 5.4 GB | every cached snapshot commit (698) still exists in the Hub history | 698 of 698 present |
| `paper/figdata` | 0.5 GB | rebuilt from the Hub into a separate directory with nothing staged locally (job 6601268), compared array by array (`scripts/maintenance/compare_figdata.py`) | 13 files, 0 differences (manifest build timestamp ignored) |

The staged groups were removed with `stage_data.py evict`, which also removes their markers under
`data/hfcache/staged/`, so the GPU driver re-stages them when a job needs them. `data/hfcache/{index,splits,stats}`
were kept. The Hugging Face login token (`.hf_cache/token`, `.hf_cache/stored_tokens`) was kept.

## Not deleted

- `work/probe` (4.6 GB): two 2-epoch FNO T1 L timing probes (jobs 6243138/6243139). Their timings are recorded in
  `DECISIONS.md` (2026-10-13) and `docs/tables/gpu_probe.md`, but the checkpoints are not on the Hub and GPU training
  is not bit-reproducible, so they fail the owner's condition.
- `runs/full/**/best.pt` (30 GB), `data/sources` (20 GB), `aux/review_round2/` (kept until submission): not approved.

## How to restore

```bash
source scripts/env.sh
# staged groups (pinned to v1.0.2; run on the login node, 1-2 workers, page-cache sweeper built in)
python scripts/slurm/gpu/stage_data.py stage --tier XL  --group T4
python scripts/slurm/gpu/stage_data.py stage --tier XXL --group T1
python scripts/slurm/gpu/stage_data.py stage --tier XXL --group T4
# paper figure arrays (Slurm CPU job, ~2 min, ~6 GB fetched to node-local disk)
sbatch scripts/maintenance/figdata_rebuild_check.sbatch   # writes work/delete_check/figdata_rebuild
#   or directly: python scripts/paper_figdata.py --out paper/figdata
# verification mirror: same allow-patterns as the original mirror
python -c "from huggingface_hub import snapshot_download as s; s('Xirro/AmpScape', repo_type='dataset', \
  local_dir='work/verify/hub_mirror', allow_patterns=['aux/results/runs_full/**/*.json','aux/results/runs_full/**/*.md',\
  'aux/results/runs_full/**/*.csv','aux/results/runs_full/**/*.log','aux/results/runs_full/**/*.txt',\
  'aux/results/predictions/**/*.json','aux/results/predictions/**/*.md','aux/t4_bs1_reference/**/*.parquet',\
  'aux/t4_bs1_reference/**/*.md','aux/t4_bs1_reference/**/*.json','aux/t4_blocksize_baselines/**/*.parquet',\
  'aux/t4_blocksize_baselines/**/*.md','aux/t4_blocksize_baselines/**/*.json','aux/wp7/*.parquet','aux/wp7/*.md',\
  'aux/wp7/*.json'])"
#   add revision='01c5afa0a2027687566277e098c9d34b21b617b0' for the exact 2026-10-15 state
# .hf_cache: refills itself on the next download
```
