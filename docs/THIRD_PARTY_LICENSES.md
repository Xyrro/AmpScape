# Third-party code vendored into AmpScape

| component | location | origin | licence |
|---|---|---|---|
| MgNO (multigrid neural operator; He et al., ICLR 2024) | `ampscape/models/mgno.py` | https://github.com/xlliu2017/MgNO, `models.py` at commit 3a68a90 (fetched 2026-10-04) | MIT, Copyright (c) 2024 Xinliang Liu — full notice in the module |

Changes to the vendored code are listed in the module docstring (output head width; imports); the model block is
otherwise verbatim. Reference solvers (Circuitscape.jl, Omniscape.jl) are dependencies, not vendored.
