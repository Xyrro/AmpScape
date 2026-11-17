# Prior art survey — learned surrogates for circuit-theoretic landscape connectivity

Phase 1 deliverable (2026-09-05). Purpose: establish what already exists, what AmpScape
must be compared against, and where the novelty lies. Only references whose existence and
bibliographic details were verified during this survey are listed; each carries a DOI, arXiv
ID, or persistent URL. Items I looked for but could **not** find are listed explicitly in §7.

---

## 1. Circuit theory for landscape connectivity (the ground-truth model)

**Foundations.** McRae (2006) introduced *isolation by resistance*: gene flow across a
heterogeneous landscape is modelled as current flow in a resistor network, so that the
*resistance distance* (effective resistance) between two locations predicts genetic
differentiation better than Euclidean or least-cost distance [1]. McRae, Dickson, Keitt and
Shah (2008) generalised this to ecological connectivity: a raster of per-cell resistances is
turned into a graph, Kirchhoff/Ohm equations are solved with unit current injected at one focal
node and grounded at another, and the resulting *current density* map identifies pathways and
pinch-points that integrate over all possible random-walk routes, not just the least-cost path
[2]. Dickson et al. (2019) review ten years of applications and remaining challenges, including
computational cost at large extents [3].

**Software lineage.**
- *Circuitscape* (Python, 2008–) → *Circuitscape.jl* (Julia, v5, 2019–): Anantharaman, Hall,
  Shah and Edelman report the Julia port with a preconditioned conjugate-gradient solver using an
  algebraic multigrid (AMG) preconditioner and a CHOLMOD direct solver, and 2–4× speed-ups over
  the Python version [4]. Hall et al. (2021) describe applications enabled by the Julia rewrite
  and the resulting *Omniscape.jl* [5].
- *Omniscape* (McRae et al. 2016, TNC report) applies Circuitscape in a moving window around
  every source pixel ("coreless" / omnidirectional connectivity); *Omniscape.jl* is the
  reference implementation (Landau et al. 2021, JOSS) [6, 7]. Omniscape is the engine behind
  the global protected-area connectivity map of Brennan et al. (2022, *Science*) [8], which is
  the clearest demonstration that circuit-theoretic connectivity is applied at planetary scale
  and at meaningful cost.
- *gflow* (Leonard et al. 2017) massively parallelises pairwise Circuitscape solves on HPC
  systems to reach continental extents [9].
- *ConScape* (Van Moorter et al. 2023, Julia) computes randomised-shortest-path (RSP) based
  connectivity metrics that interpolate between least-cost and random-walk (circuit) extremes
  [10]; the RSP framework is due to Panzacchi et al. (2016) and is also exposed by the R package
  *gdistance* (van Etten 2017) [11, 12]. Least-cost modelling (Adriaensen et al. 2003) remains
  the historical baseline [13].

**Why it is expensive.** Each pairwise solve is a sparse symmetric positive-(semi)definite
linear system of size ≈ number of non-NoData pixels. Theory gives nearly-linear-time SDD
solvers (Spielman & Teng; Koutis, Miller & Peng 2010 [14]) and nearly-linear-time
approximation of *all* effective resistances via Johnson–Lindenstrauss sketches (Spielman &
Srivastava 2011 [15]), but practical Circuitscape workloads still rely on CG+AMG or CHOLMOD;
Omniscape multiplies the cost by the number of source windows. This is the computational gap a
learned surrogate targets.

**Inputs are uncertain by construction.** Resistance surfaces are expert- or data-derived
(Zeller, McGarigal & Whiteley 2012 review [16]); *ResistanceGA* (Peterman 2018) optimises them
against genetic data by running Circuitscape thousands of times inside a genetic algorithm [17];
Hanks & Hooten (2013) embed circuit theory in a Bayesian model whose likelihood evaluation
requires repeated resistance-distance computations [18]. Bowman et al. (2020) show current
density is robust to the *magnitude* of cost values as long as their *rank order* is preserved
[19]. All three points motivate a fast surrogate: inverse/optimisation loops need many forward
solves, and the input-space uncertainty means a surrogate must generalise across resistance
tables, which is why AmpScape includes multiple tables and an OOD-table split.

## 2. Machine learning *for* connectivity (adjacent, not surrogate)

