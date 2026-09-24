# Tuning pass on the dev subset (owner item 3; tier S, test_id, single seed)

| task | model | variant | extra channels | params (M) | epochs | GPU-h | mae_log10eps | rel_l2 | top5_iou | pinch_recall |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | fno | base | – | 2.11 | 18 | 0.017 | 0.598 | 1.144 | 0.107 | 0.343 |
| T1 | fno | base | – | 2.11 | 21 | 0.019 | 0.601 | 1.132 | 0.102 | 0.215 |
| T1 | fno | m32 | – | 8.40 | 84 | 0.079 | 0.387 | 0.771 | 0.401 | 0.614 |
| T1 | fno | m64 | dist | 33.56 | 74 | 0.088 | 0.198 | 0.340 | 0.542 | 0.731 |
| T1 | fno | m64 | – | 33.56 | 63 | 0.070 | 0.324 | 0.469 | 0.443 | 0.676 |
| T1 | gnn | base | dist | 0.16 | 42 | 0.344 | 0.468 | 1.071 | 0.434 | 0.573 |
| T1 | gnn | base | – | 0.16 | 30 | 0.243 | 0.613 | 1.038 | 0.406 | 0.537 |
| T1 | gnn | ms | dist | 0.25 | 67 | 0.326 | 0.337 | 0.693 | 0.464 | 0.634 |
| T1 | gnn | ms | – | 0.24 | 111 | 0.534 | 0.434 | 0.947 | 0.427 | 0.614 |
| T1 | unet | base | dist | 7.77 | 120 | 0.125 | 0.144 | 0.269 | 0.626 | 0.709 |
| T1 | unet | base | – | 7.77 | 119 | 0.113 | 0.145 | 0.251 | 0.650 | 0.726 |
| T1 | unet | wide | dist | 17.47 | 120 | 0.126 | 0.156 | 0.278 | 0.614 | 0.710 |
| T1 | unet | wide | – | 17.47 | 113 | 0.105 | 0.137 | 0.244 | 0.665 | 0.744 |
| T1 | vit | base | dist | 3.03 | 19 | 0.021 | 0.284 | 0.610 | 0.406 | 0.575 |
| T1 | vit | base | – | 3.02 | 61 | 0.063 | 0.433 | 0.574 | 0.243 | 0.684 |
| T1 | vit | p2 | dist | 3.62 | 31 | 0.084 | 0.284 | 0.590 | 0.442 | 0.576 |
| T1 | vit | p2 | – | 3.62 | 22 | 0.058 | 0.592 | 0.980 | 0.129 | 0.569 |
| T3 | fno | base | – | 2.11 | 69 | 0.055 | 0.305 | 0.543 | 0.342 | 0.467 |
| T3 | fno | m64 | – | 33.56 | 65 | 0.073 | 0.274 | 0.490 | 0.374 | 0.578 |
| T3 | unet | base | dist | 7.77 | 102 | 0.103 | 0.184 | 0.322 | 0.585 | 0.643 |
| T3 | unet | base | – | 7.77 | 96 | 0.077 | 0.175 | 0.303 | 0.587 | 0.650 |
| T4 | fno | base | – | 2.11 | 82 | 0.068 | 0.155 | 0.121 | 0.649 | 0.636 |
| T4 | fno | m64 | – | 33.56 | 73 | 0.078 | 0.170 | 0.138 | 0.630 | 0.743 |
| T4 | gnn | base | – | 0.16 | 89 | 0.731 | 0.127 | 0.170 | 0.562 | 0.655 |
| T4 | gnn | ms | – | 0.24 | 52 | 0.255 | 0.098 | 0.149 | 0.582 | 0.655 |
| T4 | unet | base | – | 7.77 | 57 | 0.048 | 0.063 | 0.093 | 0.743 | 0.834 |
| T4 | vit | base | – | 3.02 | 33 | 0.028 | 0.280 | 0.165 | 0.562 | 0.770 |

Tuning cost: 2.69 GPU-h (16 runs). **Frozen official configurations** (`ampscape.models.OFFICIAL`): U-Net base; FNO 64 modes + distance channel; ViT base; GNN multi-scale + distance channel. FNO recovers on T1 (1.14 → 0.34 rel-L2) once it can represent the point sources (64 modes) and is told where they are (distance channel); the GNN improves (1.04 → 0.69) with the 4×-coarsened graph level but stays behind the U-Net; the wide U-Net and the patch-2 ViT are within single-seed noise of their base configs; the distance channel does not help the convolutional models.
