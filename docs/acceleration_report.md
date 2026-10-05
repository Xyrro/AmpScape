# Item 1 — solver-acceleration metric on learned voltage heads (2026-10-05; L and T1V rows pending)

**Question.** Does a learned voltage map accelerate the exact solve? Metric (Phase 9 definition): AMG-PCG iterations
and wall time to relative residual 1e-6 when the solve is warm-started from the predicted voltage, versus from zero,
on the exact graph of each test landscape (`julia/AmpScapeSolve.jl/scripts/warm_start_eval.jl`, same preconditioner,
matrix and tolerance as the stored baselines; CPU).

**Models.** The official U-Net and FNO configurations re-trained with the voltage map as target
(`train.py --target voltage`, floor-log transform as for every other target; seed 1; 30 epochs): T3 (advanced mode,
one system per landscape) at S/M/L; T1 via the `T1V` task (first focal pair of each `points` landscape, point source
and ground, voltages pre-solved into `aux/t1_pair1/`). Evaluated on `test_id` and `test_ood` of the training tier.

**Result (S and M; `docs/tables/acceleration.md`).**

| task | tier | model | split | systems | iters zero → warm | time zero → warm (ms) | warm-start residual (zero = 1) |
|---|---|---|---|---|---|---|---|
| T3 | S | U-Net | test_id | 9,850 | 10 → 10 | 19.3 → 19.1 | 82 |
| T3 | S | FNO | test_id | 9,850 | 10 → 10 | 19.3 → 19.7 | 181 |
| T3 | M | U-Net | test_id | 4,823 | 12 → 13 | 99.9 → 102.3 | 580 |
| T3 | M | FNO | test_id | 4,823 | 12 → 13 | 119.9 → 120.9 | 559 |
| T3 | S/M | both | test_ood | 6,460 / 3,222 | 11 → 11, 16 → 16 | within ±5 % | 109–783 |

No acceleration: iteration counts are equal or one higher, wall time within ±5 %, and the warm start converges in
100 % of systems only because PCG does. The predicted voltages are good *maps* — the heads reach a validation
log-MSE of 0.005–0.03 and a median per-landscape voltage MAE of 0.05–0.14 V on fields whose typical pixel is
≈ 0.9 V (median over S landscapes; `eval_accel_*/results.json`, `voltage_mae`) — but poor *initial guesses*: the
relative Kirchhoff residual of the predicted field is 80–580 (median) and 10⁴ (mean) times that of the zero vector
(`phys_kirchhoff_residual`). A pixel-wise regression error of a few per cent is high-frequency, the graph Laplacian
amplifies exactly those components, and AMG-PCG removes them in the same ≈ 10–16 iterations it needs from zero. The
mean voltage MAE (35–73 V) is dominated by the few landscapes with very high resistance where voltages reach the
hundreds and a relative error becomes a large absolute one.

**Reading.** At S–M the exact solve is cheap (10–16 PCG iterations, 20–120 ms) and the surrogate's value is the
10³–10⁵× speed-up of the *map* itself, not a better starting point; a warm start would need a residual-aware
objective (training on ‖L v − b‖ or on smoothed fields) rather than a pixel-wise loss. This is the solver-acceleration
number the paper reports for T1–T3 (the review addendum asked for it as the practically relevant quantity): zero gain
in this form. L rows (longer solves, more headroom) and the T1 first-pair rows follow when their runs finish and will
be appended to `docs/tables/acceleration.md`.

Cost so far: 4 voltage-head runs ≈ 4.4 GPU-h (0.7 / 1.0 / 1.0 / 1.7); evaluations ≈ 6 CPU-h.
