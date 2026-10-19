# Hybrid numerical-solver + ML methods with accuracy guarantees for sparse SPD elliptic systems (2019-2026)

Scope note: 23 tool calls; primary sources are arXiv abstract/HTML pages and PMLR proceedings. Numbers marked "(derived)" are my arithmetic on a paper's table. Every number below was read from the cited page in this session unless it is listed under Gaps. Two PDFs (2310.00177, 2510.27517) did not parse as PDFs, so their numbers come from the arXiv HTML versions. Several 2026 items are recent preprints with no peer review yet; they are flagged as such.

Framing for AmpScape: the requirement is "faster than AMG-PCG at fixed accuracy" or "a certified map cheaper than the solver". Most learned-preconditioner papers compare against Jacobi, IC(0), SSOR or ILU, not against a tuned AMG. That distinction runs through every section below.

---

## Q1. Reported speedups versus well-tuned AMG-PCG or IC-PCG (iterations and wall time, with inference). Which papers honestly beat AMG in wall time?

### Takeaway
Only a few papers report beating AMG in wall time with inference included. The clearest is Lan et al. (ICML 2024): a GPU neural preconditioner with fixed structure, on 128^3-256^3 fluid-pressure Poisson problems whose domain changes every frame, so AMG must redo its setup each time. Its average solve is 0.267 s versus 0.819 s for AmgX and 1.691 s for AMGCL. Where AMG setup can be amortized (fixed operator, smooth coefficients), learned SPAI or IC-type preconditioners lose to AMG-PCG on GPU in their own appendix tables (Yang et al. 2025), and learned incomplete factorizations only tie IC(0) (NeuralIF).

