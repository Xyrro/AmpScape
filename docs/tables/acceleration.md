# Solver acceleration: AMG-PCG warm-started from the predicted voltage vs zero start (rtol 1e-6)

Voltage heads: official U-Net / FNO configurations trained to predict the voltage map (T3 advanced mode;
T1V = first pair of each T1 landscape, point source/ground, pre-solved) — seed 1. Medians over systems;
'reduction' = median of 1 − warm/zero per system; residual_start = relative residual of the warm start
(zero start = 1). CPU, Julia, same preconditioner/matrix/tolerance as the stored baselines.

| task | tier | model | split | systems | iters zero → warm | iter reduction | time zero → warm (ms) | time reduction | warm-start residual | converged |
|---|---|---|---|---|---|---|---|---|---|---|
| T3 | M | fno | test_id | 4823 | 12 → 13 | +0.0 % | 119.9 → 120.9 | -0.5 % | 559 | 100.0 % |
| T3 | M | fno | test_ood | 3222 | 16 → 16 | +0.0 % | 167.2 → 169.3 | -0.5 % | 653 | 100.0 % |
| T3 | S | fno | test_id | 9850 | 10 → 10 | +0.0 % | 19.3 → 19.7 | -0.1 % | 181 | 100.0 % |
| T3 | S | fno | test_ood | 6460 | 11 → 11 | +0.0 % | 25.4 → 25.6 | +0.0 % | 212 | 100.0 % |
| T3 | M | unet | test_id | 4823 | 12 → 13 | -2.9 % | 99.9 → 102.3 | -1.0 % | 580 | 100.0 % |
| T3 | M | unet | test_ood | 3222 | 16 → 16 | -4.5 % | 140.7 → 144.5 | -4.5 % | 783 | 100.0 % |
| T3 | S | unet | test_id | 9850 | 10 → 10 | +0.0 % | 19.3 → 19.1 | +0.1 % | 82.5 | 100.0 % |
| T3 | S | unet | test_ood | 6460 | 11 → 11 | +0.0 % | 25.4 → 24.5 | +0.1 % | 109 | 100.0 % |
