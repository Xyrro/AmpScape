# Status — 2026-09-13 (end of Phase 9)

**Phase 9 complete; waiting for confirmation to start Phase 10 (learned baselines).**

- Metrics package (`ampscape/metrics`: pixel in log10-ε space, domain, Reff, physics, efficiency, solver acceleration) with hand-computed unit tests; `scripts/evaluate.py` + documented predictions format (`docs/evaluation.md`), deterministic, works on any subset.
- `test_ood_published` built and finalised: 45 S tiles (Eurac Alps, Hawaiian gallinule) + 1 XXL tile (raccoon Europe), resistance as given, geometric-mean resampling rule, provenance in every tile; 46 samples / 230 configs, 100 % QC, CHOLMOD, CG baselines; XXL solve 3 h (Omniscape 2.9 h, 9.6 GB).
- Coarsen-×4 → CHOLMOD → upsample baseline run through `evaluate.py` on the mini test splits (T1 mae_log10eps 0.093 / rel-L2 0.43 / top-5 IoU 0.59; T3 0.089 / 0.26 / 0.59; T4 0.47 / 0.73 / 0.57; speed-up 2.4–4.7×, Omniscape ≈ 60×) and on `test_ood_published`; results tables in `docs/phase_09_report.md`. Getting a physically comparable baseline needed three documented scale rules (1/f current scaling, focal in-fill, ground-wins T3 blocks) — all in `DECISIONS.md`.
- Findings: a coarse-solve warm start does not accelerate PCG (S: 11 → 10 iterations; XXL: worse); Circuitscape leaves a node that is both source and ground ungrounded; `refine_voltage!` now survives an ungrounded component.
- Tests: 122 passing. No downloads, no HF pushes; ICE usage well under the gates.

Full report: `docs/phase_09_report.md`.