- Deep reinforcement learning for connectivity conservation planning (Equihua, Beckmann &
  Seppelt 2024, MEE) optimises which land to protect; it uses connectivity metrics as reward
  and would directly benefit from a fast forward model [20].
- Graph-based optimisation of connectivity (GECOT, Hamonic et al. 2025, MEE) and the RSP
  sensitivity work in ConScape are optimisation layers on top of exact solvers [21, 10].
- Deep learning in landscape genetics (e.g. *disperseNN*, Smith et al. 2023) infers dispersal
  parameters from genotypes with CNNs but does not emulate a connectivity solver [22].

None of these learn a map from resistance raster to solver output.

## 3. Learned surrogates for elliptic / Laplacian problems (the ML lineage)

Circuitscape's linear system is the 5-/9-point finite-difference discretisation of a
variable-coefficient Poisson equation ∇·(σ∇φ) = f with point sources and Dirichlet grounds,
where σ = 1/R is conductance. The relevant surrogate literature is therefore the neural-operator
and PDE-emulator literature:

- **Fourier Neural Operator** (Li et al., ICLR 2021) established Darcy flow — exactly this
  operator, with a random-field coefficient — as the canonical steady-state benchmark [23];
  the *neuraloperator* library (Kossaifi et al. 2024) is the maintained reference
  implementation we pin as a baseline [24].
- **U-Net** (Ronneberger et al. 2015) [25] and **Swin-Unet** (Cao et al., ECCVW 2022) [26]
  are the standard convolutional and transformer encoder–decoders; PDEArena (Gupta &
  Brandstetter 2022) found modern U-Nets to be very strong PDE surrogates [27].
- **Graph networks** (Battaglia et al. 2018 [28]; MeshGraphNets, Pfaff et al. ICLR 2021 [29])
  operate on the discretisation graph itself, which for Circuitscape is literally the resistor
  network — the natural inductive bias for exact edge conductances and NoData holes.
