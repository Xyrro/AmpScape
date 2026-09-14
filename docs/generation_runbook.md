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
python scripts/generate.py submit --build data/v1/S --max-concurrent 400          # arrays of ≤ 400 shards; scratch guard
# finalize + validate + stream, in the sync loop (login node, HF pushes only here):
nohup scripts/slurm/v1/sync_loop.sh data/v1/S S > data/v1/S/logs/sync_loop.out 2>&1 &
```

`sync_loop.sh` every 15 min: `generate.py finalize --build … --quicklooks` (new shards only), then
`python scripts/sync_shards.py --build … --tier … --live --publish-index` — validate → split by task group →
upload → verify sha256 on the Hub → `.uploaded` marker → delete the final shard and staged files locally; the
index rows, `.ok`/`.uploaded` markers and quicklooks stay on scratch. A shard that fails verification twice gets
`.upload_failed` and the loop exits non-zero (stop rule).

## 3. Resume procedure

Everything is idempotent at the shard level: `prepare` skips shards with inputs, the array skips shards with a
final file, `finalize` skips existing finals, `sync` skips `.uploaded`. After a node failure or a cancelled array:
`python scripts/generate.py status --build data/v1/T` → `submit` again (only missing shards are queued). After a
login-node restart: relaunch `sync_loop.sh`. Nothing needs the network except tile extraction and the uploads.

## 4. Daily summary and stop rule

`python scripts/generation_log.py --builds data/v1/S data/v1/M … --since 2026-09-15` appends to
`docs/status/generation_log.md`: shards planned / solved / finalized / uploaded per tier, QC failure rate, GB
verified on the Hub, local GB, core-hours used (sacct). **Stop rule:** pause submissions and report to the owner if
the QC failure rate of any tier exceeds 1 % or any shard fails to upload twice (both are printed as TRIGGERED).

## 5. Scratch guard

`generate.py submit` refuses while `data/` holds more than 200 GB (`limits.scratch_pause_gb` in
`configs/cluster/ice.yaml`; override `--ignore-scratch-guard` only with the owner's approval). Scratch cap is 300 GB.

## 6. On completion

Assemble the final per-tier indexes and split lists (`publish_index`), the Croissant file and the dataset card
(remove the in-progress notice), push the tuned baseline results, mint the Zenodo DOI (Phase 12).
