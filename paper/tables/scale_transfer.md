# Scale transfer: models trained at L evaluated at L, XL and XXL (from runs/full/*/results_transfer.json; L rows from results.json). Mean ± std over seeds; zero-shot = official config; scale-aware = --target-norm scale.

| task | model | variant | eval tier | split | seeds | rel-L2 | Spearman | top-5 % IoU | throughput err |
|---|---|---|---|---|---|---|---|---|---|
| T1 | FNO | scale-aware | L | ood_region | 1 | 0.355 | 0.972 | 0.712 | 0.056 |
| T1 | FNO | scale-aware | L | test_id | 1 | 0.411 | 0.945 | 0.643 | 0.084 |
| T1 | FNO | scale-aware | L | test_ood | 1 | 0.460 | 0.955 | 0.660 | 0.067 |
| T1 | FNO | scale-aware | XL | ood_region | 1 | 0.558 | 0.944 | 0.558 | 0.228 |
| T1 | FNO | scale-aware | XL | test_id | 1 | 0.572 | 0.928 | 0.550 | 0.259 |
| T1 | FNO | scale-aware | XL | test_ood | 1 | 0.679 | 0.934 | 0.547 | 0.264 |
| T1 | FNO | scale-aware | XXL | ood_region | 1 | 0.687 | 0.885 | 0.349 | 0.275 |
| T1 | FNO | scale-aware | XXL | test_id | 1 | 0.671 | 0.916 | 0.504 | 0.298 |
| T1 | FNO | scale-aware | XXL | test_ood | 1 | 0.701 | 0.875 | 0.464 | 0.305 |
| T1 | FNO | zero-shot | L | ood_region | 3 | 0.298 ± 0.024 | 0.972 ± 0.001 | 0.712 ± 0.003 | 0.057 ± 0.001 |
| T1 | FNO | zero-shot | L | test_id | 3 | 0.361 ± 0.024 | 0.945 ± 0.001 | 0.645 ± 0.005 | 0.084 ± 0.003 |
| T1 | FNO | zero-shot | L | test_ood | 3 | 0.375 ± 0.026 | 0.955 ± 0.001 | 0.661 ± 0.003 | 0.069 ± 0.000 |
| T1 | FNO | zero-shot | XL | ood_region | 3 | 0.717 ± 0.064 | 0.942 ± 0.003 | 0.537 ± 0.062 | 0.569 ± 0.308 |
| T1 | FNO | zero-shot | XL | test_id | 3 | 0.707 ± 0.056 | 0.925 ± 0.003 | 0.532 ± 0.065 | 0.509 ± 0.275 |
| T1 | FNO | zero-shot | XL | test_ood | 3 | 0.747 ± 0.058 | 0.931 ± 0.004 | 0.530 ± 0.064 | 0.546 ± 0.298 |
| T1 | FNO | zero-shot | XXL | ood_region | 3 | 1.716 ± 0.377 | 0.880 ± 0.005 | 0.327 ± 0.026 | 2.125 ± 0.622 |
| T1 | FNO | zero-shot | XXL | test_id | 3 | 1.502 ± 0.387 | 0.913 ± 0.005 | 0.484 ± 0.074 | 1.826 ± 0.646 |
| T1 | FNO | zero-shot | XXL | test_ood | 3 | 1.593 ± 0.376 | 0.871 ± 0.005 | 0.447 ± 0.041 | 1.932 ± 0.663 |
| T1 | U-Net | scale-aware | L | ood_region | 1 | 0.309 | 0.888 | 0.597 | 0.085 |
| T1 | U-Net | scale-aware | L | test_id | 1 | 0.369 | 0.873 | 0.542 | 0.116 |
| T1 | U-Net | scale-aware | L | test_ood | 1 | 0.348 | 0.877 | 0.558 | 0.101 |
| T1 | U-Net | scale-aware | XL | ood_region | 1 | 0.956 | 0.731 | 0.413 | 0.968 |
| T1 | U-Net | scale-aware | XL | test_id | 1 | 0.957 | 0.729 | 0.413 | 0.973 |
| T1 | U-Net | scale-aware | XL | test_ood | 1 | 0.952 | 0.725 | 0.414 | 0.971 |
| T1 | U-Net | scale-aware | XXL | ood_region | 1 | 1.001 | 0.607 | 0.235 | 0.915 |
| T1 | U-Net | scale-aware | XXL | test_id | 1 | 0.987 | 0.597 | 0.286 | 0.980 |
| T1 | U-Net | scale-aware | XXL | test_ood | 1 | 0.988 | 0.568 | 0.245 | 0.938 |
| T1 | U-Net | zero-shot | L | ood_region | 3 | 0.348 ± 0.023 | 0.890 ± 0.006 | 0.603 ± 0.021 | 0.076 ± 0.007 |
| T1 | U-Net | zero-shot | L | test_id | 3 | 0.397 ± 0.011 | 0.876 ± 0.008 | 0.549 ± 0.023 | 0.107 ± 0.011 |
| T1 | U-Net | zero-shot | L | test_ood | 3 | 0.387 ± 0.015 | 0.881 ± 0.007 | 0.565 ± 0.020 | 0.090 ± 0.009 |
| T1 | U-Net | zero-shot | XL | ood_region | 3 | 1.427 ± 0.513 | 0.724 ± 0.017 | 0.425 ± 0.007 | 0.932 ± 0.019 |
| T1 | U-Net | zero-shot | XL | test_id | 3 | 1.250 ± 0.421 | 0.721 ± 0.020 | 0.418 ± 0.008 | 0.943 ± 0.018 |
| T1 | U-Net | zero-shot | XL | test_ood | 3 | 1.522 ± 0.820 | 0.715 ± 0.018 | 0.419 ± 0.007 | 0.934 ± 0.019 |
| T1 | U-Net | zero-shot | XXL | ood_region | 3 | 9.770 ± 9.349 | 0.356 ± 0.109 | 0.245 ± 0.005 | 1.400 ± 0.361 |
| T1 | U-Net | zero-shot | XXL | test_id | 3 | 4.425 ± 3.659 | 0.461 ± 0.034 | 0.301 ± 0.006 | 0.959 ± 0.033 |
| T1 | U-Net | zero-shot | XXL | test_ood | 3 | 6.035 ± 4.656 | 0.442 ± 0.024 | 0.252 ± 0.013 | 1.204 ± 0.194 |
| T1 | ViT | scale-aware | L | ood_region | 1 | 0.579 | 0.656 | 0.132 | 0.307 |
| T1 | ViT | scale-aware | L | test_id | 1 | 0.617 | 0.665 | 0.147 | 0.329 |
| T1 | ViT | scale-aware | L | test_ood | 1 | 0.970 | 0.651 | 0.130 | 0.303 |
| T1 | ViT | scale-aware | XL | ood_region | 1 | 0.637 | 0.667 | 0.160 | 0.362 |
| T1 | ViT | scale-aware | XL | test_id | 1 | 0.656 | 0.657 | 0.141 | 0.363 |
| T1 | ViT | scale-aware | XL | test_ood | 1 | 0.667 | 0.646 | 0.138 | 0.363 |
| T1 | ViT | zero-shot | L | ood_region | 3 | 0.628 ± 0.034 | 0.656 ± 0.000 | 0.132 ± 0.001 | 0.334 ± 0.012 |
| T1 | ViT | zero-shot | L | test_id | 3 | 0.648 ± 0.033 | 0.665 ± 0.000 | 0.146 ± 0.001 | 0.354 ± 0.007 |
| T1 | ViT | zero-shot | L | test_ood | 3 | 0.963 ± 0.501 | 0.651 ± 0.001 | 0.130 ± 0.001 | 0.329 ± 0.005 |
| T1 | ViT | zero-shot | XL | ood_region | 3 | 0.738 ± 0.003 | 0.662 ± 0.001 | 0.158 ± 0.001 | 0.570 ± 0.074 |
| T1 | ViT | zero-shot | XL | test_id | 3 | 0.768 ± 0.006 | 0.657 ± 0.001 | 0.141 ± 0.001 | 0.591 ± 0.069 |
| T1 | ViT | zero-shot | XL | test_ood | 3 | 0.802 ± 0.048 | 0.645 ± 0.002 | 0.139 ± 0.001 | 0.584 ± 0.117 |
| T4 | FNO | scale-aware | L | ood_region | 1 | 0.084 | 0.987 | 0.721 | – |
| T4 | FNO | scale-aware | L | test_id | 1 | 0.120 | 0.973 | 0.715 | – |
| T4 | FNO | scale-aware | L | test_ood | 1 | 0.128 | 0.959 | 0.594 | – |
| T4 | FNO | scale-aware | XL | ood_region | 1 | 0.120 | 0.986 | 0.713 | – |
| T4 | FNO | scale-aware | XL | test_id | 1 | 0.162 | 0.956 | 0.670 | – |
| T4 | FNO | scale-aware | XL | test_ood | 1 | 0.158 | 0.962 | 0.579 | – |
| T4 | FNO | scale-aware | XXL | ood_region | 1 | 0.189 | 0.976 | 0.618 | – |
| T4 | FNO | scale-aware | XXL | test_id | 1 | 0.201 | 0.940 | 0.627 | – |
| T4 | FNO | scale-aware | XXL | test_ood | 1 | 0.250 | 0.922 | 0.545 | – |
| T4 | FNO | zero-shot | L | ood_region | 3 | 0.084 ± 0.001 | 0.987 ± 0.000 | 0.719 ± 0.003 | – |
| T4 | FNO | zero-shot | L | test_id | 3 | 0.120 ± 0.001 | 0.973 ± 0.000 | 0.713 ± 0.002 | – |
| T4 | FNO | zero-shot | L | test_ood | 3 | 0.127 ± 0.002 | 0.958 ± 0.000 | 0.592 ± 0.002 | – |
| T4 | FNO | zero-shot | XL | ood_region | 3 | 0.517 ± 0.000 | 0.986 ± 0.000 | 0.711 ± 0.002 | – |
| T4 | FNO | zero-shot | XL | test_id | 3 | 0.532 ± 0.000 | 0.956 ± 0.000 | 0.668 ± 0.002 | – |
| T4 | FNO | zero-shot | XL | test_ood | 3 | 0.525 ± 0.002 | 0.962 ± 0.001 | 0.578 ± 0.001 | – |
| T4 | FNO | zero-shot | XXL | ood_region | 3 | 0.765 ± 0.001 | 0.976 ± 0.000 | 0.618 ± 0.003 | – |
| T4 | FNO | zero-shot | XXL | test_id | 3 | 0.765 ± 0.001 | 0.941 ± 0.000 | 0.627 ± 0.001 | – |
| T4 | FNO | zero-shot | XXL | test_ood | 3 | 0.775 ± 0.001 | 0.922 ± 0.001 | 0.542 ± 0.004 | – |
| T4 | U-Net | scale-aware | L | ood_region | 1 | 0.063 | 0.996 | 0.807 | – |
| T4 | U-Net | scale-aware | L | test_id | 1 | 0.080 | 0.991 | 0.807 | – |
| T4 | U-Net | scale-aware | L | test_ood | 1 | 0.088 | 0.982 | 0.700 | – |
| T4 | U-Net | scale-aware | XL | ood_region | 1 | 0.169 | 0.973 | 0.589 | – |
| T4 | U-Net | scale-aware | XL | test_id | 1 | 0.189 | 0.946 | 0.597 | – |
| T4 | U-Net | scale-aware | XL | test_ood | 1 | 0.184 | 0.940 | 0.494 | – |
| T4 | U-Net | scale-aware | XXL | ood_region | 1 | 0.324 | 0.948 | 0.447 | – |
| T4 | U-Net | scale-aware | XXL | test_id | 1 | 0.312 | 0.905 | 0.507 | – |
| T4 | U-Net | scale-aware | XXL | test_ood | 1 | 0.284 | 0.913 | 0.427 | – |
| T4 | U-Net | zero-shot | L | ood_region | 3 | 0.064 ± 0.001 | 0.996 ± 0.000 | 0.814 ± 0.006 | – |
| T4 | U-Net | zero-shot | L | test_id | 3 | 0.081 ± 0.001 | 0.992 ± 0.000 | 0.812 ± 0.005 | – |
| T4 | U-Net | zero-shot | L | test_ood | 3 | 0.089 ± 0.001 | 0.983 ± 0.001 | 0.708 ± 0.008 | – |
| T4 | U-Net | zero-shot | XL | ood_region | 3 | 0.508 ± 0.002 | 0.973 ± 0.001 | 0.587 ± 0.004 | – |
| T4 | U-Net | zero-shot | XL | test_id | 3 | 0.515 ± 0.002 | 0.946 ± 0.000 | 0.596 ± 0.002 | – |
| T4 | U-Net | zero-shot | XL | test_ood | 3 | 0.516 ± 0.005 | 0.939 ± 0.001 | 0.491 ± 0.004 | – |
| T4 | U-Net | zero-shot | XXL | ood_region | 3 | 0.748 ± 0.010 | 0.946 ± 0.002 | 0.440 ± 0.008 | – |
| T4 | U-Net | zero-shot | XXL | test_id | 3 | 0.749 ± 0.002 | 0.904 ± 0.001 | 0.505 ± 0.003 | – |
| T4 | U-Net | zero-shot | XXL | test_ood | 3 | 0.755 ± 0.005 | 0.913 ± 0.000 | 0.424 ± 0.005 | – |
| T4 | ViT | scale-aware | L | ood_region | 1 | 0.129 | 0.973 | 0.597 | – |
| T4 | ViT | scale-aware | L | test_id | 1 | 0.161 | 0.951 | 0.602 | – |
| T4 | ViT | scale-aware | L | test_ood | 1 | 0.156 | 0.911 | 0.451 | – |
| T4 | ViT | scale-aware | XL | ood_region | 1 | 0.169 | 0.976 | 0.600 | – |
| T4 | ViT | scale-aware | XL | test_id | 1 | 0.203 | 0.935 | 0.572 | – |
| T4 | ViT | scale-aware | XL | test_ood | 1 | 0.181 | 0.940 | 0.467 | – |
| T4 | ViT | zero-shot | L | ood_region | 3 | 0.125 ± 0.004 | 0.974 ± 0.001 | 0.597 ± 0.009 | – |
| T4 | ViT | zero-shot | L | test_id | 3 | 0.159 ± 0.004 | 0.953 ± 0.002 | 0.605 ± 0.009 | – |
| T4 | ViT | zero-shot | L | test_ood | 3 | 0.152 ± 0.003 | 0.914 ± 0.005 | 0.449 ± 0.009 | – |
| T4 | ViT | zero-shot | XL | ood_region | 3 | 0.518 ± 0.001 | 0.976 ± 0.002 | 0.601 ± 0.013 | – |
| T4 | ViT | zero-shot | XL | test_id | 3 | 0.538 ± 0.000 | 0.937 ± 0.002 | 0.573 ± 0.008 | – |
| T4 | ViT | zero-shot | XL | test_ood | 3 | 0.523 ± 0.002 | 0.941 ± 0.004 | 0.463 ± 0.013 | – |
