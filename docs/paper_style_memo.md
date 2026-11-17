# Paper style memo — form, not content (2026-10-16)

Read for form: PDEBench (NeurIPS D&B 2022, arXiv 2210.07182), The Well (NeurIPS D&B 2024, 2412.00568), PGLearn (2025,
2505.22825), OGB (NeurIPS D&B 2020, 2005.00687), and two recent accepted papers — EngiBench (NeurIPS 2025 Datasets and
Benchmarks Track, 2508.00831) and Bubbleformer / BubbleML 2.0 (NeurIPS 2025 spotlight, 2507.21244; a dataset-plus-model
paper whose track label the public pages do not show) — plus the NeurIPS paper checklist (neurips.cc/public/guides/PaperChecklist),
the NeurIPS 2026 formatting instructions (`neurips_2026.sty`, revision 2026-01-29; the target is NeurIPS 2027, whose style file and call were not yet published on 2026-10-17) and the 2026 Evaluations & Datasets
track call. Structural counts come from the arXiv HTML of each paper (main text = sections before acknowledgements /
references / appendix), parsed in `work/lit/`.

## 1. What the main text looks like

| paper | main-text words | top-level sections | main-text figures | main-text tables | abstract words | median words / sentence |
|---|---|---|---|---|---|---|
| PDEBench 2022 | 5,744 | 5 (Motivation, Related work, Benchmark, Experiments, Conclusions & limitations) | 7 (teaser montage + 2 code listings + 4 result panels) | 1 (dataset summary) | 250 | 23 |
| The Well 2024 | 4,796 | 5 (Intro, Related, Contents, Benchmark, Conclusion) | 6 (5 snapshot galleries + 1 metric figure) | 3 (dataset table, 2 result tables) | 167 | 23–24 |
| PGLearn 2025 | 4,941 | 7 (Intro with 1.1 motivation / 1.2 related / 1.3 contributions, Formulations, Datasets, Software, Metrics, Limitations, Conclusion) | 2 (toolkit schematic, one analysis figure) | 1 (summary statistics) | 238 | 23 |
| OGB 2020 | 15,813 (ICLR-style long paper) | 8 | 4 (diversity diagram, pipeline schematic, t-SNE, example graph) | 18 (overview, statistics, one results table per dataset) | 175 | 25 |
| EngiBench 2025 | ≈ 6,000 | 6 (Intro, Preliminaries & related, EngiBench, Proof-of-concept experiments, Use cases / limitations / future, Conclusion) | 4 (problem gallery, API listing, Pareto-front comparison, generated designs) | 2 (problem table with simulation times, results table) | 204 | 17 |
| Bubbleformer 2025 | 5,068 | 7 (Intro, Problem, Failure modes, Model, Dataset, Results, Conclusions & limitations) | 5 | 1 (dataset summary) | 182 | 22 |

Reading: 4,800–6,000 words of main text, 5–7 top-level sections, 4–7 figures and 1–3 tables in the nine pages is the
norm; OGB is the outlier (long format, per-dataset result tables). Abstracts run 170–250 words and state the artefact,
its scale, the tasks, the baselines' headline finding and the release (licence, hosting).

## 2. First page and Figure 1

