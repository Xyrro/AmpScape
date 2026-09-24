# Contributing

- **Setup**: `uv sync --extra dev`, `pre-commit install`; `python -m pytest -q` (offline tests; `-m "not julia"` without the
  solver, `-m "not slow"` for the quick set); Julia tests: `julia --project=julia/AmpScapeSolve.jl -e 'using Pkg; Pkg.test()'`.
- **Style**: ruff (`ruff check . && ruff format --check .`), line length 100, Python 3.11; type hints; docstrings state
  the rule or decision a function implements and where it is documented.
- **Decisions**: anything that refines or deviates from `docs/TASK_BRIEF.md` goes into `DECISIONS.md` (date, decision,
  rationale, phase); `CHANGELOG.md` per phase; phase reports in `docs/phase_XX_report.md`.
- **Data changes**: the generation pipeline is frozen at the tag `v1.0-pipeline`; changes that alter stored outputs need
  a new dataset version and tag. Never fabricate sources, licences or citations; unverifiable items are listed as such.
- **New baselines**: implement under `ampscape/models/`, register in `MODEL_VARIANTS`, train with `scripts/train.py`,
  evaluate only through `scripts/evaluate.py` (predictions format in `docs/evaluation.md`), report on `test_id` and every
  OOD split, three seeds for the paper tables.
- **New metrics**: `ampscape/metrics/` with a hand-computed unit test in `tests/test_metrics.py` and an entry in
  `docs/evaluation.md`; thresholds are conventions and must be documented as such.
- **Commits**: small, reviewable; no AI-attribution trailers; PRs describe what changed and why.
