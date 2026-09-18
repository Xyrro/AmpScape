> **Owner corrections on adoption (2026-09-17), which take precedence over the text below**
> 1. **WP1 premise**: the production Omniscape block rule (block = largest odd ≤ radius/10; block 1 at S, i.e. exact) was
>    chosen in the Phase-5/6 fidelity study by relative L2 and maximum difference against block 1 — the measured values
>    are stated in `docs/t4_fidelity.md`, not the addendum's assumption of a substantial approximation. The extension
>    (top-q IoU, pinch-point recall, non-source rel-L2, `correct_artifacts` documented) and the block-1 reference subset at
>    M and L are still done, with a cost estimate first.
> 2. **§4, first bullet** (ICE policy): resolved, no action.
> 3. **WP8 motivation**: add the many-query uses of T1–T3 — ResistanceGA-style resistance optimisation, all-pairs effective
>    resistance in landscape genetics, Bayesian resistance inference.
>
> Execution order set by the owner: WP3 → WP5 (design the probe set, estimate its cost) → WP1 → WP2, all on CPU alongside
> generation, stopping for confirmation after WP1 and after WP2; WP4, WP6, WP7 wait for the GPU allocation; a cost
> estimate precedes each package.

# AmpScape — External Review Addendum (September 2026)

**To:** the Claude Code instance executing `docs/TASK_BRIEF.md` (project formerly EcoFlowBench, now AmpScape)
**From:** the owner, summarising an independent review carried out in a separate Claude session
**Place this file at:** `docs/REVIEW_ADDENDUM_2026-09.md`, and log its adoption in `DECISIONS.md`
**Status it assumes:** Phases 0–11 built and tested; v1.0 generation running (Tier S complete and audited, M → XXL in progress); full baselines, Phase 12 and the paper still to do.

## How to use this document

1. It is an **addendum**, not a replacement brief. v1.0 generation continues unchanged. Do not alter the schema, splits or content of shards already published.
2. The reviewer only ever saw the original scaffold zip (README, CLAUDE.md, `TASK_BRIEF.md`) and a one-page status summary. **You know the real state of the repository better than this document does.** For every item below, first check whether it is already done or is contradicted by what was actually built; if so, say so in the report rather than redoing or forcing it.
3. All additions are delivered as auxiliary artefacts (`aux/` files, extra Parquet tables, new metrics, new docs) or as a later v1.1 — never as silent changes to v1.0.
4. The gates in `CLAUDE.md` still apply (>500 CPU-h, >20 GPU-h, any public push, any deletion → ask first). Give a cost estimate before each work package.
5. "Do not fabricate" still applies. Section 2 lists sources with URLs; **re-verify each one before citing it** in any project document. Numbers marked *pilot* come from a toy experiment and must never be cited as results of this project.
6. When finished with each work package, write `docs/addendum_WPx_report.md`, commit, summarise in chat, and stop for confirmation.

---

## 1. Outcome of the review in one paragraph

The project should be **finished and submitted**; the remaining cost is small relative to what exists. But the original motivation ("the solver is exact but slow at scale") does not survive scrutiny for single full-raster solves, and the paper must not rest on it. The defensible framing is two-tier: **T4 (Omniscape) is the task with a real, documented compute problem; T1–T3 are a hard operator-learning problem (globally coupled, high-contrast, singular sources, real-world coefficients) rather than a practical acceleration need.** Several cheap additions (Section 3) close the gaps a reviewer is most likely to attack. Scope must not grow further.

---

## 2. Evidence gathered during the review

### 2.1 Measured in a sandbox (single CPU core, Python + pyamg, 8-neighbour grid, contrast 10³ with gapped barriers, CG tol 1e-8)

