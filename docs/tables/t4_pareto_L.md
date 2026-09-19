# T4 error vs cost at tier L (errors against the exact block-1 map on the reference subset)

| split | method | n | cost s / landscape | rel_l2 | ns_rel_l2 | mae_log10eps | top5_iou | pinch_recall | spearman |
|---|---|---|---|---|---|---|---|---|---|
| test_id | block 1 (exact, reference) | 9 | 1.1e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_id | block 3 (correct_artifacts=1) | 9 | 1.29e+03 | 0.0299 | 0.0373 | 0.0103 | 0.9597 | 0.9216 | 0.9993 |
| test_id | block 5 (correct_artifacts=0) | 9 | 492 | 0.0950 | 0.1079 | 0.0281 | 0.8594 | 0.9750 | 0.9963 |
| test_id | production block 5 (correct_artifacts=1) | 9 | 480 | 0.0361 | 0.0477 | 0.0205 | 0.9514 | 0.9360 | 0.9988 |
| test_id | block 11 (correct_artifacts=1) | 9 | 120 | 0.0941 | 0.1252 | 0.0577 | 0.8673 | 0.7809 | 0.9943 |
| test_ood | block 1 (exact, reference) | 4 | 1.3e+04 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_ood | block 3 (correct_artifacts=1) | 4 | 1.66e+03 | 0.0187 | 0.0282 | 0.0073 | 0.9694 | 0.9268 | 0.9997 |
| test_ood | block 5 (correct_artifacts=0) | 4 | 622 | 0.0953 | 0.2322 | 0.0701 | 0.9241 | 0.9789 | 0.9957 |
| test_ood | production block 5 (correct_artifacts=1) | 4 | 603 | 0.0227 | 0.0467 | 0.0637 | 0.9660 | 0.9758 | 0.9970 |
| test_ood | block 11 (correct_artifacts=1) | 4 | 141 | 0.0673 | 0.1568 | 0.1745 | 0.9093 | 0.8934 | 0.9890 |
