# GPU-type and input-pipeline probes — 2026-10-13 (`scripts/slurm/gpu/gpu_probe.sbatch`, logs in `logs/probe/`)

One cold epoch of the official config (T4, M tier, batch 8, seed 1) on the staged Hub cache; `epoch_s` from log.csv.
Queue wait = submit → start. All jobs under QoS coc-ice except the two coe-gpu rows (coe-ice).

| model | GPU (partition) | loader | workers | wait | epoch 1 | epoch 2 | note |
|---|---|---|---|---|---|---|---|
| U-Net | L40S (coc-gpu) | HDF5 | 6 | 2 s | 170 s | | baseline (official runs: 122 s warm) |
| U-Net | H100 (coe-gpu) | HDF5 | 6 | 3 s | 154 s | | |
| U-Net | H200 (ice-gpu) | HDF5 | 6 | 5 s | 169 s | | |
| FNO | L40S (coc-gpu) | HDF5 | 6 | 2 s | 208 s | | baseline |
| FNO | H100 (ice-gpu) | HDF5 | 6 | 4 s | 203 s | | |
| FNO | H200 (coe-gpu) | HDF5 | 6 | 3 s | 197 s | | |
| U-Net | L40S | HDF5 | 12 | 1 s | 94 s | | loader CPU-bound |
| U-Net | H200 | HDF5 | 12 | 27 s | 100 s | | |
| FNO | H200 | HDF5 | 12 | 27 s | 116 s | | |
| U-Net | L40S | (a) local NVMe copy of the group, HDF5 | 12 | 211 s | 93 s | | copy 51 GB in 26 s; no gain |
| U-Net | L40S | (c) packed memmaps | 12 | 159 s | 88 s | 87 s | pack 41 GB in 95 s |
| U-Net | L40S | (c) packed memmaps | 6 | 1 s | 88 s | 87 s | workers no longer matter |
| U-Net | H200 | (c) packed memmaps | 12 | 473 s | 57 s | 56 s | pack in 57 s |
| FNO | L40S | (c) packed memmaps | 12 | 234 s | 185 s | 183 s | FNO is compute-bound on L40S |
| FNO | H200 | (c) packed memmaps | 12 | 193 s | 61 s | 59 s | |
| U-Net | L40S | (b) batch 16, prefetch 4, HDF5 | 12 | 1 s | 108 s | | information only; the batch is part of the official config |
| U-Net | L40S | (c) packed, RNG-preserving re-run | 6 | 1 s | 87 s | | losses 0.07356 / 0.02498 = the HDF5 run's exactly |

L tier (T1, batch 4, 8 workers; the group fetched from the Hub straight to the node's NVMe in 1 122 s — 79 GB — then packed):

| model | GPU | loader | epoch | official L40S/HDF5 run (log.csv) | speed-up |
|---|---|---|---|---|---|
| U-Net | H100 | packed (64 GB in 85 s) | 115 s | 178 s | 1.55× |
| FNO | H100 | packed (77 GB in 101 s) | 88 s | 322 s | 3.7× |

The matching H200 L probe waited 67 min on "Priority" (2 free H200 GPUs) and was cancelled; H100 had ≥ 60 free GPUs
all morning, so the driver's pool order is H100 → H200 → L40S → A100.

Node facts (`logs/probe/nodeinfo_*.out`): every GPU node has a local NVMe RAID at `/tmp` (= `/scratch`, 11–28 TB, ≥ 96 %
free), 755 GB–2 TB RAM, 64 cores (8 per GPU). The cu126 torch 2.14 wheel runs on H100/H200 (sm 9.0) under driver
615.71 (CUDA 13.4).

## Production re-runs (phase 14, tuned configs, 30 epochs) — measured on the real jobs, 2026-10-13

| run | before: L40S, HDF5 (6 workers) | after: packed, H100/H200 | speed-up |
|---|---|---|---|
| FNO w48 T1 M | 361–371 s/epoch (T3/T4 runs, 3.0–3.1 GPU-h) | 84 s/epoch on H200 (0.73 GPU-h) | 4.3× |
| U-Net w64 T1/T3 M | 254 s/epoch (T4 run, 2.1 GPU-h) | 108–111 s/epoch on H100 (0.91–0.94 GPU-h) | 2.3× |
| ViT p16g16 T1/T4 M | 61–120 s/epoch on L40S (0.5–1.0 GPU-h) | (not re-run on H100 yet) | — |

The "before" rows are the same configs on legs submitted before the switch (M/T4 and M/T3 legs ran out on L40S with the
HDF5 loader); the "after" rows are the M/T1 and M/T3 legs submitted after it.