| Problem | Nodes | Time per solve |
|---|---|---|
| Full raster 128² | 1.6e4 | 0.07 s |
| Full raster 512² | 2.6e5 | 1.6 s |
| Full raster 1024² | 1.0e6 | 8 s |
| Full raster 2048² | 4.2e6 | 49 s |
| Omniscape-style window, r = 50 px | 7.8e3 | 0.04 s |
| Omniscape-style window, r = 100 px | 3.1e4 | 0.17 s |
| Omniscape-style window, r = 200 px | 1.3e5 | 0.9 s |

Implication: a single full-raster solve is cheap; Omniscape is expensive only because the number of window solves ≈ (pixels with source) / block_size². You have real Circuitscape.jl/Omniscape.jl timings in `stats/solve_times.parquet`; **use yours, not these**, but check they tell the same story.

### 2.2 Literature findings (re-verify before citing)

Documented Omniscape cost / practitioner pain:
- Conservation-planning comparison reporting an Omniscape analysis on 55 CPUs, 350 GB RAM, ~140 h per species, versus < 2 h for the Circuitscape analyses, and stating such capacity is unavailable to most practitioners — https://www.frontiersin.org/journals/conservation-science/articles/10.3389/fcosc.2023.976914/full
- A British Columbia connectivity repository noting a 30 m regional Omniscape run of ~196 h and runs needing hundreds of GB of RAM — https://github.com/Heckford/bc-connectivity
- Omniscape.jl issue with radius 668 px (~1.4 M pixels per solve), multi-hour runs — https://github.com/Circuitscape/Omniscape.jl/issues/92
- Practitioner paper (Biodiversity Net Gain, England) listing supercomputer access as a barrier — https://www.sciencedirect.com/science/article/pii/S0301479722024306

`block_size` practice:
- Omniscape.jl docs: block_size > 1 "can significantly reduce compute times" with negligible differences in cumulative current — https://docs.circuitscape.org/Omniscape.jl/stable/usage/
- North America study: block size set to 10 % of the window radius; outputs across block sizes "highly correlated"; radii 30–700 km — https://link.springer.com/article/10.1007/s10980-022-01530-9
- Real-world radii are often large (hundreds to > 1000 px), so the "Omniscape is a local operator" argument (output pixel depends only on inputs within 2r + block_size) helps CNNs only for moderate radii.

Closest ML prior art (must appear in related work, with the precise delta):
- FNO Darcy; PDEBench Darcy.
- HANO multiscale elliptic benchmark — https://arxiv.org/abs/2210.10890
- MgNO (benchmarks "Darcy rough", "Darcy multiscale") — https://arxiv.org/abs/2310.19809
- Dilated convolution neural operator, which documents that the standard Darcy-rough coefficient takes values 12 / 2 (contrast 6) with f ≡ 1 — https://arxiv.org/abs/2408.00775
- LOD-based multiscale neural operator for rough, high-contrast coefficients — https://arxiv.org/abs/2607.12570
- Delta to state: real-world coefficient fields; contrast up to 10⁶; per-sample singular sources/sinks instead of f ≡ 1; grids up to 2048²; systematic OOD splits; domain metrics.

Connectivity-side prior art:
- 2026 preprint deriving closed-form sensitivities of landscape functionality for LCP / circuit theory / SAMC / RSP, implemented in ConScape, and explicitly describing a differentiable framework usable for gradient-based optimisation — https://www.biorxiv.org/content/10.64898/2026.01.05.697654v1.full
  Consequence: never claim that exact connectivity solvers are non-differentiable or that differentiability is unique to neural surrogates.

Search result on novelty: roughly six differently-worded web searches found **no learned surrogate/emulator of Circuitscape or Omniscape and no GPU port**. This was not a Scholar/CNKI-grade search. `docs/prior_art.md` should record its own search protocol and date; repeat the search shortly before submission.

### 2.3 Toy pilot on Omniscape (*pilot*; own re-implementation without `correct_artifacts`; synthetic landscapes; r = 12 px; 0.3 M-parameter U-Net; CPU only)

