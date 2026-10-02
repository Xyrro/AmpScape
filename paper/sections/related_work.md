# Related Work

<!-- Draft 2026-10-02 for Phase 12. Every citation below is VERIFIED in related_work_sources.md (access date
2026-10-02 for all URLs). Claims marked UNVERIFIED in that file are deliberately not made here. -->

**Circuit theory as the ground-truth model.** McRae [1] introduced *isolation by resistance*: gene flow across a
heterogeneous landscape is modelled as current in a resistor network, and the resulting resistance distance is "more
theoretically justified and more robust to spatial heterogeneity than Euclidean or least cost path-based distance
measures". McRae et al. [2] turned this into a connectivity tool: a resistance raster becomes a graph, Kirchhoff's
equations are solved with current injected at focal nodes, and the current-density map evaluates "contributions of
multiple dispersal pathways" rather than the single route of least-cost modelling [3]. The Julia reimplementation uses CG+AMG and
CHOLMOD solvers and reports speed-ups of up to 18× over the Python version [4, 5]; Omniscape applies it in a circular moving window around every source pixel [6, 7]; gflow parallelises
pairwise solves on HPC systems [8]; ConScape covers the randomised-shortest-path continuum between least-cost and
random-walk movement [9, 10]; and circuit-theoretic current density and effective resistance have been computed at global
extent for the world's protected areas [11]. Each solve is a sparse symmetric positive-definite system with one unknown
per pixel; nearly-linear-time solvers [12] and effective-resistance sketches [13] exist in theory, but production
workloads still use CG+AMG or CHOLMOD. Resistance surfaces are uncertain, expert- or data-derived inputs [14], so
solvers are called repeatedly: ResistanceGA runs Circuitscape inside a genetic algorithm [15], model-based inference
embeds the resistance distance in a Gaussian Markov random field [16], and cost-uncertainty studies re-solve under
perturbed tables [17].

**Documented Omniscape cost.** The practitioner literature records the problem AmpScape's T4 task targets. Dertien and
Baldwin [18] ran local and regional Circuitscape analyses in under 2 h on 4–8 CPUs, but their Omniscape analysis needed
"55 CPUs and 350 GB RAM (approximately 140 h)" per species, "a level of high-throughput computing capacity likely not
available to most conservation practitioners"; Martinez-Cillero et al. [19] list supercomputers as "unlikely to be
available for many practitioners"; an Omniscape.jl issue reports "a moving window size of 668, so about 1.4M pixels per
Circuitscape solve" and multi-hour runs on 32–64 threads [20]; and a regional 30 m run in British Columbia is logged at
196 h with runs needing "potentially hundreds of GB of RAM" [21]. The standard mitigation is `block_size`, which the
Omniscape.jl documentation says "can significantly reduce compute times" with "only negligable [sic] differences in the
cumulative current map" [22]; Belote et al. [23] set it to 10 % of the window radius (radii 30–700 km) and found outputs
"highly correlated" across block sizes. AmpScape quantifies this approximation against exact block-1 solutions rather
than assuming it (Section X), and reports learned models and block-size rows on the same cost axis.

**Deciding where to intervene, and ML for connectivity.** Prior work on *where* to act is extensive and AmpScape does
not replace it: Barrier Mapper detects barriers and quantifies restoration benefit [24]; Pinchpoint Mapper runs
Circuitscape within mapped corridors [25]; Zonation [26, 27] and Marxan Connect [28] are spatial-prioritisation
frameworks, the latter operationalising connectivity in reserve design; GECOT optimises a connectivity indicator under a
budget with mixed-integer or heuristic solvers [29]. Most relevant, Van Moorter et al. [30] derive analytical
sensitivities of landscape functionality to local perturbations of habitat quality or permeability, unified across
least-cost paths, circuit theory, spatial absorbing Markov chains and randomised shortest paths, "reducing computation
time by several orders of magnitude" relative to node removal; and JAXScape provides "differentiable and GPU-accelerated"
least-cost, resistance and RSP distances, reporting 74× over Circuitscape.jl's CG+AMG on a 1000² grid [31]. Exact
connectivity solvers are therefore differentiable and can run on accelerators; the case for a learned surrogate is
amortised cost across many queries, not differentiability.
Machine learning has otherwise been used *around* connectivity, not as its solver: deep reinforcement learning optimises
graph-based connectivity indices for planning [32], and disperseNN infers dispersal from genotypes with a CNN [33].
Our searches (prior-art protocol in the supplement, re-run 2026-10-02) found no learned surrogate or emulator of
Circuitscape or Omniscape, no public benchmark of solver-computed circuit-theory outputs, and no GPU port of either
package.

