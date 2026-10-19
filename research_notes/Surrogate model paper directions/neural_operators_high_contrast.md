# Learned surrogate architectures (2023-2026) for high-contrast elliptic PDEs with point sources on large grids

Scope note: these notes come from about 21 search/fetch calls on 2026-10-19. "Verified" means I read the number or claim this session on the linked page (arXiv abstract or HTML, or the PDF text extracted with pdftotext). Items tagged **[not fetched]** cite well-known papers whose URL I give from prior knowledge. I did not open those pages this session, so their numbers are deliberately left out. Relevance to AmpScape: contrast up to 1e6, single-pixel sources and grounds, NoData holes, 8-neighbour graph Laplacian, 128^2-2048^2.

**Main cross-cutting finding.** Every neural-operator benchmark I could verify uses a coefficient contrast of order 10^0-10^1. One example is the "Darcy rough" two-phase field with values 12 and 2, a contrast of 6. None reports training at 1e5-1e6 contrast or with point sources. High-contrast robustness (10^4-10^6) shows up only in the *learned-preconditioner / learned-coarse-space* literature, where the network sits inside an iterative solver.

---

## Q1. Multigrid and hierarchical neural operators (MgNO, U-NO, MWT, HANO, DCNO, Transolver/++, CNO, GNOT, LNO)

### Takeaway
On rough or multiscale Darcy at low contrast (around 6), the hierarchical and multigrid operators (MgNO, HANO, DCNO) beat FNO, U-NO, MWT and GT by roughly 2-5x in relative L2. MgNO is also the smallest and fastest model in its comparison. All of these numbers are at 256^2-512^2, with contrast far below AmpScape's. On the standard FNO Darcy set, attention-based geometry operators (Transolver, LANO) reach about 0.5% rel-L2 but are reported to err along coefficient interfaces.

