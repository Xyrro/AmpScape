# v1.0 generation runbook (ICE, streaming upload to the public `Xirro/AmpScape`)

Owner decisions 2026-09-14: v1.0 runs on ICE; budget 13 000 core-hours incl. contingency (the 500 CPU-hour gate is
lifted for this run; the 20 GPU-hour gate stays); finished shards stream to the public Hub repo; tier S launches
first after the freeze checklist is approved.

## 0. Frozen inputs

| item | value |
|---|---|
| pipeline | git tag `v1.0-pipeline` (recorded in every sample as `pipeline_tag` + `pipeline_git_sha`) |
| design | `configs/datasets/v1_0.yaml` (recommended ladder S 100 000 / M 50 000 / L 20 000 / XL 4 000 / XXL 400; 60/40 synthetic/real; fidelity Omniscape blocks) |
| splits | frozen cell assignment `configs/splits/cell_assignment_v1.json` (seed 20260906); tile-level region hold-out; no XXL parent regions |
| tiles | `data/tiles/v1` (v1.0 tile streams S/M/L/XL/XXL + `XXL_strict`, prefix-extracted, 5 resistance rasters per tile) |
| solver | CHOLMOD reference, CG baselines on test/OOD samples, QC threshold 1e-6 |
| planner | `scripts/plan_v1.py --tier T --n N --out data/v1/T --shard-size S` (prefix streams; the dev subset is the first 3 000 S / 500 M) |

## 1. Cost and array design (512 concurrent cores; ≤ 400 tasks per array under the 500-job submit limit)

Per-landscape wall time (dev measurements for S/M, Phase-5 scaling for L–XXL; single core except XL/XXL):

| tier | landscapes | s / landscape | shard size | shard wall | cpus | shards | concurrent jobs | waves | tier core-hours | tier storage |
|---|---|---|---|---|---|---|---|---|---|---|
| S | 100 000 | 55 | 200 | ≈ 3.2 h | 1 | 500 | 400 + 100 | 2 | ≈ 1 550 | 110 GB |
| M | 50 000 | 112 | 100 | ≈ 3.2 h | 1 | 500 | 400 + 100 | 2 | ≈ 1 600 | 200 GB |
| L | 20 000 | 590 | 20 | ≈ 3.4 h | 1 | 1 000 | 400 | 3 | ≈ 3 300 | 260 GB |
| XL | 4 000 | 1 930 | 6 | ≈ 3.3 h | 4 | 667 | 128 | 6 | ≈ 2 150 | 200 GB |
| XXL | 400 | 10 600 | 1 | ≈ 3 h | 8 (test: 20 GB) | 400 | 64 | 7 | ≈ 1 200 | 70 GB |
| total | 174 400 | | | | | 3 067 | | | **≈ 9 800 (+15 % overhead ≈ 11 300)** | ≈ 840 GB |

Walltime 04:00:00 everywhere (shard sizes chosen for ≈ 3.2 h so that one Julia start-up per shard is amortised and
a 4 h limit still holds). Submission order **S → M → L → XL → XXL**; the next tier starts when the previous tier's
final wave is queued. The S tier alone (110 GB) fits under the 200 GB scratch guard; from M on, waves are sized so
that `finalized-but-not-uploaded` never exceeds ≈ 80 GB (the sync loop drains ≈ 100 GB/h).

## 2. Commands (per tier, on the login node)

```bash
source scripts/env.sh
python scripts/plan_v1.py --tier S --n 100000 --out data/v1/S --shard-size 200 --dataset-version 1.0.0
sbatch scripts/slurm/dev/prepare_dev.sh data/v1/S                 # inputs (no network needed after tile extraction)
python scripts/generate.py submit --build data/v1/S --shards 0-399 --max-concurrent 400   # then --shards 400-499; scratch guard
# finalize + validate + stream, in the sync loop (login node, HF pushes only here):
setsid nohup scripts/slurm/v1/sync_loop.sh data/v1/S S >/dev/null 2>&1 < /dev/null &   # see §2.1
```

Finalize (merge, QC, schema validation, quicklooks) runs on the compute node at the end of every array task
(`solve_shard.sbatch`), or through `scripts/slurm/v1/finalize_range.sh` for shards solved before that change (tier S).
`sync_loop.sh` every 15 min runs only `python scripts/sync_shards.py --build … --tier … --live --publish-index` — validate → split by task group →
upload → verify sha256 on the Hub → `.uploaded` marker → delete the final shard and staged files locally; the
index rows, `.ok`/`.uploaded` markers and quicklooks stay on scratch. A shard that fails verification twice gets
`.upload_failed` and the loop exits non-zero (stop rule).

### 2.1 Sync supervisor (login node, detached from any session)

```bash
setsid nohup /storage/ice1/1/8/yxiao413/EcoFlowBench/scripts/slurm/v1/sync_loop.sh data/v1/S S >/dev/null 2>&1 < /dev/null &
```

