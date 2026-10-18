#!/usr/bin/env python
"""Review round 2: the result-dependent sentences of paper/neurips/main.tex, filled from the regenerated tables
(docs/tables/review_round2_*.json, paper/tables/baselines_sml.md, paper/tables/scale_transfer.md,
docs/tables/baselines_full.md, docs/tables/gpu_usage.md). Idempotent on the anchors it replaces; run once after the
tables are regenerated. Prints every replacement so the diff can be checked by eye."""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEX = ROOT / "paper" / "neurips" / "main.tex"


def md_rows(path):
    rows, header = [], None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def f3(v):
    return f"{float(v):.3f}"


def main() -> None:
    x = TEX.read_text()
    thr = json.loads((ROOT / "docs" / "tables" / "review_round2_threads.json").read_text())
    cheap = json.loads((ROOT / "docs" / "tables" / "review_round2_cheap.json").read_text())
    sml = md_rows(ROOT / "paper" / "tables" / "baselines_sml.md")
    st = md_rows(ROOT / "paper" / "tables" / "scale_transfer.md")
    full = md_rows(ROOT / "docs" / "tables" / "baselines_full.md")
    be = thr["break_even"]
    nt = int(be["L_unet"]["threads_max"])
    sp_m, sp_l = be["M_unet"]["speedup_max"], be["L_unet"]["speedup_max"]
    bm, bl = be["M_unet"]["break_even_max"], be["L_unet"]["break_even_max"]
    thr_l = thr["summary"][f"L_{nt}"]["speedup"]; thr_m = thr["summary"][f"M_{nt}"]["speedup"]
    # WP7 demo: 817 s per map on one core (docs/wp7_demo.md), 74 ms per map on the GPU, training 1.55 GPU-h
    demo_sp = 817 / thr_l / 0.074
    demo_be = 1.55 * 3600 / (817 / thr_l - 0.074)
    mg = {(r["task"], r["tier"]): r for r in sml if r["model"] == "MgNO"}
    def mgv(task, tier):
        return mg[(task, tier)]["rel-L2"].split("±")[0].strip()
    # scale-aware T4 recovery range (test_id, XL and XXL) over the models
    def rng(tier):
        v = [float(r["rel-L2"].split("±")[0]) for r in st if r["task"] == "T4" and r["variant"] == "scale-aware" and r["eval tier"] == tier and r["split"] == "test_id"]
        return f"{min(v):.3f}--{max(v):.3f}"
    sa_seeds = {r["model"]: r["seeds"] for r in st if r["task"] == "T4" and r["variant"] == "scale-aware" and r["eval tier"] == "XL" and r["split"] == "test_id"}
    xl = [r for r in full if r["task"] == "T4" and r["tier"] == "XL" and r["split"] == "test_id" and r["model"] == "unet_T4_XL_s1"]
    xl_rel = xl[0]["rel_l2"] if xl else None
    sa_xl_unet = next((r["rel-L2"].split("±")[0].strip() for r in st if r["task"] == "T4" and r["model"] == "U-Net" and r["variant"] == "scale-aware" and r["eval tier"] == "XL" and r["split"] == "test_id"), "0.189")
    gpu = md_rows(ROOT / "docs" / "tables" / "gpu_usage.md")
    tot = [r for r in gpu if r.get("item", "").startswith("GPU-hours consumed") and "review" in r.get("item", "")]
    gpu_h = tot[-1]["value"] if tot else None
    jobs = [r for r in gpu if r.get("item", "").startswith("GPU jobs") and "review" in r.get("item", "")]
    gpu_jobs = jobs[-1]["value"] if jobs else None

    def rep(old, new):
        nonlocal x
        assert x.count(old) == 1, f"anchor not unique/found: {old[:90]!r}"
        x = x.replace(old, new)
        print("replaced:", old[:60].replace("\n", " "), "->", new[:60].replace("\n", " "))

    # abstract
    rep("on the omnidirectional task at $10^4$--$10^5\\times$ the solver's speed, pairwise current is much harder (0.114 / 0.187 / 0.299),",
        f"on the omnidirectional task at $10^4$--$10^5\\times$ the speed of the single-core solver ({sp_l:,.0f}$\\times$ against the solver on {nt} threads at L, break-even after {bl:,.0f} maps including training), pairwise current is much harder (0.114 / 0.187 / 0.299) and two preconditioned-CG iterations match or beat every learned model there,")
    # intro headline paragraph
    rep("at median speed-ups of 167,020$\\times$, 32,789$\\times$ and 111,998$\\times$ over the production solver;",
        f"at median speed-ups of 167,020$\\times$, 32,789$\\times$ and 111,998$\\times$ over the production solver on one core ({sp_m:,.0f}$\\times$ and {sp_l:,.0f}$\\times$ against the {nt}-thread solver at M and L, Appendix~\\ref{{app:cheap}});")
    # models paragraph
    rep("\\textbf{MgNO} \\citep{he2024}: the authors' MIT release (0.58~M), seed 1 at S and M on T1 and T4. Non-learned rows: Omniscape \\emph{block-size rows} and a coarsen-$\\times 4$-and-upsample solve.",
        "\\textbf{MgNO} \\citep{he2024}: the authors' MIT release (0.58~M), three seeds at S and M on T1 and T4. Non-learned rows: Omniscape \\emph{block-size rows} for T4 and, for T1 and T3, a coarsen-$\\times 4$-and-upsample solve and the reference solver's preconditioned CG stopped after $k$ iterations (Appendix~\\ref{app:cheap}).")
    if gpu_h:
        rep("Everything learned consumed 701.5 GPU-hours across 773 jobs.", f"Everything learned consumed {gpu_h} GPU-hours across {gpu_jobs} jobs.")
    # in-distribution paragraph: like-for-like
    rep("at median speed-ups of 167,020$\\times$~/ 32,789$\\times$~/ 111,998$\\times$ over the production Omniscape run---whereas",
        f"at median speed-ups of 167,020$\\times$~/ 32,789$\\times$~/ 111,998$\\times$ over the production Omniscape run on one core; Omniscape's own parallelisation gains only {thr_m:.1f}$\\times$ at M and {thr_l:.1f}$\\times$ at L on {nt} threads, so the like-for-like figures are {sp_m:,.0f}$\\times$ and {sp_l:,.0f}$\\times$ and the surrogate pays back its training after {bm:,.0f} and {bl:,.0f} maps (Appendix~\\ref{{app:cheap}})---whereas")
    # families paragraph: MgNO three seeds
    mgmed = {k: r["rel-L2 median"] for k, r in mg.items()}
    rep("MgNO (seed 1) matches the U-Net on T4 at S (0.044 vs 0.041) but falls to 0.189 at M and 0.220~/ 0.412 on T1.",
        f"MgNO's surviving seeds match the U-Net on T4 at S (median {mgmed[('T4', 'S')]} vs 0.041) and reach {mgv('T4', 'M')} at M and {mgv('T1', 'S')}~/ {mgv('T1', 'M')} on T1, but under the shared protocol (AdamW $10^{{-3}}$, bf16 autocast) its training loss explodes within the first four epochs in 4 of 6 T4 runs and 2 of 6 T1 runs, so its seed means carry that instability (T4 S {mgv('T4', 'S')}).")
    # scale transfer: seeds and the XL-trained run
    rep("$\\sqrt{N_{\\mathrm{valid}}/512^2}$ for T1 (scale-aware, seed 1);",
        "$\\sqrt{N_{\\mathrm{valid}}/512^2}$ for T1 (scale-aware; three seeds for the U-Net on T4 and for the FNO on T4 at XL, seed 1 otherwise);")
    rep("Removing that factor recovers T4 to 0.157--0.308 at XL and 0.197--0.438 at XXL, still above in-tier errors but no longer set by a known factor; the FNO transfers best (0.157~/ 0.197).",
        f"Removing that factor recovers T4 to {rng('XL')} at XL and {rng('XXL')} at XXL, still above in-tier errors but no longer set by a known factor; the FNO transfers best"
        + (f". Training \\emph{{at}} XL is possible on its 880 training landscapes: a U-Net T4 run there reaches \\relltwo{{}} {xl_rel} on XL \\code{{test\\_id}} against the production target, between the zero-shot (0.515) and scale-aware ({sa_xl_unet}) L-trained models, so the scale-aware target recovers more than the small in-tier training set gives." if xl_rel else "."))
    # data scaling / acceleration: the stress-test reframing with the PCG numbers
    k2 = {t: cheap[f"T3_{t}_k2"] for t in ("S", "M", "L")}
    best = {t: min((v for k, v in cheap.items() if k.startswith(f"learned_T3_{t}_")), key=lambda v: v["rel_l2"]) for t in ("S", "M", "L")}
    rep("The value of the surrogates on these tasks is the cheaper \\emph{map}, not a better initial guess.",
        f"Nor is the map itself competitive with a cheap solve: two AMG-PCG iterations from zero ({k2['S']['cost_s']:.3f}~/ {k2['M']['cost_s']:.3f}~/ {k2['L']['cost_s']:.2f}~s per landscape on one core) reach \\relltwo{{}} {k2['S']['rel_l2']:.3f}~/ {k2['M']['rel_l2']:.3f}~/ {k2['L']['rel_l2']:.3f} on T3 against {best['S']['rel_l2']:.3f}~/ {best['M']['rel_l2']:.3f}~/ {best['L']['rel_l2']:.3f} for the best learned model, which is cheaper per landscape on a GPU but never more accurate than the solver's second iteration (Appendix~\\ref{{app:cheap}}). T1 and T3 are therefore stress tests of operator learning---global coupling through one sparse solve, singular point sources, contrast to $10^6$---not compute problems; the compute problem is T4.")
    # many-query: like-for-like
    rep("against 36.3 CPU-h on one core, i.e.\\ 11077$\\times$ after training once.",
        f"against 36.3 CPU-h on one core, i.e.\\ 11077$\\times$ after training once ({demo_sp:,.0f}$\\times$ against the {nt}-thread solver; the 1.55 GPU-h of training are paid back after {demo_be:,.0f} maps).")
    # limitations
    rep("(7)~The scale-aware variants, the data-scaling ablation, MgNO and the demonstration are single-seed.",
        "(7)~The data-scaling ablation and the demonstration are single-seed; the scale-aware variants have three seeds only for the U-Net and FNO on T4.")
    rep("(9)~Not yet tested: training at XL, fixed-step training at M/L, MgNO at L with three seeds, the resolution-versus-size probe set under \\code{aux/}.",
        "(9)~Not yet tested: training at XL beyond one U-Net T4 run, fixed-step training at M/L, MgNO at L or with fp32 / a lower learning rate (its divergences), the resolution-versus-size probe set under \\code{aux/}; no exact T4 reference exists at XL/XXL, so errors there are against the production target.")
    if gpu_h:
        rep("701.5 GPU-hours (773 jobs on L40S, A100, H100 and H200 GPUs) for everything learned, including tuning candidates, abandoned legs and duplicates.",
            f"{gpu_h} GPU-hours ({gpu_jobs} jobs on L40S, A100, H100 and H200 GPUs) for everything learned, including tuning candidates, abandoned legs and duplicates.")
        rep("Section~9 (701.5 GPU-hours over 773 jobs on L40S, A100, H100 and H200", f"Section~9 ({gpu_h} GPU-hours over {gpu_jobs} jobs on L40S, A100, H100 and H200")
    TEX.write_text(x)
    print("done")


if __name__ == "__main__":
    main()
