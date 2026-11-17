# Solver acceleration: AMG-PCG warm-started from the predicted voltage vs zero start (rtol 1e-6)

Voltage heads: official U-Net / FNO configurations trained to predict the voltage map (T3 advanced mode;
T1V = first pair of each T1 landscape, point source/ground, pre-solved) — seed 1. Medians over systems;
'reduction' = median of 1 − warm/zero per system; residual_start = relative residual of the warm start
(zero start = 1). CPU, Julia, same preconditioner/matrix/tolerance as the stored baselines.

| task | tier | model | split | systems | iters zero → warm | iter reduction | time zero → warm (ms) | time reduction | warm-start residual | converged |
|---|---|---|---|---|---|---|---|---|---|---|
| T1V | L | fno | test_id | 1928 | 16 → 18 | -7.7 % | 517.9 → 580.5 | -7.5 % | 34.7 | 100.0 % |
| T1V | L | fno | test_ood | 1278 | 25 → 26 | -7.1 % | 860.1 → 930.0 | -7.3 % | 91.1 | 100.0 % |
| T1V | M | fno | test_id | 4823 | 12 → 12 | +0.0 % | 102.5 → 105.7 | -4.5 % | 22.2 | 100.0 % |
| T1V | M | fno | test_ood | 3225 | 16 → 16 | +0.0 % | 141.3 → 143.4 | -1.8 % | 22.2 | 100.0 % |
| T1V | S | fno | test_id | 9850 | 9 → 10 | +0.0 % | 23.2 → 23.4 | -0.8 % | 11 | 100.0 % |
| T1V | S | fno | test_ood | 6460 | 11 → 12 | +0.0 % | 30.2 → 30.7 | -0.2 % | 11.4 | 100.0 % |
| T3 | L | fno | test_id | 1928 | 17 → 18 | -5.6 % | 757.0 → 808.7 | -6.2 % | 1.62e+03 | 100.0 % |
| T3 | L | fno | test_ood | 1275 | 23 → 24 | -4.2 % | 1159.8 → 1221.1 | -4.4 % | 1.89e+03 | 100.0 % |
| T3 | M | fno | test_id | 4823 | 12 → 13 | +0.0 % | 119.9 → 120.9 | -0.5 % | 559 | 100.0 % |
| T3 | M | fno | test_ood | 3222 | 16 → 16 | +0.0 % | 167.2 → 169.3 | -0.5 % | 653 | 100.0 % |
| T3 | S | fno | test_id | 9850 | 10 → 10 | +0.0 % | 19.3 → 19.7 | -0.1 % | 181 | 100.0 % |
| T3 | S | fno | test_ood | 6460 | 11 → 11 | +0.0 % | 25.4 → 25.6 | +0.0 % | 212 | 100.0 % |
| T1V | L | unet | test_id | 1928 | 16 → 17 | -6.7 % | 739.5 → 821.4 | -7.4 % | 22.5 | 100.0 % |
| T1V | L | unet | test_ood | 1278 | 25 → 26 | -5.6 % | 1248.0 → 1320.7 | -5.7 % | 22.5 | 100.0 % |
| T1V | M | unet | test_id | 4823 | 12 → 12 | -5.6 % | 86.9 → 91.6 | -6.5 % | 19.4 | 100.0 % |
| T1V | M | unet | test_ood | 3225 | 16 → 17 | -4.8 % | 129.4 → 137.6 | -5.7 % | 17.6 | 100.0 % |
| T1V | S | unet | test_id | 9850 | 9 → 9 | +0.0 % | 14.4 → 14.4 | +0.0 % | 5.06 | 100.0 % |
| T1V | S | unet | test_ood | 6460 | 11 → 11 | +0.0 % | 19.2 → 19.3 | +0.1 % | 4.69 | 100.0 % |
| T3 | L | unet | test_id | 1928 | 17 → 19 | -9.1 % | 763.2 → 858.6 | -9.5 % | 3.32e+03 | 100.0 % |
| T3 | L | unet | test_ood | 1275 | 23 → 25 | -8.8 % | 1164.0 → 1281.7 | -8.8 % | 3.87e+03 | 100.0 % |
| T3 | M | unet | test_id | 4823 | 12 → 13 | -2.9 % | 99.9 → 102.3 | -1.0 % | 580 | 100.0 % |
| T3 | M | unet | test_ood | 3222 | 16 → 16 | -4.5 % | 140.7 → 144.5 | -4.5 % | 783 | 100.0 % |
| T3 | S | unet | test_id | 9850 | 10 → 10 | +0.0 % | 19.3 → 19.1 | +0.1 % | 82.5 | 100.0 % |
| T3 | S | unet | test_ood | 6460 | 11 → 11 | +0.0 % | 25.4 → 24.5 | +0.1 % | 109 | 100.0 % |