**Learned surrogates for elliptic problems.** Circuitscape's system is a finite-difference discretisation of
∇·(σ∇φ) = f with point sources and grounds, so the closest ML lineage is operator learning on Darcy flow: FNO [34]
established the benchmark, PDEBench [35] and the neuraloperator library [36] standardised it, U-Nets remain strong
baselines [37, 38], and graph networks operate on the discretisation graph itself [39, 40]. Multiscale and
high-contrast coefficients are the recognised hard case: HANO [41], MgNO [42] (benchmarks "Darcy rough" and "Darcy
multiscale"), the dilated-convolution neural operator [43], and the LOD-based multiscale neural operator for "rough and
high-contrast inputs" [44]; ConDiff makes contrast an explicit difficulty axis [45]. Learned preconditioners [46, 47]
accelerate rather than replace the solver, a route AmpScape's acceleration track evaluates directly. The precise delta is
in the data: the standard Darcy-rough coefficient "takes the value 12 for the positive part of the real line and 2 for the
negative part, with a contrast of 6" with "f(x) ≡ 1" [43], whereas AmpScape uses real-world land-cover-derived
coefficient fields alongside synthetic ones, contrast up to 10⁶ (with 10⁶ held out), per-sample singular sources, sinks
and grounds instead of a uniform forcing, grids from 128² to 2048², systematic OOD splits by region, scale, resistance
table, contrast and synthetic→real, and domain metrics (top-q IoU, pinch-point recall, non-source error) in addition to
relative L2.

**Benchmark design.** We model the release on PGLearn [48] — default reference solver, standard instance families,
"complete primal and dual solutions" for several formulations, Hugging Face hosting — and on OPFData and OPF-Learn
[49, 50]. The asymmetry should be stated: AC-OPF is "nonlinear,
non-convex" [48] and re-solved at operational cadence, whereas our forward problem is a linear SPD system that is cheap
for a single raster and costly only through repetition — Omniscape windows, optimisation loops, scenario sweeps. PDEBench, The Well and AirfRANS supply the pattern of uniform HDF5 shards, dataset cards and explicit OOD tasks
[35, 51, 52]; Datasheets for Datasets and the NeurIPS Evaluations & Datasets call set the documentation and Croissant
requirements [53, 54].

## References (URL; accessed 2026-10-02)

1. McRae, B. H. (2006). Isolation by resistance. *Evolution* 60(8):1551–1561. https://doi.org/10.1111/j.0014-3820.2006.tb00500.x
2. McRae, B. H., Dickson, B. G., Keitt, T. H., & Shah, V. B. (2008). Using circuit theory to model connectivity in ecology, evolution, and conservation. *Ecology* 89(10):2712–2724. https://doi.org/10.1890/07-1861.1
3. Adriaensen, F., et al. (2003). The application of 'least-cost' modelling as a functional landscape model. *Landscape and Urban Planning* 64(4):233–247. https://doi.org/10.1016/S0169-2046(02)00242-6
4. Anantharaman, R., Hall, K., Shah, V. B., & Edelman, A. (2020). Circuitscape in Julia: High performance connectivity modelling to support conservation decisions. *Proc. JuliaCon Conf.* 1(1):58. https://proceedings.juliacon.org/papers/10.21105/jcon.00058
5. Hall, K. R., et al. (2021). Circuitscape in Julia: Empowering dynamic approaches to connectivity assessment. *Land* 10(3):301. https://doi.org/10.3390/land10030301
6. McRae, B. H., Popper, K., Jones, A., Schindel, M., Buttrick, S., Hall, K., Unnasch, R. S., & Platt, J. (2016). Conserving Nature's Stage: Mapping omnidirectional connectivity for resilient terrestrial landscapes in the Pacific Northwest. The Nature Conservancy, Portland, OR, 47 pp. https://www.sciencebase.gov/catalog/item/5807ba6de4b0841e59e3a494
7. Landau, V. A., Shah, V. B., Anantharaman, R., & Hall, K. R. (2021). Omniscape.jl: Software to compute omnidirectional landscape connectivity. *JOSS* 6(57):2829. https://joss.theoj.org/papers/10.21105/joss.02829
8. Leonard, P. B., et al. (2017). gflow: software for modelling circuit theory-based connectivity at any scale. *MEE* 8(4):519–526. https://doi.org/10.1111/2041-210X.12689
9. Van Moorter, B., et al. (2023). Accelerating advances in landscape connectivity modelling with the ConScape library. *MEE* 14(1):133–145. https://doi.org/10.1111/2041-210X.13850
10. Panzacchi, M., et al. (2016). Predicting the continuum between corridors and barriers to animal movements using Step Selection Functions and Randomized Shortest Paths. *J. Anim. Ecol.* 85(1):32–42. https://doi.org/10.1111/1365-2656.12386
11. Brennan, A., Naidoo, R., Greenstreet, L., Mehrabi, Z., Ramankutty, N., & Kremen, C. (2022). Functional connectivity of the world's protected areas. *Science* 376(6597):1101–1104. https://doi.org/10.1126/science.abl8974 ; data: https://zenodo.org/records/6473366
12. Koutis, I., Miller, G. L., & Peng, R. (2010). Approaching optimality for solving SDD linear systems. *FOCS 2010*, 235–244. https://doi.org/10.1109/FOCS.2010.29
13. Spielman, D. A., & Srivastava, N. (2011). Graph sparsification by effective resistances. *SIAM J. Comput.* 40(6):1913–1926. https://doi.org/10.1137/080734029
14. Zeller, K. A., McGarigal, K., & Whiteley, A. R. (2012). Estimating landscape resistance to movement: a review. *Landscape Ecology* 27(6):777–797. https://doi.org/10.1007/s10980-012-9737-0
15. Peterman, W. E. (2018). ResistanceGA: An R package for the optimization of resistance surfaces using genetic algorithms. *MEE* 9(6):1638–1647. https://doi.org/10.1111/2041-210X.12984
16. Hanks, E. M., & Hooten, M. B. (2013). Circuit theory and model-based inference for landscape connectivity. *JASA* 108(501):22–33. https://doi.org/10.1080/01621459.2012.724647
17. Bowman, J., et al. (2020). Effects of cost surface uncertainty on current density estimates from circuit theory. *PeerJ* 8:e9617. https://doi.org/10.7717/peerj.9617
18. Dertien, J. S., & Baldwin, R. F. (2023). Does scale or method matter for conservation? Application of directional and omnidirectional connectivity models in spatial prioritizations. *Frontiers in Conservation Science* 4. https://www.frontiersin.org/journals/conservation-science/articles/10.3389/fcosc.2023.976914/full
19. Martinez-Cillero, R., Siggery, B., Murphy, R., Perez-Diaz, A., Christie, I., & Chimbwandira, S. J. (2023). Functional connectivity modelling and biodiversity Net Gain in England: Recommendations for practitioners. *J. Environ. Manage.* 328:116857. https://www.sciencedirect.com/science/article/pii/S0301479722024306
20. Omniscape.jl issue #92, "Compute time doesn't seem to scale well with increasing number of threads past a certain point" (2021-03-09). https://github.com/Circuitscape/Omniscape.jl/issues/92
21. Heckford, bc-connectivity repository (README and `reports/`), 2026. https://github.com/Heckford/bc-connectivity
22. Omniscape.jl User Guide, `block_size`. https://docs.circuitscape.org/Omniscape.jl/stable/usage/
23. Belote, R. T., Barnett, K., Zeller, K., Brennan, A., & Gage, J. (2022). Examining local and regional ecological connectivity throughout North America. *Landscape Ecology* 37:2977–2990. https://link.springer.com/article/10.1007/s10980-022-01530-9
24. McRae, B. H., Hall, S. A., Beier, P., & Theobald, D. M. (2012). Where to restore ecological connectivity? Detecting barriers and quantifying restoration benefits. *PLoS ONE* 7(12):e52604. https://doi.org/10.1371/journal.pone.0052604
25. Linkage Mapper tools (Pinchpoint Mapper, Barrier Mapper, Centrality Mapper). https://linkagemapper.org/linkage-mapper-tools/
26. Moilanen, A., Franco, A. M. A., Early, R. I., Fox, R., Wintle, B., & Thomas, C. D. (2005). Prioritizing multiple-use landscapes for conservation: methods for large multi-species planning problems. *Proc. R. Soc. B* 272(1575):1885–1891. https://doi.org/10.1098/rspb.2005.3164
27. Moilanen, A., Lehtinen, P., Kohonen, I., Jalkanen, J., Virtanen, E. A., & Kujala, H. (2022). Novel methods for spatial prioritization with applications in conservation, land use planning and ecological impact avoidance. *MEE* 13(5):1062–1072. https://doi.org/10.1111/2041-210X.13819
28. Daigle, R. M., et al. (2020). Operationalizing ecological connectivity in spatial conservation planning with Marxan Connect. *MEE* 11(4):570–579. https://doi.org/10.1111/2041-210X.13349
29. Hamonic, F., Vaxès, Y., Couëtoux, B., & Albert, C. H. (2025). GECOT: Graph-based ecological connectivity optimization tool. *MEE* 16(9):1914–1922. https://doi.org/10.1111/2041-210X.70055
30. Van Moorter, B., Kivimäki, I., Panzacchi, M., Schouten, R., Wuyts, B., Niebuhr, B. B., Saerens, M., & Boussange, V. (2026). A unified framework for prioritizing habitat and connectivity conservation through analytical sensitivity. bioRxiv. https://www.biorxiv.org/content/10.64898/2026.01.05.697654v1
31. Boussange, V. (2025). JAXScape: A minimal JAX library for connectivity modelling at scale. Software (MIT), Zenodo doi:10.5281/zenodo.15267703. https://github.com/vboussange/jaxscape
32. Equihua, J., Beckmann, M., & Seppelt, R. (2024). Connectivity conservation planning through deep reinforcement learning. *MEE* 15(4):779–790. https://doi.org/10.1111/2041-210X.14300
33. Smith, C. C. R., Tittes, S., Ralph, P. L., & Kern, A. D. (2023). Dispersal inference from population genetic variation using a convolutional neural network. *Genetics* 224(2):iyad068. https://doi.org/10.1093/genetics/iyad068
34. Li, Z., et al. (2021). Fourier neural operator for parametric partial differential equations. *ICLR 2021*. https://arxiv.org/abs/2010.08895
35. Takamoto, M., et al. (2022). PDEBench: An extensive benchmark for scientific machine learning. *NeurIPS 2022 Datasets and Benchmarks*. https://arxiv.org/abs/2210.07182
36. Kossaifi, J., et al. (2024). A library for learning neural operators. arXiv:2412.10354. https://arxiv.org/abs/2412.10354
37. Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for biomedical image segmentation. *MICCAI 2015*, LNCS 9351:234–241. https://doi.org/10.1007/978-3-319-24574-4_28
38. Gupta, J. K., & Brandstetter, J. (2022). Towards multi-spatiotemporal-scale generalized PDE modeling. arXiv:2209.15616 (TMLR 2023). https://arxiv.org/abs/2209.15616
39. Battaglia, P. W., et al. (2018). Relational inductive biases, deep learning, and graph networks. arXiv:1806.01261. https://arxiv.org/abs/1806.01261
40. Pfaff, T., Fortunato, M., Sanchez-Gonzalez, A., & Battaglia, P. W. (2021). Learning mesh-based simulation with graph networks. *ICLR 2021*. https://arxiv.org/abs/2010.03409
41. Liu, X., Xu, B., Cao, S., & Zhang, L. (2024). Mitigating spectral bias for the multiscale operator learning. *J. Comput. Phys.* 506:112944. https://arxiv.org/abs/2210.10890
42. He, J., Liu, X., & Xu, J. (2024). MgNO: Efficient parameterization of linear operators via multigrid. *ICLR 2024*. https://arxiv.org/abs/2310.19809
43. Xu, B., Liu, X., & Zhang, L. (2024). Dilated convolution neural operator for multiscale partial differential equations. arXiv:2408.00775. https://arxiv.org/abs/2408.00775
44. Haltmayer, M., Seo, J., Lee, Y., Lee, S., Jeong, J., & Lee, J. Y. (2026). Deep learning-based surrogate modelling of the LOD method for multiscale problems. arXiv:2607.12570. https://arxiv.org/abs/2607.12570
45. Trifonov, V., Rudikov, A., Iliev, O., Laevsky, Y. M., Oseledets, I., & Muravleva, E. (2024). ConDiff: A challenging dataset for neural solvers of partial differential equations. arXiv:2406.04709. https://arxiv.org/abs/2406.04709
46. Lan, K. W., Gueidon, E., Kaneda, A., Panetta, J., & Teran, J. (2024). A neural-preconditioned Poisson solver for mixed Dirichlet and Neumann boundary conditions. *ICML 2024*, PMLR 235:25976–25994. https://proceedings.mlr.press/v235/lan24a.html
47. Li, Y., Chen, P. Y., Du, T., & Matusik, W. (2023). Learning preconditioners for conjugate gradient PDE solvers. *ICML 2023*, PMLR 202:19425–19439. https://proceedings.mlr.press/v202/li23e.html
48. Klamkin, M., Tanneau, M., & Van Hentenryck, P. (2025). PGLearn — An open-source learning toolkit for optimal power flow. arXiv:2505.22825. https://arxiv.org/abs/2505.22825
49. Lovett, S., et al. (2024). OPFData: Large-scale datasets for AC optimal power flow with topological perturbations. arXiv:2406.07234. https://arxiv.org/abs/2406.07234
50. Joswig-Jones, T., Baker, K., & Zamzam, A. S. (2021). OPF-Learn: An open-source framework for creating representative AC optimal power flow datasets. arXiv:2111.01228 (IEEE ISGT-NA 2022). https://arxiv.org/abs/2111.01228
51. Ohana, R., McCabe, M., et al. (2024). The Well: a large-scale collection of diverse physics simulations for machine learning. *NeurIPS 2024 Datasets and Benchmarks*. https://arxiv.org/abs/2412.00568
52. Bonnet, F., Mazari, J. A., Cinnella, P., & Gallinari, P. (2022). AirfRANS: High fidelity computational fluid dynamics dataset for approximating Reynolds-averaged Navier–Stokes solutions. *NeurIPS 2022 Datasets and Benchmarks*. https://arxiv.org/abs/2212.07564
53. Gebru, T., et al. (2021). Datasheets for datasets. *CACM* 64(12):86–92. https://doi.org/10.1145/3458723
54. NeurIPS 2026 Evaluations & Datasets Track, Call for Papers. https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets
