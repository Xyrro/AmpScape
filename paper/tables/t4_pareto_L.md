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
| test_ood | block 1 (exact, reference) | 16 | 1.4e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_ood | block 3 (correct_artifacts=1) | 16 | 2.02e+03 | 0.0175 | 0.0267 | 0.0065 | 0.9388 | 0.9503 | 0.9978 |
| test_ood | block 5 (correct_artifacts=0) | 16 | 764 | 0.1004 | 0.1480 | 0.0405 | 0.7137 | 0.9802 | 0.9783 |
| test_ood | production block 5 (correct_artifacts=1) | 16 | 706 | 0.0204 | 0.0347 | 0.0322 | 0.9317 | 0.9544 | 0.9964 |
| test_ood | block 11 (correct_artifacts=1) | 16 | 201 | 0.0608 | 0.1091 | 0.0939 | 0.8226 | 0.8563 | 0.9825 |