- **Title + abstract + start of the introduction** fill page 1. The abstract names the artefact in the first or second
  sentence ("we introduce the Well, a diverse 15 TB collection…"; "PDEBench, a benchmark suite of time-dependent
  simulation tasks…"), gives one or two scale numbers, lists what is released, and ends with the hosting/licence line.
- **Figure 1 is a teaser on page 1 or 2** in four of six papers: PDEBench (four simulation snapshots, no axes),
  OGB (a diagram of dataset diversity; Figure 2 is the pipeline), PGLearn (the toolkit as a block diagram: datasets →
  generator → ML toolkit), Bubbleformer ((a) dataset gallery across configurations, (b) the downstream tasks). The Well
  has no teaser — its Figures 1–5 are a snapshot gallery inside the contents section. EngiBench opens with a problem
  gallery (Figure 2) after a one-column overview figure.
- **Pattern for the first paragraph**: a two-sentence statement of why the domain matters ("Simulation is one of the most
  ubiquitous and important tools…"), then the gap in one sentence ("there is still a lack of benchmarks for Scientific ML
  that are easy to use but still challenging…"), then "To address this gap, we introduce X" with a compact scale clause.
- **Contributions** appear as (a)–(e) in running text (PDEBench), as a bulleted list under "Contributions and Outline"
  (PGLearn, OGB) or as a closing paragraph of the introduction (The Well, EngiBench). All are one sentence each and
  reference the section that delivers them.

## 3. Data overview

- A **single summary table** of the collection is universal: datasets/tiers as rows; resolution, counts, size, splits,
  generation cost as columns (PDEBench Table 1; The Well Table 1 with coordinate system, resolution, steps,
  trajectories, size; PGLearn Table 1 summary statistics; OGB Tables 2–3; EngiBench Table 1 with simulation time per
  problem; Bubbleformer Table 1 with physical parameters and Δt).
- **Galleries** show raw samples with no axes, one row per dataset or family, a shared colour map and a tight caption
  that names the fields shown (The Well Figures 1–5; PDEBench Figure 1; Bubbleformer Figure 1a).
- The **generation / provenance** paragraph states the solver or simulator, its version, the precision or tolerance, the
  compute used (GPU-hours, core-hours) and the storage format; details per dataset go to an appendix with one
  subsection per dataset (The Well Appendix C; PDEBench Appendix D).
- The **access** paragraph is short and concrete: hosting platform, licence, loader API (PDEBench and OGB show a
  5–10-line code listing; The Well points to a library), versioning and maintenance.

## 4. Tasks, metrics, baselines

- Tasks are defined once, formally but briefly, with inputs → outputs and the quantity learned (PDEBench §3.1 "General
  Problem Definition"; PGLearn §2 formulations with the optimisation problems as numbered displays; OGB per dataset:
  graph, prediction task, split).
- Metrics get their own subsection with one sentence per metric and why it is reported (PDEBench §3.3; The Well §4.1
  VRMSE and why it is normalised; PGLearn §5 lists accuracy and computational metrics and insists on reporting
  mean / std and maximum).
- Baselines: 3–5 standard model families, stated with their configuration source (PDEBench: FNO, U-Net, PINN with
  hyper-parameters in Appendix C; The Well: FNO, TFNO, U-net, CNextU-net, "powerful but naive models employed en masse
  without accounting for the specific physical characteristics"; EngiBench: GANs, diffusion, surrogates over 10 seeds).
  Seeds: OGB 10 seeds with mean and unbiased std "corresponding to the best validation results"; EngiBench 10 seeds;
  The Well reports single numbers; PDEBench single numbers with a note on variance in the appendix.

## 5. Results presentation

- **Tables**: one summary results table in the main text, rows = datasets (or tasks × tiers), columns = models, best
  value in **bold** (The Well Tables 2–3; EngiBench Table 2 adds a colour gradient; OGB prints mean ± std with the
  best bold), lower-is-better stated in the caption, the metric defined in the caption ("VRMSE is scaled such that
  predicting the mean value of the target gives a value of 1"). Numbers are 3–4 significant figures.
- **Figures**: one headline comparison figure (PDEBench Figure 4: RMSE per dataset and model as grouped bars; The Well
  Figure 6: metric across state variables and time windows), one or two analysis figures (error vs a parameter, error
  over time, Pareto front), and qualitative panels (prediction vs ground truth) — PDEBench puts the prediction
  visualisations in the appendix (Appendix I), Bubbleformer keeps two in the main text (rollout panels), EngiBench shows
  generated designs.
- **Prose** states the observation, then the mechanism, then the implication, in that order: "FNO provides the best
  prediction for most metrics. It learns the differential operators well, leading to low errors even for the conserved
  quantities… Additionally, FNO has a consistent error of about 4 × 10⁻⁴ across the frequency spectrum" (PDEBench);
  "the FNO's error increases with decreasing diffusion coefficient where a strong discontinuity appears. This can be
  attributed to Gibb's phenomenon…". Numbers in prose are few and point to the table or figure that holds them.
- Negative or limiting results are given their own paragraph or subsection ("our benchmark also reveals several tasks
  which these methods cannot treat properly"; Bubbleformer §3 "Failure Modes"), and every paper ends its main text with
  a limitations paragraph or section.

## 6. Tone and sentence patterns

- Present tense, first person plural, declarative; "we" is used freely (PDEBench 25, OGB 51, EngiBench 107 occurrences)
  except PGLearn, which writes impersonally. Sentences average 17–25 words; paragraphs 4–7 sentences with a bold run-in
  lead where the section enumerates items (The Well §4.2 "Physical constraints. … Long-term stability. …").
- Quantities are stated with units and a comparison point ("15 TB", "140 h on 55 CPUs", "orders of magnitude"), never as
  bare decimals; precision is 2–3 significant figures in prose, 3–4 in tables.
- Claims are scoped ("Among the baseline surrogate models", "on the datasets considered") and hedged with mechanism
  rather than adjectives; no "novel", "significant" without a number.
- Captions are complete sentences that say what is plotted, how it was aggregated, and what to look for; axis names
  and units are in the figure, not the caption.

## 7. Appendix contents (what goes out of the main text)

Datasheet / data card (The Well Appendix A, PDEBench Appendix K: motivation, composition, collection, preprocessing, uses,
distribution, maintenance), per-dataset details and equations (one subsection each), the data format and loader
(PGLearn Appendix B: one table per file type; OGB code snippets), training protocol and hyper-parameters (PDEBench
Appendix C, EngiBench Tables 8–13), detailed scores per dataset and metric (PDEBench Appendix E, The Well Appendix E.4),
runtime / compute tables (PDEBench Appendix F–G, PGLearn Appendix C), qualitative visualisations (PDEBench Appendix I–J),
licences and links (EngiBench A.1–A.2), maintenance and contribution policy (EngiBench A.3), and the checklist last.

## 8. Formatting rules that bind (NeurIPS 2026 instructions and E&D call)

- Nine content pages including figures and tables; references, acknowledgements, the checklist and technical appendices
  do not count; the appendix is "optional reading" — nothing that supports a main claim may live only there.
- `neurips_2026.sty` is the only supported style; options `final`, `preprint`, `nonatbib`, plus track options (`eandd`
  sets the footer to "Track on Evaluations and Datasets"); at submission omit `final`/`preprint` → anonymised with line
  numbers. Figures and tables use `\caption` under / above as the style sets; 10-point Times; references may be 9-point.
- E&D track (formerly D&B): double-blind by default, single-blind only if the dataset cannot be anonymised; datasets
  hosted on an ML hosting site with a Croissant file (core + RAI) submitted with the paper; a small sample for datasets
  above 4 GB; code required when the contribution is a reusable executable artefact (a benchmark suite); the paper must
  state the evaluative role of the dataset: what claims it supports, under what assumptions, with what limitations.

## 9. Checklist items that need an explicit answer (16, in the style file; answered Yes / No / NA with a justification
pointing at a section)

1. Claims match contributions and scope (abstract, §1). 2. Limitations section. 3. Theory: assumptions and proofs (the
scale-transfer derivation → Appendix). 4. Experimental reproducibility (code, data, protocol). 5. Open access to data and
code with instructions and the exact commands. 6. Experimental settings: splits, hyper-parameters, how chosen. 7. Error
bars: what varies (seeds), how computed (sample std), 1-sigma stated. 8. Compute: hardware type, per-run and total
GPU-hours, and whether the project used more than reported. 9. Code of ethics. 10. Broader impacts (positive and negative).
11. Safeguards (NA for a solver-output dataset). 12. Licences of existing assets cited with version and licence name.
13. New assets documented (card, Croissant, licence, limitations). 14. Crowdsourcing / human subjects (NA). 15. IRB (NA).
16. LLM usage declaration (NA unless LLMs are part of the method).

## 10. What AmpScape adopts

- Nine pages: abstract ≈ 180 words; §1 Introduction (problem, gap, "we introduce AmpScape", contributions in running
  text, Figure 1 = pipeline + task menu); §2 Related work (one page); §3 Problem and tasks; §4 The dataset (overview
  table, gallery Figure 2, generation and fidelity, access); §5 Splits and OOD; §6 Metrics and protocol; §7 Baselines and
  results (one results table, Figures 3–7: qualitative, error vs tier, Pareto, scale transfer, OOD); §8 Many-query
  demonstration; §9 Limitations, ethics, maintenance; one reproducibility paragraph. Operational narrative out.
- Figures: 7 in the main text, all from `scripts/paper_figures.py` in one style (serif-free sans labels, shared colour
  map for current maps, no axes on raster panels, legend keys = model names), vector PDF; the appendix holds the
  training-curve grid, data-scaling curves, dataset statistics, fidelity and precision-pass figures, WP7 panels.
- Tables: one main results table with rel-L2 mean ± std [median] and best per row in bold; full tables in the appendix
  generated from `docs/tables/*.md` so that every number is traceable; captions define the metric and the aggregation.
- Prose: observation → mechanism → implication; "we"; present tense; 2–3 significant figures in text; every quantity
  with its unit and comparison; negative results (acceleration, ViT at L, GNN on T1) stated plainly in their own
  paragraphs; limitations as a numbered list.
- Appendix: datasheet pointer (card), per-task definitions, generation record (precision pass, fidelity), splits and
  subsets, protocol and hyper-parameters, full tables, qualitative panels, licences, Croissant snippet, checklist.
