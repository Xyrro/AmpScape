# GPU usage of the tuning re-runs (phases 13c–16), Slurm accounting 2026-10-13 00:00Z → 2026-10-15 20:30Z

## Phases 13c–15 (2026-10-13 00:00Z → 2026-10-14 07:10Z)

| item | GPU-h |
|---|---|
| GNN M re-runs + GNN L candidate (phase 14) | 58.9 |
| U-Net/FNO/ViT M re-runs (phase 14) | 47.8 |
| FNO w48 L re-runs (phase 15) | 16.3 |
| phase 13c remainder (MgNO, T1V, evaluations) | 11.4 |
| XL/XXL transfer legs (phase 15) | 6.5 |
| tuning candidates (phase 13) | 6.2 |
| GPU-type / input-pipeline probes | 3.9 |
| other | 0.0 |
| **total** | **150.9** |

Elapsed × allocated GPUs of every job (training legs, evaluation legs, transfer legs, probes); CPU backfills excluded.
Phase 14 (30 tuned M re-runs) and phase 15 (11 FNO w48 L runs + 16 transfer legs) were approved at ≈ 117 and ≈ 32 GPU-h;
the packed input pipeline and the H100/H200 pools cut the non-GNN re-runs well below the estimate, the GNN re-runs (HDF5 graph path, 6–9 h each) dominate.

## Phase 16 (2026-10-14 07:10Z → 2026-10-15 20:30Z; approved at ≈ 114 GPU-h)

| item | GPU-h |
|---|---|
| GNN T1 L seeds 2–3, GNN T4 L seeds 1–3, two scale-aware L runs (48 two-hour training/evaluation legs on H200, incl. 1.1 h lost to a faulted GPU) | 71.7 |
| XL/XXL transfer legs (16, L40S) | 7.8 |
| **total** | **79.4** |

Seed 1 of GNN T1 L reused the tuning candidate (≈ 9 GPU-h saved). GNN L epochs took 1 033–1 332 s on H200, the same as on H100.
**Cumulative since 2026-10-13 00:00Z: 230.3 GPU-h** (`sacct -u $USER -S 2026-10-13T00:00 -X -P -o JobID,JobName,ElapsedRaw,AllocTRES,State`, elapsed × allocated GPUs; CPU backfills excluded).
