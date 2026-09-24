#!/usr/bin/env python
"""Dataset statistics figures for v1.0 (Phase 12 §data): contrast, biome/realm coverage, NoData fraction, solve-time
distributions and per-tier storage, from the published indexes (data/hf/AmpScape/index/*.parquet), the tile manifest,
the Hub size table (docs/tables/final_counts.json) and the NoData sample (docs/tables/nodata_sample.parquet).

  python scripts/dataset_stats_figures.py [--out docs/figures] [--table docs/tables/dataset_statistics.md]
"""

from __future__ import annotations

import argparse
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

TIERS = ["S", "M", "L", "XL", "XXL"]
CONFIG_ORDER = ["points", "wall_to_wall_NS", "wall_to_wall_EW", "regions", "advanced", "omniscape"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", default="data/hf/AmpScape/index")
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--table", default="docs/tables/dataset_statistics.md")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    idx = pd.concat(
        [pd.read_parquet(f"{a.index_dir}/{t}.parquet").assign(tier=t) for t in TIERS],
        ignore_index=True,
    )
    samples = idx.drop_duplicates("sample_id")
    tiles = pd.read_parquet("data/tiles/v1.0/tiles.parquet")
    counts = json.loads(pathlib.Path("docs/tables/final_counts.json").read_text())
    lines = ["# v1.0 dataset statistics", ""]

    # 1. contrast (synthetic: design contrast; real: max/min of the resistance table → recorded contrast column)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for fam, axi in (("synthetic", ax[0]), ("real", ax[1])):
        sub = samples[samples.family == fam]
        for t in TIERS:
            c = sub[sub.tier == t].contrast.dropna()
            if len(c):
                axi.hist(np.log10(c), bins=40, histtype="step", label=f"{t} (n={len(c):,})")
        axi.set_xlabel("log10 contrast (max / min resistance)")
        axi.set_ylabel("landscapes")
        axi.set_title(f"{fam} landscapes")
        axi.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "dataset_stats_contrast.png", dpi=150)
    plt.close(fig)
    lines += [
        "## Contrast",
        "",
        "| tier | family | n | log10 contrast p10 / p50 / p90 | max |",
        "|---|---|---|---|---|",
    ]
    for t in TIERS:
        for fam in ("synthetic", "real"):
            c = samples[(samples.tier == t) & (samples.family == fam)].contrast.dropna()
            if len(c):
                q = np.log10(c).quantile([0.1, 0.5, 0.9])
                lines.append(
                    f"| {t} | {fam} | {len(c):,} | {q.iloc[0]:.2f} / {q.iloc[1]:.2f} / {q.iloc[2]:.2f} | {c.max():.3g} |"
                )

    # 2. biome / realm coverage of the real tiles (per tier, sample level)
    real = samples[samples.family == "real"].merge(
        tiles[["tile_id", "biome_name"]], on="tile_id", how="left"
    )
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    bi = (
        real.groupby(["biome_name", "tier"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=TIERS, fill_value=0)
    )
    bi = bi.loc[bi.sum(axis=1).sort_values(ascending=False).index]
    bi.plot.barh(stacked=True, ax=ax[0])
    ax[0].set_xlabel("real landscapes")
    ax[0].set_title("biome (WWF Ecoregions 2017)")
    ax[0].invert_yaxis()
    ax[0].tick_params(axis="y", labelsize=7)
    re_ = (
        real.groupby(["realm", "tier"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=TIERS, fill_value=0)
    )
    re_.plot.barh(stacked=True, ax=ax[1])
    ax[1].set_xlabel("real landscapes")
    ax[1].set_title("biogeographic realm")
    ax[1].invert_yaxis()
    fig.tight_layout()
    fig.savefig(out / "dataset_stats_biome_realm.png", dpi=150)
    plt.close(fig)
    lines += [
        "",
        "## Biome / realm coverage (real landscapes, all tiers)",
        "",
        "| biome | landscapes | tiles |",
        "|---|---|---|",
    ]
    for b, g in real.groupby("biome_name"):
        lines.append(f"| {b} | {len(g):,} | {g.tile_id.nunique():,} |")
    lines += ["", "| realm | landscapes | tiles |", "|---|---|---|"]
    for r, g in real.groupby("realm"):
        lines.append(f"| {r} | {len(g):,} | {g.tile_id.nunique():,} |")

    # 3. NoData fraction: real tiles from the manifest (qc_frac_unusable), synthetic from the design sample
    nd = pd.read_parquet("docs/tables/nodata_sample.parquet")
    fig, ax = plt.subplots(figsize=(7, 4))
    rt = real.merge(tiles[["tile_id", "qc_frac_unusable"]], on="tile_id", how="left")
    ax.hist(
        rt.qc_frac_unusable.dropna(),
        bins=40,
        histtype="step",
        label=f"real tiles, all tiers (n={rt.qc_frac_unusable.notna().sum():,})",
    )
    syn = nd[nd.family == "synthetic"]
    ax.hist(
        syn.nodata_frac_measured,
        bins=40,
        histtype="step",
        label=f"synthetic, sampled shards (n={len(syn):,})",
    )
    ax.set_xlabel("NoData fraction of the raster")
    ax.set_ylabel("landscapes")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "dataset_stats_nodata.png", dpi=150)
    plt.close(fig)
    lines += [
        "",
        "## NoData fraction",
        "",
        "| population | n | p10 / p50 / p90 | max |",
        "|---|---|---|---|",
    ]
    for name, s in (
        ("real tiles (manifest, all tiers)", rt.qc_frac_unusable.dropna()),
        ("synthetic (sampled shards)", syn.nodata_frac_measured),
    ):
        q = s.quantile([0.1, 0.5, 0.9])
        lines.append(
            f"| {name} | {len(s):,} | {q.iloc[0]:.3f} / {q.iloc[1]:.3f} / {q.iloc[2]:.3f} | {s.max():.3f} |"
        )

    # 4. solve-time distributions per tier and configuration
    fig, axes = plt.subplots(1, 5, figsize=(18, 4), sharey=False)
    for axi, t in zip(axes, TIERS):
        sub = idx[idx.tier == t]
        data = [
            np.log10(sub[sub.config == c].solve_time_s.clip(lower=1e-2).dropna())
            for c in CONFIG_ORDER
        ]
        axi.boxplot(
            data,
            labels=[c.replace("wall_to_wall_", "w2w_") for c in CONFIG_ORDER],
            showfliers=False,
        )
        axi.set_title(f"tier {t}")
        axi.tick_params(axis="x", rotation=60, labelsize=7)
        axi.set_ylabel("log10 solve time (s)")
    fig.tight_layout()
    fig.savefig(out / "dataset_stats_solve_times.png", dpi=150)
    plt.close(fig)
    lines += [
        "",
        "## Solve time per configuration (seconds; median / p90 / max)",
        "",
        "| tier | " + " | ".join(CONFIG_ORDER) + " | per landscape (median) |",
        "|---|" + "---|" * (len(CONFIG_ORDER) + 1),
    ]
    for t in TIERS:
        sub = idx[idx.tier == t]
        cells = []
        for c in CONFIG_ORDER:
            s = sub[sub.config == c].solve_time_s.dropna()
            cells.append(
                f"{s.median():.0f} / {s.quantile(0.9):.0f} / {s.max():.0f}" if len(s) else "—"
            )
        per = sub.groupby("sample_id").solve_time_s.sum()
        lines.append(f"| {t} | " + " | ".join(cells) + f" | {per.median():.0f} |")

    # 5. per-tier storage on the Hub, by task group
    gb = counts["per_tier_group_gb"]
    groups = ["T1", "T1W", "T1R", "T3", "T4"]
    mat = np.array([[gb.get(f"{t}/{g}", 0.0) for g in groups] for t in TIERS])
    fig, ax = plt.subplots(figsize=(7, 4))
    bottom = np.zeros(len(TIERS))
    for j, g in enumerate(groups):
        ax.bar(TIERS, mat[:, j], bottom=bottom, label=g)
        bottom += mat[:, j]
    ax.set_ylabel("GB on the Hub")
    ax.set_title(f"storage by tier and task group (total {counts['total_data_gb']:.0f} GB)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "dataset_stats_storage.png", dpi=150)
    plt.close(fig)
    lines += [
        "",
        "## Storage on the Hub (GB)",
        "",
        "| tier | " + " | ".join(groups) + " | total | landscapes | GB per landscape |",
        "|---|" + "---|" * (len(groups) + 3),
    ]
    for i, t in enumerate(TIERS):
        n = counts["tiers"][t]["samples"]
        lines.append(
            f"| {t} | "
            + " | ".join(f"{v:.1f}" for v in mat[i])
            + f" | {mat[i].sum():.1f} | {n:,} | {mat[i].sum() / n * 1000:.1f} MB |"
        )
    lines.append(
        "| **total** | "
        + " | ".join(f"{v:.1f}" for v in mat.sum(axis=0))
        + f" | **{mat.sum():.1f}** | {sum(counts['tiers'][t]['samples'] for t in TIERS):,} | |"
    )
    lines += [
        "",
        f"Subsets: mini {counts['mini_subset_gb']} GB, core {counts['core_subset_gb']} GB ({counts['core_files']:,} files), full {counts['total_data_gb']} GB; `aux/` {counts['aux_gb']} GB.",
        "",
        "Figures: `docs/figures/dataset_stats_{contrast,biome_realm,nodata,solve_times,storage}.png`.",
    ]
    pathlib.Path(a.table).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
