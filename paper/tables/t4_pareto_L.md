# T4 error vs cost at tier L (errors against the exact block-1 map on the reference subset)

| split | method | n | cost s / landscape | rel_l2 | ns_rel_l2 | mae_log10eps | top5_iou | pinch_recall | spearman |
|---|---|---|---|---|---|---|---|---|---|
| ood_region | block 1 (exact, reference) | 20 | 1.32e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| ood_region | block 3 (correct_artifacts=1) | 20 | 1.82e+03 | 0.0264 | 0.0211 | 0.0074 | 0.9344 | 0.9360 | 0.9987 |
| ood_region | block 5 (correct_artifacts=0) | 20 | 729 | 0.1002 | 0.1008 | 0.0188 | 0.7521 | 0.9647 | 0.9901 |
| ood_region | production block 5 (correct_artifacts=1) | 20 | 725 | 0.0284 | 0.0261 | 0.0111 | 0.9310 | 0.9269 | 0.9985 |
| ood_region | block 11 (correct_artifacts=1) | 20 | 191 | 0.0791 | 0.0662 | 0.0339 | 0.8318 | 0.8189 | 0.9909 |
| test_id | block 1 (exact, reference) | 24 | 1.23e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_id | block 3 (correct_artifacts=1) | 24 | 1.65e+03 | 0.0280 | 0.0286 | 0.0079 | 0.9410 | 0.9347 | 0.9982 |
| test_id | block 5 (correct_artifacts=0) | 24 | 638 | 0.1011 | 0.1141 | 0.0217 | 0.7710 | 0.9767 | 0.9870 |
| test_id | production block 5 (correct_artifacts=1) | 24 | 566 | 0.0315 | 0.0359 | 0.0135 | 0.9344 | 0.9319 | 0.9979 |
| test_id | block 11 (correct_artifacts=1) | 24 | 164 | 0.0854 | 0.0954 | 0.0409 | 0.8317 | 0.8183 | 0.9895 |
| test_id | gnn_T4_L_s1_scalenorm (learned, 1 seed) | 1927 | 0.0665 | 0.1407 | – | 0.0733 | 0.6306 | 0.7139 | 0.9609 |
| test_id | gnn_T4_L (learned, 3 seeds) | 1927 | 0.0658 | 0.1416 | – | 0.0738 | 0.6321 | 0.7041 | 0.9604 |
| test_id | vit_T4_L (learned, 3 seeds) | 1927 | 0.0141 | 0.1586 | – | 0.0973 | 0.6046 | 0.7348 | 0.9529 |
| test_id | vit_T4_L_s1_scalenorm (learned, 1 seed) | 1927 | 0.0125 | 0.1614 | – | 0.0983 | 0.6017 | 0.7361 | 0.9513 |
| test_id | fno_T4_L_s1_scalenorm (learned, 1 seed) | 1927 | 0.00744 | 0.1199 | – | 0.0735 | 0.7145 | 0.5492 | 0.9734 |
| test_id | unet_T4_L (learned, 3 seeds) | 1927 | 0.00652 | 0.0810 | – | 0.0377 | 0.8122 | 0.8254 | 0.9916 |
| test_id | fno_T4_L (learned, 3 seeds) | 1927 | 0.00541 | 0.1198 | – | 0.0729 | 0.7132 | 0.5531 | 0.9735 |
| test_id | unet_T4_L_s1_scalenorm (learned, 1 seed) | 1927 | 0.00538 | 0.0804 | – | 0.0385 | 0.8070 | 0.8262 | 0.9913 |
| test_ood | block 1 (exact, reference) | 16 | 1.4e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_ood | block 3 (correct_artifacts=1) | 16 | 2.02e+03 | 0.0175 | 0.0267 | 0.0065 | 0.9388 | 0.9503 | 0.9978 |
| test_ood | block 5 (correct_artifacts=0) | 16 | 764 | 0.1004 | 0.1480 | 0.0405 | 0.7137 | 0.9802 | 0.9783 |
| test_ood | production block 5 (correct_artifacts=1) | 16 | 706 | 0.0204 | 0.0347 | 0.0322 | 0.9317 | 0.9544 | 0.9964 |
| test_ood | block 11 (correct_artifacts=1) | 16 | 201 | 0.0608 | 0.1091 | 0.0939 | 0.8226 | 0.8563 | 0.9825 |
