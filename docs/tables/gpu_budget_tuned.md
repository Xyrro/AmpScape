# GPU budget (Phase 10 dev runs, L40S, bf16 autocast except FNO)

| model | task | params (M) | train items | epochs run | best epoch | s / epoch | GPU-h / epoch | training GPU-h |
|---|---|---|---|---|---|---|---|---|
| fno | T1 | 8.40 | 1786 | 84 | 72 | 3.3 | 0.0009 | 0.079 |
| fno | T1 | 33.56 | 1786 | 74 | 62 | 4.1 | 0.0012 | 0.088 |
| fno | T1 | 33.56 | 1786 | 63 | 51 | 3.8 | 0.0011 | 0.070 |
| fno | T3 | 33.56 | 1839 | 65 | 53 | 3.9 | 0.0011 | 0.073 |
| fno | T4 | 33.56 | 1839 | 73 | 61 | 3.6 | 0.0010 | 0.078 |
| gnn | T1 | 0.16 | 1786 | 42 | 30 | 29.5 | 0.0082 | 0.344 |
| gnn | T1 | 0.25 | 1786 | 67 | 55 | 17.5 | 0.0049 | 0.326 |
| gnn | T1 | 0.24 | 1786 | 111 | 99 | 17.3 | 0.0048 | 0.534 |
| gnn | T4 | 0.24 | 1839 | 52 | 40 | 17.7 | 0.0049 | 0.255 |
| unet | T1 | 7.77 | 1786 | 120 | 110 | 3.7 | 0.0010 | 0.125 |
| unet | T3 | 7.77 | 1839 | 102 | 90 | 3.6 | 0.0010 | 0.103 |
| unet | T1 | 17.47 | 1786 | 120 | 111 | 3.7 | 0.0010 | 0.126 |
| unet | T1 | 17.47 | 1786 | 113 | 101 | 3.3 | 0.0009 | 0.105 |
| vit | T1 | 3.03 | 1786 | 19 | 7 | 3.9 | 0.0011 | 0.021 |
| vit | T1 | 3.62 | 1786 | 31 | 19 | 9.7 | 0.0027 | 0.084 |
| vit | T1 | 3.62 | 1786 | 22 | 10 | 9.4 | 0.0026 | 0.058 |

Dev training total: **2.47 GPU-h** (16 runs); evaluation passes add a few minutes each.

## Extrapolation to v1.0 (3 seeds; per model × task; assumptions in the script docstring)

| model | task | s / sample-epoch at S | epochs assumed (S / M / L / XL) | S | M | L | XL | total GPU-h (3 seeds) |
|---|---|---|---|---|---|---|---|---|
| fno | T1 | 1.87 ms | 13 / 17 / 28 / 124 | 1 | 4 | 9 | 8 | **21** |
| fno | T1 | 2.32 ms | 11 / 14 / 24 / 107 | 1 | 4 | 9 | 8 | **22** |
| fno | T1 | 2.16 ms | 9 / 12 / 20 / 88 | 1 | 3 | 7 | 6 | **17** |
| fno | T3 | 2.14 ms | 10 / 12 / 21 / 93 | 1 | 3 | 7 | 6 | **18** |
| fno | T4 | 1.98 ms | 11 / 14 / 24 / 106 | 1 | 3 | 8 | 7 | **19** |
| gnn | T1 | 16.52 ms | 6 / 7 / 12 / 52 | 5 | 14 | 32 | 28 | **79** |
| gnn | T1 | 9.80 ms | 10 / 13 / 22 / 95 | 5 | 15 | 35 | 30 | **86** |
| gnn | T1 | 9.69 ms | 17 / 23 / 38 / 170 | 8 | 27 | 60 | 54 | **149** |
| gnn | T4 | 9.60 ms | 7 / 10 / 16 / 70 | 3 | 12 | 25 | 22 | **62** |
| unet | T1 | 2.09 ms | 19 / 25 / 43 / 189 | 2 | 6 | 15 | 13 | **36** |
| unet | T3 | 1.98 ms | 16 / 21 / 35 / 157 | 2 | 5 | 11 | 10 | **28** |
| unet | T1 | 2.10 ms | 19 / 25 / 43 / 190 | 2 | 6 | 15 | 13 | **36** |
| unet | T1 | 1.86 ms | 18 / 23 / 39 / 173 | 2 | 5 | 12 | 10 | **29** |
| vit | T1 | 2.17 ms | 5 / 5 / 5 / 12 | 1 | 1 | 2 | 1 | **4** |
| vit | T1 | 5.45 ms | 5 / 5 / 8 / 33 | 1 | 3 | 7 | 6 | **18** |
| vit | T1 | 5.28 ms | 5 / 5 / 5 / 18 | 1 | 3 | 4 | 3 | **12** |

Grand total (square-root epoch rule): **636 GPU-h** (L40S-equivalent).

## Conservative scenario: 30 epochs at every tier (or the dev best epoch if larger), 3 seeds

| model | task | S | M | L | XL | total GPU-h |
|---|---|---|---|---|---|---|
| fno | T1 | 7 | 16 | 22 | 4 | **49** |
| fno | T1 | 7 | 17 | 23 | 5 | **53** |
| fno | T1 | 6 | 13 | 18 | 4 | **40** |
| fno | T3 | 6 | 14 | 18 | 4 | **42** |
| fno | T4 | 6 | 15 | 20 | 4 | **44** |
| gnn | T1 | 25 | 59 | 81 | 16 | **181** |
| gnn | T1 | 27 | 65 | 88 | 18 | **197** |
| gnn | T1 | 49 | 115 | 156 | 31 | **351** |
| gnn | T4 | 20 | 46 | 62 | 12 | **141** |
| unet | T1 | 12 | 28 | 37 | 7 | **84** |
| unet | T3 | 9 | 21 | 29 | 6 | **65** |
| unet | T1 | 12 | 28 | 38 | 8 | **85** |
| unet | T1 | 10 | 23 | 31 | 6 | **69** |
| vit | T1 | 3 | 8 | 11 | 2 | **24** |
| vit | T1 | 8 | 20 | 27 | 5 | **60** |
| vit | T1 | 8 | 19 | 26 | 5 | **58** |

Grand total (30-epoch rule): **1543 GPU-h**. Both scenarios exclude evaluation passes (a few minutes per run at S; XL/XXL inference is batch-1 and adds ~1 GPU-h per model), hyper-parameter search, and the physics-informed variant. Per-epoch times were measured with small datasets (1.8k items), where fixed per-step overheads dominate: the ms/sample figures are upper bounds for well-batched training at scale.

ViT rows at L/XL assume windowed attention (global attention at 512² with patch 4 = 16 384 tokens is not feasible); GNN rows assume the same 12-hop depth (its receptive field, not its cost, is the limit at larger tiers).
