# Per-tier tuning pass at M and L — selection on val only (T1, seed 1; `scripts/tuning_select.py`)

Criterion: best validation loss over epochs (masked MSE, log target). A candidate replaces the official
config only if it beats the official seed-1 value by more than the official config's seed spread
(std of best val loss over seeds 1–3). Test splits are not used.

| tier | model | variant | best val loss | epoch | params (M) | train GPU-h | vs official | decision |
|---|---|---|---|---|---|---|---|---|
| M | unet | base official | 0.0364 | 30 | 7.8 | 1.20 |  |  |
| M | unet | w64  | 0.0213 | 30 | 31.0 | 2.06 | -41.5 % | **chosen** |
| M | unet | wide  | 0.0252 | 30 | 17.5 | 1.44 | -30.9 % |  |
| M | unet | (official seed spread) | ± 0.0060 | | | | | config changes |
| M | fno | m64 official | 0.0498 | 29 | 33.6 | 1.63 |  |  |
| M | fno | m96  | 0.0493 | 27 | 75.5 | 2.32 | -1.0 % |  |
| M | fno | w48  | 0.0463 | 25 | 75.5 | 3.02 | -6.9 % | **chosen** |
| M | fno | (official seed spread) | ± 0.0003 | | | | | config changes |
| M | vit | base official | 0.2222 | 30 | 3.0 | 1.54 |  |  |
| M | vit | p16g16  | 0.0559 | 28 | 3.0 | 1.07 | -74.8 % | **chosen** |
| M | vit | p8g32  | 0.1678 | 29 | 3.0 | 1.53 | -24.5 % |  |
| M | vit | (official seed spread) | ± 0.0820 | | | | | config changes |
| M | gnn | ms official | 0.2150 | 30 | 0.2 | 9.20 |  |  |
| M | gnn | ms8  | 0.1633 | 30 | 0.2 | 10.84 | -24.0 % | **chosen** |
| M | gnn | (official seed spread) | ± 0.0008 | | | | | config changes |
| L | unet | base official | 0.0887 | 30 | 7.8 | 1.49 |  | **chosen** |
| L | unet | wide  | 0.0832 | 27 | 17.5 | 1.26 | -6.1 % |  |
| L | unet | (official seed spread) | ± 0.0056 | | | | | official kept |
| L | fno | m64 official | 0.0628 | 28 | 33.6 | 2.70 |  |  |
| L | fno | m96  | 0.0618 | 27 | 75.5 | 0.85 | -1.6 % |  |
| L | fno | w48  | 0.0605 | 30 | 75.5 | 1.08 | -3.7 % | **chosen** |
| L | fno | (official seed spread) | ± 0.0003 | | | | | config changes |
| L | vit | base official | 0.2636 | 29 | 3.0 | 4.44 |  | **chosen** |
| L | vit | p16g32  | 0.3895 | 22 | 3.1 | 0.43 | +47.8 % |  |
| L | vit | p8g64  | 0.4310 | 28 | 3.6 | 0.59 | +63.5 % |  |
| L | vit | (official seed spread) | ± 0.0038 | | | | | official kept |
| L | gnn | ms official | 0.3126 | 22 | 0.2 | 14.68 |  |  |
| L | gnn | ms8  | 0.2645 | 17 | 0.2 | 7.71 | -15.4 % | **chosen** |
| L | gnn | (official seed spread) | ± 0.0068 | | | | | config changes |