| | cost / 128² tile | rel. L2 | Spearman | top-10 % IoU |
|---|---|---|---|---|
| U-Net, in-distribution | 0.015 s | 0.086 | 0.986 | 0.885 |
| block_size 3, in-distribution | 4.5 s | 0.243 | 0.979 | 0.730 |
| block_size 1 (truth) | 30.7 s | — | — | — |
| U-Net, OOD (contrast ×30, extra barriers) | 0.015 s | 0.199 | 0.967 | 0.759 |
| block_size 3, OOD | 4.7 s | 0.221 | 0.976 | 0.704 |

- block_size at the practitioner ratio (r = 30, block 3 = 0.1 r, one tile): Spearman 0.994 but rel. L2 ≈ 0.15 and top-10 % IoU ≈ 0.77; excluding block-centre spikes, rel. L2 ≈ 0.09–0.11. **High rank correlation hides substantial pixel-level and hot-spot error.**
- Error concentrates on **non-source pixels** (rel. L2 0.375 vs 0.131 on source pixels for the 1500-step model; block_size 3: 0.526 vs 0.237). These are the matrix pixels where corridors and pinch points live.
- The learned model degraded OOD; the block_size approximation barely did.
- Test error was identical for 25 / 40 / 100 training tiles at equal steps and kept falling with more steps (model/training-bound at that scale).

The owner reports that at real scale "nothing is close to trivial" and resolution transfer is the hard axis. That evidence is stronger than the pilot and takes precedence; the pilot's role is only to motivate the checks below. The pilot code is not part of this project and is intentionally not provided; do not try to reproduce it — every check it motivates is to be run with the project's own Omniscape.jl pipeline and data.

---

## 3. Work packages (priority order)

### WP1 — T4 ground-truth fidelity audit and block_size = 1 reference subset  *(CPU; highest priority)*
The status summary says the production Omniscape block size was "chosen by a fidelity study". T4 targets therefore contain a blocking approximation.
1. Document in `docs/t4_fidelity.md`: block_size and radius per tier, `correct_artifacts` setting, and the exact metrics/thresholds the fidelity study used.
2. If that study relied mainly on correlation, extend it with rel. L2, log-MAE, top-q % IoU (q = 1, 5, 10), pinch-point recall and non-source rel. L2 (WP3), against block_size = 1.
3. Generate a **block_size = 1 reference subset** on test_id and each T4 OOD split (suggest 200–500 tiles in tiers S–M, fewer in L; estimate cost first). Store as `aux/t4_bs1_reference/` with its own Parquet index keyed by `sample_id`; record solve times.
4. Report production-target-vs-bs1 error next to best-baseline-vs-production-target error. **If the former is not clearly smaller than the latter, stop and flag to the owner** — the benchmark would be measuring models against label noise of comparable size.

### WP2 — block_size Pareto baseline for T4  *(CPU)*
On the WP1 subset, run block_size ≈ {0.05, 0.1, 0.2}·r (odd integers), with `correct_artifacts` on and off if the installed version exposes it (verify the config key). Store outputs and timings under `aux/t4_blocksize_baselines/`. Extend `scripts/evaluate.py` so that T4 tables always print learned models and block_size rows side by side, **on every split including OOD**, with cost columns. Deliver an error-vs-cost Pareto figure per split. Expect (from the pilot) that block_size degrades little OOD while learned models degrade more; report whatever is observed.

### WP3 — Non-source-pixel metrics  *(code only)*
Add rel. L2, log-MAE and top-q IoU restricted to pixels with zero source strength (and, for T1/T3, pixels outside focal nodes/sources plus a small exclusion halo around them, since currents are singular there). Unit-test against hand-computed cases. If the source mask is not recoverable from stored inputs for some task, report that instead of guessing.

