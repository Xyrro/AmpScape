"""Learned and non-learned baselines (brief §12)."""

from __future__ import annotations


def build_model(name: str, in_channels: int, **kw):
    if name == "unet":
        from ampscape.models.unet import UNet

        return UNet(in_channels, **kw)
    if name == "fno":
        from ampscape.models.fno import FNO2d

        return FNO2d(in_channels, **kw)
    if name == "vit":
        from ampscape.models.vit import ViTUNet

        return ViTUNet(in_channels, **kw)
    if name == "gnn":
        from ampscape.models.gnn import GridGNN, MultiScaleGridGNN

        if kw.pop("multiscale", False):
            return MultiScaleGridGNN(in_channels, **kw)
        return GridGNN(in_channels, **kw)
    raise ValueError(name)


MODEL_CONFIGS = {
    "unet": {"base": 32, "levels": 4},
    "fno": {"width": 32, "modes": 16, "layers": 4},
    "vit": {"patch": 4, "dim": 192, "depth": 6, "heads": 6},
    "gnn": {"dim": 64, "layers": 12},
}


# owner tuning pass (2026-09-14): alternatives evaluated on the dev subset; the winners become the official configs
MODEL_VARIANTS = {
    "unet": {"base": MODEL_CONFIGS["unet"], "wide": {"base": 48, "levels": 4}},
    "fno": {
        "base": MODEL_CONFIGS["fno"],
        "m32": {"width": 32, "modes": 32, "layers": 4},
        "m64": {"width": 32, "modes": 64, "layers": 4},
    },
    "vit": {
        "base": MODEL_CONFIGS["vit"],
        "p2": {"patch": 2, "dim": 192, "depth": 6, "heads": 6, "grid": 64},
    },
    "gnn": {
        "base": MODEL_CONFIGS["gnn"],
        "ms": {"multiscale": True, "dim": 64, "coarse_layers": 12, "fine_layers": 6},
    },
}

# Official baseline configurations frozen after the dev tuning pass (2026-09-14, docs/tables/tuning_dev.md):
#   unet: base (the wide variant is within single-seed noise, +3 % at 2.2× the parameters; the distance channel hurts)
#   fno:  64 modes + distance-to-source channel (T1 rel-L2 1.14 → 0.34; the only configuration in which FNO recovers)
#   vit:  base (patch 2 and the distance channel do not help)
#   gnn:  multi-scale (4× coarsened graph) + distance channel (T1 1.04 → 0.69, T4 0.17 → 0.15)
OFFICIAL = {
    "unet": ("base", ()),
    "fno": ("m64", ("dist",)),
    "vit": ("base", ()),
    "gnn": ("ms", ("dist",)),
}
