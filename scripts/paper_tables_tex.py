#!/usr/bin/env python
"""LaTeX tables of the NeurIPS submission, generated from the regenerated Markdown/JSON tables so that every number in
the paper traces to a `docs/tables/` or `paper/tables/` file (the source is written as a `% src:` comment in each
.tex file and checked by scripts/verify/check_draft_numbers.py --tex).

  python scripts/paper_tables_tex.py [--out paper/neurips/tables]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TIERS = ["S", "M", "L", "XL", "XXL"]
MODELS = ["U-Net", "FNO", "ViT", "GNN", "MgNO"]


def md_rows(path: pathlib.Path) -> list[dict]:
    rows, header = [], None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            header = None  # a file may hold several tables; each one carries its own header
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def tex(s: str) -> str:
    """Escape a table cell for LaTeX. Text written with LaTeX already (math segments between $, \\rightarrow, \\Delta,
    \\, and escaped characters) is kept; everything else is escaped."""
    s = str(s)
    if "$" in s:  # keep math segments verbatim
        parts = s.split("$")
        return "$".join(part if i % 2 else tex(part) for i, part in enumerate(parts))
    s = s.replace("\\rightarrow", "→").replace("\\Delta", "Δ").replace("\\,", " ").replace("\\%", "%").replace("\\_", "_").replace("\\&", "&").replace("\\#", "#")
    s = s.replace("\\", "\\textbackslash{}").replace("%", "\\%").replace("&", "\\&").replace("_", "\\_").replace("#", "\\#")
    s = s.replace("±", "$\\pm$").replace("Δ", "$\\Delta$").replace("²", "$^2$").replace("·", "$\\cdot$").replace("→", "$\\rightarrow$").replace("−", "$-$").replace("–", "--").replace("×", "$\\times$")
    s = s.replace("≥", "$\\geq$").replace("≤", "$\\leq$").replace("√", "$\\surd$").replace("⁴", "$^4$").replace("⁶", "$^6$")
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"`([^`]+)`", r"\\texttt{\1}", s)
    return s


def table(rows: list[list[str]], header: list[str], src: list[str], caption: str, label: str, colspec: str | None = None,
          size: str = "\\small", note: str | None = None, star: bool = False, bold: set[tuple[int, int]] | None = None,
          placement: str = "tb", body_only: bool = False) -> str:
    """body_only: caption, label and tabular without the float environment (main.tex packs it into its own float)."""
    ncol = len(header)
    colspec = colspec or ("l" * ncol)
    env = "table*" if star else "table"
    out = [f"% src: {'; '.join(src)}"] + ([] if body_only else [f"\\begin{{{env}}}[{placement}]"]) + ["\\centering", size, "\\setlength{\\tabcolsep}{3.5pt}", f"\\caption{{{caption}}}", f"\\label{{{label}}}"]
    if star:
        out.append("\\setlength{\\tabcolsep}{2.2pt}")  # wide appendix tables: never scaled below the font size
    out += [f"\\begin{{tabular}}{{{colspec}}}", "\\toprule", " & ".join(tex(h) for h in header) + " \\\\", "\\midrule"]
    for i, r in enumerate(rows):
        cells = [tex(c) for c in r]
        if bold:
            cells = [f"\\textbf{{{c}}}" if (i, j) in bold else c for j, c in enumerate(cells)]
        out.append(" & ".join(cells) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}"]
    if note:
        out.append(f"\\par\\vspace{{2pt}}{{\\footnotesize {tex(note)}}}")
    if not body_only:
        out.append(f"\\end{{{env}}}")
    return "\n".join(out) + "\n"


def pareto_method(m: str) -> str:
    """'unet_T4_M_s1_scalenorm (learned, 1 seed)' -> 'U-Net, scale-aware target (1 seed)'; solver rows keep their block."""
    m = m.replace(" (correct_artifacts=1)", ", corr. on").replace(" (correct_artifacts=0)", ", corr. off").replace("(exact, reference)", "(exact)").replace("production ", "prod. ")
    r = re.match(r"^(unet|fno|vit|gnn|mgno)_T4_[A-Z]+(?:_s\d)?(_t2)?(_scalenorm)?(?: \((tuned)\))? \(learned, (\d seeds?)\)$", m)
    if r:
        base = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN", "mgno": "MgNO"}[r.group(1)]
        return base + (" tuned" if (r.group(2) or r.group(4)) else "") + (", scale-aware target" if r.group(3) else "") + f" ({r.group(5)})"
    m = re.sub(r"radius law \+ conductance \(k=[\d.]+, beta=[\d.]+\) \(no solver, 1 core\)", "radius law, fitted (CPU)", m)
    m = m.replace("radius law (k=2/3, no fit) (no solver, 1 core)", "radius law, $k=2/3$ (CPU)")
    return m.replace(" (learned, 3 seeds)", " (3 seeds)").replace(" (learned, 1 seed)", " (1 seed)")


def ms_value(cell: str) -> float:
    m = re.match(r"\s*([-+]?[\d.]+)", cell.replace("−", "-"))
    return float(m.group(1)) if m else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="paper/neurips/tables")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)

    # ---- Table 1: counts per tier (dataset card / final_counts.json)
    fc = json.loads((ROOT / "docs" / "tables" / "final_counts.json").read_text())
    rows = []
    for t in TIERS:
        d = fc["tiers"][t]
        rows.append([t, {"S": "128² · 100 m", "M": "256² · 100 m", "L": "512² · 200 m", "XL": "1024² · 500 m", "XXL": "2048² · 1 km"}[t],
                     f"{d['samples']:,}", f"{d['rows']:,}", f"{d['family']['synthetic']:,} / {d['family']['real']:,}", f"{d['gb']:.1f}", str(d["qc_fail_rows"])])
    tot = fc["tiers"]
    rows.append(["total", "", f"{sum(tot[t]['samples'] for t in TIERS):,}", f"{sum(tot[t]['rows'] for t in TIERS):,}", "", f"{sum(tot[t]['gb'] for t in TIERS):.1f}", str(sum(tot[t]['qc_fail_rows'] for t in TIERS))])
    (out / "tab_counts.tex").write_text(table(rows, ["tier", "raster · pixel", "landscapes", "configuration rows", "synthetic / real", "GB on the Hub", "rows failing QC"],
                                               ["docs/tables/final_counts.json", "docs/dataset_card.md"],
                                               "AmpScape v1.0 per tier. A landscape is one resistance raster; each of its source configurations is a configuration row. The 25 rows failing quality control (24 landscapes, all synthetic at contrast $\\geq 10^4$) stay in the index with their flags and are excluded from the split lists.",
                                               "tab:counts", "llrrrrr", size="\\footnotesize"))

    # ---- Table 2: main results, rel-L2 mean ± std [median] per task × model × tier (paper/tables/baselines_sml.md)
    bs = md_rows(ROOT / "paper" / "tables" / "baselines_sml.md")
    rows, bold = [], set()
    for task in ("T1", "T3", "T4"):
        models = [m for m in MODELS if any(r["task"] == task and r["model"] == m for r in bs)]
        block = []
        for m in models:
            cells = [task, m]
            for t in ("S", "M", "L"):
                r = next((r for r in bs if r["task"] == task and r["model"] == m and r["tier"] == t), None)
                cells.append(f"{r['rel-L2']} [{r['rel-L2 median']}]" if r else "--")
            block.append(cells)
        for j in range(2, 5):
            vals = [(ms_value(c[j]), i) for i, c in enumerate(block) if c[j] != "--" and c[1] != "MgNO"]
            if vals:
                bold.add((len(rows) + min(vals)[1], j))
        rows += block
    (out / "tab_results_main.tex").write_text(table(rows, ["task", "model", "S", "M", "L"], ["paper/tables/baselines_sml.md"],
                                                     "Relative L2 on \\texttt{test\\_id} at the training tier, mean $\\pm$ std over three seeds with the median over seeds in brackets (official configuration per model $\\times$ task $\\times$ tier; MgNO: three seeds at S and M, not ranked because 4 of its 6 T4 runs diverged, see text). Best three-seed model per task and tier in bold; lower is better. The complete metric set (MAE, top-5\\,\\% IoU, pinch recall, Spearman, speed-up, training cost) is Table~\\ref{tab:baselines_full}.",
                                                     "tab:results", "llccc", size="\\scriptsize", bold=bold))

    # ---- appendix: full metric table on test_id
    rows = [[r["task"], r["tier"], r["model"], f"{r['rel-L2']} [{r['rel-L2 median']}]", r["MAE log10"], r["top-5 % IoU"], r["pinch recall"], r["Spearman"], r["speed-up (median)"], r["train GPU-h"]]
            for r in sorted(bs, key=lambda r: (r["task"], TIERS.index(r["tier"]), MODELS.index(r["model"])))]
    (out / "tab_baselines_full.tex").write_text(table(rows, ["task", "tier", "model", "rel-L2 [median]", "MAE log$_{10}$", "top-5\\,\\% IoU", "pinch recall", "Spearman", "speed-up", "GPU-h / run"],
                                                       ["paper/tables/baselines_sml.md"],
                                                       "Learned baselines on \\texttt{test\\_id}, every metric (mean $\\pm$ std over three seeds; median speed-up = solver wall time / inference time per landscape; GPU-h = training cost per run).",
                                                       "tab:baselines_full", "llllllllrr", size="\\scriptsize", star=True))

    # ---- appendix: configuration decisions
    dec = md_rows(ROOT / "docs" / "tables" / "tuning_decisions.md")
    rows = [[r["tier"], r["task"], r["model"], r["tuned variant"], r["val loss pre-tuning (mean ± std)"], r["val loss tuned (mean)"], r["Δ"], r["official config"].replace("**", "")] for r in dec]
    (out / "tab_decisions.tex").write_text(table(rows, ["tier", "task", "model", "variant", "val loss pre-tuning", "tuned", "$\\Delta$", "official"], ["docs/tables/tuning_decisions.md"],
                                                 "Configuration selection per model $\\times$ task $\\times$ tier on validation loss alone (masked MSE in the log-target space; mean over three pre-tuning seeds $\\pm$ std against the mean of three tuned seeds; the tuned configuration is official when it beats the pre-tuning mean by more than std$/\\sqrt{3}$).",
                                                 "tab:decisions", "lllllllr", size="\\scriptsize", star=True))

    # ---- appendix: tuning effect on test_id
    te = [r for r in md_rows(ROOT / "docs" / "tables" / "tuning_effect.md") if r.get("split") == "test_id"]
    def _split(cell: str) -> tuple[str, str]:
        m = re.match(r"(.*?)\s*\((.*)\)\s*$", cell)
        return (m.group(1), m.group(2)) if m else (cell, "")

    rows = []
    for r in te:
        rl, d_rl = _split(r["rel-L2 pre-tuning → tuned (Δ)"])
        mae, d_mae = _split(r["MAE log10 pre-tuning → tuned (Δ)"])
        rows.append([r["task"], r["tier"], r["model"], r["official"], rl, d_rl, mae, d_mae])
    (out / "tab_tuning_effect.tex").write_text(table(rows, ["task", "tier", "model", "official", "rel-L2 pre-tuning $\\rightarrow$ tuned", "$\\Delta$", "MAE log$_{10}$ pre-tuning $\\rightarrow$ tuned", "$\\Delta$"], ["docs/tables/tuning_effect.md"],
                                                     "Effect of the per-tier tuning on \\texttt{test\\_id} (mean $\\pm$ std over three seeds), with the official choice of Table~\\ref{tab:decisions}. The validation rule keeps the pre-tuning configuration for U-Net T3 M despite a better test rel-L2 and for ViT and GNN T4 M where the tuned one is worse on test: test metrics are never read.",
                                                     "tab:tuning_effect", "llllrrrr", size="\\scriptsize", star=True))

    # ---- appendix: T4 Pareto at M and L (test_id rows)
    for tier in ("M", "L"):
        pr = [r for r in md_rows(ROOT / "paper" / "tables" / f"t4_pareto_{tier}.md") if r["split"] == "test_id"]
        n_sub = pr[0]["n"] if pr else ""
        rows = [[pareto_method(r["method"]), r["cost s / landscape"], r["rel_l2"], r["rel_l2 median (seeds)"], r["ns_rel_l2"], r["mae_log10eps"], r["top5_iou"], r["pinch_recall"], r["spearman"]] for r in pr]
        (out / f"tab_pareto_{tier}.tex").write_text(table(rows, ["method", "cost (s)", "rel-L2", "median", "non-source rel-L2", "MAE log$_{10}$", "top-5\\,\\% IoU", "pinch recall", "Spearman"], [f"paper/tables/t4_pareto_{tier}.md"],
                                                            f"T4 at tier {tier} against the exact block-1 Omniscape map on the \\texttt{{test\\_id}} reference subset ($n = {n_sub}$ landscapes): Omniscape solver rows (corr. = artefact correction; cost = single-core wall time per landscape) and learned models (cost = median batch-amortised GPU inference per landscape; median = median over seeds; seeds averaged otherwise).",
                                                            f"tab:pareto_{tier}", "lrrrrrrrr", size="\\scriptsize", star=True))

    # ---- appendix: scale transfer (test_id rows)
    st = [r for r in md_rows(ROOT / "paper" / "tables" / "scale_transfer.md") if r["split"] == "test_id"]
    rows = [[r["task"], r["model"], r["variant"], r["eval tier"], r["seeds"], f"{r['rel-L2']} [{r['rel-L2 median']}]", r["Spearman"], r["top-5 % IoU"], r["throughput err"]] for r in st]
    (out / "tab_scale_transfer.tex").write_text(table(rows, ["task", "model", "variant", "eval tier", "seeds", "rel-L2 [median]", "Spearman", "top-5\\,\\% IoU", "throughput err."], ["paper/tables/scale_transfer.md"],
                                                      "Scale transfer on \\texttt{test\\_id}: models trained at L evaluated at L, XL and XXL at batch 1 with the training tier's normalisation statistics; zero-shot = official configuration (three seeds), scale-aware = \\texttt{-{}-target-norm scale} (seed 1). The ViT's interpolated positional embedding stops at XL.",
                                                      "tab:scale_transfer", "lllllllll", size="\\scriptsize", star=True))

    # ---- appendix: OOD degradation
    od = md_rows(ROOT / "paper" / "tables" / "ood_degradation.md")
    rows = [[r["task"], r["tier"], r["model"], r["test_id [median]"], r["test_ood [median]"], r["ood_region [median]"], r["published [median]"], r["test_ood / id"], r["ood_region / id"], r["published / id"]] for r in od]
    (out / "tab_ood.tex").write_text(table(rows, ["task", "tier", "model", "test\\_id", "test\\_ood", "ood\\_region", "published", "test\\_ood / id", "ood\\_region / id", "published / id"], ["paper/tables/ood_degradation.md"],
                                           "Rel-L2 per in-tier split (mean over three seeds, median in brackets) and ratios to \\texttt{test\\_id}; \\texttt{test\\_ood} = held-out resistance table and contrast $10^6$, \\texttt{ood\\_region} = held-out biomes and realm, published = real tiles with published resistance surfaces (S only).",
                                           "tab:ood", "lllrrrrrrr", size="\\scriptsize", star=True))

    # ---- appendix: acceleration
    ac = md_rows(ROOT / "docs" / "tables" / "acceleration.md")
    rows = [[r["task"], r["tier"], {"fno": "FNO", "unet": "U-Net"}.get(r["model"], r["model"]), r["split"], r["systems"], r["iters zero → warm"], r["iter reduction"], r["time zero → warm (ms)"], r["time reduction"], r["warm-start residual"]] for r in ac]
    (out / "tab_acceleration.tex").write_text(table(rows, ["task", "tier", "model", "split", "systems", "iterations zero $\\rightarrow$ warm", "reduction", "time zero $\\rightarrow$ warm (ms)", "reduction", "warm-start residual"], ["docs/tables/acceleration.md"],
                                                    "Solver acceleration: AMG-preconditioned CG warm-started from the predicted voltage versus a zero start, to a relative residual of $10^{-6}$ (medians over systems; reduction = median of $1 - $ warm/zero per system; warm-start residual = relative Kirchhoff residual of the prediction, zero start = 1). T1V = first pair of each T1 landscape.",
                                                    "tab:acceleration", "llllrlrlrr", size="\\scriptsize", star=True))

    # ---- appendix: data scaling
    wp4 = md_rows(ROOT / "paper" / "tables" / "wp4_data_scaling.md")
    rows = [[r["model"], r["n train"], {"ep30": "fixed epochs (30)", "steps": "fixed steps", "full": "official run"}.get(r["regime"], r["regime"]), r["rel-L2"], r["MAE log10"], r["top-5 % IoU"], r["epochs"], r["train GPU-h"]] for r in wp4]
    (out / "tab_wp4.tex").write_text(table(rows, ["model", "n train", "regime", "rel-L2", "MAE log$_{10}$", "top-5\\,\\% IoU", "epochs", "GPU-h"], ["paper/tables/wp4_data_scaling.md"],
                                           "Data-scaling ablation at S on T1 (seed 1): training on 1,000 / 5,000 / 20,000 landscapes for 30 epochs or for the official run's number of optimisation steps, against the official run on all training landscapes.",
                                           "tab:wp4", "llllllrr", size="\\footnotesize", body_only=True))

    # ---- appendix: precision pass
    pp = md_rows(ROOT / "docs" / "tables" / "precision_pass.md")
    rows = [[r["tier"].replace("**", ""), r["rows re-solved"].replace("**", ""), r["of which `cg+amg` (now `cholmod`)"], r["residual after: p50 / p90 / p99 / max"], r["rows > 1e-9 (floor, recorded)"], r["rows > 1e-6 (flagged, excluded from splits)"]] for r in pp]
    (out / "tab_precision.tex").write_text(table(rows, ["tier", "rows re-solved", "CG+AMG $\\rightarrow$ CHOLMOD", "residual after: p50 / p90 / p99 / max", "rows $> 10^{-9}$", "rows $> 10^{-6}$ (flagged)"], ["docs/tables/precision_pass.md"],
                                                "Post-run precision pass per tier: every T1/T1W/T1R/T3 row above $10^{-9}$, unmeasured, CG+AMG-solved or QC-failed was re-solved with CHOLMOD on the reduced system plus up to three refinement steps; rows that cannot reach $10^{-6}$ in double precision are flagged and excluded from the split lists.",
                                                "tab:precision", "lrrlrr", size="\\scriptsize", star=True))

    # ---- appendix: splits per tier
    rows = []
    for t in TIERS:
        s = fc["tiers"][t]["splits"]
        rows.append([t, f"{s.get('train', 0):,}", f"{s.get('val', 0):,}", f"{s.get('test_id', 0):,}", f"{s.get('test_ood', 0):,}", f"{s.get('ood_region', 0):,}", str(fc["tiers"][t]["qc_fail_samples"])])
    (out / "tab_splits.tex").write_text(table(rows, ["tier", "train", "val", "test\\_id", "test\\_ood", "ood\\_region", "QC-failing landscapes"], ["docs/tables/final_counts.json"],
                                             "Landscapes per split and tier (index counts before QC exclusion; XL after the v1.0.2 correction of amendment C3).",
                                             "tab:splits", "lrrrrrr", size="\\small"))

    # ---- appendix: licences (docs/licenses.md; its cells contain '|' inside braces, so the rows are transcribed)
    rows = [["ESA WorldCover land cover, 10 m", "2021 v200", "CC BY 4.0", "class codes"],
            ["Copernicus DEM GLO-30", "2021 release (DLR 2010--2014, Airbus 2014--2018)", "Copernicus licence; Art. 4 rights of use, Art. 6 notices reproduced", "elevation, slope"],
            ["GRIP4 global roads", "v4, 2018", "CC0 by the publisher; CC BY 4.0 in secondary catalogues (attributed as CC BY 4.0)", "distance-to-road only"],
            ["HydroRIVERS", "v1.0", "CC BY 4.0", "distance-to-river only"],
            ["gHM global Human Modification", "v1, 1 km", "CC BY 4.0", "gHM"],
            ["RESOLVE Ecoregions 2017", "2017", "CC BY 4.0", "stratification only (biome, realm)"],
            ["Eurac Alps permeability", "2022", "CC BY 4.0", "published resistance tiles"],
            ["Hawaiian gallinule resistance", "2020", "CC0 1.0", "published resistance tiles"],
            ["Northern raccoon Europe maps", "2025", "CC BY 4.0", "published resistance tiles"]]
    (out / "tab_licences.tex").write_text(table(rows, ["layer", "version", "licence", "derived rasters redistributed"], ["docs/licenses.md"],
                                               "Upstream data sources, their licences and what AmpScape stores (derived rasters only; never the source tiles). WDPA polygons (restrictive licence) and OpenStreetMap (ODbL) are not used. The dataset is released under CC BY 4.0, code and solver wrapper under MIT.",
                                               "tab:licences", "p{2.9cm}p{2.9cm}p{4.6cm}p{2.7cm}", size="\\scriptsize", star=True, placement="htbp"))
    # ---- appendix (review round 2): Omniscape wall time vs threads, like-for-like speed-up and break-even
    thr = ROOT / "docs" / "tables" / "review_round2_threads.md"
    if thr.exists():
        rows_t = [[r["tier"], r["threads"], r["n landscapes"], r["wall s per landscape (median)"], r["speed-up vs 1 thread"], r["parallel efficiency"]] for r in md_rows(thr) if "threads" in r]
        (out / "tab_threads.tex").write_text(table(rows_t, ["tier", "Julia threads", "landscapes", "wall s / landscape (median)", "speed-up vs 1 thread", "parallel efficiency"], ["docs/tables/review_round2_threads.md"],
                                               "Production Omniscape solve (radius / block: M 32 / 3, L 64 / 5; CHOLMOD window solver; artefact correction on) on the first \\texttt{test\\_id} reference landscapes with Omniscape's own parallelisation (\\texttt{parallelize = true}) on one CPU node; 1 thread is the production setting under which every solver time in this paper was measured.",
                                               "tab:threads", "llrrrr", size="\\footnotesize"))
        rows_b = [[r["tier"], r["model"], r["inference s / map (GPU)"], r["train GPU-h"], r["solver s / map, 1 thread"], r["speed-up, 1 thread"], r["solver s / map, max threads"].split(" (")[0], r["speed-up, max threads"], r["break-even maps (1 thread)"], r["break-even maps (max threads)"]] for r in md_rows(thr) if "break-even maps (1 thread)" in r]
        (out / "tab_breakeven.tex").write_text(table(rows_b, ["tier", "model", "inference s", "train GPU-h", "solver s (1)", "speed-up (1)", "solver s (24)", "speed-up (24)", "break-even (1)", "break-even (24)"], ["docs/tables/review_round2_threads.md"],
                                                 "Like-for-like cost of the T4 surrogates at M and L (rel-L2 against the exact block-1 map in Table~\\ref{tab:pareto_M} and \\ref{tab:pareto_L}): GPU inference seconds per landscape (batch-amortised, official runs, seed mean) and training GPU-hours of one run against the production solver's seconds per landscape on 1 and on 24 threads (Table~\\ref{tab:threads}); break-even = the number of maps from which training once plus inference costs less wall time than the solver, $N \\ge T_{\\mathrm{train}} / (t_{\\mathrm{solver}} - t_{\\mathrm{inference}})$. GPU and CPU-node hours are not priced equally; only wall time is compared.",
                                                 "tab:breakeven", "llrrrrrrrr", size="\\scriptsize", star=True))
    # ---- appendix (review rounds 2-3): truncated PCG and coarsen-x4 against the learned models on T1 and T3, same
    # landscapes and same targets (round 3: T1 over every pair; mean and median both reported)
    pj = ROOT / "docs" / "tables" / "review_round3_pcg.json"
    if pj.exists():
        import json as _json
        d = _json.loads(pj.read_text())
        rows_c = []
        for task in ("T1", "T3"):
            for tier in ("S", "M", "L"):
                rs = {r["method"]: r for r in d.get(task, {}).get(tier, [])}
                if not rs:
                    continue
                mm = lambda r: f"{r['rel_l2_mean']:.3f} / {r['rel_l2_median']:.3f}"  # noqa: E731
                learned = [r for k, r in rs.items() if not k.startswith(("PCG", "coarsen")) and k != "MgNO"]
                best = min(learned, key=lambda r: r["rel_l2_mean"])
                rows_c.append([task, tier, str(rs["PCG k=2"]["n"]), mm(rs["PCG k=2"]), f"{rs['PCG k=2']['cost_s']:.3f}", mm(rs["PCG k=4"]), mm(rs["PCG k=8"]),
                               f"{rs['PCG to 1e-6']['cost_s']:.3f}", mm(rs["coarsen x4"]) if "coarsen x4" in rs else "--",
                               f"{mm(best)} ({best['method']})"])
        (out / "tab_cheap.tex").write_text(table(rows_c, ["task", "tier", "$n$", "PCG $k=2$", "s", "PCG $k=4$", "PCG $k=8$", "PCG to $10^{-6}$: s", "coarsen $\\times 4$", "best learned"], ["docs/tables/review_round3_pcg.md"],
                                             "Cheap numerical baselines against the learned models on the same \\texttt{test\\_id} landscapes and the same targets (T1: the cumulative map over all pairs; T3: the advanced-mode current): rel-L2 mean / median over the landscapes. AMG-preconditioned CG from zero stopped after $k$ iterations, with its cost in seconds per landscape on one CPU core (AMG setup included; T1: one setup per grounded node, all pairs), the cost of the full solve to relative residual $10^{-6}$, coarsen-$\\times 4$-solve-upsample, and the official learned model with the lowest mean (seed mean per landscape; MgNO excluded as in Table~\\ref{tab:results}).",
                                             "tab:cheap", "llrlllllll", size="\\scriptsize", star=True))
    # ---- appendix (review round 3): bootstrap intervals and strata of the headline rel-L2
    bj = ROOT / "docs" / "tables" / "review_round3_bootstrap.json"
    if bj.exists():
        import json as _json

        import pandas as _pd
        bd = _pd.DataFrame(_json.loads(bj.read_text())["rows"])
        strata = ["test_id synthetic", "test_id real", "test_ood contrast 1e6", "test_ood held-out table", "published (S)"]
        rows_bs = []
        for task in ("T1", "T3", "T4"):
            for tier in ("S", "M", "L"):
                for model in ("U-Net", "FNO", "ViT", "GNN", "MgNO"):
                    g = bd[(bd.task == task) & (bd.tier == tier) & (bd.model == model)].set_index("stratum")
                    if "test_id" not in g.index:
                        continue
                    r = g.loc["test_id"]
                    cells = [task, tier, model, f"{r.rel_l2:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}]"]
                    cells += [f"{g.loc[st].rel_l2:.3f}" if st in g.index else "--" for st in strata]
                    rows_bs.append(cells)
        (out / "tab_bootstrap.tex").write_text(table(rows_bs, ["task", "tier", "model", "test_id [95 % CI]", "synthetic", "real", "contrast $10^6$", "held-out table", "published"], ["docs/tables/review_round3_bootstrap.md"],
                                                 "Relative L2 of the official runs by stratum (seed mean of per-seed means, as in Table~\\ref{tab:results}). The interval resamples landscapes (2,000 resamples, the same for every seed; percentile interval) and so reflects landscape sampling, not seed variance (the $\\pm$ of Table~\\ref{tab:results}). Synthetic and real: the two families of \\texttt{test\\_id}; contrast $10^6$ and held-out table: the two parts of \\texttt{test\\_ood}; published: \\texttt{test\\_ood\\_published} (S only). Intervals for every stratum are in the source file.",
                                                 "tab:bootstrap", "lllllllll", size="\\scriptsize", star=True, placement="htbp"))
    # ---- appendix (review round 3): decision-level evaluation of the many-query demonstration, bf16 vs fp32 inference
    dj = {t: ROOT / "docs" / "tables" / f"review_round3_decision_{t}.json" for t in ("bf16", "fp32")}
    if all(f.exists() for f in dj.values()):
        import json as _json
        dd = {t: _json.loads(f.read_text()) for t, f in dj.items()}
        rows_d = []
        for top in (1.0, 5.0, 10.0):
            for frac in (0.375, 0.5, 0.75):
                cells = [f"{top:g}", f"{frac:g}"]
                for t in ("bf16", "fp32"):
                    r = next(x for x in dd[t]["sweep"] if x["top_percent"] == top and x["persistence"] == frac and x["tolerance_px"] == 3)
                    cells += [f"{r['precision']:.3f}", f"{r['recall']:.3f}", f"{r['n_model']:.0f}"]
                cells.append(f"{r['n_solver']:.0f}")
                rows_d.append(cells)
        (out / "tab_decision.tex").write_text(table(rows_d, ["top \\%", "persistence", "bf16 precision", "bf16 recall", "bf16 points", "fp32 precision", "fp32 recall", "fp32 points", "solver points"], ["docs/tables/review_round3_decision_bf16.md", "docs/tables/review_round3_decision_fp32.md"],
                                                 "Persistent pinch points of the surrogate route against the solver route in the many-query demonstration (20 real L tiles $\\times$ 8 tables, U-Net seed 1), over the decision parameters: a pinch point is a local maximum in the top-$q$\\,\\% of a map; persistent = present (within 3~px) in at least the given share of the tables; matching tolerance 3~px; precision, recall and points per tile averaged over tiles. Left block: inference under bf16 autocast (the setting of Section~\\ref{sec:wp7}); right block: fp32 inference of the same model. The demonstration's setting is $q=5$, persistence 0.5.",
                                                 "tab:decision", "rrrrrrrrr", size="\\scriptsize", placement="htbp"))
        rows_v = []
        for m in (0, 2, 4, 5, 6, 7, 8):
            cells = [str(m)]
            for t in ("bf16", "fp32"):
                r = next(x for x in dd[t]["budget"] if x["tables_solved"] == m)
                cells += [f"{r['precision']:.3f}", f"{r['recall']:.3f}", f"{r['core_iou']:.3f}"]
            cells.append(f"{r['solver_cpu_h_per_tile']:.2f}")
            rows_v.append(cells)
        (out / "tab_verify.tex").write_text(table(rows_v, ["tables solved", "bf16 precision", "bf16 recall", "bf16 core IoU", "fp32 precision", "fp32 recall", "fp32 core IoU", "solver CPU-h / tile"], ["docs/tables/review_round3_decision_bf16.md", "docs/tables/review_round3_decision_fp32.md"],
                                               "Verification budget in the many-query demonstration: $m$ of the 8 tables per tile are solved exactly and the surrogate supplies the rest (tables in the surrogate's own order of influence, reference table first). Persistent-pinch-point precision and recall and the consensus-core IoU against the all-solver route, for bf16 (left) and fp32 (right) inference, and the solver cost per tile (one core).",
                                               "tab:verify", "rrrrrrrr", size="\\scriptsize", placement="htbp"))
    # ---- appendix (review round 3): T4 under source rules the models never saw
    sj = ROOT / "docs" / "tables" / "review_round3_source_ood.json"
    if sj.exists():
        import json as _json
        sd = _json.loads(sj.read_text())
        rows_s = []
        names = {"unet": "U-Net", "fno": "FNO", "vit": "ViT", "gnn": "GNN", "mgno": "MgNO", "unchanged": "production-rule map"}
        for tier in ("S", "M"):
            if tier not in sd:
                continue
            ag = {(r["model"], r["rule"], r["input"]): r["rel_l2"] for r in sd[tier]["rows"]}
            for mk in ("unet", "fno", "vit", "gnn", "mgno", "unchanged"):
                if mk == "unchanged":
                    cells = [tier, names[mk], "0"]
                    for rule in ("uniform", "random_field", "habitat_core"):
                        cells += ["--", f"{ag[(mk, rule, '-')]:.3f}"]
                else:
                    cells = [tier, names[mk], f"{ag[(mk, 'default', 'true')]:.3f}"]
                    for rule in ("uniform", "random_field", "habitat_core"):
                        cells += [f"{ag[(mk, rule, 'true')]:.3f}", f"{ag[(mk, rule, 'production')]:.3f}"]
                rows_s.append(cells)
        (out / "tab_source.tex").write_text(table(rows_s, ["tier", "model", "production rule", "uniform: true", "swapped", "random field: true", "swapped", "habitat core: true", "swapped"], ["docs/tables/review_round3_source_ood.md"],
                                                 "T4 under source rules the models never saw: rel-L2 against the exact Omniscape map of each rule on the same \\texttt{test\\_id} landscapes (200 at S, 100 at M) and Omniscape geometry. \\emph{true}: the rule's own source raster as input; \\emph{swapped}: the production source raster of the same landscape as input, so a model that ignored its source channel would score the same in both columns; production-rule map: the solver's map under the production rule used as the prediction. Rules: uniform sources on every valid pixel; a Gaussian random field independent of resistance, kept above its median; $(1/R)^2$ above its 0.8 quantile. Official runs, three seeds, fp32 inference on CPU.",
                                                 "tab:source", "llrrrrrrr", size="\\scriptsize", star=True, placement="htbp"))
    print("tables:", sorted(p.name for p in out.glob("*.tex")))


if __name__ == "__main__":
    main()
