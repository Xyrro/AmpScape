# Scale transfer: models trained at L evaluated at L, XL and XXL (from runs/full/*/results_transfer.json; L rows from results.json). Mean ± std over seeds; zero-shot = official config; scale-aware = --target-norm scale.

| task | model | variant | eval tier | split | seeds | rel-L2 | Spearman | top-5 % IoU | throughput err |
|---|---|---|---|---|---|---|---|---|---|
| T1 | FNO | scale-aware | L | ood_region | 1 | 0.238 | 0.975 | 0.732 | 0.056 |
| T1 | FNO | scale-aware | L | test_id | 1 | 0.302 | 0.949 | 0.664 | 0.085 |
| T1 | FNO | scale-aware | L | test_ood | 1 | 0.297 | 0.958 | 0.681 | 0.070 |
| T1 | FNO | scale-aware | XL | ood_region | 1 | 0.690 | 0.945 | 0.507 | 0.427 |
| T1 | FNO | scale-aware | XL | test_id | 1 | 0.700 | 0.928 | 0.496 | 0.453 |
| T1 | FNO | scale-aware | XL | test_ood | 1 | 0.711 | 0.935 | 0.492 | 0.446 |
| T1 | FNO | scale-aware | XXL | ood_region | 1 | 0.746 | 0.887 | 0.319 | 0.423 |
| T1 | FNO | scale-aware | XXL | test_id | 1 | 0.762 | 0.918 | 0.449 | 0.490 |
| T1 | FNO | scale-aware | XXL | test_ood | 1 | 0.761 | 0.877 | 0.431 | 0.455 |
| T1 | FNO | zero-shot | L | ood_region | 3 | 0.232 ± 0.014 | 0.975 ± 0.000 | 0.732 ± 0.002 | 0.054 ± 0.001 |
| T1 | FNO | zero-shot | L | test_id | 3 | 0.299 ± 0.011 | 0.949 ± 0.001 | 0.665 ± 0.003 | 0.083 ± 0.003 |
| T1 | FNO | zero-shot | L | test_ood | 3 | 0.303 ± 0.017 | 0.958 ± 0.001 | 0.680 ± 0.001 | 0.067 ± 0.003 |
| T1 | FNO | zero-shot | XL | ood_region | 3 | 0.626 ± 0.003 | 0.950 ± 0.000 | 0.563 ± 0.001 | 0.497 ± 0.102 |
| T1 | FNO | zero-shot | XL | test_id | 3 | 0.617 ± 0.010 | 0.932 ± 0.000 | 0.554 ± 0.001 | 0.434 ± 0.083 |
| T1 | FNO | zero-shot | XL | test_ood | 3 | 0.638 ± 0.008 | 0.939 ± 0.001 | 0.552 ± 0.004 | 0.486 ± 0.109 |
| T1 | FNO | zero-shot | XXL | ood_region | 3 | 1.710 ± 0.223 | 0.896 ± 0.002 | 0.353 ± 0.004 | 2.151 ± 0.323 |
| T1 | FNO | zero-shot | XXL | test_id | 3 | 1.352 ± 0.092 | 0.921 ± 0.001 | 0.507 ± 0.003 | 1.689 ± 0.182 |
| T1 | FNO | zero-shot | XXL | test_ood | 3 | 1.405 ± 0.154 | 0.881 ± 0.004 | 0.477 ± 0.006 | 1.764 ± 0.232 |
| T1 | GNN | scale-aware | L | ood_region | 1 | 1.290 | 0.893 | 0.550 | 0.882 |
| T1 | GNN | scale-aware | L | test_id | 1 | 1.287 | 0.860 | 0.495 | 0.854 |
| T1 | GNN | scale-aware | L | test_ood | 1 | 1.181 | 0.870 | 0.497 | 0.799 |
| T1 | GNN | scale-aware | XL | ood_region | 1 | 7.591 | 0.760 | 0.399 | 0.735 |
| T1 | GNN | scale-aware | XL | test_id | 1 | 7.509 | 0.736 | 0.381 | 0.725 |
| T1 | GNN | scale-aware | XL | test_ood | 1 | 3.683 | 0.754 | 0.395 | 0.706 |
| T1 | GNN | scale-aware | XXL | ood_region | 1 | 1.666 | 0.738 | 0.278 | 0.773 |
| T1 | GNN | scale-aware | XXL | test_id | 1 | 1.405 | 0.723 | 0.355 | 0.735 |
| T1 | GNN | scale-aware | XXL | test_ood | 1 | 1.890 | 0.725 | 0.348 | 0.955 |
| T1 | GNN | zero-shot | L | ood_region | 3 | 0.923 ± 0.169 | 0.894 ± 0.004 | 0.558 ± 0.011 | 0.913 ± 0.088 |
| T1 | GNN | zero-shot | L | test_id | 3 | 0.941 ± 0.160 | 0.861 ± 0.003 | 0.501 ± 0.008 | 0.873 ± 0.075 |
| T1 | GNN | zero-shot | L | test_ood | 3 | 0.927 ± 0.160 | 0.872 ± 0.004 | 0.504 ± 0.008 | 0.837 ± 0.082 |
| T1 | GNN | zero-shot | XL | ood_region | 3 | 1.501 ± 0.941 | 0.765 ± 0.003 | 0.393 ± 0.001 | 1.085 ± 0.063 |
| T1 | GNN | zero-shot | XL | test_id | 3 | 1.415 ± 0.821 | 0.741 ± 0.001 | 0.377 ± 0.001 | 0.985 ± 0.043 |
| T1 | GNN | zero-shot | XL | test_ood | 3 | 1.408 ± 0.757 | 0.758 ± 0.001 | 0.389 ± 0.003 | 1.056 ± 0.061 |
| T1 | GNN | zero-shot | XXL | ood_region | 3 | 1.532 ± 0.538 | 0.745 ± 0.004 | 0.275 ± 0.003 | 1.692 ± 0.151 |
| T1 | GNN | zero-shot | XXL | test_id | 3 | 1.615 ± 0.582 | 0.727 ± 0.002 | 0.352 ± 0.007 | 1.709 ± 0.125 |
| T1 | GNN | zero-shot | XXL | test_ood | 3 | 1.995 ± 0.631 | 0.732 ± 0.005 | 0.344 ± 0.004 | 2.758 ± 0.223 |
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
| T4 | FNO | scale-aware | L | ood_region | 1 | 0.079 | 0.988 | 0.734 | – |
| T4 | FNO | scale-aware | L | test_id | 1 | 0.115 | 0.975 | 0.726 | – |
| T4 | FNO | scale-aware | L | test_ood | 1 | 0.123 | 0.961 | 0.607 | – |
| T4 | FNO | scale-aware | XL | ood_region | 1 | 0.115 | 0.987 | 0.722 | – |
| T4 | FNO | scale-aware | XL | test_id | 1 | 0.157 | 0.958 | 0.679 | – |
| T4 | FNO | scale-aware | XL | test_ood | 1 | 0.155 | 0.963 | 0.592 | – |
| T4 | FNO | scale-aware | XXL | ood_region | 1 | 0.184 | 0.977 | 0.621 | – |
| T4 | FNO | scale-aware | XXL | test_id | 1 | 0.197 | 0.941 | 0.637 | – |
| T4 | FNO | scale-aware | XXL | test_ood | 1 | 0.242 | 0.924 | 0.555 | – |
| T4 | FNO | zero-shot | L | ood_region | 3 | 0.079 ± 0.000 | 0.988 ± 0.000 | 0.732 ± 0.002 | – |
| T4 | FNO | zero-shot | L | test_id | 3 | 0.116 ± 0.000 | 0.975 ± 0.000 | 0.723 ± 0.002 | – |
| T4 | FNO | zero-shot | L | test_ood | 3 | 0.125 ± 0.000 | 0.961 ± 0.000 | 0.606 ± 0.003 | – |
| T4 | FNO | zero-shot | XL | ood_region | 3 | 0.514 ± 0.003 | 0.987 ± 0.000 | 0.721 ± 0.002 | – |
| T4 | FNO | zero-shot | XL | test_id | 3 | 0.531 ± 0.002 | 0.958 ± 0.000 | 0.676 ± 0.002 | – |
| T4 | FNO | zero-shot | XL | test_ood | 3 | 0.523 ± 0.003 | 0.963 ± 0.000 | 0.589 ± 0.004 | – |
| T4 | FNO | zero-shot | XXL | ood_region | 3 | 0.760 ± 0.002 | 0.977 ± 0.000 | 0.625 ± 0.005 | – |
| T4 | FNO | zero-shot | XXL | test_id | 3 | 0.764 ± 0.001 | 0.942 ± 0.000 | 0.635 ± 0.002 | – |
| T4 | FNO | zero-shot | XXL | test_ood | 3 | 0.774 ± 0.003 | 0.923 ± 0.001 | 0.552 ± 0.002 | – |
| T4 | GNN | scale-aware | L | ood_region | 1 | 0.100 | 0.981 | 0.640 | – |
| T4 | GNN | scale-aware | L | test_id | 1 | 0.142 | 0.962 | 0.643 | – |
| T4 | GNN | scale-aware | L | test_ood | 1 | 0.135 | 0.913 | 0.470 | – |
| T4 | GNN | scale-aware | XL | ood_region | 1 | 0.269 | 0.943 | 0.490 | – |
| T4 | GNN | scale-aware | XL | test_id | 1 | 0.308 | 0.894 | 0.472 | – |
| T4 | GNN | scale-aware | XL | test_ood | 1 | 0.261 | 0.881 | 0.381 | – |
| T4 | GNN | scale-aware | XXL | ood_region | 1 | 0.401 | 0.931 | 0.405 | – |
| T4 | GNN | scale-aware | XXL | test_id | 1 | 0.438 | 0.872 | 0.438 | – |
| T4 | GNN | scale-aware | XXL | test_ood | 1 | 0.382 | 0.874 | 0.377 | – |
| T4 | GNN | zero-shot | L | ood_region | 3 | 0.100 ± 0.001 | 0.981 ± 0.000 | 0.639 ± 0.004 | – |
| T4 | GNN | zero-shot | L | test_id | 3 | 0.142 ± 0.001 | 0.962 ± 0.000 | 0.641 ± 0.003 | – |
| T4 | GNN | zero-shot | L | test_ood | 3 | 0.136 ± 0.001 | 0.913 ± 0.001 | 0.470 ± 0.002 | – |
| T4 | GNN | zero-shot | XL | ood_region | 3 | 0.469 ± 0.003 | 0.943 ± 0.001 | 0.487 ± 0.003 | – |
| T4 | GNN | zero-shot | XL | test_id | 3 | 0.498 ± 0.003 | 0.894 ± 0.001 | 0.469 ± 0.002 | – |
| T4 | GNN | zero-shot | XL | test_ood | 3 | 0.478 ± 0.001 | 0.880 ± 0.003 | 0.380 ± 0.004 | – |
| T4 | GNN | zero-shot | XXL | ood_region | 3 | 0.723 ± 0.002 | 0.930 ± 0.001 | 0.401 ± 0.002 | – |
| T4 | GNN | zero-shot | XXL | test_id | 3 | 0.739 ± 0.002 | 0.872 ± 0.001 | 0.435 ± 0.002 | – |
| T4 | GNN | zero-shot | XXL | test_ood | 3 | 0.736 ± 0.001 | 0.876 ± 0.002 | 0.377 ± 0.001 | – |
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