### WP4 — Data-scaling ablation  *(GPU; give estimate, respect the 20 GPU-h gate)*
Tier S, U-Net plus one other baseline, training-set sizes {1k, 5k, 20k, 100k}, fixed step budget and fixed-epoch variants, one seed first. Purpose: either justify the dataset size or report honest saturation. Either outcome goes in the paper.

### WP5 — Resolution-versus-size confound  *(analysis; small generation only if needed)*
Tabulate pixel size × raster size per tier. If the two co-vary across tiers, "resolution transfer" and "size extrapolation" are confounded in `test_ood_scale`. Then either (a) build a small controlled probe set — same pixel size at two raster sizes, and same raster size at two pixel sizes, from existing tiles — or (b) state the confound explicitly in the dataset card and paper. Also confirm in writing how XXL real tiles (2048² at coarse resolution cover ~2000 km) were kept geographically independent across splits.

### WP6 — One multiscale-operator baseline  *(GPU; optional, ask first)*
Add HANO or MgNO **only if** an official or clearly licensed implementation can be verified. Otherwise record the attempt in `docs/prior_art.md`. Without it, the paper must still discuss this family.

### WP7 — Downstream many-query demonstration  *(after full baselines)*
On ~20 held-out real tiles, run the best T4 model across all resistance tables (plus `random_table` draws) and compare, against the true solver, the *conclusions* a user would draw: stability of top-q % regions across tables, ranking of tables by their effect, pinch-point persistence. Report agreement and total cost of both routes. This is the paper's answer to "who would use this".

### WP8 — Paper framing (Phase 12 outline and docs)
- **Motivation:** lead with the documented Omniscape cost and many-query uses (sensitivity analysis over resistance parameters, scenario comparison, resistance-surface optimisation). State plainly, with your own timings, that single full-raster solves are cheap and that T1–T3 are included as an operator-learning challenge, with solver-acceleration (warm-start / iterations-saved) metrics as the practically relevant number for them.
- **Headline result:** a speed–accuracy–robustness trade-off, not "surrogates beat solvers".
- **Related work:** Section 2.2 lists the minimum; include the PGLearn design comparison and note the asymmetry (OPF is non-convex with real-time needs; this problem is linear and costly only through repetition).
- **Limitations to state:** resistance tables are structural proxies, not ecological truth; a faster approximation does not reduce resistance-surface uncertainty; learned models degrade OOD and final decision maps should be verified with the solver; T4 targets include a quantified blocking approximation (WP1); any confound from WP5.
- **Claims to avoid:** "Circuitscape is slow" without qualification; "exact solvers are not differentiable"; "no prior work on where to intervene" (Barrier Mapper, Zonation, Marxan Connect, ConScape sensitivities exist); any citation of *pilot* numbers as project results.
- **Venues:** NeurIPS 2027 D&B primary; keep a fallback plan (data-descriptor journal or an ecological-informatics/methods journal) in `paper/outline.md`.

---

## 4. Items to report back to the owner (no action beyond reporting)
- Whether research-scale generation on PACE-ICE (an instructional cluster) is within policy, and the required acknowledgement text.
- Status of the GRIP4 licence enquiry and the fallback if the answer is negative.
- Any work package above that is already complete, infeasible, or based on a wrong assumption about the repository.

## 5. Explicitly out of scope
- New tasks, tiers, modes or instance families.
- Changing anything already published in v1.0.
- The owner's follow-on research (robustness of urban connectivity conclusions to resistance-parameter uncertainty; budget-constrained robust intervention design). It will reuse this project's tile pipeline, resistance tables, Omniscape driver and trained T4 models, so keep those components importable and documented — but build nothing for it here.

## 6. Suggested order and gates
WP3 → WP1 → WP2 (CPU, can run alongside v1.0 generation if they do not compete for the same allocation) → report and stop → WP5 → WP4 → full three-seed baselines (already planned) → WP6 if approved → WP7 → WP8. Stop for confirmation after WP1 (because of its flag condition), after WP2, and before any GPU work beyond the gate.