That is the exact restart command (owner requirement): safe to run at any time — a pid lock
(`$AMPSCAPE_SCRATCH/logs/sync_S.pid`) refuses a second copy, every step is idempotent (finalize skips existing
finals, sync skips `.uploaded` shards, uploads are verified by checksum before anything is deleted). Log:
`$AMPSCAPE_SCRATCH/logs/sync.log` (one block per 15-min cycle: finalize, sync records, counts). Stop with
`kill $(cat $AMPSCAPE_SCRATCH/logs/sync_S.pid)`. Replace `S` by the tier for later tiers (one loop per tier).

## 3. Resume procedure

Everything is idempotent at the shard level: `prepare` skips shards with inputs, the array skips shards with a
final or an outputs file, `finalize` skips existing finals, `sync` skips `.uploaded`.

**Login-node reboot mid-run** (owner requirement 2): running and pending Slurm array tasks are unaffected — they are
owned by the scheduler, not by the login session. Only two things live on the login node and must be re-launched:
1. the sync supervisor — the one-line command in §2.1 (safe to repeat; the lock prevents duplicates);
2. any array **not yet submitted** (later waves / tiers): `python scripts/generate.py status --build data/v1/T`
   shows the state; `python scripts/generate.py submit --build data/v1/T --shards a-b --max-concurrent 400` queues
   only the shards that have neither a final nor an outputs file (already-solved shards are picked up by finalize).
After a compute-node failure or a cancelled array the same `submit` re-queues the missing shards. Nothing needs the
network except tile extraction and the uploads.

## 4. Daily summary and stop rule

`python scripts/generation_log.py --builds data/v1/S data/v1/M … --since 2026-09-15` appends to
`docs/status/generation_log.md`: shards planned / solved / finalized / uploaded per tier, QC failure rate, GB
verified on the Hub, local GB, core-hours used (sacct). **Stop rule:** pause submissions and report to the owner if
the QC failure rate of any tier exceeds 1 % or any shard fails to upload twice (both are printed as TRIGGERED).

## 5. Scratch budget and submission waves (revised 2026-09-16 after the tier-S quota incident)

Measured on tier S: a finalized shard of 200 landscapes is ≈ 130 MB; its raw intermediates are ≈ 245 MB (inputs
37 MB + outputs 208 MB) and exist from `prepare` until the finalize inside the array task deletes them; the
validated final exists until the sync loop has verified it on the Hub (one commit per shard, five task-group files;
measured throughput ≈ 25–30 shards/h ≈ 3.5 GB/h for S). Scratch is 300 GB; the fixed footprint (sources 19 GB,
v1.0 tiles 36 GB, dev/mini/published builds 22 GB, environments, Julia depot) is ≈ 90 GB, so the generation may
use **≤ 200 GB** in flight:

    in_flight = (shards prepared but not yet finalized) × (inputs + outputs)
              + (finalized, not yet uploaded) × final_size            must stay < 200 GB − fixed ≈ 110 GB

| tier | landscapes / shard | final / shard | intermediates / shard | max shards in flight (110 GB) | wave size | shards per tier |
|---|---|---|---|---|---|---|
| S | 200 | 0.13 GB | 0.25 GB | ≈ 290 (all raw) → 400 if raw is deleted at finalize | **200** | 500 |
| M | 100 | 0.36 GB | 0.7 GB | ≈ 100 | **80** | 500 |
| L | 20 | 0.26 GB | 0.5 GB | ≈ 140 | **100** | 1 000 |
| XL | 6 | 0.30 GB | 0.6 GB | ≈ 120 | **100** | 667 |
| XXL | 1 | 0.17 GB | 0.35 GB | ≈ 200 | **64** | 400 |

Rules: (1) `prepare` only the next wave (inputs are 15–20 % of the intermediates but add up: 100 000 S inputs were
18 GB); (2) submit the next wave only when `uploaded ≥ submitted − wave_size` (i.e. the upload backlog is below one
wave) and `du -sb data/` < 200 GB — `generate.py submit` enforces the second; (3) the finalize inside the array task
deletes the raw inputs/outputs of every validated shard, so a wave's intermediates vanish as it completes; (4) the
sync loop never writes more than one shard's temporary split at a time and removes it in every case.

What went wrong on tier S: all 500 shards ran at once (the scheduler granted 500 cores), finalize ran in a separate
array after the solves, and the sync only deleted the *final* after upload — so 500 × (245 + 130) MB ≈ 190 GB of
S data plus the fixed footprint filled the 300 GB quota; the split of shard 12 was truncated by the full disk and the
loop retried it every 15 min without counting the failure. Fixed as above (owner items 1–5).

## 6. Scratch guard

`generate.py submit` refuses while `data/` holds more than 200 GB (`limits.scratch_pause_gb` in
`configs/cluster/ice.yaml`; override `--ignore-scratch-guard` only with the owner's approval). Scratch cap is 300 GB.

## 7. On completion

Assemble the final per-tier indexes and split lists (`publish_index`), the Croissant file and the dataset card
(remove the in-progress notice), push the tuned baseline results, mint the Zenodo DOI (Phase 12).
