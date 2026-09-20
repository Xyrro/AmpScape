# T4 error vs cost at tier L (errors against the exact block-1 map on the reference subset)

| split | method | n | cost s / landscape | rel_l2 | ns_rel_l2 | mae_log10eps | top5_iou | pinch_recall | spearman |
|---|---|---|---|---|---|---|---|---|---|
| test_id | block 1 (exact, reference) | 12 | 1.14e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_id | block 3 (correct_artifacts=1) | 12 | 1.48e+03 | 0.0293 | 0.0349 | 0.0095 | 0.9436 | 0.9362 | 0.9970 |
| test_id | block 5 (correct_artifacts=0) | 12 | 561 | 0.0980 | 0.1081 | 0.0261 | 0.7995 | 0.9783 | 0.9805 |
| test_id | production block 5 (correct_artifacts=1) | 12 | 545 | 0.0350 | 0.0452 | 0.0180 | 0.9371 | 0.9470 | 0.9965 |
| test_id | block 11 (correct_artifacts=1) | 12 | 137 | 0.0916 | 0.1219 | 0.0537 | 0.8398 | 0.8110 | 0.9844 |
| test_ood | block 1 (exact, reference) | 8 | 1.25e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_ood | block 3 (correct_artifacts=1) | 8 | 1.55e+03 | 0.0161 | 0.0304 | 0.0071 | 0.9759 | 0.9572 | 0.9997 |
| test_ood | block 5 (correct_artifacts=0) | 8 | 602 | 0.1052 | 0.1748 | 0.0634 | 0.8991 | 0.9880 | 0.9956 |
| test_ood | production block 5 (correct_artifacts=1) | 8 | 580 | 0.0198 | 0.0417 | 0.0569 | 0.9704 | 0.9733 | 0.9969 |
| test_ood | block 11 (correct_artifacts=1) | 8 | 145 | 0.0622 | 0.1455 | 0.1655 | 0.9088 | 0.8858 | 0.9886 |
