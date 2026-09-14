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
        from ampscape.models.gnn import GridGNN

        return GridGNN(in_channels, **kw)
    raise ValueError(name)


MODEL_CONFIGS = {
    "unet": {"base": 32, "levels": 4},
    "fno": {"width": 32, "modes": 16, "layers": 4},
    "vit": {"patch": 4, "dim": 192, "depth": 6, "heads": 6},
    "gnn": {"dim": 64, "layers": 12},
}
