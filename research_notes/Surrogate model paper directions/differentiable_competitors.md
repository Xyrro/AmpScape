# Differentiable and accelerated exact connectivity tools: competitors or complements to a learned Circuitscape/Omniscape surrogate

Research date: 2026-10-19. Several primary pages were not reachable this session: bioRxiv returned HTTP 429, brage.nina.no gave DNS failure, and DOAJ returned 403. Every claim below is tagged with the page it was read from. Items not verified this session are listed under Gaps and marked "(unverified this session)".

## 1. JAXScape: what it computes, speed, scale, differentiability, accompanying paper

### Takeaway
JAXScape is a small MIT-licensed JAX library from Victor Boussange (ETH Zürich). It provides differentiable, GPU-capable least-cost, resistance-distance and RSP distances, plus moving-window utilities. On one RTX 3090 its README reports 74x over Circuitscape.jl cg+amg and 17x over CHOLMOD at 1000 x 1000. No peer-reviewed paper or preprint accompanies it yet; it is cited as a Zenodo software DOI. It is the most direct "why not an exact differentiable GPU solver" competitor.

### Cited Findings
- It describes itself as "a minimal JAX library for connectivity analysis" that provides "differentiable and GPU-accelerated graph distance metrics". — [GitHub vboussange/jaxscape](https://github.com/vboussange/jaxscape)
- Supported distances: `LCPDistance` (least-cost path), `ResistanceDistance` and `RSPDistance` (randomised shortest path, with `theta` and a `cost` function). It also has raster-to-graph and graph-to-raster mappings and moving-window utilities for large-scale pipelines. The README does not mention current-density maps of the Circuitscape/Omniscape kind; what it computes is distances. — [GitHub](https://github.com/vboussange/jaxscape)
- Optional solvers for large-scale resistance distance are `CholmodSolver`, `PyAMGSolver` and `AMJaxCGSolver`. — [GitHub](https://github.com/vboussange/jaxscape)
- Benchmarks from the README, all on an RTX 3090 against CPU tools:
  - Resistance distance on a 1000 x 1000 grid: "74x faster" than Circuitscape.jl with cg+amg, and "17x faster" than Circuitscape.jl with cholmod.
  - Sensitivity on a 175 x 175 grid: "12x faster" than gdistance `shortestPath`, and "5.0x faster" than gdistance `passage` (resistance sensitivity).
  - Inverse landscape genetics on a 100 x 100 grid: "32x faster" than ResistanceGA, with a final relative RMSE "about 16x lower".

  — [GitHub](https://github.com/vboussange/jaxscape)
- The README claims "differentiability across the codebase for awesome sensitivity analysis and optimization". Its stated uses are sensitivity analysis and inverse landscape genetics. — [GitHub](https://github.com/vboussange/jaxscape)
- Citation as given: Boussange, Victor (2025), JAXScape, DOI 10.5281/zenodo.15267703 (concept DOI). The latest Zenodo version is v0.0.10, published 2026-10-06 (version DOI 10.5281/zenodo.23182436), MIT license, with no associated paper listed. — [Zenodo record](https://zenodo.org/records/15267703); [GitHub](https://github.com/vboussange/jaxscape)
- Install: `uv add jaxscape` gives a CPU build and `jaxscape[cuda]` an NVIDIA build. — [GitHub](https://github.com/vboussange/jaxscape)

### Inferences
- The largest benchmark the README states is 1000 x 1000 (10^6 cells). That is far below the 437 M cells reported for Circuitscape.jl (section 3). Wall-to-wall Omniscape-scale current maps are not a documented JAXScape output.
- The version number (0.0.x) and the lack of a paper mean reviewers may see it as early-stage. It is still the obvious baseline to run against: exact, differentiable and on GPU.
- The README's best speedup comes from GPU against CPU on one consumer GPU. A learned surrogate's speed argument should be made like-for-like, on the same GPU against JAXScape, not against CPU Circuitscape.

### Gaps
- No README figures for absolute wall-clock times, memory, or maximum grid size. The same goes for how gradients are obtained through the sparse solvers (implicit differentiation or adjoint vs. unrolling); the source code would need to be read.
- No preprint found. A search for "JAXScape" returned no paper.

## 2. ConScape and the RSP framework; Van Moorter et al. 2026 analytical sensitivity

### Takeaway
ConScape (Julia) computes randomised-shortest-path (RSP) connectivity. RSP sits on a continuum between least-cost and random-walk (circuit) movement. The library reduces its heavy dense-matrix cost with JIT compilation, efficient algorithms and "landmarks" (coarse target sets). The 2026 bioRxiv preprint proposes analytical sensitivity: derivatives of landscape-level connectivity with respect to local units, replacing node-removal experiments that are computationally infeasible.

### Cited Findings
- ConScape is "a high-performance Julia library" for landscape connectivity using randomised shortest paths. It represents "connectivity along the continuum from optimal to random movements". — [Conservation Gateway summary](https://www.conservationgateway.org/collections/land/accelerating-landscape-connectivity-modelling-conscape-library/); [NINA Brage record](https://brage.nina.no/nina-xmlui/handle/11250/3049409)
- Its computational strategy is "the combination of Julia's 'just-in-time' compiler, efficient algorithms and 'landmarks' to reduce the computational load". The case study is wild reindeer in Norway, using remote sensing and GPS data. — [Conservation Gateway](https://www.conservationgateway.org/collections/land/accelerating-landscape-connectivity-modelling-conscape-library/)
- The landmarks are built by "merging npix pixels into the center pixel" to form a sparse matrix of target qualities. — [ConScape.jl docs](https://docs.juliahub.com/ConScape/C8nRa/0.2.3/)
- The search results list the journal as Methods in Ecology and Evolution, January 2023 (DOAJ listing). — [DOAJ](https://doaj.org/article/02776583e4384ed49440ee1f8458c702) (page returned 403 on fetch; the title and journal come from the search snippet only)
- The 2026 preprint is "A unified framework for prioritizing habitat and connectivity conservation through analytical sensitivity", bioRxiv DOI 10.64898/2026.01.05.697654, January 2026. From the search snippets:
  - Existing metrics capture either the habitat role or the connector role of a spatial unit, not both.
  - "Comprehensive node-removal approaches are computationally infeasible at the spatial resolutions needed" for planning.
  - Analytical sensitivity is proposed to cover both roles, demonstrated on wild reindeer in Norway.

  — [bioRxiv PDF](https://www.biorxiv.org/content/10.64898/2026.01.05.697654.full.pdf) (full text not retrievable, HTTP 429)
- JAXScape also benchmarks "sensitivity" against gdistance, showing that autodiff sensitivity of distance metrics is an explicit use case on GPU. — [GitHub jaxscape](https://github.com/vboussange/jaxscape)

### Inferences
- In the RSP framework the fundamental matrix Z = (I − W)^-1 is generally dense, so memory grows with (cells x targets). This is the usual reason for landmarks. The ConScape pages read this session do not state it, so treat it as background to be checked in the MEE paper.
- Analytical sensitivity gives an exact local derivative (one linearisation around the current landscape). It answers "which pixel matters most now" but not "what happens after a large, non-local change". It also still needs the exact base solve at full resolution. A surrogate could serve many scenarios that are non-infinitesimal (finite edits, many candidate plans).

### Gaps
- Not verified this session (PDF unreachable): ConScape's exact complexity, memory ceilings, the largest landscape (pixel count) and its runtimes. The same applies to the 2026 preprint's author list, its derivative formulas, cost relative to one forward solve, the largest landscape treated and the software used.
- Citation to confirm: Van Moorter, B., Kivimäki, I., Noack, A., Devooght, R., Panzacchi, M., Hall, K. R., Leleux, P., Saerens, M. (2023), *Methods Ecol. Evol.* 14(1):133–145, doi:10.1111/2041-210X.13850 (unverified this session; from prior knowledge, check before citing).

## 3. GPU, parallel or distributed Circuitscape/Omniscape implementations and reported speedups

### Takeaway
I found no CUDA or GPU port of Circuitscape or Omniscape. Speedups in the literature are CPU-side:
- Circuitscape.jl: solver improvements plus thread parallelism, "up to 1800%" faster, up to 437 M cells.
- gflow: MPI/HPC parallel, 173x on HPC and 8.4x on a desktop.

JAXScape's GPU resistance distance (section 1) is the only GPU exact-solver evidence found.

### Cited Findings
- Circuitscape.jl (Julia 5.0): "speed improvements of up to 1800%", "scaling of problem sizes up to 437 million grid cells", via "improved parallel processing and solvers". — [arXiv 1906.03542](https://arxiv.org/abs/1906.03542)
- Current Circuitscape.jl solver options:
  - `cg+amg` is the default, iterative, for large grids.
  - `cholmod` is direct and uses more memory.
  - `accelerate` (macOS only) and `pardiso` are also available.
  - `parallelize` (default False) runs pair or focal solves on Julia threads.
  - `precision` is double or single; single works with cg+amg, cholmod and accelerate.
  - `cholmod_batch_size` (default 32) sets how many right-hand sides a direct solve handles at once.
  - There is no GPU option.

  — [Circuitscape.jl options docs](https://docs.circuitscape.org/Circuitscape.jl/latest/options/)
- gflow: Leonard, Duffy, Baldwin, McRae, Shah & Mohapatra, *Methods Ecol. Evol.* 8(4):519–526 (2017), doi:10.1111/2041-210X.12689. It "massively parallelizes the computation of circuit theory-based connectivity", designed for HPC but runs on Linux/macOS desktops. Reported speedups are "173x" over existing software on HPC and "8.4x" on a desktop, "while drastically reducing memory requirements". — [Conservation Gateway gflow page](https://www.conservationgateway.org/ConservationPlanning/ToolsData/sitepages/view.aspx?ID=1071); [ScienceDaily press release](https://www.sciencedaily.com/releases/2016/11/161122123549.htm)
- Omniscape provides wall-to-wall moving-window connectivity, which handles large rasters without computing all pairs. — [Omniscape.jl examples](https://docs.circuitscape.org/Omniscape.jl/latest/examples/)
- A search for a Circuitscape GPU/CUDA implementation returned only unrelated GPU "graph connected components" work. — [arXiv 2008.11839](https://arxiv.org/pdf/2008.11839) (irrelevant; noted to show the search came up empty)

### Inferences
- Exact large-scale circuit connectivity today means CPU HPC: AMG-PCG or CHOLMOD with thread or MPI parallelism over sources. Per query, the cost grows with the number of source/focal solves. That is where amortisation by a surrogate pays off.
- An AmpScape paper should frame GPU exact solving as available but immature for current maps. The candidates are JAXScape, or AMG-PCG on GPU via generic libraries such as AmgX/cuSPARSE, but no ecology tool was found that packages the latter.

### Gaps
- No cloud pipeline (Google Earth Engine, AWS) for Circuitscape/Omniscape was verified this session.
- Not checked: whether gflow itself uses PETSc. The search snippets did not confirm it.

## 4. Gradient-based resistance-surface fitting (differentiable landscape genetics) and solve counts

### Takeaway
radish (Pope and Peterman) does maximum-likelihood fitting of isolation-by-resistance models with exact gradients, Hessians and influence measures through a sparse Cholesky of the graph Laplacian, practical below about 1 M cells. ResistanceGA uses a derivative-free genetic algorithm and needs many forward solves. JAXScape reports 32x over ResistanceGA with lower error at 100 x 100.

### Cited Findings
- radish is "an R package for maximum likelihood estimation of isolation-by-resistance models", where conductance is a function of spatial covariates. It "provides fast computation of the gradient, Hessian matrix, and derivative-based leverage/influence measures". — [GitHub nspope/radish](https://github.com/nspope/radish)
- Scale: radish is "intended for moderate-sized problems (e.g. rasters with less than 1mil cells, where a sparse Cholesky decomposition of the graph Laplacian is feasible)". "Larger problems are possible (with sufficient memory), but slow". It is described as a work in progress. — [GitHub nspope/radish](https://github.com/nspope/radish); [LandGenCourse radish tutorial](https://bookdown.org/hhwagner1/LandGenCourse_book/bonus-10a.html)
- In the tutorial, resistance is log-linear in covariates. The example MLPE fit converged in 8 Newton–Raphson steps. No runtimes are reported. — [LandGenCourse tutorial](https://bookdown.org/hhwagner1/LandGenCourse_book/bonus-10a.html)
- ResistanceGA "utilizes a genetic algorithm to optimize resistance surfaces based on pairwise genetic distances". It is derivative-free, so each GA generation needs a population of full resistance-distance evaluations. — [GitHub wpeterman/ResistanceGA](https://github.com/wpeterman/ResistanceGA)
- JAXScape inverse landscape genetics on a 100 x 100 grid: "32x faster" than ResistanceGA, with a final relative RMSE "about 16x lower". — [GitHub jaxscape](https://github.com/vboussange/jaxscape)

### Inferences
- Gradient-based fitting cuts outer iterations from hundreds or thousands of GA evaluations to tens of Newton/quasi-Newton steps. Each step still needs a Laplacian factorisation plus solves for the sampled pairs. With an adjoint, the gradient costs roughly one extra solve set per step (standard adjoint reasoning, not stated in the radish README).
- The ceiling at about 1 M cells for Cholesky-based exact gradients leaves an opening for surrogates at larger extents or for many repeated fits (bootstrap, model selection, multiple species).

### Gaps
- No radish paper found or verified. Its gradient method (adjoint vs. otherwise) and solve count per iteration are not documented in the README; see the repo's `ms/` folder.
- No other differentiable landscape-genetics packages (for example Julia or PyTorch) were verified this session.

## 5. Effective-resistance approximations from theoretical CS (Laplacian solvers, sketching, Spielman–Srivastava) in ecology or spatial graphs

### Takeaway
I found no ecological or landscape-connectivity application of JL/random-projection effective-resistance sketches or of nearly-linear-time Laplacian solvers beyond AMG-PCG. The practical ecology toolchain stops at AMG-preconditioned CG or CHOLMOD, plus moving windows and coarsening.

### Cited Findings
- A search for random-projection effective-resistance approximations in landscape connectivity returned only standard Circuitscape and Omniscape material. That material covers the raster-to-graph construction, effective resistance from random-walk commute times, and Omniscape moving windows as the scale workaround. — [How Circuitscape Works](https://docs.circuitscape.org/Circuitscape.jl/latest/usage/); [Circuitscape 4.0 user guide](https://Circuitscape.org/downloads/circuitscape_4_0.pdf)
- Circuitscape.jl's iterative default is cg+amg, an AMG-preconditioned CG Laplacian solver. — [Circuitscape.jl options](https://docs.circuitscape.org/Circuitscape.jl/latest/options/)
- Theory reference: Spielman & Srivastava, "Graph Sparsification by Effective Resistances". Its JL-based approach gives approximations of all effective resistances, at a cost of O(log n) Laplacian solves. — [arXiv 0803.0929](https://arxiv.org/abs/0803.0929) (not re-fetched this session; abstract content from prior knowledge, verify before citing)

### Inferences
- JL sketches approximate pairwise effective resistance for many pairs cheaply, but not current-density maps. Omniscape's cumulative current is a different functional, a sum over sources of |current| per cell. Sketching therefore does not directly replace the surrogate's target.
- The truncated AMG-PCG and coarsen-x4 cheap numerical baselines already in AmpScape (review round 2, commit 4903376) are the practical stand-ins for "approximate exact solvers". Reviewers could still ask for a JL sketch baseline on pairwise effective resistance.

### Gaps
- No published ecology paper using Spielman–Srivastava sketching, Laplacian sparsification or Kyng–Sachdeva-type solvers for connectivity was found. This is absence of evidence from limited searching, not proof of absence.

## 6. Where a learned surrogate is complementary

### Takeaway
Exact differentiable tools win on single-landscape precision and local derivatives up to about 10^6 cells: JAXScape, radish, and analytical RSP sensitivity. A surrogate's defensible niche has four parts:
- Amortised many-query use: scenario sweeps, many species, repeated fits.
- Finite (non-local) edits, where linear sensitivity breaks down.
- Wall-to-wall current maps at extents where exact GPU tools are unbenchmarked.
- Cheap screening before exact confirmation.

### Cited Findings
- Exact node-removal prioritisation is "computationally infeasible at the spatial resolutions needed". This is the motivation for analytical sensitivity, and the same pressure motivates surrogates. — [bioRxiv 2026 preprint](https://www.biorxiv.org/content/10.64898/2026.01.05.697654.full.pdf)
- Exact gradient-based fitting (radish) is limited to about 1 M cells by Cholesky feasibility. — [GitHub nspope/radish](https://github.com/nspope/radish)
- JAXScape's largest stated benchmark is 1000 x 1000, and its outputs are distances (LCP, resistance, RSP). — [GitHub jaxscape](https://github.com/vboussange/jaxscape)
- Exact CPU Circuitscape.jl scales to 437 M cells but is not differentiable and has no GPU option. — [arXiv 1906.03542](https://arxiv.org/abs/1906.03542); [Circuitscape.jl options](https://docs.circuitscape.org/Circuitscape.jl/latest/options/)

### Inferences
- **Positioning:** Treat JAXScape and ConScape sensitivity as complements, not rivals. Exact differentiable solvers can provide surrogate training labels and gradient targets (Sobolev training). They can also confirm the top-k candidates the surrogate screens.
- **Baseline a reviewer will request:** JAXScape ResistanceDistance on the same GPU at AmpScape tile sizes, reporting time per query and the break-even number of queries against surrogate training cost. This extends AmpScape's existing break-even analysis.
- **Gradient comparison:** Compare surrogate gradients d(output)/d(resistance) with JAXScape autodiff gradients on small tiles. This tests whether "fast gradients via the surrogate" are faithful, not just fast.
- **Uncertainty propagation:** Monte Carlo over uncertain resistance surfaces needs N exact solves per landscape. The surrogate makes N large cheaply, but its own error must be calibrated against exact solves.
- **Avoid overclaiming:** The surrogate does not beat exact solvers on accuracy, and for a single query at ≤10^6 cells a GPU exact solver may already be fast enough.

### Gaps
- No published learned surrogate for Circuitscape/Omniscape currents was examined in this note; that is out of scope here.
- No direct head-to-head between JAXScape and any ML surrogate exists in the sources found.