### Cited Findings
- **MgNO (He, Liu, Xu; arXiv 2310.19809, v3 Jun 2024; the arXiv page lists no venue, though the task brief calls it ICLR 2024).** It parameterizes each linear operator with a V-cycle multigrid structure and has no lifting or projection layers. It "handles diverse boundary conditions" — [arXiv abs](https://arxiv.org/abs/2310.19809)
- MgNO Table 1 (rel L2 / H1 ×10^-2; Darcy rough at 256^2):

  | Model | Smooth L2 | Rough L2 | Rough H1 | Multiscale L2 | Params |
  |---|---|---|---|---|---|
  | FNO | 0.684 | 1.613 | 7.516 | 1.800 | 2.37M |
  | U-NO | 0.492 | 1.023 | 3.784 | 1.187 | 16.39M |
  | MWT | — | 1.138 | 4.107 | 1.021 | 9.80M |
  | GT | 0.945 | 1.790 | 6.269 | 1.052 | 2.22M |
  | LSM | 0.601 | 2.658 | 4.446 | 1.050 | 4.81M |
  | U-Net | 2.169 | 3.519 | 5.795 | 1.425 | 17.27M |
  | **MgNO** | **0.176** | **0.339** | **1.380** | **0.715** | **0.57M** |

  MgNO trains at 6.6 s/iter against 7.4 s/iter for FNO. Darcy uses 6 multigrid levels. In the NS ablation, error goes from 1.63 (5 levels) to 2.10 (4 levels) to 2.44 (3 levels), so depth of the hierarchy matters — [arXiv HTML v3](https://arxiv.org/html/2310.19809v3)
- MgNO resolution transfer (Darcy multiscale, trained at low resolution, which appears to be 64, tested at 128/256/512): MgNO L2 goes from 1.032 to 1.205 (×10^-2), while FNO goes from 5.28 to 9.11. The paper reports that MgNO "converges quickly without overfitting", while MWT, U-NO and LSM reach similar training error but much higher test error. It reports **no divergence**. This contrasts with AmpScape's 4/6 diverged runs, but the paper's contrast is low (exact a_max/a_min not stated) — [arXiv HTML v3](https://arxiv.org/html/2310.19809v3)
- MgNO on Helmholtz at 100^2: L2 0.71e-2 against FNO 1.69e-2 and U-NO 1.26e-2 — [arXiv HTML v3](https://arxiv.org/html/2310.19809v3)
- **DCNO (Xu, Liu, Zhang; arXiv 2408.00775, Jul 2024).** It interleaves Fourier layers (low-frequency global modes) with dilated convolutions (local high-frequency detail). Table 1 (rel L2 ×10^-2, mean ± sd):

  | Model | Darcy rough | Trigonometric | Params | Time/epoch at 256^2 |
  |---|---|---|---|---|
  | FNO | 1.749 | 1.744 | 2.37M | 5.65 s |
  | MWT | 1.289 | 0.929 | 9.81M | 17.94 s |
  | U-NO | 1.159 | 1.183 | 16.39M | 8.71 s |
  | GT | 1.351 | 1.073 | 2.22M | 35.25 s |
  | HANO | 0.556 | 0.594 | 8.65M | 9.92 s |
  | DCNO | **0.531** | **0.541** | 2.51M | 10.14 s |

  The Darcy rough coefficient takes values 12 and 2 (**contrast 6**), with roughness c = 9 or 20. References are on 512^2 (Darcy) and 1023^2 (trigonometric) grids; there are 1000 training samples. The paper says DCNO reduces error "across all frequencies", with faster decay at high frequencies — [arXiv HTML](https://arxiv.org/html/2408.00775v1)
- The DCNO paper says FNO and GT "have shown spectral bias" on multiscale PDEs, and that the FNO pointwise path does not capture high-frequency information — [arXiv HTML](https://arxiv.org/html/2408.00775v1)
- **HANO (Liu, Xu, Cao, Zhang; arXiv 2210.10890).** Hierarchical-matrix-inspired attention with a scale-adaptive interaction range across levels, plus an **empirical H1 loss** to emphasize high-frequency components. It captures solution derivatives on the trigonometric multiscale benchmark, where FNO captures only the "homogenized" behaviour. A JCP publication is commonly cited, but I could not confirm the journal this session — [arXiv](https://arxiv.org/pdf/2210.10890); [NSF PAR copy](https://par.nsf.gov/servlets/purl/10504166)
- **Transolver / attention operators on the standard FNO Darcy set** (rel L2 ×10^-2, from the LANO comparison table): FNO 1.08, geo-FNO 1.08, U-NO 1.13, F-FNO 0.77, GNOT 1.05, ONO 0.76, Transolver 0.57. LANO (Zhong & Yan, arXiv 2510.16816) reports 21.1% better than Transolver, which works out to about 0.45 (my arithmetic). LANO states that "Transolver exhibits large deviations along material interfaces where a(x) changes abruptly" — [LANO arXiv 2510.16816 (PDF)](https://arxiv.org/pdf/2510.16816)
- **Transolver++ (Luo, Wu et al., ICML 2025).** Adds local adaptive slicing and multi-GPU parallelism for million-point inputs, and reports "13% relative promotion across six standard PDE benchmarks". I did not retrieve a Darcy-specific number — [arXiv 2502.02414](https://arxiv.org/pdf/2502.02414); [ICML poster](https://icml.cc/virtual/2025/poster/46177)
- **CNO (Raonić et al., arXiv 2302.01178; NeurIPS 2023).** A continuous-discrete-equivalent U-Net-style operator, evaluated on a "representative PDE benchmark" with multiscale solutions. I did not retrieve its Darcy/Poisson numbers this session — [arXiv abs](https://arxiv.org/abs/2302.01178)
- **U-NO** [not fetched]: [arXiv 2204.11127](https://arxiv.org/abs/2204.11127). **MWT** [not fetched]: [arXiv 2109.13459](https://arxiv.org/abs/2109.13459). **GNOT** [not fetched]: [arXiv 2302.14376](https://arxiv.org/abs/2302.14376). **Transolver** [not fetched directly; numbers above come via LANO]: [arXiv 2402.02366](https://arxiv.org/abs/2402.02366). **LNO (Latent Neural Operator)** [not fetched]: [arXiv 2406.03923](https://arxiv.org/abs/2406.03923).

### Inferences
- The low-contrast results ranking MgNO ≈ DCNO ≈ HANO > U-NO/MWT > FNO line up with AmpScape's finding that errors are high-frequency, near sources and along flow paths. Two cheap moves follow from the ablations: (a) an **H1 / gradient loss**, as in HANO and in LANO's "rel L2 + 0.1 L∇" Darcy loss, and (b) a deeper multigrid hierarchy. With 6 levels at 256^2, a 2048^2 grid needs about 9 levels to reach a similar coarsest grid.
- The MgNO divergence in AmpScape is probably tied to the 1e6 contrast, since none of the papers above trains beyond a contrast of about 10. A plausible fix is input normalisation (log-conductance, which AmpScape may already use), plus normalising per-sample targets by source strength. This is inference only.
- Transolver-style slice attention reportedly fails at sharp coefficient interfaces even at contrast around 4-6. That makes it a poor candidate for 1e6 without local mechanisms (Transolver++ adds "local adaptive" slicing).

### Gaps
- No paper found trains a neural operator at 1e4-1e6 contrast on an end-to-end surrogate task.
- I did not get exact Darcy numbers for CNO, GNOT, LNO or Transolver++, or costs at 1024^2-2048^2. None of the verified tables goes above 512^2 (MgNO-high-in uses 512^2 input).
- HANO's JCP venue was not confirmed.

---

## Q2. Green's-function / fundamental-solution learning and singularity handling for point sources

### Takeaway
The 2024-2026 Green's-function literature consistently **separates the singular part analytically** (known fundamental solution or parametrix) and learns only a smooth remainder, or lifts the kernel into a higher dimension to regularize it. Most work is on continuous variable-coefficient elliptic operators at small scale. I found none on large variable-coefficient graph Laplacians, but the structure carries over directly to AmpScape's K point sources.

### Cited Findings
- **SDC-GON (arXiv 2609.23206).** Splits G into an analytically known singular part plus a learned smooth correction, and adds a regularizer for consistency between G and ∇G. Its stated motivation is that the singularity near the source point places a hard approximation burden on networks — [arXiv HTML](https://arxiv.org/html/2609.23206)
- **Kernel decomposition (arXiv 2610.09101).** For self-adjoint second-order elliptic operators, it removes the singular part (analytic, or via a Laplace parametrix) and recasts the problem as learning a boundary extension operator — [arXiv HTML](https://arxiv.org/html/2610.09101)
- **Singularity-encoded Green's functions (arXiv 2509.11580; JCP 2026).** Unsupervised. It lifts G with an augmented variable to gain regularity, and uses the learned G as a **preconditioner or inside hybrid iterative solvers** (2D and 4D) — [arXiv PDF](https://arxiv.org/pdf/2509.11580v1); [JCP](https://www.sciencedirect.com/science/article/abs/pii/S0021999126002445)
- **BIN-G / domain-independent Green's function (CMAME 2024).** For variable-coefficient elliptic PDEs, using an RBF kernel refined near the singularity — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0045782524000355)
- **GreensONet (arXiv 2412.16644).** A DeepONet-based learned Green's function with binary-structured networks for near-diagonal singular behaviour — [Pith summary](https://pith.science/paper/2412.16644) (secondary aggregator; primary arXiv page not fetched)
- **Neural Green's Functions (Yoo, Yeo, Hwang, Sung; NeurIPS 2025, arXiv 2511.01924).** For linear PDEs with eigendecomposable operators: it predicts a decomposition of the solution operator from point-cloud features and evaluates solutions by integration. It reports 13.9% lower error than SOTA neural operators on steady thermal analysis (MCB dataset), and up to 350x speed-up over a meshing solver. The search snippet was consistent with the abstract — [arXiv](https://arxiv.org/abs/2511.01924); [NeurIPS poster](https://neurips.cc/virtual/2025/poster/115639)
- **Neural Green's Operators (Melchers et al., arXiv 2406.01857).** Parametric linear PDEs, with a Green's-formulation architecture. A 2026 follow-up (arXiv 2605.19867) finds that NGO is the only design in its 2x2 study that works as a **coarse solve in two-level preconditioning**, "matching the iteration count of an exact coarse solve" on diffusion and advection-diffusion. Other designs give non-symmetric spectra and PCG breakdown. Contrast is not stated — [arXiv 2406.01857](https://export.arxiv.org/abs/2406.01857); [arXiv 2605.19867](https://arxiv.org/abs/2605.19867)
- Foundations [not fetched]: Boullé & Townsend, randomized-SVD learning of elliptic Green's functions — [arXiv 2102.00491](https://arxiv.org/abs/2102.00491); GreenLearning (Boullé, Earls, Townsend) — [arXiv 2105.00266](https://arxiv.org/abs/2105.00266).

### Inferences
- For AmpScape, the natural port of these methods is **singularity subtraction on the graph**. Subtract a cheap analytic or numeric proxy for each point source: the homogeneous-conductance lattice Green's function (or its log-r asymptote) scaled by the local conductance at the source and ground pixels. The network then learns the smooth, heterogeneity-driven remainder, which removes the near-source high-frequency error that dominates AmpScape's residuals.
- Pairwise cumulative current is a sum over source pairs of |current| fields. Linearity holds only for voltages, before the absolute value. A Green's/basis decomposition therefore fits best when it predicts potentials and derives currents by a fixed graph-gradient (Ohm's law) layer, rather than predicting the current maps directly.

### Gaps
- None of these papers handles a graph Laplacian with 1e6 contrast, NoData holes, or grids above about 256^2. All are small-domain continuous PDEs.
- The SDC-GON and kernel-decomposition abstracts gave no quantitative error numbers, and GreensONet was seen only through an aggregator.

---

## Q3. Graph/mesh networks with Kirchhoff/conservation constraints and multigrid message passing

### Takeaway
Multiscale GNNs (BSMS-GNN, MS-MeshGraphNets, Graph U-Nets) solve the receptive-field problem on meshes but are tested on transient mechanics or fluids, not on high-contrast elliptic problems. Kirchhoff-constrained GNNs exist for power grids: KCLNet enforces KCL exactly by projection, and flow-attention GNNs build conservation into the attention. The one GNN line verified on weighted graph Laplacians is learned AMG (Luz et al.).

### Cited Findings
- **BSMS-GNN (Cao, Chai, Li, Jiang; ICML 2023).** Bi-stride pooling on alternating BFS layers, with non-parametric interpolation-based pooling and unpooling. No hand-made coarse meshes, and it avoids wrong edges across geometry boundaries (relevant to NoData holes). It is compared against GraphUNet and MS-GNN-Grid. Code: [GitHub](https://github.com/Eydcao/BSMS-GNN); it also ships in NVIDIA PhysicsNeMo — [PMLR](https://proceedings.mlr.press/v202/cao23a.html); [arXiv 2210.02573](https://arxiv.org/pdf/2210.02573); [PhysicsNeMo source](https://docs.nvidia.com/physicsnemo/latest/_modules/physicsnemo/models/meshgraphnet/bsms_mgn.html)
- **MultiScale MeshGraphNets** (Fortunato et al. 2022) [not fetched]: [arXiv 2210.00612](https://arxiv.org/abs/2210.00612)
- **KCLNet (Dogoulis, Tit, Cordy; arXiv 2506.12902).** Power-flow GNN that enforces Kirchhoff's Current Law as a **hard constraint via hyperplane projections**, guaranteeing zero KCL violation with competitive accuracy. It notes that earlier work used only soft penalties — [arXiv](https://arxiv.org/pdf/2506.12902)
- **Flow-attentional GNNs (Plettenberg et al., arXiv 2506.06127).** Graph attention modified to satisfy Kirchhoff's first law (node flow conservation), aimed at electrical circuits and power grids — [arXiv PDF](https://arxiv.org/pdf/2506.06127v1)
- **Learning AMG with GNNs (Luz, Galun, Maron, Basri, Yavneh; ICML 2020).** A GNN maps sparse SPD matrices to AMG prolongation weights using an unsupervised loss. It was tested on **graph Laplacians with random edge weights** and on 2D diffusion, and beat classical AMG convergence. It was trained on block-circulant problems — [PMLR](https://proceedings.mlr.press/v119/luz20a.html); [arXiv 2003.05744](https://arxiv.org/pdf/2003.05744)
- **GNN from linear algebra (arXiv 2405.15557)**: a GNN approach to preconditioner learning, seen in search results only and not read — [arXiv HTML](https://arxiv.org/html/2405.15557v3)

### Inferences
- AmpScape's 2-level-coarsening GNN probably fails for lack of depth. Global coupling at 512^2 needs about log2(512) ≈ 9 levels, the same lesson as MgNO's level ablation. A BSMS-style hierarchy with 7-9 levels is the GNN analogue.
- A **hard KCL output layer** is cheap and exact on AmpScape's 8-neighbour graph. Predict node potentials, then compute edge currents as g_ij (v_i − v_j). This gives KCL by construction at non-source nodes, and source and ground injections can be imposed. Physical consistency of the current maps would improve even where potential error stays.

### Gaps
- I found no GNN surrogate paper on resistor or circuit networks at 1e5+ nodes with high contrast, and none on Darcy on graphs with a verified high-contrast number.
- The MS-MeshGraphNets content was not fetched.

---

## Q4. Foundation PDE models (Poseidon, DPOT, MPP, PDEformer) on elliptic problems

### Takeaway
Poseidon is the only foundation model with verified elliptic downstream results: Poisson-Gauss, with a Gaussian-sum forcing that resembles smoothed point sources, and Helmholtz. It fine-tunes well there despite pretraining only on time-dependent fluids. None has been evaluated on high-contrast coefficients.

### Cited Findings
- **Poseidon (Herde et al., arXiv 2405.19101).** Downstream Poisson-Gauss is a Poisson equation with a superposition-of-Gaussians forcing and **Dirichlet BCs**, while pretraining is periodic and has no elliptic data. The paper calls it one of the most surprising generalization results. Gains relative to FNO (EG = efficiency gain, AG = accuracy gain):

  | Task | Poseidon-L | CNO-FM | MPP-B | CNO | scOT |
  |---|---|---|---|---|---|
  | Poisson-Gauss | 42.5 / 20.5 | 25.0 / 9.2 | 17.0 / 7.3 | 21.1 / 7.0 | 9.8 / 5.3 |
  | Helmholtz | 78.3 / 6.1 | 54.0 / 5.1 | 22.4 / 3.0 | 68.9 / 7.3 | 60.4 / 9.0 |

  - Note that plain **CNO trained from scratch** is competitive (Helmholtz AG 7.3 > Poseidon-L 6.1).
  - Steady states are handled as the long-time limit with lead time 1.
  - The authors expect elliptic pretraining data would help.

  [arXiv HTML v2](https://arxiv.org/html/2405.19101v2)
- **DPOT** [not fetched]: [arXiv 2403.03542](https://arxiv.org/abs/2403.03542). **MPP** [not fetched; evaluated as a baseline above]: [arXiv 2310.02994](https://arxiv.org/abs/2310.02994). **PDEformer** [not fetched]: [arXiv 2402.12652](https://arxiv.org/abs/2402.12652).

### Inferences
- Poseidon-L works on 128^2 patches with periodic pretraining. Fine-tuning at 512^2-2048^2 with 1e6 contrast would be well outside its demonstrated envelope. The strong showing of from-scratch CNO suggests a foundation model is not the lever for AmpScape's failure mode.

### Gaps
- I did not verify any foundation-model evaluation on high-contrast Darcy or on graph Laplacians, nor DPOT or PDEformer elliptic results.

---

## Q5. Size generalisation (train small, test large) and domain decomposition

### Takeaway
The most credible routes to 1024^2-2048^2 are **local operators wrapped in an iterative domain-decomposition or Schwarz loop**, and multigrid operators that are discretization-consistent. L-DDM reports 0.645% error on a domain 50x larger than training, and Mosaic Flow reports Laplace inference on domains 4096x larger. Pure zero-shot extension of global-attention models needs added locality biases.

### Cited Findings
- **L-DDM (arXiv 2507.17328).** A neural operator trained on simple small domains serves as the local solver inside an iterative DDM. On an elliptic test on a domain **50x larger** than training, the final error stabilizes at **0.645%** — [arXiv](https://arxiv.org/abs/2507.17328)
- **Schwarz Neural Inference (arXiv 2504.00510).** Partitions the domain, solves local problems with neural operators, and stitches the results Schwarz-style for geometry generalization — [arXiv HTML](https://arxiv.org/html/2504.00510)
- **Mosaic Flow (distributed, arXiv 2308.14258).** Physics-informed networks pre-trained on small domains give Laplace inference on domains **4096x** larger than training — [arXiv PDF](https://arxiv.org/pdf/2308.14258)
- **Scale-consistent learning (Li, Lanthaler, …, Anandkumar; arXiv 2507.18813).** Rescaling-based data augmentation plus a sub-domain consistency loss and a scale-informed neural operator. It covers Darcy and Helmholtz among others, with a 34% average error reduction. I got no per-task Darcy numbers — [arXiv](https://arxiv.org/abs/2507.18813)
- **Zero-shot domain extension for transformer operators (de Villeroché et al., arXiv 2606.14597, 2026).** Adds a decomposable locality bias to attention logits plus RoPE. The authors call the setting "barely explored". The PDEs and extension factor are not given in the abstract — [arXiv](https://arxiv.org/abs/2606.14597)
- MgNO's discretization transfer (trained at low resolution, tested to 512^2, error 1.03 to 1.21 ×10^-2) is also relevant — [arXiv HTML v3](https://arxiv.org/html/2310.19809v3)
- **Hybrid neural/iterative solvers.**
  - HINTS pairs a DeepONet (smooth error modes) with a relaxation smoother (high-frequency modes) — [arXiv 2208.13273](https://arxiv.org/html/2208.13273v2)
  - DeepONet-based hybrid preconditioners (Kopaničáková & Karniadakis 2024) improve Krylov convergence by a large margin and are robust across parameters and resolutions — [arXiv 2401.02016](https://arxiv.org/abs/2401.02016v2)
  - DL-HIM for Helmholtz uses the same spectral-bias split — [arXiv 2408.08540](https://arxiv.org/pdf/2408.08540v1)

### Inferences
- Size transfer for globally coupled Kirchhoff problems is fundamentally limited for any purely local model. Domain decomposition plus a coarse correction (a neural local solver with a classical or neural coarse space) is the structurally correct answer. It also matches AmpScape's tiling at 2048^2.
- AmpScape's high-frequency error near sources is precisely the component that HINTS-style hybrids hand to a classical smoother. A "neural coarse + Jacobi/GS smoother" few-iteration hybrid may beat any one-shot surrogate on the rel-L2 metric at modest cost. It also connects to the paper's existing truncated-AMG-PCG baselines.

### Gaps
- No verified numbers for scale-consistent learning on Darcy, or for the 2606.14597 benchmarks.
- No train-small / test-large result on high-contrast elliptic problems with point sources was found.

---

## Q6. Stable training at 1e5-1e6 contrast

### Takeaway
I found **no end-to-end neural operator or surrogate paper** that reports stable training or accuracy at 1e5-1e6 coefficient contrast. High-contrast robustness appears only where ML **selects or builds coarse spaces for domain decomposition** (ML-FETI-DP, ML-BDDC, ML-AGDSW from the Cologne group). There the classical solver guarantees convergence and the network only predicts which edges or eigenproblems are needed.

### Cited Findings
- **ML-FETI-DP / ML-AGDSW (Heinlein, Klawonn, Lanser, Weber).** A neural network classifies which subdomain edges need local generalized eigenproblems for adaptive coarse spaces. It was trained on stationary diffusion "with jumps and high contrasts in the diffusion coefficient". Its input samples the coefficient, which makes it discretization-independent. A regression variant predicts the full coarse space (3D hybrid version in SIAM J. Sci. Comput., 2021). The specific contrast values were not confirmed in what I read — [ML-DDM survey arXiv 2312.14050](https://arxiv.org/pdf/2312.14050); [ML-AGDSW tech report](https://kups.ub.uni-koeln.de/36257/1/CDS_TR-2021-02.pdf); [Nonlinear FETI-DP adaptive constraints arXiv 2312.14252](https://arxiv.org/pdf/2312.14252)
- Low-contrast operator benchmarks for comparison: DCNO and MgNO Darcy rough use a two-phase field of 12/2 (contrast 6) — [DCNO HTML](https://arxiv.org/html/2408.00775v1)
- A classical (non-learned) multiscale multigrid preconditioner for high-contrast Darcy exists as a reference point — [arXiv 2403.19342](https://arxiv.org/html/2403.19342)

### Inferences
- AmpScape's 1e6 contrast is 5 orders of magnitude beyond any verified neural-operator training set. That gap is itself a publishable "stress test" claim. It also suggests that MgNO divergence is a contrast-scaling issue, not an implementation bug.
- Mitigations consistent with the literature, none verified at 1e6:
  - log-conductance inputs
  - predicting log-potential or normalised potentials
  - an H1/gradient loss
  - Kirchhoff-exact output layers
  - singularity subtraction
  - wrapping the model as a preconditioner, so that accuracy is recovered by iteration

### Gaps
- No primary source verified reporting neural surrogate stability at ≥1e4 contrast. The exact contrast values in the ML-FETI-DP and ML-AGDSW papers were not extracted.
