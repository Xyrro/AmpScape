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
                                                     "Relative L2 on \\texttt{test\\_id} at the training tier, mean $\\pm$ std over three seeds with the median over seeds in brackets (official configuration per model $\\times$ task $\\times$ tier; MgNO: one seed, not ranked). Best three-seed model per task and tier in bold; lower is better. The complete metric set (MAE, top-5\\,\\% IoU, pinch recall, Spearman, speed-up, training cost) is Table~\\ref{tab:baselines_full}.",
                                                     "tab:results", "llccc", size="\\small", bold=bold))

    # ---- appendix: full metric table on test_id
    rows = [[r["task"], r["tier"], r["model"], f"{r['rel-L2']} [{r['rel-L2 median']}]", r["MAE log10"], r["top-5 % IoU"], r["pinch recall"], r["Spearman"], r["speed-up (median)"], r["train GPU-h"]]
            for r in sorted(bs, key=lambda r: (r["task"], TIERS.index(r["tier"]), MODELS.index(r["model"])))]
    (out / "tab_baselines_full.tex").write_text(table(rows, ["task", "tier", "model", "rel-L2 [median]", "MAE log$_{10}$", "top-5\\,\\% IoU", "pinch recall", "Spearman", "speed-up", "GPU-h / run"],
                                                       ["paper/tables/baselines_sml.md"],
                                                       "Learned baselines on \\texttt{test\\_id}, every metric (mean $\\pm$ std over three seeds, MgNO one seed; median speed-up = solver wall time / inference time per landscape; GPU-h = training cost per run).",
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
    print("tables:", sorted(p.name for p in out.glob("*.tex")))


if __name__ == "__main__":
    main()
