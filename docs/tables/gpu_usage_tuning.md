# GPU usage of the tuning re-runs (phases 13c–15), Slurm accounting 2026-10-13 00:00Z → 2026-10-14 07:10Z

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
