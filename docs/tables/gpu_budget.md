# GPU budget (Phase 10 dev runs, L40S, bf16 autocast except FNO)

**External GPU request: 1 000 GPU-hours (owner decision, 2026-09-14)** — covers the conservative 30-epoch scenario below (933 GPU-h) for the ten model × task pairs, three seeds, S–XL, on L40S-class hardware.

| model | task | params (M) | train items | epochs run | best epoch | s / epoch | GPU-h / epoch | training GPU-h |
|---|---|---|---|---|---|---|---|---|
| fno | T1 | 2.11 | 1786 | 18 | 6 | 3.5 | 0.0010 | 0.017 |
| fno | T3 | 2.11 | 1839 | 69 | 57 | 2.9 | 0.0008 | 0.055 |
| fno | T4 | 2.11 | 1839 | 82 | 70 | 3.0 | 0.0008 | 0.068 |
| gnn | T1 | 0.16 | 1786 | 30 | 18 | 29.1 | 0.0081 | 0.243 |
| gnn | T4 | 0.16 | 1839 | 89 | 77 | 29.6 | 0.0082 | 0.731 |
| unet | T1 | 7.77 | 1786 | 119 | 107 | 3.4 | 0.0009 | 0.113 |
| unet | T3 | 7.77 | 1839 | 96 | 84 | 2.9 | 0.0008 | 0.077 |
| unet | T4 | 7.77 | 1839 | 57 | 45 | 3.0 | 0.0008 | 0.048 |
| vit | T1 | 3.02 | 1786 | 61 | 49 | 3.7 | 0.0010 | 0.063 |
| vit | T4 | 3.02 | 1839 | 33 | 21 | 3.1 | 0.0009 | 0.028 |

Dev training total: **1.44 GPU-h** (10 runs); evaluation passes add a few minutes each.

## Extrapolation to v1.0 (3 seeds; per model × task; assumptions in the script docstring)

| model | task | s / sample-epoch at S | epochs assumed (S / M / L / XL) | S | M | L | XL | total GPU-h (3 seeds) |
|---|---|---|---|---|---|---|---|---|
| fno | T1 | 1.95 ms | 5 / 5 / 5 / 11 | 0 | 1 | 2 | 1 | **4** |
| fno | T3 | 1.55 ms | 10 / 13 / 23 / 99 | 1 | 2 | 6 | 5 | **14** |
| fno | T4 | 1.62 ms | 13 / 16 / 28 / 122 | 1 | 3 | 7 | 6 | **18** |
| gnn | T1 | 16.30 ms | 5 / 5 / 7 / 31 | 4 | 10 | 19 | 16 | **49** |
| gnn | T4 | 16.09 ms | 14 / 18 / 30 / 134 | 11 | 35 | 79 | 70 | **195** |
| unet | T1 | 1.90 ms | 19 / 24 / 41 / 184 | 2 | 5 | 13 | 11 | **31** |
| unet | T3 | 1.56 ms | 15 / 19 / 33 / 146 | 1 | 4 | 8 | 7 | **20** |
| unet | T4 | 1.65 ms | 8 / 11 / 18 / 79 | 1 | 2 | 5 | 4 | **12** |
| vit | T1 | 2.08 ms | 9 / 11 / 19 / 84 | 1 | 3 | 6 | 6 | **16** |
| vit | T4 | 1.66 ms | 5 / 5 / 9 / 37 | 0 | 1 | 2 | 2 | **6** |

Grand total (square-root epoch rule): **365 GPU-h** (L40S-equivalent).

## Conservative scenario: 30 epochs at every tier (or the dev best epoch if larger), 3 seeds

| model | task | S | M | L | XL | total GPU-h |
|---|---|---|---|---|---|---|
| fno | T1 | 3 | 7 | 10 | 2 | **21** |
| fno | T3 | 4 | 11 | 14 | 3 | **32** |
| fno | T4 | 6 | 14 | 18 | 4 | **42** |
| gnn | T1 | 25 | 59 | 80 | 16 | **179** |
| gnn | T4 | 63 | 149 | 202 | 40 | **453** |
| unet | T1 | 10 | 24 | 33 | 7 | **74** |
| unet | T3 | 7 | 16 | 21 | 4 | **48** |
| unet | T4 | 4 | 9 | 12 | 2 | **27** |
| vit | T1 | 5 | 12 | 17 | 3 | **37** |
| vit | T4 | 3 | 6 | 8 | 2 | **18** |

Grand total (30-epoch rule): **933 GPU-h**. Both scenarios exclude evaluation passes (a few minutes per run at S; XL/XXL inference is batch-1 and adds ~1 GPU-h per model), hyper-parameter search, and the physics-informed variant. Per-epoch times were measured with small datasets (1.8k items), where fixed per-step overheads dominate: the ms/sample figures are upper bounds for well-batched training at scale.

ViT rows at L/XL assume windowed attention (global attention at 512² with patch 4 = 16 384 tokens is not feasible); GNN rows assume the same 12-hop depth (its receptive field, not its cost, is the limit at larger tiers).
