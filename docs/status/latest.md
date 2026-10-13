# Status — 2026-10-13 08:20Z: GPU policy check and probes; input pipeline fixed (packed node-local items, 2–3.5× per epoch); driver routes to H200/H100 first; plan reordered GNN-last

## Policy check (owner's question)
- QoS `coc-ice`: MaxSubmitPU 50, MaxTRESRunMinsPU gres/gpu = 1 920 min (32 GPU-h concurrent) — per user **per QoS**.
  `coe-ice` (also in the account's QoS list) carries the same limits and is a separate budget by Slurm semantics; it is
  the QoS for `coe-gpu`, where 25 of the 37 H100/H200 nodes live. `ice-gpu` (AllowQos=ALL) reaches 6 H100 + 6 H200 nodes
  under coc-ice. The driver uses ice-gpu/coc-gpu only; whether to use coe-gpu/coe-ice as a second 32 GPU-h budget is the
  owner's call (it would double concurrency, not per-job speed).
- Queue waits: 2–5 s on every pool at 07:02Z (H200 via ice-gpu and coe-gpu, H100, L40S); later H200 waits of 27 s,
  473 s, and one probe pending > 20 min on "Priority" (2 free H200 GPUs at the time) — H100 had ≥ 60 free GPUs all
  morning. The cu126 torch 2.14 wheel runs on H200/H100 (sm 9.0) under driver 615.71 (CUDA 13.4).

## Per-epoch probes (T4, M tier, official batch 8; `docs/tables/gpu_probe.md`)
| loader | workers | U-Net L40S | U-Net H200 | FNO L40S | FNO H200 |
|---|---|---|---|---|---|
| HDF5 (as run until today) | 6 | 170 s | 169 s | 208 s | 197 s |
| HDF5 | 12 | 94 s | 100 s | — | 116 s |
| (a) group copied to node NVMe, HDF5 | 12 | 93 s | — | — | — |
| (b) batch 16 + prefetch 4, HDF5 | 12 | 108 s | — | — | — |
| **(c) packed memmaps on node NVMe** | 6 / 12 | **87 s** | **56 s** | **183 s** | **59 s** |

- The epoch was bound by gzip-4/HDF5 decoding in the loader workers: the GPU type made no difference (H200 1.0–1.06×),
  12 workers nearly halved it, a local copy of the files changed nothing (CPU-bound, not I/O-bound), a larger batch did
  not help. Packing the loader's own tensors once per job (`ampscape/data/packed.py`, 41 GB in 57–95 s on the node's
  NVMe RAID; byte-identical items; RNG state preserved → the packed run reproduces the HDF5 run's losses exactly) makes
  the epoch GPU-bound: U-Net 3.0× and FNO 3.5× faster on H200 than before; FNO alone is 3.1× faster on H200 than on L40S.
- L tier: probe running (U-Net + FNO on T1 L, group fetched to the node's NVMe directly since scratch cannot hold L/T1
  until the M/T4 legs end) — numbers follow in this file.
- Applied (driver restarted 07:53Z, commit dec252d): every non-GNN training leg runs `PACK=1`; legs go to `ice-gpu` H200
  → H100 → `coc-gpu` L40S → A100 (spill after 3 pending on a type), all under coc-ice. GNN keeps the HDF5/graph path.
  Probing cost ≈ 2.5 GPU-h (three probes re-run after I deleted their output directory while they ran — my error).

## Plan order and storage
- The merged plan had the six GNN M re-runs in tier order; three started at 07:00–07:20Z and would have pinned M/T4 for
  ≈ 12 h while neither L/T1 nor M/T1 fits beside it under the 280 GB guard — all other work would have idled until ≈ 19:00Z.
  Cancelled them (1 epoch each; they resume from last.pt), restored "GNN strictly last", driver restarted on the reordered
  plan. Scratch 267 GB; incomplete M/T1 and L/T4 download fragments (10 GB, no staged marker) and probe outputs removed.

## Calendar (pending work: 42 jobs; measured L40S/HDF5 hours → projected with packing + H200)
| block | jobs | before (GPU-h) | after (GPU-h) | notes |
|---|---|---|---|---|
| 13c remainder: L tuning candidates, T1V L, MgNO, T4 reference backfills | 12 | 34 | 20 | GNN L tune (10 h) unchanged |
| phase 14 non-GNN M re-runs (U-Net w64, FNO w48, ViT p16g16) | 24 | 52 | 19 | ≈ 0.5–0.8 h per run on H200 |
| phase 14 GNN M re-runs | 6 | 65 | 65 | loader-bound by graph construction, not probed |
| total | 42 | 151 | 104 | GNN = 72 % of what remains |

Wall-clock, storage-serialized (one 150 GB staging window): M/T4 legs end ≈ 10:00Z → L/T1 staged → L tuning + T1V L
(≈ 2 h on H200) → M/T1, M/T3 re-runs (≈ 3 h) → GNN tail (7 jobs × 10–11 h in parallel; needs M/T4 + M/T1 + L/T1 staged in
turn) → **≈ 2026-10-14 05:00–15:00Z** (the range is the GNN L candidate's placement). Before (L40S, HDF5, original order):
the GNN-pinning deadlock plus 151 GPU-h at ≤ 16 concurrent legs ≈ 2026-10-15 00:00Z. The L re-run decision (six L
candidates) now lands ≈ 12:30Z today instead of tomorrow.

Next: L probe numbers → this file; owner decisions: (1) coe-gpu/coe-ice as a second budget, (2) a 12-worker/graph-caching
probe for the GNN (the remaining 72 %).
