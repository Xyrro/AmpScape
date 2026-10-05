# Solver acceleration: AMG-PCG warm-started from the predicted voltage vs zero start (rtol 1e-6)

Voltage heads: official U-Net / FNO configurations trained to predict the voltage map (T3 advanced mode;
T1V = first pair of each T1 landscape, point source/ground, pre-solved) — seed 1. Medians over systems;
'reduction' = median of 1 − warm/zero per system; residual_start = relative residual of the warm start
(zero start = 1). CPU, Julia, same preconditioner/matrix/tolerance as the stored baselines.

| task | tier | model | split | systems | iters zero → warm | iter reduction | time zero → warm (ms) | time reduction | warm-start residual | converged |
|---|---|---|---|---|---|---|---|---|---|---|
