# WP4 data-scaling ablation at S, task T1, seed 1 (from docs/tables/baselines_full.md)

fixed-epoch = 30 epochs on the subset; fixed-step ≈ the full run's optimisation steps; full = the official run (all train landscapes).

| model | n train | regime | rel-L2 | MAE log10 | top-5 % IoU | epochs | train GPU-h |
|---|---|---|---|---|---|---|---|
| FNO | 1,000 | ep30 | 0.575 | 0.255 | 0.416 | 30 | 0.15 |
| FNO | 1,000 | steps | 0.438 | 0.243 | 0.462 | 39 | 0.19 |
| FNO | 5,000 | ep30 | 0.357 | 0.180 | 0.577 | 30 | 0.22 |
| FNO | 5,000 | steps | 0.298 | 0.173 | 0.597 | 54 | 0.36 |
| FNO | 20,000 | ep30 | 0.243 | 0.137 | 0.665 | 30 | 0.41 |
| FNO | 20,000 | steps | 0.246 | 0.138 | 0.664 | 36 | 0.48 |
| FNO | 61,577 | full | 0.198 | 0.112 | 0.719 | 29 | 0.95 |
| U-Net | 1,000 | ep30 | 0.496 | 0.213 | 0.484 | 30 | 0.17 |
| U-Net | 1,000 | steps | 0.368 | 0.162 | 0.607 | 88 | 0.35 |
| U-Net | 5,000 | ep30 | 0.316 | 0.155 | 0.604 | 30 | 0.15 |
| U-Net | 5,000 | steps | 0.139 | 0.076 | 0.818 | 143 | 0.76 |
| U-Net | 20,000 | ep30 | 0.188 | 0.072 | 0.771 | 30 | 0.31 |
| U-Net | 20,000 | steps | 0.103 | 0.042 | 0.877 | 94 | 0.94 |
| U-Net | 61,577 | full | 0.111 | 0.042 | 0.857 | 30 | 0.86 |
