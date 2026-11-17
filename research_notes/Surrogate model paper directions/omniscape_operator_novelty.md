# Learning the Omniscape omnidirectional-connectivity operator with a scale-consistent architecture: novelty and design space

Researcher notes, 2026-10-19. Code-level facts about Omniscape come from the installed Omniscape.jl **v0.6.2** source (`julia_depot/packages/Omniscape/VSLPS/src/{utils.jl,main.jl,config.jl}` in this repo; upstream at https://github.com/Circuitscape/Omniscape.jl/tree/main/src). Upstream `main` may differ from v0.6.2 in line numbers. Anything marked "Inference" is my own reasoning or derivation, not a published claim.

## Q1. Has anyone published a learned surrogate of Omniscape, moving-window Circuitscape, or omnidirectional connectivity? What is the closest prior work?

### Takeaway
I found no published learned surrogate (CNN, U-Net, neural operator, GNN) of Omniscape, moving-window Circuitscape, pairwise Circuitscape, resistant kernels or UNICOR in any venue the search tools reached. The only hit that learns Omniscape is AmpScape itself (the owner's GitHub repo, which turns up in public web search). The nearest ML work is either a surrogate for a different "connectivity" notion (architectural space syntax) or ML that predicts genetic connectivity from data rather than emulating a circuit solver. On this evidence a scale-consistent Omniscape surrogate looks novel. This is not proof of absence, because Google Scholar, Web of Science and the journal sites were not queried directly (see Gaps).

### Search log (query → outcome)
| # | Query (WebSearch) | Outcome |
|---|---|---|
| 1 | `deep learning surrogate Circuitscape connectivity current density neural network` (extended) | No Circuitscape surrogate. Off-topic surrogates (electrolyzer current density, superconducting-circuit GNN, network reliability). One adjacent hit: "Deep learning surrogate models for spatial and visual connectivity" (arXiv 1912.12616), which is about architectural floor plans, not landscapes. |
| 2 | `Omniscape machine learning emulator omnidirectional connectivity` (extended) | Only ML hit was **github.com/Xyrro/AmpScape**, the owner's own project. Everything else was Omniscape docs, the JOSS paper, a SyncroSim wrapper, the Julia package page. |
| 3 | `"resistant kernels" Compton 2007 connectivity UNICOR cumulative resistant kernel` | Original method papers and applications only. No ML surrogate. |
| 4 | `convolutional neural network predict landscape connectivity map circuit theory resistance surface` (extended) | No CNN connectivity surrogate. Returned a comparative connectivity-model evaluation that uses 256x256 simulated resistance surfaces (Sci Rep 2022), a circuit-theory occupancy-model preprint, and ResistanceGA. |
| 5 | `deep learning emulate circuit theory connectivity Circuitscape graph neural network ecology` (extended) | Nothing on point (neuroscience connectomics, EDA circuit GNNs). |
| 6 | `neural network surrogate landscape connectivity model resistance kernel least-cost "deep learning" fast approximation 2024 2025` (extended) | Nothing on point (kernel surrogates for NTK, aerodynamics). |
| 7 | `U-Net OR CNN "Circuitscape" OR "Omniscape" emulation speedup connectivity prediction` (extended) | No emulation paper. Circuitscape/Omniscape docs, the R package `circuitscaper`, a CFD U-Net, and arXiv 1912.12616 again. |
| 8 | `bioRxiv machine learning approximate circuit theory current flow landscape genetics connectivity surrogate model` (extended) | No surrogate. Adjacent: random-forest genetic-connectivity mapping (PNAS 2021), "Graph Learning for Inverse Landscape Genetics" (arXiv 2006.12334), circuit-theory occupancy model (bioRxiv 2023). |
| 9 | `McRae 2016 Omniscape "omnidirectional" Pacific Northwest ...` | Primary-source metadata for the McRae et al. 2016 report (below). |
| 10 | `Omniscape radius sensitivity cumulative current increases with radius flow potential normalization` | No quantitative radius-scaling study. Docs and vignettes only (see Q4). |

### Cited Findings
- AmpScape is indexed by public web search as "a benchmark dataset and evaluation suite for learned surrogates of circuit-theoretic landscape connectivity (Circuitscape / Omniscape)", with a task "T4 Omnidirectional connectivity (Omniscape)". It is the only search result that learns Omniscape. — [GitHub Xyrro/AmpScape](https://github.com/Xyrro/AmpScape)
- Closest "connectivity surrogate" in ML: CNN surrogates trained on simulation outputs to approximate spatial and visual connectivity analyses of floor plans (architecture and space syntax, not ecological circuit theory). — [arXiv 1912.12616](https://arxiv.org/pdf/1912.12616)
- Closest ML-for-landscape-connectivity work is data-driven rather than solver emulation. A random forest predicts genetic distance for *Aedes aegypti* from environmental covariates (reported R = 0.83) and maps genetic connectivity. — [PNAS 2021, doi 10.1073/pnas.2003201118](https://www.pnas.org/doi/pdf/10.1073/pnas.2003201118)
- Graph learning for inverse landscape genetics, which learns resistance from genetic data using effective resistance as the connectivity measure. This is an inverse problem, not a forward surrogate. — [arXiv 2006.12334](https://arxiv.org/pdf/2006.12334)
- Circuit theory (commute distance) built into spatial occupancy models. This is a statistical model, not a surrogate. — [bioRxiv 10.1101/2023.09.26.559320](https://www.biorxiv.org/content/10.1101/2023.09.26.559320v1)
- Resistant kernels (Compton, McGarigal, Cushman & Gamble 2007, *Conservation Biology*, "A resistant-kernel model of connectivity for amphibians that breed in vernal pools") modify a kernel density estimator so the kernel spreads by cost-distance from each focal pixel up to a maximum distance. Summing these gives "cumulative resistant kernels" (UNICOR). It is a moving-window, sum-over-sources construction like Omniscape, but built on cost-distance rather than current, and no learned surrogate was found. — [USDA FS RMRS 2007 Compton](https://www.fs.usda.gov/rm/pubs_other/rmrs_2007_compton_b001.pdf); [USDA FS RMRS 2014 (cumulative resistant kernels, black bear)](https://www.fs.usda.gov/rm/pubs_journals/2014/rmrs_2014_hand_b001.pdf)
- Omniscape origin: McRae, Popper, Jones, Schindel, Buttrick, Hall, Unnasch & Platt (2016), *Conserving Nature's Stage: Mapping Omnidirectional Connectivity for Resilient Terrestrial Landscapes in the Pacific Northwest*, The Nature Conservancy, Portland OR, 47 pp. Described as "a moving window implementation of CircuitScape". — [ScienceBase record](https://sciencebase.gov/catalog/item/5807ba6de4b0841e59e3a494); [Data Basin dataset](https://databasin.org/datasets/f5ff92497fb44012869981b4bbebd2eb/)
- Omniscape.jl: Landau, Shah, Anantharaman & Hall (2021), JOSS 6(57), 2829, doi 10.21105/joss.02829. The original Omniscape code was Python and was not a user-friendly package. — [JOSS PDF](https://www.theoj.org/joss-papers/joss.02829/10.21105.joss.02829.pdf)

### Inferences
- The "learned Omniscape" niche is open in the literature I could reach, and so is the narrower "learned surrogate that transfers across Omniscape radius / raster size / pixel size by construction". A paper claiming novelty would still need a direct Google Scholar / Web of Science pass (queries in Gaps) before submission.
- The resistant-kernel / UNICOR family has the same window-sum structure (per-source local kernel, truncated at a distance, summed). A window-structured learned operator would therefore plausibly carry over to resistant kernels, a possible generality claim.
- **Disclosure flag for the owner:** `github.com/Xyrro/AmpScape` appears in public web search results, so the GitHub repo appears to be publicly visible even though the HF dataset is private. This affects anonymity for double-blind review and the "no public artifact without approval" gate. Worth checking the repo's visibility.

### Gaps
- Not run: direct Google Scholar, Web of Science, Scopus, or the journal sites' own search for Ecological Informatics, Landscape Ecology, MEE, Ecography. Suggested exact queries: `"Omniscape" neural`, `"Circuitscape" "neural network"`, `"Circuitscape" surrogate`, `"current density" landscape "deep learning"`, `"resistant kernel" "neural network"`, `ConScape` (Van Moorter et al., a related randomized-shortest-path tool that was not searched).
- Grey literature (theses, conference posters such as IALE or ESA) is not covered.
- Could not verify whether UNICOR has any ML acceleration. No UNICOR documentation surfaced.

## Q2. Which ML structures fit (Green's-function or superposition learning, compact-support kernels, windowed operators, scale-equivariant CNNs, parameter-conditioned operators, resolution invariance)?

### Takeaway
The building blocks all exist separately: Green's-function learning (Boullé et al.; Neural Green's Functions), compactly supported local integral kernels in neural operators (Liu-Schiaffini et al., ICML 2024), scale-equivariant CNNs (Sosnovik et al. ICLR 2020; Worrall & Welling NeurIPS 2019; Ghosh & Gupta 2019), and PDE-parameter conditioning (CAPE, ICML 2023; FiLM, AAAI 2018). None was found combined into a "learned per-window operator plus exact Omniscape aggregation" or applied to connectivity. Omniscape has three properties that change which designs fit (Q3): a per-window absolute value, per-target re-grounding, and per-window normalization of sources. Because of them, Omniscape is **not** a single linear Green's-function operator on the global source field.

### Cited Findings
- **Green's-function learning.** Boullé, Earls & Townsend learn Green's functions of hidden linear PDEs with rational neural networks from responses to Gaussian-process forcings (Sci Rep 2022). — [arXiv 2105.00266](https://arxiv.org/abs/2105.00266v2)
- **Neural Green's Functions** (Yoo et al., NeurIPS 2025) predict an eigendecomposition-style factorization of the solution operator from per-point domain features and so generalize across geometries. They report 13.9% average error reduction and up to 350x speed-up over a numerical solver on a thermal task. The paper notes that earlier Green's-function learners (Boullé; Teng et al.) are tied to one domain and need retraining for new geometries. — [arXiv 2511.01924](https://arxiv.org/abs/2511.01924)
- **Localized (compact-support) kernels.** Liu-Schiaffini, Berner, Bonev, Kurth, Azizzadenesheli & Anandkumar (ICML 2024) add local integral kernels (discrete-continuous convolutions) and differential kernels to FNOs while keeping resolution-agnostic prediction, with a 34-72% rel-L2 reduction. — [arXiv 2402.16845](https://arxiv.org/abs/2402.16845v2); [PMLR v235](https://proceedings.mlr.press/v235/liu-schiaffini24a.html)
- **Scale-equivariant CNNs.** Sosnovik, Szmaja & Smeulders, *Scale-Equivariant Steerable Networks* (ICLR 2020), use steerable multi-scale filter bases and scale-convolutions. Their paper notes that Ghosh & Gupta (2019) pre-compute multi-scale filters for scale *invariance* and that Worrall & Welling (2019) handle only integer downscale factors. — [arXiv 1910.11093](https://arxiv.org/abs/1910.11093)
- Worrall & Welling, *Deep Scale-spaces: Equivariance Over Scale* (NeurIPS 2019), give scale-equivariant cross-correlations from scale-space and semigroup theory, plug-and-play in standard architectures. — [arXiv 1905.11697](https://arxiv.org/abs/1905.11697v1)
- Ghosh & Gupta (2019), "scale steerable filters for locally scale-invariant CNNs". **Not directly verified.** It is known here only through Sosnovik et al.'s related-work description. — [arXiv 1910.11093 (secondary)](https://ar5iv.arxiv.org/html/1910.11093)
- **Parameter conditioning.** CAPE (Takamoto, Alesiani & Niepert, ICML 2023) is a channel-attention module driven by an MLP embedding of PDE parameters. It can be added to any neural PDE solver to adapt to unseen parameters, with little extra inference cost. — [arXiv 2304.14118](https://arxiv.org/abs/2304.14118v2); [PMLR v202](https://proceedings.mlr.press/v202/takamoto23a.html)
- FiLM (Perez, Strub, de Vries, Dumoulin & Courville, AAAI 2018) is a feature-wise affine modulation from conditioning information. — [arXiv 1709.07871](https://arxiv.org/abs/1709.07871v2)

### Inferences (design space, mapped onto Omniscape's exact structure; see Q3 for the code facts)
Write the Omniscape cumulative map as $C(x)=\sum_{t\in T} \kappa_t(x)\,\big|J\big[g|_{D(t,r)},\ \tilde s_t\big](x)\big|$. Here $D(t,r)$ is the clipped disk (insulating outside, since clipped cells become no-data), $\tilde s_t$ is the window's sources rescaled to sum to the target amps $A_t$, the target block is zeroed, $t$ is grounded, $J$ is the branch-current magnitude map, and $\kappa_t$ is the block-artefact correction.

1. **Exact-structure surrogate ("learned window operator plus exact aggregation").** Learn $K_\theta: (g|_D, \tilde s_t)\mapsto$ window current map on a canonical disk, then scatter-add over targets as Omniscape does.
   - Transfer: raster size transfers by construction. Block size, source threshold, `correct_artifacts` and buffer become exact, solver-free bookkeeping.
   - Radius does not transfer unless $K_\theta$ is radius-conditioned (FiLM/CAPE on $r$) or defined on a normalized disk with a learned or analytic radius law.
   - The per-window problem is a grounded, Neumann-boundary Green's-function problem. Green's-function learners fit here, but only per window: the global map is a sum of absolute values of per-window fields with different groundings, so it cannot be collapsed into one linear operator.
   - Cost: still $N_T$ network evaluations on $(2r+1)^2$ patches. Cheaper than $N_T$ sparse solves on GPU, but far more than one forward pass. Training data come almost for free, because each Omniscape run yields $N_T$ window solves if per-window maps are dumped. Omniscape does not expose them; they would need instrumentation.
2. **Amortized fully-convolutional surrogate with structure priors** (closest to the current U-Net).
   - Predict normalized current $C/F$ (Omniscape's own `normalized_cum_currmap = cum_currmap ./ fp_cum_currmap`, main.jl). Then multiply by a cheap flow-potential estimate $F$. The radius-linear factor lives in $F$ (Q4), so the network only learns an O(1) channelization field.
   - $F$ depends only on sources, radius and block size, and resistance is fixed at 1. It is approximately a fixed-kernel computation and could be precomputed analytically or by a small separately learned model.
   - Condition on $r$ (in pixels) and on pixel size via FiLM/CAPE.
   - Use a receptive field at least $2r$, or localized integral kernels with support tied to $r$ (Liu-Schiaffini-type DISCO kernels give compact support in physical units, so changing $r$ means rescaling the support).
3. **Scale-consistency by resampling (test-time, no retraining).** Under joint coarsening by factor $\lambda$ (source summed per coarse pixel, conductance averaged, radius $r/\lambda$), the homogeneous scaling law of Q4 gives $C_r \approx \lambda^{-1}\,U_\lambda[\,C_{r/\lambda}(D_\lambda g, D_\lambda s)\,]$. A model trained at $r=64$ could then be evaluated at $r=256$ by down-sampling by 4. Resistance coarsening is only approximate (series/parallel averaging), so this needs empirical testing. It is a cheap ablation that fits AmpScape's existing XL tier.
4. **Scale-equivariant layers (SESN / Deep Scale-spaces).** The relevant symmetry is not plain image-scale equivariance. It is a joint action: spatial scale, radius shift, and amplitude scaling by $\lambda$ (Q4). SESN-style scale channels could encode it if the radius enters as a scale index. Scale-invariant designs (Ghosh & Gupta) are the wrong target, because the output amplitude must change with scale.
5. **Invariances to hard-code, all exact from the algorithm** (Inference from the code in Q3):
   - Window currents are invariant to multiplying all conductances by a constant, because sources are current injections.
   - The cumulative map is linear in a global source scale, because target amps and per-window injection both scale.
   - Global translation is equivariant except at raster edges, where windows are clipped. Edge clipping is part of the operator, so a CNN with zero padding is not exactly consistent there.

### Gaps
- No published work found that conditions a neural operator on a window or kernel support radius specifically. Searched implicitly via the CAPE/FiLM and localized-kernel queries; not searched explicitly.
- Teng et al. (Gaussian-delta Green's-function regression) is known only via the Neural Green's Functions paper; not verified.
- Patch- or window-based neural operators (e.g. domain-decomposition neural operators, multipole graph neural operators) were not searched in this pass.

## Q3. How do Omniscape's parameters and block-artefact correction work exactly, and what is the cost structure a learned single-window operator would save?

### Takeaway
Omniscape grids targets every `block_size` pixels, giving each the summed source strength of its block. For each target it clips the resistance to a disk of radius `radius`+`buffer`, injects current equal to the target's amps (distributed among in-radius sources proportional to strength, with the target block zeroed), grounds the target, and scatter-adds the current map. With `block_size > 1` and `correct_artifacts = true` (the default), each window map is multiplied elementwise by one precomputed correction array: the ratio of "unblocked" to "blocked" null-resistance currents. Cost is about $N_T \approx (H/b)(W/b)$ sparse solves of about $\pi (r+\text{buffer})^2$ unknowns each, doubled when flow potential is computed.

### Cited Findings
- Algorithm (verbatim structure): the window centres on a target pixel with source strength greater than 0 (or a threshold). Both rasters are clipped to the circular window. Every in-radius source pixel greater than 0 is a source. Circuitscape runs in "advanced" mode with the target grounded. "The total amount of current injected is equal to the source strength of the target pixel, and is divvied up among the source pixels in proportion to their source strengths." Window maps are summed. — [Landau et al. 2021, JOSS](https://www.theoj.org/joss-papers/joss.02829/10.21105.joss.02829.pdf); [Omniscape.jl docs, algorithm page](https://docs.circuitscape.org/Omniscape.jl/stable/algorithm/)
- Flow potential is computed "exactly as cumulative current flow, but with resistance set to one". Normalized current = cumulative current / flow potential. Values above 1 mean channelized, below 1 impeded. — [JOSS](https://www.theoj.org/joss-papers/joss.02829/10.21105.joss.02829.pdf). Code confirms `normalized_cum_currmap = cum_currmap ./ fp_cum_currmap`, with NaN set to 0. — [main.jl](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/main.jl). Note that one docs example page describes the ratio the other way round, per search snippet. The code and JOSS agree on cum/FP.
- `block_size`: "An odd, positive integer specifying the side length for source layer blocking in target generation." Only block centres are targets, with "a new source strength equal to the sum of the 9 pixels in the 3x3 block", so "the total amount of current injected will be the same regardless of the value of block_size". Block size "can significantly reduce compute times and result in only negligable differences". Example: 81 solves at b=1 vs 9 at b=3. — [Omniscape.jl User Guide](https://docs.circuitscape.org/Omniscape.jl/stable/usage/)
- `buffer` (default 0): extra clip distance beyond `radius`. Sources in the buffer ring are set to 0, but the resistance is kept. `source_threshold` (default 0): pixels below it are not sources. `radius`: "radius in pixels of the moving window". `r_cutoff` / `source_from_resistance`: sources = 1/resistance, set to 0 above `r_cutoff`. — [User Guide](https://docs.circuitscape.org/Omniscape.jl/stable/usage/)
- Defaults in code: `block_size = "1"`, `correct_artifacts = "true"`. — [config.jl](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/config.jl). The User Guide page fetched did not document `correct_artifacts`, so its behaviour below comes from source.
- **Target generation** (`get_targets`, utils.jl): targets on the grid `start = block_radius+1` with stride `block_size` in x and y. Amps = sum of sources in the b x b block. Targets with amps of 0 are dropped. — [utils.jl](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/utils.jl)
- **Window source** (`get_source`): clip sources to the disk of radius `radius` (`clip` sets cells with Euclidean distance > r to missing), pad by `buffer`, zero the target's own b x b block, then rescale `source = source * target.amps / sum(source)`. Conditional source/target matching is applied after that. — [utils.jl](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/utils.jl)
- **Window conductance** (`get_conductance`): resistance clipped to a disk of radius `radius+buffer`, then inverted unless `resistance_is_conductance`. The ground is the target pixel. — [utils.jl](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/utils.jl)
- **Per-target work** (`solve_target!`): one Circuitscape solve for current. If flow potential is requested, a second solve on the same source/ground with conductance 1 everywhere. If `correct_artifacts && block_size != 1`, both maps are multiplied elementwise by `correction_array` (cropped at raster edges). The result is scatter-added into `cum_currmap` (and `fp_cum_currmap`) over the window's bounding box. — [utils.jl](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/utils.jl)
- **Artefact correction** (`calc_correction`), computed once per run on a homogeneous (all-ones) disk:
  - (a) `block_null_current`: current for a blocked target (amps = b², sources via `get_source`, so the target block is zeroed and the rest is uniform).
  - (b) `null_current`: an unblocked target, with every in-disk pixel except the centre given 1/(n_sources-1).
  - (c) `null_current_total`: (b) summed over all b x b shifts of the centre within the block, then cropped back.
  - correction = (c) ./ (a), with zeros guarded to 1.
  - It is therefore a fixed, resistance-independent multiplicative kernel that makes a blocked solve mimic the sum of b² unblocked solves under null resistance.
  - — [utils.jl](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/utils.jl)
- Multithreading: window solves are independent and solved in parallel with Julia threads. — [JOSS](https://www.theoj.org/joss-papers/joss.02829/10.21105.joss.02829.pdf)
- A larger radius "increases computation time substantially" according to an R-wrapper vignette. Not quantified. — [circuitscaper vignette](https://cran.r-project.org/package=circuitscaper)

### Inferences (cost structure)
- Number of solves: $N_T \le \lceil H/b\rceil\lceil W/b\rceil$, minus all-zero blocks, times 2 if flow potential is requested. Each solve has about $\pi(r+\text{buffer})^2$ unknowns.
  - Example: H = W = 1024, b = 5, r = 64 gives about 41.6k solves of about 12.9k unknowns.
  - At r = 256 the solve count is the same but each solve has about 206k unknowns, 16x more.
  - A sparse direct 2-D solve scales as about $n^{1.5}$ (nested dissection) and AMG-PCG as about $n$. So the total grows like $HW\,r^{2}$ to $HW\,r^{3}/b^2$.
  - The output is independent of b to first order (docs), so b is a pure accuracy/cost knob.
- What a learned single-window operator saves: it replaces each sparse solve with a fixed-cost patch inference, but the $N_T$-fold loop remains. The large saving is only achieved by amortizing the window sum into one fully convolutional pass (design 2 in Q2). The window-operator design is most valuable as (i) a structural prior or teacher, (ii) a component that makes raster size, block size, buffer, threshold and edge clipping exact, and (iii) a source of $N_T$ cheap training pairs per Omniscape run.
- Because `correction_array` is resistance-independent and precomputable, and source rescaling and target gridding are exact arithmetic, a structure-consistent surrogate only needs to learn the windowed solve $|J[g|_D,\tilde s_t]|$. Everything else can be copied from Omniscape exactly.
- Since window maps are absolute currents and each window is grounded at its own target, $C$ is nonlinear in the source field: Omniscape is not $\int G(x,y)s(y)\,dy$ for any single $G$. This rules out a pure global Green's-function surrogate and favours a per-window or amortized design.

### Gaps
- The McRae et al. 2016 report PDF was not read, so the original Python implementation details and the reasoning behind artefact correction are unverified.
- No published Omniscape runtime benchmarks (seconds per solve, scaling with r) were found. The AmpScape project's own timings (paper appendix, "Omniscape parallelize timing") are the best available numbers.

## Q4. Are there published scaling laws or theory for how omnidirectional current scales with radius?

### Takeaway
I found no published scaling law for Omniscape cumulative current versus radius. The docs only say a larger radius admits more pairs and costs more. A short continuum derivation (Inference) gives $C \approx \tfrac{2}{3}\,s\,r$ in a homogeneous interior with uniform source density $s$ per pixel, independent of b. This reproduces exactly the observed transfer error $1-r_{\text{train}}/r_{\text{eval}}$. It also predicts that normalized current (cum/FP) is O(1) and approximately radius-invariant to leading order, so radius transfer should target normalized current or an explicitly $r$-scaled output.

### Cited Findings
- Omniscape evaluates connectivity for pairs no further apart than the window radius. Cumulative current is the sum over windows. — [Omniscape.jl docs](https://docs.circuitscape.org/Omniscape.jl/stable/algorithm/)
- Each window injects total current equal to the target's amps (block-summed source strength). This does not depend on r. — [JOSS](https://www.theoj.org/joss-papers/joss.02829/10.21105.joss.02829.pdf); [utils.jl `get_source`](https://github.com/Circuitscape/Omniscape.jl/blob/main/src/utils.jl)
- Flow potential uses resistance 1 and otherwise identical computation. — [JOSS](https://www.theoj.org/joss-papers/joss.02829/10.21105.joss.02829.pdf)
- Search outcome: query 10 found docs and vignettes only, with no quantitative radius-scaling study. — [Omniscape.jl examples](https://docs.circuitscape.org/Omniscape.jl/stable/examples/)

### Inferences (derivation; mine, not published)
**Homogeneous radius law.**
- Assumptions: homogeneous conductance, uniform source density $s$ (amps per pixel), target amps $A=s b^2$, sources uniform in the disk of radius $r$ (target block excluded), grounded at the centre, insulating disk boundary.
- By Gauss's law, the radial current crossing the circle of radius $\rho$ equals $A(1-\rho^2/r^2)$. The current density is $j(\rho)=A(1-\rho^2/r^2)/(2\pi\rho)$.
- Summing over targets on a b-grid within distance $r$ of pixel $x$: $C(x)\approx b^{-2}\int_0^r j(\rho)\,2\pi\rho\,d\rho = (A/b^2)(r - r/3) = \tfrac{2}{3}s\,r$.
- So $C$ is linear in $r$ and independent of $b$, consistent with the docs' claim that block size has negligible effect. The rel-L2 error of predicting $C_{r_1}$ when the truth is $C_{r_2}$ is $1-r_1/r_2$, matching the AmpScape observation exactly.
- Corrections:
  - A $\log$-type near-target term from the singular $1/\rho$ near each sink, of lower order.
  - Edge effects within $r$ of the raster boundary, where fewer windows cover a pixel and $C$ drops.
  - Heterogeneity enters through the normalized field.

**Normalized current.** FP obeys the same law ($F\approx\tfrac23 s r$ in the homogeneous interior), so $C/F$ is O(1). Its radius dependence comes only from how channelization averages over windows of different size. This is the quantity a radius-transferable model should learn; the AmpScape recovery from 1.0 to 0.19-0.32 by dividing by the radius ratio is the first-order version of this.

**Pixel size.** Radius is in pixels. At fixed physical radius $R$ and pixel width $\Delta$ with source density $\sigma$ per unit area ($s=\sigma\Delta^2$, $r=R/\Delta$), $C\approx\tfrac23\sigma\Delta R$. Per-pixel current scales with pixel width (current through a wider pixel). This gives the resampling rule in Q2 design 3: $C_{\text{fine}} \approx \lambda^{-1}U_\lambda[C_{\text{coarse}}]$.

**Invariances.** Conductance scale-invariance and source-scale linearity (Q2) are exact. Together with the radius law they fix the output's units, so a model can be made exactly consistent with them by construction: input normalization plus output multiplied by $s\,r$ or by $F$.

### Gaps
- No peer-reviewed source states the radius law. It should be checked numerically (homogeneous raster, several r and b) before it is used as a claim. AmpScape already has the data to do so.
- The heterogeneous case has no closed form. Whether $C/F$ is radius-stable on real resistance surfaces is an empirical question; no published sensitivity analysis was found.
