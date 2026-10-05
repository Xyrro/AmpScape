# T4 error vs cost at tier M (errors against the exact block-1 map on the reference subset)

| split | method | n | cost s / landscape | rel_l2 | ns_rel_l2 | mae_log10eps | top5_iou | pinch_recall | spearman |
|---|---|---|---|---|---|---|---|---|---|
| ood_region | block 1 (exact, reference) | 300 | 740 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| ood_region | production block 3 (correct_artifacts=1) | 300 | 123 | 0.0274 | 0.0349 | 0.0121 | 0.9168 | 0.9135 | 0.9979 |
| ood_region | block 3 (correct_artifacts=0) | 300 | 121 | 0.1094 | 0.1000 | 0.0267 | 0.4962 | 0.7279 | 0.9806 |
| ood_region | block 7 (correct_artifacts=1) | 300 | 29.1 | 0.0927 | 0.0951 | 0.0437 | 0.7625 | 0.7722 | 0.9830 |
| ood_region | block 7 (correct_artifacts=0) | 300 | 25.3 | 0.2917 | 0.3311 | 0.0601 | 0.4434 | 0.9752 | 0.9597 |
| test_id | block 1 (exact, reference) | 400 | 776 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_id | block 3 (correct_artifacts=0) | 400 | 112 | 0.1105 | 0.1069 | 0.0260 | 0.6105 | 0.7658 | 0.9856 |
| test_id | production block 3 (correct_artifacts=1) | 400 | 111 | 0.0291 | 0.0371 | 0.0119 | 0.9357 | 0.9312 | 0.9983 |
| test_id | block 7 (correct_artifacts=1) | 400 | 25.5 | 0.0983 | 0.1064 | 0.0526 | 0.8081 | 0.8081 | 0.9845 |
| test_id | block 7 (correct_artifacts=0) | 400 | 25.4 | 0.2918 | 0.3771 | 0.0679 | 0.5468 | 0.9662 | 0.9664 |
| test_ood | block 1 (exact, reference) | 300 | 860 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_ood | production block 3 (correct_artifacts=1) | 300 | 133 | 0.0316 | 0.0517 | 0.0112 | 0.9154 | 0.9252 | 0.9954 |
| test_ood | block 3 (correct_artifacts=0) | 300 | 132 | 0.1153 | 0.1520 | 0.0266 | 0.5998 | 0.7793 | 0.9626 |
| test_ood | block 7 (correct_artifacts=0) | 300 | 30.7 | 0.2992 | 0.5477 | 0.1059 | 0.5370 | 0.9575 | 0.9220 |
| test_ood | block 7 (correct_artifacts=1) | 300 | 30.2 | 0.1027 | 0.1493 | 0.0889 | 0.7680 | 0.8216 | 0.9632 |