### Cited Findings
**Learned preconditioners (neural IC / SPAI / neural-operator preconditioners)**
- NeuralIF (Häusner, Öktem, Sjölund; TMLR, arXiv 2305.16368). A GNN outputs a sparse incomplete-Cholesky-shaped factor, trained with a stochastic Frobenius loss that needs only mat-vecs. Code: github.com/paulhausner/neural-incomplete-factorization. — [arXiv](https://arxiv.org/abs/2305.16368)
  - Small 2D FEM Poisson (20k-150k unknowns), total time (s):
    - IC(0): 0.53 (166 iterations)
    - NeuralIF(0): 0.52 (168 iterations)
    - MIC+: 0.43 (101 iterations), which beats NeuralIF(1) at 0.47 (111 iterations)
    - Synthetic (n = 10k): NeuralIF 1.19 vs IC(0) 1.40
    - Large Poisson (up to 500k unknowns): "on par with IC(0)". No AMG comparison.
    - Caveat: the network ran on a Titan Xp GPU while baselines ran on a 6-core CPU. — [arXiv HTML v3](https://arxiv.org/html/2305.16368v3)
  - A follow-up extends NeuralIF to GMRES. — [arXiv 2409.08262](https://arxiv.org/abs/2409.08262)
- NeuralPCG (Li, Chen, Du, Matusik). A GNN produces an approximate decomposition used in PCG, with a loss weighted toward the solution-vector distribution. Listed as ICML 2023 (camera-ready file name). — [arXiv 2305.16432](https://arxiv.org/abs/2305.16432); [camera-ready PDF](https://people.csail.mit.edu/yichenl/projects/preconditioner/paper.pdf)
  - In NeuralIF's tables, NeuralPCG is slower than IC(0): 0.59 s vs 0.53 s on Poisson. — [NeuralIF HTML](https://arxiv.org/html/2305.16368v3)
- FCG-NO (Rudikov, Fanaskov, Muravleva, Laevsky, Oseledets; ICML 2024, PMLR 235:42766-42782). A neural operator serves as a nonlinear preconditioner inside flexible CG, using the Notay-type loss on Krylov residuals. — [PMLR](https://proceedings.mlr.press/v235/rudikov24a.html)
  - Iterations to a 1e-6 residual at 128^2:
    - Poisson: NO+FCG 20, CG 216, GS(4) 37, ILU(8) 128
    - Smooth diffusion: 19
  - No AMG baseline and no wall-clock timings. — [ar5iv 2402.05598](https://ar5iv.labs.arxiv.org/html/2402.05598)
- Learned SPAI on GPU (Yang, Li, Lyu, Li, Du, Liu; arXiv 2510.27517). A GNN predicts G with M^-1 = GG^T + eps*I, so each application costs two SpMVs and no triangular solves.
  - Main GPU table (ms, rtol 1e-8): Poisson 26 (Ours) vs 101 (IC) vs 45 (Diag).
  - Appendix Table 9, GPU: AMGX+CG beats it on every elliptic case:
    - Heat: 20 ms vs 36 ms
    - Heat-Large: 41 ms vs 154 ms
    - Poisson: 10 ms vs 26 ms
  - It wins only on hyperelasticity and synthetic matrices, where default-config AMG fails.
  - The paper itself says AMG is "effective for Heat/Poisson". — [arXiv HTML](https://arxiv.org/html/2510.27517v1)
- Neural-preconditioned Poisson solver, NPSDO (Lan, Gueidon, Kaneda, Panetta, Teran; ICML 2024). Fluid pressure Poisson on regular grids with mixed Dirichlet/Neumann boundaries that change every frame. — [PMLR](https://proceedings.mlr.press/v235/lan24a.html); [arXiv](https://arxiv.org/abs/2310.00177)
  - Setup: RTX 3080, tolerance 1e-6 residual reduction, single-precision network inside double-precision CG, inference included. Network evaluation is 79.4% of solve time.
  - Average solve time (s): NPSDO 0.267, AmgX 0.819, AMGCL 1.691, IC 2.667, CG 3.232
  - Smoke 256^3 (s): NPSDO 0.636, AmgX 3.156
  - Fastest on 95.6% of systems.
  - Trained at 128^3 and (256,128,128); tested at 256^3 and other unseen shapes. Training took about 5 days. — [arXiv HTML v5](https://arxiv.org/html/2310.00177v5)
  - Note: the AMG baselines pay setup on every system. The advantage is largely amortization against changing domains, not a better asymptotic preconditioner (see Inferences).
- Deep Conjugate Direction Method (DCDM, Kaneda et al.) is NPSDO's predecessor. In the NPSDO paper it is far slower: 12.35 s vs 0.052 s on a FluidNet example. — [arXiv HTML v5](https://arxiv.org/html/2310.00177v5)

**Learned AMG components** (more in Q2)
- Learned polynomial / pseudo-inverse Jacobi smoother inside Ruge-Stüben AMG (Chillón, Lidtke, Doan, Font; arXiv 2606.19251, 2026 preprint).
  - Up to 36% fewer V-cycles.
  - Wall-clock solve speedups of 4-37%.
  - Setup up to 10.5x the relaxed-Jacobi setup on structured meshes.
  - The baseline is the authors' own AMG with ω = 2/3 Jacobi. No library AMG is compared.
  - Internal inconsistencies: the paper gives both 17-25% and 4-37% as its speedup range, and "128x larger" meshes against a 4x-per-dimension test. — [arXiv HTML](https://arxiv.org/html/2606.19251v1)
- RAPNet (Fink, Ben-Yair, Ruthotto, Treister; arXiv 2605.26854, 2026 preprint). A GNN adds sparse corrections ΔP, ΔR, ΔAc to an unsmoothed-aggregation hierarchy and runs only at setup.
  - Setup time (s), 3D geometric 512k: RAPNet 1.66 (GPU), AGG 1.25, SpSA 3.50 (both CPU).
  - Solve-phase per-iteration time is "nearly identical".
  - Iterations, 3D geometric 128k/256k/512k: 59/64/71, vs 99/108/113 without ΔP/ΔR (ablation).
  - Not compared against Ruge-Stüben, BoomerAMG or AmgX. — [arXiv HTML](https://arxiv.org/html/2605.26854v1)
- GMP (Zhang, Li, Saad; arXiv 2607.28456; claims KDD 2026). Learns smoothing, restriction and interpolation on an AMG hierarchy, benchmarked against classical AMG and ILUT on more than 800 matrices.
  - The abstract reports "both promise and limitations", including cases where it adds overhead relative to strong single-level baselines. No numbers in the abstract. — [arXiv](https://arxiv.org/abs/2607.28456)

**Non-learned GPU baseline strength**
- BootCMatchGX beat AmgX on preconditioned CG in a multi-GPU energy study on large Poisson-type problems. This is a reminder that "AmgX default" is not the strongest AMG baseline. — [arXiv 2510.02878](https://arxiv.org/pdf/2510.02878)

### Inferences
- No paper found compares against tuned Ruge-Stüben AMG-PCG on a CPU with setup amortized, which is the AmpScape baseline. Learned methods beat AMG in wall time when one of three things holds:
  - AMG setup is paid per solve and the matrix changes every time (NPSDO).
  - The network runs on a GPU while the baseline runs on a CPU.
  - Default-config AMG fails on non-elliptic matrices (learned SPAI).
- For a fixed, well-conditioned-by-AMG elliptic operator, the honest evidence (Yang et al. Table 9; NeuralIF's parity with IC) suggests learned single-level preconditioners do not beat AMG-PCG.
- Learning AMG components (smoother, ΔP/ΔR/ΔAc, coarsening) keeps AMG's guarantee structure. The reported gains are modest: 4-37% wall clock, about 30-40% fewer cycles. That is the realistic band for "faster solver at fixed accuracy".
- Any nonlinear network preconditioner (FCG-NO, NPSDO-type) needs flexible CG or a fixed linear-SPD structure (SPAI GG^T, NeuralIF LL^T) to retain CG convergence guarantees. Convergence to the requested tolerance is still guaranteed because the outer Krylov loop checks the true residual.

### Gaps
- No paper found reports learned vs AMG-PCG at 1e4-1e6 contrast with wall time.
- NeuralPCG's own numbers vs IC/AMG were not extracted (PDF not parsed).
- Luz et al. (2020) quantitative tables were not extracted (only the abstract was read).

---

## Q2. Results on high-contrast coefficients (Darcy 1e4-1e6) and on graph Laplacians; learned AMG components

### Takeaway
High-contrast evidence is thin. The best is Kopaničáková, Lee and Karniadakis (2025): DeepONet-built deflation for PCG on "JumpDarcy" with channel coefficients from 1 to 1e5. It reports iterations only, against SSOR/ICC/ASM, not AMG. For graph Laplacians, the learned-AMG line has run from Luz 2020 (GNN prolongation), through Taghibakhshi 2021 (RL coarsening) and Taghibakhshi 2023 (MG-GNN), to RAPNet 2026 (graph Laplacians up to 1M nodes, trained on 4k-node graphs). The strongest non-learned Laplacian solvers (approxchol, LAMG, CMG) are rarely used as baselines.

### Cited Findings
- Greenfeld, Galun, Kimmel, Yavneh, Basri (ICML 2019). One network maps a family of 2D diffusion problems to prolongation operators, trained with an unsupervised loss. Converges faster than Black-Box multigrid. — [PMLR v97](https://proceedings.mlr.press/v97/greenfeld19a.html)
- Luz, Galun, Maron, Basri, Yavneh (ICML 2020). A GNN learns AMG prolongation for sparse SPD/SPSD matrices with an unsupervised loss. Reports "improved convergence rates compared to classical AMG". — [arXiv 2003.05744](https://arxiv.org/abs/2003.05744)
- Taghibakhshi, MacLachlan, Olson, West (NeurIPS 2021). An RL agent built on GNNs selects AMG coarse grids, is trained on small graphs and is applied to large unstructured graphs. Inference cost is linear in graph size. — [arXiv 2106.01854](https://arxiv.org/abs/2106.01854); [NeurIPS poster](https://neurips.cc/virtual/2021/poster/25928)
- MG-GNN (Taghibakhshi, Nytko, Zaman, MacLachlan, Olson, West; ICML 2023). Learns one-level smoothers and two-level prolongations for domain decomposition. — [arXiv 2301.11378](https://arxiv.org/pdf/2301.11378)
- RAPNet (2026 preprint) evaluates graph Laplacians with highly connected hubs: Watts-Strogatz up to 1M nodes, temporal Barabási-Albert, social hub, 2D/3D geometric with random weights. Trained on about 4,000-node graphs; PDE models trained on 2D and tested on 3D. — [arXiv HTML](https://arxiv.org/html/2605.26854v1)
- DeepONet deflated PCG (Kopaničáková, Lee, Karniadakis; arXiv 2508.00101, 2025). — [arXiv HTML](https://arxiv.org/html/2508.00101)
  - JumpDarcy, channel coefficients 1 to 1e5, ASM-preconditioned with DD grouping, S = 4: NICO deflation 1,492 iterations; DeepONet trunk-basis deflation 1,098; recycled-solution deflation 1,171.
  - NICO "fails to produce a suitable coarse space" for JumpDarcy.
  - No wall-clock results and no AMG baseline.
- Learned BDDC adaptive coarse spaces (2021). A network predicts dominant eigenvectors for adaptive BDDC coarse spaces on stochastic elliptic problems with oscillatory, high-contrast coefficients. — [arXiv 2104.09162](https://arxiv.org/pdf/2104.09162)
- Two-grid + FNO/Attention-U-Net multiscale basis prediction for high-contrast Darcy (Li, Chen, Fu; arXiv 2606.02582, 2026 preprint). 128^2 fine grid, 4x4 coarse grid, ILU(0) smoother. No contrast ratio, iteration counts or timings reported; one basis has R^2 = 0.554, contradicting the claim "all R^2 > 0.9". — [arXiv HTML](https://arxiv.org/html/2606.02582)
- Learned SPAI (Yang et al.) varies heat diffusivity only from 1e-4 to 5e-4 (a 5x spread). This is not high contrast. — [arXiv HTML](https://arxiv.org/html/2510.27517v1)
- FCG-NO's "diffusion" coefficient is a(x) = P(5,5,2) + 10, which is low contrast. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2402.05598)
- **Non-learned graph-Laplacian solvers**
  - Approximate Cholesky (Gao, Kyng, Spielman, 2023) preconditions CG and is benchmarked single-threaded against CMG, BoomerAMG (HYPRE/PETSc), LAMG and ICC. The authors claim robustness "not seen before in SDDM solvers". — [arXiv 2303.00709](https://arxiv.org/html/2303.00709v2)
  - Laplacians.jl docs name `approxchol_lap` as its fastest Laplacian solver. — [GitHub](https://github.com/danspielman/Laplacians.jl/)
  - LAMG+ (2026 preprint, single author): approximate Cholesky is faster on social/citation graphs; LAMG+ is faster on FE/structural matrices. — [arXiv 2606.24791](https://arxiv.org/pdf/2606.24791)

### Inferences
- AmpScape's contrast (1e6) and point sources are beyond what any learned-preconditioner paper found here tests. A benchmark with tuned RS-AMG, approximate Cholesky and AmgX baselines at 1e6 contrast would itself be a contribution.
- 4-connected raster Laplacians with random weights are close to RAPNet's "2D geometric with random weights" and to Luz et al.'s setting. The learned-AMG line is the natural fit for Circuitscape-style matrices.
- Approximate Cholesky (Laplacians.jl, Julia, the same ecosystem as Circuitscape) is an untested non-learned competitor for AmpScape. It should be timed before claiming any learned method beats "the solver".

### Gaps
- No paper found reports contrast 1e6 for a learned preconditioner or learned AMG component.
- No direct learned-AMG vs approximate Cholesky comparison was found.
- Luz 2020 graph-Laplacian (Delaunay) numbers were not verified.

---

## Q3. Learned low-frequency corrections, coarse spaces, deflation; learned initial guesses and why naive warm starts fail

### Takeaway
Learned predictions help CG reliably when used in one of three ways:
- as a subspace: deflation, augmentation or coarse space (Kopaničáková et al. 2025);
- inside the iteration on the low-frequency band the network represents well, with a classical smoother handling high frequencies (HINTS);
- as a warm start against weak preconditioners (NOWS: Jacobi, SSOR, ICC, ILU; no AMG tested).

A warm start in front of AMG-PCG, as in AmpScape, is the weakest case: AMG already removes smooth error in a few cycles, and the network's high-frequency error is exactly what the residual amplifies.

### Cited Findings
- NOWS, Neural Operator Warm Starts (arXiv 2511.02481, CMAME 2026). Inference time is included in runtimes. Preconditioners tested on Darcy: Jacobi, SSOR, ICC, ILU; the paper says AMG/multilevel is "future work". — [arXiv HTML v4](https://arxiv.org/html/2511.02481v4); [CMAME](https://www.sciencedirect.com/science/article/pii/S0045782526002628)
  - Burgers: 9.62 s to 4.75 s.
  - Smoke-plume pressure: 294.74 s to 93.85 s.
  - Poisson iteration savings: 30-40% on coarse meshes, more than 50% on finer ones.
  - The paper says the network "removes large-scale error components… leaving the classical solver to perform only fine-scale corrections", and that savings shrink at tighter tolerances.
- HINTS (Zhang, Kahana, Turkel, Zhang, Dong, Karniadakis, Lu). Alternates Jacobi/Gauss-Seidel with a DeepONet step at ratio 1:(n_r - 1). It exploits DeepONet's spectral bias toward low frequencies while relaxation kills high frequencies, giving roughly uniform convergence across modes and accuracy near machine precision. — [arXiv 2208.13273](https://arxiv.org/abs/2208.13273)
  - Geometry-transfer follow-up. — [arXiv 2210.17392](https://arxiv.org/pdf/2210.17392)
  - Spectral-bias survey discussion. — [arXiv 2501.09987](https://arxiv.org/pdf/2501.09987)
- DeepONet deflation keeps DPCG's convergence guarantees because the network only builds the deflation space. Both the trunk-basis and recycled-prediction variants beat Nicolaides deflation.
  - Initial guesses are corrected as u0 = u00 + C(f - A u00).
  - Darcy with ICC: 1,191.6 to 869.8 iterations. Heat with SSOR: 1,719.8 to 860.2.
  - Per-vector cost limits k: deflation stays worthwhile up to about k ≲ 30 at θ ≈ 0.008.
  - Trained on the coarsest mesh and applied to finer meshes; a POD-trunk variant does not transfer across resolutions. — [arXiv HTML](https://arxiv.org/html/2508.00101)
- Neural H²-matrix preconditioner (Osborne, Guo, Owens, Matusik; SIGGRAPH Asia 2026 poster). Probe-based losses (cosine-Hutchinson) have vanishing gradients on the near-null modes that drive CG iteration counts. Switching to a truncated Kaporin condition-number loss cut CG iterations from 116 to 33 on a held-out frame. — [arXiv 2605.13343](https://arxiv.org/abs/2605.13343)
- FCG-NO ablation: the Notay-type loss on Krylov-subspace residuals beats the L2 loss and random right-hand sides.
  - Diffusion 128, L2 loss: did not converge. Random-RHS training: no convergence to 1e-6.
  - That is, training must target the residual distribution the solver actually sees. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2402.05598)
- Recycling Krylov methods: a survey (Soodhalter, de Sturler, Kilmer, GAMM-Mitteilungen 2020) of augmentation, deflation and recycling for sequences of systems with slowly changing matrices or multiple right-hand sides. — [arXiv 2001.10347](https://arxiv.org/pdf/2001.10347)
  - Parks et al. (2004) report about 2x iteration reductions on model problems. — [IDEALS](https://www.ideals.illinois.edu/items/10805)

### Inferences
- Why AmpScape's warm start saved nothing, consistent with the above:
  - The residual r0 = A e0 weights each error mode by its eigenvalue. A prediction with small high-frequency error can therefore have a residual comparable to or larger than ||b||. Checking ||r0|| vs ||b|| would confirm this.
  - AMG-PCG converges the remaining error at a nearly mesh-independent rate. Removing smooth error, which is what the network is good at, buys at most a fraction of the 1-2 cycles AMG would spend on it anyway.
  - NOWS's gains were all measured against single-level preconditioners whose bottleneck is exactly that smooth error.
- Two fixes follow:
  1. Use the network's output as a deflation or augmentation vector, or a small set of them (e.g., prediction plus a trunk or POD basis), rather than as x0. A projection then removes only the component the network gets right; CG's guarantee is unchanged.
  2. Smooth the prediction first: apply one or two AMG V-cycles or Jacobi sweeps to the error equation before starting CG (HINTS logic). Then test against AMG, not Jacobi.
- With AMG at 2-4 iterations per digit, expected savings from either fix are bounded, roughly by one AMG iteration (inference, not measured). This is probably not enough for a paper unless setup is the bottleneck.

### Gaps
- No paper found tests learned warm starts or learned deflation against AMG-PCG and reports net wall-time savings.
- No paper found explicitly analyzes residual amplification of high-frequency warm-start error. The argument above is my inference from standard CG theory.

---

## Q4. A-posteriori error estimation and certified surrogates

### Takeaway
For SPD systems the cheapest guarantee is the residual: ||e||_A ≤ ||r||_{A^-1}, bounded via the smallest eigenvalue or a preconditioned dual norm (inference from standard theory). The ML literature builds on this in three ways: residual-based correction (one linear solve), dual-norm certification, and reduced-basis neural operators whose loss is a reliable error estimator.

### Cited Findings
- Residual-based error correction for neural-operator surrogates (Cao et al., arXiv 2210.03008). Corrects a neural-operator prediction by solving a linear variational problem built from the PDE residual. — [arXiv](https://arxiv.org/pdf/2210.03008); [OSTI](https://www.osti.gov/pages/servlets/purl/2421120)
  - Nonlinear-BVP variant. — [arXiv 2306.12047](https://arxiv.org/pdf/2306.12047)
  - A secondary review reports optimization errors falling from about 80% to below 6% with the correction (secondary; not verified in the primary paper). — [search result](https://arxiv.org/pdf/2503.05598)
- A posteriori certification of PDE approximations, including neural networks (arXiv 2502.20336). Two-sided bounds via the dual norm of the residual, with computable surrogates for the supremum. — [arXiv](https://arxiv.org/html/2502.20336v5)
- Variationally correct reduced-basis neural operator (Qiu, Dahmen, Chen; arXiv 2512.21319). Argues that plain PDE-residual losses are not variationally correct, so a small residual need not mean a small error. Designs the loss so it is a reliable, computable a posteriori estimator. — [arXiv](https://arxiv.org/abs/2512.21319)

### Inferences
- Certified accuracy for AmpScape maps is cheap to compute: one SpMV for the residual, plus an AMG V-cycle as an approximate A^-1-norm. This turns any learned prediction into either a verified output or a fallback trigger.
- But the certificate costs about as much as one or two AMG iterations, and AmpScape already shows two AMG-PCG iterations beat the surrogates. So "certified surrogate cheaper than the solver" looks implausible for full Circuitscape solves at these sizes (inference).
- The certificate becomes economical only if inference plus certification is far cheaper than AMG setup plus solve. That may hold for very many tiny Omniscape windows where setup dominates.

### Gaps
- No certified-surrogate paper found targets graph Laplacians or 1e6 contrast.

---

## Q5. GPU iterative solvers (non-learned competitor) and the Omniscape question (many small windowed solves)

### Takeaway
The strongest non-learned options for thousands of small related SPD solves are two. First, batched GPU Krylov solvers (Ginkgo batched CG/BiCGStab with per-system stopping, built for many small sparse systems). Second, cutting or amortizing AMG setup across windows. Among learned approaches, the most plausible are setup-only learned AMG corrections (RAPNet style: one GNN pass replaces costly setup, solve phase unchanged) and fixed-structure GPU preconditioners whose value comes from avoiding per-system setup (NPSDO, neural H²). Krylov recycling suits overlapping windows in principle, but no evidence was found for this exact setting.

### Cited Findings
- Ginkgo batched sparse iterative solvers. — [arXiv 2308.08417](https://arxiv.org/pdf/2308.08417)
  - Per-item stopping criteria, multiple batched formats and preconditioners (BatchIsai needs BatchCsr).
  - Used for XGC fusion collision kernels against a 40-core CPU node, on V100/A100/MI100. — [ORNL](https://impact.ornl.gov/en/publications/integrating-batched-sparse-iterative-solvers-for-the-collision-op/)
  - Intel PVC SYCL port averages 2.4x over the H100 CUDA version on PeleLM inputs. — [arXiv 2308.08417](https://arxiv.org/pdf/2308.08417)
- NPSDO motivation: multigrid setup "must be re-executed every time domain shapes or boundary conditions change". Its wall-time win over AmgX (about 3x average, derived) comes in exactly that regime. — [arXiv HTML v5](https://arxiv.org/html/2310.00177v5)
- Neural H² preconditioner: AMG setup alone exceeds an 8-16 ms budget "at a few thousand unknowns". The learned preconditioner fits 8.3 ms for N = 572-3,647. — [arXiv 2605.13343](https://arxiv.org/abs/2605.13343)
- JAX-AMG (arXiv 2606.09001) uses an AmgX backend and notes that warm re-setup-and-solve is the operation repeated in optimization and time-stepping loops. — [arXiv](https://arxiv.org/pdf/2606.09001)
- The RAPNet GNN runs only at setup, and its solve phase is standard AMG. — [arXiv HTML](https://arxiv.org/html/2605.26854v1)
- Krylov recycling covers sequences with slowly changing matrices and many right-hand sides. — [Soodhalter et al. survey](https://arxiv.org/pdf/2001.10347)

### Inferences (Omniscape recommendation)
- Omniscape windows (radius 16-256 px, so about 1k-260k unknowns each) overlap heavily between neighboring centers. For small radii, per-window AMG setup likely dominates the cost (inference; should be profiled).
- Most promising, in order:
  1. **Batched GPU PCG with a cheap fixed preconditioner** (Jacobi, block-ISAI, or a learned SPAI with GG^T form, as in Yang et al.) over thousands of small windows. This is non-learned or lightly learned, and guaranteed by the residual stopping test.
  2. **Amortized or learned AMG setup.** Reuse the hierarchy from a neighboring window, or predict P/Ac corrections with a RAPNet-style GNN trained on small windows. The accuracy guarantee comes from the PCG loop.
  3. **Recycling or deflation across overlapping windows.** Carry a few smooth vectors from one window to the next, either recycled Ritz vectors or learned ones as in Kopaničáková et al.
- A learned single-level preconditioner is unlikely to beat AMG on the largest windows (Q1 evidence). Its plausible niche is the small-radius regime where setup cost dominates.

### Gaps
- No paper found on accelerating Omniscape or Circuitscape solves with ML or batching.
- No benchmark found of batched CG for graph-Laplacian windows.
- No published AmgX timing found for 128^2-512^2 2D Laplacians that could be compared with AmpScape's 0.04-1 s single-core figures.
