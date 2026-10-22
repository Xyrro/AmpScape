# T4 error vs cost at tier L (errors against the exact block-1 map on the reference subset)

| split | method | n | cost s / landscape | rel_l2 | rel_l2 median (seeds) | ns_rel_l2 | mae_log10eps | top5_iou | pinch_recall | spearman |
|---|---|---|---|---|---|---|---|---|---|---|
| ood_region | block 1 (exact, reference) | 40 | 1.31e+04 | 0.0000 | – | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| ood_region | block 3 (correct_artifacts=1) | 40 | 1.62e+03 | 0.0252 | – | 0.0218 | 0.0070 | 0.9324 | 0.9321 | 0.9989 |
| ood_region | block 5 (correct_artifacts=0) | 40 | 735 | 0.1019 | – | 0.1008 | 0.0186 | 0.7149 | 0.9708 | 0.9911 |
| ood_region | production block 5 (correct_artifacts=1) | 40 | 694 | 0.0270 | – | 0.0264 | 0.0109 | 0.9298 | 0.9200 | 0.9988 |
| ood_region | block 11 (correct_artifacts=1) | 40 | 182 | 0.0752 | – | 0.0683 | 0.0354 | 0.8278 | 0.8052 | 0.9922 |
| ood_region | radius law (k=2/3, no fit) (no solver, 1 core) | 40 | 0.07 | 0.3903 | – | – | 0.2629 | 0.3158 | – | 0.8648 |
| ood_region | radius law + conductance (k=0.775, beta=0.75) (no solver, 1 core) | 40 | 0.07 | 0.2271 | – | – | 0.1861 | 0.4805 | – | 0.9308 |
| test_id | block 1 (exact, reference) | 48 | 1.18e+04 | 0.0000 | – | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_id | block 3 (correct_artifacts=1) | 48 | 1.88e+03 | 0.0287 | – | 0.0268 | 0.0078 | 0.9327 | 0.9331 | 0.9981 |
| test_id | production block 5 (correct_artifacts=1) | 48 | 727 | 0.0321 | – | 0.0341 | 0.0125 | 0.9257 | 0.9286 | 0.9978 |
| test_id | block 5 (correct_artifacts=0) | 48 | 648 | 0.1027 | – | 0.1154 | 0.0206 | 0.7382 | 0.9763 | 0.9856 |
| test_id | block 11 (correct_artifacts=1) | 48 | 186 | 0.0854 | – | 0.0928 | 0.0380 | 0.8206 | 0.8143 | 0.9880 |
| test_id | radius law + conductance (k=0.775, beta=0.75) (no solver, 1 core) | 48 | 0.0707 | 0.2573 | – | – | 0.2376 | 0.4702 | – | 0.8858 |
| test_id | radius law (k=2/3, no fit) (no solver, 1 core) | 48 | 0.0707 | 0.4418 | – | – | 0.3195 | 0.2536 | – | 0.6925 |
| test_id | gnn_T4_L_scalenorm (tuned) (learned, 1 seed) | 48 | 0.0446 | 0.1385 | 0.1385 | – | 0.0751 | 0.6081 | 0.6832 | 0.9581 |
| test_id | gnn_T4_L (tuned) (learned, 3 seeds) | 48 | 0.0445 | 0.1375 | 0.1376 | – | 0.0755 | 0.6053 | 0.6686 | 0.9574 |
| test_id | vit_T4_L (learned, 3 seeds) | 48 | 0.0151 | 0.1541 | 0.1537 | – | 0.0960 | 0.5808 | 0.6983 | 0.9577 |
| test_id | vit_T4_L_scalenorm (learned, 1 seed) | 48 | 0.0126 | 0.1566 | 0.1566 | – | 0.0982 | 0.5851 | 0.7129 | 0.9536 |
| test_id | unet_T4_L (learned, 3 seeds) | 48 | 0.00652 | 0.0850 | 0.0849 | – | 0.0412 | 0.7894 | 0.8029 | 0.9905 |
| test_id | unet_T4_L_scalenorm (learned, 3 seeds) | 48 | 0.00447 | 0.0865 | 0.0870 | – | 0.0421 | 0.7851 | 0.7949 | 0.9902 |
| test_id | fno_T4_L_scalenorm (tuned) (learned, 3 seeds) | 48 | 0.00317 | 0.1144 | 0.1145 | – | 0.0736 | 0.7109 | 0.5583 | 0.9776 |
| test_id | fno_T4_L (tuned) (learned, 3 seeds) | 48 | 0.00281 | 0.1148 | 0.1145 | – | 0.0736 | 0.7105 | 0.5584 | 0.9776 |
| test_ood | block 1 (exact, reference) | 32 | 1.5e+04 | 0.0000 | – | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| test_ood | block 3 (correct_artifacts=1) | 32 | 2.03e+03 | 0.0273 | – | 0.0303 | 0.0080 | 0.9204 | 0.9569 | 0.9963 |
| test_ood | block 5 (correct_artifacts=0) | 32 | 919 | 0.1078 | – | 0.1395 | 0.0343 | 0.6885 | 0.9745 | 0.9740 |
| test_ood | production block 5 (correct_artifacts=1) | 32 | 780 | 0.0319 | – | 0.0371 | 0.0262 | 0.9149 | 0.9565 | 0.9952 |
| test_ood | block 11 (correct_artifacts=1) | 32 | 215 | 0.0800 | – | 0.1009 | 0.0739 | 0.7994 | 0.8745 | 0.9783 |
| test_ood | radius law (k=2/3, no fit) (no solver, 1 core) | 32 | 0.0697 | 0.5131 | – | – | 0.4601 | 0.2032 | – | 0.5813 |
| test_ood | radius law + conductance (k=0.775, beta=0.75) (no solver, 1 core) | 32 | 0.0697 | 0.3565 | – | – | 0.3744 | 0.3283 | – | 0.8041 |