- **Learned preconditioners / neural solvers** for Poisson systems (Lan et al. 2024, ICML,
  neural-preconditioned solver for mixed BCs [30]; "Learning preconditioners for conjugate
  gradient PDE solvers", ICML 2023 [31]) are the complementary route: accelerate, rather than
  replace, the solver. AmpScape's stored ground truth and solve-time statistics support
  evaluating that route too.
- Effective resistance is also an object of interest in graph ML as a **positional encoding**
  (e.g. Wang et al. ICLR 2022 [32]); a fast learned approximation of Reff on grid graphs is of
  independent interest.

## 4. Benchmark datasets we model ourselves on

| Dataset | Domain | Design features AmpScape adopts |
|---|---|---|
| **PGLearn** (Klamkin, Tanneau, Van Hentenryck 2025, arXiv:2505.22825) [33] | AC/DC optimal power flow | fixed reference solver; standardised instance families; multiple formulations per instance; complete primal/dual solution data; generation code released as a package; official splits; baseline table; HF hosting |
| OPFData (Lovett et al. 2024, arXiv:2406.07234) [34] | AC-OPF with topological perturbations | large scale, structural (graph) perturbations, HF-style distribution |
| OPF-Learn (Joswig-Jones et al. 2021, arXiv:2111.01228) [35] | AC-OPF | representative sampling of the feasible input space |
| **PDEBench** (Takamoto et al., NeurIPS 2022 D&B) [36] | 1–3D PDEs incl. Darcy | HDF5 shards, per-PDE configs, FNO/U-Net/PINN baselines, forward + inverse tasks |
| PDEArena (Gupta & Brandstetter 2022) [27] | NS, shallow water, Maxwell | many models, one codebase, strong U-Net baselines |
| **The Well** (Ohana et al., NeurIPS 2024 D&B) [37] | 16 physics simulations, 15 TB | uniform HDF5 layout + metadata, per-dataset cards, streaming loaders |
| AirfRANS (Bonnet et al., NeurIPS 2022 D&B) [38] | RANS over airfoils | explicit OOD tasks (Reynolds / angle-of-attack extrapolation), scarce-data regime |
| ConDiff (2024, arXiv:2406.04709) [39] | diffusion with high-contrast coefficients | *contrast* as a difficulty axis — directly analogous to our resistance dynamic-range ladder |

Documentation standards: *Datasheets for Datasets* (Gebru et al. 2021) [40]; the NeurIPS
2026 Evaluations & Datasets track requires hosting on Hugging Face / Dataverse / Kaggle /
OpenML, mandatory **Croissant** metadata (core + RAI fields), and long-term availability [41].
(2026 deadlines have passed — full paper May 6, 2026 — so the realistic target is the 2027
cycle or another venue; flagged in the phase report.)

## 5. Synthetic landscape generation

Neutral landscape models are the standard way to create controllable synthetic landscapes:
*NLMpy* (Etherington, Holland & O'Sullivan 2015, MEE) implements random clusters, planar and
distance gradients, midpoint-displacement fractals and mosaics in NumPy [42]. AmpScape
uses it directly (pinned) plus Gaussian random fields and barrier overlays.

## 6. Novelty assessment

Verified gaps (as of 2026-09-05; see §7 for the searches performed):

1. **No public dataset of solver-computed circuit-theory connectivity outputs exists** in the
   PGLearn / PDEBench sense (standardised instances, official splits, OOD test sets, baselines,
   generation code). Individual studies release their own current maps, but not as an ML
   benchmark.
2. **No published learned surrogate of Circuitscape / Omniscape** was found. The closest
   items are (a) Darcy-flow neural operators (same PDE, but smooth log-normal coefficients,
   no point sources, no NoData, no 8-neighbour graph semantics, no effective-resistance target)
   and (b) generic Poisson neural preconditioners.
3. Distinctive elements AmpScape adds beyond Darcy-style benchmarks: point-source /
   grounded configurations and pairwise cumulative maps (T1), an effective-resistance matrix
   target (T2), source-strength/ground rasters (T3), the windowed Omniscape operator (T4),
   real-world covariate stacks with multiple resistance tables, NoData masks, extreme
   coefficient contrast (10–10⁴), and explicit OOD splits by region, scale, table, contrast and
   synthetic→real.

## 7. Searches performed and negative results

Web searches (Sept 2026) on: "Circuitscape" + {neural network, deep learning, surrogate,
emulator, U-Net, graph neural network, neural operator}; "Omniscape" + {machine learning,
emulator}; "landscape connectivity" + {surrogate, emulator, neural operator, current density
prediction}; "effective resistance" + {neural network prediction, learned}; "connectivity
benchmark dataset machine learning". None returned a paper or dataset that learns
resistance-raster → current-map / Reff mappings. Searches on arXiv listings for 2025–2026 with
the same terms were also negative. This is a search-based finding, not a proof of absence; the
phase report recommends a final check on Google Scholar / Semantic Scholar by the owner before
submission.

## References

1. McRae, B. H. (2006). Isolation by resistance. *Evolution* 60(8):1551–1561. doi:10.1111/j.0014-3820.2006.tb00500.x
2. McRae, B. H., Dickson, B. G., Keitt, T. H., & Shah, V. B. (2008). Using circuit theory to model connectivity in ecology, evolution, and conservation. *Ecology* 89(10):2712–2724. doi:10.1890/07-1861.1
3. Dickson, B. G., et al. (2019). Circuit-theory applications to connectivity science and conservation. *Conservation Biology* 33(2):239–249. doi:10.1111/cobi.13230
4. Anantharaman, R., Hall, K., Shah, V. B., & Edelman, A. (2020). Circuitscape in Julia: High performance connectivity modelling to support conservation decisions. *Proceedings of the JuliaCon Conferences* 1(1):58. doi:10.21105/jcon.00058 (arXiv:1906.03542)
5. Hall, K. R., Anantharaman, R., Landau, V. A., Clark, M., Dickson, B. G., Jones, A., et al. (2021). Circuitscape in Julia: Empowering dynamic approaches to connectivity assessment. *Land* 10(3):301. doi:10.3390/land10030301
6. McRae, B. H., Popper, K., Jones, A., Schindel, M., Buttrick, S., Hall, K., Unnasch, B., & Platt, J. (2016). Conserving Nature's Stage: Mapping omnidirectional connectivity for resilient terrestrial landscapes in the Pacific Northwest. The Nature Conservancy, Portland, OR. (Technical report; cited via [7].)
7. Landau, V. A., Shah, V. B., Anantharaman, R., & Hall, K. R. (2021). Omniscape.jl: Software to compute omnidirectional landscape connectivity. *Journal of Open Source Software* 6(57):2829. doi:10.21105/joss.02829
8. Brennan, A., Naidoo, R., Greenstreet, L., Mehrabi, Z., Ramankutty, N., & Kremen, C. (2022). Functional connectivity of the world's protected areas. *Science* 376(6597):1101–1104. doi:10.1126/science.abl8974
9. Leonard, P. B., Duffy, E. B., Baldwin, R. F., McRae, B. H., Shah, V. B., & Mohapatra, T. K. (2017). gflow: software for modelling circuit theory-based connectivity at any scale. *Methods in Ecology and Evolution* 8(4):519–526. doi:10.1111/2041-210X.12689
10. Van Moorter, B., Kivimäki, I., Panzacchi, M., Saerens, M., et al. (2023). Accelerating advances in landscape connectivity modelling with the ConScape library. *Methods in Ecology and Evolution* 14(1):133–145. doi:10.1111/2041-210X.13850
11. Panzacchi, M., Van Moorter, B., Strand, O., Saerens, M., Kivimäki, I., St. Clair, C. C., Herfindal, I., & Boitani, L. (2016). Predicting the continuum between corridors and barriers to animal movements using Step Selection Functions and Randomized Shortest Paths. *Journal of Animal Ecology* 85(1):32–42. doi:10.1111/1365-2656.12386
12. van Etten, J. (2017). R package gdistance: Distances and routes on geographical grids. *Journal of Statistical Software* 76(13). doi:10.18637/jss.v076.i13
13. Adriaensen, F., Chardon, J. P., De Blust, G., Swinnen, E., Villalba, S., Gulinck, H., & Matthysen, E. (2003). The application of 'least-cost' modelling as a functional landscape model. *Landscape and Urban Planning* 64(4):233–247. doi:10.1016/S0169-2046(02)00242-6
14. Koutis, I., Miller, G. L., & Peng, R. (2010). Approaching optimality for solving SDD linear systems. *FOCS 2010*, 235–244. doi:10.1109/FOCS.2010.29 (arXiv:1003.2958)
15. Spielman, D. A., & Srivastava, N. (2011). Graph sparsification by effective resistances. *SIAM Journal on Computing* 40(6):1913–1926. doi:10.1137/080734029 (STOC 2008; arXiv:0803.0929)
16. Zeller, K. A., McGarigal, K., & Whiteley, A. R. (2012). Estimating landscape resistance to movement: a review. *Landscape Ecology* 27(6):777–797. doi:10.1007/s10980-012-9737-0
17. Peterman, W. E. (2018). ResistanceGA: An R package for the optimization of resistance surfaces using genetic algorithms. *Methods in Ecology and Evolution* 9(6):1638–1647. doi:10.1111/2041-210X.12984
18. Hanks, E. M., & Hooten, M. B. (2013). Circuit theory and model-based inference for landscape connectivity. *Journal of the American Statistical Association* 108(501):22–33. doi:10.1080/01621459.2012.724647
19. Bowman, J., Adey, E., Angoh, S. Y. J., Baici, J. E., Brown, M. G. C., Cordes, C., Dupuis, A. E., Newar, S. L., Scott, L. M., & Solmundson, K. (2020). Effects of cost surface uncertainty on current density estimates from circuit theory. *PeerJ* 8:e9617. doi:10.7717/peerj.9617
20. Equihua, J., Beckmann, M., & Seppelt, R. (2024). Connectivity conservation planning through deep reinforcement learning. *Methods in Ecology and Evolution* 15(4):779–790. doi:10.1111/2041-210X.14300
21. Hamonic, F., et al. (2025). GECOT: Graph-based ecological connectivity optimization tool. *Methods in Ecology and Evolution*. doi:10.1111/2041-210X.70055
22. Smith, C. C. R., Tittes, S., Ralph, P. L., & Kern, A. D. (2023). Dispersal inference from population genetic variation using a convolutional neural network. *Genetics* 224(2):iyad068. (bioRxiv 10.1101/2022.08.25.505329; PMC10213498)
23. Li, Z., Kovachki, N., Azizzadenesheli, K., Liu, B., Bhattacharya, K., Stuart, A., & Anandkumar, A. (2021). Fourier neural operator for parametric partial differential equations. *ICLR 2021*. arXiv:2010.08895
24. Kossaifi, J., Kovachki, N., Li, Z., Pitt, D., Liu-Schiaffini, M., George, R. J., Bonev, B., Azizzadenesheli, K., Berner, J., Duruisseaux, V., & Anandkumar, A. (2024). A library for learning neural operators. arXiv:2412.10354
25. Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for biomedical image segmentation. *MICCAI 2015*, LNCS 9351:234–241. doi:10.1007/978-3-319-24574-4_28
26. Cao, H., Wang, Y., Chen, J., Jiang, D., Zhang, X., Tian, Q., & Wang, M. (2022). Swin-Unet: Unet-like pure transformer for medical image segmentation. *ECCV 2022 Workshops*, LNCS 13803. doi:10.1007/978-3-031-25066-8_9
27. Gupta, J. K., & Brandstetter, J. (2022). Towards multi-spatiotemporal-scale generalized PDE modeling. arXiv:2209.15616 (PDEArena, https://github.com/pdearena/pdearena)
28. Battaglia, P. W., et al. (2018). Relational inductive biases, deep learning, and graph networks. arXiv:1806.01261
29. Pfaff, T., Fortunato, M., Sanchez-Gonzalez, A., & Battaglia, P. W. (2021). Learning mesh-based simulation with graph networks. *ICLR 2021*. arXiv:2010.03409
30. Lan, K., Gershenson, S., Kim, S., & Teran, J. (2024). A neural-preconditioned Poisson solver for mixed Dirichlet and Neumann boundary conditions. *ICML 2024*, PMLR 235. arXiv:2310.00177
31. Li, Y., Chen, P. Y., Du, T., & Matusik, W. (2023). Learning preconditioners for conjugate gradient PDE solvers. *ICML 2023*, PMLR 202.
32. Wang, H., Yin, H., Zhang, M., & Li, P. (2022). Equivariant and stable positional encoding for more powerful graph neural networks. *ICLR 2022*. arXiv:2203.00199
33. Klamkin, M., Tanneau, M., & Van Hentenryck, P. (2025). PGLearn — An open-source learning toolkit for optimal power flow. arXiv:2505.22825
34. Lovett, S., et al. (2024). OPFData: Large-scale datasets for AC optimal power flow with topological perturbations. arXiv:2406.07234
35. Joswig-Jones, T., Baker, K., & Zamzam, A. S. (2021). OPF-Learn: An open-source framework for creating representative AC optimal power flow datasets. arXiv:2111.01228
36. Takamoto, M., et al. (2022). PDEBench: An extensive benchmark for scientific machine learning. *NeurIPS 2022 Datasets and Benchmarks Track*. arXiv:2210.07182
37. Ohana, R., McCabe, M., et al. (2024). The Well: a large-scale collection of diverse physics simulations for machine learning. *NeurIPS 2024 Datasets and Benchmarks Track*. arXiv:2412.00568
38. Bonnet, F., Mazari, J. A., Cinnella, P., & Gallinari, P. (2022). AirfRANS: High fidelity computational fluid dynamics dataset for approximating Reynolds-averaged Navier–Stokes solutions. *NeurIPS 2022 Datasets and Benchmarks Track*. arXiv:2212.07564
39. ConDiff: A challenging dataset for neural solvers of partial differential equations (2024). arXiv:2406.04709
40. Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé III, H., & Crawford, K. (2021). Datasheets for datasets. *Communications of the ACM* 64(12):86–92. doi:10.1145/3458723 (arXiv:1803.09010)
41. NeurIPS 2026 Evaluations & Datasets Track, Call for Papers. https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets (accessed 2026-09-05)
42. Etherington, T. R., Holland, E. P., & O'Sullivan, D. (2015). NLMpy: a Python software package for the creation of neutral landscape models within a general numerical framework. *Methods in Ecology and Evolution* 6(2):164–168. doi:10.1111/2041-210X.12308

### Verification notes
- Journal volume/page details for [3], [9], [10], [16], [17] were taken from publisher landing
  pages or indexing services surfaced by the searches; [6] is a grey-literature report cited
  through the Omniscape.jl JOSS paper and was not independently retrieved.
- [21] was found via the Wiley landing page (2025, MEE); the full author list beyond the first
  author was not confirmed.
- [22]'s *Genetics* citation was not independently confirmed beyond the bioRxiv/PMC records; treat the journal details as provisional.
- [31] author list is from the ICML proceedings listing; verify before citing in the paper.
- [39] author list was not retrieved; cite by arXiv ID only until confirmed.

---

## 7 (continued). Searches performed — 2026-10-02 re-run before Phase 12 drafting

Appended 2026-10-02 (append-only; the §1–§7 text above is left as written on 2026-09-05). Belongs to §7.

**Protocol.** Engine: Claude Code `WebSearch` (single web engine, US-only index; no Google Scholar, CNKI or arXiv
full-text search available) plus direct `WebFetch` of candidate pages and of the Circuitscape.jl / Omniscape.jl
repositories, docs and issue trackers. Date: 2026-10-02. Each query run once, verbatim:

| # | Query |
|---|---|
| 1 | neural surrogate Circuitscape |
| 2 | learned emulator Omniscape |
| 3 | deep learning current density landscape connectivity |
| 4 | GPU Circuitscape |
| 5 | neural operator landscape connectivity |
| 6 | machine learning circuit theory conservation current map prediction |
| 7 | Omniscape acceleration |
| 8 | surrogate model resistance surface connectivity |
| 9 | Circuitscape emulator neural network |
| 10 | Omniscape GPU CUDA |
| 11 | effective resistance prediction neural network raster |
| 12 | convolutional neural network predict connectivity current flow landscape |
| 13 | arxiv Circuitscape PyTorch JAX differentiable connectivity |
| 14 | bioRxiv "Circuitscape" "surrogate" OR "emulator" deep learning |
| 15 | Circuitscape.jl Omniscape.jl GPU CUDA support github issue |
| 16 | jaxscape Boussange connectivity JAX paper arXiv |
| 17 | "Circuitscape" "neural network" surrogate OR emulator current density raster 2025 OR 2026 |
| 18 | U-Net predict Circuitscape current map from resistance raster |
| 19 | Boussange differentiable connectivity modelling preprint JAXScape "Nature Communications" OR bioRxiv OR arXiv |

Direct fetches: `github.com/Circuitscape/Circuitscape.jl` (README; issues matching "GPU OR CUDA"),
`github.com/Circuitscape/Omniscape.jl` (README; issues matching "GPU OR CUDA"),
`docs.circuitscape.org/Circuitscape.jl/latest/`, `github.com/vboussange/jaxscape`, Semantic Scholar / Europe PMC
records for candidate papers.

**Result.** No learned surrogate or emulator of Circuitscape or Omniscape, and no public ML benchmark of
solver-computed circuit-theory outputs, was found other than this project's own repository
(https://github.com/Xyrro/AmpScape, which already surfaces for query 2 — relevant for double-blind submission).
No GPU port of Circuitscape.jl or Omniscape.jl exists: neither README, the docs, nor the issue trackers mention
GPU/CUDA (the only "GPU OR CUDA" hit in Circuitscape.jl is PR #448, "Replace IterativeSolvers.jl with Krylov.jl",
merged 2026-04-04, which is not GPU work); solvers remain CG+AMG, CHOLMOD, and the Accelerate/Pardiso extensions,
with parallelism via Julia threads.

Borderline item: **JAXScape** (https://github.com/vboussange/jaxscape, V. Boussange, MIT, v0.0.6, Zenodo
doi:10.5281/zenodo.15267703) — a "differentiable and GPU-accelerated" *direct numerical* implementation in JAX of
least-cost, resistance-distance and randomized-shortest-path metrics, reporting "74x faster than Circuitscape.jl with
cg+amg solver and 17x faster than Circuitscape.jl with cholmod solver" on a 1000×1000 grid. It is not a learned
surrogate, not a port of Circuitscape/Omniscape, has no moving-window (Omniscape) mode and no dedicated paper; it is
the closest "fast exact solver" prior work and the natural GPU comparison point. Its author is a co-author of the
ConScape analytical-sensitivity preprint (bioRxiv 10.64898/2026.01.05.697654), confirming that exact connectivity
solvers are differentiable — the paper must not claim otherwise.

Adjacent, non-overlapping hits (all previously known): Equihua et al. 2024 (DRL over graph connectivity indices),
Pless et al. 2021 PNAS 118(9):e2003201118 (random forest predicting genetic distance, no circuit theory),
ResistanceGA (GA over resistance surfaces with exact solvers as the forward model), generic Darcy/porous-media
CNN and neural-operator surrogates, the SyncroSim `omniscape` workflow wrapper (apexrms.github.io/omniscape). All
remaining hits for queries 1, 6, 9–11 were electronics, neuroscience or loss-landscape name collisions.

Caveat: single-engine web search; a very recent preprint could be missed. Recommend a final Google Scholar /
Semantic Scholar pass by the owner at submission time.

### Verification addendum 2026-10-02 (corrections to the reference list above; original entries left unchanged)

All 42 references and the inline links were re-verified on 2026-10-02 (full table with quotes and status:
`paper/sections/related_work_sources.md`). All resolve. Corrections to carry into any future citation:
- [4] the Julia port reports "speed improvements of up to 1800%" (≈ 18×); the "2–4×" figure in §1 is not in the paper.
- [3] the "computational cost at large extents" sentence is not in the abstract and was not confirmed in the full text.
- [6] full author list: McRae, Popper, Jones, Schindel, Buttrick, Hall, Unnasch, Platt (2016), 47 pp.; no DOI; cite via
  https://www.sciencebase.gov/catalog/item/5807ba6de4b0841e59e3a494.
- [8] the Zenodo data record (10.5281/zenodo.6473366) confirms effective-resistance and current-density outputs; the
  attribution to Omniscape specifically was not confirmed from any fetched text.
- [21] authors Hamonic, Vaxès, Couëtoux, Albert; *MEE* 16(9):1914–1922 (2025).
- [22] journal DOI 10.1093/genetics/iyad068 (confirmed).
- [26] pages 205–218; publisher year 2023.
- [27] also published in TMLR 2023; "very strong U-Net" wording is supported in substance but not quotable verbatim.
- [30] author list is wrong: Lan, K. W., Gueidon, E., Kaneda, A., Panetta, J., & Teran, J.; PMLR 235:25976–25994.
- [31] authors confirmed (Li, Chen, Du, Matusik); PMLR 202:19425–19439.
- [32] does not use effective resistance as a positional encoding — misattributed; effective-resistance PE is in
  Velingker et al. 2023 (arXiv:2206.11941) and Black et al. 2024 (arXiv:2402.14202).
- [39] authors: Trifonov, Rudikov, Iliev, Laevsky, Oseledets, Muravleva.
- HANO is now *J. Comput. Phys.* 506:112944 (2024); MgNO is ICLR 2024; DCNO is arXiv:2408.00775 (2024); LOD-MSNO is
  arXiv:2607.12570 (Haltmayer et al., 14 Jul 2026).
- [41] still resolves; no NeurIPS 2027 call exists yet (neurips.cc/Conferences/2027 → 404 on 2026-10-02).

### 2026-10-05 WP6 implementation check (MgNO, HANO; details in `docs/wp6_implementations.md`)

- **MgNO** — https://github.com/xlliu2017/MgNO, MIT (`LICENSE.txt`, (c) 2024 Xinliang Liu), pure PyTorch; `MgNO_DC` with the README Darcy config (6 levels, 24 channels, 4 layers, `[[1,0]]*5+[[2,0]]`) has 572,661 parameters = the paper's 0.57 M; resolution-agnostic for 128²/256² (H, W divisible by 32). **USABLE** — vendor ~150 lines into `ampscape/models/mgno.py` with `num_channel_f = in_channels` and an `output_dim` head fix.
- **HANO** — https://github.com/xlliu2017/HANO (URL given in JCP §3.9), MIT (`LICENSE.txt`, (c) 2021 Shuhao Cao). The repo's `HANO` is now an unpublished "multigrid-attention" model (≈5.2 M params) introduced by a Copilot commit on 2026-05-31; the paper's hierarchical window-attention model survives only as `hano_legacy.py`, unwired, with a 3-level/dim-64 config that contradicts the paper's Table 1 (5 levels, dim 32, window 3, 2 cycles) and a 2^k+1-grid convention. **NOT USABLE** as an official baseline; keep as related work.
- The HANO README (Copilot PR #2, merged 2026-10-01) cites a non-existent "NeurIPS 2023" HANO paper (arXiv 2311.10189 is an unrelated FPGA paper; authors do not match). Cite only arXiv 2210.10890 / JCP 506:112944 (Liu, Xu, Cao, Zhang).
- Both repos pin `torch==1.13.0`, `timm==0.6.12`, `numpy==1.23.5` (requirements.txt identical); none of these pins is needed for the MgNO model code, which imports only torch.
- Paper reference numbers for later comparison (×1e-2, 256², H1-trained): MgNO Darcy rough L2 0.339 / H1 1.380, multiscale 0.715 / 1.756; HANO Darcy rough 0.343 / 1.846, multiscale 0.580 / 1.749.
